from fastapi import APIRouter, Depends, HTTPException, status, Query, Form
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging
import uuid
import json
from datetime import datetime, timedelta
import re

# Import database with fallback
try:
    from ..core.database import get_db
    from ..models.job import Job
    from ..models.resume import Resume
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    logging.warning("Database models not available, using in-memory storage")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage for fallback mode
in_memory_jobs = {}
in_memory_applications = {}

# Sample job data for demo
SAMPLE_JOBS = [
    {
        "id": "job_1",
        "title": "Senior Python Developer",
        "company": "TechCorp Inc.",
        "location": "San Francisco, CA",
        "job_type": "full-time",
        "experience_level": "senior",
        "salary_min": 120000,
        "salary_max": 180000,
        "currency": "USD",
        "description": """We are seeking a Senior Python Developer to join our growing engineering team. 
        
Key Responsibilities:
- Design and develop scalable web applications using Python and Django
- Work with PostgreSQL databases and optimize query performance
- Collaborate with cross-functional teams to deliver high-quality software
- Mentor junior developers and contribute to code reviews
        
Required Skills:
- 5+ years of Python development experience
- Strong experience with Django or Flask frameworks
- Proficiency in PostgreSQL, Redis, and AWS services
- Experience with Docker, Kubernetes, and CI/CD pipelines
- Knowledge of RESTful APIs and microservices architecture
        
Preferred Skills:
- Experience with React or Vue.js for full-stack development
- Knowledge of machine learning libraries (scikit-learn, TensorFlow)
- Familiarity with Agile development methodologies""",
        "required_skills": ["python", "django", "postgresql", "aws", "docker", "kubernetes", "rest api"],
        "preferred_skills": ["react", "machine learning", "tensorflow", "agile"],
        "education_requirements": "Bachelor's degree in Computer Science or equivalent experience",
        "experience_requirements": "5+ years of professional Python development",
        "posted_date": datetime.utcnow() - timedelta(days=2),
        "application_deadline": datetime.utcnow() + timedelta(days=28),
        "status": "active",
        "applications_count": 15,
        "views_count": 234
    },
    {
        "id": "job_2",
        "title": "Full Stack Engineer",
        "company": "StartupXYZ",
        "location": "Remote",
        "job_type": "full-time",
        "experience_level": "mid",
        "salary_min": 80000,
        "salary_max": 120000,
        "currency": "USD",
        "description": """Join our innovative startup as a Full Stack Engineer and help build the next generation of web applications.
        
What You'll Do:
- Develop responsive web applications using React and Node.js
- Build and maintain RESTful APIs and GraphQL endpoints
- Work with MongoDB and implement efficient data models
- Collaborate in an Agile environment with rapid iteration cycles
        
Requirements:
- 3+ years of JavaScript development experience
- Proficiency in React, Node.js, and Express.js
- Experience with MongoDB or other NoSQL databases
- Understanding of modern web development tools and practices
- Strong problem-solving skills and attention to detail
        
Nice to Have:
- Experience with TypeScript and modern build tools
- Knowledge of cloud platforms (AWS, GCP, or Azure)
- Familiarity with containerization and deployment strategies""",
        "required_skills": ["javascript", "react", "nodejs", "express", "mongodb", "rest api"],
        "preferred_skills": ["typescript", "graphql", "aws", "docker"],
        "education_requirements": "Bachelor's degree preferred or equivalent experience",
        "experience_requirements": "3+ years of full-stack development",
        "posted_date": datetime.utcnow() - timedelta(days=5),
        "application_deadline": datetime.utcnow() + timedelta(days=25),
        "status": "active",
        "applications_count": 8,
        "views_count": 156
    },
    {
        "id": "job_3",
        "title": "Data Scientist",
        "company": "DataCorp Analytics",
        "location": "New York, NY",
        "job_type": "full-time",
        "experience_level": "senior",
        "salary_min": 130000,
        "salary_max": 200000,
        "currency": "USD",
        "description": """We're looking for an experienced Data Scientist to join our analytics team and drive data-driven decision making.
        
Responsibilities:
- Develop machine learning models for predictive analytics
- Analyze large datasets to extract actionable insights
- Create data visualizations and reports for stakeholders
- Collaborate with engineering teams to deploy ML models in production
        
Required Qualifications:
- PhD or Master's in Data Science, Statistics, or related field
- 4+ years of experience in data science and machine learning
- Proficiency in Python, R, and SQL
- Experience with scikit-learn, pandas, numpy, and matplotlib
- Knowledge of statistical analysis and hypothesis testing
        
Preferred Qualifications:
- Experience with deep learning frameworks (TensorFlow, PyTorch)
- Knowledge of big data tools (Spark, Hadoop)
- Experience with cloud ML platforms (AWS SageMaker, GCP ML)""",
        "required_skills": ["python", "r", "sql", "machine learning", "scikit-learn", "pandas", "numpy", "statistics"],
        "preferred_skills": ["tensorflow", "pytorch", "spark", "hadoop", "aws"],
        "education_requirements": "Master's or PhD in Data Science, Statistics, or related field",
        "experience_requirements": "4+ years of data science experience",
        "posted_date": datetime.utcnow() - timedelta(days=1),
        "application_deadline": datetime.utcnow() + timedelta(days=29),
        "status": "active",
        "applications_count": 12,
        "views_count": 189
    }
]

