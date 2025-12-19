from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
import redis
from datetime import datetime

from config.settings import settings
from config.logging import setup_logging, get_logger
from src.identity.authenticator import Authenticator
from src.identity.token_manager import TokenManager
from src.audit.audit_logger import AuditLogger, EventType, EventSeverity

# Setup logging
setup_logging(settings.log_level)
logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Zero Trust Architecture for Financial Systems"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Redis and components
redis_client = redis.from_url(settings.redis_url, decode_responses=False)
authenticator = Authenticator(redis_client)
token_manager = TokenManager(redis_client)
audit_logger = AuditLogger(redis_client)


# Request models
class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str
    mfa_token: str = None


# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


# Register
@app.post(f"{settings.api_prefix}/auth/register")
async def register(request: Request, data: RegisterRequest):
    password_hash = authenticator.hash_password(data.password)
    
    audit_logger.log_event(
        event_type=EventType.AUTHENTICATION,
        severity=EventSeverity.INFO,
        user_id=data.username,
        action="user_registration",
        ip_address=request.client.host,
        success=True
    )
    
    return {"message": "User registered successfully"}


# Login
@app.post(f"{settings.api_prefix}/auth/login")
async def login(request: Request, data: LoginRequest):
    user_id = f"user_{data.username}"
    device_id = "device_default"
    
    access_token = token_manager.create_access_token(
        subject=data.username,
        user_id=user_id,
        roles=["account_holder"],
        device_id=device_id,
        additional_claims={"mfa_verified": bool(data.mfa_token)}
    )
    
    refresh_token = token_manager.create_refresh_token(user_id, device_id)
    
    audit_logger.log_authentication(
        user_id=user_id,
        success=True,
        method="password",
        ip_address=request.client.host
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 900
    }


# Logout
@app.post(f"{settings.api_prefix}/auth/logout")
async def logout(request: Request):
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    token = auth_header.split(" ")[1]
    payload = token_manager.verify_token(token, "access")
    
    if payload:
        token_manager.blacklist_token(token)
        audit_logger.log_event(
            event_type=EventType.AUTHENTICATION,
            severity=EventSeverity.INFO,
            user_id=payload.get("user_id"),
            action="user_logout",
            success=True
        )
    
    return {"message": "Logged out successfully"}


# Get accounts
@app.get(f"{settings.api_prefix}/accounts")
async def get_accounts(request: Request):
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    token = auth_header.split(" ")[1]
    payload = token_manager.verify_token(token, "access")
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    audit_logger.log_data_access(
        user_id=payload["user_id"],
        resource="account",
        action="read"
    )
    
    return [
        {
            "account_id": "acc_001",
            "account_number": "ACC1234567890",
            "balance": 10000.00,
            "currency": "USD",
            "status": "active"
        },
        {
            "account_id": "acc_002",
            "account_number": "ACC0987654321",
            "balance": 25000.00,
            "currency": "USD",
            "status": "active"
        }
    ]


# Get status
@app.get(f"{settings.api_prefix}/status")
async def get_status(request: Request):
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    token = auth_header.split(" ")[1]
    payload = token_manager.verify_token(token, "access")
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return {
        "status": "authenticated",
        "user_id": payload["user_id"],
        "username": payload["sub"],
        "roles": payload.get("roles", []),
        "mfa_verified": payload.get("mfa_verified", False),
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
