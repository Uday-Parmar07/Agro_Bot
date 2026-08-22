from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DiseasePredictionResponse(BaseModel):
    filename: str
    predicted_class: str
    confidence: float
    detailed_classification: str
    possible_cause: str
    treatment: str
    llm_enhanced: bool


class DiseasePredictionHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    farm_id: int
    image_path: Optional[str] = None
    predicted_class: str
    confidence: float
    treatment_text: Optional[str] = None
    source: str
    created_at: datetime
