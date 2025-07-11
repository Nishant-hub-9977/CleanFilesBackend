from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid
import os
import shutil
import json

router = APIRouter()
security = HTTPBearer()

# Pydantic models
class ResumeResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    candidate_name: Optional[str]
    candidate_email: Optional[str]
    candidate_phone: Optional[str]
    skills: List[str]
    experience_years: Optional[int]
    education: List[str]
    match_scores: dict
    status: str
    uploaded_at: str
    processed_at: Optional[str]
    file_url: str

class ResumeAnalysis(BaseModel):
    candidate_name: str
    email: str
    phone: str
    skills: List[str]
    experience_years: int
    education: List[str]
    summary: str
    match_score: int

class BulkUploadResponse(BaseModel):
    success_count: int
    failed_count: int
    total_count: int
    successful_uploads: List[ResumeResponse]
    failed_uploads: List[dict]

# Mock database
mock_resumes = [
    {
        "id": "resume_001",
        "filename": "john_doe_resume.pdf",
        "original_filename": "John_Doe_Resume.pdf",
        "file_size": 245760,
        "file_type": "application/pdf",
        "candidate_name": "John Doe",
        "candidate_email": "john.doe@email.com",
        "candidate_phone": "+1-555-0123",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
        "experience_years": 5,
        "education": ["BS Computer Science - MIT", "MS Software Engineering - Stanford"],
        "match_scores": {
            "job_001": 85,
            "job_002": 45
        },
        "status": "processed",
        "uploaded_at": "2024-01-01T10:00:00Z",
        "processed_at": "2024-01-01T10:02:00Z",
        "file_url": "/uploads/resumes/john_doe_resume.pdf"
    },
    {
        "id": "resume_002",
        "filename": "jane_smith_resume.pdf",
        "original_filename": "Jane_Smith_Resume.pdf",
        "file_size": 198432,
        "file_type": "application/pdf",
        "candidate_name": "Jane Smith",
        "candidate_email": "jane.smith@email.com",
        "candidate_phone": "+1-555-0124",
        "skills": ["React", "TypeScript", "Node.js", "CSS", "JavaScript"],
        "experience_years": 3,
        "education": ["BS Computer Science - UC Berkeley"],
        "match_scores": {
            "job_001": 35,
            "job_002": 92
        },
        "status": "processed",
        "uploaded_at": "2024-01-02T14:30:00Z",
        "processed_at": "2024-01-02T14:32:00Z",
        "file_url": "/uploads/resumes/jane_smith_resume.pdf"
    }
]

# Helper functions
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    return {"email": "admin@recruitai.com", "id": "user_001"}

def generate_resume_id():
    return f"resume_{uuid.uuid4().hex[:8]}"

def analyze_resume(file_content: bytes, filename: str) -> ResumeAnalysis:
    """Mock AI resume analysis - in production, use actual AI/ML service"""
    # Mock analysis based on filename
    if "john" in filename.lower():
        return ResumeAnalysis(
            candidate_name="John Doe",
            email="john.doe@email.com",
            phone="+1-555-0123",
            skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
            experience_years=5,
            education=["BS Computer Science"],
            summary="Experienced Python developer with 5 years of backend development experience.",
            match_score=85
        )
    elif "jane" in filename.lower():
        return ResumeAnalysis(
            candidate_name="Jane Smith",
            email="jane.smith@email.com",
            phone="+1-555-0124",
            skills=["React", "TypeScript", "JavaScript"],
            experience_years=3,
            education=["BS Computer Science"],
            summary="Frontend developer with strong React and TypeScript skills.",
            match_score=78
        )
    else:
        return ResumeAnalysis(
            candidate_name="Unknown Candidate",
            email="candidate@email.com",
            phone="+1-555-0000",
            skills=["General Skills"],
            experience_years=2,
            education=["Bachelor's Degree"],
            summary="Resume analysis completed.",
            match_score=65
        )

def calculate_job_matches(skills: List[str]) -> dict:
    """Calculate match scores for all jobs"""
    # Mock job matching logic
    matches = {}
    if "python" in [s.lower() for s in skills]:
        matches["job_001"] = 85
        matches["job_002"] = 35
    elif "react" in [s.lower() for s in skills]:
        matches["job_001"] = 35
        matches["job_002"] = 92
    else:
        matches["job_001"] = 50
        matches["job_002"] = 50
    
    return matches

