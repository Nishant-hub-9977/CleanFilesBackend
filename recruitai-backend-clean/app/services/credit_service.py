"""
Credit management service for handling user credits and transactions
"""

from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from ..models.credit import Credit
from ..models.user import User

async def get_user_credit_balance(user_id: int, db: Session) -> int:
    """Get current credit balance for user"""
    
    latest_credit = db.query(Credit).filter(
        Credit.user_id == user_id
    ).order_by(Credit.created_at.desc()).first()
    
    return latest_credit.balance_after if latest_credit else 0

async def deduct_credits(
    user_id: int, 
    amount: int, 
    transaction_type: str, 
    db: Session,
    description: Optional[str] = None,
    reference_id: Optional[str] = None
) -> bool:
    """Deduct credits from user account"""
    
    if amount <= 0:
        return False
    
    # Get current balance
    current_balance = await get_user_credit_balance(user_id, db)
    
    # Check if user has enough credits
    if current_balance < amount:
        return False
    
    # Create deduction transaction
    credit_transaction = Credit(
        user_id=user_id,
        amount=-amount,  # Negative for deduction
        balance_after=current_balance - amount,
        transaction_type=transaction_type,
        description=description or f"Credit usage: {transaction_type}",
        reference_id=reference_id,
        status="completed"
    )
    
    db.add(credit_transaction)
    db.commit()
    
    return True

async def add_credits(
    user_id: int,
    amount: int,
    transaction_type: str,
    db: Session,
    description: Optional[str] = None,
    reference_id: Optional[str] = None,
    payment_method: Optional[str] = None,
    payment_reference: Optional[str] = None,
    amount_paid: Optional[float] = None,
    currency: Optional[str] = None
) -> bool:
    """Add credits to user account"""
    
    if amount <= 0:
        return False
    
    # Get current balance
    current_balance = await get_user_credit_balance(user_id, db)
    
    # Create addition transaction
    credit_transaction = Credit(
        user_id=user_id,
        amount=amount,  # Positive for addition
        balance_after=current_balance + amount,
        transaction_type=transaction_type,
        description=description or f"Credit purchase: {amount} credits",
        reference_id=reference_id,
        payment_method=payment_method,
        payment_reference=payment_reference,
        amount_paid=amount_paid,
        currency=currency,
        status="completed"
    )
    
    db.add(credit_transaction)
    db.commit()
    
    return True

async def get_credit_history(
    user_id: int, 
    db: Session, 
    skip: int = 0, 
    limit: int = 100
) -> list:
    """Get credit transaction history for user"""
    
    credits = db.query(Credit).filter(
        Credit.user_id == user_id
    ).order_by(Credit.created_at.desc()).offset(skip).limit(limit).all()
    
    return credits

async def get_credit_statistics(user_id: int, db: Session) -> dict:
    """Get credit statistics for user"""
    
    # Total credits earned (positive transactions)
    total_earned = db.query(Credit).filter(
        Credit.user_id == user_id,
        Credit.amount > 0
    ).with_entities(db.func.sum(Credit.amount)).scalar() or 0
    
    # Total credits spent (negative transactions)
    total_spent = abs(db.query(Credit).filter(
        Credit.user_id == user_id,
        Credit.amount < 0
    ).with_entities(db.func.sum(Credit.amount)).scalar() or 0)
    
    # Current balance
    current_balance = await get_user_credit_balance(user_id, db)
    
    # Last transaction date
    last_transaction = db.query(Credit).filter(
        Credit.user_id == user_id
    ).order_by(Credit.created_at.desc()).first()
    
    return {
        "current_balance": current_balance,
        "total_earned": total_earned,
        "total_spent": total_spent,
        "last_transaction": last_transaction.created_at if last_transaction else None
    }

async def process_credit_purchase(
    user_id: int,
    amount: int,
    payment_method: str,
    payment_reference: str,
    amount_paid: float,
    currency: str,
    db: Session
) -> bool:
    """Process credit purchase transaction"""
    
    try:
        # Add credits to user account
        success = await add_credits(
            user_id=user_id,
            amount=amount,
            transaction_type="purchase",
            db=db,
            description=f"Credit purchase: {amount} credits",
            payment_method=payment_method,
            payment_reference=payment_reference,
            amount_paid=amount_paid,
            currency=currency
        )
        
        return success
        
    except Exception as e:
        print(f"Error processing credit purchase: {e}")
        return False

async def refund_credits(
    user_id: int,
    amount: int,
    original_transaction_id: str,
    db: Session,
    reason: Optional[str] = None
) -> bool:
    """Refund credits to user account"""
    
    try:
        # Add credits back to user account
        success = await add_credits(
            user_id=user_id,
            amount=amount,
            transaction_type="refund",
            db=db,
            description=f"Credit refund: {reason or 'Refund processed'}",
            reference_id=original_transaction_id
        )
        
        return success
        
    except Exception as e:
        print(f"Error processing credit refund: {e}")
        return False

