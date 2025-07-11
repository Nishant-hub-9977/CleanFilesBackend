from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid
import json

router = APIRouter()
security = HTTPBearer()

# Pydantic models
class JobCreate(BaseModel):
    title: str
    description: str
    requirements: List[str]
    location: str
    salary_range: Optional[str] = None
    employment_type: str = "Full-time"
    experience_level: str = "Mid-level"
    skills_required: List[str] = []
    department: Optional[str] = None

class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[List[str]] = None
    location: Optional[str] = None
    salary_range: Optional[str] = None
    employment_type: Optional[str] = None
    experience_level: Optional[str] = None
    skills_required: Optional[List[str]] = None
    department: Optional[str] = None
    status: Optional[str] = None

class JobResponse(BaseModel):
    id: str
    title: str
    description: str
    requirements: List[str]
    location: str
    salary_range: Optional[str]
    employment_type: str
    experience_level: str
    skills_required: List[str]
    department: Optional[str]
    status: str
    created_at: str
    updated_at: str
    created_by: str
    applications_count: int

# Mock database
mock_jobs = [
    {
        "id": "job_001",
        "title": "Senior Python Developer",
        "description": "We are looking for an experienced Python developer to join our team.",
        "requirements": ["5+ years Python experience", "FastAPI knowledge", "Database design"],
        "location": "Remote",
        "salary_range": "$80,000 - $120,000",
        "employment_type": "Full-time",
        "experience_level": "Senior",
        "skills_required": ["Python", "FastAPI", "PostgreSQL", "Docker"],
        "department": "Engineering",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "created_by": "admin@recruitai.com",
        "applications_count": 15
    },
    {
        "id": "job_002",
        "title": "Frontend React Developer",
        "description": "Join our frontend team to build amazing user interfaces.",
        "requirements": ["3+ years React experience", "TypeScript knowledge", "UI/UX understanding"],
        "location": "New York, NY",
        "salary_range": "$70,000 - $100,000",
        "employment_type": "Full-time",
        "experience_level": "Mid-level",
        "skills_required": ["React", "TypeScript", "CSS", "JavaScript"],
        "department": "Engineering",
        "status": "active",
        "created_at": "2024-01-02T00:00:00Z",
        "updated_at": "2024-01-02T00:00:00Z",
        "created_by": "admin@recruitai.com",
        "applications_count": 23
    }
]

# Helper functions
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # Simple token validation - in production, use proper JWT validation
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    return {"email": "admin@recruitai.com", "id": "user_001"}

def generate_job_id():
    return f"job_{uuid.uuid4().hex[:8]}"

# Job endpoints
@router.get("/jobs", response_model=List[JobResponse])
async def get_jobs(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    department: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all jobs with optional filtering"""
    try:
        jobs = mock_jobs.copy()
        
        # Apply filters
        if status:
            jobs = [job for job in jobs if job["status"] == status]
        if department:
            jobs = [job for job in jobs if job.get("department") == department]
        
        # Apply pagination
        jobs = jobs[skip:skip + limit]
        
        return jobs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching jobs: {str(e)}")

@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific job by ID"""
    try:
        job = next((job for job in mock_jobs if job["id"] == job_id), None)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching job: {str(e)}")

@router.post("/jobs", response_model=JobResponse)
async def create_job(job_data: JobCreate, current_user: dict = Depends(get_current_user)):
    """Create a new job posting"""
    try:
        job_id = generate_job_id()
        current_time = datetime.utcnow().isoformat() + "Z"
        
        new_job = {
            "id": job_id,
            "title": job_data.title,
            "description": job_data.description,
            "requirements": job_data.requirements,
            "location": job_data.location,
            "salary_range": job_data.salary_range,
            "employment_type": job_data.employment_type,
            "experience_level": job_data.experience_level,
            "skills_required": job_data.skills_required,
            "department": job_data.department,
            "status": "active",
            "created_at": current_time,
            "updated_at": current_time,
            "created_by": current_user["email"],
            "applications_count": 0
        }
        
        mock_jobs.append(new_job)
        
        return new_job
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating job: {str(e)}")

@router.put("/jobs/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: str, 
    job_data: JobUpdate, 
    current_user: dict = Depends(get_current_user)
):
    """Update an existing job"""
    try:
        job_index = next((i for i, job in enumerate(mock_jobs) if job["id"] == job_id), None)
        if job_index is None:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = mock_jobs[job_index]
        
        # Update fields
        update_data = job_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                job[field] = value
        
        job["updated_at"] = datetime.utcnow().isoformat() + "Z"
        mock_jobs[job_index] = job
        
        return job
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating job: {str(e)}")

@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a job posting"""
    try:
        job_index = next((i for i, job in enumerate(mock_jobs) if job["id"] == job_id), None)
        if job_index is None:
            raise HTTPException(status_code=404, detail="Job not found")
        
        deleted_job = mock_jobs.pop(job_index)
        
        return {
            "success": True,
            "message": f"Job '{deleted_job['title']}' deleted successfully",
            "deleted_job_id": job_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting job: {str(e)}")

@router.get("/jobs/{job_id}/applications")
async def get_job_applications(job_id: str, current_user: dict = Depends(get_current_user)):
    """Get applications for a specific job"""
    try:
        job = next((job for job in mock_jobs if job["id"] == job_id), None)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Mock applications data
        applications = [
            {
                "id": "app_001",
                "candidate_name": "John Doe",
                "email": "john.doe@email.com",
                "phone": "+1-555-0123",
                "resume_url": "/resumes/john_doe_resume.pdf",
                "cover_letter": "I am very interested in this position...",
                "match_score": 85,
                "status": "under_review",
                "applied_at": "2024-01-03T10:30:00Z"
            },
            {
                "id": "app_002",
                "candidate_name": "Jane Smith",
                "email": "jane.smith@email.com",
                "phone": "+1-555-0124",
                "resume_url": "/resumes/jane_smith_resume.pdf",
                "cover_letter": "With my 5 years of experience...",
                "match_score": 92,
                "status": "interview_scheduled",
                "applied_at": "2024-01-04T14:15:00Z"
            }
        ]
        
        return {
            "job_id": job_id,
            "job_title": job["title"],
            "total_applications": len(applications),
            "applications": applications
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching applications: {str(e)}")

@router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    """Get dashboard statistics"""
    try:
        total_jobs = len(mock_jobs)
        active_jobs = len([job for job in mock_jobs if job["status"] == "active"])
        total_applications = sum(job["applications_count"] for job in mock_jobs)
        
        return {
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "total_applications": total_applications,
            "total_candidates": 48,  # Mock data
            "total_resumes": 156,    # Mock data
            "total_interviews": 23,  # Mock data
            "avg_match_score": 92,
            "avg_time_to_hire": 4.2,
            "interview_success_rate": 85
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching dashboard stats: {str(e)}")

