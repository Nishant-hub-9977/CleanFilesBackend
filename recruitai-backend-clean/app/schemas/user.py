"""
User schemas for request/response validation
"""

from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: EmailStr
    company_name: str
    phone_number: Optional[str] = None
    role: str = "user"

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    company_name: Optional[str] = None
    phone_number: Optional[str] = None
    bio: Optional[str] = None
    
    @validator('username')
    def validate_username(cls, v):
        if v is not None and len(v) < 3:
            raise ValueError('Username must be at least 3 characters long')
        return v

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    profile_picture: Optional[str] = None
    bio: Optional[str] = None
    
    class Config:
        from_attributes = True

class UserProfile(BaseModel):
    id: int
    username: str
    email: str
    company_name: str
    phone_number: Optional[str] = None
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    profile_picture: Optional[str] = None
    bio: Optional[str] = None
    
    # Statistics
    total_jobs: Optional[int] = 0
    total_candidates: Optional[int] = 0
    total_interviews: Optional[int] = 0
    credits_balance: Optional[int] = 0
    
    class Config:
        from_attributes = True

class UserStats(BaseModel):
    total_users: int
    active_users: int
    new_users_this_month: int
    total_companies: int

