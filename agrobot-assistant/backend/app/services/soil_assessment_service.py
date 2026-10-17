"""Versioned questionnaire screening index, independent of crop/LLM availability.

The six indicators have equal weight. All must be explicitly answered; missing
answers never become favourable defaults. NPK values and texture-based estimates
are excluded: crop-specific nutrient targets and lab methods are not recorded.
See docs/SOIL_ASSESSMENT.md for the rubric and its limitations.
"""

from sqlalchemy.orm import Session

from app.database.schemas import QuestionnaireResponse
from app.models.soil_assessment import SoilAssessment


# (questionnaire set, field, answer -> screening points out of ten)
INDICATORS = (
    ("set_1", "soil_top_layer", {"dark_crumbly": 10.0, "mixed": 5.0, "hard_compact": 0.0}),
    ("set_1", "water_retention", {"moderate": 10.0, "retains_long": 5.0, "drains_quickly": 5.0}),
    ("set_2", "yellowing_slow_growth", {False: 10.0, True: 0.0}),
    ("set_5", "uses_organic_matter", {True: 10.0, False: 0.0}),
    ("set_5", "crop_residue_practice", {"leave_in_field": 10.0, "compost": 10.0, "remove": 5.0, "burn": 0.0}),
    ("set_5", "earthworms_present", {True: 10.0, False: 0.0}),
)


def assess_soil(user_data: dict) -> SoilAssessment:
    components, missing = {}, []
    for set_name, field, rubric in INDICATORS:
        answers = user_data.get(set_name)
        value = answers.get(field) if isinstance(answers, dict) else None
        # Strict typing matters for legacy/unvalidated submit-set payloads:
        # False is an answer, but 0, "false", null and containers are not.
        valid = type(value) is type(next(iter(rubric)))
        if not valid or value not in rubric:
            missing.append(field)
        else:
            components[field] = rubric[value]
    return SoilAssessment(
        score=round(sum(components.values()) / len(INDICATORS), 1) if not missing else None,
        status="insufficient_data" if missing else "estimated",
        components=components,
        missing_fields=missing,
    )


def get_soil_assessment(db: Session, farm_id: int) -> SoilAssessment:
    responses = db.query(QuestionnaireResponse).filter(QuestionnaireResponse.farm_id == farm_id).all()
    return assess_soil({f"set_{row.set_number}": row.answers for row in responses})
