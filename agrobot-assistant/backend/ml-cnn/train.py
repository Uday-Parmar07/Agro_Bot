import argparse
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim

from config import TrainConfig
from src.dataset import get_dataloaders
from src.model import PlantDiseaseCNN
from src.utils import evaluate, get_device, save_checkpoint, save_classes, set_seed, train_one_epoch


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train CNN for plant disease classification")
    parser.add_argument("--data-root", type=Path, default=TrainConfig.data_root)
    parser.add_argument("--epochs", type=int, default=TrainConfig.epochs)
    parser.add_argument("--batch-size", type=int, default=TrainConfig.batch_size)
    parser.add_argument("--learning-rate", type=float, default=TrainConfig.learning_rate)
    parser.add_argument("--image-size", type=int, default=TrainConfig.image_size)
    parser.add_argument("--num-workers", type=int, default=TrainConfig.num_workers)
    parser.add_argument("--seed", type=int, default=TrainConfig.seed)
    parser.add_argument("--checkpoint-dir", type=Path, default=TrainConfig.checkpoint_dir)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    set_seed(args.seed)

    train_loader, val_loader, class_names = get_dataloaders(
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
    optimizer = optim.Adam(model.parameters(), lr=args.learning_rate)

    best_val_acc = 0.0

    args.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    classes_path = args.checkpoint_dir / "classes.json"
    save_classes(classes_path, class_names)

    for epoch in range(1, args.epochs + 1):
        train_loss, train_acc = train_one_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_acc = evaluate(model, val_loader, criterion, device)

        print(
            f"Epoch {epoch}/{args.epochs} | "
            f"train_loss={train_loss:.4f} train_acc={train_acc:.4f} | "
            f"val_loss={val_loss:.4f} val_acc={val_acc:.4f}"
        )

        payload = {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "val_acc": val_acc,
            "class_names": class_names,
            "image_size": args.image_size,
        }

        save_checkpoint(args.checkpoint_dir / "last_model.pt", payload)

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            save_checkpoint(args.checkpoint_dir / "best_model.pt", payload)

    print(f"Training complete. Best val accuracy: {best_val_acc:.4f}")


if __name__ == "__main__":
    main()
