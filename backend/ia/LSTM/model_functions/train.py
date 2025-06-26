import torch
from loguru import logger
import os

import matplotlib.pyplot as plt


def train_model(
    model,
    train_loader,
    loss_fn,
    optimizer,
    n_epochs,
    patience,
    device,
    plot_loss=False,
):
    loss_list = []

    best_loss = float("inf")
    patience_counter = 0
    best_model_state = None

    for epoch in range(n_epochs):
        model.train()
        epoch_loss = 0
        for X_batch, y_batch in train_loader:
            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device)
            optimizer.zero_grad()
            pred = model(X_batch)
            y_batch = y_batch.squeeze(-1)
            loss = loss_fn(pred, y_batch)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item() if loss.item() is not None else 0

        avg_loss = epoch_loss / len(train_loader)
        logger.info(f"Epoch {epoch+1}/{n_epochs} - Loss: {avg_loss:.4f}")
        loss_list.append(avg_loss)

        if avg_loss < best_loss:
            best_loss = avg_loss
            patience_counter = 0
            best_model_state = model.state_dict()  # Salva pesos
        else:
            patience_counter += 1

        if patience_counter >= patience:
            logger.info("Early stopping ativado!")
            n_epochs = epoch + 1
            break

    if best_model_state is not None:
        model.load_state_dict(best_model_state)

    plt.plot(range(1, n_epochs + 1), loss_list)
    plt.title("Erro Quadrático Médio (MSE) durante o Treinamento")
    plt.xlabel("Épocas")
    plt.ylabel("MSE")
    plt.xticks(range(1, n_epochs + 1, max(1, n_epochs // 10)))

    if not os.path.exists("ia_models"):
        os.makedirs("ia_models")
    plt.savefig("ia_models/loss.png")
    if plot_loss:
        plt.show()

    plt.close()
