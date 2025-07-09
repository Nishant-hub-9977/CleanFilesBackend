"""
Jobs router for job posting and management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional

from ..core.database import get_db
from ..core.security import get_current_active_user, get_admin_user
from ..models.user import User
from ..models.job import Job
from ..models.candidate import Candidate
from ..models.interview import Interview
from ..schemas.job import (
    JobCreate, JobUpdate, JobResponse, JobListResponse, 
    JobStats, JobSearchFilters
)
from ..services.ai_service import generate_interview_questions_with_ai

router = APIRouter()

@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: JobCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new job posting"""
    
    # Create job
    db_job = Job(
        title=job_data.title,
        description=job_data.description,
        company=job_data.company,
        location=job_data.location,
        job_type=job_data.job_type,
        experience_level=job_data.experience_level,
        salary_min=job_data.salary_min,
        salary_max=job_data.salary_max,
        currency=job_data.currency,
        required_skills=job_data.required_skills,
        preferred_skills=job_data.preferred_skills,
        education_requirements=job_data.education_requirements,
        experience_requirements=job_data.experience_requirements,
        application_deadline=job_data.application_deadline,
        owner_id=current_user.id,
        is_active=True,
        is_published=False
    )
    
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    
    # Generate AI content in background
    background_tasks.add_task(generate_ai_job_content, db_job.id, db)
    
    return db_job

async def generate_ai_job_content(job_id: int, db: Session):
    """Background task to generate AI content for job"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return
    
    try:
         # Generate interview questions
        questions = await generate_interview_questions_with_ai(job.description)
        job.ai_generated_questions = questions
        
        # Job summary can be generated from description
        job.summary = job.description[:200] + "..." if len(job.description) > 200 else job.description
        
        db.commit()
    except Exception as e:
        print(f"Error generating AI content for job {job_id}: {e}")

@router.get("/", response_model=List[JobListResponse])
async def get_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    experience_level: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    is_published: Optional[bool] = Query(None),
    my_jobs: bool = Query(False),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get jobs with filtering and pagination"""
    
    query = db.query(Job)
    
    # Filter by owner if my_jobs is True
    if my_jobs:
        query = query.filter(Job.owner_id == current_user.id)
    
    # Apply search filters
    if search:
        query = query.filter(
            or_(
                Job.title.contains(search),
                Job.description.contains(search),
                Job.company.contains(search)
            )
        )
    
    if job_type:
        query = query.filter(Job.job_type == job_type)
    
    if experience_level:
        query = query.filter(Job.experience_level == experience_level)
    
    if location:
        query = query.filter(Job.location.contains(location))
    
    if company:
        query = query.filter(Job.company.contains(company))
    
    if is_active is not None:
        query = query.filter(Job.is_active == is_active)
    
    if is_published is not None:
        query = query.filter(Job.is_published == is_published)
    
    # Get jobs with candidate counts
    jobs = query.offset(skip).limit(limit).all()
    
    # Add statistics for each job
    job_responses = []
    for job in jobs:
        total_candidates = db.query(Candidate).filter(Candidate.job_id == job.id).count()
        qualified_candidates = db.query(Candidate).filter(
            and_(Candidate.job_id == job.id, Candidate.is_qualified == True)
        ).count()
        
        job_response = JobListResponse(
            id=job.id,
            title=job.title,
            company=job.company,
            location=job.location,
            job_type=job.job_type,
            experience_level=job.experience_level,
            is_active=job.is_active,
            is_published=job.is_published,
            created_at=job.created_at,
            total_candidates=total_candidates,
            qualified_candidates=qualified_candidates
        )
        job_responses.append(job_response)
    
    return job_responses

@router.get("/stats", response_model=JobStats)
async def get_job_statistics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get job statistics for current user"""
    
    # Total jobs by user
    total_jobs = db.query(Job).filter(Job.owner_id == current_user.id).count()
    
    # Active jobs
    active_jobs = db.query(Job).filter(
        and_(Job.owner_id == current_user.id, Job.is_active == True)
    ).count()
    
    # Published jobs
    published_jobs = db.query(Job).filter(
        and_(Job.owner_id == current_user.id, Job.is_published == True)
    ).count()
    
    # Total applications
    total_applications = db.query(Candidate).join(Job).filter(
        Job.owner_id == current_user.id
    ).count()
    
    # Qualified applications
    qualified_applications = db.query(Candidate).join(Job).filter(
        and_(Job.owner_id == current_user.id, Candidate.is_qualified == True)
    ).count()
    
    return JobStats(
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        published_jobs=published_jobs,
        total_applications=total_applications,
        qualified_applications=qualified_applications
    )

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get job by ID"""
    
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Check if user owns the job or is admin
    if job.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Add statistics
    total_candidates = db.query(Candidate).filter(Candidate.job_id == job.id).count()
    qualified_candidates = db.query(Candidate).filter(
        and_(Candidate.job_id == job.id, Candidate.is_qualified == True)
    ).count()
    interviews_completed = db.query(Interview).filter(
        and_(Interview.job_id == job.id, Interview.status == "completed")
    ).count()
    
    job_response = JobResponse.from_orm(job)
    job_response.total_candidates = total_candidates
    job_response.qualified_candidates = qualified_candidates
    job_response.interviews_completed = interviews_completed
    
    return job_response

@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: int,
    job_update: JobUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update job"""
    
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Check if user owns the job or is admin
    if job.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Update fields
    update_data = job_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(job, field):
            setattr(job, field, value)
    
    db.commit()
    db.refresh(job)
    
    # Regenerate AI content if job description or requirements changed
    if any(field in update_data for field in ['description', 'required_skills', 'preferred_skills']):
        background_tasks.add_task(generate_ai_job_content, job.id, db)
    
    return job

@router.delete("/{job_id}")
async def delete_job(
    job_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete job"""
    
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Check if user owns the job or is admin
    if job.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if job has candidates
    candidate_count = db.query(Candidate).filter(Candidate.job_id == job.id).count()
    if candidate_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete job with existing candidates. Deactivate instead."
        )
    
    db.delete(job)
    db.commit()
    
    return {"message": "Job deleted successfully"}

@router.post("/{job_id}/publish")
async def publish_job(
    job_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Publish job"""
    
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Check if user owns the job
    if job.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    job.is_published = True
    job.is_active = True
    db.commit()
    
    return {"message": "Job published successfully"}

@router.post("/{job_id}/unpublish")
async def unpublish_job(
    job_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Unpublish job"""
    
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Check if user owns the job
    if job.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    job.is_published = False
    db.commit()
    
    return {"message": "Job unpublished successfully"}

