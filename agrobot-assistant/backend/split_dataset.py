from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split image dataset by class folders into train/val sets."
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path("Plant_Disease/PlantVillage"),
        help="Directory containing disease class subfolders.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("Plant_Disease/split"),
        help="Output directory where train/ and val/ folders are created.",
    )
    parser.add_argument(
        "--val-ratio",
        type=float,
        default=0.2,
        help="Validation split ratio (default: 0.2).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible shuffling.",
    )
    parser.add_argument(
        "--move",
        action="store_true",
        help="Move files instead of copying.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Delete output directory before splitting if it already exists.",
    )
    args, _ = parser.parse_known_args()
    return args


def list_images(class_dir: Path) -> list[Path]:
    return [
        file_path
        for file_path in class_dir.iterdir()
        if file_path.is_file() and file_path.suffix.lower() in IMAGE_EXTENSIONS
    ]


def compute_split_counts(total: int, val_ratio: float) -> tuple[int, int]:
    if total <= 1:
        return total, 0

    val_count = int(round(total * val_ratio))
    val_count = max(1, min(val_count, total - 1))
    train_count = total - val_count
    return train_count, val_count


def split_dataset(
    source_dir: Path,
    output_dir: Path,
    val_ratio: float,
    seed: int,
    move_files: bool,
) -> None:
    class_dirs = sorted([path for path in source_dir.iterdir() if path.is_dir()])
    if not class_dirs:
        raise ValueError(f"No class folders found in: {source_dir}")

    random.seed(seed)
    copy_or_move = shutil.move if move_files else shutil.copy2

    total_train = 0
    total_val = 0

    for class_dir in class_dirs:
        images = list_images(class_dir)
        if not images:
            print(f"Skipping {class_dir.name}: no images found")
            continue

        random.shuffle(images)
        train_count, val_count = compute_split_counts(len(images), val_ratio)

        train_images = images[:train_count]
        val_images = images[train_count:]

        train_class_dir = output_dir / "train" / class_dir.name
        val_class_dir = output_dir / "val" / class_dir.name
        train_class_dir.mkdir(parents=True, exist_ok=True)
        val_class_dir.mkdir(parents=True, exist_ok=True)

        for image_path in train_images:
            copy_or_move(image_path, train_class_dir / image_path.name)
        for image_path in val_images:
            copy_or_move(image_path, val_class_dir / image_path.name)

        total_train += len(train_images)
        total_val += len(val_images)

        print(
            f"{class_dir.name}: total={len(images)}, train={len(train_images)}, val={len(val_images)}"
        )

    print("\nSplit complete")
    print(f"Output: {output_dir}")
    print(f"Total train images: {total_train}")
    print(f"Total val images: {total_val}")


def main() -> None:
    args = parse_args()

    if not args.source_dir.exists() or not args.source_dir.is_dir():
        raise FileNotFoundError(f"Source directory not found: {args.source_dir}")

    if not (0 < args.val_ratio < 1):
        raise ValueError("--val-ratio must be between 0 and 1")

    if args.output_dir.exists():
        if args.overwrite:
            shutil.rmtree(args.output_dir)
        elif any(args.output_dir.iterdir()):
            raise FileExistsError(
                f"Output directory already exists and is not empty: {args.output_dir}. "
                "Use --overwrite to replace it."
            )

    split_dataset(
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        val_ratio=args.val_ratio,
        seed=args.seed,
        move_files=args.move,
    )


if __name__ == "__main__":
    main()
