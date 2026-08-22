from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.database.schemas import User
from app.services.ai_service import ai_service
from app.utils.auth_utils import get_current_user

router = APIRouter()


@router.post("/transcribe")
async def transcribe_voice(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    if not audio.content_type or not audio.content_type.startswith("audio/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload a valid audio file",
        )

    content = await audio.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio is empty",
        )

    transcript = await ai_service.transcribe_audio(
        filename=audio.filename or "voice.webm",
        content=content,
        content_type=audio.content_type,
    )
    return {
        "transcript": transcript,
        "language": current_user.preferred_language,
    }
