import json
import logging
import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from app.models.farm_context import DataSource, FarmContext, RainfallCompatibility, RainfallPeriod
from app.models.recommendation import CandidateSource, CropCandidate, SourceReference


logger = logging.getLogger(__name__)
CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "crop_catalog.v1.json"


def canonical_crop_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").strip().lower())


class CropProfile(BaseModel):
    crop_slug: str
    display_name: str
    is_active: bool = True
    is_model_supported: bool = False
    knowledge_profile_complete: bool = False
    allowed_seasons: list[str] = Field(default_factory=list)
    sowing_months: list[int] = Field(default_factory=list)
    supported_states: Optional[list[str]] = None
    supported_districts: Optional[list[str]] = None
    supported_soil_types: list[str] = Field(default_factory=list)
    min_ph: Optional[float] = None
    max_ph: Optional[float] = None
    min_temperature_c: Optional[float] = None
    max_temperature_c: Optional[float] = None
    min_rainfall_mm: Optional[float] = None
    max_rainfall_mm: Optional[float] = None
    rainfall_period: Optional[RainfallPeriod] = None
    water_requirement: Optional[str] = None
    minimum_irrigation_level: Optional[str] = None
    typical_duration_days_min: Optional[int] = None
    typical_duration_days_max: Optional[int] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    source_last_verified_at: Optional[str] = None
    profile_version: str

    def has_verified_constraints(self) -> bool:
        return any(
            (
                self.allowed_seasons,
                self.sowing_months,
                self.supported_states,
                self.supported_districts,
                self.supported_soil_types,
                self.min_ph is not None,
                self.max_ph is not None,
                self.min_temperature_c is not None,
                self.max_temperature_c is not None,
                self.rainfall_period is not None
                and (self.min_rainfall_mm is not None or self.max_rainfall_mm is not None),
                self.water_requirement,
                self.minimum_irrigation_level,
            )
        )


