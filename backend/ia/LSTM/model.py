import torch
import torch.optim as optim
import torch.nn as nn
import pandas as pd
import joblib

from database.mongo import get_collection
from .preprocess import preprocess_data
from .dataloader import create_dataloaders
from .LSTM import LSTM

from .model_functions.train import train_model
from .model_functions.test import test_model
from .model_functions.predict import predict as p_func

import os


N_EPOCHS = 200
BATCH_SIZE = 64
HIDDEN_SIZE = 128
LEARNING_RATE = 0.00015
TEST_SIZE = 0.2
PATIENCE = 50

# Leitura a cada 15 minutos
PASSO = 4 * 24 * 7
FUTURE_STEPS = 4 * 12


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def save_model(model, scaler, le):
    if not os.path.exists("ia_models"):
        os.makedirs("ia_models")

    torch.save(model, "ia_models/modelo.pt")
    joblib.dump(scaler, "ia_models/scaler.pkl")
    joblib.dump(le, "ia_models/le.pkl")


def load_model():
    model = torch.load(
        "ia_models/modelo.pt", weights_only=False, map_location=torch.device("cpu")
    )
    model.eval()
    scaler = joblib.load("ia_models/scaler.pkl")
    le = joblib.load("ia_models/le.pkl")
    return model, scaler, le


def create_model(
    hidden_size=HIDDEN_SIZE,
    passo=PASSO,
    future_steps=FUTURE_STEPS,
    n_epochs=N_EPOCHS,
    batch_size=BATCH_SIZE,
    patience=PATIENCE,
    learning_rate=LEARNING_RATE,
):

    dados = list(get_collection().find())
    df = pd.DataFrame(dados)
    if df.empty:
        raise ValueError("Não há dados suficientes para treinar o modelo.")
    df.drop(columns=["_id"], inplace=True)

    df, X_train, X_test, y_train, y_test, scaler, le = preprocess_data(
        df, passo=passo, future_steps=future_steps, test_size=TEST_SIZE
    )
    train_loader, test_loader = create_dataloaders(
        X_train, y_train, X_test, y_test, batch_size
    )

    input_size = X_train.shape[2]
    model = LSTM(
        input_size=input_size,
        future_steps=future_steps,
        passo=passo,
        hidden_size=hidden_size,
    ).to(device)

    loss_fn = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)

    train_model(model, train_loader, loss_fn, optimizer, n_epochs, patience, device)
    test_model(model, test_loader, scaler, device=device)
    save_model(model, scaler, le)
    return model, scaler, le


def predict(model, scaler, le, mac):
    return p_func(model, scaler, le, mac)
