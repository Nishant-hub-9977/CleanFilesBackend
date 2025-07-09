"""
Candidate schemas for request/response validation
"""

from pydantic import BaseModel, EmailStr, validator
from typing import List, Optional, Dict, Any
from datetime import datetime

class CandidateBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None

class CandidateCreate(CandidateBase):
    job_id: int
    resume_id: Optional[int] = None

class CandidateUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    application_status: Optional[str] = None
    recruiter_notes: Optional[str] = None
    feedback: Optional[str] = None
    
    @validator('application_status')
    def validate_status(cls, v):
        if v is not None:
            allowed_statuses = ['applied', 'screening', 'interview', 'hired', 'rejected']
            if v not in allowed_statuses:
                raise ValueError(f'Status must be one of: {", ".join(allowed_statuses)}')
        return v

class CandidateResponse(CandidateBase):
    id: int
    application_status: str
    application_date: datetime
    match_score: Optional[float] = None
    match_details: Optional[Dict[str, Any]] = None
    is_qualified: bool
    ai_assessment: Optional[Dict[str, Any]] = None
    skill_scores: Optional[Dict[str, float]] = None
    interview_scheduled: bool
    interview_completed: bool
    interview_link: Optional[str] = None
    interview_token: Optional[str] = None
    last_contacted: Optional[datetime] = None
    contact_history: Optional[List[Dict[str, Any]]] = None
    recruiter_notes: Optional[str] = None
    feedback: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    job_id: int
    resume_id: Optional[int] = None
    
    class Config:
        from_attributes = True

class CandidateListResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    application_status: str
    application_date: datetime
    match_score: Optional[float] = None
    is_qualified: bool
    interview_scheduled: bool
    interview_completed: bool
    job_id: int
    job_title: Optional[str] = None
    
    class Config:
        from_attributes = True

class CandidateStats(BaseModel):
    total_candidates: int
    qualified_candidates: int
    interviewed_candidates: int
    hired_candidates: int
    rejected_candidates: int

class CandidateAssessment(BaseModel):
    candidate_id: int
    overall_score: float
    skill_scores: Dict[str, float]
    strengths: List[str]
    weaknesses: List[str]
    recommendation: str  # hire, consider, reject
    confidence: float
    
    class Config:
        from_attributes = True

class CandidateSearchFilters(BaseModel):
    search: Optional[str] = None
    job_id: Optional[int] = None
    application_status: Optional[str] = None
    is_qualified: Optional[bool] = None
    interview_scheduled: Optional[bool] = None
    interview_completed: Optional[bool] = None
    min_match_score: Optional[float] = None

