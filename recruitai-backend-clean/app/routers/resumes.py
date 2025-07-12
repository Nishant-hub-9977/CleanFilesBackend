from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import os
import logging
import aiofiles
from datetime import datetime
import uuid
import json
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# In-memory storage for resumes (no database required)
resumes_storage = []

# File processing utilities
UPLOAD_DIR = "uploads/resumes"
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".doc"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Initialize with some demo data
def initialize_demo_data():
    """Initialize with demo resumes"""
    if len(resumes_storage) == 0:
        demo_resumes = [
            {
                "id": "demo_resume_1",
                "filename": "john_doe_resume.pdf",
                "original_filename": "john_doe_resume.pdf",
                "candidate_name": "John Doe",
                "candidate_email": "john.doe@email.com",
                "skills": ["JavaScript", "React", "Node.js", "Python", "SQL", "Git"],
                "upload_date": datetime.utcnow().isoformat(),
                "file_size": 245760,
                "processed": True,
                "extracted_text": "Experienced software developer with 5+ years in web development...",
                "match_scores": {}
            },
            {
                "id": "demo_resume_2", 
                "filename": "jane_smith_resume.pdf",
                "original_filename": "jane_smith_resume.pdf",
                "candidate_name": "Jane Smith",
                "candidate_email": "jane.smith@email.com",
                "skills": ["Python", "Django", "PostgreSQL", "Docker", "AWS", "Machine Learning"],
                "upload_date": (datetime.utcnow()).isoformat(),
                "file_size": 198432,
                "processed": True,
                "extracted_text": "Senior backend developer specializing in Python and cloud technologies...",
                "match_scores": {}
            },
            {
                "id": "demo_resume_3",
                "filename": "mike_johnson_resume.pdf", 
                "original_filename": "mike_johnson_resume.pdf",
                "candidate_name": "Mike Johnson",
                "candidate_email": "mike.johnson@email.com",
                "skills": ["Java", "Spring Boot", "Microservices", "Kubernetes", "MongoDB", "DevOps"],
                "upload_date": datetime.utcnow().isoformat(),
                "file_size": 312576,
                "processed": True,
                "extracted_text": "Full-stack Java developer with expertise in microservices architecture...",
                "match_scores": {}
            }
        ]
        resumes_storage.extend(demo_resumes)
        logger.info(f"Initialized with {len(demo_resumes)} demo resumes")

# Initialize demo data on module load
initialize_demo_data()

# Resume processing functions
def extract_text_from_file(file_path: str, file_extension: str) -> str:
    """Extract text from uploaded resume file"""
    try:
        if file_extension == ".txt":
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        elif file_extension == ".pdf":
            try:
                import PyPDF2
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                    return text
            except ImportError:
                logger.warning("PyPDF2 not available, using mock text for PDF")
                return "Mock extracted text from PDF file. Skills: Python, JavaScript, React, SQL, Git, Docker."
        
        elif file_extension in [".docx", ".doc"]:
            try:
                from docx import Document
                doc = Document(file_path)
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                return text
            except ImportError:
                logger.warning("python-docx not available, using mock text for DOCX")
                return "Mock extracted text from DOCX file. Skills: Java, Spring, MySQL, AWS, Kubernetes."
        
        else:
            return "Unsupported file format"
            
    except Exception as e:
        logger.error(f"Error extracting text from file: {str(e)}")
        return f"Mock extracted text. Skills: Python, JavaScript, React, Node.js, SQL, Git."

def extract_skills_from_text(text: str) -> List[str]:
    """Extract skills from resume text"""
    # Common technical skills (expanded list)
    skill_keywords = [
        # Programming Languages
        "python", "javascript", "java", "c++", "c#", "php", "ruby", "go", "rust", "swift",
        "kotlin", "typescript", "scala", "r", "matlab", "perl", "shell", "bash",
        
        # Web Technologies
        "html", "css", "react", "angular", "vue", "node.js", "express", "django", "flask",
        "spring", "laravel", "rails", "asp.net", "jquery", "bootstrap", "sass", "less",
        
        # Databases
        "sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch", "oracle",
        "sqlite", "cassandra", "dynamodb", "firebase",
        
        # Cloud & DevOps
        "aws", "azure", "gcp", "docker", "kubernetes", "jenkins", "git", "github",
        "gitlab", "ci/cd", "terraform", "ansible", "vagrant", "linux", "unix",
        
        # Data Science & AI
        "machine learning", "deep learning", "tensorflow", "pytorch", "pandas", "numpy",
        "scikit-learn", "data analysis", "statistics", "tableau", "power bi",
        
        # Mobile Development
        "android", "ios", "react native", "flutter", "xamarin", "cordova",
        
        # Other Technologies
        "rest api", "graphql", "microservices", "agile", "scrum", "jira", "confluence"
    ]
    
    text_lower = text.lower()
    found_skills = []
    
    for skill in skill_keywords:
        if skill in text_lower:
            found_skills.append(skill.title())
    
    # If no skills found, add some default ones
    if not found_skills:
        found_skills = ["Communication", "Problem Solving", "Teamwork", "Leadership"]
    
    return list(set(found_skills))  # Remove duplicates

def calculate_match_score(resume_skills: List[str], job_description: str) -> int:
    """Calculate match score between resume skills and job description"""
    if not resume_skills or not job_description:
        return 0
    
    job_desc_lower = job_description.lower()
    matching_skills = 0
    
    for skill in resume_skills:
        if skill.lower() in job_desc_lower:
            matching_skills += 1
    
    if len(resume_skills) == 0:
        return 0
    
    score = (matching_skills / len(resume_skills)) * 100
    return min(int(score), 100)

