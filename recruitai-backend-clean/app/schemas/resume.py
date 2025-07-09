"""
Resume schemas for request/response validation
"""

from pydantic import BaseModel, EmailStr, validator
from typing import List, Optional, Dict, Any
from datetime import datetime

class ResumeBase(BaseModel):
    filename: str
    original_filename: str
    file_size: int
    file_type: str

class ResumeUploadResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    processing_status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ResumeResponse(ResumeBase):
    id: int
    file_path: str
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    candidate_phone: Optional[str] = None
    extracted_text: Optional[str] = None
    skills: Optional[List[str]] = None
    experience: Optional[List[Dict[str, Any]]] = None
    education: Optional[List[Dict[str, Any]]] = None
    certifications: Optional[List[str]] = None
    ai_summary: Optional[str] = None
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    is_processed: bool
    processing_status: str
    processing_error: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    uploaded_by: int
    
    class Config:
        from_attributes = True

class ResumeListResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    file_size: int
    file_type: str
    is_processed: bool
    processing_status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ResumeAnalysisRequest(BaseModel):
    resume_id: int
    job_id: int

class ResumeMatchResult(BaseModel):
    resume_id: int
    job_id: int
    match_score: float
    is_qualified: bool
    match_details: Dict[str, Any]
    
    class Config:
        from_attributes = True

class ResumeProcessingStatus(BaseModel):
    id: int
    processing_status: str
    is_processed: bool
    processing_error: Optional[str] = None
    processed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class ResumeStats(BaseModel):
    total_resumes: int
    processed_resumes: int
    pending_resumes: int
    failed_resumes: int

class BulkResumeUploadResponse(BaseModel):
    successful_uploads: List[ResumeUploadResponse]
    failed_uploads: List[Dict[str, str]]
    total_uploaded: int
    total_failed: int

