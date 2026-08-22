from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.schemas import User
from app.models.user import LanguageUpdate, UserResponse
from app.utils.auth_utils import get_current_user

router = APIRouter()


@router.patch("/me/language", response_model=UserResponse)
async def update_preferred_language(
    payload: LanguageUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.preferred_language not in {"en", "hi"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="preferred_language must be 'en' or 'hi'",
        )

    current_user.preferred_language = payload.preferred_language
    db.commit()
    db.refresh(current_user)
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_new_user=current_user.is_new_user,
        created_at=current_user.created_at,
        onboarding_completed=current_user.onboarding_completed,
        preferred_language=current_user.preferred_language,
        role=current_user.role,
    )
