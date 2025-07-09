"""
Candidates router for candidate management and tracking
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional
import uuid

from ..core.database import get_db
from ..core.security import get_current_active_user, get_admin_user
from ..core.config import settings
from ..models.user import User
from ..models.candidate import Candidate
from ..models.job import Job
from ..models.resume import Resume
from ..models.interview import Interview
from ..schemas.candidate import (
    CandidateCreate, CandidateUpdate, CandidateResponse, 
    CandidateListResponse, CandidateStats, CandidateAssessment
)
from ..services.resume_service import match_resume_to_job
from ..services.credit_service import deduct_credits

router = APIRouter()

@router.post("/", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    candidate_data: CandidateCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new candidate"""
    
    # Check if job exists and user owns it
    job = db.query(Job).filter(Job.id == candidate_data.job_id).first()
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
    
    # Check if resume exists (if provided)
    resume = None
    if candidate_data.resume_id:
        resume = db.query(Resume).filter(Resume.id == candidate_data.resume_id).first()
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )
        
        if resume.uploaded_by != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions for resume"
            )
    
    # Check if candidate already exists for this job
    existing_candidate = db.query(Candidate).filter(
        and_(
            Candidate.email == candidate_data.email,
            Candidate.job_id == candidate_data.job_id
        )
    ).first()
    
    if existing_candidate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Candidate already exists for this job"
        )
    
    # Create candidate
    db_candidate = Candidate(
        name=candidate_data.name,
        email=candidate_data.email,
        phone=candidate_data.phone,
        job_id=candidate_data.job_id,
        resume_id=candidate_data.resume_id,
        application_status="applied",
        is_qualified=False
    )
    
    db.add(db_candidate)
    db.commit()
    db.refresh(db_candidate)
    
    # If resume is provided, calculate match score in background
    if resume and resume.is_processed:
        background_tasks.add_task(calculate_candidate_match, db_candidate.id, db)
    
    return db_candidate

async def calculate_candidate_match(candidate_id: int, db: Session):
    """Background task to calculate candidate match score"""
    
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate or not candidate.resume_id:
        return
    
    resume = db.query(Resume).filter(Resume.id == candidate.resume_id).first()
    job = db.query(Job).filter(Job.id == candidate.job_id).first()
    
    if not resume or not job or not resume.is_processed:
        return
    
    try:
        # Calculate match score
        match_result = await match_resume_to_job(resume, job)
        
        # Update candidate with match results
        candidate.match_score = match_result.get("match_score", 0.0)
        candidate.match_details = match_result.get("match_details", {})
        candidate.is_qualified = match_result.get("is_qualified", False)
        
        # If qualified, generate interview token
        if candidate.is_qualified:
            candidate.interview_token = str(uuid.uuid4())
            candidate.interview_link = f"/interview/{candidate.interview_token}"
        
        db.commit()
        
    except Exception as e:
        print(f"Error calculating match for candidate {candidate_id}: {e}")

