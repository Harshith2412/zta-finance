"""
Tests for Policy Engine and Authorization
"""

import pytest
from src.policy.policy_engine import PolicyEngine
from src.policy.pdp import PolicyDecisionPoint
from src.policy.pep import PolicyEnforcementPoint
from src.verification.risk_analyzer import RiskAnalyzer
from unittest.mock import Mock, patch
from fastapi import HTTPException


class TestPolicyEngine:
    """Test PolicyEngine class"""
    
    @pytest.fixture
    def policy_engine(self):
        return PolicyEngine()
    
    def test_load_policies(self, policy_engine):
        """Test policy loading"""
        assert len(policy_engine.policies.get("policies", [])) > 0
        assert "risk_factors" in policy_engine.policies
    
    def test_evaluate_policy_allowed(self, policy_engine):
        """Test policy evaluation - access allowed"""
        context = {
            "user_verified": True,
            "device_trusted": True,
            "risk_score": 20,
            "mfa_verified": False,
            "roles": ["account_holder"]
        }
        
        decision = policy_engine.evaluate_policy("account", "read", context)
        
        assert decision["allowed"] is True
        assert "policy_id" in decision
    
    def test_evaluate_policy_denied_high_risk(self, policy_engine):
        """Test policy evaluation - denied due to high risk"""
        context = {
            "user_verified": True,
            "device_trusted": True,
            "risk_score": 95,  # Very high risk
            "mfa_verified": True,
            "roles": ["account_holder"]
        }
        
        decision = policy_engine.evaluate_policy("account", "read", context)
        
        assert decision["allowed"] is False
        assert "risk_score" in decision.get("reason", "")
    
    def test_evaluate_policy_denied_untrusted_device(self, policy_engine):
        """Test policy evaluation - denied due to untrusted device"""
        context = {
            "user_verified": True,
            "device_trusted": False,  # Device not trusted
            "risk_score": 30,
            "mfa_verified": True,
            "roles": ["account_holder"]
        }
        
        decision = policy_engine.evaluate_policy("transaction", "create", context)
        
        assert decision["allowed"] is False
    
    def test_evaluate_policy_no_mfa(self, policy_engine):
        """Test policy evaluation - requires MFA"""
        context = {
            "user_verified": True,
            "device_trusted": True,
            "risk_score": 25,
            "mfa_verified": False,  # No MFA
            "roles": ["account_holder"]
        }
        
        decision = policy_engine.evaluate_policy("payment", "execute", context)
        
        assert decision["allowed"] is False
    
    def test_evaluate_policy_admin_access(self, policy_engine):
        """Test admin policy evaluation"""
        context = {
            "user_verified": True,
            "device_trusted": True,
            "risk_score": 5,
            "mfa_verified": True,
            "roles": ["admin"],
            "ip_whitelisted": True
        }
        
        decision = policy_engine.evaluate_policy("*", "*", context)
        
        assert decision["allowed"] is True
    
    def test_calculate_risk_score(self, policy_engine):
        """Test risk score calculation"""
        risk_indicators = {
            "unknown_device": True,
            "unknown_location": True,
            "high_transaction_amount": True
        }
        
        score = policy_engine.calculate_risk_score(risk_indicators)
        
        assert 0 <= score <= 100
        assert score > 50  # Should be high with these indicators
    
    def test_calculate_risk_score_no_risks(self, policy_engine):
        """Test risk score with no risk factors"""
        risk_indicators = {
            "unknown_device": False,
            "unknown_location": False,
            "high_transaction_amount": False
        }
        
        score = policy_engine.calculate_risk_score(risk_indicators)
        
        assert score == 0


