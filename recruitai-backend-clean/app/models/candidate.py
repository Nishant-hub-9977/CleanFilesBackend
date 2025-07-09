"""
Candidate model for candidate management and job applications
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..core.database import Base

class Candidate(Base):
    __tablename__ = "candidates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    
    # Application details
    application_status = Column(String(50), default="applied")  # applied, screening, interview, hired, rejected
    application_date = Column(DateTime(timezone=True), server_default=func.now())
    
    # Resume matching
    match_score = Column(Float, nullable=True)  # 0.0 to 1.0
    match_details = Column(JSON, nullable=True)  # Detailed matching analysis
    is_qualified = Column(Boolean, default=False)  # Based on match threshold
    
    # AI assessment
    ai_assessment = Column(JSON, nullable=True)  # Overall AI assessment
    skill_scores = Column(JSON, nullable=True)  # Individual skill scores
    
    # Interview status
    interview_scheduled = Column(Boolean, default=False)
    interview_completed = Column(Boolean, default=False)
    interview_link = Column(String(500), nullable=True)
    interview_token = Column(String(100), nullable=True, unique=True)
    
    # Communication
    last_contacted = Column(DateTime(timezone=True), nullable=True)
    contact_history = Column(JSON, nullable=True)  # Communication log
    
    # Notes and feedback
    recruiter_notes = Column(Text, nullable=True)
    feedback = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Foreign keys
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True)
    
    # Relationships
    job = relationship("Job", back_populates="candidates")
    resume = relationship("Resume", back_populates="candidates")
    interviews = relationship("Interview", back_populates="candidate")
    
    def __repr__(self):
        return f"<Candidate(id={self.id}, name='{self.name}', email='{self.email}', job_id={self.job_id})>"

