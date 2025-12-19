"""
Transaction Service
Handles transaction processing and history
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from config.logging import get_logger
from src.services.account_service import AccountService

logger = get_logger(__name__)


class TransactionService:
    """Service for managing financial transactions"""
    
    def __init__(self, db_session=None, account_service: AccountService = None):
        self.db = db_session
        self.account_service = account_service or AccountService(db_session)
    
    def create_transaction(
        self,
        user_id: str,
        account_id: str,
        transaction_type: str,
        amount: float,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new transaction"""
        
        # Verify account ownership
        if not self.account_service.verify_account_ownership(account_id, user_id):
            raise ValueError("Account does not belong to user")
        
        # Validate amount
        if amount <= 0:
            raise ValueError("Transaction amount must be positive")
        
        # Check balance for withdrawals
        if transaction_type in ["withdrawal", "debit"]:
            current_balance = self.account_service.get_account_balance(account_id)
            if current_balance < amount:
                raise ValueError("Insufficient funds")
        
        transaction_id = str(uuid.uuid4())
        
        # Calculate new balance
        current_balance = self.account_service.get_account_balance(account_id)
        
        if transaction_type in ["deposit", "credit"]:
            balance_after = current_balance + amount
        else:
            balance_after = current_balance - amount
        
        transaction = {
            "transaction_id": transaction_id,
            "account_id": account_id,
            "transaction_type": transaction_type,
            "amount": amount,
            "balance_after": balance_after,
            "description": description,
            "status": "completed",
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat()
        }
        
        # Update account balance
        operation = "add" if transaction_type in ["deposit", "credit"] else "subtract"
        self.account_service.update_balance(account_id, amount, operation)
        
        # In production, save to database within transaction
        logger.info(
            f"Transaction created - ID: {transaction_id}, "
            f"Type: {transaction_type}, Amount: {amount}"
        )
        
        return transaction
    
    def get_transaction(self, transaction_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get transaction by ID"""
        
        # In production, query database and verify ownership
        transaction = {
            "transaction_id": transaction_id,
            "account_id": "acc_001",
            "transaction_type": "deposit",
            "amount": 1000.00,
            "balance_after": 11000.00,
            "status": "completed",
            "created_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Transaction retrieved: {transaction_id}")
        return transaction
    
    def get_transactions(
        self,
        user_id: str,
        account_id: Optional[str] = None,
        transaction_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get transactions with filters"""
        
        # In production, query database with filters
        # For demo, return mock data
        transactions = [
            {
                "transaction_id": "txn_001",
                "account_id": account_id or "acc_001",
                "transaction_type": "deposit",
                "amount": 1000.00,
                "balance_after": 11000.00,
                "status": "completed",
                "created_at": "2024-12-18T10:00:00Z"
            },
            {
                "transaction_id": "txn_002",
                "account_id": account_id or "acc_001",
                "transaction_type": "withdrawal",
                "amount": 500.00,
                "balance_after": 10500.00,
                "status": "completed",
                "created_at": "2024-12-18T11:00:00Z"
            }
        ]
        
        logger.info(f"Retrieved {len(transactions)} transactions for user: {user_id}")
        return transactions[:limit]
    
    def reverse_transaction(
        self,
        transaction_id: str,
        user_id: str,
        reason: str
    ) -> Dict[str, Any]:
        """Reverse a transaction"""
        
        # Get original transaction
        original = self.get_transaction(transaction_id, user_id)
        
        if not original:
            raise ValueError("Transaction not found")
        
        if original["status"] != "completed":
            raise ValueError("Can only reverse completed transactions")
        
        # Create reversal transaction
        reversal_type = "credit" if original["transaction_type"] in ["withdrawal", "debit"] else "debit"
        
        reversal = self.create_transaction(
            user_id=user_id,
            account_id=original["account_id"],
            transaction_type=reversal_type,
            amount=original["amount"],
            description=f"Reversal of {transaction_id}: {reason}",
            metadata={
                "original_transaction_id": transaction_id,
                "reversal_reason": reason
            }
        )
        
        logger.warning(
            f"Transaction reversed - Original: {transaction_id}, "
            f"Reversal: {reversal['transaction_id']}"
        )
        
        return reversal
    
    def get_pending_transactions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all pending transactions for user"""
        
        # In production, query database
        transactions = []
        
        logger.info(f"Retrieved {len(transactions)} pending transactions for user: {user_id}")
        return transactions
    
    def approve_transaction(self, transaction_id: str, user_id: str) -> bool:
        """Approve a pending transaction"""
        
        # In production, update transaction status
        logger.info(f"Transaction approved: {transaction_id} by user: {user_id}")
        
        return True
    
    def reject_transaction(
        self,
        transaction_id: str,
        user_id: str,
        reason: str
    ) -> bool:
        """Reject a pending transaction"""
        
        # In production, update transaction status
        logger.warning(
            f"Transaction rejected: {transaction_id} by user: {user_id}, "
            f"Reason: {reason}"
        )
        
        return True
    
    def get_transaction_summary(
        self,
        user_id: str,
        account_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get transaction summary statistics"""
        
        # In production, calculate from database
        summary = {
            "total_transactions": 10,
            "total_deposits": 5000.00,
            "total_withdrawals": 2000.00,
            "net_change": 3000.00,
            "average_transaction": 700.00
        }
        
        logger.info(f"Transaction summary generated for user: {user_id}")
        
        return summary
    
    def search_transactions(
        self,
        user_id: str,
        query: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search transactions by description or metadata"""
        
        # In production, full-text search in database
        transactions = []
        
        logger.info(f"Transaction search - User: {user_id}, Query: {query}")
        
        return transactions