from dataclasses import dataclass, field
import os

from app.models.farm_context import DataQualityAssessment, DataQualityLevel, FarmContext
from app.models.recommendation import (
    CandidateSource,
    CandidateRecommendationStatus,
    CropCandidate,
    ModelPredictionStatus,
    SuitabilityBand,
    ValidationCoverage,
    ValidationCoverageSummary,
    ValidationStatus,
)
from app.services.crop_catalog_service import canonical_crop_slug
from app.services.crop_validation_service import crop_validation_service


@dataclass(frozen=True)
class RankingConfiguration:
    version: str = "crop-ranking-v2"
    # Product heuristics, not scientifically validated weights.
    weights: dict[str, float] = field(
        default_factory=lambda: {
            "agronomic_model_signal": 0.45,
            "season": 0.10,
            "region": 0.10,
            "soil": 0.10,
            "water": 0.10,
            "climate": 0.10,
            "farmer_preferences": 0.05,
        }
    )
    data_quality_factors: dict[str, float] = field(
        default_factory=lambda: {"high": 1.0, "medium": 0.85, "low": 0.70}
    )
    warning_penalty: float = 0.025
    max_warning_penalty: float = 0.20
    out_of_distribution_factor: float = 0.80
    # Provisional product-safety thresholds; these are not agronomically
    # validated and must be reviewed against expert and field outcomes.
    minimum_recommendation_score: int = int(os.getenv("MIN_RECOMMENDATION_SCORE", "50"))
    minimum_preliminary_score: int = int(os.getenv("MIN_PRELIMINARY_SCORE", "25"))
    minimum_verified_checks_for_recommendation: int = int(
        os.getenv("MIN_VERIFIED_CHECKS_FOR_RECOMMENDATION", "4")
    )


RANKING_CONFIG = RankingConfiguration()


class RankedCandidate(CropCandidate):
    overall_suitability_score: int
    suitability_band: SuitabilityBand
    recommendation_status: CandidateRecommendationStatus
    validation_coverage: ValidationCoverage
    validation_coverage_summary: ValidationCoverageSummary


class CropRankingService:
    def merge_candidates(self, lanes: list[list[CropCandidate]]) -> list[CropCandidate]:
        merged: dict[str, CropCandidate] = {}
        for lane in lanes:
            for item in lane:
                slug = canonical_crop_slug(item.crop_slug or item.crop_name)
                if slug not in merged:
                    merged[slug] = item.model_copy(update={"crop_slug": slug})
                    continue
                current = merged[slug]
                sources = list(dict.fromkeys([*current.candidate_sources, *item.candidate_sources]))
                references = {
                    (ref.name, ref.url): ref for ref in [*current.source_references, *item.source_references]
                }
                merged[slug] = current.model_copy(
                    update={
                        "candidate_sources": sources,
                        "model_probability": current.model_probability if current.model_probability is not None else item.model_probability,
                        "model_rank": current.model_rank if current.model_rank is not None else item.model_rank,
                        "knowledge_score": current.knowledge_score if current.knowledge_score is not None else item.knowledge_score,
                        "matched_conditions": list(dict.fromkeys([*current.matched_conditions, *item.matched_conditions])),
                        "warnings": [*current.warnings, *item.warnings],
                        "source_references": list(references.values()),
                    }
                )
        return list(merged.values())

    def rank(
        self,
        model_candidates: list[CropCandidate],
        knowledge_candidates: list[CropCandidate],
        context: FarmContext,
        data_quality: DataQualityAssessment,
        model_status: ModelPredictionStatus,
        limit: int = 3,
    ) -> list[RankedCandidate]:
        ranked = []
        for candidate in self.merge_candidates([model_candidates, knowledge_candidates]):
            validation = crop_validation_service.validate(candidate, context, model_status)
            if validation.status != ValidationStatus.ELIGIBLE:
                continue
            signal_values = [
                value
                for value in (candidate.model_probability, candidate.knowledge_score)
                if value is not None
            ]
            if not signal_values:
                continue
            component_scores = {"agronomic_model_signal": sum(signal_values) / len(signal_values)}
            component_scores.update(validation.dimension_scores)
            applicable_weight = sum(RANKING_CONFIG.weights[name] for name in component_scores)
            weighted = sum(
                RANKING_CONFIG.weights[name] * value for name, value in component_scores.items()
            ) / applicable_weight
            quality_factor = RANKING_CONFIG.data_quality_factors[data_quality.level.value]
            warning_penalty = min(
                len(validation.warnings) * RANKING_CONFIG.warning_penalty,
                RANKING_CONFIG.max_warning_penalty,
            )
            overall = weighted * quality_factor * (1.0 - warning_penalty)
            if model_status == ModelPredictionStatus.OUT_OF_DISTRIBUTION and CandidateSource.XGBOOST in candidate.candidate_sources:
                overall *= RANKING_CONFIG.out_of_distribution_factor
            score = max(0, min(100, round(overall * 100)))
            if score <= 0 or score < RANKING_CONFIG.minimum_preliminary_score:
                continue
            can_be_recommended = (
                score >= RANKING_CONFIG.minimum_recommendation_score
                and data_quality.level != DataQualityLevel.LOW
                and model_status
                not in {
                    ModelPredictionStatus.LOW_CONFIDENCE,
                    ModelPredictionStatus.OUT_OF_DISTRIBUTION,
                    ModelPredictionStatus.PRELIMINARY_ESTIMATED_INPUT,
                    ModelPredictionStatus.PRELIMINARY_MISSING_INPUT,
                }
                and validation.validation_coverage_summary.verified_checks
                >= RANKING_CONFIG.minimum_verified_checks_for_recommendation
            )
            recommendation_status = (
                CandidateRecommendationStatus.RECOMMENDED
                if can_be_recommended
                else CandidateRecommendationStatus.PRELIMINARY
            )
            band = (
                SuitabilityBand.HIGH
                if score >= 75
                else SuitabilityBand.MEDIUM
                if score >= 50
                else SuitabilityBand.LOW
            )
            ranked.append(
                RankedCandidate(
                    **candidate.model_dump(exclude={"warnings", "matched_conditions", "validation_status"}),
                    validation_status=ValidationStatus.ELIGIBLE,
                    warnings=validation.warnings,
                    matched_conditions=validation.matched_conditions,
                    overall_suitability_score=score,
                    suitability_band=band,
                    recommendation_status=recommendation_status,
                    validation_coverage=validation.validation_coverage,
                    validation_coverage_summary=validation.validation_coverage_summary,
                )
            )
        ranked.sort(
            key=lambda item: (
                -item.overall_suitability_score,
                item.model_rank if item.model_rank is not None else 10_000,
                item.crop_slug,
            )
        )
        return ranked[: max(0, limit)]


crop_ranking_service = CropRankingService()
