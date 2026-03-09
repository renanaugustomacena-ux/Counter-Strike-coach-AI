import torch
from torch.utils.data import Dataset


class ProPerformanceDataset(Dataset):
    def __init__(self, X, y):
        # Avoid double wrapping if already a tensor
        if isinstance(X, torch.Tensor):
            self.X = X.clone().detach().requires_grad_(False).float()
        else:
            self.X = torch.tensor(X, dtype=torch.float32)

        if isinstance(y, torch.Tensor):
            self.y = y.clone().detach().requires_grad_(False).float()
        else:
            self.y = torch.tensor(y, dtype=torch.float32)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


class SelfSupervisedDataset(Dataset):
    """
    Dataset for JEPA Self-Supervised Learning.
    Splits long sequences of match state into (Context, Target) pairs.
    """

    def __init__(self, X: torch.Tensor, context_len: int = 10, prediction_len: int = 5):
        self.context_len = context_len
        self.prediction_len = prediction_len

        # Ensure X is a tensor
        if not isinstance(X, torch.Tensor):
            self.X = torch.tensor(X, dtype=torch.float32)
        else:
            self.X = X.clone().detach().float()

        # Assuming X is [N_samples, Features] (ticks)
        # We perform a sliding window over the data
        self.num_samples = len(self.X) - context_len - prediction_len

        if self.num_samples <= 0:
            raise ValueError(
                f"Data length {len(self.X)} too short for buffer {context_len+prediction_len}"
            )

    def __len__(self):
        # NOTE (F3-34): max(0, ...) guards against edge-case negatives. The constructor
        # raises ValueError for num_samples<=0, making len=0 unreachable in practice.
        # If this ever returns 0, DataLoader will silently produce no batches.
        return max(0, self.num_samples)

    def __getitem__(self, idx):
        # Context window: [t : t+context_len]
        context = self.X[idx : idx + self.context_len]

        # Target window: [t+context_len : t+context_len+prediction_len]
        target = self.X[idx + self.context_len : idx + self.context_len + self.prediction_len]

        return context, target
