from pydantic import BaseModel
from typing import Dict, Any, Optional
from enum import Enum

class SoilTexture(str, Enum):
    SANDY = "sandy"
    LOAMY = "loamy"
    CLAYEY = "clayey"
    SILTY = "silty"
    DONT_KNOW = "dont_know"

class WaterRetention(str, Enum):
    RETAINS_LONG = "retains_long"
    DRAINS_QUICKLY = "drains_quickly"
    MODERATE = "moderate"

class SoilTopLayer(str, Enum):
    DARK_CRUMBLY = "dark_crumbly"
    HARD_COMPACT = "hard_compact"
    MIXED = "mixed"

class IrrigationType(str, Enum):
    CANAL = "canal"
    BOREWELL = "borewell"
    DRIP = "drip"
    RAINFED = "rainfed"
    SPRINKLER = "sprinkler"

class AreaUnit(str, Enum):
    ACRE = "acre"
    HECTARE = "hectare"
    BIGHA = "bigha"

# Set 1: Soil Physical Properties
class SoilPhysicalProperties(BaseModel):
    soil_texture: SoilTexture
    water_retention: WaterRetention
    soil_top_layer: SoilTopLayer

# Set 2: Soil Fertility & Nutrients
class SoilFertilityNutrients(BaseModel):
    soil_test_done: bool
    npk_nitrogen: Optional[float] = None
    npk_phosphorus: Optional[float] = None
    npk_potassium: Optional[float] = None
    yellowing_slow_growth: bool
    fertilizer_type: str  # "organic", "chemical", "both", "none"

# Set 3: Moisture & Irrigation
class MoistureIrrigation(BaseModel):
    irrigation_type: IrrigationType
    watering_frequency: str  # "daily", "weekly", "bi_weekly", "monthly", "rainfed"

# Set 4: Environmental & Regional
class EnvironmentalRegional(BaseModel):
    state: str
    district: str
    average_rainfall: Optional[float] = None  # mm per year
    average_temperature: Optional[float] = None  # celsius
    total_area: float
    area_unit: AreaUnit

# Set 5: Organic Matter & Practices
class OrganicMatterPractices(BaseModel):
    uses_organic_matter: bool
    organic_matter_types: Optional[list[str]] = []  # ["compost", "green_manure", "animal_dung"]
    crop_residue_practice: str  # "leave_in_field", "burn", "remove", "compost"
    earthworms_present: bool

class QuestionnaireSubmission(BaseModel):
    user_id: int
    set_number: int
    answers: Dict[str, Any]

class CompleteQuestionnaire(BaseModel):
    user_id: int
    soil_physical: SoilPhysicalProperties
    soil_fertility: SoilFertilityNutrients
    moisture_irrigation: MoistureIrrigation
    environmental: EnvironmentalRegional
    organic_practices: OrganicMatterPractices
