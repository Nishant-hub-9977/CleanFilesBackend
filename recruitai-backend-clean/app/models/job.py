"""
Job model for job postings and requirements
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..core.database import Base

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=False)
    company = Column(String(100), nullable=False)
    location = Column(String(100), nullable=True)
    job_type = Column(String(50), nullable=False)  # full-time, part-time, contract, internship
    experience_level = Column(String(50), nullable=False)  # entry, mid, senior, executive
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    currency = Column(String(10), default="USD")
    
    # Requirements and skills
    required_skills = Column(JSON, nullable=True)  # List of required skills
    preferred_skills = Column(JSON, nullable=True)  # List of preferred skills
    education_requirements = Column(Text, nullable=True)
    experience_requirements = Column(Text, nullable=True)
    
    # Job status
    is_active = Column(Boolean, default=True)
    is_published = Column(Boolean, default=False)
    application_deadline = Column(DateTime(timezone=True), nullable=True)
    
    # AI-generated content
    ai_generated_questions = Column(JSON, nullable=True)  # Interview questions
    job_summary = Column(Text, nullable=True)  # AI-generated summary
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Foreign keys
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="jobs")
    candidates = relationship("Candidate", back_populates="job")
    interviews = relationship("Interview", back_populates="job")
    
    def __repr__(self):
        return f"<Job(id={self.id}, title='{self.title}', company='{self.company}')>"