class CropCatalogService:
    def __init__(self, catalog_path: Path = CATALOG_PATH):
        self.catalog_path = catalog_path
        self.catalog_version = "unknown"
        self._profiles: dict[str, CropProfile] = {}
        self.reload()

    def reload(self) -> None:
        payload = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        defaults = payload.get("profile_defaults", {})
        profiles: dict[str, CropProfile] = {}
        for raw in payload.get("profiles", []):
            merged = {**defaults, **raw}
            merged["crop_slug"] = canonical_crop_slug(merged["crop_slug"])
            profile = CropProfile(**merged)
            if profile.crop_slug in profiles:
                raise ValueError(f"Duplicate crop catalogue slug: {profile.crop_slug}")
            profiles[profile.crop_slug] = profile
        self.catalog_version = payload["catalog_version"]
        self._profiles = profiles

    def get_crop_profile(self, crop_slug: str) -> Optional[CropProfile]:
        return self._profiles.get(canonical_crop_slug(crop_slug))

    def get_active_profiles(self) -> list[CropProfile]:
        return [profile for profile in self._profiles.values() if profile.is_active]

    def get_model_supported_crops(self) -> list[CropProfile]:
        return [
            profile
            for profile in self.get_active_profiles()
            if profile.is_model_supported
        ]

    def get_knowledge_profiles(self) -> list[CropProfile]:
        return [
            profile
            for profile in self.get_active_profiles()
            if profile.knowledge_profile_complete
            and profile.source_name
            and profile.has_verified_constraints()
        ]

    def validate_catalog_consistency(self, model_classes: list[str]) -> list[str]:
        model_slugs = {canonical_crop_slug(name) for name in model_classes}
        catalog_slugs = {profile.crop_slug for profile in self.get_model_supported_crops()}
        messages = []
        missing = sorted(model_slugs - catalog_slugs)
        stale = sorted(catalog_slugs - model_slugs)
        if missing:
            messages.append(f"Model classes missing from crop catalogue: {', '.join(missing)}")
        if stale:
            messages.append(f"Catalogue crops marked model-supported but absent from model: {', '.join(stale)}")
        for message in messages:
            logger.error(message)
        return messages

    def find_knowledge_candidates(self, context: FarmContext) -> list[CropCandidate]:
        candidates = []
        for profile in self.get_knowledge_profiles():
            matched = []
            applicable = 0
            compatible = 0

            def compare(available: bool, matches: bool, label: str) -> None:
                nonlocal applicable, compatible
                if not available:
                    return
                applicable += 1
                if matches:
                    compatible += 1
                    matched.append(label)

            season = (context.season or "").lower()
            compare(
                bool(season and season != "not_sure" and profile.allowed_seasons),
                season in {item.lower() for item in profile.allowed_seasons},
                "Season compatible",
            )
            compare(
                bool(context.intended_sowing_month and profile.sowing_months),
                context.intended_sowing_month in profile.sowing_months,
                "Sowing month compatible",
            )
            compare(
                bool(context.soil_type and profile.supported_soil_types),
                context.soil_type.lower() in {item.lower() for item in profile.supported_soil_types},
                "Soil type compatible",
            )
            compare(
                bool(context.state and profile.supported_states),
                context.state.lower() in {item.lower() for item in profile.supported_states or []},
                "State coverage compatible",
            )
            compare(
                bool(context.district and profile.supported_districts),
                context.district.lower() in {item.lower() for item in profile.supported_districts or []},
                "District coverage compatible",
            )
            compare(
                bool(
                    context.ph is not None
                    and context.ph_source == DataSource.LABORATORY_TEST
                    and (profile.min_ph is not None or profile.max_ph is not None)
                ),
                (profile.min_ph is None or context.ph >= profile.min_ph)
                and (profile.max_ph is None or context.ph <= profile.max_ph),
                "pH range compatible",
            )
            compare(
                bool(
                    context.temperature is not None
                    and context.temperature_source
                    in {
                        DataSource.WEATHER_API,
                        DataSource.CACHED_WEATHER_API,
                        DataSource.HISTORICAL_CLIMATE,
                    }
                    and (profile.min_temperature_c is not None or profile.max_temperature_c is not None)
                ),
                (profile.min_temperature_c is None or context.temperature >= profile.min_temperature_c)
                and (profile.max_temperature_c is None or context.temperature <= profile.max_temperature_c),
                "Temperature range compatible",
            )
            compare(
                bool(
                    context.rainfall_value is not None
                    and (profile.min_rainfall_mm is not None or profile.max_rainfall_mm is not None)
                    and profile.rainfall_period is not None
                    and context.rainfall_period == profile.rainfall_period
                    and context.rainfall_compatibility == RainfallCompatibility.COMPATIBLE
                ),
                (profile.min_rainfall_mm is None or context.rainfall_value >= profile.min_rainfall_mm)
                and (profile.max_rainfall_mm is None or context.rainfall_value <= profile.max_rainfall_mm),
                "Rainfall range compatible",
            )
            water_required = (profile.minimum_irrigation_level or profile.water_requirement or "").lower()
            water_available = (context.water_availability or "").lower()
            compare(
                bool(water_required and water_available),
                not (
                    water_required in {"high", "assured", "abundant"}
                    and water_available in {"none", "limited", "low", "rainfed"}
                ),
                "Water availability compatible",
            )
            if applicable == 0:
                continue

            knowledge_score = compatible / applicable
            references = [SourceReference(name=profile.source_name, url=profile.source_url)]
            candidates.append(
                CropCandidate(
                    crop_slug=profile.crop_slug,
                    crop_name=profile.display_name,
                    candidate_sources=[CandidateSource.KNOWLEDGE_BASE],
                    knowledge_score=round(knowledge_score, 4),
                    matched_conditions=matched,
                    source_references=references,
                )
            )
        return candidates


crop_catalog_service = CropCatalogService()
