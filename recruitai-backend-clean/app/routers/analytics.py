"""
Analytics router for dashboard metrics and reporting
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from ..core.database import get_db
from ..core.security import get_current_active_user, get_admin_user
from ..models.user import User
from ..services.analytics_service import (
    get_dashboard_analytics, get_hiring_funnel_analytics,
    get_time_series_analytics, get_job_performance_analytics,
    get_admin_analytics
)

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard_metrics(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive dashboard analytics for current user"""
    
    analytics = await get_dashboard_analytics(current_user.id, db, days)
    return analytics

@router.get("/hiring-funnel")
async def get_hiring_funnel(
    job_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get hiring funnel analytics"""
    
    funnel = await get_hiring_funnel_analytics(current_user.id, db, job_id)
    return funnel

@router.get("/time-series")
async def get_time_series(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get time series analytics for charts"""
    
    time_series = await get_time_series_analytics(current_user.id, db, days)
    return time_series

@router.get("/job-performance")
async def get_job_performance(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get performance analytics for each job"""
    
    job_analytics = await get_job_performance_analytics(current_user.id, db)
    return {"jobs": job_analytics}

@router.get("/summary")
async def get_analytics_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get quick analytics summary for current user"""
    
    # Get basic metrics
    analytics = await get_dashboard_analytics(current_user.id, db, 30)
    
    # Extract key metrics for summary
    summary = {
        "total_jobs": analytics["jobs"]["total"],
        "active_jobs": analytics["jobs"]["active"],
        "total_candidates": analytics["candidates"]["total"],
        "qualified_candidates": analytics["candidates"]["qualified"],
        "total_interviews": analytics["interviews"]["total"],
        "completed_interviews": analytics["interviews"]["completed"],
        "current_credits": analytics["credits"]["current_balance"],
        "avg_match_score": analytics["performance"]["avg_match_score"],
        "avg_interview_score": analytics["performance"]["avg_interview_score"]
    }
    
    return summary

# Admin analytics endpoints
@router.get("/admin/overview")
async def get_admin_overview(
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get system-wide analytics overview (admin only)"""
    
    analytics = await get_admin_analytics(db)
    return analytics

@router.get("/admin/user-activity")
async def get_user_activity_analytics(
    days: int = Query(30, ge=1, le=365),
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get user activity analytics (admin only)"""
    
    from datetime import datetime, timedelta
    from sqlalchemy import func, and_
    from ..models.user import User
    from ..models.job import Job
    from ..models.candidate import Candidate
    from ..models.interview import Interview
    from ..models.resume import Resume
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Daily user registrations
    daily_registrations = db.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('count')
    ).filter(
        User.created_at >= start_date
    ).group_by(func.date(User.created_at)).all()
    
    # Daily job postings
    daily_jobs = db.query(
        func.date(Job.created_at).label('date'),
        func.count(Job.id).label('count')
    ).filter(
        Job.created_at >= start_date
    ).group_by(func.date(Job.created_at)).all()
    
    # Daily applications
    daily_applications = db.query(
        func.date(Candidate.application_date).label('date'),
        func.count(Candidate.id).label('count')
    ).filter(
        Candidate.application_date >= start_date
    ).group_by(func.date(Candidate.application_date)).all()
    
    # Most active users
    active_users = db.query(
        User.id,
        User.username,
        User.email,
        func.count(Job.id).label('job_count')
    ).join(Job, User.id == Job.owner_id).group_by(
        User.id, User.username, User.email
    ).order_by(func.count(Job.id).desc()).limit(10).all()
    
    return {
        "period_days": days,
        "daily_registrations": [
            {"date": str(item.date), "count": item.count}
            for item in daily_registrations
        ],
        "daily_jobs": [
            {"date": str(item.date), "count": item.count}
            for item in daily_jobs
        ],
        "daily_applications": [
            {"date": str(item.date), "count": item.count}
            for item in daily_applications
        ],
        "most_active_users": [
            {
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "job_count": user.job_count
            }
            for user in active_users
        ]
    }

@router.get("/admin/system-health")
async def get_system_health_metrics(
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get system health metrics (admin only)"""
    
    from sqlalchemy import func, and_
    from ..models.resume import Resume
    from ..models.interview import Interview
    from ..models.credit import Credit
    
    # Resume processing health
    total_resumes = db.query(Resume).count()
    processed_resumes = db.query(Resume).filter(Resume.is_processed == True).count()
    failed_resumes = db.query(Resume).filter(Resume.processing_status == "failed").count()
    pending_resumes = db.query(Resume).filter(Resume.processing_status == "pending").count()
    
    # Interview completion health
    total_interviews = db.query(Interview).count()
    completed_interviews = db.query(Interview).filter(Interview.status == "completed").count()
    cancelled_interviews = db.query(Interview).filter(Interview.status == "cancelled").count()
    
    # Credit system health
    total_transactions = db.query(Credit).count()
    failed_transactions = db.query(Credit).filter(Credit.status == "failed").count()
    
    # Error rates
    resume_error_rate = (failed_resumes / total_resumes * 100) if total_resumes > 0 else 0
    interview_cancellation_rate = (cancelled_interviews / total_interviews * 100) if total_interviews > 0 else 0
    transaction_error_rate = (failed_transactions / total_transactions * 100) if total_transactions > 0 else 0
    
    return {
        "resume_processing": {
            "total": total_resumes,
            "processed": processed_resumes,
            "failed": failed_resumes,
            "pending": pending_resumes,
            "error_rate": resume_error_rate,
            "health_status": "healthy" if resume_error_rate < 5 else "warning" if resume_error_rate < 15 else "critical"
        },
        "interviews": {
            "total": total_interviews,
            "completed": completed_interviews,
            "cancelled": cancelled_interviews,
            "cancellation_rate": interview_cancellation_rate,
            "health_status": "healthy" if interview_cancellation_rate < 10 else "warning" if interview_cancellation_rate < 25 else "critical"
        },
        "credit_system": {
            "total_transactions": total_transactions,
            "failed_transactions": failed_transactions,
            "error_rate": transaction_error_rate,
            "health_status": "healthy" if transaction_error_rate < 1 else "warning" if transaction_error_rate < 5 else "critical"
        },
        "overall_health": "healthy"  # Could be calculated based on individual health statuses
    }

