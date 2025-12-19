"""
Payment Service
Handles payment processing and transfers
"""

from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from config.logging import get_logger
from src.services.account_service import AccountService
from src.services.transaction_service import TransactionService

logger = get_logger(__name__)


class PaymentService:
    """Service for managing payments and transfers"""
    
    def __init__(
        self,
        db_session=None,
        account_service: AccountService = None,
        transaction_service: TransactionService = None
    ):
        self.db = db_session
        self.account_service = account_service or AccountService(db_session)
        self.transaction_service = transaction_service or TransactionService(db_session)
    
    def execute_payment(
        self,
        user_id: str,
        from_account_id: str,
        to_account_id: str,
        amount: float,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a payment/transfer"""
        
        # Validate inputs
        if amount <= 0:
            raise ValueError("Payment amount must be positive")
        
        if from_account_id == to_account_id:
            raise ValueError("Cannot transfer to the same account")
        
        # Verify sender account ownership
        if not self.account_service.verify_account_ownership(from_account_id, user_id):
            raise ValueError("Source account does not belong to user")
        
        # Check sender balance
        sender_balance = self.account_service.get_account_balance(from_account_id)
        if sender_balance < amount:
            raise ValueError("Insufficient funds")
        
        payment_id = str(uuid.uuid4())
        
        try:
            # Create debit transaction for sender
            debit_txn = self.transaction_service.create_transaction(
                user_id=user_id,
                account_id=from_account_id,
                transaction_type="payment_debit",
                amount=amount,
                description=f"Payment to {to_account_id}: {description or ''}",
                metadata={
                    "payment_id": payment_id,
                    "to_account": to_account_id,
                    "payment_type": "transfer"
                }
            )
            
            # Create credit transaction for recipient
            # In production, get recipient user_id from account
            credit_txn = self.transaction_service.create_transaction(
                user_id="recipient_user",  # Would get from account lookup
                account_id=to_account_id,
                transaction_type="payment_credit",
                amount=amount,
                description=f"Payment from {from_account_id}: {description or ''}",
                metadata={
                    "payment_id": payment_id,
                    "from_account": from_account_id,
                    "payment_type": "transfer"
                }
            )
            
            payment = {
                "payment_id": payment_id,
                "from_account_id": from_account_id,
                "to_account_id": to_account_id,
                "amount": amount,
                "description": description,
                "status": "completed",
                "debit_transaction_id": debit_txn["transaction_id"],
                "credit_transaction_id": credit_txn["transaction_id"],
                "created_at": datetime.utcnow().isoformat(),
                "completed_at": datetime.utcnow().isoformat()
            }
            
            logger.info(
                f"Payment executed - ID: {payment_id}, "
                f"From: {from_account_id}, To: {to_account_id}, Amount: {amount}"
            )
            
            return payment
            
        except Exception as e:
            logger.error(f"Payment failed - ID: {payment_id}, Error: {str(e)}")
            raise
    
    def schedule_payment(
        self,
        user_id: str,
        from_account_id: str,
        to_account_id: str,
        amount: float,
        scheduled_date: datetime,
        description: Optional[str] = None,
        recurring: bool = False,
        frequency: Optional[str] = None
    ) -> Dict[str, Any]:
        """Schedule a future payment"""
        
        if scheduled_date <= datetime.utcnow():
            raise ValueError("Scheduled date must be in the future")
        
        payment_id = str(uuid.uuid4())
        
        scheduled_payment = {
            "payment_id": payment_id,
            "user_id": user_id,
            "from_account_id": from_account_id,
            "to_account_id": to_account_id,
            "amount": amount,
            "description": description,
            "status": "scheduled",
            "scheduled_date": scheduled_date.isoformat(),
            "recurring": recurring,
            "frequency": frequency,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # In production, save to database
        logger.info(
            f"Payment scheduled - ID: {payment_id}, "
            f"Date: {scheduled_date.isoformat()}"
        )
        
        return scheduled_payment
    
    def cancel_payment(self, payment_id: str, user_id: str) -> bool:
        """Cancel a scheduled payment"""
        
        # In production, verify ownership and update status
        logger.info(f"Payment cancelled - ID: {payment_id}, User: {user_id}")
        
        return True
    
    def get_payment(self, payment_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get payment details"""
        
        # In production, query database
        payment = {
            "payment_id": payment_id,
            "from_account_id": "acc_001",
            "to_account_id": "acc_002",
            "amount": 500.00,
            "status": "completed",
            "created_at": datetime.utcnow().isoformat()
        }
        
        return payment
    
    def get_user_payments(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> list[Dict[str, Any]]:
        """Get all payments for a user"""
        
        # In production, query database with filters
        payments = [
            {
                "payment_id": "pay_001",
                "from_account_id": "acc_001",
                "to_account_id": "acc_002",
                "amount": 500.00,
                "status": "completed",
                "created_at": "2024-12-18T12:00:00Z"
            }
        ]
        
        logger.info(f"Retrieved {len(payments)} payments for user: {user_id}")
        
        return payments
    
    def validate_payment_limit(
        self,
        user_id: str,
        account_id: str,
        amount: float
    ) -> Dict[str, Any]:
        """Validate payment against user limits"""
        
        # In production, check user's daily/transaction limits
        daily_limit = 10000.00
        transaction_limit = 5000.00
        
        validation = {
            "valid": True,
            "amount": amount,
            "daily_limit": daily_limit,
            "transaction_limit": transaction_limit,
            "daily_spent": 0.00,
            "remaining_daily": daily_limit,
            "exceeds_daily_limit": False,
            "exceeds_transaction_limit": amount > transaction_limit
        }
        
        if validation["exceeds_transaction_limit"]:
            validation["valid"] = False
            validation["reason"] = "Amount exceeds transaction limit"
        
        return validation
    
    def request_payment(
        self,
        user_id: str,
        from_user_id: str,
        amount: float,
        description: str
    ) -> Dict[str, Any]:
        """Create a payment request"""
        
        request_id = str(uuid.uuid4())
        
        payment_request = {
            "request_id": request_id,
            "from_user_id": from_user_id,
            "to_user_id": user_id,
            "amount": amount,
            "description": description,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow().timestamp() + 86400)  # 24 hours
        }
        
        # In production, save to database and notify user
        logger.info(f"Payment request created - ID: {request_id}")
        
        return payment_request
    
    def approve_payment_request(
        self,
        request_id: str,
        user_id: str,
        account_id: str
    ) -> Dict[str, Any]:
        """Approve and execute a payment request"""
        
        # In production, get request details and execute payment
        logger.info(f"Payment request approved - ID: {request_id}, User: {user_id}")
        
        return {
            "request_id": request_id,
            "status": "approved",
            "payment_id": str(uuid.uuid4())
        }
    
    def get_payment_history(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get payment history summary"""
        
        # In production, aggregate from database
        history = {
            "user_id": user_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_payments": 10,
            "total_amount_sent": 5000.00,
            "total_amount_received": 3000.00,
            "net_flow": -2000.00
        }
        
        return history