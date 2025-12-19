import hashlib
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from config.logging import get_logger

logger = get_logger(__name__)


class DeviceVerifier:
    """Device trust verification and fingerprinting"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def generate_device_fingerprint(self, device_info: Dict[str, Any]) -> str:
        """
        Generate unique device fingerprint
        
        Args:
            device_info: Dictionary containing device attributes
                - user_agent: Browser user agent
                - screen_resolution: Screen dimensions
                - timezone: User timezone
                - language: Browser language
                - platform: Operating system
                - plugins: Installed plugins (optional)
        """
        
        # Concatenate device attributes
        fingerprint_data = json.dumps(device_info, sort_keys=True)
        
        # Generate SHA-256 hash
        fingerprint = hashlib.sha256(fingerprint_data.encode()).hexdigest()
        
        return fingerprint
    
    def register_device(
        self,
        user_id: str,
        device_id: str,
        device_info: Dict[str, Any]
    ) -> bool:
        """Register a new trusted device for user"""
        
        key = f"device:{user_id}:{device_id}"
        
        device_data = {
            "device_id": device_id,
            "user_id": user_id,
            "device_info": device_info,
            "trust_score": 50,  # Initial trust score
            "registered_at": datetime.utcnow().isoformat(),
            "last_seen": datetime.utcnow().isoformat(),
            "access_count": 0,
            "trusted": False
        }
        
        # Store device data (30 days expiry for untrusted devices)
        self.redis.setex(key, 2592000, json.dumps(device_data))
        
        logger.info(f"Device registered - User: {user_id}, Device: {device_id}")
        return True
    
    def verify_device(self, user_id: str, device_id: str) -> Dict[str, Any]:
        """
        Verify device and return trust information
        
        Returns:
            {
                "trusted": bool,
                "trust_score": int (0-100),
                "first_seen": datetime,
                "last_seen": datetime,
                "access_count": int
            }
        """
        
        key = f"device:{user_id}:{device_id}"
        device_data = self.redis.get(key)
        
        if not device_data:
            return {
                "trusted": False,
                "trust_score": 0,
                "known": False,
                "reason": "Unknown device"
            }
        
        device = json.loads(device_data)
        
        # Update last seen and access count
        device["last_seen"] = datetime.utcnow().isoformat()
        device["access_count"] += 1
        
        # Calculate trust score based on usage patterns
        trust_score = self._calculate_trust_score(device)
        device["trust_score"] = trust_score
        
        # Mark as trusted if score is high enough
        if trust_score >= 70 and not device["trusted"]:
            device["trusted"] = True
            device["trusted_at"] = datetime.utcnow().isoformat()
            logger.info(f"Device marked as trusted - User: {user_id}, Device: {device_id}")
        
        # Update device data
        self.redis.setex(key, 2592000, json.dumps(device))
        
        return {
            "trusted": device["trusted"],
            "trust_score": trust_score,
            "known": True,
            "first_seen": device["registered_at"],
            "last_seen": device["last_seen"],
            "access_count": device["access_count"]
        }
    
    def _calculate_trust_score(self, device: Dict[str, Any]) -> int:
        """Calculate device trust score"""
        
        score = 50  # Base score
        
        # Age of device registration
        registered_at = datetime.fromisoformat(device["registered_at"])
        age_days = (datetime.utcnow() - registered_at).days
        
        if age_days > 30:
            score += 20
        elif age_days > 7:
            score += 10
        
        # Access frequency
        access_count = device.get("access_count", 0)
        if access_count > 100:
            score += 15
        elif access_count > 50:
            score += 10
        elif access_count > 10:
            score += 5
        
        # Already trusted
        if device.get("trusted"):
            score += 15
        
        return min(score, 100)
    
    def revoke_device_trust(self, user_id: str, device_id: str) -> bool:
        """Revoke trust for a device"""
        
        key = f"device:{user_id}:{device_id}"
        device_data = self.redis.get(key)
        
        if not device_data:
            return False
        
        device = json.loads(device_data)
        device["trusted"] = False
        device["trust_score"] = 0
        device["revoked_at"] = datetime.utcnow().isoformat()
        
        self.redis.setex(key, 2592000, json.dumps(device))
        
        logger.warning(f"Device trust revoked - User: {user_id}, Device: {device_id}")
        return True
    
    def list_user_devices(self, user_id: str) -> list[Dict[str, Any]]:
        """List all devices for a user"""
        
        pattern = f"device:{user_id}:*"
        devices = []
        
        for key in self.redis.scan_iter(match=pattern):
            device_data = self.redis.get(key)
            if device_data:
                device = json.loads(device_data)
                devices.append(device)
        
        return devices
    
    def remove_device(self, user_id: str, device_id: str) -> bool:
        """Remove device from user's trusted devices"""
        
        key = f"device:{user_id}:{device_id}"
        result = self.redis.delete(key)
        
        if result:
            logger.info(f"Device removed - User: {user_id}, Device: {device_id}")
        
        return result > 0