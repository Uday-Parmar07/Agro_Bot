import io

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.schemas import DiseasePrediction, User
from app.models.disease import DiseasePredictionHistoryItem, DiseasePredictionResponse
from app.services.disease_inference_service import disease_inference_service
from app.services.farm_service import get_user_farm
from app.utils.auth_utils import get_current_user
from app.utils.rate_limit import limiter, user_or_ip
from app.utils.uploads import read_upload_limited

router = APIRouter()

MAX_IMAGE_BYTES = 10 * 1024 * 1024
# Phone cameras top out well below this; it stops decompression bombs that
# would otherwise expand into gigabytes during decode.
MAX_IMAGE_PIXELS = 50_000_000


def _validate_image(image_bytes: bytes) -> None:
    invalid = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Please upload a valid image file",
    )
    try:
        # Image.open only parses the header, so the size check runs before any pixels are decoded.
        with Image.open(io.BytesIO(image_bytes)) as img:
            if img.width * img.height > MAX_IMAGE_PIXELS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Image resolution is too large",
                )
            # A full decode, matching what inference does; verify() also
            # rejects slightly malformed files that decode fine.
            img.load()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError) as exc:
        raise invalid from exc


@router.post("/predict", response_model=DiseasePredictionResponse)
@limiter.limit("10/minute;60/hour", key_func=user_or_ip)
async def predict_disease(
    request: Request,
    farm_id: int | None = None,
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload a valid image file",
        )

    image_bytes = await read_upload_limited(image, MAX_IMAGE_BYTES)
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image is empty",
        )
    _validate_image(image_bytes)

    try:
        farm = get_user_farm(db, current_user, farm_id)
        db.commit()

        result = disease_inference_service.predict(
            image_bytes,
            image.content_type,
            language=current_user.preferred_language,
        )
        prediction = DiseasePrediction(
            farm_id=farm.id,
            image_path=image.filename or "uploaded_image",
            predicted_class=result["predicted_class"],
            confidence=result["confidence"],
            treatment_text=result["treatment"],
            source="cnn+groq_vision" if result["llm_enhanced"] else "cnn",
        )
        db.add(prediction)
        db.commit()

        return DiseasePredictionResponse(
            filename=image.filename or "uploaded_image",
            predicted_class=result["predicted_class"],
            confidence=result["confidence"],
            detailed_classification=result["detailed_classification"],
            possible_cause=result["possible_cause"],
            treatment=result["treatment"],
            llm_enhanced=result["llm_enhanced"],
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Model artifacts not found. Train the CNN first and ensure checkpoint exists. {exc}"
            ),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Disease prediction failed: {exc}",
        ) from exc


@router.get("/history", response_model=list[DiseasePredictionHistoryItem])
async def get_disease_history(
    farm_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    farm = get_user_farm(db, current_user, farm_id)
    db.commit()

    return (
        db.query(DiseasePrediction)
        .filter(DiseasePrediction.farm_id == farm.id)
        .order_by(DiseasePrediction.created_at.desc())
        .limit(50)
        .all()
    )
