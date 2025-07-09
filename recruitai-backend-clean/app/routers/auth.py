"""
Authentication router for user registration, login, and token management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from datetime import timedelta

from ..core.database import get_db
from ..core.security import (
    verify_password, 
    get_password_hash, 
    create_access_token, 
    create_refresh_token,
    get_current_user,
    get_current_active_user
)
from ..core.config import settings
from ..models.user import User
from ..models.credit import Credit
from ..schemas.auth import UserRegister, UserLogin, Token, ChangePassword
from ..schemas.user import UserResponse, UserProfile

router = APIRouter()
security = HTTPBearer()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user"""
    
    # Check if username already exists
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        company_name=user_data.company_name,
        phone_number=user_data.phone_number,
        role=user_data.role,
        is_active=True,
        is_verified=False
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Give free credits to new user
    credit_transaction = Credit(
        user_id=db_user.id,
        amount=settings.FREE_CREDITS_ON_SIGNUP,
        balance_after=settings.FREE_CREDITS_ON_SIGNUP,
        transaction_type="signup_bonus",
        description=f"Welcome bonus: {settings.FREE_CREDITS_ON_SIGNUP} free credits",
        status="completed"
    )
    
    db.add(credit_transaction)
    db.commit()
    
    return db_user

@router.post("/login", response_model=Token)
async def login_user(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return access token"""
    
    # Find user by username or email
    user = db.query(User).filter(
        (User.username == user_credentials.username_or_email) |
        (User.email == user_credentials.username_or_email)
    ).first()
    
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    # Create refresh token
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    # Update last login
    from sqlalchemy import func
    user.last_login = func.now()
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get current user profile with statistics"""
    
    # Get user statistics
    total_jobs = db.query(db.query(User).filter(User.id == current_user.id).first().jobs).count() if hasattr(current_user, 'jobs') else 0
    
    # Get credit balance
    latest_credit = db.query(Credit).filter(Credit.user_id == current_user.id).order_by(Credit.created_at.desc()).first()
    credits_balance = latest_credit.balance_after if latest_credit else 0
    
    # Create response with statistics
    user_profile = UserProfile(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        company_name=current_user.company_name,
        phone_number=current_user.phone_number,
        role=current_user.role,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        profile_picture=current_user.profile_picture,
        bio=current_user.bio,
        credits_balance=credits_balance
    )
    
    return user_profile

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    
    # Update allowed fields
    allowed_fields = ['username', 'email', 'company_name', 'phone_number', 'bio']
    
    for field, value in user_update.items():
        if field in allowed_fields and value is not None:
            # Check if username/email already exists (if being updated)
            if field == 'username' and value != current_user.username:
                if db.query(User).filter(User.username == value, User.id != current_user.id).first():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Username already taken"
                    )
            
            if field == 'email' and value != current_user.email:
                if db.query(User).filter(User.email == value, User.id != current_user.id).first():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email already registered"
                    )
            
            setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return current_user

@router.post("/change-password")
async def change_password(
    password_data: ChangePassword,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    
    return {"message": "Password updated successfully"}

@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    """Refresh access token using refresh token"""
    
    from ..core.security import verify_token
    
    payload = verify_token(refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

