"""
Analytics service for dashboard metrics and reporting
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from ..models.user import User
from ..models.job import Job
from ..models.candidate import Candidate
from ..models.interview import Interview
from ..models.resume import Resume
from ..models.credit import Credit

async def get_dashboard_analytics(user_id: int, db: Session, days: int = 30) -> Dict[str, Any]:
    """Get comprehensive dashboard analytics for user"""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get user's jobs
    user_jobs = db.query(Job).filter(Job.owner_id == user_id).all()
    job_ids = [job.id for job in user_jobs]
    
    # Basic metrics
    total_jobs = len(user_jobs)
    active_jobs = len([job for job in user_jobs if job.is_active])
    published_jobs = len([job for job in user_jobs if job.is_published])
    
    # Candidate metrics
    total_candidates = db.query(Candidate).filter(Candidate.job_id.in_(job_ids)).count() if job_ids else 0
    qualified_candidates = db.query(Candidate).filter(
        and_(Candidate.job_id.in_(job_ids), Candidate.is_qualified == True)
    ).count() if job_ids else 0
    
    # Interview metrics
    total_interviews = db.query(Interview).filter(Interview.job_id.in_(job_ids)).count() if job_ids else 0
    completed_interviews = db.query(Interview).filter(
        and_(Interview.job_id.in_(job_ids), Interview.status == "completed")
    ).count() if job_ids else 0
    
    # Resume metrics
    total_resumes = db.query(Resume).filter(Resume.uploaded_by == user_id).count()
    processed_resumes = db.query(Resume).filter(
        and_(Resume.uploaded_by == user_id, Resume.is_processed == True)
    ).count()
    
    # Credit metrics
    latest_credit = db.query(Credit).filter(Credit.user_id == user_id).order_by(Credit.created_at.desc()).first()
    current_credits = latest_credit.balance_after if latest_credit else 0
    
    # Recent activity (last 30 days)
    recent_candidates = db.query(Candidate).filter(
        and_(
            Candidate.job_id.in_(job_ids) if job_ids else False,
            Candidate.application_date >= start_date
        )
    ).count() if job_ids else 0
    
    recent_interviews = db.query(Interview).filter(
        and_(
            Interview.job_id.in_(job_ids) if job_ids else False,
            Interview.created_at >= start_date
        )
    ).count() if job_ids else 0
    
    # Performance metrics
    avg_match_score = db.query(func.avg(Candidate.match_score)).filter(
        and_(
            Candidate.job_id.in_(job_ids) if job_ids else False,
            Candidate.match_score.isnot(None)
        )
    ).scalar() or 0.0
    
    avg_interview_score = db.query(func.avg(Interview.overall_score)).filter(
        and_(
            Interview.job_id.in_(job_ids) if job_ids else False,
            Interview.overall_score.isnot(None)
        )
    ).scalar() or 0.0
    
    return {
        "period_days": days,
        "jobs": {
            "total": total_jobs,
            "active": active_jobs,
            "published": published_jobs
        },
        "candidates": {
            "total": total_candidates,
            "qualified": qualified_candidates,
            "recent": recent_candidates,
            "qualification_rate": (qualified_candidates / total_candidates * 100) if total_candidates > 0 else 0
        },
        "interviews": {
            "total": total_interviews,
            "completed": completed_interviews,
            "recent": recent_interviews,
            "completion_rate": (completed_interviews / total_interviews * 100) if total_interviews > 0 else 0
        },
        "resumes": {
            "total": total_resumes,
            "processed": processed_resumes,
            "processing_rate": (processed_resumes / total_resumes * 100) if total_resumes > 0 else 0
        },
        "credits": {
            "current_balance": current_credits
        },
        "performance": {
            "avg_match_score": float(avg_match_score),
            "avg_interview_score": float(avg_interview_score)
        }
    }

async def get_hiring_funnel_analytics(user_id: int, db: Session, job_id: Optional[int] = None) -> Dict[str, Any]:
    """Get hiring funnel analytics"""
    
    # Get user's jobs
    if job_id:
        jobs = db.query(Job).filter(and_(Job.id == job_id, Job.owner_id == user_id)).all()
    else:
        jobs = db.query(Job).filter(Job.owner_id == user_id).all()
    
    job_ids = [job.id for job in jobs]
    
    if not job_ids:
        return {"stages": [], "conversion_rates": {}}
    
    # Funnel stages
    total_applications = db.query(Candidate).filter(Candidate.job_id.in_(job_ids)).count()
    qualified_candidates = db.query(Candidate).filter(
        and_(Candidate.job_id.in_(job_ids), Candidate.is_qualified == True)
    ).count()
    interviewed_candidates = db.query(Candidate).filter(
        and_(Candidate.job_id.in_(job_ids), Candidate.interview_completed == True)
    ).count()
    hired_candidates = db.query(Candidate).filter(
        and_(Candidate.job_id.in_(job_ids), Candidate.application_status == "hired")
    ).count()
    
    stages = [
        {"name": "Applications", "count": total_applications},
        {"name": "Qualified", "count": qualified_candidates},
        {"name": "Interviewed", "count": interviewed_candidates},
        {"name": "Hired", "count": hired_candidates}
    ]
    
    # Conversion rates
    conversion_rates = {
        "application_to_qualified": (qualified_candidates / total_applications * 100) if total_applications > 0 else 0,
        "qualified_to_interviewed": (interviewed_candidates / qualified_candidates * 100) if qualified_candidates > 0 else 0,
        "interviewed_to_hired": (hired_candidates / interviewed_candidates * 100) if interviewed_candidates > 0 else 0,
        "overall_conversion": (hired_candidates / total_applications * 100) if total_applications > 0 else 0
    }
    
    return {
        "stages": stages,
        "conversion_rates": conversion_rates
    }

async def get_time_series_analytics(user_id: int, db: Session, days: int = 30) -> Dict[str, Any]:
    """Get time series analytics for charts"""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get user's jobs
    user_jobs = db.query(Job).filter(Job.owner_id == user_id).all()
    job_ids = [job.id for job in user_jobs]
    
    # Daily applications
    daily_applications = db.query(
        func.date(Candidate.application_date).label('date'),
        func.count(Candidate.id).label('count')
    ).filter(
        and_(
            Candidate.job_id.in_(job_ids) if job_ids else False,
            Candidate.application_date >= start_date
        )
    ).group_by(func.date(Candidate.application_date)).all() if job_ids else []
    
    # Daily interviews
    daily_interviews = db.query(
        func.date(Interview.created_at).label('date'),
        func.count(Interview.id).label('count')
    ).filter(
        and_(
            Interview.job_id.in_(job_ids) if job_ids else False,
            Interview.created_at >= start_date
        )
    ).group_by(func.date(Interview.created_at)).all() if job_ids else []
    
    # Daily resume uploads
    daily_resumes = db.query(
        func.date(Resume.created_at).label('date'),
        func.count(Resume.id).label('count')
    ).filter(
        and_(
            Resume.uploaded_by == user_id,
            Resume.created_at >= start_date
        )
    ).group_by(func.date(Resume.created_at)).all()
    
    return {
        "period_days": days,
        "daily_applications": [
            {"date": str(item.date), "count": item.count}
            for item in daily_applications
        ],
        "daily_interviews": [
            {"date": str(item.date), "count": item.count}
            for item in daily_interviews
        ],
        "daily_resumes": [
            {"date": str(item.date), "count": item.count}
            for item in daily_resumes
        ]
    }

async def get_job_performance_analytics(user_id: int, db: Session) -> List[Dict[str, Any]]:
    """Get performance analytics for each job"""
    
    jobs = db.query(Job).filter(Job.owner_id == user_id).all()
    
    job_analytics = []
    for job in jobs:
        # Candidate metrics
        total_candidates = db.query(Candidate).filter(Candidate.job_id == job.id).count()
        qualified_candidates = db.query(Candidate).filter(
            and_(Candidate.job_id == job.id, Candidate.is_qualified == True)
        ).count()
        interviewed_candidates = db.query(Candidate).filter(
            and_(Candidate.job_id == job.id, Candidate.interview_completed == True)
        ).count()
        hired_candidates = db.query(Candidate).filter(
            and_(Candidate.job_id == job.id, Candidate.application_status == "hired")
        ).count()
        
        # Average scores
        avg_match_score = db.query(func.avg(Candidate.match_score)).filter(
            and_(Candidate.job_id == job.id, Candidate.match_score.isnot(None))
        ).scalar() or 0.0
        
        avg_interview_score = db.query(func.avg(Interview.overall_score)).filter(
            and_(Interview.job_id == job.id, Interview.overall_score.isnot(None))
        ).scalar() or 0.0
        
        job_analytics.append({
            "job_id": job.id,
            "job_title": job.title,
            "job_type": job.job_type,
            "experience_level": job.experience_level,
            "is_active": job.is_active,
            "is_published": job.is_published,
            "created_at": job.created_at,
            "metrics": {
                "total_candidates": total_candidates,
                "qualified_candidates": qualified_candidates,
                "interviewed_candidates": interviewed_candidates,
                "hired_candidates": hired_candidates,
                "qualification_rate": (qualified_candidates / total_candidates * 100) if total_candidates > 0 else 0,
                "interview_rate": (interviewed_candidates / qualified_candidates * 100) if qualified_candidates > 0 else 0,
                "hire_rate": (hired_candidates / interviewed_candidates * 100) if interviewed_candidates > 0 else 0,
                "avg_match_score": float(avg_match_score),
                "avg_interview_score": float(avg_interview_score)
            }
        })
    
    return job_analytics

async def get_admin_analytics(db: Session) -> Dict[str, Any]:
    """Get system-wide analytics for admin dashboard"""
    
    # User metrics
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    admin_users = db.query(User).filter(User.role == "admin").count()
    
    # Job metrics
    total_jobs = db.query(Job).count()
    active_jobs = db.query(Job).filter(Job.is_active == True).count()
    published_jobs = db.query(Job).filter(Job.is_published == True).count()
    
    # Candidate metrics
    total_candidates = db.query(Candidate).count()
    qualified_candidates = db.query(Candidate).filter(Candidate.is_qualified == True).count()
    
    # Interview metrics
    total_interviews = db.query(Interview).count()
    completed_interviews = db.query(Interview).filter(Interview.status == "completed").count()
    
    # Resume metrics
    total_resumes = db.query(Resume).count()
    processed_resumes = db.query(Resume).filter(Resume.is_processed == True).count()
    
    # Credit metrics
    total_credits_issued = db.query(func.sum(Credit.amount)).filter(Credit.amount > 0).scalar() or 0
    total_credits_used = abs(db.query(func.sum(Credit.amount)).filter(Credit.amount < 0).scalar() or 0)
    total_revenue = db.query(func.sum(Credit.amount_paid)).filter(Credit.amount_paid.isnot(None)).scalar() or 0.0
    
    # Recent activity (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    new_users_week = db.query(User).filter(User.created_at >= week_ago).count()
    new_jobs_week = db.query(Job).filter(Job.created_at >= week_ago).count()
    new_candidates_week = db.query(Candidate).filter(Candidate.application_date >= week_ago).count()
    
    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "admin": admin_users,
            "new_this_week": new_users_week
        },
        "jobs": {
            "total": total_jobs,
            "active": active_jobs,
            "published": published_jobs,
            "new_this_week": new_jobs_week
        },
        "candidates": {
            "total": total_candidates,
            "qualified": qualified_candidates,
            "qualification_rate": (qualified_candidates / total_candidates * 100) if total_candidates > 0 else 0,
            "new_this_week": new_candidates_week
        },
        "interviews": {
            "total": total_interviews,
            "completed": completed_interviews,
            "completion_rate": (completed_interviews / total_interviews * 100) if total_interviews > 0 else 0
        },
        "resumes": {
            "total": total_resumes,
            "processed": processed_resumes,
            "processing_rate": (processed_resumes / total_resumes * 100) if total_resumes > 0 else 0
        },
        "credits": {
            "total_issued": int(total_credits_issued),
            "total_used": int(total_credits_used),
            "total_revenue": float(total_revenue)
        }
    }

