from datetime import date, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.farm_context import DataQualityAssessment


class CandidateSource(str, Enum):
    XGBOOST = "xgboost"
    KNOWLEDGE_BASE = "knowledge_base"


class ValidationStatus(str, Enum):
    PENDING = "pending"
    ELIGIBLE = "eligible"
    REJECTED = "rejected"
    INSUFFICIENT_DATA = "insufficient_data"


class ModelPredictionStatus(str, Enum):
    SUCCESS = "success"
    LOW_CONFIDENCE = "low_confidence"
    OUT_OF_DISTRIBUTION = "out_of_distribution"
    MODEL_UNAVAILABLE = "model_unavailable"
    INVALID_INPUT = "invalid_input"
    INSUFFICIENT_COMPATIBLE_INPUT = "insufficient_compatible_input"
    PRELIMINARY_ESTIMATED_INPUT = "preliminary_estimated_input"
    PRELIMINARY_MISSING_INPUT = "preliminary_missing_input"


class RecommendationStatus(str, Enum):
    SUCCESS = "success"
    PRELIMINARY = "preliminary"
    NO_RELIABLE_RECOMMENDATION = "no_reliable_recommendation"


class CandidateRecommendationStatus(str, Enum):
    RECOMMENDED = "recommended"
    PRELIMINARY = "preliminary"
    INSUFFICIENT_SUPPORT = "insufficient_support"
    REJECTED = "rejected"


