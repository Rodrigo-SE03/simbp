import torch
import pandas as pd
import numpy as np
from database.mongo import get_collection
from ..preprocess import preprocess_data, preprocess_input
from loguru import logger


def predict(model, scaler, le, mac):
    cursor = (
        get_collection()
        .find({"mac": mac})
        .sort("timestamp", -1)
        .limit(model.future_steps)
    )
    dados = list(cursor)
    if len(dados) < model.future_steps:
        logger.warning("Não há dados suficientes para esse MAC.")
        return []

    dados = sorted(dados, key=lambda x: x["timestamp"])
    df = pd.DataFrame(dados)
    X_seq = preprocess_input(df, scaler, le, model.passo, model.future_steps)
    model.eval()
    with torch.no_grad():
        output = model(X_seq)

    # Reverter escala
    output_np = output.numpy().squeeze()
    output_original = scaler.inverse_transform(output_np.reshape(-1, 1)).flatten()

    return output_original[: model.future_steps]
