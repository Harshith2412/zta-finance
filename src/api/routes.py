"""
API Routes for ZTA-Finance
Protected endpoints with ZTA enforcement
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

from src.identity.authenticator import Authenticator
from src.identity.token_manager import TokenManager
from src.policy.pep import PolicyEnforcementPoint
from src.services.account_service import AccountService
from src.services.transaction_service import TransactionService
from src.services.payment_service import PaymentService
from src.audit.audit_logger import AuditLogger, EventType, EventSeverity

# Request/Response Models

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    

class LoginRequest(BaseModel):
    username: str
    password: str
    mfa_token: Optional[str] = None
    device_info: Optional[dict] = {}


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TransactionRequest(BaseModel):
    account_id: str
    transaction_type: str
    amount: float
    description: Optional[str] = None


class PaymentRequest(BaseModel):
    from_account_id: str
    to_account_id: str
    amount: float
    description: Optional[str] = None


class AccountResponse(BaseModel):
    account_id: str
    account_number: str
    account_type: str
    balance: float
    currency: str
    status: str


class TransactionResponse(BaseModel):
    transaction_id: str
    account_id: str
    transaction_type: str
    amount: float
    balance_after: float
    status: str
    created_at: datetime


# Initialize router
router = APIRouter()


# Authentication Routes

@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    data: RegisterRequest,
    authenticator: Authenticator = Depends(),
    audit_logger: AuditLogger = Depends()
):
    """Register a new user"""
    
    # Hash password
    password_hash = authenticator.hash_password(data.password)
    
    # In production, store in database
    # For now, return success
    
    audit_logger.log_event(
        event_type=EventType.AUTHENTICATION,
        severity=EventSeverity.INFO,
        user_id=data.username,
        action="user_registration",
        ip_address=request.state.ip_address,
        success=True
    )
    
    return {
        "message": "User registered successfully",
        "username": data.username,
        "email": data.email
    }


@router.post("/auth/login", response_model=LoginResponse)
async def login(
    request: Request,
    data: LoginRequest,
    authenticator: Authenticator = Depends(),
    token_manager: TokenManager = Depends(),
    audit_logger: AuditLogger = Depends()
):
    """Authenticate user and issue tokens"""
    
    # Verify credentials (in production, check database)
    # For demo purposes, accepting any valid request
    
    user_id = f"user_{data.username}"
    device_id = request.state.device_id or "device_unknown"
    
    # Generate tokens
    access_token = token_manager.create_access_token(
        subject=data.username,
        user_id=user_id,
        roles=["account_holder"],
        device_id=device_id,
        additional_claims={"mfa_verified": bool(data.mfa_token)}
    )
    
    refresh_token = token_manager.create_refresh_token(user_id, device_id)
    
    # Log authentication
    audit_logger.log_authentication(
        user_id=user_id,
        success=True,
        method="password_mfa" if data.mfa_token else "password",
        ip_address=request.state.ip_address,
        device_id=device_id
    )
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=900  # 15 minutes
    )


@router.post("/auth/logout")
async def logout(
    current_user: dict = Depends(),
    token_manager: TokenManager = Depends(),
    audit_logger: AuditLogger = Depends()
):
    """Logout and invalidate tokens"""
    
    user_id = current_user["user_id"]
    device_id = current_user["device_id"]
    
    # Revoke tokens
    token_manager.revoke_refresh_token(user_id, device_id)
    
    audit_logger.log_event(
        event_type=EventType.AUTHENTICATION,
        severity=EventSeverity.INFO,
        user_id=user_id,
        action="user_logout",
        success=True
    )
    
    return {"message": "Logged out successfully"}


# Account Routes

@router.get("/accounts", response_model=List[AccountResponse])
async def get_accounts(
    request: Request,
    current_user: dict = Depends(),
    context: dict = Depends(),
    pep: PolicyEnforcementPoint = Depends(),
    account_service: AccountService = Depends(),
    audit_logger: AuditLogger = Depends()
):
    """Get user accounts"""
    
    # Enforce policy
    pep.enforce(
        user_id=current_user["user_id"],
        resource="account",
        action="read",
        request_context=context
    )
    
    # Get accounts
    accounts = account_service.get_user_accounts(current_user["user_id"])
    
    # Log access
    audit_logger.log_data_access(
        user_id=current_user["user_id"],
        resource="account",
        action="read",
        record_count=len(accounts)
    )
    
    return accounts


@router.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: str,
    request: Request,
    current_user: dict = Depends(),
    context: dict = Depends(),
    pep: PolicyEnforcementPoint = Depends(),
    account_service: AccountService = Depends(),
    audit_logger: AuditLogger = Depends()
):
    """Get specific account"""
    
    # Enforce policy
    pep.enforce(
        user_id=current_user["user_id"],
        resource="account",
        action="read",
        request_context=context
    )
    
    # Get account
    account = account_service.get_account(account_id, current_user["user_id"])
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Log access
    audit_logger.log_data_access(
        user_id=current_user["user_id"],
        resource="account",
        action="read"
    )
    
    return account


# Transaction Routes

@router.get("/transactions", response_model=List[TransactionResponse])
async def get_transactions(
    account_id: Optional[str] = None,
    limit: int = 50,
    current_user: dict = Depends(),
    context: dict = Depends(),
    pep: PolicyEnforcementPoint = Depends(),
    transaction_service: TransactionService = Depends(),
    audit_logger: AuditLogger = Depends()
):
    """Get transactions"""
    
    # Enforce policy
    pep.enforce(
        user_id=current_user["user_id"],
        resource="transaction",
        action="read",
        request_context=context
    )
    
    # Get transactions
    transactions = transaction_service.get_transactions(
        user_id=current_user["user_id"],
        account_id=account_id,
        limit=limit
    )
    
    # Log access
    audit_logger.log_data_access(
        user_id=current_user["user_id"],
        resource="transaction",
        action="read",
        record_count=len(transactions)
    )
    
    return transactions


@router.post("/transactions", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    data: TransactionRequest,
    current_user: dict = Depends(),
    context: dict = Depends(),
    pep: PolicyEnforcementPoint = Depends(),
    transaction_service: TransactionService = Depends(),
    audit_logger: AuditLogger = Depends()
):
    """Create a new transaction"""
    
    # Add transaction amount to context for risk assessment
    context["transaction_amount"] = data.amount
    
    # Enforce policy
    pep.enforce(
        user_id=current_user["user_id"],
        resource="transaction",
        action="create",
        request_context=context
    )
    
    # Create transaction
    transaction = transaction_service.create_transaction(
        user_id=current_user["user_id"],
        account_id=data.account_id,
        transaction_type=data.transaction_type,
        amount=data.amount,
        description=data.description
    )
    
    # Log transaction
    audit_logger.log_transaction(
        user_id=current_user["user_id"],
        transaction_type=data.transaction_type,
        amount=data.amount,
        account_id=data.account_id,
        success=True,
        transaction_id=transaction["transaction_id"]
    )
    
    return transaction


# Payment Routes

@router.post("/payments", status_code=status.HTTP_201_CREATED)
async def create_payment(
    data: PaymentRequest,
    current_user: dict = Depends(),
    context: dict = Depends(),
    pep: PolicyEnforcementPoint = Depends(),
    payment_service: PaymentService = Depends(),
    audit_logger: AuditLogger = Depends()
):
    """Execute a payment"""
    
    # Add payment amount to context
    context["transaction_amount"] = data.amount
    
    # Enforce policy
    pep.enforce(
        user_id=current_user["user_id"],
        resource="payment",
        action="execute",
        request_context=context
    )
    
    # Execute payment
    payment = payment_service.execute_payment(
        user_id=current_user["user_id"],
        from_account_id=data.from_account_id,
        to_account_id=data.to_account_id,
        amount=data.amount,
        description=data.description
    )
    
    # Log payment
    audit_logger.log_transaction(
        user_id=current_user["user_id"],
        transaction_type="payment",
        amount=data.amount,
        account_id=data.from_account_id,
        success=True,
        details={
            "to_account": data.to_account_id,
            "payment_id": payment["payment_id"]
        }
    )
    
    return payment


# Health and Status

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "zta-finance"
    }


@router.get("/status")
async def status_check(
    current_user: dict = Depends()
):
    """Authenticated status check"""
    return {
        "status": "authenticated",
        "user_id": current_user["user_id"],
        "roles": current_user.get("roles", []),
        "timestamp": datetime.utcnow().isoformat()
    }