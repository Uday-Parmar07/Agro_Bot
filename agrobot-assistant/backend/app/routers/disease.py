from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.database.schemas import User
from app.models.disease import DiseasePredictionResponse
from app.services.disease_inference_service import disease_inference_service
from app.utils.auth_utils import get_current_user

router = APIRouter()


@router.post("/predict", response_model=DiseasePredictionResponse)
async def predict_disease(
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
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
        result = disease_inference_service.predict(image_bytes, image.content_type)
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Disease prediction failed: {exc}",
        ) from exc
