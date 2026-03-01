from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.questionnaire import QuestionnaireSubmission, CompleteQuestionnaire
from app.models.user import UserResponse
from app.database.connection import get_db
from app.database.schemas import User, QuestionnaireResponse
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
    
    # Save or update questionnaire response
    existing_response = db.query(QuestionnaireResponse).filter(
        QuestionnaireResponse.user_id == submission.user_id,
        QuestionnaireResponse.set_number == submission.set_number
    ).first()
    
    if existing_response:
        existing_response.answers = submission.answers
    else:
        new_response = QuestionnaireResponse(
            user_id=submission.user_id,
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
    
    # Save all questionnaire data
    questionnaire_data = {
        1: questionnaire.soil_physical.dict(),
        2: questionnaire.soil_fertility.dict(),
        3: questionnaire.moisture_irrigation.dict(),
        4: questionnaire.environmental.dict(),
        5: questionnaire.organic_practices.dict()
    }
    
    # Save each set
    for set_num, answers in questionnaire_data.items():
        existing_response = db.query(QuestionnaireResponse).filter(
            QuestionnaireResponse.user_id == questionnaire.user_id,
            QuestionnaireResponse.set_number == set_num
        ).first()
        
        if existing_response:
            existing_response.answers = answers
        else:
            new_response = QuestionnaireResponse(
                user_id=questionnaire.user_id,
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    responses = db.query(QuestionnaireResponse).filter(
        QuestionnaireResponse.user_id == current_user.id
    ).all()
    
    formatted_responses = {}
    for response in responses:
        formatted_responses[f"set_{response.set_number}"] = response.answers
    
    return formatted_responses
