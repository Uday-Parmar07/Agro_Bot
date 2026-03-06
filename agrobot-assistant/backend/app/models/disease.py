from pydantic import BaseModel


class DiseasePredictionResponse(BaseModel):
    filename: str
    predicted_class: str
    confidence: float
    detailed_classification: str
    possible_cause: str
    treatment: str
    llm_enhanced: bool
