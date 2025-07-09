"""
Resume processing service for extracting and analyzing resume content
"""

import os
import PyPDF2
import docx
from typing import Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from ..models.resume import Resume
from ..models.job import Job
from ..core.config import settings
from .ai_service import analyze_resume_with_ai, match_candidates_with_ai

async def process_resume(resume_id: int, db: Session) -> bool:
    """Process resume to extract information"""
    
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        return False
    
    try:
        # Update status to processing
        resume.processing_status = "processing"
        db.commit()
        
        # Extract text from file
        extracted_text = extract_text_from_file(resume.file_path, resume.file_type)
        
        if not extracted_text:
            raise Exception("Could not extract text from file")
        
        # Store extracted text
        resume.extracted_text = extracted_text
        
        # Use AI to extract structured information
        ai_extracted = await analyze_resume_with_ai(extracted_text)
        
        if ai_extracted:
            resume.candidate_name = ai_extracted.get("candidate_name")
            resume.candidate_email = ai_extracted.get("candidate_email")
            resume.candidate_phone = ai_extracted.get("candidate_phone")
            resume.skills = ai_extracted.get("skills", [])
            resume.experience = ai_extracted.get("experience", [])
            resume.education = ai_extracted.get("education", [])
            resume.certifications = ai_extracted.get("certifications", [])
            resume.ai_summary = ai_extracted.get("summary")
        
        # Mark as processed
        resume.is_processed = True
        resume.processing_status = "completed"
        resume.processed_at = datetime.utcnow()
        resume.processing_error = None
        
        db.commit()
        return True
        
    except Exception as e:
        # Mark as failed
        resume.processing_status = "failed"
        resume.processing_error = str(e)
        db.commit()
        return False

def extract_text_from_file(file_path: str, file_type: str) -> str:
    """Extract text from different file types"""
    
    try:
        if file_type == "pdf":
            return extract_text_from_pdf(file_path)
        elif file_type == "docx":
            return extract_text_from_docx(file_path)
        elif file_type == "doc":
            # For .doc files, we'd need python-docx2txt or similar
            # For now, return empty string
            return ""
        elif file_type == "txt":
            return extract_text_from_txt(file_path)
        else:
            return ""
    except Exception as e:
        print(f"Error extracting text from {file_path}: {e}")
        return ""

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF file"""
    
    text = ""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
    
    return text.strip()

def extract_text_from_docx(file_path: str) -> str:
    """Extract text from DOCX file"""
    
    text = ""
    try:
        doc = docx.Document(file_path)
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
    except Exception as e:
        print(f"Error reading DOCX {file_path}: {e}")
    
    return text.strip()

def extract_text_from_txt(file_path: str) -> str:
    """Extract text from TXT file"""
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading TXT {file_path}: {e}")
        return ""

async def match_resume_to_job(resume: Resume, job: Job) -> Dict[str, Any]:
    """Match resume to job and return detailed analysis"""
    
    if not resume.is_processed:
        raise Exception("Resume is not processed yet")
    
    # Use AI to calculate match score
    job_requirements = [job.title, job.description] + (job.requirements or [])
    match_result = await analyze_resume_with_ai(resume.extracted_text, job_requirements)
    
    # Extract match score from analysis
    if match_result and match_result.get('analysis'):
        return {
            "match_score": match_result['analysis'].get('match_score', 0.5),
            "provider": match_result.get('provider', 'offline'),
            "analysis": match_result['analysis']
        }
    
    return {"match_score": 0.5, "provider": "offline", "analysis": {}}

def get_resume_statistics(resume: Resume) -> Dict[str, Any]:
    """Get statistical information about resume"""
    
    stats = {
        "file_size_mb": round(resume.file_size / (1024 * 1024), 2),
        "text_length": len(resume.extracted_text or ""),
        "skills_count": len(resume.skills or []),
        "experience_count": len(resume.experience or []),
        "education_count": len(resume.education or []),
        "certifications_count": len(resume.certifications or []),
        "processing_time": None
    }
    
    if resume.processed_at and resume.created_at:
        processing_time = resume.processed_at - resume.created_at
        stats["processing_time"] = processing_time.total_seconds()
    
    return stats