class TestPolicyDecisionPoint:
    """Test PolicyDecisionPoint class"""
    
    @pytest.fixture
    def policy_engine(self):
        return PolicyEngine()
    
    @pytest.fixture
    def risk_analyzer(self):
        mock = Mock()
        mock.calculate_request_risk = Mock(return_value=30)
        return mock
    
    @pytest.fixture
    def pdp(self, policy_engine, risk_analyzer):
        return PolicyDecisionPoint(policy_engine, risk_analyzer)
    
    def test_make_decision_allowed(self, pdp):
        """Test making authorization decision - allowed"""
        context = {
            "user_verified": True,
            "device_trusted": True,
            "mfa_verified": False,
            "roles": ["account_holder"]
        }
        
        decision = pdp.make_decision(
            user_id="user_123",
            resource="account",
            action="read",
            request_context=context
        )
        
        assert decision["allowed"] is True
        assert "risk_score" in decision
        assert "risk_level" in decision
    
    def test_make_decision_denied(self, pdp):
        """Test making authorization decision - denied"""
        context = {
            "user_verified": True,
            "device_trusted": False,
            "mfa_verified": False,
            "roles": ["account_holder"]
        }
        
        decision = pdp.make_decision(
            user_id="user_123",
            resource="payment",
            action="execute",
            request_context=context
        )
        
        assert decision["allowed"] is False
    
    def test_risk_level_mapping(self, pdp, risk_analyzer):
        """Test risk level categorization"""
        risk_analyzer.calculate_request_risk.return_value = 85
        
        context = {
            "user_verified": True,
            "device_trusted": True,
            "mfa_verified": True,
            "roles": ["account_holder"]
        }
        
        decision = pdp.make_decision(
            user_id="user_123",
            resource="account",
            action="read",
            request_context=context
        )
        
        assert decision["risk_level"] == "critical"


class TestPolicyEnforcementPoint:
    """Test PolicyEnforcementPoint class"""
    
    @pytest.fixture
    def pdp_mock(self):
        return Mock()
    
    @pytest.fixture
    def pep(self, pdp_mock):
        return PolicyEnforcementPoint(pdp_mock)
    
    def test_enforce_allowed(self, pep, pdp_mock):
        """Test enforcement when access is allowed"""
        pdp_mock.make_decision.return_value = {
            "allowed": True,
            "reason": "All conditions met",
            "risk_score": 20,
            "risk_level": "low"
        }
        
        decision = pep.enforce(
            user_id="user_123",
            resource="account",
            action="read",
            request_context={}
        )
        
        assert decision["allowed"] is True
    
    def test_enforce_denied(self, pep, pdp_mock):
        """Test enforcement when access is denied"""
        pdp_mock.make_decision.return_value = {
            "allowed": False,
            "reason": "High risk score",
            "risk_score": 90,
            "risk_level": "critical",
            "policy_id": "account_read",
            "failed_conditions": ["risk_score"]
        }
        
        with pytest.raises(HTTPException) as exc_info:
            pep.enforce(
                user_id="user_123",
                resource="account",
                action="read",
                request_context={}
            )
        
        assert exc_info.value.status_code == 403
    
    def test_enforce_additional_verification_required(self, pep, pdp_mock):
        """Test when additional verification is required"""
        pdp_mock.make_decision.return_value = {
            "allowed": True,
            "requires_additional_verification": True,
            "additional_verification_methods": ["mfa"],
            "risk_score": 85
        }
        
        with pytest.raises(HTTPException) as exc_info:
            pep.enforce(
                user_id="user_123",
                resource="payment",
                action="execute",
                request_context={}
            )
        
        assert exc_info.value.status_code == 401
    
    def test_check_permission_allowed(self, pep, pdp_mock):
        """Test permission check without exception - allowed"""
        pdp_mock.make_decision.return_value = {
            "allowed": True,
            "risk_score": 20
        }
        
        result = pep.check_permission(
            user_id="user_123",
            resource="account",
            action="read",
            request_context={}
        )
        
        assert result is True
    
    def test_check_permission_denied(self, pep, pdp_mock):
        """Test permission check without exception - denied"""
        pdp_mock.make_decision.return_value = {
            "allowed": False,
            "risk_score": 90
        }
        
        result = pep.check_permission(
            user_id="user_123",
            resource="payment",
            action="execute",
            request_context={}
        )
        
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])