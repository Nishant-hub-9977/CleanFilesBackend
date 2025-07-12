from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
import jwt
import bcrypt
from datetime import datetime, timedelta
import logging
import os
from passlib.context import CryptContext

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Pydantic models
class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    role: Optional[str] = "candidate"
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    full_name: Optional[str] = None
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

# In-memory user storage (replace with database in production)
users_db = {
    "admin@recruitai.com": {
        "id": "admin_id",
        "email": "admin@recruitai.com",
        "password_hash": pwd_context.hash("password123"),
        "role": "admin",
        "full_name": "Admin User",
        "created_at": datetime.utcnow()
    },
    "recruiter@recruitai.com": {
        "id": "recruiter_id", 
        "email": "recruiter@recruitai.com",
        "password_hash": pwd_context.hash("password123"),
        "role": "recruiter",
        "full_name": "Recruiter User",
        "created_at": datetime.utcnow()
    },
    "candidate@recruitai.com": {
        "id": "candidate_id",
        "email": "candidate@recruitai.com", 
        "password_hash": pwd_context.hash("password123"),
        "role": "candidate",
        "full_name": "Candidate User",
        "created_at": datetime.utcnow()
    }
}

# Token storage (replace with Redis in production)
refresh_tokens = {}

# Utility functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str, token_type: str = "access"):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != token_type:
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.JWTError:
        return None

def get_user_by_email(email: str):
    """Get user by email"""
    return users_db.get(email)

def create_user(user_data: UserRegister) -> dict:
    """Create a new user"""
    if user_data.email in users_db:
        raise HTTPException(
            status_code=400,
            detail="User with this email already exists"
        )
    
    user_id = f"user_{len(users_db) + 1}_{int(datetime.utcnow().timestamp())}"
    password_hash = get_password_hash(user_data.password)
    
    new_user = {
        "id": user_id,
        "email": user_data.email,
        "password_hash": password_hash,
        "role": user_data.role,
        "full_name": user_data.full_name or user_data.email.split("@")[0],
        "created_at": datetime.utcnow()
    }
    
    users_db[user_data.email] = new_user
    return new_user

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user"""
    token = credentials.credentials
    payload = verify_token(token, "access")
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    email = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

# Routes
@router.post("/login", response_model=TokenResponse)
async def login(user_credentials: UserLogin):
    """Authenticate user and return tokens"""
    try:
        user = get_user_by_email(user_credentials.email)
        
        if not user or not verify_password(user_credentials.password, user["password_hash"]):
            logger.warning(f"Failed login attempt for email: {user_credentials.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Create tokens
        access_token = create_access_token(data={"sub": user["email"]})
        refresh_token = create_refresh_token(data={"sub": user["email"]})
        
        # Store refresh token
        refresh_tokens[refresh_token] = {
            "user_email": user["email"],
            "created_at": datetime.utcnow()
        }
        
        # Create user response
        user_response = UserResponse(
            id=user["id"],
            email=user["email"],
            role=user["role"],
            full_name=user["full_name"],
            created_at=user["created_at"]
        )
        
        logger.info(f"Successful login for user: {user['email']}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )

@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    """Register a new user"""
    try:
        # Create user
        new_user = create_user(user_data)
        
        # Create tokens
        access_token = create_access_token(data={"sub": new_user["email"]})
        refresh_token = create_refresh_token(data={"sub": new_user["email"]})
        
        # Store refresh token
        refresh_tokens[refresh_token] = {
            "user_email": new_user["email"],
            "created_at": datetime.utcnow()
        }
        
        # Create user response
        user_response = UserResponse(
            id=new_user["id"],
            email=new_user["email"],
            role=new_user["role"],
            full_name=new_user["full_name"],
            created_at=new_user["created_at"]
        )
        
        # Fixed the f-string syntax error here
        logger.info(f"New user registered: {new_user['email']}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during registration"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        role=current_user["role"],
        full_name=current_user["full_name"],
        created_at=current_user["created_at"]
    )

@router.post("/refresh")
async def refresh_access_token(refresh_token: str):
    """Refresh access token using refresh token"""
    try:
        # Verify refresh token
        payload = verify_token(refresh_token, "refresh")
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        # Check if refresh token exists in storage
        if refresh_token not in refresh_tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found"
            )
        
        email = payload.get("sub")
        user = get_user_by_email(email)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Create new access token
        new_access_token = create_access_token(data={"sub": email})
        
        logger.info(f"Access token refreshed for user: {email}")
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during token refresh"
        )

@router.post("/logout")
async def logout(
    refresh_token: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Logout user and invalidate refresh token"""
    try:
        if refresh_token and refresh_token in refresh_tokens:
            del refresh_tokens[refresh_token]
        
        logger.info(f"User logged out: {current_user['email']}")
        
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during logout"
        )

@router.get("/health")
async def auth_health():
    """Authentication service health check"""
    return {
        "status": "healthy",
        "service": "authentication",
        "timestamp": datetime.utcnow().isoformat(),
        "users_count": len(users_db),
        "active_tokens": len(refresh_tokens),
        "features": [
            "JWT Authentication",
            "Password Hashing",
            "Token Refresh",
            "Role-based Access"
        ]
    }

@router.get("/demo-users")
async def get_demo_users():
    """Get demo user credentials for testing"""
    demo_users = []
    for email, user_data in users_db.items():
        if email in ["admin@recruitai.com", "recruiter@recruitai.com", "candidate@recruitai.com"]:
            demo_users.append({
                "email": email,
                "password": "password123",
                "role": user_data["role"],
                "description": f"{user_data['role'].title()} access level"
            })
    
    return {
        "demo_users": demo_users,
        "note": "These are demo credentials for testing purposes"
    }

