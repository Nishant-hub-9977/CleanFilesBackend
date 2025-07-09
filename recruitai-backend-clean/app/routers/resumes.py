"""
Resumes router for resume upload and management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional
import os
import uuid
import magic
from datetime import datetime

from ..core.database import get_db
from ..core.security import get_current_active_user, get_admin_user
from ..core.config import settings
from ..models.user import User
from ..models.resume import Resume
from ..models.job import Job
from ..models.candidate import Candidate
from ..models.credit import Credit
from ..schemas.resume import (
    ResumeUploadResponse, ResumeResponse, ResumeListResponse,
    ResumeAnalysisRequest, ResumeMatchResult, ResumeProcessingStatus,
    ResumeStats, BulkResumeUploadResponse
)
from ..services.resume_service import process_resume, match_resume_to_job
from ..services.credit_service import deduct_credits

router = APIRouter()

@router.post("/upload", response_model=ResumeUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload a single resume file"""
    
    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )
    
    # Check file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    
    # Check file size
    file_content = await file.read()
    if len(file_content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE / (1024*1024):.1f}MB"
        )
    
    # Detect file type
    file_type = magic.from_buffer(file_content, mime=True)
    allowed_mime_types = {
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.txt': 'text/plain'
    }
    
    if file_type not in allowed_mime_types.values():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type"
        )
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
    
    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Save file
    with open(file_path, "wb") as buffer:
        buffer.write(file_content)
    
    # Create resume record
    db_resume = Resume(
        filename=unique_filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=len(file_content),
        file_type=file_ext[1:],  # Remove the dot
        uploaded_by=current_user.id,
        is_processed=False,
        processing_status="pending"
    )
    
    db.add(db_resume)
    db.commit()
    db.refresh(db_resume)
    
    # Process resume in background
    background_tasks.add_task(process_resume_background, db_resume.id, db)
    
    return db_resume

async def process_resume_background(resume_id: int, db: Session):
    """Background task to process resume"""
    try:
        await process_resume(resume_id, db)
    except Exception as e:
        # Update resume with error
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if resume:
            resume.processing_status = "failed"
            resume.processing_error = str(e)
            db.commit()

@router.post("/upload-bulk", response_model=BulkResumeUploadResponse)
async def upload_bulk_resumes(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload multiple resume files"""
    
    if len(files) > 50:  # Limit bulk upload
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 50 files allowed in bulk upload"
        )
    
    successful_uploads = []
    failed_uploads = []
    
    for file in files:
        try:
            # Validate file
            if not file.filename:
                failed_uploads.append({
                    "filename": "unknown",
                    "error": "No filename provided"
                })
                continue
            
            # Check file extension
            file_ext = os.path.splitext(file.filename)[1].lower()
            if file_ext not in settings.ALLOWED_EXTENSIONS:
                failed_uploads.append({
                    "filename": file.filename,
                    "error": f"File type not allowed: {file_ext}"
                })
                continue
            
            # Check file size
            file_content = await file.read()
            if len(file_content) > settings.MAX_FILE_SIZE:
                failed_uploads.append({
                    "filename": file.filename,
                    "error": "File too large"
                })
                continue
            
            # Generate unique filename
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
            
            # Save file
            with open(file_path, "wb") as buffer:
                buffer.write(file_content)
            
            # Create resume record
            db_resume = Resume(
                filename=unique_filename,
                original_filename=file.filename,
                file_path=file_path,
                file_size=len(file_content),
                file_type=file_ext[1:],
                uploaded_by=current_user.id,
                is_processed=False,
                processing_status="pending"
            )
            
            db.add(db_resume)
            db.commit()
            db.refresh(db_resume)
            
            successful_uploads.append(ResumeUploadResponse.from_orm(db_resume))
            
            # Process resume in background
            background_tasks.add_task(process_resume_background, db_resume.id, db)
            
        except Exception as e:
            failed_uploads.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    return BulkResumeUploadResponse(
        successful_uploads=successful_uploads,
        failed_uploads=failed_uploads,
        total_uploaded=len(successful_uploads),
        total_failed=len(failed_uploads)
    )

@router.get("/", response_model=List[ResumeListResponse])
async def get_resumes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    file_type: Optional[str] = Query(None),
    processing_status: Optional[str] = Query(None),
    is_processed: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get resumes with filtering and pagination"""
    
    query = db.query(Resume).filter(Resume.uploaded_by == current_user.id)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                Resume.original_filename.contains(search),
                Resume.candidate_name.contains(search),
                Resume.candidate_email.contains(search)
            )
        )
    
    if file_type:
        query = query.filter(Resume.file_type == file_type)
    
    if processing_status:
        query = query.filter(Resume.processing_status == processing_status)
    
    if is_processed is not None:
        query = query.filter(Resume.is_processed == is_processed)
    
    resumes = query.order_by(Resume.created_at.desc()).offset(skip).limit(limit).all()
    return resumes