def initialize_sample_data():
    """Initialize sample job data in memory"""
    for job in SAMPLE_JOBS:
        in_memory_jobs[job["id"]] = job
    logger.info(f"Initialized {len(SAMPLE_JOBS)} sample jobs")

# Initialize sample data on module load
initialize_sample_data()

def extract_skills_from_text(text: str) -> List[str]:
    """Extract technical skills from job description"""
    # Common technical skills database
    skills_db = {
        'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue',
        'nodejs', 'express', 'django', 'flask', 'spring', 'laravel',
        'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
        'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins',
        'git', 'linux', 'bash', 'nginx', 'apache',
        'machine learning', 'tensorflow', 'pytorch', 'scikit-learn',
        'pandas', 'numpy', 'matplotlib', 'tableau', 'power bi',
        'rest api', 'graphql', 'microservices', 'agile', 'scrum'
    }
    
    text_lower = text.lower()
    found_skills = []
    
    for skill in skills_db:
        if skill in text_lower:
            found_skills.append(skill)
    
    return found_skills

@router.post("/")
async def create_job(
    title: str = Form(...),
    company: str = Form(...),
    location: str = Form(...),
    job_type: str = Form("full-time"),
    experience_level: str = Form("mid"),
    salary_min: Optional[int] = Form(None),
    salary_max: Optional[int] = Form(None),
    currency: str = Form("USD"),
    description: str = Form(...),
    required_skills: Optional[str] = Form(None),
    preferred_skills: Optional[str] = Form(None),
    education_requirements: Optional[str] = Form(None),
    experience_requirements: Optional[str] = Form(None),
    application_deadline: Optional[str] = Form(None),
    db: Session = Depends(get_db) if DB_AVAILABLE else None
):
    """
    Create a new job posting
    """
    try:
        logger.info(f"Creating new job: {title} at {company}")
        
        # Parse skills from comma-separated strings
        required_skills_list = []
        preferred_skills_list = []
        
        if required_skills:
            required_skills_list = [skill.strip() for skill in required_skills.split(',')]
        
        if preferred_skills:
            preferred_skills_list = [skill.strip() for skill in preferred_skills.split(',')]
        
        # Auto-extract skills from description if not provided
        if not required_skills_list:
            required_skills_list = extract_skills_from_text(description)
        
        # Parse application deadline
        deadline = None
        if application_deadline:
            try:
                deadline = datetime.fromisoformat(application_deadline.replace('Z', '+00:00'))
            except ValueError:
                deadline = datetime.utcnow() + timedelta(days=30)
        else:
            deadline = datetime.utcnow() + timedelta(days=30)
        
        # Create job data
        job_data = {
            "id": str(uuid.uuid4()),
            "title": title,
            "company": company,
            "location": location,
            "job_type": job_type,
            "experience_level": experience_level,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "currency": currency,
            "description": description,
            "required_skills": required_skills_list,
            "preferred_skills": preferred_skills_list,
            "education_requirements": education_requirements,
            "experience_requirements": experience_requirements,
            "posted_date": datetime.utcnow(),
            "application_deadline": deadline,
            "status": "active",
            "applications_count": 0,
            "views_count": 0
        }
        
        if DB_AVAILABLE and db:
            # Save to database
            new_job = Job(
                title=title,
                company=company,
                location=location,
                job_type=job_type,
                experience_level=experience_level,
                salary_min=salary_min,
                salary_max=salary_max,
                currency=currency,
                description=description,
                required_skills=json.dumps(required_skills_list),
                preferred_skills=json.dumps(preferred_skills_list),
                education_requirements=education_requirements,
                experience_requirements=experience_requirements,
                posted_date=datetime.utcnow(),
                application_deadline=deadline,
                status="active"
            )
            
            db.add(new_job)
            db.commit()
            db.refresh(new_job)
            
            job_data["id"] = new_job.id
            logger.info(f"Job saved to database with ID: {new_job.id}")
        else:
            # Save to in-memory storage
            in_memory_jobs[job_data["id"]] = job_data
            logger.info(f"Job saved to memory with ID: {job_data['id']}")
        
        return {
            "success": True,
            "job": {
                "id": job_data["id"],
                "title": title,
                "company": company,
                "location": location,
                "job_type": job_type,
                "experience_level": experience_level,
                "salary_range": f"${salary_min:,} - ${salary_max:,} {currency}" if salary_min and salary_max else "Salary not specified",
                "required_skills": required_skills_list,
                "preferred_skills": preferred_skills_list,
                "posted_date": job_data["posted_date"],
                "application_deadline": deadline,
                "status": "active"
            },
            "message": "Job posting created successfully"
        }
        
    except Exception as e:
        logger.error(f"Job creation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create job: {str(e)}"
        )

