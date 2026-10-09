from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from app.database.schemas import User
from app.services.ai_service import ai_service
from app.utils.auth_utils import get_current_user
from app.utils.rate_limit import limiter, user_or_ip
from app.utils.uploads import read_upload_limited

router = APIRouter()

# Groq's Whisper endpoint rejects files above 25 MB.
MAX_AUDIO_BYTES = 25 * 1024 * 1024


@router.post("/transcribe")
@limiter.limit("20/minute;200/hour", key_func=user_or_ip)
async def transcribe_voice(
    request: Request,
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    if not audio.content_type or not audio.content_type.startswith("audio/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload a valid audio file",
        )

    content = await read_upload_limited(audio, MAX_AUDIO_BYTES)
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
