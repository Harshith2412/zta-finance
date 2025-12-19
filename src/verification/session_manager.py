import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import secrets

from config.settings import settings
from config.logging import get_logger

logger = get_logger(__name__)


class SessionManager:
    """Continuous session monitoring and management"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.session_timeout = settings.session_timeout_minutes * 60  # Convert to seconds
    
    def create_session(
        self,
        user_id: str,
        device_id: str,
        ip_address: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create new session"""
        
        session_id = secrets.token_urlsafe(32)
        
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "device_id": device_id,
            "ip_address": ip_address,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "activity_count": 0,
            "metadata": metadata or {}
        }
        
        key = f"session:{session_id}"
        self.redis.setex(key, self.session_timeout, json.dumps(session_data))
        
        # Add to user's active sessions
        user_sessions_key = f"user_sessions:{user_id}"
        self.redis.sadd(user_sessions_key, session_id)
        self.redis.expire(user_sessions_key, self.session_timeout)
        
        logger.info(f"Session created - User: {user_id}, Session: {session_id}")
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data"""
        
        key = f"session:{session_id}"
        session_data = self.redis.get(key)
        
        if not session_data:
            return None
        
        return json.loads(session_data)
    
    def update_session_activity(self, session_id: str) -> bool:
        """Update session last activity timestamp"""
        
        session = self.get_session(session_id)
        
        if not session:
            return False
        
        session["last_activity"] = datetime.utcnow().isoformat()
        session["activity_count"] += 1
        
        key = f"session:{session_id}"
        self.redis.setex(key, self.session_timeout, json.dumps(session))
        
        return True
    
    def verify_session(
        self,
        session_id: str,
        device_id: str,
        ip_address: str
    ) -> Dict[str, Any]:
        """
        Verify session and check for anomalies
        
        Returns:
            {
                "valid": bool,
                "anomalies": list[str],
                "session": dict
            }
        """
        
        session = self.get_session(session_id)
        
        if not session:
            return {
                "valid": False,
                "anomalies": ["session_not_found"],
                "session": None
            }
        
        anomalies = []
        
        # Check device consistency
        if session["device_id"] != device_id:
            anomalies.append("device_mismatch")
            logger.warning(f"Device mismatch for session: {session_id}")
        
        # Check IP address consistency
        if session["ip_address"] != ip_address:
            anomalies.append("ip_address_change")
            logger.warning(f"IP address changed for session: {session_id}")
        
        # Check session freshness
        last_activity = datetime.fromisoformat(session["last_activity"])
        time_since_activity = (datetime.utcnow() - last_activity).total_seconds()
        
        if time_since_activity > self.session_timeout:
            anomalies.append("session_expired")
            self.invalidate_session(session_id)
            return {
                "valid": False,
                "anomalies": anomalies,
                "session": None
            }
        
        # Update activity
        self.update_session_activity(session_id)
        
        return {
            "valid": len(anomalies) == 0,
            "anomalies": anomalies,
            "session": session
        }
    
    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate/terminate session"""
        
        session = self.get_session(session_id)
        
        if not session:
            return False
        
        # Remove from Redis
        key = f"session:{session_id}"
        self.redis.delete(key)
        
        # Remove from user's active sessions
        user_id = session["user_id"]
        user_sessions_key = f"user_sessions:{user_id}"
        self.redis.srem(user_sessions_key, session_id)
        
        logger.info(f"Session invalidated - Session: {session_id}, User: {user_id}")
        
        return True
    
    def invalidate_all_user_sessions(self, user_id: str) -> int:
        """Invalidate all sessions for a user"""
        
        user_sessions_key = f"user_sessions:{user_id}"
        session_ids = self.redis.smembers(user_sessions_key)
        
        count = 0
        for session_id in session_ids:
            if isinstance(session_id, bytes):
                session_id = session_id.decode()
            
            if self.invalidate_session(session_id):
                count += 1
        
        # Clean up user sessions set
        self.redis.delete(user_sessions_key)
        
        logger.info(f"All sessions invalidated for user: {user_id}, count: {count}")
        
        return count
    
    def get_user_sessions(self, user_id: str) -> list[Dict[str, Any]]:
        """Get all active sessions for a user"""
        
        user_sessions_key = f"user_sessions:{user_id}"
        session_ids = self.redis.smembers(user_sessions_key)
        
        sessions = []
        for session_id in session_ids:
            if isinstance(session_id, bytes):
                session_id = session_id.decode()
            
            session = self.get_session(session_id)
            if session:
                sessions.append(session)
        
        return sessions
    
    def is_session_fresh(self, session_id: str, max_age_minutes: int = 5) -> bool:
        """Check if session activity is recent (for high-security operations)"""
        
        session = self.get_session(session_id)
        
        if not session:
            return False
        
        last_activity = datetime.fromisoformat(session["last_activity"])
        age_seconds = (datetime.utcnow() - last_activity).total_seconds()
        
        return age_seconds <= (max_age_minutes * 60)