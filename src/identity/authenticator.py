import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets

from config.logging import get_logger

logger = get_logger(__name__)
ph = PasswordHasher()


class Authenticator:
    """Multi-factor authentication handler"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        
    def hash_password(self, password: str) -> str:
        """Hash password using Argon2"""
        return ph.hash(password)
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            ph.verify(password_hash, password)
            
            # Check if rehashing is needed
            if ph.check_needs_rehash(password_hash):
                return {"verified": True, "rehash_needed": True}
            
            return {"verified": True, "rehash_needed": False}
        except VerifyMismatchError:
            logger.warning("Password verification failed")
            return {"verified": False, "rehash_needed": False}
    
    def generate_mfa_secret(self) -> str:
        """Generate TOTP secret for MFA"""
        return pyotp.random_base32()
    
    def get_mfa_uri(self, secret: str, username: str, issuer: str = "ZTA-Finance") -> str:
        """Generate provisioning URI for QR code"""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=username, issuer_name=issuer)
    
    def verify_mfa_token(self, secret: str, token: str) -> bool:
        """Verify TOTP token"""
        totp = pyotp.TOTP(secret)
        is_valid = totp.verify(token, valid_window=1)
        
        if is_valid:
            # Prevent token reuse
            token_key = f"mfa_used:{secret}:{token}"
            if self.redis.exists(token_key):
                logger.warning("MFA token reuse attempt detected")
                return False
            
            # Mark token as used (30 second window)
            self.redis.setex(token_key, 30, "1")
            
        return is_valid
    
    def track_failed_attempt(self, username: str) -> Dict[str, Any]:
        """Track failed login attempts"""
        key = f"failed_attempts:{username}"
        attempts = self.redis.incr(key)
        
        if attempts == 1:
            # Set expiry on first attempt
            self.redis.expire(key, 1800)  # 30 minutes
        
        logger.warning(f"Failed login attempt for {username}, count: {attempts}")
        
        return {
            "attempts": attempts,
            "locked": attempts >= 5,
            "lockout_duration": 1800 if attempts >= 5 else 0
        }
    
    def clear_failed_attempts(self, username: str):
        """Clear failed attempt counter"""
        key = f"failed_attempts:{username}"
        self.redis.delete(key)
    
    def is_account_locked(self, username: str) -> bool:
        """Check if account is locked due to failed attempts"""
        key = f"failed_attempts:{username}"
        attempts = self.redis.get(key)
        return int(attempts or 0) >= 5
    
    def generate_reset_token(self, username: str) -> str:
        """Generate secure password reset token"""
        token = secrets.token_urlsafe(32)
        key = f"reset_token:{token}"
        
        # Store token with 1 hour expiry
        self.redis.setex(key, 3600, username)
        
        logger.info(f"Password reset token generated for {username}")
        return token
    
    def verify_reset_token(self, token: str) -> Optional[str]:
        """Verify and consume reset token"""
        key = f"reset_token:{token}"
        username = self.redis.get(key)
        
        if username:
            # Delete token after use (one-time use)
            self.redis.delete(key)
            return username.decode() if isinstance(username, bytes) else username
        
        return None