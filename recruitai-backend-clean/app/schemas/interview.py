"""
Interview schemas for request/response validation
"""

from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any
from datetime import datetime

class InterviewBase(BaseModel):
    title: str
    description: Optional[str] = None
    duration_minutes: int = 30
    
    @validator('duration_minutes')
    def validate_duration(cls, v):
        if v < 5 or v > 120:
            raise ValueError('Duration must be between 5 and 120 minutes')
        return v

class InterviewCreate(InterviewBase):
    candidate_id: int
    job_id: int
    scheduled_at: Optional[datetime] = None

class InterviewUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[str] = None
    
    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            allowed_statuses = ['scheduled', 'in_progress', 'completed', 'cancelled']
            if v not in allowed_statuses:
                raise ValueError(f'Status must be one of: {", ".join(allowed_statuses)}')
        return v

class InterviewResponse(InterviewBase):
    id: int
    interview_token: str
    status: str
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    questions: Optional[List[Dict[str, Any]]] = None
    responses: Optional[List[Dict[str, Any]]] = None
    overall_score: Optional[float] = None
    communication_score: Optional[float] = None
    technical_score: Optional[float] = None
    problem_solving_score: Optional[float] = None
    ai_analysis: Optional[Dict[str, Any]] = None
    emotion_analysis: Optional[Dict[str, Any]] = None
    speech_analysis: Optional[Dict[str, Any]] = None
    ai_recommendation: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_feedback: Optional[str] = None
    video_url: Optional[str] = None
    audio_url: Optional[str] = None
    transcript: Optional[str] = None
    recording_enabled: bool
    ai_analysis_enabled: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    candidate_id: int
    job_id: int
    interviewer_id: int
    
    class Config:
        from_attributes = True

class InterviewListResponse(BaseModel):
    id: int
    interview_token: str
    title: str
    status: str
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    overall_score: Optional[float] = None
    ai_recommendation: Optional[str] = None
    candidate_id: int
    candidate_name: Optional[str] = None
    job_id: int
    job_title: Optional[str] = None
    
    class Config:
        from_attributes = True

class InterviewStats(BaseModel):
    total_interviews: int
    scheduled_interviews: int
    completed_interviews: int
    in_progress_interviews: int
    cancelled_interviews: int
    average_score: Optional[float] = None

class InterviewQuestion(BaseModel):
    id: int
    question: str
    type: str  # text, video, coding
    expected_duration: int  # seconds
    skills_assessed: List[str]

class InterviewResponse(BaseModel):
    question_id: int
    response_text: Optional[str] = None
    response_video_url: Optional[str] = None
    response_audio_url: Optional[str] = None
    duration: int  # seconds
    timestamp: datetime

class InterviewAnalysis(BaseModel):
    interview_id: int
    overall_score: float
    communication_score: float
    technical_score: float
    problem_solving_score: float
    detailed_analysis: Dict[str, Any]
    recommendation: str
    confidence: float
    feedback: str
    
    class Config:
        from_attributes = True

class InterviewStartRequest(BaseModel):
    interview_token: str

class InterviewSubmitResponse(BaseModel):
    question_id: int
    response_text: Optional[str] = None
    response_duration: Optional[int] = None

class InterviewCompleteRequest(BaseModel):
    interview_token: str
    responses: List[InterviewSubmitResponse]

