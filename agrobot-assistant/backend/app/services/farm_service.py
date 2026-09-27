from sqlalchemy.orm import Session

from app.database.schemas import Farm, QuestionnaireResponse, User


def get_or_create_default_farm(db: Session, user: User) -> Farm:
    farm = (
        db.query(Farm)
        .filter(Farm.user_id == user.id)
        .order_by(Farm.id.asc())
        .first()
    )
    if farm:
        return farm

    location = None
    area_acres = None
    env_response = (
        db.query(QuestionnaireResponse)
        .filter(
            QuestionnaireResponse.user_id == user.id,
            QuestionnaireResponse.set_number == 4,
        )
        .order_by(QuestionnaireResponse.updated_at.desc())
        .first()
    )
    if env_response and env_response.answers:
        answers = env_response.answers
        location = ", ".join(
            part for part in [answers.get("district"), answers.get("state")] if part
        ) or None
        area = answers.get("total_area")
        if area is not None:
            try:
                area_acres = float(area)
                if answers.get("area_unit") == "hectare":
                    area_acres *= 2.47105
            except (TypeError, ValueError):
                area_acres = None

    farm = Farm(
        user_id=user.id,
        name="Default Farm",
        location=location,
        area_acres=area_acres,
    )
    db.add(farm)
    db.flush()
    return farm


def get_user_farm(db: Session, user: User, farm_id: int | None = None) -> Farm:
    if farm_id is None:
        return get_or_create_default_farm(db, user)

    farm = (
        db.query(Farm)
        .filter(Farm.id == farm_id, Farm.user_id == user.id)
        .first()
    )
    if not farm:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found",
        )
    return farm


def get_existing_user_farm(db: Session, user: User, farm_id: int | None = None) -> Farm:
    """Resolve an owned farm without creating or mutating data (safe for GETs)."""
    query = db.query(Farm).filter(Farm.user_id == user.id)
    if farm_id is not None:
        query = query.filter(Farm.id == farm_id)
    farm = query.order_by(Farm.id.asc()).first()
    if not farm:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    return farm
