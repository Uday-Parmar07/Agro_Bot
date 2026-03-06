import argparse
import json
import random
from pathlib import Path

import torch
from PIL import Image
from torchvision import transforms

from config import PredictConfig
from config import TrainConfig
from src.model import PlantDiseaseCNN
from src.utils import get_device


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Predict plant disease class from one image")
    parser.add_argument("--image", type=Path)
    parser.add_argument("--data-root", type=Path, default=TrainConfig.data_root)
    parser.add_argument(
        "--split",
        type=str,
        choices=["train", "val"],
        default="val",
        help="Dataset split used for random image selection when --image is omitted.",
    )
    parser.add_argument("--checkpoint", type=Path, default=PredictConfig.checkpoint_path)
    parser.add_argument("--classes", type=Path, default=Path("artifacts/checkpoints/classes.json"))
    parser.add_argument("--image-size", type=int, default=PredictConfig.image_size)
    return parser.parse_args()


def choose_random_image(data_root: Path, split: str) -> Path:
    split_dir = data_root / split
    if not split_dir.exists() or not split_dir.is_dir():
        raise FileNotFoundError(f"Split directory not found: {split_dir}")

    candidates = [
        path
        for path in split_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]
    if not candidates:
        raise FileNotFoundError(f"No images found in: {split_dir}")

    return random.choice(candidates)


def main() -> None:
    args = parse_args()
    device = get_device()

    image_path = args.image if args.image else choose_random_image(args.data_root, args.split)

    class_names = json.loads(args.classes.read_text(encoding="utf-8"))

    model = PlantDiseaseCNN(num_classes=len(class_names)).to(device)
    checkpoint = torch.load(args.checkpoint, map_location=device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    transform = transforms.Compose(
        [
            transforms.Resize((args.image_size, args.image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    image = Image.open(image_path).convert("RGB")
    tensor = transform(image).unsqueeze(0).to(device)

    with torch.no_grad():
        logits = model(tensor)
        probs = torch.softmax(logits, dim=1)
        score, pred_idx = torch.max(probs, dim=1)

    predicted_class = class_names[pred_idx.item()]
    confidence = score.item()

    print(f"Image used: {image_path}")
    print(f"Predicted class: {predicted_class}")
    print(f"Confidence: {confidence:.4f}")


if __name__ == "__main__":
    main()
