import argparse
from pathlib import Path

import torch
import torch.nn as nn

from config import TrainConfig
from src.dataset import get_dataloaders
from src.model import PlantDiseaseCNN
from src.utils import evaluate, get_device


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate trained CNN model")
    parser.add_argument("--data-root", type=Path, default=TrainConfig.data_root)
    parser.add_argument("--batch-size", type=int, default=TrainConfig.batch_size)
    parser.add_argument("--image-size", type=int, default=TrainConfig.image_size)
    parser.add_argument("--num-workers", type=int, default=TrainConfig.num_workers)
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=Path("artifacts/checkpoints/best_model.pt"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    _, val_loader, class_names = get_dataloaders(
        data_root=args.data_root,
        train_dir_name=TrainConfig.train_dir_name,
        val_dir_name=TrainConfig.val_dir_name,
        image_size=args.image_size,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
    )

    device = get_device()
    model = PlantDiseaseCNN(num_classes=len(class_names)).to(device)
    criterion = nn.CrossEntropyLoss()

    checkpoint = torch.load(args.checkpoint, map_location=device)
    model.load_state_dict(checkpoint["model_state_dict"])

    val_loss, val_acc = evaluate(model, val_loader, criterion, device)
    print(f"Validation loss: {val_loss:.4f}")
    print(f"Validation accuracy: {val_acc:.4f}")


if __name__ == "__main__":
    main()