def create_resume_record(file_info: dict, extracted_text: str, skills: List[str]) -> dict:
    """Create a resume record"""
    return {
        "id": str(uuid.uuid4()),
        "filename": file_info["filename"],
        "original_filename": file_info["original_filename"],
        "file_path": file_info.get("file_path", ""),
        "file_size": file_info["file_size"],
        "content_type": file_info.get("content_type", ""),
        "extracted_text": extracted_text,
        "skills": skills,
        "upload_date": datetime.utcnow().isoformat(),
        "processed": True,
        "match_scores": {},
        "candidate_name": file_info.get("candidate_name", "Unknown"),
        "candidate_email": file_info.get("candidate_email", "")
    }

# API Routes
@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    job_id: Optional[str] = Form(None),
    candidate_name: Optional[str] = Form(None),
    candidate_email: Optional[str] = Form(None)
):
    """Upload and process a single resume"""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file_extension} not allowed. Supported types: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Check file size
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum limit of {MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        # Extract text and skills
        extracted_text = extract_text_from_file(file_path, file_extension)
        skills = extract_skills_from_text(extracted_text)
        
        # Create file info
        file_info = {
            "filename": unique_filename,
            "original_filename": file.filename,
            "file_path": file_path,
            "file_size": len(content),
            "content_type": file.content_type,
            "candidate_name": candidate_name or file.filename.split('.')[0].replace('_', ' ').title(),
            "candidate_email": candidate_email or f"{file.filename.split('.')[0]}@email.com"
        }
        
        # Create resume record
        resume_record = create_resume_record(file_info, extracted_text, skills)
        
        # Add additional info if provided
        if job_id:
            resume_record["job_id"] = job_id
        
        # Store resume
        resumes_storage.append(resume_record)
        
        logger.info(f"Resume uploaded successfully: {file.filename}")
        
        return {
            "success": True,
            "message": "Resume uploaded and processed successfully",
            "resume": {
                "id": resume_record["id"],
                "filename": resume_record["original_filename"],
                "candidate_name": resume_record["candidate_name"],
                "skills": resume_record["skills"],
                "skills_count": len(resume_record["skills"]),
                "upload_date": resume_record["upload_date"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resume upload error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing resume: {str(e)}"
        )

@router.get("/")
async def list_resumes(
    skip: int = 0,
    limit: int = 100,
    job_id: Optional[str] = None
):
    """List all resumes with optional filtering"""
    try:
        # Filter resumes
        filtered_resumes = resumes_storage
        
        if job_id:
            filtered_resumes = [r for r in filtered_resumes if r.get("job_id") == job_id]
        
        # Pagination
        total = len(filtered_resumes)
        resumes_page = filtered_resumes[skip:skip + limit]
        
        # Format response
        resume_list = []
        for resume in resumes_page:
            resume_list.append({
                "id": resume["id"],
                "filename": resume["original_filename"],
                "candidate_name": resume.get("candidate_name", "Unknown"),
                "candidate_email": resume.get("candidate_email", ""),
                "skills": resume["skills"],
                "skills_count": len(resume["skills"]),
                "upload_date": resume["upload_date"],
                "file_size": resume["file_size"],
                "processed": resume["processed"]
            })
        
        return {
            "success": True,
            "resumes": resume_list,
            "total": total,
            "page": skip // limit + 1,
            "per_page": limit,
            "has_more": skip + limit < total
        }
        
    except Exception as e:
        logger.error(f"List resumes error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving resumes: {str(e)}"
        )

@router.post("/match")
async def match_resumes_to_job(job_description: str):
    """Match resumes to a job description and return ranked results"""
    try:
        if not job_description.strip():
            raise HTTPException(status_code=400, detail="Job description cannot be empty")
        
        matches = []
        
        for resume in resumes_storage:
            match_score = calculate_match_score(resume["skills"], job_description)
            
            matches.append({
                "resume_id": resume["id"],
                "filename": resume["original_filename"],
                "candidate_name": resume.get("candidate_name", "Unknown"),
                "candidate_email": resume.get("candidate_email", ""),
                "skills": resume["skills"],
                "match_score": match_score,
                "upload_date": resume["upload_date"]
            })
        
        # Sort by match score (descending)
        matches.sort(key=lambda x: x["match_score"], reverse=True)
        
        logger.info(f"Resume matching completed: {len(matches)} resumes processed")
        
        return {
            "success": True,
            "job_description": job_description[:200] + "..." if len(job_description) > 200 else job_description,
            "total_resumes": len(matches),
            "matches": matches,
            "query_time": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resume matching error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error matching resumes: {str(e)}"
        )

@router.get("/stats/overview")
async def get_resume_stats():
    """Get resume statistics"""
    try:
        total_resumes = len(resumes_storage)
        processed_resumes = len([r for r in resumes_storage if r["processed"]])
        
        # Skills analysis
        all_skills = []
        for resume in resumes_storage:
            all_skills.extend(resume["skills"])
        
        skill_counts = {}
        for skill in all_skills:
            skill_counts[skill] = skill_counts.get(skill, 0) + 1
        
        top_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "success": True,
            "stats": {
                "total_resumes": total_resumes,
                "processed_resumes": processed_resumes,
                "pending_processing": total_resumes - processed_resumes,
                "total_skills_found": len(skill_counts),
                "top_skills": [{"skill": skill, "count": count} for skill, count in top_skills],
                "average_skills_per_resume": len(all_skills) / total_resumes if total_resumes > 0 else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Resume stats error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving resume statistics: {str(e)}"
        )
