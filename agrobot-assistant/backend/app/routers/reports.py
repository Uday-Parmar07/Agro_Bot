from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.schemas import ForumPost, ForumReply, MarketplaceListing, Report, User
from app.models.community import ReportCreate, ReportResponse
from app.utils.auth_utils import get_current_user, require_role

router = APIRouter()


@router.post("", response_model=ReportResponse)
async def create_report(
    payload: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = Report(reported_by=current_user.id, **payload.model_dump())
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.post("/admin/hide")
async def hide_content(
    target_type: str,
    target_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    model = {
        "listing": MarketplaceListing,
        "post": ForumPost,
        "reply": ForumReply,
    }.get(target_type)
    if not model:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported target type")

    item = db.query(model).filter(model.id == target_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")

    item.hidden = True
    db.commit()
    return {"message": "Content hidden"}
