from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    is_new_user = Column(Boolean, default=True)
    onboarding_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    questionnaire_responses = relationship('QuestionnaireResponse', back_populates='user')
    recommendations = relationship('Recommendation', back_populates='user')

class QuestionnaireResponse(Base):
    __tablename__ = 'questionnaire_responses'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    set_number = Column(Integer, nullable=False)
    answers = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship('User', back_populates='questionnaire_responses')

class Recommendation(Base):
    __tablename__ = 'recommendations'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    soil_health_score = Column(Float, nullable=True)
    recommended_crops = Column(JSON, nullable=True)
    farming_calendar = Column(JSON, nullable=True)
    soil_improvement_tips = Column(JSON, nullable=True)
    irrigation_recommendations = Column(JSON, nullable=True)
    fertilizer_recommendations = Column(JSON, nullable=True)
    pest_disease_prevention = Column(JSON, nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow)
    next_review_date = Column(String, nullable=True)  # Changed to String to avoid DateTime issues

    # Relationships
    user = relationship('User', back_populates='recommendations')
