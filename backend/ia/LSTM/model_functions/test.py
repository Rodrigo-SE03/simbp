import torch
import numpy as np
import os

import matplotlib.pyplot as plt
from sklearn.metrics import r2_score


def plot(initial, y_true, y_pred, name, show=False):
    y_true = np.concatenate([initial, y_true])
    y_pred = np.concatenate([[initial[-1]], y_pred])

    x_true = range(len(y_true))
    x_pred = range(len(initial) - 1, len(initial) - 1 + len(y_pred))

    plt.plot(x_true, y_true, label="Curva Real")
    plt.plot(x_pred, y_pred, label="Curva Prevista")

    plt.title(name)
    plt.xlabel("Passos")
    plt.ylabel("Valores")
    plt.legend()

    if not os.path.exists("ia_models"):
        os.makedirs("ia_models")

    plt.savefig(f"ia_models/{name.lower().replace(' ', '_')}.png")
    if show:
        plt.show()
    plt.close()


def test_model(model, test_loader, scaler, device, show=False):

    model.eval()
    preds = []
    truths = []
    initial_values = []

    with torch.no_grad():
        for X_batch, y_batch in test_loader:
            x_input = X_batch.to(device)
            pred = model(x_input)
            preds.append(pred.cpu().numpy())
            truths.append(y_batch.cpu().numpy())
            initial_values.append(X_batch[:, :, 0].cpu().numpy())

    preds = np.concatenate(preds, axis=0)
    truths = np.concatenate(truths, axis=0).squeeze(-1)
    initial_values = np.concatenate(initial_values, axis=0)

    y_test_original = scaler.inverse_transform(truths)
    y_pred_original = scaler.inverse_transform(preds)
    initial_values_original = scaler.inverse_transform(initial_values)

    mae = np.mean(np.abs(y_test_original - y_pred_original))
    rmse = np.sqrt(np.mean((y_test_original - y_pred_original) ** 2))
    wape = np.sum(np.abs(y_test_original - y_pred_original)) / np.sum(
        np.abs(y_test_original)
    )

    print(f"RMSE: {rmse:.4f}")
    print(f"MAE: {mae:.4f}")
    print(f"WAPE: {wape:.4f}")

    y_true_mean = np.mean(y_test_original, axis=0)
    y_pred_mean = np.mean(y_pred_original, axis=0)
    initial_mean = np.mean(initial_values_original, axis=0)
    plot(
        initial_mean,
        y_true_mean,
        y_pred_mean,
        "Comparação entre Curva Real vs Prevista (Média)",
        show=show,
    )

    for i in range(4):
        initial = initial_values_original[i, :]
        y_true = y_test_original[i, :]
        y_pred = y_pred_original[i, :]
        plot(
            initial,
            y_true,
            y_pred,
            f"Comparação entre Curva Real vs Prevista ({i})",
            show=show,
        )
