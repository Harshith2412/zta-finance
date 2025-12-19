"""
Tests for Identity & Authentication modules
"""

import pytest
from unittest.mock import Mock, MagicMock
from src.identity.authenticator import Authenticator
from src.identity.token_manager import TokenManager
from src.identity.identity_provider import IdentityProvider


class TestAuthenticator:
    """Test Authenticator class"""
    
    @pytest.fixture
    def redis_mock(self):
        return Mock()
    
    @pytest.fixture
    def authenticator(self, redis_mock):
        return Authenticator(redis_mock)
    
    def test_password_hashing(self, authenticator):
        """Test password hashing"""
        password = "SecurePassword123!"
        hashed = authenticator.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$argon2")
    
    def test_password_verification_success(self, authenticator):
        """Test successful password verification"""
        password = "SecurePassword123!"
        hashed = authenticator.hash_password(password)
        
        result = authenticator.verify_password(password, hashed)
        assert result["verified"] is True
    
    def test_password_verification_failure(self, authenticator):
        """Test failed password verification"""
        password = "SecurePassword123!"
        wrong_password = "WrongPassword456"
        hashed = authenticator.hash_password(password)
        
        result = authenticator.verify_password(wrong_password, hashed)
        assert result["verified"] is False
    
    def test_mfa_secret_generation(self, authenticator):
        """Test MFA secret generation"""
        secret = authenticator.generate_mfa_secret()
        
        assert len(secret) == 32
        assert secret.isalnum()
        assert secret.isupper()
    
    def test_mfa_uri_generation(self, authenticator):
        """Test MFA provisioning URI generation"""
        secret = authenticator.generate_mfa_secret()
        username = "testuser@example.com"
        uri = authenticator.get_mfa_uri(secret, username)
        
        assert uri.startswith("otpauth://totp/")
        assert username in uri
        assert secret in uri
    
    def test_track_failed_attempt(self, authenticator, redis_mock):
        """Test failed attempt tracking"""
        redis_mock.incr.return_value = 3
        
        result = authenticator.track_failed_attempt("testuser")
        
        assert result["attempts"] == 3
        assert result["locked"] is False
        redis_mock.incr.assert_called_once()
    
    def test_account_lockout(self, authenticator, redis_mock):
        """Test account lockout after max attempts"""
        redis_mock.incr.return_value = 5
        
        result = authenticator.track_failed_attempt("testuser")
        
        assert result["locked"] is True
        assert result["lockout_duration"] == 1800
    
    def test_clear_failed_attempts(self, authenticator, redis_mock):
        """Test clearing failed attempts"""
        authenticator.clear_failed_attempts("testuser")
        
        redis_mock.delete.assert_called_once()
    
    def test_is_account_locked(self, authenticator, redis_mock):
        """Test checking if account is locked"""
        redis_mock.get.return_value = b"5"
        
        is_locked = authenticator.is_account_locked("testuser")
        
        assert is_locked is True


class TestTokenManager:
    """Test TokenManager class"""
    
    @pytest.fixture
    def redis_mock(self):
        mock = Mock()
        mock.setex = Mock()
        mock.get = Mock()
        mock.exists = Mock(return_value=0)
        return mock
    
    @pytest.fixture
    def token_manager(self, redis_mock):
        return TokenManager(redis_mock)
    
    def test_create_access_token(self, token_manager):
        """Test access token creation"""
        token = token_manager.create_access_token(
            subject="testuser",
            user_id="user_123",
            roles=["account_holder"],
            device_id="device_456"
        )
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_valid_token(self, token_manager, redis_mock):
        """Test verifying valid token"""
        token = token_manager.create_access_token(
            subject="testuser",
            user_id="user_123",
            roles=["account_holder"],
            device_id="device_456"
        )
        
        payload = token_manager.verify_token(token, "access")
        
        assert payload is not None
        assert payload["user_id"] == "user_123"
        assert payload["type"] == "access"
    
    def test_verify_invalid_token(self, token_manager):
        """Test verifying invalid token"""
        payload = token_manager.verify_token("invalid_token", "access")
        
        assert payload is None
    
    def test_create_refresh_token(self, token_manager, redis_mock):
        """Test refresh token creation"""
        token = token_manager.create_refresh_token("user_123", "device_456")
        
        assert isinstance(token, str)
        redis_mock.setex.assert_called()
    
    def test_blacklist_token(self, token_manager, redis_mock):
        """Test token blacklisting"""
        token = token_manager.create_access_token(
            subject="testuser",
            user_id="user_123",
            roles=["account_holder"],
            device_id="device_456"
        )
        
        token_manager.blacklist_token(token)
        redis_mock.setex.assert_called()
    
    def test_is_token_blacklisted(self, token_manager, redis_mock):
        """Test checking if token is blacklisted"""
        redis_mock.exists.return_value = 1
        
        is_blacklisted = token_manager.is_token_blacklisted("some_token")
        
        assert is_blacklisted is True


class TestIdentityProvider:
    """Test IdentityProvider class"""
    
    @pytest.fixture
    def db_mock(self):
        return Mock()
    
    @pytest.fixture
    def identity_provider(self, db_mock):
        return IdentityProvider(db_mock)
    
    def test_create_user(self, identity_provider):
        """Test user creation"""
        user = identity_provider.create_user(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            roles=["account_holder"]
        )
        
        assert user["username"] == "testuser"
        assert user["email"] == "test@example.com"
        assert "user_id" in user
        assert user["active"] is True
        assert user["verified"] is False
    
    def test_verify_user(self, identity_provider):
        """Test user verification"""
        result = identity_provider.verify_user("user_123")
        
        assert result is True
    
    def test_enable_mfa(self, identity_provider):
        """Test enabling MFA"""
        result = identity_provider.enable_mfa("user_123", "mfa_secret_key")
        
        assert result is True
    
    def test_disable_mfa(self, identity_provider):
        """Test disabling MFA"""
        result = identity_provider.disable_mfa("user_123")
        
        assert result is True
    
    def test_deactivate_user(self, identity_provider):
        """Test user deactivation"""
        result = identity_provider.deactivate_user("user_123", "Account suspended")
        
        assert result is True
    
    def test_add_role(self, identity_provider):
        """Test adding role to user"""
        identity_provider.get_user = Mock(return_value={
            "user_id": "user_123",
            "roles": ["account_holder"]
        })
        
        result = identity_provider.add_role("user_123", "admin")
        
        assert result is True
    
    def test_remove_role(self, identity_provider):
        """Test removing role from user"""
        identity_provider.get_user = Mock(return_value={
            "user_id": "user_123",
            "roles": ["account_holder", "admin"]
        })
        
        result = identity_provider.remove_role("user_123", "admin")
        
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])