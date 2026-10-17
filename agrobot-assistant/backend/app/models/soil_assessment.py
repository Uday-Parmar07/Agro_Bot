from typing import Literal

from pydantic import BaseModel, Field


class SoilAssessment(BaseModel):
    score: float | None = Field(default=None, ge=0, le=10)
    status: Literal["estimated", "insufficient_data"] = "insufficient_data"
    method_version: str = "soil-observations-v1"
    explanation: str = (
        "Estimated from soil structure, drainage, crop symptoms, organic inputs, "
        "residue management and earthworm observations. This is a questionnaire "
        "screening score, not a laboratory soil-health measurement."
    )
    components: dict[str, float] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
