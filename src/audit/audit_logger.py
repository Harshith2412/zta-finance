import json
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

from src.encryption.data_encryptor import DataEncryptor
from config.settings import settings
from config.logging import get_logger

logger = get_logger("audit")
security_logger = get_logger("security")


class EventType(str, Enum):
    """Audit event types"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    CONFIGURATION_CHANGE = "configuration_change"
    SECURITY_EVENT = "security_event"
    TRANSACTION = "transaction"
    ADMIN_ACTION = "admin_action"


class EventSeverity(str, Enum):
    """Event severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditLogger:
    """Comprehensive audit logging with encryption support"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.encryptor = DataEncryptor() if settings.audit_log_encryption else None
    
    def log_event(
        self,
        event_type: EventType,
        severity: EventSeverity,
        user_id: Optional[str],
        action: str,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        device_id: Optional[str] = None,
        session_id: Optional[str] = None,
        success: bool = True
    ):
        """
        Log audit event
        
        Args:
            event_type: Type of event
            severity: Severity level
            user_id: User performing action
            action: Action performed
            resource: Resource affected
            details: Additional event details
            ip_address: Source IP address
            device_id: Device identifier
            session_id: Session identifier
            success: Whether action was successful
        """
        
        event = {
            "event_id": self._generate_event_id(),
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type.value,
            "severity": severity.value,
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "details": details or {},
            "ip_address": ip_address,
            "device_id": device_id,
            "session_id": session_id,
            "success": success
        }
        
        # Encrypt sensitive event data if configured
        if self.encryptor and settings.audit_log_encryption:
            event = self._encrypt_sensitive_fields(event)
        
        # Log to structured logger
        log_method = getattr(logger, severity.value.lower())
        log_method(
            f"{action} - User: {user_id or 'anonymous'}, "
            f"Resource: {resource or 'N/A'}, Success: {success}",
            extra=event
        )
        
        # Store in Redis for recent event queries
        self._store_event(event)
        
        # Log security events separately
        if event_type == EventType.SECURITY_EVENT or severity in [EventSeverity.ERROR, EventSeverity.CRITICAL]:
            security_logger.warning(
                f"Security event: {action}",
                extra=event
            )
    
    def log_authentication(
        self,
        user_id: str,
        success: bool,
        method: str = "password",
        ip_address: Optional[str] = None,
        device_id: Optional[str] = None,
        failure_reason: Optional[str] = None
    ):
        """Log authentication event"""
        
        details = {
            "method": method,
            "failure_reason": failure_reason if not success else None
        }
        
        self.log_event(
            event_type=EventType.AUTHENTICATION,
            severity=EventSeverity.WARNING if not success else EventSeverity.INFO,
            user_id=user_id,
            action=f"authentication_{method}_{'success' if success else 'failure'}",
            details=details,
            ip_address=ip_address,
            device_id=device_id,
            success=success
        )
    
    def log_authorization(
        self,
        user_id: str,
        resource: str,
        action: str,
        allowed: bool,
        reason: Optional[str] = None,
        risk_score: Optional[int] = None
    ):
        """Log authorization decision"""
        
        details = {
            "reason": reason,
            "risk_score": risk_score
        }
        
        self.log_event(
            event_type=EventType.AUTHORIZATION,
            severity=EventSeverity.WARNING if not allowed else EventSeverity.INFO,
            user_id=user_id,
            action=f"authorization_{'granted' if allowed else 'denied'}",
            resource=resource,
            details=details,
            success=allowed
        )
    
    def log_transaction(
        self,
        user_id: str,
        transaction_type: str,
        amount: float,
        account_id: str,
        success: bool,
        transaction_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log financial transaction"""
        
        transaction_details = {
            "transaction_type": transaction_type,
            "amount": amount,
            "account_id": account_id,
            "transaction_id": transaction_id,
            **(details or {})
        }
        
        self.log_event(
            event_type=EventType.TRANSACTION,
            severity=EventSeverity.INFO if success else EventSeverity.ERROR,
            user_id=user_id,
            action=f"transaction_{transaction_type}",
            resource="transaction",
            details=transaction_details,
            success=success
        )
    
    def log_data_access(
        self,
        user_id: str,
        resource: str,
        action: str,
        record_count: int = 1,
        query: Optional[str] = None
    ):
        """Log data access event"""
        
        details = {
            "record_count": record_count,
            "query": query
        }
        
        self.log_event(
            event_type=EventType.DATA_ACCESS,
            severity=EventSeverity.INFO,
            user_id=user_id,
            action=action,
            resource=resource,
            details=details
        )
    
    def log_security_event(
        self,
        event_name: str,
        severity: EventSeverity,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ):
        """Log security-related event"""
        
        self.log_event(
            event_type=EventType.SECURITY_EVENT,
            severity=severity,
            user_id=user_id,
            action=event_name,
            details=details,
            ip_address=ip_address
        )
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        import uuid
        return str(uuid.uuid4())
    
    def _encrypt_sensitive_fields(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive fields in event data"""
        
        sensitive_fields = ["details", "ip_address"]
        
        encrypted_event = event.copy()
        
        for field in sensitive_fields:
            if field in encrypted_event and encrypted_event[field]:
                value_str = json.dumps(encrypted_event[field]) if isinstance(encrypted_event[field], dict) else str(encrypted_event[field])
                encrypted_event[field] = self.encryptor.encrypt(value_str)
        
        return encrypted_event
    
    def _store_event(self, event: Dict[str, Any]):
        """Store event in Redis for quick queries"""
        
        # Store in time-series list
        key = f"audit_events:{datetime.utcnow().strftime('%Y%m%d')}"
        self.redis.lpush(key, json.dumps(event))
        
        # Set expiry based on retention policy
        retention_seconds = settings.audit_log_retention_days * 86400
        self.redis.expire(key, retention_seconds)
        
        # Store user-specific events
        if event.get("user_id"):
            user_key = f"user_events:{event['user_id']}"
            self.redis.lpush(user_key, json.dumps(event))
            self.redis.ltrim(user_key, 0, 999)  # Keep last 1000 events
            self.redis.expire(user_key, retention_seconds)
    
    def get_user_events(
        self,
        user_id: str,
        limit: int = 100
    ) -> list[Dict[str, Any]]:
        """Retrieve audit events for a user"""
        
        key = f"user_events:{user_id}"
        events = self.redis.lrange(key, 0, limit - 1)
        
        return [json.loads(event) for event in events]
    
    def get_recent_events(
        self,
        date: Optional[str] = None,
        limit: int = 100
    ) -> list[Dict[str, Any]]:
        """Retrieve recent audit events"""
        
        if not date:
            date = datetime.utcnow().strftime('%Y%m%d')
        
        key = f"audit_events:{date}"
        events = self.redis.lrange(key, 0, limit - 1)
        
        return [json.loads(event) for event in events]