"""
Resume model for resume storage and analysis
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..core.database import Base

class Resume(Base):
    __tablename__ = "resumes"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(50), nullable=False)  # pdf, doc, docx
    
    # Extracted information
    candidate_name = Column(String(100), nullable=True)
    candidate_email = Column(String(100), nullable=True)
    candidate_phone = Column(String(20), nullable=True)
    
    # AI-extracted content
    extracted_text = Column(Text, nullable=True)
    skills = Column(JSON, nullable=True)  # List of extracted skills
    experience = Column(JSON, nullable=True)  # Work experience details
    education = Column(JSON, nullable=True)  # Education details
    certifications = Column(JSON, nullable=True)  # Certifications
    
    # AI analysis
    ai_summary = Column(Text, nullable=True)
    strengths = Column(JSON, nullable=True)  # List of strengths
    weaknesses = Column(JSON, nullable=True)  # List of areas for improvement
    
    # Processing status
    is_processed = Column(Boolean, default=False)
    processing_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    processing_error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Foreign keys
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    uploader = relationship("User")
    candidates = relationship("Candidate", back_populates="resume")
    
    def __repr__(self):
        return f"<Resume(id={self.id}, filename='{self.filename}', candidate='{self.candidate_name}')>"

