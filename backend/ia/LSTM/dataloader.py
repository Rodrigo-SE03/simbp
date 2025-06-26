import torch
from torch.utils.data import Dataset, DataLoader


class BueiroDataset(Dataset):
    def __init__(self, X, y):
        self.X = torch.tensor(X, dtype=torch.float32)  # (batch, seq_len, n_features)
        self.y = torch.tensor(y, dtype=torch.float32).unsqueeze(-1)  # (batch, 1)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


def create_dataloaders(X_train, y_train, X_test, y_test, batch_size=32):
    train_loader = DataLoader(
        BueiroDataset(X_train, y_train), batch_size=batch_size, shuffle=True
    )
    test_loader = DataLoader(BueiroDataset(X_test, y_test), batch_size=batch_size)
    return train_loader, test_loader
