from dataclasses import dataclass
from pathlib import Path


@dataclass
class TrainConfig:
    data_root: Path = Path("../Plant_Disease/Plant_Disease_Dataset")
    train_dir_name: str = "train"
    val_dir_name: str = "val"
    image_size: int = 224
    batch_size: int = 32
    num_workers: int = 2
    learning_rate: float = 1e-3
    epochs: int = 15
    seed: int = 42
    checkpoint_dir: Path = Path("artifacts/checkpoints")
    best_model_name: str = "best_model.pt"
    last_model_name: str = "last_model.pt"


@dataclass
class PredictConfig:
    image_size: int = 224
    checkpoint_path: Path = Path("artifacts/checkpoints/best_model.pt")
