from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, JSON, Date, UniqueConstraint
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
    preferred_language = Column(String, nullable=False, default='en')
    role = Column(String, nullable=False, default='farmer')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    farms = relationship('Farm', back_populates='user')
    questionnaire_responses = relationship('QuestionnaireResponse', back_populates='user')
    recommendations = relationship('Recommendation', back_populates='user')
    marketplace_listings = relationship('MarketplaceListing', back_populates='farmer')
    forum_posts = relationship('ForumPost', back_populates='user')
    forum_replies = relationship('ForumReply', back_populates='user')

class Farm(Base):
    __tablename__ = 'farms'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    name = Column(String, nullable=False, default='Default Farm')
    location = Column(String, nullable=True)
    area_acres = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship('User', back_populates='farms')
    questionnaire_responses = relationship('QuestionnaireResponse', back_populates='farm')
    recommendations = relationship('Recommendation', back_populates='farm')
    disease_predictions = relationship('DiseasePrediction', back_populates='farm')
    weather_snapshots = relationship('WeatherSnapshot', back_populates='farm')
    crops = relationship('FarmCrop', back_populates='farm')

class QuestionnaireResponse(Base):
    __tablename__ = 'questionnaire_responses'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    farm_id = Column(Integer, ForeignKey('farms.id'), nullable=True, index=True)
    set_number = Column(Integer, nullable=False)
    answers = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship('User', back_populates='questionnaire_responses')
    farm = relationship('Farm', back_populates='questionnaire_responses')

class Recommendation(Base):
    __tablename__ = 'recommendations'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    farm_id = Column(Integer, ForeignKey('farms.id'), nullable=True, index=True)
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
    farm = relationship('Farm', back_populates='recommendations')

class DiseasePrediction(Base):
    __tablename__ = 'disease_predictions'

    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey('farms.id'), nullable=False, index=True)
    image_path = Column(String, nullable=True)
    predicted_class = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    treatment_text = Column(String, nullable=True)
    source = Column(String, nullable=False, default='cnn')
    created_at = Column(DateTime, default=datetime.utcnow)

    farm = relationship('Farm', back_populates='disease_predictions')

class WeatherSnapshot(Base):
    __tablename__ = 'weather_snapshots'
    __table_args__ = (
        UniqueConstraint('farm_id', 'date', name='uq_weather_snapshots_farm_date'),
    )

    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey('farms.id'), nullable=False, index=True)
    date = Column(Date, nullable=False)
    source = Column(String, nullable=False)
    temp = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    rainfall_mm = Column(Float, nullable=True)
    raw_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    farm = relationship('Farm', back_populates='weather_snapshots')

class FarmCrop(Base):
    __tablename__ = 'farm_crops'

    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey('farms.id'), nullable=False, index=True)
    crop_name = Column(String, nullable=False)
    variety = Column(String, nullable=True)
    area_acres = Column(Float, nullable=True)
    planting_date = Column(Date, nullable=True)
    expected_harvest_date = Column(Date, nullable=True)
    added_by = Column(String, nullable=False, default='user')
    status = Column(String, nullable=False, default='active')
    added_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    farm = relationship('Farm', back_populates='crops')
    harvest_outcomes = relationship('HarvestOutcome', back_populates='farm_crop')

class AdvisorFarmerLink(Base):
    __tablename__ = 'advisor_farmer_links'

    id = Column(Integer, primary_key=True, index=True)
    advisor_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    farmer_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)

class SchemeRecord(Base):
    __tablename__ = 'scheme_records'

    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey('farms.id'), nullable=False, index=True)
    scheme_name = Column(String, nullable=False)
    source_url = Column(String, nullable=True)
    summary = Column(String, nullable=True)
    eligibility_text = Column(String, nullable=True)
    estimated_benefit = Column(String, nullable=True)
    status = Column(String, nullable=False, default='saved')
    applied_at = Column(DateTime, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class HarvestOutcome(Base):
    __tablename__ = 'harvest_outcomes'

    id = Column(Integer, primary_key=True, index=True)
    farm_crop_id = Column(Integer, ForeignKey('farm_crops.id'), nullable=False, index=True)
    actual_yield = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    sale_price_per_unit = Column(Float, nullable=False)
    harvested_at = Column(Date, nullable=False)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    farm_crop = relationship('FarmCrop', back_populates='harvest_outcomes')

class MarketplaceListing(Base):
    __tablename__ = 'marketplace_listings'

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    crop_name = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    location = Column(String, nullable=True)
    contact_pref = Column(String, nullable=True)
    status = Column(String, nullable=False, default='active')
    hidden = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    farmer = relationship('User', back_populates='marketplace_listings')

class ForumPost(Base):
    __tablename__ = 'forum_posts'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    region = Column(String, nullable=False, index=True)
    crop_tag = Column(String, nullable=True)
    title = Column(String, nullable=False)
    body = Column(String, nullable=False)
    hidden = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='forum_posts')
    replies = relationship('ForumReply', back_populates='post')

class ForumReply(Base):
    __tablename__ = 'forum_replies'

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey('forum_posts.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    body = Column(String, nullable=False)
    hidden = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    post = relationship('ForumPost', back_populates='replies')
    user = relationship('User', back_populates='forum_replies')

class Report(Base):
    __tablename__ = 'reports'

    id = Column(Integer, primary_key=True, index=True)
    target_type = Column(String, nullable=False)
    target_id = Column(Integer, nullable=False)
    reported_by = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    reason = Column(String, nullable=False)
    status = Column(String, nullable=False, default='open')
    created_at = Column(DateTime, default=datetime.utcnow)
