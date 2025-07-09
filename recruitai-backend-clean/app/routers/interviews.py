"""
Interviews router for AI-powered video interviews
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional
import uuid
from datetime import datetime

from ..core.database import get_db
from ..core.security import get_current_active_user, get_admin_user
from ..core.config import settings
from ..models.user import User
from ..models.interview import Interview
from ..models.candidate import Candidate
from ..models.job import Job
from ..schemas.interview import (
    InterviewCreate, InterviewUpdate, InterviewResponse, 
    InterviewListResponse, InterviewStats, InterviewStartRequest,
    InterviewSubmitResponse, InterviewCompleteRequest, InterviewAnalysis
)
from ..services.ai_service import generate_interview_questions_with_ai
from ..services.credit_service import deduct_credits

router = APIRouter()

@router.post("/", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
async def create_interview(
    interview_data: InterviewCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new interview"""
    
    # Check if candidate exists
    candidate = db.query(Candidate).filter(Candidate.id == interview_data.candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    # Check if job exists and user owns it
    job = db.query(Job).filter(Job.id == interview_data.job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if candidate belongs to the job
    if candidate.job_id != job.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Candidate does not belong to this job"
        )
    
    # Check if interview already exists for this candidate
    existing_interview = db.query(Interview).filter(
        Interview.candidate_id == candidate.id
    ).first()
    
    if existing_interview:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview already exists for this candidate"
        )
    
    # Generate unique interview token
    interview_token = str(uuid.uuid4())
    
    # Create interview
    db_interview = Interview(
        interview_token=interview_token,
        title=interview_data.title,
        description=interview_data.description,
        duration_minutes=interview_data.duration_minutes,
        scheduled_at=interview_data.scheduled_at,
        status="scheduled",
        candidate_id=candidate.id,
        job_id=job.id,
        interviewer_id=current_user.id,
        questions=job.ai_generated_questions or [],
        recording_enabled=True,
        ai_analysis_enabled=True
    )
    
    db.add(db_interview)
    db.commit()
    db.refresh(db_interview)
    
    # Update candidate interview status
    candidate.interview_scheduled = True
    candidate.interview_token = interview_token
    candidate.interview_link = f"/interview/{interview_token}"
    db.commit()
    
    return db_interview

