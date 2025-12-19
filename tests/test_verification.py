"""
Tests for Verification modules
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta
from src.verification.device_verifier import DeviceVerifier
from src.verification.risk_analyzer import RiskAnalyzer
from src.verification.session_manager import SessionManager


class TestDeviceVerifier:
    """Test DeviceVerifier class"""
    
    @pytest.fixture
    def redis_mock(self):
        mock = Mock()
        mock.setex = Mock()
        mock.get = Mock()
        mock.smembers = Mock(return_value=set())
        mock.scan_iter = Mock(return_value=[])
        return mock
    
    @pytest.fixture
    def device_verifier(self, redis_mock):
        return DeviceVerifier(redis_mock)
    
    def test_generate_device_fingerprint(self, device_verifier):
        """Test device fingerprint generation"""
        device_info = {
            "user_agent": "Mozilla/5.0",
            "screen_resolution": "1920x1080",
            "timezone": "UTC",
            "language": "en-US",
            "platform": "Linux"
        }
        
        fingerprint = device_verifier.generate_device_fingerprint(device_info)
        
        assert isinstance(fingerprint, str)
        assert len(fingerprint) == 64  # SHA-256 produces 64 hex chars
    
    def test_fingerprint_consistency(self, device_verifier):
        """Test that same device info produces same fingerprint"""
        device_info = {
            "user_agent": "Mozilla/5.0",
            "screen_resolution": "1920x1080"
        }
        
        fp1 = device_verifier.generate_device_fingerprint(device_info)
        fp2 = device_verifier.generate_device_fingerprint(device_info)
        
        assert fp1 == fp2
    
    def test_register_device(self, device_verifier, redis_mock):
        """Test device registration"""
        device_info = {"user_agent": "Mozilla/5.0"}
        
        result = device_verifier.register_device(
            user_id="user_123",
            device_id="device_456",
            device_info=device_info
        )
        
        assert result is True
        redis_mock.setex.assert_called_once()
    
    def test_verify_known_device(self, device_verifier, redis_mock):
        """Test verifying a known device"""
        device_data = {
            "device_id": "device_456",
            "user_id": "user_123",
            "trusted": False,
            "trust_score": 60,
            "registered_at": datetime.utcnow().isoformat(),
            "access_count": 10
        }
        
        import json
        redis_mock.get.return_value = json.dumps(device_data)
        
        result = device_verifier.verify_device("user_123", "device_456")
        
        assert result["known"] is True
        assert "trust_score" in result
    
    def test_verify_unknown_device(self, device_verifier, redis_mock):
        """Test verifying an unknown device"""
        redis_mock.get.return_value = None
        
        result = device_verifier.verify_device("user_123", "unknown_device")
        
        assert result["known"] is False
        assert result["trusted"] is False
    
    def test_trust_score_calculation(self, device_verifier, redis_mock):
        """Test trust score calculation"""
        old_registration = (datetime.utcnow() - timedelta(days=35)).isoformat()
        
        device_data = {
            "device_id": "device_456",
            "registered_at": old_registration,
            "access_count": 120,
            "trusted": False
        }
        
        score = device_verifier._calculate_trust_score(device_data)
        
        assert score > 70  # Should be high due to age and usage
    
    def test_revoke_device_trust(self, device_verifier, redis_mock):
        """Test revoking device trust"""
        device_data = {
            "device_id": "device_456",
            "trusted": True,
            "trust_score": 85
        }
        
        import json
        redis_mock.get.return_value = json.dumps(device_data)
        
        result = device_verifier.revoke_device_trust("user_123", "device_456")
        
        assert result is True
        redis_mock.setex.assert_called()


class TestRiskAnalyzer:
    """Test RiskAnalyzer class"""
    
    @pytest.fixture
    def redis_mock(self):
        mock = Mock()
        mock.get = Mock(return_value=None)
        mock.smembers = Mock(return_value=set())
        mock.incr = Mock(return_value=1)
        mock.sadd = Mock()
        mock.setex = Mock()
        mock.lpush = Mock()
        mock.ltrim = Mock()
        mock.expire = Mock()
        return mock
    
    @pytest.fixture
    def risk_analyzer(self, redis_mock):
        return RiskAnalyzer(redis_mock)
    
    def test_calculate_request_risk_low(self, risk_analyzer):
        """Test low risk calculation"""
        context = {
            "device_trusted": True,
            "ip_address": "192.168.1.1",
            "user_id": "user_123",
            "transaction_amount": 100
        }
        
        score = risk_analyzer.calculate_request_risk(context)
        
        assert 0 <= score <= 100
        assert score < 50  # Should be low risk
    
    def test_calculate_request_risk_high(self, risk_analyzer):
        """Test high risk calculation"""
        context = {
            "device_trusted": False,  # Untrusted device
            "ip_address": "192.168.1.1",
            "user_id": "user_123",
            "transaction_amount": 50000  # High amount
        }
        
        score = risk_analyzer.calculate_request_risk(context)
        
        assert score > 40  # Should have elevated risk
    
    def test_unknown_location_detection(self, risk_analyzer, redis_mock):
        """Test unknown location detection"""
        redis_mock.smembers.return_value = set()
        
        context = {
            "location": {"country": "US", "city": "New York"},
            "user_id": "user_123"
        }
        
        is_unknown = risk_analyzer._is_unknown_location(context)
        
        assert is_unknown is True
    
    def test_known_location_detection(self, risk_analyzer, redis_mock):
        """Test known location detection"""
        redis_mock.smembers.return_value = {b"US:New York"}
        
        context = {
            "location": {"country": "US", "city": "New York"},
            "user_id": "user_123"
        }
        
        is_unknown = risk_analyzer._is_unknown_location(context)
        
        assert is_unknown is False
    
    def test_unusual_time_detection(self, risk_analyzer):
        """Test unusual time detection"""
        # This will vary based on current time
        is_unusual = risk_analyzer._is_unusual_time()
        
        assert isinstance(is_unusual, bool)
    
    def test_rapid_requests_detection(self, risk_analyzer, redis_mock):
        """Test rapid request detection"""
        redis_mock.incr.return_value = 35  # Over threshold
        
        is_rapid = risk_analyzer._detect_rapid_requests("user_123")
        
        assert is_rapid is True
    
    def test_failed_attempts_check(self, risk_analyzer, redis_mock):
        """Test failed attempts checking"""
        redis_mock.get.return_value = b"5"
        
        has_failures = risk_analyzer._has_recent_failed_attempts("user_123")
        
        assert has_failures is True


class TestSessionManager:
    """Test SessionManager class"""
    
    @pytest.fixture
    def redis_mock(self):
        mock = Mock()
        mock.setex = Mock()
        mock.get = Mock()
        mock.delete = Mock()
        mock.sadd = Mock()
        mock.srem = Mock()
        mock.smembers = Mock(return_value=set())
        mock.expire = Mock()
        return mock
    
    @pytest.fixture
    def session_manager(self, redis_mock):
        return SessionManager(redis_mock)
    
    def test_create_session(self, session_manager, redis_mock):
        """Test session creation"""
        session_id = session_manager.create_session(
            user_id="user_123",
            device_id="device_456",
            ip_address="192.168.1.1"
        )
        
        assert isinstance(session_id, str)
        assert len(session_id) > 0
        redis_mock.setex.assert_called()
    
    def test_get_session_exists(self, session_manager, redis_mock):
        """Test getting existing session"""
        session_data = {
            "session_id": "session_789",
            "user_id": "user_123",
            "created_at": datetime.utcnow().isoformat()
        }
        
        import json
        redis_mock.get.return_value = json.dumps(session_data)
        
        session = session_manager.get_session("session_789")
        
        assert session is not None
        assert session["user_id"] == "user_123"
    
    def test_get_session_not_exists(self, session_manager, redis_mock):
        """Test getting non-existent session"""
        redis_mock.get.return_value = None
        
        session = session_manager.get_session("nonexistent")
        
        assert session is None
    
    def test_update_session_activity(self, session_manager, redis_mock):
        """Test updating session activity"""
        session_data = {
            "session_id": "session_789",
            "user_id": "user_123",
            "activity_count": 5,
            "last_activity": datetime.utcnow().isoformat()
        }
        
        import json
        redis_mock.get.return_value = json.dumps(session_data)
        
        result = session_manager.update_session_activity("session_789")
        
        assert result is True
    
    def test_verify_session_valid(self, session_manager, redis_mock):
        """Test verifying valid session"""
        session_data = {
            "session_id": "session_789",
            "user_id": "user_123",
            "device_id": "device_456",
            "ip_address": "192.168.1.1",
            "last_activity": datetime.utcnow().isoformat()
        }
        
        import json
        redis_mock.get.return_value = json.dumps(session_data)
        
        result = session_manager.verify_session(
            session_id="session_789",
            device_id="device_456",
            ip_address="192.168.1.1"
        )
        
        assert result["valid"] is True
        assert len(result["anomalies"]) == 0
    
    def test_verify_session_device_mismatch(self, session_manager, redis_mock):
        """Test session verification with device mismatch"""
        session_data = {
            "session_id": "session_789",
            "device_id": "device_456",
            "ip_address": "192.168.1.1",
            "last_activity": datetime.utcnow().isoformat()
        }
        
        import json
        redis_mock.get.return_value = json.dumps(session_data)
        
        result = session_manager.verify_session(
            session_id="session_789",
            device_id="different_device",
            ip_address="192.168.1.1"
        )
        
        assert result["valid"] is False
        assert "device_mismatch" in result["anomalies"]
    
    def test_invalidate_session(self, session_manager, redis_mock):
        """Test session invalidation"""
        session_data = {
            "session_id": "session_789",
            "user_id": "user_123"
        }
        
        import json
        redis_mock.get.return_value = json.dumps(session_data)
        
        result = session_manager.invalidate_session("session_789")
        
        assert result is True
        redis_mock.delete.assert_called()
    
    def test_is_session_fresh(self, session_manager, redis_mock):
        """Test checking if session is fresh"""
        recent_time = datetime.utcnow().isoformat()
        session_data = {
            "session_id": "session_789",
            "last_activity": recent_time
        }
        
        import json
        redis_mock.get.return_value = json.dumps(session_data)
        
        is_fresh = session_manager.is_session_fresh("session_789", max_age_minutes=5)
        
        assert is_fresh is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])