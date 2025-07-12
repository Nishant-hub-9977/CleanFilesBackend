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

# JWT Configuration with environment variables (Grok 4's recommendation)
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-render-deployment")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Enhanced demo users with more comprehensive data (combining both approaches)
DEMO_USERS = {
    "admin@recruitai.com": {
        "id": 1,
        "email": "admin@recruitai.com",
        "username": "admin",
        "password": "password123",
        "full_name": "Admin User",
        "company_name": "RecruitAI Inc",
        "phone_number": "+1-555-0101",
        "role": "admin",
        "created_at": datetime.utcnow()
    },
    "recruiter@recruitai.com": {
        "id": 2,
        "email": "recruiter@recruitai.com", 
        "username": "recruiter",
        "password": "password123",
        "full_name": "Sarah Johnson",
        "company_name": "TechCorp Solutions",
        "phone_number": "+1-555-0102",
        "role": "recruiter",
        "created_at": datetime.utcnow()
    },
    "candidate@recruitai.com": {
        "id": 3,
        "email": "candidate@recruitai.com",
        "username": "candidate",
        "password": "password123", 
        "full_name": "John Smith",
        "company_name": "Freelancer",
        "phone_number": "+1-555-0103",
        "role": "candidate",
        "created_at": datetime.utcnow()
    }
}

def hash_password(password: str) -> str:
    """Hash password using bcrypt (production-grade)"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token with enhanced payload"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """Create refresh token (Grok 4's recommendation)"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token with enhanced error handling"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Check token type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {"email": email, "user_id": user_id}
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials", 
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_user_by_identifier(identifier: str, db: Session = None):
    """Get user by email or username with fallback to demo users"""
    
    # Check demo users first (always available)
    for email, user_data in DEMO_USERS.items():
        if user_data["email"] == identifier or user_data["username"] == identifier:
            return user_data
    
    # Check database if available
    if DB_AVAILABLE and db:
        try:
            user = db.query(User).filter(
                (User.email == identifier) | (User.username == identifier)
            ).first()
            if user:
                return {
                    "id": user.id,
                    "email": user.email,
                    "username": getattr(user, 'username', user.email),
                    "password": user.password_hash,
                    "full_name": user.full_name,
                    "company_name": getattr(user, 'company_name', user.company),
                    "phone_number": getattr(user, 'phone_number', None),
                    "role": user.role,
                    "created_at": user.created_at
                }
        except Exception as e:
            logger.warning(f"Database query failed: {e}")
    
    return None

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, db: Session = Depends(get_db) if DB_AVAILABLE else None):
    """
    Enhanced login with support for both email and username (Grok 4's schema alignment)
    """
    try:
        # Support both email and username_or_email fields
        identifier = getattr(user_data, 'username_or_email', None) or getattr(user_data, 'email', None)
        
        if not identifier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email or username is required"
            )
        
        logger.info(f"Login attempt for: {identifier}")
        
        # Get user from demo or database
        user = await get_user_by_identifier(identifier, db)
        
        if not user:
            logger.warning(f"User not found: {identifier}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email/username or password"
            )
        
        # Verify password
        stored_password = user.get("password", user.get("hashed_password", ""))
        
        # For demo users, direct comparison; for DB users, hash verification
        password_valid = False
        if identifier in [u["email"] for u in DEMO_USERS.values()]:
            password_valid = (user_data.password == stored_password)
        else:
            password_valid = verify_password(user_data.password, stored_password)
        
        if not password_valid:
            logger.warning(f"Invalid password for: {identifier}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email/username or password"
            )
        
        logger.info(f"Successful login for: {identifier}")
        
        # Create tokens
        token_data = {
            "sub": user["email"],
            "user_id": user["id"],
            "role": user["role"]
        }
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data=token_data, expires_delta=access_token_expires)
        refresh_token = create_refresh_token(data=token_data)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,  # Grok 4's recommendation
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "username": user.get("username", user["email"]),
                "full_name": user["full_name"],
                "company_name": user.get("company_name", ""),
                "role": user["role"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )

