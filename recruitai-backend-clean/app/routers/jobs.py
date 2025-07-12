


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
    created_at: datetime
    updated_at: datetime
    created_by: str
    applications_count: int
    views_count: int
    status: str

# In-memory storage for demo/fallback mode
mock_jobs = [
    {
        "id": "job1",
        "title": "Senior Software Engineer",
        "description": "We are looking for a passionate Senior Software Engineer to join our team. You will be responsible for developing and maintaining high-quality software solutions.",
        "requirements": ["5+ years experience", "Strong Python skills", "Experience with FastAPI"],
        "location": "Remote",
        "salary_range": "$120,000 - $150,000",
        "employment_type": "Full-time",
        "experience_level": "Senior",
        "skills_required": ["Python", "FastAPI", "SQLAlchemy", "Docker", "AWS"],
        "department": "Engineering",
        "created_at": datetime.fromisoformat("2024-01-01T10:00:00Z"),
        "updated_at": datetime.fromisoformat("2024-01-01T10:00:00Z"),
        "created_by": "admin_id",
        "applications_count": 15,
        "views_count": 120,
        "status": "active"
    },
    {
        "id": "job2",
        "title": "Frontend Developer",
        "description": "Join our dynamic team as a Frontend Developer and build amazing user interfaces using modern web technologies.",
        "requirements": ["3+ years experience", "Proficiency in React", "HTML, CSS, JavaScript"],
        "location": "New York, NY",
        "salary_range": "$90,000 - $110,000",
        "employment_type": "Full-time",
        "experience_level": "Mid-level",
        "skills_required": ["React", "JavaScript", "HTML", "CSS", "TypeScript", "Redux"],
        "department": "Engineering",
        "created_at": datetime.fromisoformat("2024-01-05T11:30:00Z"),
        "updated_at": datetime.fromisoformat("2024-01-05T11:30:00Z"),
        "created_by": "recruiter_id",
        "applications_count": 20,
        "views_count": 150,
        "status": "active"
    },
    {
        "id": "job3",
        "title": "DevOps Engineer",
        "description": "We need an experienced DevOps Engineer to streamline our development and operations processes.",
        "requirements": ["4+ years experience", "Kubernetes, Docker", "CI/CD pipelines"],
        "location": "San Francisco, CA",
        "salary_range": "$130,000 - $160,000",
        "employment_type": "Full-time",
        "experience_level": "Senior",
        "skills_required": ["Docker", "Kubernetes", "AWS", "Azure", "CI/CD", "Ansible", "Terraform"],
        "department": "Operations",
        "created_at": datetime.fromisoformat("2024-01-10T09:00:00Z"),
        "updated_at": datetime.fromisoformat("2024-01-10T09:00:00Z"),
        "created_by": "admin_id",
        "applications_count": 12,
        "views_count": 90,
        "status": "active"
    },
    {
        "id": "job4",
        "title": "Data Scientist",
        "description": "As a Data Scientist, you will be responsible for analyzing large datasets and building predictive models.",
        "requirements": ["PhD or Master's in a quantitative field", "Strong Python/R skills", "Machine Learning"],
        "location": "Boston, MA",
        "salary_range": "$110,000 - $140,000",
        "employment_type": "Full-time",
        "experience_level": "Mid-level",
        "skills_required": ["Python", "R", "Machine Learning", "SQL", "Pandas", "NumPy", "Scikit-learn"],
        "department": "Data Science",
        "created_at": datetime.fromisoformat("2024-01-15T14:00:00Z"),
        "updated_at": datetime.fromisoformat("2024-01-15T14:00:00Z"),
        "created_by": "recruiter_id",
        "applications_count": 8,
        "views_count": 70,
        "status": "closed"
    },
    {
        "id": "job5",
        "title": "UI/UX Designer",
        "description": "Create intuitive and visually appealing user interfaces for our web and mobile applications.",
        "requirements": ["2+ years experience", "Proficiency in Figma, Sketch, Adobe XD", "User-centered design"],
        "location": "Remote",
        "salary_range": "$80,000 - $100,000",
        "employment_type": "Full-time",
        "experience_level": "Junior",
        "skills_required": ["Figma", "Sketch", "Adobe XD", "User Research", "Prototyping", "Wireframing"],
        "department": "Design",
        "created_at": datetime.fromisoformat("2024-01-20T16:00:00Z"),
        "updated_at": datetime.fromisoformat("2024-01-20T16:00:00Z"),
        "created_by": "admin_id",
        "applications_count": 18,
        "views_count": 110,
        "status": "active"
    }
]

