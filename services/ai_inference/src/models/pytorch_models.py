import torch
import torch.nn as nn
import torch.nn.functional as F

class TabularClassifier(nn.Module):
    """
    Feedforward Neural Network for Structured Tabular Classification / Scoring.
    """
    def __init__(self, input_dim: int = 4, hidden_dim: int = 32, num_classes: int = 2):
        super(TabularClassifier, self).__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.bn1 = nn.BatchNorm1d(hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim // 2)
        self.fc3 = nn.Linear(hidden_dim // 2, num_classes)
        self.dropout = nn.Dropout(0.2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = F.relu(self.fc1(x))
        if not self.training or x.size(0) > 1:
            x = self.bn1(x)
        x = self.dropout(x)
        x = F.relu(self.fc2(x))
        x = self.fc3(x)
        return x

class TextEmbeddingClassifier(nn.Module):
    """
    Embedding Bag & Dense Neural Network for Text Understanding & Sentiment Classification.
    """
    def __init__(self, vocab_size: int = 5000, embed_dim: int = 64, num_classes: int = 3):
        super(TextEmbeddingClassifier, self).__init__()
        self.embedding = nn.EmbeddingBag(vocab_size, embed_dim, sparse=False)
        self.fc1 = nn.Linear(embed_dim, 32)
        self.fc2 = nn.Linear(32, num_classes)
        self.dropout = nn.Dropout(0.2)

    def forward(self, text_tensor: torch.Tensor, offsets: torch.Tensor = None) -> torch.Tensor:
        embedded = self.embedding(text_tensor, offsets)
        x = F.relu(self.fc1(embedded))
        x = self.dropout(x)
        x = self.fc2(x)
        return x