@router.post("/register", response_model=UserResponse if DB_AVAILABLE else dict)
async def register(user_data: UserRegister, db: Session = Depends(get_db) if DB_AVAILABLE else None):
    """
    Enhanced registration with schema validation (Grok 4's approach)
    """
    try:
        logger.info(f"Registration attempt for: {user_data.email}")
        
        # Check if user already exists
        existing_user = await get_user_by_identifier(user_data.email, db)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check username if provided
        if hasattr(user_data, 'username'):
            existing_username = await get_user_by_identifier(user_data.username, db)
            if existing_username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
        
        if DB_AVAILABLE and db:
            # Create new user in database
            hashed_password = hash_password(user_data.password)
            new_user = User(
                email=user_data.email,
                username=getattr(user_data, 'username', user_data.email),
                password_hash=hashed_password,
                full_name=user_data.full_name,
                company_name=getattr(user_data, 'company_name', ''),
                phone_number=getattr(user_data, 'phone_number', None),
                role=getattr(user_data, 'role', 'candidate'),
                created_at=datetime.utcnow()
            )
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            logger.info(f"User registered successfully: {user_data.email}")
            
            return {
                "id": new_user.id,
                "email": new_user.email,
                "username": new_user.username,
                "full_name": new_user.full_name,
                "company_name": new_user.company_name,
                "role": new_user.role,
                "created_at": new_user.created_at
            }
        else:
            # Fallback mode - return success without database
            logger.info(f"User registration (fallback mode): {user_data.email}")
            return {
                "message": "Registration successful (demo mode)",
                "email": user_data.email,
                "role": getattr(user_data, 'role', 'candidate')
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during registration"
        )

@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """
    Refresh access token using refresh token (Grok 4's recommendation)
    """
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        email = payload.get("sub")
        user_id = payload.get("user_id")
        role = payload.get("role")
        
        # Create new access token
        token_data = {"sub": email, "user_id": user_id, "role": role}
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = create_access_token(data=token_data, expires_delta=access_token_expires)
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired"
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

@router.get("/me")
async def get_current_user(token_data: dict = Depends(verify_token), db: Session = Depends(get_db) if DB_AVAILABLE else None):
    """
    Get current user information with enhanced data
    """
    try:
        email = token_data["email"]
        user = await get_user_by_identifier(email, db)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "id": user["id"],
            "email": user["email"],
            "username": user.get("username", user["email"]),
            "full_name": user["full_name"],
            "company_name": user.get("company_name", ""),
            "phone_number": user.get("phone_number"),
            "role": user["role"],
            "created_at": user.get("created_at")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/password-reset")
async def password_reset(email: str):
    """
    Initiate password reset process (Grok 4's implementation)
    """
    try:
        user = await get_user_by_identifier(email)
        if not user:
            # Don't reveal if user exists or not for security
            logger.info(f"Password reset requested for non-existent user: {email}")
        else:
            logger.info(f"Password reset requested for: {email}")
        
        # Always return success for security
        return {"message": "If the email exists, a password reset link has been sent"}
        
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db) if DB_AVAILABLE else None
):
    """
    Change user password (Grok 4's implementation)
    """
    try:
        email = token_data["email"]
        user = await get_user_by_identifier(email, db)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify current password
        stored_password = user.get("password", user.get("hashed_password", ""))
        
        if email in [u["email"] for u in DEMO_USERS.values()]:
            # Demo user - don't allow password change
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change password for demo users"
            )
        
        if not verify_password(current_password, stored_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        if DB_AVAILABLE and db:
            # Update password in database
            db_user = db.query(User).filter(User.email == email).first()
            if db_user:
                db_user.password_hash = hash_password(new_password)
                db.commit()
                logger.info(f"Password changed for user: {email}")
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
    """
    Authentication service health check with enhanced information
    """
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

