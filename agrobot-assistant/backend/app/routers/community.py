from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.schemas import ForumPost, ForumReply, Report, User
from app.models.community import ForumPostCreate, ForumPostResponse, ForumReplyCreate, ForumReplyResponse, ReportCreate, ReportResponse
from app.utils.auth_utils import get_current_user, require_role

router = APIRouter()


@router.post("/posts", response_model=ForumPostResponse)
async def create_post(
    payload: ForumPostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = ForumPost(user_id=current_user.id, **payload.model_dump())
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.get("/posts", response_model=list[ForumPostResponse])
async def list_posts(
    region: str | None = None,
    crop: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ForumPost).filter(ForumPost.hidden == False)  # noqa: E712
    if region:
        query = query.filter(ForumPost.region.ilike(f"%{region}%"))
    if crop:
        query = query.filter(ForumPost.crop_tag.ilike(f"%{crop}%"))
    return query.order_by(ForumPost.created_at.desc()).all()


@router.post("/posts/{post_id}/replies", response_model=ForumReplyResponse)
async def create_reply(
    post_id: int,
    payload: ForumReplyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(ForumPost).filter(ForumPost.id == post_id, ForumPost.hidden == False).first()  # noqa: E712
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    reply = ForumReply(post_id=post_id, user_id=current_user.id, body=payload.body)
    db.add(reply)
    db.commit()
    db.refresh(reply)
    return reply


@router.post("/reports", response_model=ReportResponse)
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
async def hide_reported_content(
    target_type: str,
    target_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    model = {"post": ForumPost, "reply": ForumReply}.get(target_type)
    if not model:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported target type")
    item = db.query(model).filter(model.id == target_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    item.hidden = True
    db.commit()
    return {"message": "Content hidden"}
