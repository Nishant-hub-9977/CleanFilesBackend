"""
Credit model for tracking user credits and usage
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..core.database import Base

class Credit(Base):
    __tablename__ = "credits"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Credit details
    amount = Column(Integer, nullable=False)  # Credit amount (positive for add, negative for deduct)
    balance_after = Column(Integer, nullable=False)  # Balance after this transaction
    
    # Transaction details
    transaction_type = Column(String(50), nullable=False)  # signup_bonus, purchase, interview_usage, resume_analysis
    description = Column(Text, nullable=True)
    reference_id = Column(String(100), nullable=True)  # Reference to related entity (interview_id, resume_id, etc.)
    
    # Payment details (for purchases)
    payment_method = Column(String(50), nullable=True)  # stripe, paypal, etc.
    payment_reference = Column(String(100), nullable=True)
    amount_paid = Column(Float, nullable=True)  # Amount paid in currency
    currency = Column(String(10), nullable=True)
    
    # Status
    status = Column(String(50), default="completed")  # pending, completed, failed, refunded
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="credits")
    
    def __repr__(self):
        return f"<Credit(id={self.id}, user_id={self.user_id}, amount={self.amount}, type='{self.transaction_type}')>"

