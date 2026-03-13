"""XGBoost-based crop prediction service.

Loads the trained model lazily, builds a feature vector from questionnaire
data + weather API, and returns the top-N crop predictions with confidence.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).resolve().parents[2] / "artifacts" / "xgboost_crop_model.joblib"

# Smart defaults for NPK by soil texture (kg/ha, calibrated to dataset ranges)
_NPK_DEFAULTS = {
    "sandy":  {"N": 30.0, "P": 35.0, "K": 30.0},
    "loamy":  {"N": 50.0, "P": 55.0, "K": 45.0},
    "clayey": {"N": 60.0, "P": 60.0, "K": 50.0},
    "silty":  {"N": 55.0, "P": 50.0, "K": 40.0},
}
_NPK_FALLBACK = {"N": 50.0, "P": 50.0, "K": 40.0}

_PH_BY_TEXTURE = {
    "sandy": 6.0,
    "loamy": 6.5,
    "clayey": 7.0,
    "silty": 6.8,
}


class CropPredictionService:
    """XGBoost crop prediction with lazy model loading."""

    def __init__(self):
        self._model = None
        self._label_encoder = None
        self._feature_columns = None
        self._loaded = False

    # ── Lazy loading ──────────────────────────────────────────────────

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        import joblib

        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"XGBoost model not found: {MODEL_PATH}")

        artifact = joblib.load(MODEL_PATH)
        self._model = artifact["model"]
        self._label_encoder = artifact["label_encoder"]
        self._feature_columns = artifact["feature_columns"]
        self._loaded = True
        logger.info(
            "XGBoost crop model loaded: %d classes, features=%s",
            len(self._label_encoder.classes_),
            self._feature_columns,
        )

    # ── Feature extraction ────────────────────────────────────────────

    async def _build_feature_vector(self, user_data: Dict[str, Any]) -> Dict[str, float]:
        """Build [N, P, K, temperature, humidity, ph, rainfall] from user data + weather."""
        soil_physical = user_data.get("set_1", {})
        soil_fertility = user_data.get("set_2", {})
        environmental = user_data.get("set_4", {})

        texture = str(soil_physical.get("soil_texture", "")).lower()
        soil_test_done = bool(soil_fertility.get("soil_test_done"))
        fertilizer_type = str(soil_fertility.get("fertilizer_type", "none")).lower()

        n = self._resolve_npk(soil_fertility.get("npk_nitrogen"), soil_test_done, "N", texture, fertilizer_type)
        p = self._resolve_npk(soil_fertility.get("npk_phosphorus"), soil_test_done, "P", texture, fertilizer_type)
        k = self._resolve_npk(soil_fertility.get("npk_potassium"), soil_test_done, "K", texture, fertilizer_type)
        ph = self._resolve_ph(soil_fertility.get("soil_ph"), soil_test_done, texture)

        rainfall = self._safe_float(environmental.get("average_rainfall"))
        if rainfall is None:
            rainfall = 850.0

        temperature = self._safe_float(environmental.get("average_temperature"))
        humidity = None

        if temperature is None or humidity is None:
            weather = await self._fetch_weather(user_data)
            if weather:
                if temperature is None:
                    temperature = weather.get("temperature", 27.0)
                if humidity is None:
                    humidity = weather.get("humidity", 65.0)

        if temperature is None:
            temperature = 27.0
        if humidity is None:
            humidity = 65.0

        return {
            "N": n, "P": p, "K": k,
            "temperature": temperature,
            "humidity": humidity,
            "ph": ph,
            "rainfall": rainfall,
        }

    @staticmethod
    def _resolve_npk(raw_value, soil_test_done: bool, nutrient: str,
                     texture: str, fertilizer_type: str) -> float:
        if soil_test_done:
            val = CropPredictionService._safe_float(raw_value)
            if val is not None:
                return val

        base = _NPK_DEFAULTS.get(texture, _NPK_FALLBACK)
        value = base[nutrient]

        if fertilizer_type in ("chemical", "both"):
            value *= 1.2
        elif fertilizer_type == "none":
            value *= 0.7

        return round(value, 1)

    @staticmethod
    def _resolve_ph(raw_ph, soil_test_done: bool, texture: str) -> float:
        if soil_test_done:
            val = CropPredictionService._safe_float(raw_ph)
            if val is not None:
                return val
        return _PH_BY_TEXTURE.get(texture, 6.5)

    @staticmethod
    async def _fetch_weather(user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            from app.services.weather_service import weather_service

            environmental = user_data.get("set_4", {})
            district = environmental.get("district", "")
            state = environmental.get("state", "")

            if not district and not state:
                return None

            return await weather_service.get_current_weather(
                city=district or state,
                state=state or district,
            )
        except Exception as e:
            logger.warning("Weather fetch failed during crop prediction: %s", e)
            return None

    @staticmethod
    def _safe_float(value) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    # ── Prediction ────────────────────────────────────────────────────

    async def predict_crops(self, user_data: Dict[str, Any],
                            top_n: int = 5) -> List[Dict[str, Any]]:
        """Return top N crop predictions with confidence scores.

        Returns: [{"crop_name": "rice", "confidence": 0.87, "rank": 1}, ...]
        """
        try:
            self._ensure_loaded()
        except Exception as e:
            logger.error("Failed to load XGBoost model: %s", e)
            return []

        try:
            import numpy as np
            import pandas as pd

            features = await self._build_feature_vector(user_data)
            logger.info("XGBoost feature vector: %s", features)

            df = pd.DataFrame([features])[self._feature_columns]
            proba = self._model.predict_proba(df)[0]

            top_indices = np.argsort(proba)[::-1][:top_n]

            predictions = []
            for rank, idx in enumerate(top_indices, start=1):
                crop_name = self._label_encoder.inverse_transform([idx])[0]
                confidence = float(proba[idx])
                if confidence >= 0.01:
                    predictions.append({
                        "crop_name": crop_name,
                        "confidence": round(confidence, 4),
                        "rank": rank,
                    })

            logger.info("XGBoost predictions: %s", predictions)
            return predictions

        except Exception as e:
            logger.error("XGBoost prediction failed: %s", e, exc_info=True)
            return []


crop_prediction_service = CropPredictionService()
