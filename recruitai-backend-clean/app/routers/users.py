"""
Users management router for admin operations
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, timedelta

from ..core.database import get_db
from ..core.security import get_admin_user, get_current_active_user
from ..models.user import User
from ..models.credit import Credit
from ..schemas.user import UserResponse, UserStats, UserUpdate
from ..schemas.credit import CreditResponse

router = APIRouter()

@router.get("/", response_model=List[UserResponse])
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get all users (admin only)"""
    
    query = db.query(User)
    
    # Apply filters
    if search:
        query = query.filter(
            (User.username.contains(search)) |
            (User.email.contains(search)) |
            (User.company_name.contains(search))
        )
    
    if role:
        query = query.filter(User.role == role)
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    users = query.offset(skip).limit(limit).all()
    return users

@router.get("/stats", response_model=UserStats)
async def get_user_statistics(
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get user statistics (admin only)"""
    
    # Total users
    total_users = db.query(User).count()
    
    # Active users
    active_users = db.query(User).filter(User.is_active == True).count()
    
    # New users this month
    start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_users_this_month = db.query(User).filter(User.created_at >= start_of_month).count()
    
    # Total companies (unique company names)
    total_companies = db.query(func.count(func.distinct(User.company_name))).scalar()
    
    return UserStats(
        total_users=total_users,
        active_users=active_users,
        new_users_this_month=new_users_this_month,
        total_companies=total_companies
    )

@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get user by ID (admin only)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Update user (admin only)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(user, field):
            setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return user

@router.post("/{user_id}/activate")
async def activate_user(
    user_id: int,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Activate user account (admin only)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = True
    db.commit()
    
    return {"message": f"User {user.username} activated successfully"}

@router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Deactivate user account (admin only)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate admin user"
        )
    
    user.is_active = False
    db.commit()
    
    return {"message": f"User {user.username} deactivated successfully"}

@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Delete user account (admin only)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete admin user"
        )
    
    # Note: In production, you might want to soft delete or archive user data
    # instead of hard delete to maintain data integrity
    db.delete(user)
    db.commit()
    
    return {"message": f"User {user.username} deleted successfully"}

@router.get("/{user_id}/credits", response_model=List[CreditResponse])
async def get_user_credits(
    user_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get user credit history (admin only)"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    credits = db.query(Credit).filter(Credit.user_id == user_id).order_by(Credit.created_at.desc()).offset(skip).limit(limit).all()
    return credits

@router.post("/{user_id}/credits/add")
async def add_credits_to_user(
    user_id: int,
    amount: int,
    description: str = "Admin credit adjustment",
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Add credits to user account (admin only)"""
    
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
    
    # Get current balance
    latest_credit = db.query(Credit).filter(Credit.user_id == user_id).order_by(Credit.created_at.desc()).first()
    current_balance = latest_credit.balance_after if latest_credit else 0
    
    # Create credit transaction
    credit_transaction = Credit(
        user_id=user_id,
        amount=amount,
        balance_after=current_balance + amount,
        transaction_type="admin_adjustment",
        description=description,
        status="completed"
    )
    
    db.add(credit_transaction)
    db.commit()
    
    return {
        "message": f"Added {amount} credits to user {user.username}",
        "new_balance": current_balance + amount
    }

