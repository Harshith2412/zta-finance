from typing import Dict, Any, Callable
from functools import wraps
from fastapi import HTTPException, status

from src.policy.pdp import PolicyDecisionPoint
from config.logging import get_logger

logger = get_logger(__name__)


class PolicyEnforcementPoint:
    """
    Policy Enforcement Point (PEP) - Enforces authorization decisions
    Intercepts requests and enforces PDP decisions
    """
    
    def __init__(self, pdp: PolicyDecisionPoint):
        self.pdp = pdp
    
    def enforce(
        self,
        user_id: str,
        resource: str,
        action: str,
        request_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enforce policy decision
        
        Raises HTTPException if access is denied
        Returns decision if access is allowed
        """
        
        decision = self.pdp.make_decision(user_id, resource, action, request_context)
        
        if not decision["allowed"]:
            logger.warning(
                f"Access denied - User: {user_id}, Resource: {resource}, Action: {action}, "
                f"Reason: {decision['reason']}"
            )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Access Denied",
                    "reason": decision["reason"],
                    "policy_id": decision.get("policy_id"),
                    "failed_conditions": decision.get("failed_conditions", []),
                    "risk_level": decision.get("risk_level")
                }
            )
        
        # Check if additional verification is required
        if decision.get("requires_additional_verification"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "Additional Verification Required",
                    "reason": "High risk activity detected",
                    "required_methods": decision.get("additional_verification_methods", []),
                    "risk_score": decision.get("risk_score")
                }
            )
        
        return decision
    
    def require_permission(self, resource: str, action: str):
        """
        Decorator for route handlers to enforce permissions
        
        Usage:
            @app.get("/transactions")
            @pep.require_permission("transaction", "read")
            async def get_transactions(user: User):
                ...
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract user and request context from kwargs
                # This assumes user and request_context are passed to the handler
                user_id = kwargs.get("user_id")
                request_context = kwargs.get("request_context", {})
                
                if not user_id:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required"
                    )
                
                # Enforce policy
                self.enforce(user_id, resource, action, request_context)
                
                # Call original function
                return await func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def check_permission(
        self,
        user_id: str,
        resource: str,
        action: str,
        request_context: Dict[str, Any]
    ) -> bool:
        """
        Check permission without raising exception
        Returns True if allowed, False otherwise
        """
        
        try:
            decision = self.pdp.make_decision(user_id, resource, action, request_context)
            return decision["allowed"] and not decision.get("requires_additional_verification")
        except Exception as e:
            logger.error(f"Error checking permission: {str(e)}")
            return False
    
    def get_user_permissions(
        self,
        user_id: str,
        resources: list[str],
        request_context: Dict[str, Any]
    ) -> Dict[str, Dict[str, bool]]:
        """
        Get all permissions for a user across multiple resources
        Useful for UI to determine what actions to show
        
        Returns:
            {
                "transaction": {"read": True, "write": False, "create": True},
                "account": {"read": True, "write": True}
            }
        """
        
        permissions = {}
        actions = ["read", "write", "create", "delete", "execute"]
        
        for resource in resources:
            permissions[resource] = {}
            for action in actions:
                permissions[resource][action] = self.check_permission(
                    user_id, resource, action, request_context
                )
        
        return permissions