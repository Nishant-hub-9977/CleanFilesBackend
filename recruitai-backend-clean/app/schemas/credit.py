"""
Credit schemas for request/response validation
"""

from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime

class CreditBase(BaseModel):
    amount: int
    transaction_type: str
    description: Optional[str] = None
    reference_id: Optional[str] = None

class CreditCreate(CreditBase):
    user_id: int

class CreditResponse(CreditBase):
    id: int
    balance_after: int
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    amount_paid: Optional[float] = None
    currency: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    user_id: int
    
    class Config:
        from_attributes = True

class CreditBalance(BaseModel):
    user_id: int
    current_balance: int
    total_earned: int
    total_spent: int
    last_transaction: Optional[datetime] = None

class CreditPurchase(BaseModel):
    amount: int
    payment_method: str = "stripe"
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        if v > 1000:
            raise ValueError('Maximum purchase amount is 1000 credits')
        return v

class CreditUsage(BaseModel):
    amount: int
    transaction_type: str
    description: str
    reference_id: Optional[str] = None
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Usage amount must be positive')
        return v

class CreditStats(BaseModel):
    total_credits_issued: int
    total_credits_used: int
    total_revenue: float
    active_users_with_credits: int

