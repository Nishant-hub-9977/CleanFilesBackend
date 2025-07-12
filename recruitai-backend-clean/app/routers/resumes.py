from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, status
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

# Try to import database models, fallback to in-memory storage
try:
    from app.core.database import get_db
    from app.models.resume import Resume
    DATABASE_AVAILABLE = True
    logger.info("Database models imported successfully")
except ImportError as e:
    DATABASE_AVAILABLE = False
    logger.warning("Database models not available, using in-memory storage")

# In-memory storage for resumes (fallback)
resumes_storage = []

# File processing utilities
UPLOAD_DIR = "uploads/resumes"
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".doc"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

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
                logger.warning("PyPDF2 not available, cannot process PDF files")
                return "PDF processing not available"
        
        elif file_extension in [".docx", ".doc"]:
            try:
                from docx import Document
                doc = Document(file_path)
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                return text
            except ImportError:
                logger.warning("python-docx not available, cannot process DOCX files")
                return "DOCX processing not available"
        
        else:
            return "Unsupported file format"
            
    except Exception as e:
        logger.error(f"Error extracting text from file: {str(e)}")
        return f"Error processing file: {str(e)}"

def extract_skills_from_text(text: str) -> List[str]:
    """Extract skills from resume text"""
    # Common technical skills (simplified list)
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
        "file_path": file_info["file_path"],
        "file_size": file_info["file_size"],
        "content_type": file_info["content_type"],
        "extracted_text": extracted_text,
        "skills": skills,
        "upload_date": datetime.utcnow().isoformat(),
        "processed": True,
        "match_scores": {}
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
            "content_type": file.content_type
        }
        
        # Create resume record
        resume_record = create_resume_record(file_info, extracted_text, skills)
        
        # Add additional info if provided
        if candidate_name:
            resume_record["candidate_name"] = candidate_name
        if candidate_email:
            resume_record["candidate_email"] = candidate_email
        if job_id:
            resume_record["job_id"] = job_id
        
        # Store resume (database or in-memory)
        if DATABASE_AVAILABLE:
            # TODO: Save to database
            pass
        
        resumes_storage.append(resume_record)
        
        logger.info(f"Resume uploaded successfully: {file.filename}")
        
        return {
            "success": True,
            "message": "Resume uploaded and processed successfully",
            "resume": {
                "id": resume_record["id"],
                "filename": resume_record["original_filename"],
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

@router.post("/bulk-upload")
async def bulk_upload_resumes(files: List[UploadFile] = File(...)):
    """Upload and process multiple resumes"""
    try:
        if len(files) > 20:
            raise HTTPException(
                status_code=400,
                detail="Maximum 20 files allowed per bulk upload"
            )
        
        results = []
        successful_uploads = 0
        failed_uploads = 0
        
        for file in files:
            try:
                # Process each file individually
                result = await upload_resume(file)
                results.append({
                    "filename": file.filename,
                    "status": "success",
                    "resume_id": result["resume"]["id"],
                    "skills_count": result["resume"]["skills_count"]
                })
                successful_uploads += 1
                
            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "status": "failed",
                    "error": str(e)
                })
                failed_uploads += 1
        
        logger.info(f"Bulk upload completed: {successful_uploads} successful, {failed_uploads} failed")
        
        return {
            "success": True,
            "message": f"Bulk upload completed: {successful_uploads} successful, {failed_uploads} failed",
            "summary": {
                "total_files": len(files),
                "successful": successful_uploads,
                "failed": failed_uploads
            },
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk upload error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during bulk upload: {str(e)}"
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

@router.get("/{resume_id}")
async def get_resume(resume_id: str):
    """Get detailed information about a specific resume"""
    try:
        resume = next((r for r in resumes_storage if r["id"] == resume_id), None)
        
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        return {
            "success": True,
            "resume": {
                "id": resume["id"],
                "filename": resume["original_filename"],
                "candidate_name": resume.get("candidate_name", "Unknown"),
                "candidate_email": resume.get("candidate_email", ""),
                "skills": resume["skills"],
                "extracted_text": resume["extracted_text"][:500] + "..." if len(resume["extracted_text"]) > 500 else resume["extracted_text"],
                "upload_date": resume["upload_date"],
                "file_size": resume["file_size"],
                "content_type": resume["content_type"],
                "processed": resume["processed"],
                "match_scores": resume.get("match_scores", {})
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get resume error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving resume: {str(e)}"
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

@router.delete("/{resume_id}")
async def delete_resume(resume_id: str):
    """Delete a resume"""
    try:
        resume = next((r for r in resumes_storage if r["id"] == resume_id), None)
        
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        # Remove file
        try:
            if os.path.exists(resume["file_path"]):
                os.remove(resume["file_path"])
        except Exception as e:
            logger.warning(f"Could not delete file {resume['file_path']}: {str(e)}")
        
        # Remove from storage
        resumes_storage.remove(resume)
        
        logger.info(f"Resume deleted: {resume_id}")
        
        return {
            "success": True,
            "message": "Resume deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete resume error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting resume: {str(e)}"
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

@router.get("/health")
async def resumes_health():
    """Resume service health check"""
    return {
        "status": "healthy",
        "service": "resumes",
        "timestamp": datetime.utcnow().isoformat(),
        "storage_type": "database" if DATABASE_AVAILABLE else "in_memory",
        "total_resumes": len(resumes_storage),
        "upload_directory": UPLOAD_DIR,
        "supported_formats": list(ALLOWED_EXTENSIONS),
        "max_file_size_mb": MAX_FILE_SIZE // (1024 * 1024),
        "features": [
            "File upload (PDF, DOCX, TXT)",
            "Text extraction",
            "Skill extraction",
            "Resume matching",
            "Bulk upload",
            "Statistics"
        ]
    }