@router.get("/", response_model=List[InterviewListResponse])
async def get_interviews(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    job_id: Optional[int] = Query(None),
    candidate_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get interviews with filtering and pagination"""
    
    # Base query - only interviews for jobs owned by current user (unless admin)
    if current_user.role == "admin":
        query = db.query(Interview)
    else:
        query = db.query(Interview).join(Job).filter(Job.owner_id == current_user.id)
    
    # Apply filters
    if status:
        query = query.filter(Interview.status == status)
    
    if job_id:
        query = query.filter(Interview.job_id == job_id)
    
    if candidate_id:
        query = query.filter(Interview.candidate_id == candidate_id)
    
    # Get interviews with related information
    interviews = query.order_by(Interview.created_at.desc()).offset(skip).limit(limit).all()
    
    # Create response with candidate and job information
    interview_responses = []
    for interview in interviews:
        candidate = db.query(Candidate).filter(Candidate.id == interview.candidate_id).first()
        job = db.query(Job).filter(Job.id == interview.job_id).first()
        
        interview_response = InterviewListResponse(
            id=interview.id,
            interview_token=interview.interview_token,
            title=interview.title,
            status=interview.status,
            scheduled_at=interview.scheduled_at,
            completed_at=interview.completed_at,
            overall_score=interview.overall_score,
            ai_recommendation=interview.ai_recommendation,
            candidate_id=interview.candidate_id,
            candidate_name=candidate.name if candidate else None,
            job_id=interview.job_id,
            job_title=job.title if job else None
        )
        interview_responses.append(interview_response)
    
    return interview_responses

@router.get("/stats", response_model=InterviewStats)
async def get_interview_statistics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get interview statistics for current user"""
    
    # Base query for user's interviews
    if current_user.role == "admin":
        base_query = db.query(Interview)
    else:
        base_query = db.query(Interview).join(Job).filter(Job.owner_id == current_user.id)
    
    # Total interviews
    total_interviews = base_query.count()
    
    # Scheduled interviews
    scheduled_interviews = base_query.filter(Interview.status == "scheduled").count()
    
    # Completed interviews
    completed_interviews = base_query.filter(Interview.status == "completed").count()
    
    # In progress interviews
    in_progress_interviews = base_query.filter(Interview.status == "in_progress").count()
    
    # Cancelled interviews
    cancelled_interviews = base_query.filter(Interview.status == "cancelled").count()
    
    # Average score
    avg_score = base_query.filter(
        and_(Interview.status == "completed", Interview.overall_score.isnot(None))
    ).with_entities(func.avg(Interview.overall_score)).scalar()
    
    return InterviewStats(
        total_interviews=total_interviews,
        scheduled_interviews=scheduled_interviews,
        completed_interviews=completed_interviews,
        in_progress_interviews=in_progress_interviews,
        cancelled_interviews=cancelled_interviews,
        average_score=float(avg_score) if avg_score else None
    )

@router.get("/{interview_id}", response_model=InterviewResponse)
async def get_interview(
    interview_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get interview by ID"""
    
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    # Check permissions
    job = db.query(Job).filter(Job.id == interview.job_id).first()
    if job and job.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return interview

@router.get("/token/{interview_token}", response_model=InterviewResponse)
async def get_interview_by_token(
    interview_token: str,
    db: Session = Depends(get_db)
):
    """Get interview by token (public endpoint for candidates)"""
    
    interview = db.query(Interview).filter(Interview.interview_token == interview_token).first()
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    return interview

@router.post("/start")
async def start_interview(
    start_request: InterviewStartRequest,
    db: Session = Depends(get_db)
):
    """Start interview (public endpoint for candidates)"""
    
    interview = db.query(Interview).filter(
        Interview.interview_token == start_request.interview_token
    ).first()
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    if interview.status != "scheduled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview is not in scheduled status"
        )
    
    # Update interview status
    interview.status = "in_progress"
    interview.started_at = datetime.utcnow()
    db.commit()
    
    return {
        "message": "Interview started successfully",
        "interview_id": interview.id,
        "questions": interview.questions,
        "duration_minutes": interview.duration_minutes
    }

@router.post("/complete")
async def complete_interview(
    complete_request: InterviewCompleteRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Complete interview and submit responses (public endpoint for candidates)"""
    
    interview = db.query(Interview).filter(
        Interview.interview_token == complete_request.interview_token
    ).first()
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    if interview.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview is not in progress"
        )
    
    # Check if user has enough credits for AI analysis
    job = db.query(Job).filter(Job.id == interview.job_id).first()
    if job:
        interviewer = db.query(User).filter(User.id == interview.interviewer_id).first()
        if interviewer:
            if not await deduct_credits(
                interviewer.id, 
                settings.CREDIT_COST_PER_INTERVIEW, 
                "interview_analysis", 
                db,
                reference_id=str(interview.id)
            ):
                # Still complete the interview but without AI analysis
                interview.ai_analysis_enabled = False
    
    # Store responses
    interview.responses = [response.dict() for response in complete_request.responses]
    interview.status = "completed"
    interview.completed_at = datetime.utcnow()
    
    # Update candidate status
    candidate = db.query(Candidate).filter(Candidate.id == interview.candidate_id).first()
    if candidate:
        candidate.interview_completed = True
        candidate.application_status = "interview"
    
    db.commit()
    
    # Analyze interview responses in background (if AI analysis is enabled)
    if interview.ai_analysis_enabled:
        background_tasks.add_task(analyze_interview_background, interview.id, db)
    
    return {"message": "Interview completed successfully"}

async def analyze_interview_background(interview_id: int, db: Session):
    """Background task to analyze interview responses"""
    
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        return
    
    try:
        # Analyze responses using AI
        # Simple analysis for now - can be enhanced with AI later
        total_questions = len(interview.questions or [])
        answered_questions = len([q for q in interview.questions if q.get('response')])
        completion_rate = answered_questions / total_questions if total_questions > 0 else 0
        
        analysis_result = {
            "overall_score": min(completion_rate * 100, 85),  # Cap at 85 for basic completion
            "completion_rate": completion_rate,
            "total_questions": total_questions,
            "answered_questions": answered_questions,
            "feedback": "Interview completed successfully" if completion_rate > 0.8 else "Partial completion",
            "provider": "offline"
        }
        
        if analysis_result:
            # Update interview with analysis results
            interview.overall_score = analysis_result.get("overall_score")
            interview.communication_score = analysis_result.get("communication_score")
            interview.technical_score = analysis_result.get("technical_score")
            interview.problem_solving_score = analysis_result.get("problem_solving_score")
            interview.ai_analysis = analysis_result.get("detailed_analysis")
            interview.ai_recommendation = analysis_result.get("recommendation")
            interview.ai_confidence = analysis_result.get("confidence")
            interview.ai_feedback = analysis_result.get("feedback")
            
            # Update candidate with AI assessment
            candidate = db.query(Candidate).filter(Candidate.id == interview.candidate_id).first()
            if candidate:
                candidate.ai_assessment = analysis_result.get("detailed_analysis")
                candidate.skill_scores = {
                    "communication": interview.communication_score,
                    "technical": interview.technical_score,
                    "problem_solving": interview.problem_solving_score
                }
            
            db.commit()
        
    except Exception as e:
        print(f"Error analyzing interview {interview_id}: {e}")

@router.put("/{interview_id}", response_model=InterviewResponse)
async def update_interview(
    interview_id: int,
    interview_update: InterviewUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update interview"""
    
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    # Check permissions
    job = db.query(Job).filter(Job.id == interview.job_id).first()
    if job and job.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Update fields
    update_data = interview_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(interview, field):
            setattr(interview, field, value)
    
    db.commit()
    db.refresh(interview)
    
    return interview

@router.post("/{interview_id}/cancel")
async def cancel_interview(
    interview_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cancel interview"""
    
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    # Check permissions
    job = db.query(Job).filter(Job.id == interview.job_id).first()
    if job and job.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    if interview.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel completed interview"
        )
    
    # Update interview status
    interview.status = "cancelled"
    
    # Update candidate status
    candidate = db.query(Candidate).filter(Candidate.id == interview.candidate_id).first()
    if candidate:
        candidate.interview_scheduled = False
    
    db.commit()
    
    return {"message": "Interview cancelled successfully"}

@router.delete("/{interview_id}")
async def delete_interview(
    interview_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete interview"""
    
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    # Check permissions
    job = db.query(Job).filter(Job.id == interview.job_id).first()
    if job and job.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    if interview.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete completed interview"
        )
    
    # Update candidate status
    candidate = db.query(Candidate).filter(Candidate.id == interview.candidate_id).first()
    if candidate:
        candidate.interview_scheduled = False
        candidate.interview_token = None
        candidate.interview_link = None
    
    db.delete(interview)
    db.commit()
    
    return {"message": "Interview deleted successfully"}

