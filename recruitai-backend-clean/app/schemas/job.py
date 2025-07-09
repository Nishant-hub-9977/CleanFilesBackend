"""
Job schemas for request/response validation
"""

from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any
from datetime import datetime

class JobBase(BaseModel):
    title: str
    description: str
    company: str
    location: Optional[str] = None
    job_type: str  # full-time, part-time, contract, internship
    experience_level: str  # entry, mid, senior, executive
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: str = "USD"
    required_skills: Optional[List[str]] = []
    preferred_skills: Optional[List[str]] = []
    education_requirements: Optional[str] = None
    experience_requirements: Optional[str] = None
    application_deadline: Optional[datetime] = None
    
    @validator('job_type')
    def validate_job_type(cls, v):
        allowed_types = ['full-time', 'part-time', 'contract', 'internship']
        if v not in allowed_types:
            raise ValueError(f'Job type must be one of: {", ".join(allowed_types)}')
        return v
    
    @validator('experience_level')
    def validate_experience_level(cls, v):
        allowed_levels = ['entry', 'mid', 'senior', 'executive']
        if v not in allowed_levels:
            raise ValueError(f'Experience level must be one of: {", ".join(allowed_levels)}')
        return v
    
    @validator('salary_max')
    def validate_salary_range(cls, v, values):
        if v is not None and 'salary_min' in values and values['salary_min'] is not None:
            if v < values['salary_min']:
                raise ValueError('Maximum salary must be greater than minimum salary')
        return v

class JobCreate(JobBase):
    pass

class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: Optional[str] = None
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    education_requirements: Optional[str] = None
    experience_requirements: Optional[str] = None
    application_deadline: Optional[datetime] = None
    is_active: Optional[bool] = None
    is_published: Optional[bool] = None

class JobResponse(JobBase):
    id: int
    is_active: bool
    is_published: bool
    ai_generated_questions: Optional[List[Dict[str, Any]]] = None
    job_summary: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    owner_id: int
    
    # Statistics
    total_candidates: Optional[int] = 0
    qualified_candidates: Optional[int] = 0
    interviews_completed: Optional[int] = 0
    
    class Config:
        from_attributes = True

class JobListResponse(BaseModel):
    id: int
    title: str
    company: str
    location: Optional[str] = None
    job_type: str
    experience_level: str
    is_active: bool
    is_published: bool
    created_at: datetime
    total_candidates: Optional[int] = 0
    qualified_candidates: Optional[int] = 0
    
    class Config:
        from_attributes = True

class JobStats(BaseModel):
    total_jobs: int
    active_jobs: int
    published_jobs: int
    total_applications: int
    qualified_applications: int

class JobSearchFilters(BaseModel):
    search: Optional[str] = None
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    location: Optional[str] = None
    company: Optional[str] = None
    is_active: Optional[bool] = None
    is_published: Optional[bool] = None

