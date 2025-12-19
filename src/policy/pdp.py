from typing import Dict, Any
from datetime import datetime

from src.policy.policy_engine import PolicyEngine
from src.verification.risk_analyzer import RiskAnalyzer
from config.logging import get_logger

logger = get_logger(__name__)


class PolicyDecisionPoint:
    """
    Policy Decision Point (PDP) - Makes authorization decisions
    Central component that evaluates policies and returns allow/deny decisions
    """
    
    def __init__(self, policy_engine: PolicyEngine, risk_analyzer: RiskAnalyzer):
        self.policy_engine = policy_engine
        self.risk_analyzer = risk_analyzer
    
    def make_decision(
        self,
        user_id: str,
        resource: str,
        action: str,
        request_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Make authorization decision
        
        Args:
            user_id: User making the request
            resource: Resource being accessed
            action: Action being performed
            request_context: Complete request context including device, location, etc.
        
        Returns:
            Decision with allowed status, reason, and additional context
        """
        
        # Enrich context with risk score
        risk_score = self.risk_analyzer.calculate_request_risk(request_context)
        enriched_context = {
            **request_context,
            "risk_score": risk_score,
            "decision_timestamp": datetime.utcnow().isoformat()
        }
        
        # Evaluate policy
        decision = self.policy_engine.evaluate_policy(resource, action, enriched_context)
        
        # Add risk information to decision
        decision["risk_score"] = risk_score
        decision["risk_level"] = self._get_risk_level(risk_score)
        decision["user_id"] = user_id
        decision["resource"] = resource
        decision["action"] = action
        
        # Log decision
        self._log_decision(decision, enriched_context)
        
        # Additional checks for high-risk scenarios
        if risk_score > 80 and decision["allowed"]:
            decision["requires_additional_verification"] = True
            decision["additional_verification_methods"] = ["mfa", "security_question"]
        
        return decision
    
    def _get_risk_level(self, risk_score: int) -> str:
        """Convert risk score to risk level"""
        if risk_score < 30:
            return "low"
        elif risk_score < 60:
            return "medium"
        elif risk_score < 80:
            return "high"
        else:
            return "critical"
    
    def _log_decision(self, decision: Dict[str, Any], context: Dict[str, Any]):
        """Log authorization decision for audit"""
        
        log_data = {
            "event": "authorization_decision",
            "user_id": decision.get("user_id"),
            "resource": decision.get("resource"),
            "action": decision.get("action"),
            "allowed": decision.get("allowed"),
            "reason": decision.get("reason"),
            "risk_score": decision.get("risk_score"),
            "risk_level": decision.get("risk_level"),
            "policy_id": decision.get("policy_id"),
            "timestamp": datetime.utcnow().isoformat(),
            "ip_address": context.get("ip_address"),
            "device_id": context.get("device_id")
        }
        
        if decision["allowed"]:
            logger.info("Authorization granted", extra=log_data)
        else:
            logger.warning("Authorization denied", extra=log_data)
    
    def batch_evaluate(
        self,
        user_id: str,
        requests: list[Dict[str, Any]]
    ) -> list[Dict[str, Any]]:
        """
        Evaluate multiple authorization requests in batch
        Useful for checking multiple permissions at once
        """
        
        decisions = []
        
        for request in requests:
            decision = self.make_decision(
                user_id=user_id,
                resource=request["resource"],
                action=request["action"],
                request_context=request.get("context", {})
            )
            decisions.append(decision)
        
        return decisions