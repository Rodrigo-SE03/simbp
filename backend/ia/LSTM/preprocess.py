import torch
import numpy as np
from sklearn.preprocessing import MinMaxScaler, LabelEncoder
from sklearn.model_selection import train_test_split


def gerar_sequencias_multivariadas(df, features_columns, passo=4, future_steps=3):
    X, y = [], []
    for mac in df["mac"].unique():

        df_mac = df[df["mac"] == mac].sort_values("timestamp")
        features = df_mac[features_columns].values
        targets = df_mac["distancia_norm"].values
        if len(features) < passo + future_steps:
            continue

        for i in range(len(features) - passo - future_steps):
            X.append(features[i : i + passo])
            y.append(targets[i + passo : i + passo + future_steps])

    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


def preprocess_data(df, passo=4, future_steps=3, test_size=0.2):

    scaler = MinMaxScaler()
    df["distancia_norm"] = scaler.fit_transform(df[["distancia"]])

    le = LabelEncoder()
    df["tipo_zona_encoded"] = le.fit_transform(df["tipo_zona"])

    features = ["distancia_norm", "tipo_zona_encoded", "rain_level"]
    X, y = gerar_sequencias_multivariadas(
        df, features, passo=passo, future_steps=future_steps
    )
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, shuffle=False
    )
    return df, X_train, X_test, y_train, y_test, scaler, le


def preprocess_input(df_raw, scaler, le, passo, future_steps):

    df_raw["distancia_norm"] = scaler.transform(df_raw[["distancia"]])
    df_raw["tipo_zona_encoded"] = le.transform(df_raw["tipo_zona"])

    if df_raw["tipo_zona_encoded"].isnull().any():
        raise ValueError("Tipo de zona desconhecido detectado.")

    features = ["distancia_norm", "tipo_zona_encoded", "rain_level"]
    df_input = df_raw[features]

    if len(df_input) < future_steps:
        raise ValueError(f"São necessários pelo menos {future_steps} pontos.")

    X_seq = df_input.iloc[-future_steps:].values.astype(np.float32)
    X_seq = torch.tensor(X_seq).unsqueeze(0)
    return X_seq
