from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from config.settings import settings
from config.logging import get_logger

logger = get_logger(__name__)


class TokenManager:
    """JWT token generation and verification"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.access_token_expire = timedelta(minutes=settings.jwt_access_token_expire_minutes)
        self.refresh_token_expire = timedelta(days=settings.jwt_refresh_token_expire_days)
    
    def create_access_token(
        self,
        subject: str,
        user_id: str,
        roles: list,
        device_id: str,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create JWT access token"""
        
        expires_delta = datetime.utcnow() + self.access_token_expire
        
        claims = {
            "sub": subject,
            "user_id": user_id,
            "roles": roles,
            "device_id": device_id,
            "exp": expires_delta,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        if additional_claims:
            claims.update(additional_claims)
        
        token = jwt.encode(claims, self.secret_key, algorithm=self.algorithm)
        
        logger.info(f"Access token created for user: {user_id}")
        return token
    
    def create_refresh_token(self, user_id: str, device_id: str) -> str:
        """Create JWT refresh token"""
        
        expires_delta = datetime.utcnow() + self.refresh_token_expire
        
        claims = {
            "user_id": user_id,
            "device_id": device_id,
            "exp": expires_delta,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        
        token = jwt.encode(claims, self.secret_key, algorithm=self.algorithm)
        
        # Store refresh token in Redis for revocation capability
        key = f"refresh_token:{user_id}:{device_id}"
        self.redis.setex(key, int(self.refresh_token_expire.total_seconds()), token)
        
        logger.info(f"Refresh token created for user: {user_id}")
        return token
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # Check token type
            if payload.get("type") != token_type:
                logger.warning(f"Invalid token type. Expected: {token_type}")
                return None
            
            # Check if token is blacklisted
            if self.is_token_blacklisted(token):
                logger.warning("Token is blacklisted")
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            return None
    
    def blacklist_token(self, token: str):
        """Add token to blacklist"""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )
            
            exp = payload.get("exp")
            if exp:
                # Calculate time until expiration
                exp_datetime = datetime.fromtimestamp(exp)
                ttl = int((exp_datetime - datetime.utcnow()).total_seconds())
                
                if ttl > 0:
                    key = f"blacklist:{token}"
                    self.redis.setex(key, ttl, "1")
                    logger.info("Token blacklisted successfully")
        except Exception as e:
            logger.error(f"Error blacklisting token: {str(e)}")
    
    def is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted"""
        key = f"blacklist:{token}"
        return self.redis.exists(key) > 0
    
    def revoke_refresh_token(self, user_id: str, device_id: str):
        """Revoke refresh token"""
        key = f"refresh_token:{user_id}:{device_id}"
        self.redis.delete(key)
        logger.info(f"Refresh token revoked for user: {user_id}, device: {device_id}")
    
    def revoke_all_user_tokens(self, user_id: str):
        """Revoke all tokens for a user"""
        pattern = f"refresh_token:{user_id}:*"
        
        for key in self.redis.scan_iter(match=pattern):
            self.redis.delete(key)
        
        logger.info(f"All tokens revoked for user: {user_id}")