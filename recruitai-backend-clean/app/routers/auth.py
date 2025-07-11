from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Security
security = HTTPBearer()

# JWT Configuration
SECRET_KEY = "recruitai-secret-key-2025-secure"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Pydantic models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

class UserResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    role: str

# Mock user database (in production, use real database)
MOCK_USERS = {
    "admin@recruitai.com": {
        "id": 1,
        "email": "admin@recruitai.com",
        "password_hash": hashlib.sha256("password123".encode()).hexdigest(),
        "first_name": "Admin",
        "last_name": "User",
        "role": "admin"
    },
    "recruiter@recruitai.com": {
        "id": 2,
        "email": "recruiter@recruitai.com", 
        "password_hash": hashlib.sha256("password123".encode()).hexdigest(),
        "first_name": "Recruiter",
        "last_name": "User",
        "role": "recruiter"
    },
    "candidate@recruitai.com": {
        "id": 3,
        "email": "candidate@recruitai.com",
        "password_hash": hashlib.sha256("password123".encode()).hexdigest(),
        "first_name": "Candidate",
        "last_name": "User", 
        "role": "candidate"
    }
}

def hash_password(password: str) -> str:
    """Hash a password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return hash_password(plain_password) == hashed_password

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user_by_email(email: str):
    """Get user by email from mock database"""
    return MOCK_USERS.get(email)

def authenticate_user(email: str, password: str):
    """Authenticate user with email and password"""
    user = get_user_by_email(email)
    if not user:
        return False
    if not verify_password(password, user["password_hash"]):
        return False
    return user

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = get_user_by_email(email)
    if user is None:
        raise credentials_exception
    return user

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    Authenticate user and return access token
    """
    try:
        logger.info(f"Login attempt for email: {request.email}")
        
        # Authenticate user
        user = authenticate_user(request.email, request.password)
        if not user:
            logger.warning(f"Failed login attempt for email: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user["email"], "role": user["role"]},
            expires_delta=access_token_expires
        )
        
        # Prepare user data (without password hash)
        user_data = {
            "id": user["id"],
            "email": user["email"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "role": user["role"]
        }
        
        logger.info(f"Successful login for email: {request.email}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )

@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest):
    """
    Register new user and return access token
    """
    try:
        logger.info(f"Registration attempt for email: {request.email}")
        
        # Check if user already exists
        if get_user_by_email(request.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        user_id = len(MOCK_USERS) + 1
        password_hash = hash_password(request.password)
        
        new_user = {
            "id": user_id,
            "email": request.email,
            "password_hash": password_hash,
            "first_name": request.first_name,
            "last_name": request.last_name,
            "role": "candidate"  # Default role
        }
        
        # Add to mock database
        MOCK_USERS[request.email] = new_user
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": new_user["email"], "role": new_user["role"]},
            expires_delta=access_token_expires
        )
        
        # Prepare user data (without password hash)
        user_data = {
            "id": new_user["id"],
            "email": new_user["email"],
            "first_name": new_user["first_name"],
            "last_name": new_user["last_name"],
            "role": new_user["role"]
        }
        
        logger.info(f"Successful registration for email: {request.email}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_data
        }
        
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
    """
    Get current user information
    """
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "first_name": current_user["first_name"],
        "last_name": current_user["last_name"],
        "role": current_user["role"]
    }

@router.post("/logout")
async def logout():
    """
    Logout user (client should remove token)
    """
    return {"message": "Successfully logged out"}

@router.get("/demo-credentials")
async def get_demo_credentials():
    """
    Get demo credentials for testing
    """
    return {
        "credentials": [
            {
                "role": "admin",
                "email": "admin@recruitai.com",
                "password": "password123",
                "description": "Full admin access"
            },
            {
                "role": "recruiter", 
                "email": "recruiter@recruitai.com",
                "password": "password123",
                "description": "Recruiter access"
            },
            {
                "role": "candidate",
                "email": "candidate@recruitai.com", 
                "password": "password123",
                "description": "Candidate access"
            }
        ]
    }

# Health check for auth module
@router.get("/health")
async def auth_health():
    """
    Check authentication module health
    """
    return {
        "status": "healthy",
        "module": "authentication",
        "users_count": len(MOCK_USERS),
        "demo_available": True
    }