@router.get("/", response_model=List[CandidateListResponse])
async def get_candidates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    job_id: Optional[int] = Query(None),
    application_status: Optional[str] = Query(None),
    is_qualified: Optional[bool] = Query(None),
    interview_scheduled: Optional[bool] = Query(None),
    interview_completed: Optional[bool] = Query(None),
    min_match_score: Optional[float] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get candidates with filtering and pagination"""
    
    # Base query - only candidates for jobs owned by current user (unless admin)
    if current_user.role == "admin":
        query = db.query(Candidate)
    else:
        query = db.query(Candidate).join(Job).filter(Job.owner_id == current_user.id)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                Candidate.name.contains(search),
                Candidate.email.contains(search)
            )
        )
    
    if job_id:
        query = query.filter(Candidate.job_id == job_id)
    
    if application_status:
        query = query.filter(Candidate.application_status == application_status)
    
    if is_qualified is not None:
        query = query.filter(Candidate.is_qualified == is_qualified)
    
    if interview_scheduled is not None:
        query = query.filter(Candidate.interview_scheduled == interview_scheduled)
    
    if interview_completed is not None:
        query = query.filter(Candidate.interview_completed == interview_completed)
    
    if min_match_score is not None:
        query = query.filter(Candidate.match_score >= min_match_score)
    
    # Get candidates with job information
    candidates = query.offset(skip).limit(limit).all()
    
    # Create response with job titles
    candidate_responses = []
    for candidate in candidates:
        job = db.query(Job).filter(Job.id == candidate.job_id).first()
        
        candidate_response = CandidateListResponse(
            id=candidate.id,
            name=candidate.name,
            email=candidate.email,
            phone=candidate.phone,
            application_status=candidate.application_status,
            application_date=candidate.application_date,
            match_score=candidate.match_score,
            is_qualified=candidate.is_qualified,
            interview_scheduled=candidate.interview_scheduled,
            interview_completed=candidate.interview_completed,
            job_id=candidate.job_id,
            job_title=job.title if job else None
        )
        candidate_responses.append(candidate_response)
    
    return candidate_responses

@router.get("/stats", response_model=CandidateStats)
async def get_candidate_statistics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get candidate statistics for current user"""
    
    # Base query for user's candidates
    if current_user.role == "admin":
        base_query = db.query(Candidate)
    else:
        base_query = db.query(Candidate).join(Job).filter(Job.owner_id == current_user.id)
    
    # Total candidates
    total_candidates = base_query.count()
    
    # Qualified candidates
    qualified_candidates = base_query.filter(Candidate.is_qualified == True).count()
    
    # Interviewed candidates
    interviewed_candidates = base_query.filter(Candidate.interview_completed == True).count()
    
    # Hired candidates
    hired_candidates = base_query.filter(Candidate.application_status == "hired").count()
    
    # Rejected candidates
    rejected_candidates = base_query.filter(Candidate.application_status == "rejected").count()
    
    return CandidateStats(
        total_candidates=total_candidates,
        qualified_candidates=qualified_candidates,
        interviewed_candidates=interviewed_candidates,
        hired_candidates=hired_candidates,
        rejected_candidates=rejected_candidates
    )

@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get candidate by ID"""
    
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    # Check permissions
    job = db.query(Job).filter(Job.id == candidate.job_id).first()
    if job and job.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return candidate

@router.put("/{candidate_id}", response_model=CandidateResponse)
async def update_candidate(
    candidate_id: int,
    candidate_update: CandidateUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update candidate"""
    
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    # Check permissions
    job = db.query(Job).filter(Job.id == candidate.job_id).first()
    if job and job.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Update fields
    update_data = candidate_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(candidate, field):
            setattr(candidate, field, value)
    
    db.commit()
    db.refresh(candidate)
    
    return candidate

@router.post("/{candidate_id}/schedule-interview")
async def schedule_interview(
    candidate_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Schedule interview for candidate"""
    
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    # Check permissions
    job = db.query(Job).filter(Job.id == candidate.job_id).first()
    if job and job.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if candidate is qualified
    if not candidate.is_qualified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Candidate is not qualified for interview"
        )
    
    # Check if interview already scheduled
    if candidate.interview_scheduled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview already scheduled for this candidate"
        )
    
    # Generate interview token if not exists
    if not candidate.interview_token:
        candidate.interview_token = str(uuid.uuid4())
        candidate.interview_link = f"/interview/{candidate.interview_token}"
    
    # Mark interview as scheduled
    candidate.interview_scheduled = True
    candidate.application_status = "interview"
    
    db.commit()
    
    return {
        "message": "Interview scheduled successfully",
        "interview_link": candidate.interview_link,
        "interview_token": candidate.interview_token
    }

@router.post("/{candidate_id}/hire")
async def hire_candidate(
    candidate_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Hire candidate"""
    
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    # Check permissions
    job = db.query(Job).filter(Job.id == candidate.job_id).first()
    if job and job.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Update candidate status
    candidate.application_status = "hired"
    db.commit()
    
    return {"message": f"Candidate {candidate.name} hired successfully"}

@router.post("/{candidate_id}/reject")
async def reject_candidate(
    candidate_id: int,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Reject candidate"""
    
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    # Check permissions
    job = db.query(Job).filter(Job.id == candidate.job_id).first()
    if job and job.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Update candidate status
    candidate.application_status = "rejected"
    if reason:
        candidate.feedback = reason
    
    db.commit()
    
    return {"message": f"Candidate {candidate.name} rejected"}

@router.delete("/{candidate_id}")
async def delete_candidate(
    candidate_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete candidate"""
    
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    # Check permissions
    job = db.query(Job).filter(Job.id == candidate.job_id).first()
    if job and job.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if candidate has completed interviews
    interview_count = db.query(Interview).filter(Interview.candidate_id == candidate.id).count()
    if interview_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete candidate with interview history"
        )
    
    db.delete(candidate)
    db.commit()
    
    return {"message": "Candidate deleted successfully"}