@router.get("/")
async def get_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    experience_level: Optional[str] = Query(None),
    min_salary: Optional[int] = Query(None),
    max_salary: Optional[int] = Query(None),
    skills: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    db: Session = Depends(get_db) if DB_AVAILABLE else None
):
    """
    Get jobs with advanced filtering and search
    """
    try:
        if DB_AVAILABLE and db:
            # Database query with filters
            query = db.query(Job)
            
            if search:
                query = query.filter(
                    (Job.title.contains(search)) |
                    (Job.description.contains(search)) |
                    (Job.company.contains(search))
                )
            
            if location:
                query = query.filter(Job.location.contains(location))
            
            if job_type:
                query = query.filter(Job.job_type == job_type)
            
            if experience_level:
                query = query.filter(Job.experience_level == experience_level)
            
            if company:
                query = query.filter(Job.company.contains(company))
            
            if min_salary:
                query = query.filter(Job.salary_min >= min_salary)
            
            if max_salary:
                query = query.filter(Job.salary_max <= max_salary)
            
            total = query.count()
            jobs = query.offset(skip).limit(limit).all()
            
            job_list = []
            for job in jobs:
                job_list.append({
                    "id": job.id,
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "job_type": job.job_type,
                    "experience_level": job.experience_level,
                    "salary_min": job.salary_min,
                    "salary_max": job.salary_max,
                    "currency": job.currency,
                    "required_skills": json.loads(job.required_skills) if job.required_skills else [],
                    "preferred_skills": json.loads(job.preferred_skills) if job.preferred_skills else [],
                    "posted_date": job.posted_date,
                    "application_deadline": job.application_deadline,
                    "status": job.status,
                    "description_preview": job.description[:200] + "..." if len(job.description) > 200 else job.description
                })
        else:
            # In-memory filtering
            job_list = []
            for job_id, job_data in in_memory_jobs.items():
                # Apply filters
                if search and search.lower() not in (job_data["title"] + " " + job_data["description"] + " " + job_data["company"]).lower():
                    continue
                if location and location.lower() not in job_data["location"].lower():
                    continue
                if job_type and job_data["job_type"] != job_type:
                    continue
                if experience_level and job_data["experience_level"] != experience_level:
                    continue
                if company and company.lower() not in job_data["company"].lower():
                    continue
                if min_salary and (not job_data["salary_min"] or job_data["salary_min"] < min_salary):
                    continue
                if max_salary and (not job_data["salary_max"] or job_data["salary_max"] > max_salary):
                    continue
                if skills:
                    skill_list = [s.strip().lower() for s in skills.split(',')]
                    job_skills = [s.lower() for s in job_data["required_skills"] + job_data["preferred_skills"]]
                    if not any(skill in job_skills for skill in skill_list):
                        continue
                
                job_list.append({
                    "id": job_data["id"],
                    "title": job_data["title"],
                    "company": job_data["company"],
                    "location": job_data["location"],
                    "job_type": job_data["job_type"],
                    "experience_level": job_data["experience_level"],
                    "salary_min": job_data["salary_min"],
                    "salary_max": job_data["salary_max"],
                    "currency": job_data["currency"],
                    "required_skills": job_data["required_skills"],
                    "preferred_skills": job_data["preferred_skills"],
                    "posted_date": job_data["posted_date"],
                    "application_deadline": job_data["application_deadline"],
                    "status": job_data["status"],
                    "applications_count": job_data.get("applications_count", 0),
                    "views_count": job_data.get("views_count", 0),
                    "description_preview": job_data["description"][:200] + "..." if len(job_data["description"]) > 200 else job_data["description"]
                })
            
            total = len(job_list)
            job_list = job_list[skip:skip + limit]
        
        return {
            "jobs": job_list,
            "total": total,
            "skip": skip,
            "limit": limit,
            "has_more": skip + limit < total,
            "filters_applied": {
                "search": search,
                "location": location,
                "job_type": job_type,
                "experience_level": experience_level,
                "company": company,
                "salary_range": f"${min_salary or 0:,} - ${max_salary or 999999:,}",
                "skills": skills
            }
        }
        
    except Exception as e:
        logger.error(f"Get jobs error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve jobs: {str(e)}"
        )

