"""
Credits router for credit management and transactions
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, timedelta

from ..core.database import get_db
from ..core.security import get_current_active_user, get_admin_user
from ..core.config import settings
from ..models.user import User
from ..models.credit import Credit
from ..schemas.credit import (
    CreditResponse, CreditBalance, CreditPurchase, 
    CreditUsage, CreditStats
)
from ..services.credit_service import (
    get_user_credit_balance, add_credits, deduct_credits,
    get_credit_history, get_credit_statistics, process_credit_purchase
)

router = APIRouter()

@router.get("/balance", response_model=CreditBalance)
async def get_credit_balance(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's credit balance"""
    
    stats = await get_credit_statistics(current_user.id, db)
    
    return CreditBalance(
        user_id=current_user.id,
        current_balance=stats["current_balance"],
        total_earned=stats["total_earned"],
        total_spent=stats["total_spent"],
        last_transaction=stats["last_transaction"]
    )

@router.get("/history", response_model=List[CreditResponse])
async def get_credit_transaction_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    transaction_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get credit transaction history for current user"""
    
    query = db.query(Credit).filter(Credit.user_id == current_user.id)
    
    if transaction_type:
        query = query.filter(Credit.transaction_type == transaction_type)
    
    credits = query.order_by(Credit.created_at.desc()).offset(skip).limit(limit).all()
    return credits

@router.post("/purchase", response_model=CreditResponse)
async def purchase_credits(
    purchase_data: CreditPurchase,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Purchase credits (mock implementation - integrate with payment processor)"""
    
    # Calculate cost based on credit amount
    cost_per_credit = settings.CREDIT_COST_USD
    total_cost = purchase_data.amount * cost_per_credit
    
    # Mock payment processing
    # In production, integrate with Stripe, PayPal, etc.
    payment_reference = f"mock_payment_{datetime.utcnow().timestamp()}"
    
    # Process credit purchase
    success = await process_credit_purchase(
        user_id=current_user.id,
        amount=purchase_data.amount,
        payment_method=purchase_data.payment_method,
        payment_reference=payment_reference,
        amount_paid=total_cost,
        currency="USD",
        db=db
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to process credit purchase"
        )
    
    # Get the latest credit transaction
    latest_credit = db.query(Credit).filter(
        Credit.user_id == current_user.id
    ).order_by(Credit.created_at.desc()).first()
    
    return latest_credit

@router.get("/pricing")
async def get_credit_pricing():
    """Get credit pricing information"""
    
    return {
        "cost_per_credit": settings.CREDIT_COST_USD,
        "currency": "USD",
        "packages": [
            {
                "name": "Starter",
                "credits": 50,
                "cost": 50 * settings.CREDIT_COST_USD,
                "savings": 0
            },
            {
                "name": "Professional",
                "credits": 200,
                "cost": 200 * settings.CREDIT_COST_USD * 0.9,  # 10% discount
                "savings": 10
            },
            {
                "name": "Enterprise",
                "credits": 500,
                "cost": 500 * settings.CREDIT_COST_USD * 0.8,  # 20% discount
                "savings": 20
            }
        ],
        "usage_costs": {
            "resume_analysis": settings.CREDIT_COST_PER_RESUME_ANALYSIS,
            "interview_analysis": settings.CREDIT_COST_PER_INTERVIEW,
            "ai_matching": settings.CREDIT_COST_PER_AI_MATCHING
        }
    }

@router.get("/usage-stats")
async def get_credit_usage_stats(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get credit usage statistics for current user"""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get usage by transaction type
    usage_by_type = db.query(
        Credit.transaction_type,
        func.sum(func.abs(Credit.amount)).label('total_used')
    ).filter(
        and_(
            Credit.user_id == current_user.id,
            Credit.amount < 0,  # Only deductions
            Credit.created_at >= start_date
        )
    ).group_by(Credit.transaction_type).all()
    
    # Get daily usage
    daily_usage = db.query(
        func.date(Credit.created_at).label('date'),
        func.sum(func.abs(Credit.amount)).label('credits_used')
    ).filter(
        and_(
            Credit.user_id == current_user.id,
            Credit.amount < 0,  # Only deductions
            Credit.created_at >= start_date
        )
    ).group_by(func.date(Credit.created_at)).all()
    
    return {
        "period_days": days,
        "usage_by_type": [
            {"type": usage.transaction_type, "credits_used": int(usage.total_used)}
            for usage in usage_by_type
        ],
        "daily_usage": [
            {"date": str(usage.date), "credits_used": int(usage.credits_used)}
            for usage in daily_usage
        ]
    }

# Admin endpoints
@router.get("/admin/stats", response_model=CreditStats)
async def get_admin_credit_statistics(
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get credit statistics for admin"""
    
    # Total credits issued
    total_issued = db.query(func.sum(Credit.amount)).filter(
        Credit.amount > 0
    ).scalar() or 0
    
    # Total credits used
    total_used = abs(db.query(func.sum(Credit.amount)).filter(
        Credit.amount < 0
    ).scalar() or 0)
    
    # Total revenue
    total_revenue = db.query(func.sum(Credit.amount_paid)).filter(
        Credit.amount_paid.isnot(None)
    ).scalar() or 0.0
    
    # Active users with credits
    active_users = db.query(func.count(func.distinct(Credit.user_id))).filter(
        Credit.balance_after > 0
    ).scalar() or 0
    
    return CreditStats(
        total_credits_issued=int(total_issued),
        total_credits_used=int(total_used),
        total_revenue=float(total_revenue),
        active_users_with_credits=active_users
    )

@router.get("/admin/transactions", response_model=List[CreditResponse])
async def get_all_credit_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user_id: Optional[int] = Query(None),
    transaction_type: Optional[str] = Query(None),
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get all credit transactions (admin only)"""
    
    query = db.query(Credit)
    
    if user_id:
        query = query.filter(Credit.user_id == user_id)
    
    if transaction_type:
        query = query.filter(Credit.transaction_type == transaction_type)
    
    credits = query.order_by(Credit.created_at.desc()).offset(skip).limit(limit).all()
    return credits

@router.post("/admin/add-credits")
async def admin_add_credits(
    user_id: int,
    amount: int,
    description: str = "Admin credit adjustment",
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Add credits to user account (admin only)"""
    
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be positive"
        )
    
    # Add credits
    success = await add_credits(
        user_id=user_id,
        amount=amount,
        transaction_type="admin_adjustment",
        db=db,
        description=description
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to add credits"
        )
    
    # Get new balance
    new_balance = await get_user_credit_balance(user_id, db)
    
    return {
        "message": f"Added {amount} credits to user {user.username}",
        "new_balance": new_balance
    }

@router.post("/admin/deduct-credits")
async def admin_deduct_credits(
    user_id: int,
    amount: int,
    description: str = "Admin credit deduction",
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Deduct credits from user account (admin only)"""
    
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be positive"
        )
    
    # Deduct credits
    success = await deduct_credits(
        user_id=user_id,
        amount=amount,
        transaction_type="admin_adjustment",
        db=db,
        description=description
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to deduct credits (insufficient balance)"
        )
    
    # Get new balance
    new_balance = await get_user_credit_balance(user_id, db)
    
    return {
        "message": f"Deducted {amount} credits from user {user.username}",
        "new_balance": new_balance
    }