@router.get("/stats", response_model=ResumeStats)
async def get_resume_statistics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get resume statistics for current user"""
    
    # Total resumes
    total_resumes = db.query(Resume).filter(Resume.uploaded_by == current_user.id).count()
    
    # Processed resumes
    processed_resumes = db.query(Resume).filter(
        and_(Resume.uploaded_by == current_user.id, Resume.is_processed == True)
    ).count()
    
    # Pending resumes
    pending_resumes = db.query(Resume).filter(
        and_(Resume.uploaded_by == current_user.id, Resume.processing_status == "pending")
    ).count()
    
    # Failed resumes
    failed_resumes = db.query(Resume).filter(
        and_(Resume.uploaded_by == current_user.id, Resume.processing_status == "failed")
    ).count()
    
    return ResumeStats(
        total_resumes=total_resumes,
        processed_resumes=processed_resumes,
        pending_resumes=pending_resumes,
        failed_resumes=failed_resumes
    )

@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get resume by ID"""
    
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )
    
    # Check if user owns the resume or is admin
    if resume.uploaded_by != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return resume

@router.get("/{resume_id}/status", response_model=ResumeProcessingStatus)
async def get_resume_processing_status(
    resume_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get resume processing status"""
    
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )
    
    # Check if user owns the resume or is admin
    if resume.uploaded_by != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return ResumeProcessingStatus(
        id=resume.id,
        processing_status=resume.processing_status,
        is_processed=resume.is_processed,
        processing_error=resume.processing_error,
        processed_at=resume.processed_at
    )

@router.post("/match", response_model=ResumeMatchResult)
async def match_resume_to_job_endpoint(
    match_request: ResumeAnalysisRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Match resume to job and return match score"""
    
    # Check if user has enough credits
    if not await deduct_credits(current_user.id, settings.CREDIT_COST_PER_RESUME_ANALYSIS, "resume_analysis", db):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient credits"
        )
    
    # Get resume and job
    resume = db.query(Resume).filter(Resume.id == match_request.resume_id).first()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )
    
    job = db.query(Job).filter(Job.id == match_request.job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Check permissions
    if resume.uploaded_by != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions for resume"
        )
    
    if job.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions for job"
        )
    
    # Check if resume is processed
    if not resume.is_processed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume is not yet processed"
        )
    
    # Perform matching
    match_result = await match_resume_to_job(resume, job)
    
    return ResumeMatchResult(
        resume_id=resume.id,
        job_id=job.id,
        match_score=match_result["match_score"],
        is_qualified=match_result["is_qualified"],
        match_details=match_result["match_details"]
    )

@router.delete("/{resume_id}")
async def delete_resume(
    resume_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete resume"""
    
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )
    
    # Check if user owns the resume or is admin
    if resume.uploaded_by != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if resume is used by candidates
    candidate_count = db.query(Candidate).filter(Candidate.resume_id == resume.id).count()
    if candidate_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete resume that is linked to candidates"
        )
    
    # Delete file
    try:
        if os.path.exists(resume.file_path):
            os.remove(resume.file_path)
    except Exception as e:
        print(f"Error deleting file {resume.file_path}: {e}")
    
    # Delete database record
    db.delete(resume)
    db.commit()
    
    return {"message": "Resume deleted successfully"}

