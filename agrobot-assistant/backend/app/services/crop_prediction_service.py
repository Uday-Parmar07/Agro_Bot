"""XGBoost candidate generation with explicit model coverage and input status."""

import hashlib
import json
import logging
import math
import os
from pathlib import Path
from typing import Optional

from app.models.farm_context import FarmContext, RainfallCompatibility
from app.models.recommendation import (
    CandidateSource,
    CropCandidate,
    CropModelResult,
    ModelPredictionStatus,
    ValidationWarning,
)
from app.services.crop_catalog_service import crop_catalog_service


logger = logging.getLogger(__name__)
BACKEND_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = BACKEND_ROOT / "artifacts" / "xgboost_crop_model.joblib"
MODEL_METADATA_PATH = BACKEND_ROOT / "artifacts" / "xgboost_crop_metadata.json"
EXPECTED_FEATURE_COLUMNS = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
ABSOLUTE_INPUT_BOUNDS = {
    "N": (0.0, 1000.0),
    "P": (0.0, 1000.0),
    "K": (0.0, 1000.0),
    "temperature": (-30.0, 70.0),
    "humidity": (0.0, 100.0),
    "ph": (0.0, 14.0),
    "rainfall": (0.0, 10000.0),
}


class CropPredictionService:
    def __init__(self, model_path: Path = MODEL_PATH, metadata_path: Path = MODEL_METADATA_PATH):
        self.model_path = model_path
        self.metadata_path = metadata_path
        self._model = None
        self._label_encoder = None
        self._feature_columns: list[str] = []
        self._model_classes: list[str] = []
        self._metadata: dict = {}
        self._model_version = "unknown"
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        import joblib

        if not self.model_path.exists():
            raise FileNotFoundError(f"XGBoost model not found: {self.model_path}")
        artifact = joblib.load(self.model_path)
        required_keys = {"model", "label_encoder", "feature_columns"}
        if not required_keys.issubset(artifact):
            raise ValueError(f"Model artifact is missing keys: {sorted(required_keys - set(artifact))}")

        feature_columns = list(artifact["feature_columns"])
        if feature_columns != EXPECTED_FEATURE_COLUMNS:
            raise ValueError(
                f"Unexpected model feature order {feature_columns}; expected {EXPECTED_FEATURE_COLUMNS}"
            )
        model_classes = [str(item) for item in artifact["label_encoder"].classes_.tolist()]
        if not model_classes:
            raise ValueError("The model label encoder contains no crop classes")

        metadata = {}
        if self.metadata_path.exists():
            metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        digest = hashlib.sha256(self.model_path.read_bytes()).hexdigest()
        if metadata.get("model_sha256") and metadata["model_sha256"] != digest:
            logger.warning("Crop model metadata hash does not match the serialized artifact")
            metadata = {}

        consistency_errors = crop_catalog_service.validate_catalog_consistency(model_classes)
        missing_mapping = any(message.startswith("Model classes missing") for message in consistency_errors)
        if missing_mapping:
            raise ValueError("Crop catalogue does not cover every class in the loaded model")

        self._model = artifact["model"]
        self._label_encoder = artifact["label_encoder"]
        self._feature_columns = feature_columns
        self._model_classes = model_classes
        self._metadata = metadata
        self._model_version = metadata.get("model_version", f"xgboost-crop-{digest[:12]}")
        self._loaded = True
        logger.info(
            "Loaded crop candidate model %s with %d label-encoder classes",
            self._model_version,
            len(model_classes),
        )

    def get_model_classes(self) -> list[str]:
        self._ensure_loaded()
        return list(self._model_classes)

    def validate_catalog_at_startup(self) -> None:
        try:
            self._ensure_loaded()
        except Exception as exc:
            logger.error("Crop model/catalogue startup validation failed: %s", exc)

    def _validate_features(
        self,
        features: dict[str, Optional[float]],
        allowed_missing: set[str] | None = None,
    ) -> list[ValidationWarning]:
        warnings = []
        allowed_missing = allowed_missing or set()
        if list(features) != EXPECTED_FEATURE_COLUMNS:
            warnings.append(
                ValidationWarning(
                    code="FEATURE_ORDER_MISMATCH",
                    message="Inference feature names or order do not match the trained model contract.",
                )
            )
            return warnings
        for name, value in features.items():
            if name in allowed_missing and value is None:
                continue
            if value is None or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                warnings.append(
                    ValidationWarning(code="MISSING_OR_INVALID_FEATURE", message=f"{name} is missing or invalid.")
                )
                continue
            lower, upper = ABSOLUTE_INPUT_BOUNDS[name]
            if float(value) < lower or float(value) > upper:
                warnings.append(
                    ValidationWarning(
                        code="EXTREME_FEATURE_VALUE",
                        message=f"{name} is outside basic numeric safety bounds.",
                    )
                )
        return warnings

    def _distribution_warnings(self, features: dict[str, float]) -> list[ValidationWarning]:
        warnings = []
        ranges = self._metadata.get("feature_ranges", {})
        for name, value in features.items():
            limits = ranges.get(name)
            if not limits:
                continue
            if value < limits["min"] or value > limits["max"]:
                warnings.append(
                    ValidationWarning(
                        code="MODEL_INPUT_OUT_OF_RANGE",
                        message=(
                            f"{name} is outside the observed training range "
                            f"[{limits['min']}, {limits['max']}]."
                        ),
                    )
                )
        return warnings

    async def generate_candidates(self, context: FarmContext, top_k: Optional[int] = None) -> CropModelResult:
        features = context.model_features()
        base = {
            "model_version": self._model_version,
            "model_supported_crop_count": len(self._model_classes),
            "model_classes": list(self._model_classes),
            "feature_columns": list(EXPECTED_FEATURE_COLUMNS),
            "feature_values": features,
        }
        try:
            self._ensure_loaded()
            base.update(
                model_version=self._model_version,
                model_supported_crop_count=len(self._model_classes),
                model_classes=list(self._model_classes),
                feature_columns=list(self._feature_columns),
            )
        except Exception as exc:
            logger.error("Crop candidate model unavailable: %s", exc)
            return CropModelResult(
                status=ModelPredictionStatus.MODEL_UNAVAILABLE,
                warnings=[ValidationWarning(code="MODEL_UNAVAILABLE", message="Crop model is unavailable.")],
                **base,
            )

        rainfall_withheld = (
            context.model_compatible_rainfall_mm is None
            or context.rainfall_compatibility != RainfallCompatibility.COMPATIBLE
        )
        allow_missing_rainfall = os.getenv(
            "ENABLE_PRELIMINARY_MODEL_WITH_MISSING_RAINFALL", "true"
        ).lower() in {"1", "true", "yes"}
        if rainfall_withheld and not allow_missing_rainfall:
            return CropModelResult(
                status=ModelPredictionStatus.INSUFFICIENT_COMPATIBLE_INPUT,
                warnings=[
                    ValidationWarning(
                        code="RAINFALL_PERIOD_INCOMPATIBLE",
                        message=(
                            "The available rainfall value has not been shown to use the same period "
                            "as the model training feature. Model inference was not run."
                        ),
                    )
                ],
                **base,
            )

        # XGBoost has a defined missing-value path. Keep rainfall absent rather
        # than converting annual rainfall or inventing a model-scale default.
        # The result is always preliminary because this artifact was not
        # validated for farm records with a missing rainfall input.
        invalid = self._validate_features(
            features,
            allowed_missing={"rainfall"} if rainfall_withheld else set(),
        )
        if invalid:
            return CropModelResult(status=ModelPredictionStatus.INVALID_INPUT, warnings=invalid, **base)

        numeric_features = {key: float(value) for key, value in features.items() if value is not None}
        distribution_warnings = self._distribution_warnings(numeric_features)
        try:
            import numpy as np
            import pandas as pd

            inference_values = {
                column: numeric_features.get(column, np.nan)
                for column in self._feature_columns
            }
            frame = pd.DataFrame([inference_values], columns=self._feature_columns)
            probabilities = self._model.predict_proba(frame)[0]
            requested = top_k if top_k is not None else int(os.getenv("CROP_MODEL_TOP_K", "10"))
            limit = max(1, min(int(requested), len(self._model_classes)))
            top_indices = np.argsort(probabilities)[::-1][:limit]
            candidates = []
            for rank, index in enumerate(top_indices, start=1):
                raw_label = str(self._label_encoder.inverse_transform([int(index)])[0])
                profile = crop_catalog_service.get_crop_profile(raw_label)
                if not profile or not profile.is_active:
                    logger.error("Dropping model class without active catalogue profile: %s", raw_label)
                    continue
                candidates.append(
                    CropCandidate(
                        crop_slug=profile.crop_slug,
                        crop_name=profile.display_name,
                        candidate_sources=[CandidateSource.XGBOOST],
                        model_probability=float(probabilities[index]),
                        model_rank=rank,
                    )
                )
            if not candidates:
                return CropModelResult(status=ModelPredictionStatus.MODEL_UNAVAILABLE, **base)
            low_threshold = float(os.getenv("CROP_MODEL_LOW_CONFIDENCE_THRESHOLD", "0.15"))
            if rainfall_withheld:
                status = ModelPredictionStatus.PRELIMINARY_MISSING_INPUT
            elif distribution_warnings:
                status = ModelPredictionStatus.OUT_OF_DISTRIBUTION
            elif candidates[0].model_probability is not None and candidates[0].model_probability < low_threshold:
                status = ModelPredictionStatus.LOW_CONFIDENCE
            else:
                status = ModelPredictionStatus.SUCCESS
            result_warnings = list(distribution_warnings)
            if rainfall_withheld:
                result_warnings.append(
                    ValidationWarning(
                        code="MODEL_RAINFALL_WITHHELD",
                        message=(
                            "Rainfall was left missing during model inference because the available value "
                            "does not have compatible time-period semantics. This result is preliminary."
                        ),
                    )
                )
            if status == ModelPredictionStatus.LOW_CONFIDENCE:
                low_warning = ValidationWarning(
                    code="LOW_MODEL_CONFIDENCE",
                    message=(
                        "The strongest model match is below the provisional product threshold; "
                        "this probability is not calibrated as a real-world success rate."
                    ),
                )
                result_warnings.append(low_warning)
            return CropModelResult(
                status=status,
                candidates=candidates,
                warnings=result_warnings,
                **base,
            )
        except Exception as exc:
            logger.exception("XGBoost candidate generation failed: %s", exc)
            return CropModelResult(
                status=ModelPredictionStatus.MODEL_UNAVAILABLE,
                warnings=[ValidationWarning(code="MODEL_INFERENCE_FAILED", message="Crop model inference failed.")],
                **base,
            )


crop_prediction_service = CropPredictionService()