# Helper function to get current user (mock for now)
async def get_current_user():
    # In a real application, this would validate a token and return user info
    return {"id": "mock_user", "email": "mock@example.com", "role": "admin"}

@router.post("/", response_model=JobResponse)
async def create_job(job: JobCreate, current_user: dict = Depends(get_current_user)):
    """Create a new job posting"""
    new_job = job.dict()
    new_job["id"] = str(uuid.uuid4())
    new_job["created_at"] = datetime.utcnow()
    new_job["updated_at"] = datetime.utcnow()
    new_job["created_by"] = current_user["id"]
    new_job["applications_count"] = 0
    new_job["views_count"] = 0
    new_job["status"] = "active"
    mock_jobs.append(new_job)
    return new_job

@router.get("/", response_model=List[JobResponse])
async def get_all_jobs(current_user: dict = Depends(get_current_user)):
    """Retrieve all job postings"""
    return mock_jobs

@router.get("/{job_id}", response_model=JobResponse)
async def get_job_by_id(job_id: str, current_user: dict = Depends(get_current_user)):
    """Retrieve a single job posting by ID"""
    job = next((job for job in mock_jobs if job["id"] == job_id), None)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.put("/{job_id}", response_model=JobResponse)
async def update_job(job_id: str, job_update: JobUpdate, current_user: dict = Depends(get_current_user)):
    """Update an existing job posting"""
    job_index = next((i for i, job in enumerate(mock_jobs) if job["id"] == job_id), None)
    if job_index is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    current_job = mock_jobs[job_index]
    updated_data = job_update.dict(exclude_unset=True)
    for key, value in updated_data.items():
        if key == "skills_required" and isinstance(value, str):
            current_job[key] = [s.strip() for s in value.split(",")]
        else:
            current_job[key] = value
    current_job["updated_at"] = datetime.utcnow()
    mock_jobs[job_index] = current_job
    return current_job

@router.delete("/{job_id}")
async def delete_job(job_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a job posting"""
    global mock_jobs
    initial_len = len(mock_jobs)
    mock_jobs = [job for job in mock_jobs if job["id"] != job_id]
    if len(mock_jobs) == initial_len:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"message": "Job deleted successfully"}

@router.get("/{job_id}/applications")
async def get_job_applications(job_id: str, current_user: dict = Depends(get_current_user)):
    """Get applications for a specific job (mock data)"""
    job = next((job for job in mock_jobs if job["id"] == job_id), None)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        applications = [
            {
                "id": "app1",
                "resume_id": "resume1",
                "candidate_name": "Alice Smith",
                "status": "pending",
                "applied_at": "2024-01-01T12:00:00Z",
                "match_score": 92,
                "cover_letter": "I am highly interested in this position..."
            },
            {
                "id": "app2",
                "resume_id": "resume2",
                "candidate_name": "Bob Johnson",
                "status": "reviewed",
                "applied_at": "2024-01-02T10:30:00Z",
                "match_score": 88,
                "cover_letter": "My experience aligns perfectly..."
            },
            {
                "id": "app3",
                "resume_id": "resume3",
                "candidate_name": "Charlie Brown",
                "status": "interview_scheduled",
                "applied_at": "2024-01-04T14:15:00Z",
                "match_score": 95,
                "cover_letter": "With my 5 years of experience..."
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
