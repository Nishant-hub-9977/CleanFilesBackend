"""
Interview model for AI-powered video interviews
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..core.database import Base

class Interview(Base):
    __tablename__ = "interviews"
    
    id = Column(Integer, primary_key=True, index=True)
    interview_token = Column(String(100), unique=True, nullable=False, index=True)
    
    # Interview details
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    duration_minutes = Column(Integer, default=30)
    
    # Interview status
    status = Column(String(50), default="scheduled")  # scheduled, in_progress, completed, cancelled
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Questions and responses
    questions = Column(JSON, nullable=True)  # List of interview questions
    responses = Column(JSON, nullable=True)  # Candidate responses
    
    # AI Analysis Results
    overall_score = Column(Float, nullable=True)  # 0.0 to 1.0
    communication_score = Column(Float, nullable=True)  # 0.0 to 1.0
    technical_score = Column(Float, nullable=True)  # 0.0 to 1.0
    problem_solving_score = Column(Float, nullable=True)  # 0.0 to 1.0
    
    # Detailed AI analysis
    ai_analysis = Column(JSON, nullable=True)  # Comprehensive AI analysis
    emotion_analysis = Column(JSON, nullable=True)  # Facial expression analysis
    speech_analysis = Column(JSON, nullable=True)  # Speech pattern analysis
    
    # AI recommendation
    ai_recommendation = Column(String(50), nullable=True)  # hire, consider, reject
    ai_confidence = Column(Float, nullable=True)  # Confidence in recommendation
    ai_feedback = Column(Text, nullable=True)  # Detailed AI feedback
    
    # Video/Audio files
    video_url = Column(String(500), nullable=True)
    audio_url = Column(String(500), nullable=True)
    transcript = Column(Text, nullable=True)
    
    # Interview settings
    recording_enabled = Column(Boolean, default=True)
    ai_analysis_enabled = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Foreign keys
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    interviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    candidate = relationship("Candidate", back_populates="interviews")
    job = relationship("Job", back_populates="interviews")
    interviewer = relationship("User", back_populates="interviews")
    
    def __repr__(self):
        return f"<Interview(id={self.id}, token='{self.interview_token}', status='{self.status}')>"

