from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.questionnaire import QuestionnaireSubmission, CompleteQuestionnaire
from app.models.user import UserResponse
from app.database.connection import get_db
from app.database.schemas import User, QuestionnaireResponse
from app.services.farm_service import get_existing_user_farm, get_user_farm
from app.utils.auth_utils import get_current_user
from typing import Dict, Any

router = APIRouter()

@router.post("/submit-set")
async def submit_questionnaire_set(
    submission: QuestionnaireSubmission,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify user owns this submission
    if submission.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to submit for this user"
        )
    
    farm = get_user_farm(db, current_user, submission.farm_id)

    # Save or update questionnaire response
    existing_response = db.query(QuestionnaireResponse).filter(
        QuestionnaireResponse.user_id == submission.user_id,
        QuestionnaireResponse.farm_id == farm.id,
        QuestionnaireResponse.set_number == submission.set_number
    ).first()
    
    if existing_response:
        existing_response.answers = submission.answers
    else:
        new_response = QuestionnaireResponse(
            user_id=submission.user_id,
            farm_id=farm.id,
            set_number=submission.set_number,
            answers=submission.answers
        )
        db.add(new_response)
    
    db.commit()
    
    return {"message": f"Set {submission.set_number} answers saved successfully"}

@router.post("/complete")
async def complete_questionnaire(
    questionnaire: CompleteQuestionnaire,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify user owns this questionnaire
    if questionnaire.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    
    farm = get_user_farm(db, current_user, questionnaire.farm_id)

    # Save all questionnaire data
    questionnaire_data = {
        1: questionnaire.soil_physical.model_dump(mode="json"),
        2: questionnaire.soil_fertility.model_dump(mode="json"),
        3: questionnaire.moisture_irrigation.model_dump(mode="json"),
        4: questionnaire.environmental.model_dump(mode="json"),
        5: questionnaire.organic_practices.model_dump(mode="json")
    }
    
    # Save each set
    for set_num, answers in questionnaire_data.items():
        existing_response = db.query(QuestionnaireResponse).filter(
            QuestionnaireResponse.user_id == questionnaire.user_id,
            QuestionnaireResponse.farm_id == farm.id,
            QuestionnaireResponse.set_number == set_num
        ).first()
        
        if existing_response:
            existing_response.answers = answers
        else:
            new_response = QuestionnaireResponse(
                user_id=questionnaire.user_id,
                farm_id=farm.id,
                set_number=set_num,
                answers=answers
            )
            db.add(new_response)
    
    # Mark user onboarding as completed
    current_user.onboarding_completed = True
    current_user.is_new_user = False
    
    db.commit()
    
    return {"message": "Questionnaire completed successfully", "onboarding_completed": True}

@router.get("/user-responses")
async def get_user_questionnaire_responses(
    farm_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    farm = get_existing_user_farm(db, current_user, farm_id)

    responses = db.query(QuestionnaireResponse).filter(
        QuestionnaireResponse.user_id == current_user.id,
        QuestionnaireResponse.farm_id == farm.id
    ).all()
    
    formatted_responses = {}
    for response in responses:
        formatted_responses[f"set_{response.set_number}"] = response.answers
    
    return formatted_responses
