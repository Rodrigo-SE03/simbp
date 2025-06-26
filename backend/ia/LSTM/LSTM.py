import torch.nn as nn


class LSTM(nn.Module):
    def __init__(self, input_size, hidden_size=64, future_steps=3, passo=4):
        super().__init__()
        self.future_steps = future_steps
        self.passo = passo
        self.lstm = nn.LSTM(
            input_size=input_size, hidden_size=hidden_size, batch_first=True
        )
        self.fc = nn.Linear(hidden_size, future_steps)

    def forward(self, x):
        _, (hn, _) = self.lstm(x)
        return self.fc(hn.squeeze(0))
