import json
from typing import Dict, Any, List, Optional
from pathlib import Path

from config.logging import get_logger

logger = get_logger(__name__)


class PolicyEngine:
    """Attribute-Based Access Control (ABAC) Policy Engine"""
    
    def __init__(self, policies_path: str = "config/policies.json"):
        self.policies = self._load_policies(policies_path)
        self.risk_factors = self.policies.get("risk_factors", {})
        self.device_trust_requirements = self.policies.get("device_trust_requirements", {})
    
    def _load_policies(self, policies_path: str) -> Dict[str, Any]:
        """Load policies from JSON file"""
        try:
            with open(policies_path, 'r') as f:
                policies = json.load(f)
            logger.info(f"Loaded {len(policies.get('policies', []))} policies")
            return policies
        except Exception as e:
            logger.error(f"Error loading policies: {str(e)}")
            return {"policies": [], "risk_factors": {}, "device_trust_requirements": {}}
    
    def evaluate_policy(
        self,
        resource: str,
        action: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate if action on resource is allowed given context
        
        Args:
            resource: Resource being accessed (e.g., 'account', 'transaction')
            action: Action being performed (e.g., 'read', 'write', 'create')
            context: Request context with attributes like user_verified, mfa_verified, etc.
        
        Returns:
            Decision with allowed status and reason
        """
        
        # Find matching policies
        matching_policies = self._find_matching_policies(resource, action)
        
        if not matching_policies:
            logger.warning(f"No policy found for resource: {resource}, action: {action}")
            return {
                "allowed": False,
                "reason": "No matching policy found",
                "policy_id": None
            }
        
        # Evaluate conditions for each matching policy
        for policy in matching_policies:
            decision = self._evaluate_conditions(policy, context)
            
            if decision["allowed"]:
                logger.info(f"Access granted - Policy: {policy['id']}, Resource: {resource}, Action: {action}")
                return decision
        
        # If no policy allowed access
        logger.warning(f"Access denied - Resource: {resource}, Action: {action}")
        return {
            "allowed": False,
            "reason": "Policy conditions not met",
            "policy_id": matching_policies[0]["id"],
            "failed_conditions": self._get_failed_conditions(matching_policies[0], context)
        }
    
    def _find_matching_policies(self, resource: str, action: str) -> List[Dict[str, Any]]:
        """Find policies matching resource and action"""
        
        matching = []
        
        for policy in self.policies.get("policies", []):
            # Check for exact match or wildcard
            resource_match = (policy["resource"] == resource or policy["resource"] == "*")
            action_match = (policy["action"] == action or policy["action"] == "*")
            
            if resource_match and action_match:
                matching.append(policy)
        
        return matching
    
    def _evaluate_conditions(
        self,
        policy: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate policy conditions against context"""
        
        conditions = policy.get("conditions", {})
        
        # Check each condition
        for condition_key, condition_value in conditions.items():
            
            # Boolean conditions
            if isinstance(condition_value, bool):
                if context.get(condition_key) != condition_value:
                    return {
                        "allowed": False,
                        "reason": f"Condition not met: {condition_key}",
                        "policy_id": policy["id"]
                    }
            
            # Numeric conditions (e.g., risk_score)
            elif isinstance(condition_value, dict):
                context_value = context.get(condition_key)
                
                if "max" in condition_value:
                    if context_value is None or context_value > condition_value["max"]:
                        return {
                            "allowed": False,
                            "reason": f"{condition_key} exceeds maximum: {condition_value['max']}",
                            "policy_id": policy["id"]
                        }
                
                if "min" in condition_value:
                    if context_value is None or context_value < condition_value["min"]:
                        return {
                            "allowed": False,
                            "reason": f"{condition_key} below minimum: {condition_value['min']}",
                            "policy_id": policy["id"]
                        }
            
            # List conditions (e.g., roles)
            elif isinstance(condition_value, list):
                context_value = context.get(condition_key, [])
                
                # Check if any required value is present
                if not any(val in context_value for val in condition_value):
                    return {
                        "allowed": False,
                        "reason": f"Required {condition_key} not present",
                        "policy_id": policy["id"]
                    }
        
        # All conditions met
        return {
            "allowed": True,
            "reason": "All policy conditions satisfied",
            "policy_id": policy["id"]
        }
    
    def _get_failed_conditions(
        self,
        policy: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[str]:
        """Get list of failed conditions"""
        
        failed = []
        conditions = policy.get("conditions", {})
        
        for condition_key, condition_value in conditions.items():
            if isinstance(condition_value, bool):
                if context.get(condition_key) != condition_value:
                    failed.append(condition_key)
            elif isinstance(condition_value, dict):
                context_value = context.get(condition_key)
                if "max" in condition_value and (context_value is None or context_value > condition_value["max"]):
                    failed.append(f"{condition_key} (exceeds max)")
                if "min" in condition_value and (context_value is None or context_value < condition_value["min"]):
                    failed.append(f"{condition_key} (below min)")
            elif isinstance(condition_value, list):
                context_value = context.get(condition_key, [])
                if not any(val in context_value for val in condition_value):
                    failed.append(condition_key)
        
        return failed
    
    def calculate_risk_score(self, risk_indicators: Dict[str, bool]) -> int:
        """Calculate risk score based on indicators"""
        
        score = 0
        
        for indicator, is_present in risk_indicators.items():
            if is_present and indicator in self.risk_factors:
                score += self.risk_factors[indicator]
        
        # Cap at 100
        return min(score, 100)