# Resume endpoints
@router.get("/resumes", response_model=List[ResumeResponse])
async def get_resumes(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    min_match_score: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all resumes with optional filtering"""
    try:
        resumes = mock_resumes.copy()
        
        # Apply filters
        if status:
            resumes = [resume for resume in resumes if resume["status"] == status]
        
        if min_match_score:
            resumes = [
                resume for resume in resumes 
                if any(score >= min_match_score for score in resume["match_scores"].values())
            ]
        
        # Apply pagination
        resumes = resumes[skip:skip + limit]
        
        return resumes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching resumes: {str(e)}")

@router.get("/resumes/{resume_id}", response_model=ResumeResponse)
async def get_resume(resume_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific resume by ID"""
    try:
        resume = next((resume for resume in mock_resumes if resume["id"] == resume_id), None)
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        return resume
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching resume: {str(e)}")

@router.post("/resumes/upload", response_model=ResumeResponse)
async def upload_resume(
    file: UploadFile = File(...),
    job_id: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """Upload and process a single resume"""
    try:
        # Validate file type
        allowed_types = ["application/pdf", "application/msword", 
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail="Invalid file type. Only PDF and Word documents are allowed."
            )
        
        # Validate file size (5MB limit)
        file_content = await file.read()
        if len(file_content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size too large. Maximum 5MB allowed.")
        
        # Generate unique filename
        resume_id = generate_resume_id()
        file_extension = os.path.splitext(file.filename)[1]
        filename = f"{resume_id}{file_extension}"
        
        # Mock file save (in production, save to cloud storage)
        file_url = f"/uploads/resumes/{filename}"
        
        # Analyze resume content
        analysis = analyze_resume(file_content, file.filename)
        
        # Calculate job matches
        match_scores = calculate_job_matches(analysis.skills)
        
        # Create resume record
        current_time = datetime.utcnow().isoformat() + "Z"
        new_resume = {
            "id": resume_id,
            "filename": filename,
            "original_filename": file.filename,
            "file_size": len(file_content),
            "file_type": file.content_type,
            "candidate_name": analysis.candidate_name,
            "candidate_email": analysis.email,
            "candidate_phone": analysis.phone,
            "skills": analysis.skills,
            "experience_years": analysis.experience_years,
            "education": analysis.education,
            "match_scores": match_scores,
            "status": "processed",
            "uploaded_at": current_time,
            "processed_at": current_time,
            "file_url": file_url
        }
        
        mock_resumes.append(new_resume)
        
        return new_resume
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading resume: {str(e)}")

@router.post("/resumes/bulk-upload", response_model=BulkUploadResponse)
async def bulk_upload_resumes(
    files: List[UploadFile] = File(...),
    job_id: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """Upload and process multiple resumes"""
    try:
        successful_uploads = []
        failed_uploads = []
        
        for file in files:
            try:
                # Process each file individually
                file_content = await file.read()
                
                # Validate file
                allowed_types = ["application/pdf", "application/msword", 
                               "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
                if file.content_type not in allowed_types:
                    failed_uploads.append({
                        "filename": file.filename,
                        "error": "Invalid file type"
                    })
                    continue
                
                if len(file_content) > 5 * 1024 * 1024:
                    failed_uploads.append({
                        "filename": file.filename,
                        "error": "File size too large"
                    })
                    continue
                
                # Process resume
                resume_id = generate_resume_id()
                file_extension = os.path.splitext(file.filename)[1]
                filename = f"{resume_id}{file_extension}"
                file_url = f"/uploads/resumes/{filename}"
                
                analysis = analyze_resume(file_content, file.filename)
                match_scores = calculate_job_matches(analysis.skills)
                
                current_time = datetime.utcnow().isoformat() + "Z"
                new_resume = {
                    "id": resume_id,
                    "filename": filename,
                    "original_filename": file.filename,
                    "file_size": len(file_content),
                    "file_type": file.content_type,
                    "candidate_name": analysis.candidate_name,
                    "candidate_email": analysis.email,
                    "candidate_phone": analysis.phone,
                    "skills": analysis.skills,
                    "experience_years": analysis.experience_years,
                    "education": analysis.education,
                    "match_scores": match_scores,
                    "status": "processed",
                    "uploaded_at": current_time,
                    "processed_at": current_time,
                    "file_url": file_url
                }
                
                mock_resumes.append(new_resume)
                successful_uploads.append(new_resume)
                
            except Exception as e:
                failed_uploads.append({
                    "filename": file.filename,
                    "error": str(e)
                })
        
        return BulkUploadResponse(
            success_count=len(successful_uploads),
            failed_count=len(failed_uploads),
            total_count=len(files),
            successful_uploads=successful_uploads,
            failed_uploads=failed_uploads
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in bulk upload: {str(e)}")

@router.delete("/resumes/{resume_id}")
async def delete_resume(resume_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a resume"""
    try:
        resume_index = next((i for i, resume in enumerate(mock_resumes) if resume["id"] == resume_id), None)
        if resume_index is None:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        deleted_resume = mock_resumes.pop(resume_index)
        
        return {
            "success": True,
            "message": f"Resume for '{deleted_resume['candidate_name']}' deleted successfully",
            "deleted_resume_id": resume_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting resume: {str(e)}")

@router.get("/resumes/{resume_id}/matches")
async def get_resume_matches(resume_id: str, current_user: dict = Depends(get_current_user)):
    """Get job matches for a specific resume"""
    try:
        resume = next((resume for resume in mock_resumes if resume["id"] == resume_id), None)
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        # Get detailed match information
        matches = []
        for job_id, score in resume["match_scores"].items():
            matches.append({
                "job_id": job_id,
                "job_title": f"Job Title {job_id}",  # In production, fetch from jobs
                "match_score": score,
                "matching_skills": resume["skills"][:3],  # Mock matching skills
                "missing_skills": ["Skill A", "Skill B"] if score < 80 else []
            })
        
        return {
            "resume_id": resume_id,
            "candidate_name": resume["candidate_name"],
            "total_matches": len(matches),
            "matches": sorted(matches, key=lambda x: x["match_score"], reverse=True)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching matches: {str(e)}")

@router.post("/resumes/{resume_id}/reprocess")
async def reprocess_resume(resume_id: str, current_user: dict = Depends(get_current_user)):
    """Reprocess a resume for updated analysis"""
    try:
        resume_index = next((i for i, resume in enumerate(mock_resumes) if resume["id"] == resume_id), None)
        if resume_index is None:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        resume = mock_resumes[resume_index]
        
        # Mock reprocessing
        resume["processed_at"] = datetime.utcnow().isoformat() + "Z"
        resume["status"] = "processed"
        
        # Recalculate matches
        resume["match_scores"] = calculate_job_matches(resume["skills"])
        
        mock_resumes[resume_index] = resume
        
        return {
            "success": True,
            "message": "Resume reprocessed successfully",
            "resume": resume
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reprocessing resume: {str(e)}")

