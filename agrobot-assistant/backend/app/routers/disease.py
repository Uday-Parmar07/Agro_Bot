from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.schemas import DiseasePrediction, User
from app.models.disease import DiseasePredictionHistoryItem, DiseasePredictionResponse
from app.services.disease_inference_service import disease_inference_service
from app.services.farm_service import get_user_farm
from app.utils.auth_utils import get_current_user

router = APIRouter()


@router.post("/predict", response_model=DiseasePredictionResponse)
async def predict_disease(
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

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image is empty",
        )

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
