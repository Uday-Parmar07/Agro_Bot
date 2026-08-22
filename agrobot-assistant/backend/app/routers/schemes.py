from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.schemas import SchemeRecord, User
from app.models.finance import SchemeRecordCreate, SchemeRecordResponse, SchemeRecordUpdate
from app.services.farm_service import get_user_farm
from app.utils.auth_utils import get_current_user

router = APIRouter()


@router.post("/{scheme_id}/save", response_model=SchemeRecordResponse)
async def save_scheme_record(
    scheme_id: str,
    payload: SchemeRecordCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    farm = get_user_farm(db, current_user, payload.farm_id)
    record = SchemeRecord(
        farm_id=farm.id,
        scheme_name=payload.scheme_name,
        source_url=payload.source_url,
        summary=payload.summary,
        eligibility_text=payload.eligibility_text,
        estimated_benefit=payload.estimated_benefit,
        notes=payload.notes or f"Saved from scheme result {scheme_id}",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/records", response_model=list[SchemeRecordResponse])
async def list_scheme_records(
    farm_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    farm = get_user_farm(db, current_user, farm_id)
    db.commit()
    return (
        db.query(SchemeRecord)
        .filter(SchemeRecord.farm_id == farm.id)
        .order_by(SchemeRecord.created_at.desc())
        .all()
    )


@router.patch("/records/{record_id}", response_model=SchemeRecordResponse)
async def update_scheme_record(
    record_id: int,
    payload: SchemeRecordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = (
        db.query(SchemeRecord)
        .filter(SchemeRecord.id == record_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheme record not found")
    get_user_farm(db, current_user, record.farm_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return record
