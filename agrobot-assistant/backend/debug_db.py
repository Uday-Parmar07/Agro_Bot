from app.database.connection import SessionLocal
from app.database.schemas import User, QuestionnaireResponse, Recommendation

def check_database():
    db = SessionLocal()
    
    # Check users
    users = db.query(User).all()
    print(f"Users in database: {len(users)}")
    for user in users:
        print(f"  User {user.id}: {user.email}, onboarding_completed: {user.onboarding_completed}")
    
    # Check questionnaire responses
    responses = db.query(QuestionnaireResponse).all()
    print(f"\nQuestionnaire responses: {len(responses)}")
    for response in responses:
        print(f"  User {response.user_id}, Set {response.set_number}: {response.answers}")
    
    # Check recommendations
    recommendations = db.query(Recommendation).all()
    print(f"\nRecommendations: {len(recommendations)}")
    for rec in recommendations:
        print(f"  User {rec.user_id}: Soil health {rec.soil_health_score}, {len(rec.recommended_crops)} crops")
    
    db.close()

if __name__ == "__main__":
    check_database()