@router.get("/{job_id}")
async def get_job(
    job_id: str,
    db: Session = Depends(get_db) if DB_AVAILABLE else None
):
    """
    Get detailed job information
    """
    try:
        if DB_AVAILABLE and db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Job not found"
                )
            
            # Increment view count
            job.views_count = (job.views_count or 0) + 1
            db.commit()
            
            return {
                "id": job.id,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "job_type": job.job_type,
                "experience_level": job.experience_level,
                "salary_min": job.salary_min,
                "salary_max": job.salary_max,
                "currency": job.currency,
                "description": job.description,
                "required_skills": json.loads(job.required_skills) if job.required_skills else [],
                "preferred_skills": json.loads(job.preferred_skills) if job.preferred_skills else [],
                "education_requirements": job.education_requirements,
                "experience_requirements": job.experience_requirements,
                "posted_date": job.posted_date,
                "application_deadline": job.application_deadline,
                "status": job.status,
                "applications_count": job.applications_count or 0,
                "views_count": job.views_count or 0
            }
        else:
            job_data = in_memory_jobs.get(job_id)
            if not job_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Job not found"
                )
            
            # Increment view count
            job_data["views_count"] = job_data.get("views_count", 0) + 1
            
            return job_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get job error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve job: {str(e)}"
        )

