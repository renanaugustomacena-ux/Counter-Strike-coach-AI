import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.win_probability")


class WinProbabilityNN(nn.Module):
    def __init__(self, input_dim=9):
        super(WinProbabilityNN, self).__init__()
        self.model = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        return self.model(x)


def train_win_prob_model(data_df: pd.DataFrame, model_path: str):
    """
    Trains the Win Probability model using match snapshots.
    """
    features = [
        "ct_alive",
        "t_alive",
        "ct_health",
        "t_health",
        "ct_armor",
        "t_armor",
        "ct_eqp",
        "t_eqp",
        "bomb_planted",
    ]
    X = torch.tensor(data_df[features].values, dtype=torch.float32)
    y = torch.tensor(data_df["did_ct_win"].values, dtype=torch.float32).reshape(-1, 1)

    model = WinProbabilityNN(input_dim=len(features))
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    # WARNING (F3-19): Trains for a fixed 100 epochs on the FULL dataset with no train/val
    # split, no early stopping, and no overfitting detection. May overfit to training data,
    # producing overconfident win probability estimates. Acceptable for current prototype scope.
    model.train()
    for epoch in range(100):
        optimizer.zero_grad()
        outputs = model(X)
        loss = criterion(outputs, y)
        loss.backward()
        optimizer.step()
        if epoch % 20 == 0:
            logger.info("Epoch %s, Loss: %s", epoch, loss.item())

    torch.save(model.state_dict(), model_path)
    return model


def predict_win_prob(model, state_dict: dict):
    """
    Predicts win probability for a given state.
    """
    features = [
        "ct_alive",
        "t_alive",
        "ct_health",
        "t_health",
        "ct_armor",
        "t_armor",
        "ct_eqp",
        "t_eqp",
        "bomb_planted",
    ]
    x = torch.tensor([[state_dict.get(f, 0) for f in features]], dtype=torch.float32)
    model.eval()
    with torch.no_grad():
        prob = model(x).item()
    return prob
