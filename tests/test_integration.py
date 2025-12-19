import pytest
from src.identity.authenticator import Authenticator
from src.policy.policy_engine import PolicyEngine
from src.verification.risk_analyzer import RiskAnalyzer
from unittest.mock import Mock


class TestAuthenticator:
    """Test authentication functionality"""
    
    def test_password_hashing(self):
        """Test password hashing and verification"""
        redis_mock = Mock()
        authenticator = Authenticator(redis_mock)
        
        password = "SecurePassword123!"
        hashed = authenticator.hash_password(password)
        
        # Password should be hashed
        assert hashed != password
        assert len(hashed) > 0
        
        # Verification should work
        result = authenticator.verify_password(password, hashed)
        assert result["verified"] is True
        
        # Wrong password should fail
        result = authenticator.verify_password("WrongPassword", hashed)
        assert result["verified"] is False
    
    def test_mfa_generation(self):
        """Test MFA secret generation"""
        redis_mock = Mock()
        authenticator = Authenticator(redis_mock)
        
        secret = authenticator.generate_mfa_secret()
        
        assert len(secret) == 32
        assert secret.isalnum()


class TestPolicyEngine:
    """Test policy evaluation"""
    
    def test_policy_evaluation_allowed(self):
        """Test policy that should allow access"""
        engine = PolicyEngine()
        
        context = {
            "user_verified": True,
            "device_trusted": True,
            "risk_score": 20,
            "mfa_verified": True,
            "roles": ["account_holder"]
        }
        
        decision = engine.evaluate_policy("account", "read", context)
        
        assert decision["allowed"] is True
        assert "policy_id" in decision
    
    def test_policy_evaluation_denied(self):
        """Test policy that should deny access"""
        engine = PolicyEngine()
        
        context = {
            "user_verified": True,
            "device_trusted": False,  # Device not trusted
            "risk_score": 90,  # High risk
            "mfa_verified": False,
            "roles": ["account_holder"]
        }
        
        decision = engine.evaluate_policy("payment", "execute", context)
        
        assert decision["allowed"] is False
        assert "reason" in decision
    
    def test_risk_score_calculation(self):
        """Test risk score calculation"""
        engine = PolicyEngine()
        
        risk_indicators = {
            "unknown_device": True,
            "unknown_location": True,
            "high_transaction_amount": True
        }
        
        score = engine.calculate_risk_score(risk_indicators)
        
        assert 0 <= score <= 100
        assert score > 0  # Should have some risk


class TestRiskAnalyzer:
    """Test risk analysis"""
    
    def test_calculate_request_risk(self):
        """Test request risk calculation"""
        redis_mock = Mock()
        redis_mock.get.return_value = None
        redis_mock.smembers.return_value = set()
        redis_mock.incr.return_value = 1
        
        analyzer = RiskAnalyzer(redis_mock)
        
        context = {
            "device_trusted": False,
            "ip_address": "192.168.1.1",
            "user_id": "user_123",
            "transaction_amount": 15000
        }
        
        risk_score = analyzer.calculate_request_risk(context)
        
        assert 0 <= risk_score <= 100
        assert risk_score > 0  # Should detect some risk


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    return Mock()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])