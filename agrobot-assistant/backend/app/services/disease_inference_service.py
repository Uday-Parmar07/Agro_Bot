import io
import json
import os
import base64
import logging
from pathlib import Path

from PIL import Image


logger = logging.getLogger(__name__)


class DiseaseInferenceService:
    def __init__(self) -> None:
        self._loaded = False
        self._device = None
        self._torch = None
        self._transforms = None
        self._model = None
        self._class_names: list[str] = []
        self._groq_client = None
        self._vision_model = os.getenv("DISEASE_VISION_MODEL", "llama-3.2-11b-vision-preview")

        groq_api_key = os.getenv("GROQ_API_KEY")
        if groq_api_key:
            try:
                from groq import Groq
                self._groq_client = Groq(api_key=groq_api_key)
            except Exception as exc:
                logger.warning("Groq client init failed, using fallback disease guidance: %s", exc)

    def _build_model(self, num_classes: int):
        nn = self._torch.nn

        class PlantDiseaseCNN(nn.Module):
            def __init__(self, classes_count: int):
                super().__init__()
                self.features = nn.Sequential(
                    nn.Conv2d(3, 32, kernel_size=3, padding=1),
                    nn.BatchNorm2d(32),
                    nn.ReLU(inplace=True),
                    nn.MaxPool2d(kernel_size=2),
                    nn.Conv2d(32, 64, kernel_size=3, padding=1),
                    nn.BatchNorm2d(64),
                    nn.ReLU(inplace=True),
                    nn.MaxPool2d(kernel_size=2),
                    nn.Conv2d(64, 128, kernel_size=3, padding=1),
                    nn.BatchNorm2d(128),
                    nn.ReLU(inplace=True),
                    nn.MaxPool2d(kernel_size=2),
                    nn.Conv2d(128, 256, kernel_size=3, padding=1),
                    nn.BatchNorm2d(256),
                    nn.ReLU(inplace=True),
                    nn.MaxPool2d(kernel_size=2),
                )
                self.classifier = nn.Sequential(
                    nn.AdaptiveAvgPool2d((1, 1)),
                    nn.Flatten(),
                    nn.Dropout(0.3),
                    nn.Linear(256, 128),
                    nn.ReLU(inplace=True),
                    nn.Dropout(0.3),
                    nn.Linear(128, classes_count),
                )

            def forward(self, x):
                x = self.features(x)
                x = self.classifier(x)
                return x

        return PlantDiseaseCNN(num_classes)

    def _resolve_paths(self) -> tuple[Path, Path]:
        backend_dir = Path(__file__).resolve().parents[2]
        checkpoint_path = backend_dir / "ml-cnn" / "artifacts" / "checkpoints" / "best_model.pt"
        classes_path = backend_dir / "ml-cnn" / "artifacts" / "checkpoints" / "classes.json"
        return checkpoint_path, classes_path

    def _format_class_name(self, class_name: str) -> str:
        return class_name.replace("___", " - ").replace("__", " ").replace("_", " ")

    def _fallback_insights(self, class_name: str) -> dict:
        friendly_name = self._format_class_name(class_name)
        lower_name = class_name.lower()

        if "healthy" in lower_name:
            return {
                "detailed_classification": friendly_name,
                "possible_cause": "No visible disease symptoms detected. Plant appears healthy.",
                "treatment": "No treatment needed. Continue regular irrigation, balanced nutrition, and field monitoring.",
                "llm_enhanced": False,
            }

        return {
            "detailed_classification": friendly_name,
            "possible_cause": (
                f"Likely {friendly_name}. Common causes include fungal/bacterial/viral pressure, humid weather, "
                "poor air circulation, contaminated tools, or infected seedlings."
            ),
            "treatment": (
                "Isolate affected leaves, improve ventilation, avoid overhead irrigation, apply crop-specific "
                "recommended fungicide/bactericide as per local agronomy guidance, and monitor spread for 5-7 days."
            ),
            "llm_enhanced": False,
        }

    def _llm_insights(self, image_bytes: bytes, content_type: str, class_name: str) -> dict:
        if self._groq_client is None:
            return self._fallback_insights(class_name)

        try:
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            data_url = f"data:{content_type};base64,{image_b64}"

            prompt = (
                "You are an expert plant pathologist. Analyze the uploaded leaf image and the CNN suggestion. "
                "Return strict JSON with keys: detailed_classification, possible_cause, treatment. "
                f"CNN predicted class: {class_name}. "
                "Treatment must be practical, concise, and farmer-friendly."
            )

            completion = self._groq_client.chat.completions.create(
                model=self._vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }
                ],
                temperature=0.2,
                max_tokens=500,
                response_format={"type": "json_object"},
            )

            raw = completion.choices[0].message.content
            parsed = json.loads(raw)

            detailed_classification = parsed.get("detailed_classification") or self._format_class_name(class_name)
            possible_cause = parsed.get("possible_cause") or self._fallback_insights(class_name)["possible_cause"]
            treatment = parsed.get("treatment") or self._fallback_insights(class_name)["treatment"]

            return {
                "detailed_classification": detailed_classification,
                "possible_cause": possible_cause,
                "treatment": treatment,
                "llm_enhanced": True,
            }
        except Exception as exc:
            logger.warning("LLM image analysis failed, falling back to default guidance: %s", exc)
            return self._fallback_insights(class_name)

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        try:
            import torch
            from torchvision import transforms
        except ImportError as exc:
            raise RuntimeError("Missing ML dependencies. Install torch and torchvision in backend environment.") from exc

        self._torch = torch
        self._transforms = transforms
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        checkpoint_path, classes_path = self._resolve_paths()
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Model checkpoint not found: {checkpoint_path}")
        if not classes_path.exists():
            raise FileNotFoundError(f"Classes file not found: {classes_path}")

        self._class_names = json.loads(classes_path.read_text(encoding="utf-8"))
        if not self._class_names:
            raise RuntimeError("classes.json is empty")

        model = self._build_model(num_classes=len(self._class_names)).to(self._device)
        checkpoint = torch.load(checkpoint_path, map_location=self._device)

        model_state_dict = checkpoint.get("model_state_dict") if isinstance(checkpoint, dict) else None
        if model_state_dict is None:
            raise RuntimeError("Invalid checkpoint format: missing model_state_dict")

        model.load_state_dict(model_state_dict)
        model.eval()
        self._model = model
        self._loaded = True

    def predict(self, image_bytes: bytes, content_type: str = "image/jpeg") -> dict:
        self._ensure_loaded()

        transform = self._transforms.Compose(
            [
                self._transforms.Resize((224, 224)),
                self._transforms.ToTensor(),
                self._transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ]
        )

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        tensor = transform(image).unsqueeze(0).to(self._device)

        with self._torch.no_grad():
            logits = self._model(tensor)
            probs = self._torch.softmax(logits, dim=1)
            score, pred_idx = self._torch.max(probs, dim=1)

        predicted_class = self._class_names[pred_idx.item()]
        confidence = float(score.item())
        insights = self._llm_insights(image_bytes=image_bytes, content_type=content_type, class_name=predicted_class)

        return {
            "predicted_class": predicted_class,
            "confidence": confidence,
            "detailed_classification": insights["detailed_classification"],
            "possible_cause": insights["possible_cause"],
            "treatment": insights["treatment"],
            "llm_enhanced": insights["llm_enhanced"],
        }


disease_inference_service = DiseaseInferenceService()