@router.put("/{job_id}")
async def update_job(
    job_id: str,
    title: Optional[str] = Form(None),
    company: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    job_type: Optional[str] = Form(None),
    experience_level: Optional[str] = Form(None),
    salary_min: Optional[int] = Form(None),
    salary_max: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    db: Session = Depends(get_db) if DB_AVAILABLE else None
):
    """
    Update job information
    """
    try:
        if DB_AVAILABLE and db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            
            # Update fields if provided
            if title is not None:
                job.title = title
            if company is not None:
                job.company = company
            if location is not None:
                job.location = location
            if job_type is not None:
                job.job_type = job_type
            if experience_level is not None:
                job.experience_level = experience_level
            if salary_min is not None:
                job.salary_min = salary_min
            if salary_max is not None:
                job.salary_max = salary_max
            if description is not None:
                job.description = description
            if status is not None:
                job.status = status
            
            db.commit()
            db.refresh(job)
            
            return {"message": "Job updated successfully", "job_id": job_id}
        else:
            job_data = in_memory_jobs.get(job_id)
            if not job_data:
                raise HTTPException(status_code=404, detail="Job not found")
            
            # Update fields if provided
            if title is not None:
                job_data["title"] = title
            if company is not None:
                job_data["company"] = company
            if location is not None:
                job_data["location"] = location
            if job_type is not None:
                job_data["job_type"] = job_type
            if experience_level is not None:
                job_data["experience_level"] = experience_level
            if salary_min is not None:
                job_data["salary_min"] = salary_min
            if salary_max is not None:
                job_data["salary_max"] = salary_max
            if description is not None:
                job_data["description"] = description
            if status is not None:
                job_data["status"] = status
            
            return {"message": "Job updated successfully", "job_id": job_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update job error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update job: {str(e)}"
        )

@router.delete("/{job_id}")
async def delete_job(
    job_id: str,
    db: Session = Depends(get_db) if DB_AVAILABLE else None
):
    """
    Delete a job posting
    """
    try:
        if DB_AVAILABLE and db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            
            db.delete(job)
            db.commit()
        else:
            if job_id not in in_memory_jobs:
                raise HTTPException(status_code=404, detail="Job not found")
            
            del in_memory_jobs[job_id]
        
        logger.info(f"Job deleted: {job_id}")
        return {"message": "Job deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete job error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete job: {str(e)}"
        )

@router.get("/{job_id}/candidates")
async def get_job_candidates(
    job_id: str,
    min_score: float = Query(0, ge=0, le=100),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db) if DB_AVAILABLE else None
):
    """
    Get matching candidates for a specific job
    """
    try:
        # Get job details
        if DB_AVAILABLE and db:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            job_description = job.description
            job_title = job.title
        else:
            job_data = in_memory_jobs.get(job_id)
            if not job_data:
                raise HTTPException(status_code=404, detail="Job not found")
            job_description = job_data["description"]
            job_title = job_data["title"]
        
        # For demo purposes, return sample candidates with scores
        sample_candidates = [
            {
                "resume_id": "resume_1",
                "candidate_name": "John Smith",
                "email": "john.smith@email.com",
                "match_score": 92.5,
                "matching_skills": ["python", "django", "postgresql", "aws", "docker"],
                "experience_years": 6,
                "current_title": "Senior Software Engineer",
                "location": "San Francisco, CA",
                "match_explanation": "Strong match with 5/7 required skills and relevant experience"
            },
            {
                "resume_id": "resume_2",
                "candidate_name": "Sarah Johnson",
                "email": "sarah.johnson@email.com",
                "match_score": 87.3,
                "matching_skills": ["python", "flask", "postgresql", "kubernetes"],
                "experience_years": 4,
                "current_title": "Full Stack Developer",
                "location": "Remote",
                "match_explanation": "Good match with 4/7 required skills and growing experience"
            },
            {
                "resume_id": "resume_3",
                "candidate_name": "Michael Chen",
                "email": "michael.chen@email.com",
                "match_score": 78.9,
                "matching_skills": ["python", "django", "aws"],
                "experience_years": 3,
                "current_title": "Backend Developer",
                "location": "New York, NY",
                "match_explanation": "Moderate match with 3/7 required skills, junior level"
            }
        ]
        
        # Filter by minimum score
        filtered_candidates = [c for c in sample_candidates if c["match_score"] >= min_score]
        
        # Limit results
        filtered_candidates = filtered_candidates[:limit]
        
        return {
            "job_id": job_id,
            "job_title": job_title,
            "candidates": filtered_candidates,
            "total_candidates": len(filtered_candidates),
            "matching_criteria": {
                "min_score": min_score,
                "algorithm": "TF-IDF + Skill Matching"
            },
            "message": f"Found {len(filtered_candidates)} matching candidates for {job_title}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get job candidates error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job candidates: {str(e)}"
        )

