from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
import uuid
from pydantic import BaseModel

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Pydantic models
class JobCreate(BaseModel):
    title: str
    description: str
    requirements: Optional[List[str]] = []
    status: Optional[str] = "active"
    department: Optional[str] = None
    location: Optional[str] = None
    salary_range: Optional[str] = None

class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[List[str]] = None
    status: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    salary_range: Optional[str] = None

# In-memory storage for jobs (no database required)
jobs_storage = []

# Initialize with some demo data
def initialize_demo_jobs():
    """Initialize with demo jobs"""
    if len(jobs_storage) == 0:
        demo_jobs = [
            {
                "id": "demo_job_1",
                "title": "Senior Frontend Developer",
                "description": "We are looking for a Senior Frontend Developer with expertise in React, JavaScript, and modern web technologies. The ideal candidate should have 5+ years of experience building scalable web applications and a strong understanding of UI/UX principles.",
                "requirements": ["React", "JavaScript", "TypeScript", "CSS", "HTML", "Git", "REST APIs"],
                "status": "active",
                "department": "Engineering",
                "location": "Remote",
                "salary_range": "$80,000 - $120,000",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "created_by": "demo_user"
            },
            {
                "id": "demo_job_2",
                "title": "Backend Python Developer",
                "description": "Join our team as a Backend Python Developer. You will work with Django, PostgreSQL, and cloud technologies to build robust backend systems. Experience with microservices and containerization is a plus.",
                "requirements": ["Python", "Django", "PostgreSQL", "REST API", "AWS", "Docker", "Git"],
                "status": "active",
                "department": "Engineering",
                "location": "New York, NY",
                "salary_range": "$75,000 - $110,000",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "created_by": "demo_user"
            },
            {
                "id": "demo_job_3",
                "title": "Full Stack Java Developer",
                "description": "We need a Full Stack Java Developer experienced in Spring Boot, microservices architecture, and modern frontend frameworks. You will be responsible for developing end-to-end solutions.",
                "requirements": ["Java", "Spring Boot", "Microservices", "React", "Docker", "Kubernetes", "MySQL"],
                "status": "active",
                "department": "Engineering",
                "location": "San Francisco, CA",
                "salary_range": "$90,000 - $130,000",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "created_by": "demo_user"
            }
        ]
        jobs_storage.extend(demo_jobs)
        logger.info(f"Initialized with {len(demo_jobs)} demo jobs")

# Initialize demo data on module load
initialize_demo_jobs()

# API Routes
@router.post("/")
async def create_job(job_data: JobCreate):
    """Create a new job posting"""
    try:
        new_job = {
            "id": str(uuid.uuid4()),
            "title": job_data.title,
            "description": job_data.description,
            "requirements": job_data.requirements or [],
            "status": job_data.status or "active",
            "department": job_data.department,
            "location": job_data.location,
            "salary_range": job_data.salary_range,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "created_by": "demo_user"  # No auth, so use demo user
        }
        
        jobs_storage.append(new_job)
        
        logger.info(f"Job created successfully: {job_data.title}")
        
        return {
            "success": True,
            "message": "Job created successfully",
            "job": new_job
        }
        
    except Exception as e:
        logger.error(f"Create job error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating job: {str(e)}"
        )

@router.get("/")
async def list_jobs(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    department: Optional[str] = None
):
    """List all jobs with optional filtering"""
    try:
        # Filter jobs
        filtered_jobs = jobs_storage
        
        if status_filter:
            filtered_jobs = [j for j in filtered_jobs if j.get("status") == status_filter]
        
        if department:
            filtered_jobs = [j for j in filtered_jobs if j.get("department") == department]
        
        # Pagination
        total = len(filtered_jobs)
        jobs_page = filtered_jobs[skip:skip + limit]
        
        return {
            "success": True,
            "jobs": jobs_page,
            "total": total,
            "page": skip // limit + 1,
            "per_page": limit,
            "has_more": skip + limit < total
        }
        
    except Exception as e:
        logger.error(f"List jobs error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving jobs: {str(e)}"
        )

@router.get("/stats/overview")
async def get_job_stats():
    """Get job statistics"""
    try:
        total_jobs = len(jobs_storage)
        active_jobs = len([j for j in jobs_storage if j.get("status") == "active"])
        inactive_jobs = total_jobs - active_jobs
        
        # Department analysis
        departments = {}
        for job in jobs_storage:
            dept = job.get("department", "Unknown")
            departments[dept] = departments.get(dept, 0) + 1
        
        # Requirements analysis
        all_requirements = []
        for job in jobs_storage:
            all_requirements.extend(job.get("requirements", []))
        
        requirement_counts = {}
        for req in all_requirements:
            requirement_counts[req] = requirement_counts.get(req, 0) + 1
        
        top_requirements = sorted(requirement_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "success": True,
            "stats": {
                "total_jobs": total_jobs,
                "active_jobs": active_jobs,
                "inactive_jobs": inactive_jobs,
                "departments": departments,
                "top_requirements": [{"requirement": req, "count": count} for req, count in top_requirements],
                "average_requirements_per_job": len(all_requirements) / total_jobs if total_jobs > 0 else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Job stats error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving job statistics: {str(e)}"
        )
