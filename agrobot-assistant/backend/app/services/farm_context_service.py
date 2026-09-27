import math
from datetime import date, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.database.schemas import WeatherSnapshot
from app.models.farm_context import (
    DataQualityAssessment,
    DataQualityLevel,
    DataSource,
    FarmContext,
    InputWarning,
    RainfallCompatibility,
    RainfallPeriod,
)
from app.services.weather_service import weather_service


NPK_DEFAULTS = {
    "sandy": {"N": 30.0, "P": 35.0, "K": 30.0},
    "loamy": {"N": 50.0, "P": 55.0, "K": 45.0},
    "clayey": {"N": 60.0, "P": 60.0, "K": 50.0},
    "silty": {"N": 55.0, "P": 50.0, "K": 40.0},
}
NPK_FALLBACK = {"N": 50.0, "P": 50.0, "K": 40.0}
PH_BY_TEXTURE = {"sandy": 6.0, "loamy": 6.5, "clayey": 7.0, "silty": 6.8}


def safe_float(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def safe_date(value: Any) -> Optional[date]:
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


class FarmContextService:
    async def build(
        self,
        db: Session,
        farm_id: int,
        user_id: int,
        user_data: dict[str, Any],
    ) -> tuple[FarmContext, DataQualityAssessment]:
        soil = user_data.get("set_1", {})
        fertility = user_data.get("set_2", {})
        irrigation = user_data.get("set_3", {})
        environment = user_data.get("set_4", {})
        practices = user_data.get("set_5", {})

        texture = str(soil.get("soil_texture") or "").strip().lower() or None
        soil_test_done = bool(fertility.get("soil_test_done"))
        tested_npk = [safe_float(fertility.get(key)) for key in ("npk_nitrogen", "npk_phosphorus", "npk_potassium")]
        has_measured_npk = soil_test_done and all(value is not None for value in tested_npk)

        if has_measured_npk:
            nitrogen, phosphorus, potassium = tested_npk
            npk_source = DataSource.LABORATORY_TEST
        else:
            base = NPK_DEFAULTS.get(texture or "", NPK_FALLBACK)
            factor = 1.0
            fertilizer_type = str(fertility.get("fertilizer_type") or "").lower()
            if fertilizer_type in {"chemical", "both"}:
                factor = 1.2
            elif fertilizer_type == "none":
                factor = 0.7
            nitrogen, phosphorus, potassium = (
                round(base["N"] * factor, 1),
                round(base["P"] * factor, 1),
                round(base["K"] * factor, 1),
            )
            npk_source = DataSource.QUESTIONNAIRE_ESTIMATE

        measured_ph = safe_float(fertility.get("soil_ph")) if soil_test_done else None
        ph = measured_ph if measured_ph is not None else PH_BY_TEXTURE.get(texture or "", 6.5)
        ph_source = DataSource.LABORATORY_TEST if measured_ph is not None else DataSource.QUESTIONNAIRE_ESTIMATE

        weather, weather_source = await self._weather(db, farm_id, environment)
        questionnaire_temperature = safe_float(environment.get("average_temperature"))
        if questionnaire_temperature is not None:
            temperature = questionnaire_temperature
            temperature_source = DataSource.FARMER_PROVIDED
        else:
            temperature = safe_float((weather or {}).get("temperature"))
            temperature_source = weather_source if temperature is not None else DataSource.UNKNOWN

        humidity = safe_float((weather or {}).get("humidity"))
        humidity_source = weather_source if humidity is not None else DataSource.UNKNOWN
        annual_rainfall = safe_float(environment.get("average_rainfall"))
        rainfall_source = (
            DataSource.FARMER_PROVIDED if annual_rainfall is not None else DataSource.UNKNOWN
        )

        context = FarmContext(
            farm_id=farm_id,
            user_id=user_id,
            state=self._optional_text(environment.get("state")),
            district=self._optional_text(environment.get("district")),
            soil_type=texture,
            season=self._optional_text(environment.get("season")),
            intended_sowing_date=safe_date(environment.get("intended_sowing_date")),
            previous_crop=self._optional_text(practices.get("previous_crop")),
            irrigation_method=self._optional_text(irrigation.get("irrigation_type")),
            water_availability=self._optional_text(irrigation.get("water_availability")),
            farm_size=safe_float(environment.get("total_area")),
            farm_size_unit=self._optional_text(environment.get("area_unit")),
            farmer_goal=self._optional_text(practices.get("farmer_goal")),
            soil_test_date=safe_date(fertility.get("soil_test_date")),
            nitrogen=nitrogen,
            phosphorus=phosphorus,
            potassium=potassium,
            ph=ph,
            temperature=temperature,
            humidity=humidity,
            rainfall_value=annual_rainfall,
            rainfall_unit="mm",
            rainfall_period=(
                RainfallPeriod.ANNUAL if annual_rainfall is not None else RainfallPeriod.UNKNOWN
            ),
            rainfall_compatibility=(
                RainfallCompatibility.INCOMPATIBLE_PERIOD
                if annual_rainfall is not None
                else RainfallCompatibility.UNKNOWN
            ),
            questionnaire_annual_rainfall_mm=annual_rainfall,
            seasonal_rainfall_mm=None,
            # The CSV calls this feature only `rainfall`; no repository source
            # documents its period. Annual questionnaire rainfall is therefore
            # never passed into the model or compared with its training range.
            model_compatible_rainfall_mm=None,
            npk_source=npk_source,
            ph_source=ph_source,
            temperature_source=temperature_source,
            humidity_source=humidity_source,
            rainfall_source=rainfall_source,
            farm_size_source=(
                DataSource.FARMER_PROVIDED
                if safe_float(environment.get("total_area")) is not None
                else DataSource.UNKNOWN
            ),
            weather_source=weather_source,
        )
        return context, self.assess_data_quality(context)

    async def _weather(self, db: Session, farm_id: int, environment: dict) -> tuple[Optional[dict], DataSource]:
        snapshot = (
            db.query(WeatherSnapshot)
            .filter(WeatherSnapshot.farm_id == farm_id, WeatherSnapshot.date == date.today())
            .first()
        )
        if snapshot:
            raw = snapshot.raw_json or {}
            current = raw.get("current", raw) if isinstance(raw, dict) else {}
            raw_source = str(snapshot.source or current.get("_source") or "").lower()
            source = DataSource.MOCK_FALLBACK if "mock" in raw_source else DataSource.CACHED_WEATHER_API
            return current, source

        district = self._optional_text(environment.get("district"))
        state = self._optional_text(environment.get("state"))
        if not district and not state:
            return None, DataSource.UNKNOWN
        weather = await weather_service.get_current_weather(district or state, state or district)
        if not weather:
            return None, DataSource.UNKNOWN
        raw_source = str(weather.get("_source") or "").lower()
        source = DataSource.MOCK_FALLBACK if "mock" in raw_source else DataSource.WEATHER_API
        snapshot = WeatherSnapshot(
            farm_id=farm_id,
            date=date.today(),
            source=source.value,
            temp=safe_float(weather.get("temperature")),
            humidity=safe_float(weather.get("humidity")),
            rainfall_mm=None,
            raw_json={"current": weather, "location": weather.get("location")},
        )
        db.add(snapshot)
        db.flush()
        return weather, source

    def assess_data_quality(self, context: FarmContext) -> DataQualityAssessment:
        measured = []
        estimated = []
        missing = []
        warnings: list[InputWarning] = []

        if context.npk_source == DataSource.LABORATORY_TEST:
            measured.extend(["N", "P", "K"])
        else:
            estimated.extend(["N", "P", "K"])
        if context.ph_source == DataSource.LABORATORY_TEST:
            measured.append("pH")
        else:
            estimated.append("pH")

        environmental_sources = {
            "temperature": context.temperature_source,
            "humidity": context.humidity_source,
        }
        for feature, source in environmental_sources.items():
            if getattr(context, feature) is None:
                missing.append(feature)
            elif source in {DataSource.WEATHER_API, DataSource.CACHED_WEATHER_API, DataSource.HISTORICAL_CLIMATE}:
                measured.append(feature)
            elif source in {DataSource.MOCK_FALLBACK, DataSource.CONFIGURED_DEFAULT, DataSource.QUESTIONNAIRE_ESTIMATE}:
                estimated.append(feature)

        if (
            context.model_compatible_rainfall_mm is not None
            and context.rainfall_compatibility == RainfallCompatibility.COMPATIBLE
        ):
            if context.rainfall_source == DataSource.HISTORICAL_CLIMATE:
                measured.append("rainfall")
            elif context.rainfall_source in {
                DataSource.CONFIGURED_DEFAULT,
                DataSource.MOCK_FALLBACK,
                DataSource.QUESTIONNAIRE_ESTIMATE,
            }:
                estimated.append("rainfall")

        if context.npk_source == DataSource.QUESTIONNAIRE_ESTIMATE or context.ph_source == DataSource.QUESTIONNAIRE_ESTIMATE:
            warnings.append(
                self._warning(
                    "ESTIMATED_SOIL_VALUES",
                    "NPK or pH values were estimated because complete soil-test values were not provided.",
                )
            )
        if context.soil_test_date is None and context.npk_source == DataSource.LABORATORY_TEST:
            warnings.append(
                self._warning(
                    "SOIL_TEST_DATE_UNKNOWN",
                    "The soil-test date is unknown, so the laboratory values cannot be confirmed as recent.",
                )
            )
        elif context.soil_test_date and context.soil_test_date < date.today() - timedelta(days=730):
            warnings.append(self._warning("SOIL_TEST_OLD", "The supplied soil test is more than two years old."))
        if context.weather_source == DataSource.MOCK_FALLBACK:
            warnings.append(
                self._warning(
                    "MOCK_WEATHER",
                    "Weather information is from a development fallback, not live conditions.",
                )
            )
        elif context.weather_source == DataSource.UNKNOWN:
            warnings.append(
                self._warning("WEATHER_UNAVAILABLE", "Current weather information is unavailable.")
            )
        if context.rainfall_source == DataSource.UNKNOWN:
            missing.append("rainfall")
            warnings.append(
                self._warning(
                    "RAINFALL_SEMANTICS_UNKNOWN",
                    "Comparable rainfall information is unavailable for the crop model.",
                )
            )
        elif context.rainfall_compatibility != RainfallCompatibility.COMPATIBLE:
            missing.append("model_compatible_rainfall")
            warnings.append(
                self._warning(
                    "RAINFALL_PERIOD_INCOMPATIBLE",
                    "The rainfall information provided cannot currently be compared reliably with the model's training data.",
                )
            )
        if context.intended_sowing_date is None:
            warnings.append(
                self._warning(
                    "SOWING_DATE_MISSING",
                    "Add the intended sowing date to check the crop's sowing window.",
                )
            )
        if missing:
            warnings.append(
                self._warning(
                    "MODEL_INPUTS_INCOMPLETE",
                    "Some information needed for the crop model is unavailable or incompatible.",
                )
            )

        recent_lab = bool(
            context.soil_test_date
            and context.soil_test_date >= date.today() - timedelta(days=730)
            and context.npk_source == DataSource.LABORATORY_TEST
            and context.ph_source == DataSource.LABORATORY_TEST
        )
        reliable_environment = all(
            source in {DataSource.WEATHER_API, DataSource.CACHED_WEATHER_API, DataSource.HISTORICAL_CLIMATE}
            for source in environmental_sources.values()
        )
        reliable_rainfall = (
            context.model_compatible_rainfall_mm is not None
            and context.rainfall_compatibility == RainfallCompatibility.COMPATIBLE
            and context.rainfall_source == DataSource.HISTORICAL_CLIMATE
        )
        if recent_lab and reliable_environment and reliable_rainfall and not missing:
            level = DataQualityLevel.HIGH
        elif estimated or missing or context.weather_source == DataSource.MOCK_FALLBACK:
            level = DataQualityLevel.LOW
        else:
            level = DataQualityLevel.MEDIUM
        if level == DataQualityLevel.LOW:
            warnings.append(
                self._warning(
                    "LOW_DATA_RELIABILITY",
                    "Important farm information is estimated, missing, or not directly comparable.",
                )
            )
        return DataQualityAssessment(
            level=level,
            measured_features=measured,
            estimated_features=estimated,
            missing_features=missing,
            warnings=list({warning.code: warning for warning in warnings}.values()),
        )

    @staticmethod
    def _warning(code: str, message: str) -> InputWarning:
        return InputWarning(code=code, message=message)

    @staticmethod
    def _optional_text(value: Any) -> Optional[str]:
        text = str(value or "").strip()
        return None if not text or text.lower() in {"not_sure", "unknown"} else text


farm_context_service = FarmContextService()