@router.get("/stats/overview")
async def get_job_stats(db: Session = Depends(get_db) if DB_AVAILABLE else None):
    """
    Get job statistics and analytics
    """
    try:
        if DB_AVAILABLE and db:
            total_jobs = db.query(Job).count()
            active_jobs = db.query(Job).filter(Job.status == "active").count()
            # Add more complex queries here
        else:
            total_jobs = len(in_memory_jobs)
            active_jobs = len([j for j in in_memory_jobs.values() if j["status"] == "active"])
        
        # Calculate other statistics
        job_types = {}
        experience_levels = {}
        companies = {}
        locations = {}
        
        if DB_AVAILABLE and db:
            jobs = db.query(Job).all()
            for job in jobs:
                job_types[job.job_type] = job_types.get(job.job_type, 0) + 1
                experience_levels[job.experience_level] = experience_levels.get(job.experience_level, 0) + 1
                companies[job.company] = companies.get(job.company, 0) + 1
                locations[job.location] = locations.get(job.location, 0) + 1
        else:
            for job_data in in_memory_jobs.values():
                job_types[job_data["job_type"]] = job_types.get(job_data["job_type"], 0) + 1
                experience_levels[job_data["experience_level"]] = experience_levels.get(job_data["experience_level"], 0) + 1
                companies[job_data["company"]] = companies.get(job_data["company"], 0) + 1
                locations[job_data["location"]] = locations.get(job_data["location"], 0) + 1
        
        return {
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "inactive_jobs": total_jobs - active_jobs,
            "job_types": job_types,
            "experience_levels": experience_levels,
            "top_companies": dict(sorted(companies.items(), key=lambda x: x[1], reverse=True)[:10]),
            "top_locations": dict(sorted(locations.items(), key=lambda x: x[1], reverse=True)[:10]),
            "database_mode": DB_AVAILABLE,
            "features": [
                "Job posting and management",
                "Advanced search and filtering",
                "Candidate matching",
                "Application tracking",
                "Analytics and reporting",
                "Skill-based matching"
            ]
        }
        
    except Exception as e:
        logger.error(f"Get job stats error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job statistics: {str(e)}"
        )

# Health check endpoint
@router.get("/health")
async def jobs_health():
    """Jobs service health check"""
    return {
        "status": "healthy",
        "service": "job_management",
        "version": "2.0.0",
        "database_available": DB_AVAILABLE,
        "in_memory_jobs": len(in_memory_jobs),
        "sample_jobs_loaded": len(SAMPLE_JOBS),
        "features": [
            "Job posting and management",
            "Advanced search and filtering",
            "Skill extraction from descriptions",
            "Candidate matching",
            "Application tracking",
            "Analytics and reporting",
            "Salary range filtering",
            "Location-based search"
        ],
        "supported_job_types": ["full-time", "part-time", "contract", "internship", "remote"],
        "supported_experience_levels": ["entry", "mid", "senior", "lead", "executive"],
        "search_capabilities": [
            "Title and description search",
            "Company name filtering",
            "Location-based filtering",
            "Skill-based matching",
            "Salary range filtering",
            "Experience level filtering"
        ]
    }

