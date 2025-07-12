import os
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db, Base
from ..schemas.auth import UserRegister, UserLogin, Token, TokenData, PasswordReset, PasswordResetConfirm, ChangePassword  # Import and use schemas

router = APIRouter(prefix="/auth", tags=["auth"])

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")  # Env-safe
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)  # Added from schema
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    company_name = Column(String)  # Added
    phone_number = Column(String, nullable=True)  # Added
    role = Column(String, default="user")  # Aligned

async def get_user(db: AsyncSession, identifier: str):  # username or email
    query = select(UserDB).where((UserDB.email == identifier) | (UserDB.username == identifier))
    result = await db.execute(query)
    return result.scalar_one_or_none()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        identifier: str = payload.get("sub")
        if identifier is None:
            raise credentials_exception
        token_data = TokenData(user_id=payload.get("user_id"))
    except JWTError:
        raise credentials_exception
    user = await get_user(db, identifier)
    if user is None:
        raise credentials_exception
    return user

@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: UserLogin = Depends(), db: AsyncSession = Depends(get_db)):  # Use schema
    user = await get_user(db, form_data.username_or_email)
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Failed login for {form_data.username_or_email}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials")
    access_token = create_token({"sub": user.email, "user_id": user.id}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    refresh_token = create_token({"sub": user.email, "user_id": user.id}, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    logger.info(f"Successful login for {user.email}")
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/register", response_model=Token)
async def register_user(user_data: UserRegister, db: AsyncSession = Depends(get_db)):  # Use schema (auto-validates)
    existing_user = await get_user(db, user_data.email) or await get_user(db, user_data.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email or username already registered")
    hashed_password = get_password_hash(user_data.password)
    new_user = UserDB(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        company_name=user_data.company_name,
        phone_number=user_data.phone_number,
        role=user_data.role
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    access_token = create_token({"sub": new_user.email, "user_id": new_user.id}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    refresh_token = create_token({"sub": new_user.email, "user_id": new_user.id}, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    logger.info(f"New user registered: {user_data.email}")
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/password-reset")
async def password_reset(reset_data: PasswordReset, db: AsyncSession = Depends(get_db)):  # New from schema
    user = await get_user(db, reset_data.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    reset_token = create_token({"sub": user.email, "scope": "reset", "user_id": user.id}, timedelta(minutes=30))
    logger.info(f"Password reset requested for {reset_data.email}")
    return {"message": "Reset token sent", "token": reset_token}  # In prod, email token instead

@router.post("/password-reset-confirm")
async def password_reset_confirm(confirm_data: PasswordResetConfirm, db: AsyncSession = Depends(get_db)):  # New from schema
    try:
        payload = jwt.decode(confirm_data.token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("scope") != "reset":
            raise JWTError
        email = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user = await get_user(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    hashed_password = get_password_hash(confirm_data.new_password)
    user.hashed_password = hashed_password
    await db.commit()
    logger.info(f"Password reset for {email}")
    return {"message": "Password reset successful"}

@router.post("/change-password")
async def change_password(change_data: ChangePassword, current_user: UserDB = Depends(get_current_user), db: AsyncSession = Depends(get_db)):  # New from schema
    if not verify_password(change_data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    hashed_password = get_password_hash(change_data.new_password)
    current_user.hashed_password = hashed_password
    await db.commit()
    logger.info(f"Password changed for {current_user.email}")
    return {"message": "Password changed successfully"}

@router.get("/me", response_model=User)
async def read_users_me(current_user: UserDB = Depends(get_current_user)):
    return {"email": current_user.email, "role": current_user.role}
