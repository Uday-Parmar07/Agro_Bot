from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DataSource(str, Enum):
    LABORATORY_TEST = "laboratory_test"
    FARMER_PROVIDED = "farmer_provided"
    QUESTIONNAIRE_ESTIMATE = "questionnaire_estimate"
    WEATHER_API = "weather_api"
    CACHED_WEATHER_API = "cached_weather_api"
    HISTORICAL_CLIMATE = "historical_climate"
    CONFIGURED_DEFAULT = "configured_default"
    MOCK_FALLBACK = "mock_fallback"
    UNKNOWN = "unknown"


class DataQualityLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RainfallPeriod(str, Enum):
    DAILY = "daily"
    MONTHLY = "monthly"
    CROP_SEASON = "crop_season"
    ANNUAL = "annual"
    TRAINING_DATASET_UNSPECIFIED = "training_dataset_unspecified"
    UNKNOWN = "unknown"


class RainfallCompatibility(str, Enum):
    COMPATIBLE = "compatible"
    INCOMPATIBLE_PERIOD = "incompatible_period"
    UNKNOWN = "unknown"


class InputWarning(BaseModel):
    code: str
    message: str


class DataQualityAssessment(BaseModel):
    level: DataQualityLevel
    score: None = None
    measured_features: list[str] = Field(default_factory=list)
    estimated_features: list[str] = Field(default_factory=list)
    missing_features: list[str] = Field(default_factory=list)
    warnings: list[InputWarning] = Field(default_factory=list)


class FarmContext(BaseModel):
    farm_id: int
    user_id: int
    state: Optional[str] = None
    district: Optional[str] = None
    soil_type: Optional[str] = None
    season: Optional[str] = None
    intended_sowing_date: Optional[date] = None
    previous_crop: Optional[str] = None
    irrigation_method: Optional[str] = None
    water_availability: Optional[str] = None
    farm_size: Optional[float] = None
    farm_size_unit: Optional[str] = None
    farmer_goal: Optional[str] = None
    soil_test_date: Optional[date] = None

    nitrogen: Optional[float] = None
    phosphorus: Optional[float] = None
    potassium: Optional[float] = None
    ph: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    rainfall_value: Optional[float] = None
    rainfall_unit: str = "mm"
    rainfall_period: RainfallPeriod = RainfallPeriod.UNKNOWN
    rainfall_compatibility: RainfallCompatibility = RainfallCompatibility.UNKNOWN
    questionnaire_annual_rainfall_mm: Optional[float] = None
    seasonal_rainfall_mm: Optional[float] = None
    model_compatible_rainfall_mm: Optional[float] = None

    npk_source: DataSource = DataSource.UNKNOWN
    ph_source: DataSource = DataSource.UNKNOWN
    temperature_source: DataSource = DataSource.UNKNOWN
    humidity_source: DataSource = DataSource.UNKNOWN
    rainfall_source: DataSource = DataSource.UNKNOWN
    farm_size_source: DataSource = DataSource.UNKNOWN
    weather_source: DataSource = DataSource.UNKNOWN

    @property
    def intended_sowing_month(self) -> Optional[int]:
        return self.intended_sowing_date.month if self.intended_sowing_date else None

    def model_features(self) -> dict[str, Optional[float]]:
        return {
            "N": self.nitrogen,
            "P": self.phosphorus,
            "K": self.potassium,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "ph": self.ph,
            "rainfall": self.model_compatible_rainfall_mm,
        }