class SuitabilityBand(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT_DATA = "insufficient_data"


class ValidationCoverageStatus(str, Enum):
    VERIFIED_MATCH = "verified_match"
    VERIFIED_MISMATCH = "verified_mismatch"
    NOT_AVAILABLE = "not_available"


class ValidationCoverage(BaseModel):
    season: ValidationCoverageStatus = ValidationCoverageStatus.NOT_AVAILABLE
    sowing_month: ValidationCoverageStatus = ValidationCoverageStatus.NOT_AVAILABLE
    region: ValidationCoverageStatus = ValidationCoverageStatus.NOT_AVAILABLE
    soil: ValidationCoverageStatus = ValidationCoverageStatus.NOT_AVAILABLE
    ph: ValidationCoverageStatus = ValidationCoverageStatus.NOT_AVAILABLE
    temperature: ValidationCoverageStatus = ValidationCoverageStatus.NOT_AVAILABLE
    rainfall: ValidationCoverageStatus = ValidationCoverageStatus.NOT_AVAILABLE
    water: ValidationCoverageStatus = ValidationCoverageStatus.NOT_AVAILABLE


class ValidationCoverageSummary(BaseModel):
    verified_checks: int = 0
    unavailable_checks: int = 8
    failed_checks: int = 0


class SourceReference(BaseModel):
    name: str
    url: Optional[str] = None


class ValidationWarning(BaseModel):
    code: str
    message: str


class CandidateValidation(BaseModel):
    status: ValidationStatus
    hard_failures: list[ValidationWarning] = Field(default_factory=list)
    warnings: list[ValidationWarning] = Field(default_factory=list)
    matched_conditions: list[str] = Field(default_factory=list)
    validation_coverage: ValidationCoverage = Field(default_factory=ValidationCoverage)
    validation_coverage_summary: ValidationCoverageSummary = Field(
        default_factory=ValidationCoverageSummary
    )
    dimension_scores: dict[str, float] = Field(default_factory=dict, exclude=True)


class CropCandidate(BaseModel):
    crop_slug: str
    crop_name: str
    candidate_sources: list[CandidateSource]
    model_probability: Optional[float] = None
    model_rank: Optional[int] = None
    knowledge_score: Optional[float] = None
    validation_status: ValidationStatus = ValidationStatus.PENDING
    rejection_reasons: list[str] = Field(default_factory=list)
    warnings: list[ValidationWarning] = Field(default_factory=list)
    matched_conditions: list[str] = Field(default_factory=list)
    source_references: list[SourceReference] = Field(default_factory=list)


class CropModelResult(BaseModel):
    status: ModelPredictionStatus
    candidates: list[CropCandidate] = Field(default_factory=list)
    model_version: str = "unknown"
    model_supported_crop_count: int = 0
    model_classes: list[str] = Field(default_factory=list)
    feature_columns: list[str] = Field(default_factory=list)
    feature_values: dict[str, Optional[float]] = Field(default_factory=dict)
    warnings: list[ValidationWarning] = Field(default_factory=list)


class CropExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    crop_slug: str
    summary: str
    why_recommended: list[str] = Field(default_factory=list)
    main_risks: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    soil_advice: list[str] = Field(default_factory=list)
    irrigation_advice: list[str] = Field(default_factory=list)
    pest_prevention: list[str] = Field(default_factory=list)


class LLMExplanationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    crop_explanations: list[CropExplanation]
    general_advice: list[str] = Field(default_factory=list)
    disclaimer: str


class CropRecommendation(BaseModel):
    crop_slug: Optional[str] = None
    crop_name: str
    rank: Optional[int] = None
    candidate_sources: list[CandidateSource] = Field(default_factory=list)
    model_probability: Optional[float] = None
    model_rank: Optional[int] = None
    knowledge_score: Optional[float] = None
    overall_suitability_score: Optional[int] = None
    suitability_band: SuitabilityBand = SuitabilityBand.INSUFFICIENT_DATA
    recommendation_status: CandidateRecommendationStatus = (
        CandidateRecommendationStatus.INSUFFICIENT_SUPPORT
    )
    matched_conditions: list[str] = Field(default_factory=list)
    validation_coverage: ValidationCoverage = Field(default_factory=ValidationCoverage)
    validation_coverage_summary: ValidationCoverageSummary = Field(
        default_factory=ValidationCoverageSummary
    )
    crop_specific_warnings: list[ValidationWarning] = Field(default_factory=list)
    # Legacy snapshots used `warnings`. New responses keep global limitations out
    # of this field and use `crop_specific_warnings` instead.
    warnings: list[ValidationWarning] = Field(default_factory=list)
    source_references: list[SourceReference] = Field(default_factory=list)
    explanation: Optional[CropExplanation] = None

    # Legacy fields remain nullable so old snapshots are readable. New results
    # never manufacture agronomic or economic values.
    variety: Optional[str] = None
    sowing_season: Optional[str] = None
    expected_yield: Optional[str] = None
    market_price_range: Optional[str] = None
    profitability_score: Optional[float] = None
    economic_potential_score: Optional[float] = None


class CalendarEvent(BaseModel):
    date: date
    activity: str
    description: str
    priority: str
    category: str


class RecommendationCoverage(BaseModel):
    model_supported_crop_count: int
    knowledge_base_crop_count: int
    limitation: str


class MissingInput(BaseModel):
    field: str
    importance: str
    reason: str
    action_route: str
    questionnaire_section: str


class ExplanationFailureCode(str, Enum):
    LLM_DISABLED = "LLM_DISABLED"
    LLM_API_KEY_MISSING = "LLM_API_KEY_MISSING"
    LLM_REQUEST_FAILED = "LLM_REQUEST_FAILED"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_RATE_LIMITED = "LLM_RATE_LIMITED"
    LLM_INVALID_JSON = "LLM_INVALID_JSON"
    LLM_SCHEMA_VALIDATION_FAILED = "LLM_SCHEMA_VALIDATION_FAILED"
    LLM_UNAUTHORIZED_CROP = "LLM_UNAUTHORIZED_CROP"
    LLM_DUPLICATE_CROP = "LLM_DUPLICATE_CROP"
    LLM_MISSING_CROP = "LLM_MISSING_CROP"
    LLM_UNSUPPORTED_NUMERIC_CLAIM = "LLM_UNSUPPORTED_NUMERIC_CLAIM"
    LLM_INTERNAL_ERROR = "LLM_INTERNAL_ERROR"


class AIRecommendationResponse(BaseModel):
    user_id: int
    farm_id: Optional[int] = None
    status: RecommendationStatus = RecommendationStatus.SUCCESS
    coverage: Optional[RecommendationCoverage] = None
    data_quality: Optional[DataQualityAssessment] = None
    generation_mode: str = "unknown"
    model_version: str = "unknown"
    crop_catalog_version: str = "unknown"
    prompt_version: str = "unknown"
    ranking_rule_version: str = "unknown"
    weather_source: str = "unknown"
    model_status: str = "unknown"
    explanation_status: str = "unknown"
    internal_llm_reason_codes: list[str] = Field(default_factory=list, exclude=True)
    is_stale: bool = False
    message: Optional[str] = None
    required_actions: list[str] = Field(default_factory=list)
    missing_inputs: list[MissingInput] = Field(default_factory=list)
    global_warnings: list[ValidationWarning] = Field(default_factory=list)
    recommended_crops: list[CropRecommendation] = Field(default_factory=list)
    preliminary_crops: list[CropRecommendation] = Field(default_factory=list)
    general_advice: list[str] = Field(default_factory=list)
    disclaimer: Optional[str] = None

    # Backward-compatible advisory fields.
    soil_health_score: Optional[float] = None
    farming_calendar: list[CalendarEvent] = Field(default_factory=list)
    soil_improvement_tips: list[str] = Field(default_factory=list)
    irrigation_recommendations: list[str] = Field(default_factory=list)
    fertilizer_recommendations: list[str] = Field(default_factory=list)
    pest_disease_prevention: list[str] = Field(default_factory=list)
    generated_at: datetime
    next_review_date: Optional[date] = None
    input_snapshot: dict[str, Any] = Field(default_factory=dict)
