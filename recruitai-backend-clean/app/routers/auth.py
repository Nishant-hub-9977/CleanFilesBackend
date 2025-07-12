


from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import jwt
import bcrypt
import logging
import os
from typing import Optional

# Import database and models with fallback
try:
    from ..core.database import get_db
    from ..models.user import User
    from ..schemas.auth import UserRegister, UserLogin, Token, UserResponse
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    logging.warning("Database models not available, using fallback mode")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# JWT Configuration with environment variables (Grok 4\"s recommendation)
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-render-deployment")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Enhanced demo users with more comprehensive data (combining both approaches)
DEMO_USERS = {
    "admin@recruitai.com": {
        "id": "admin_id",
        "email": "admin@recruitai.com",
        "hashed_password": bcrypt.hashpw("password123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
        "full_name": "Admin User",
        "role": "admin",
        "created_at": datetime.utcnow(),
        "is_active": True,
        "is_verified": True,
        "last_login": datetime.utcnow(),
        "permissions": ["all"],
        "company_name": "RecruitAI Inc."
    },
    "recruiter@recruitai.com": {
        "id": "recruiter_id",
        "email": "recruiter@recruitai.com",
        "hashed_password": bcrypt.hashpw("password123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
        "full_name": "Recruiter User",
        "role": "recruiter",
        "created_at": datetime.utcnow(),
        "is_active": True,
        "is_verified": True,
        "last_login": datetime.utcnow(),
        "permissions": ["manage_jobs", "view_resumes"],
        "company_name": "Hiring Solutions Ltd."
    },
    "candidate@recruitai.com": {
        "id": "candidate_id",
        "email": "candidate@recruitai.com",
        "hashed_password": bcrypt.hashpw("password123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
        "full_name": "Candidate User",
        "role": "candidate",
        "created_at": datetime.utcnow(),
        "is_active": True,
        "is_verified": True,
        "last_login": datetime.utcnow(),
        "permissions": ["upload_resume", "view_jobs"],
        "company_name": None
    }
}

# Helper function to create JWT tokens
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire.timestamp()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire.timestamp()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Helper function to decode JWT tokens
def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

# Dependency to get current user (for protected routes)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    try:
        payload = decode_token(token)
        user_email = payload.get("sub")
        if user_email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
        
        if DB_AVAILABLE:
            user = db.query(User).filter(User.email == user_email).first()
            if user is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
            return user
        else:
            # Fallback to demo users
            user = DEMO_USERS.get(user_email)
            if user is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found in demo mode")
            return UserResponse(**user) # Return as Pydantic model

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

# Authentication endpoints
@router.post("/register", response_model=Token)
async def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user"""
    if DB_AVAILABLE:
        db_user = db.query(User).filter(User.email == user_data.email).first()
        if db_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

        hashed_password = bcrypt.hashpw(user_data.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        new_user = User(
            id=str(uuid.uuid4()),
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            role=user_data.role,
            created_at=datetime.utcnow(),
            is_active=True,
            is_verified=True,
            last_login=datetime.utcnow()
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        access_token = create_access_token(data={"sub": new_user.email, "role": new_user.role})
        refresh_token = create_refresh_token(data={"sub": new_user.email})
        logger.info(f"User registered: {new_user.email}")
        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "user": new_user}
    else:
        # Fallback registration for demo users
        if user_data.email in DEMO_USERS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered in demo mode")
        
        new_demo_user = {
            "id": str(uuid.uuid4()),
            "email": user_data.email,
            "hashed_password": bcrypt.hashpw(user_data.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
            "full_name": user_data.full_name,
            "role": user_data.role,
            "created_at": datetime.utcnow(),
            "is_active": True,
            "is_verified": True,
            "last_login": datetime.utcnow(),
            "permissions": ["upload_resume", "view_jobs"] if user_data.role == "candidate" else ["view_jobs"]
        }
        DEMO_USERS[user_data.email] = new_demo_user
        
        access_token = create_access_token(data={"sub": new_demo_user["email"], "role": new_demo_user["role"]})
        refresh_token = create_refresh_token(data={"sub": new_demo_user["email"]})
        logger.info(f"Demo user registered: {new_demo_user["email"]}")
        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "user": UserResponse(**new_demo_user)}

@router.post("/login", response_model=Token)
async def login_for_access_token(user_data: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token"""
    user = None
    if DB_AVAILABLE:
        user = db.query(User).filter(User.email == user_data.email).first()
        if not user or not bcrypt.checkpw(user_data.password.encode("utf-8"), user.hashed_password.encode("utf-8")):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
        user.last_login = datetime.utcnow()
        db.commit()
        db.refresh(user)
    else:
        # Fallback login for demo users
        demo_user_data = DEMO_USERS.get(user_data.email)
        if not demo_user_data or not bcrypt.checkpw(user_data.password.encode("utf-8"), demo_user_data["hashed_password"].encode("utf-8")):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password in demo mode")
        user = UserResponse(**demo_user_data)
        DEMO_USERS[user_data.email]["last_login"] = datetime.utcnow() # Update last login for demo user

    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    refresh_token = create_refresh_token(data={"sub": user.email})
    logger.info(f"User logged in: {user.email}")
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "user": user}

@router.post("/refresh", response_model=Token)
async def refresh_access_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Refresh access token using refresh token"""
    refresh_token = credentials.credentials
    try:
        payload = decode_token(refresh_token)
        user_email = payload.get("sub")
        user_role = payload.get("role") # Assuming role is also in refresh token payload
        if user_email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        
        new_access_token = create_access_token(data={"sub": user_email, "role": user_role})
        logger.info(f"Token refreshed for user: {user_email}")
        return {"access_token": new_access_token, "refresh_token": refresh_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Refresh token error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: UserResponse = Depends(get_current_user)):
    """Get current authenticated user"""
    logger.info(f"Fetching current user: {current_user.email}")
    return current_user

@router.post("/logout")
async def logout_user(current_user: UserResponse = Depends(get_current_user)):
    """Logout user (client-side token invalidation)"""
    logger.info(f"User logged out: {current_user.email}")
    return {"message": "Logged out successfully"}

@router.post("/change-password")
async def change_password(current_user: UserResponse = Depends(get_current_user), 
                          old_password: str = Form(...), 
                          new_password: str = Form(...),
                          db: Session = Depends(get_db)):
    """Change user password"""
    try:
        if DB_AVAILABLE:
            user = db.query(User).filter(User.id == current_user.id).first()
            if not user or not bcrypt.checkpw(old_password.encode("utf-8"), user.hashed_password.encode("utf-8")):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect old password")
            
            user.hashed_password = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            db.commit()
            db.refresh(user)
            logger.info(f"Password changed for user: {current_user.email}")
            return {"message": "Password changed successfully"}
        
        return {"message": "Password change not available in demo mode"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Change password error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# Health check endpoint
@router.get("/health")
async def auth_health():
    """Authentication service health check with enhanced information"""
    return {
        "status": "healthy",
        "service": "authentication",
        "version": "2.0.0",
        "database_available": DB_AVAILABLE,
        "demo_users_available": len(DEMO_USERS),
        "features": [
            "JWT authentication",
            "Refresh tokens",
            "Password hashing (bcrypt)",
            "Demo credentials",
            "User registration",
            "Password reset",
            "Environment configuration",
            "Graceful fallbacks"
        ],
        "demo_credentials": {
            "admin": "admin@recruitai.com / password123",
            "recruiter": "recruiter@recruitai.com / password123",
            "candidate": "candidate@recruitai.com / password123"
        },
        "token_config": {
            "access_token_expire_minutes": ACCESS_TOKEN_EXPIRE_MINUTES,
            "refresh_token_expire_days": REFRESH_TOKEN_EXPIRE_DAYS,
            "algorithm": ALGORITHM
        }
    }
