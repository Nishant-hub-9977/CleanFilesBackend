from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
import jwt
import bcrypt
import os
from datetime import datetime, timedelta
import logging
import re

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Security
security = HTTPBearer(auto_error=False)

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Pydantic models
class UserLogin(BaseModel):
    email: str
    password: str

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    confirm_password: str
    
    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters long')
        if not re.match("^[a-zA-Z0-9_]+$", v):
            raise ValueError('Username can only contain letters, numbers, and underscores')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v

class UserResponse(BaseModel):
    id: Optional[int] = None
    username: str
    email: str
    created_at: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# Mock database (replace with real database in production)
mock_users = [
    {
        "id": 1,
        "username": "demo",
        "email": "demo@recruitai.com",
        "password": bcrypt.hashpw("demo123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
        "created_at": "2024-01-01T00:00:00Z"
    },
    {
        "id": 2,
        "username": "admin",
        "email": "admin@recruitai.com", 
        "password": bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
        "created_at": "2024-01-01T00:00:00Z"
    }
]

# Utility functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False

def get_user_by_email(email: str):
    for user in mock_users:
        if user["email"] == email:
            return user
    return None

def get_user_by_username(username: str):
    for user in mock_users:
        if user["username"] == username:
            return user
    return None

def create_user(user_data: UserRegister):
    # Check if user already exists
    if get_user_by_email(user_data.email):
        return None
    if get_user_by_username(user_data.username):
        return None
    
    # Hash password
    hashed_password = bcrypt.hashpw(user_data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Create new user
    new_user = {
        "id": len(mock_users) + 1,
        "username": user_data.username,
        "email": user_data.email,
        "password": hashed_password,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    
    mock_users.append(new_user)
    return new_user

# Authentication endpoints
@router.post("/login", response_model=TokenResponse)
async def login(user_credentials: UserLogin):
    try:
        logger.info(f"Login attempt for email: {user_credentials.email}")
        
        # Find user by email
        user = get_user_by_email(user_credentials.email)
        
        if not user:
            logger.warning(f"User not found: {user_credentials.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Verify password
        if not verify_password(user_credentials.password, user["password"]):
            logger.warning(f"Invalid password for user: {user_credentials.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user["email"], "user_id": user["id"]},
            expires_delta=access_token_expires
        )
        
        # Create user response
        user_response = UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            created_at=user["created_at"]
        )
        
        logger.info(f"Successful login for user: {user_credentials.email}")
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=user_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again later."
        )

@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    try:
        logger.info(f"Registration attempt for email: {user_data.email}")
        
        # Check if user already exists
        if get_user_by_email(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        if get_user_by_username(user_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        # Create new user
        new_user = create_user(user_data)
        
        if not new_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed. Please try again."
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": new_user["email"], "user_id": new_user["id"]},
            expires_delta=access_token_expires
        )
        
        # Create user response
        user_response = UserResponse(
            id=new_user["id"],
            username=new_user["username"],
            email=new_user["email"],
            created_at=new_user["created_at"]
        )
        
        logger.info(f"Successful registration for user: {user_data.email}")
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=user_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again later."
        )

@router.get("/me")
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Decode JWT token
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
        
        # Get user
        user = get_user_by_email(email)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            created_at=user["created_at"]
        )
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    except Exception as e:
        logger.error(f"Get current user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )

@router.post("/logout")
async def logout():
    # In a real application, you might want to blacklist the token
    return {"message": "Successfully logged out"}

# Demo credentials endpoint
@router.get("/demo-credentials")
async def get_demo_credentials():
    return {
        "demo_accounts": [
            {
                "email": "demo@recruitai.com",
                "password": "demo123",
                "username": "demo"
            },
            {
                "email": "admin@recruitai.com", 
                "password": "admin123",
                "username": "admin"
            }
        ],
        "note": "Use these credentials to test the application"
    }

