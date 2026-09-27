from app.models.farm_context import DataSource, FarmContext, RainfallCompatibility
from app.models.recommendation import (
    CandidateSource,
    CandidateValidation,
    CropCandidate,
    ModelPredictionStatus,
    ValidationCoverage,
    ValidationCoverageStatus,
    ValidationCoverageSummary,
    ValidationStatus,
    ValidationWarning,
)
from app.services.crop_catalog_service import crop_catalog_service


MATCH = ValidationCoverageStatus.VERIFIED_MATCH
MISMATCH = ValidationCoverageStatus.VERIFIED_MISMATCH
NOT_AVAILABLE = ValidationCoverageStatus.NOT_AVAILABLE
RELIABLE_CLIMATE_SOURCES = {
    DataSource.WEATHER_API,
    DataSource.CACHED_WEATHER_API,
    DataSource.HISTORICAL_CLIMATE,
}


class CropValidationService:
    def validate(
        self,
        candidate: CropCandidate,
        context: FarmContext,
        model_status: ModelPredictionStatus,
    ) -> CandidateValidation:
        hard_failures: list[ValidationWarning] = []
        crop_warnings = list(candidate.warnings)
        matched = list(candidate.matched_conditions)
        scores: dict[str, float] = {}
        coverage = ValidationCoverage()
        profile = crop_catalog_service.get_crop_profile(candidate.crop_slug)

        if not candidate.candidate_sources:
            hard_failures.append(self._issue("NO_ALLOWED_SOURCE", "Crop is not from an allowed candidate source."))
        if CandidateSource.XGBOOST not in candidate.candidate_sources and candidate.model_probability is not None:
            hard_failures.append(
                self._issue("UNSUPPORTED_MODEL_PROBABILITY", "A non-model candidate cannot have a model probability.")
            )
        if CandidateSource.XGBOOST in candidate.candidate_sources and candidate.model_probability is None:
            hard_failures.append(
                self._issue("MISSING_MODEL_PROBABILITY", "A model-backed candidate is missing its raw model probability.")
            )
        if profile is None:
            hard_failures.append(self._issue("MISSING_CROP_PROFILE", "Crop has no central catalogue profile."))
            return self._result(hard_failures, crop_warnings, matched, scores, coverage)
        if not profile.is_active:
            hard_failures.append(self._issue("INACTIVE_CROP", "Crop profile is inactive."))
        if CandidateSource.XGBOOST in candidate.candidate_sources and not profile.is_model_supported:
            hard_failures.append(self._issue("MODEL_COVERAGE_MISMATCH", "Crop is not marked as model-supported."))
        if (
            CandidateSource.KNOWLEDGE_BASE in candidate.candidate_sources
            and CandidateSource.XGBOOST not in candidate.candidate_sources
            and (
                not profile.knowledge_profile_complete
                or not profile.source_name
                or not profile.has_verified_constraints()
            )
        ):
            hard_failures.append(
                self._issue(
                    "INCOMPLETE_KNOWLEDGE_PROFILE",
                    "Knowledge-only crop lacks a complete, sourced agronomic profile.",
                )
            )

        coverage.season = self._validate_season(profile, context, hard_failures, matched, scores)
        coverage.sowing_month = self._validate_sowing_month(profile, context, hard_failures, matched)
        coverage.region = self._validate_region(profile, context, hard_failures, matched, scores)
        coverage.soil = self._validate_soil_type(profile, context, hard_failures, matched, scores)
        coverage.ph = self._validate_ph(profile, context, hard_failures, crop_warnings, matched, scores)
        coverage.temperature = self._validate_temperature(
            profile, context, hard_failures, crop_warnings, matched, scores
        )
        coverage.rainfall = self._validate_rainfall(
            profile, context, hard_failures, crop_warnings, matched, scores
        )
        coverage.water = self._validate_water(
            profile, context, hard_failures, crop_warnings, matched, scores
        )

        return self._result(
            hard_failures,
            self._dedupe(crop_warnings),
            matched,
            scores,
            coverage,
        )

    def _validate_season(self, profile, context, failures, matched, scores):
        if not profile.allowed_seasons or not context.season:
            return NOT_AVAILABLE
        compatible = context.season.lower() in {item.lower() for item in profile.allowed_seasons}
        scores["season"] = 1.0 if compatible else 0.0
        if compatible:
            matched.append("Season compatibility verified")
            return MATCH
        failures.append(self._issue("SEASON_INCOMPATIBLE", "Selected season is explicitly incompatible."))
        return MISMATCH

    def _validate_sowing_month(self, profile, context, failures, matched):
        if not profile.sowing_months or not context.intended_sowing_month:
            return NOT_AVAILABLE
        if context.intended_sowing_month in profile.sowing_months:
            matched.append("Sowing month compatibility verified")
            return MATCH
        failures.append(self._issue("SOWING_MONTH_INCOMPATIBLE", "Intended sowing month is explicitly unsupported."))
        return MISMATCH

    def _validate_region(self, profile, context, failures, matched, scores):
        checks = []
        if profile.supported_states:
            if not context.state:
                return NOT_AVAILABLE
            checks.append(context.state.lower() in {item.lower() for item in profile.supported_states})
        if profile.supported_districts:
            if not context.district:
                return NOT_AVAILABLE
            checks.append(context.district.lower() in {item.lower() for item in profile.supported_districts})
        if not checks:
            return NOT_AVAILABLE
        compatible = all(checks)
        scores["region"] = 1.0 if compatible else 0.0
        if compatible:
            matched.append("Regional compatibility verified")
            return MATCH
        failures.append(self._issue("REGION_INCOMPATIBLE", "Farm location is outside verified profile coverage."))
        return MISMATCH

    def _validate_soil_type(self, profile, context, failures, matched, scores):
        if not profile.supported_soil_types or not context.soil_type:
            return NOT_AVAILABLE
        compatible = context.soil_type.lower() in {item.lower() for item in profile.supported_soil_types}
        scores["soil"] = 1.0 if compatible else 0.0
        if compatible:
            matched.append("Soil type compatibility verified")
            return MATCH
        failures.append(self._issue("SOIL_INCOMPATIBLE", "Soil type is explicitly unsupported."))
        return MISMATCH

    def _validate_ph(self, profile, context, failures, warnings, matched, scores):
        if context.ph is None or (profile.min_ph is None and profile.max_ph is None):
            return NOT_AVAILABLE
        compatible = self._in_range(context.ph, profile.min_ph, profile.max_ph)
        if context.ph_source != DataSource.LABORATORY_TEST:
            if not compatible:
                warnings.append(
                    self._issue(
                        "ESTIMATED_PH_OUTSIDE_RANGE",
                        "Estimated soil pH may be outside this crop's verified range.",
                    )
                )
            return NOT_AVAILABLE
        scores["soil"] = min(scores.get("soil", 1.0), 1.0 if compatible else 0.0)
        if compatible:
            matched.append("Soil pH compatibility verified")
            return MATCH
        failures.append(self._issue("PH_INCOMPATIBLE", "Measured pH is outside the verified crop range."))
        return MISMATCH

    def _validate_temperature(self, profile, context, failures, warnings, matched, scores):
        if (
            context.temperature is None
            or (profile.min_temperature_c is None and profile.max_temperature_c is None)
        ):
            return NOT_AVAILABLE
        compatible = self._in_range(
            context.temperature, profile.min_temperature_c, profile.max_temperature_c
        )
        if context.temperature_source not in RELIABLE_CLIMATE_SOURCES:
            if not compatible:
                warnings.append(
                    self._issue(
                        "UNCERTAIN_TEMPERATURE_MISMATCH",
                        "Available temperature information may be outside this crop's verified range.",
                    )
                )
            return NOT_AVAILABLE
        scores["climate"] = 1.0 if compatible else 0.0
        if compatible:
            matched.append("Temperature compatibility verified")
            return MATCH
        failures.append(
            self._issue("TEMPERATURE_INCOMPATIBLE", "Reliable temperature data is outside the verified crop range.")
        )
        return MISMATCH

    def _validate_rainfall(self, profile, context, failures, warnings, matched, scores):
        if (
            context.rainfall_value is None
            or (profile.min_rainfall_mm is None and profile.max_rainfall_mm is None)
            or profile.rainfall_period is None
            or context.rainfall_period != profile.rainfall_period
            or context.rainfall_compatibility != RainfallCompatibility.COMPATIBLE
        ):
            return NOT_AVAILABLE
        compatible = self._in_range(
            context.rainfall_value, profile.min_rainfall_mm, profile.max_rainfall_mm
        )
        if compatible:
            scores["climate"] = min(scores.get("climate", 1.0), 1.0)
            matched.append("Rainfall compatibility verified")
            return MATCH
        if context.rainfall_source == DataSource.HISTORICAL_CLIMATE:
            scores["climate"] = 0.0
            failures.append(
                self._issue("RAINFALL_INCOMPATIBLE", "Comparable rainfall data is outside the verified crop range.")
            )
            return MISMATCH
        warnings.append(
            self._issue(
                "UNCERTAIN_RAINFALL_MISMATCH",
                "Comparable rainfall information may be outside this crop's verified range.",
            )
        )
        return NOT_AVAILABLE

    def _validate_water(self, profile, context, failures, warnings, matched, scores):
        if not profile.minimum_irrigation_level and not profile.water_requirement:
            return NOT_AVAILABLE
        availability = (context.water_availability or "").lower()
        if not availability:
            warnings.append(
                self._issue("WATER_AVAILABILITY_UNKNOWN", "Water availability could not be checked for this crop.")
            )
            return NOT_AVAILABLE
        required = (profile.minimum_irrigation_level or profile.water_requirement or "").lower()
        insufficient = required in {"high", "assured", "abundant"} and availability in {
            "none",
            "limited",
            "low",
            "rainfed",
        }
        scores["water"] = 0.0 if insufficient else 1.0
        if insufficient:
            failures.append(
                self._issue("INSUFFICIENT_WATER", "Known water availability is below the verified crop requirement.")
            )
            return MISMATCH
        matched.append("Water availability compatibility verified")
        return MATCH

    @staticmethod
    def _in_range(value: float, lower: float | None, upper: float | None) -> bool:
        return (lower is None or value >= lower) and (upper is None or value <= upper)

    @staticmethod
    def _issue(code: str, message: str) -> ValidationWarning:
        return ValidationWarning(code=code, message=message)

    @staticmethod
    def _dedupe(items: list[ValidationWarning]) -> list[ValidationWarning]:
        return list({item.code: item for item in items}.values())

    @staticmethod
    def _coverage_summary(coverage: ValidationCoverage) -> ValidationCoverageSummary:
        values = list(coverage.model_dump().values())
        return ValidationCoverageSummary(
            verified_checks=sum(value in {MATCH, MATCH.value} for value in values),
            unavailable_checks=sum(value in {NOT_AVAILABLE, NOT_AVAILABLE.value} for value in values),
            failed_checks=sum(value in {MISMATCH, MISMATCH.value} for value in values),
        )

    def _result(self, failures, warnings, matched, scores, coverage) -> CandidateValidation:
        coverage_summary = self._coverage_summary(coverage)
        if not failures and coverage_summary.verified_checks == 0:
            warnings = self._dedupe(
                [
                    *warnings,
                    self._issue(
                        "NO_VERIFIED_AGRONOMIC_CHECKS",
                        "No crop-specific season, region, soil, climate, or water check could be verified.",
                    ),
                ]
            )
        return CandidateValidation(
            status=ValidationStatus.REJECTED if failures else ValidationStatus.ELIGIBLE,
            hard_failures=failures,
            warnings=warnings,
            matched_conditions=list(dict.fromkeys(matched)),
            validation_coverage=coverage,
            validation_coverage_summary=coverage_summary,
            dimension_scores=scores,
        )


crop_validation_service = CropValidationService()
