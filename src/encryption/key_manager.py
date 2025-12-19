"""
Key Manager
Manages encryption keys and key rotation
"""

import base64
import secrets
from typing import Dict, Optional
from datetime import datetime, timedelta
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from config.logging import get_logger

logger = get_logger(__name__)


class KeyManager:
    """Manages encryption keys with rotation support"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.key_prefix = "encryption_key"
    
    def generate_key(self) -> str:
        """Generate a new AES-256 encryption key"""
        key = AESGCM.generate_key(bit_length=256)
        key_b64 = base64.b64encode(key).decode('utf-8')
        
        logger.info("New encryption key generated")
        return key_b64
    
    def store_key(
        self,
        key_id: str,
        key: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Store encryption key securely"""
        
        key_data = {
            "key_id": key_id,
            "key": key,
            "created_at": datetime.utcnow().isoformat(),
            "status": "active",
            "metadata": metadata or {}
        }
        
        # In production, store in a proper key management service (KMS)
        # For demo, using Redis (NOT recommended for production)
        key_name = f"{self.key_prefix}:{key_id}"
        
        import json
        self.redis.set(key_name, json.dumps(key_data))
        
        logger.info(f"Encryption key stored: {key_id}")
        return True
    
    def get_key(self, key_id: str) -> Optional[str]:
        """Retrieve encryption key"""
        
        key_name = f"{self.key_prefix}:{key_id}"
        key_data = self.redis.get(key_name)
        
        if not key_data:
            logger.warning(f"Encryption key not found: {key_id}")
            return None
        
        import json
        data = json.loads(key_data)
        
        if data["status"] != "active":
            logger.warning(f"Encryption key not active: {key_id}")
            return None
        
        return data["key"]
    
    def get_active_key(self) -> Optional[Dict]:
        """Get the current active encryption key"""
        
        # In production, maintain a pointer to current active key
        active_key_name = f"{self.key_prefix}:active"
        key_id = self.redis.get(active_key_name)
        
        if not key_id:
            return None
        
        if isinstance(key_id, bytes):
            key_id = key_id.decode()
        
        key = self.get_key(key_id)
        
        if key:
            return {
                "key_id": key_id,
                "key": key
            }
        
        return None
    
    def set_active_key(self, key_id: str) -> bool:
        """Set a key as the active encryption key"""
        
        # Verify key exists
        if not self.get_key(key_id):
            return False
        
        active_key_name = f"{self.key_prefix}:active"
        self.redis.set(active_key_name, key_id)
        
        logger.info(f"Active encryption key set to: {key_id}")
        return True
    
    def rotate_key(self) -> Dict:
        """Rotate encryption key"""
        
        # Generate new key
        new_key = self.generate_key()
        new_key_id = f"key_{int(datetime.utcnow().timestamp())}"
        
        # Store new key
        self.store_key(
            key_id=new_key_id,
            key=new_key,
            metadata={"rotation_date": datetime.utcnow().isoformat()}
        )
        
        # Get old key
        old_key_info = self.get_active_key()
        
        # Set new key as active
        self.set_active_key(new_key_id)
        
        # Mark old key as rotated (but keep for decryption)
        if old_key_info:
            self._update_key_status(old_key_info["key_id"], "rotated")
        
        logger.info(f"Key rotation completed - New key: {new_key_id}")
        
        return {
            "old_key_id": old_key_info["key_id"] if old_key_info else None,
            "new_key_id": new_key_id,
            "rotated_at": datetime.utcnow().isoformat()
        }
    
    def _update_key_status(self, key_id: str, status: str):
        """Update key status"""
        
        key_name = f"{self.key_prefix}:{key_id}"
        key_data = self.redis.get(key_name)
        
        if key_data:
            import json
            data = json.loads(key_data)
            data["status"] = status
            data["updated_at"] = datetime.utcnow().isoformat()
            self.redis.set(key_name, json.dumps(data))
    
    def revoke_key(self, key_id: str) -> bool:
        """Revoke an encryption key"""
        
        self._update_key_status(key_id, "revoked")
        
        logger.warning(f"Encryption key revoked: {key_id}")
        return True
    
    def list_keys(self) -> list:
        """List all encryption keys"""
        
        pattern = f"{self.key_prefix}:*"
        keys = []
        
        for key_name in self.redis.scan_iter(match=pattern):
            if b":active" in key_name or ":active" in str(key_name):
                continue
            
            key_data = self.redis.get(key_name)
            if key_data:
                import json
                data = json.loads(key_data)
                keys.append({
                    "key_id": data["key_id"],
                    "created_at": data["created_at"],
                    "status": data["status"]
                })
        
        return keys
    
    def schedule_rotation(self, days: int = 90):
        """Schedule automatic key rotation"""
        
        # In production, use a job scheduler
        rotation_date = datetime.utcnow() + timedelta(days=days)
        
        logger.info(f"Key rotation scheduled for: {rotation_date.isoformat()}")
        
        return {
            "scheduled_date": rotation_date.isoformat(),
            "days_until_rotation": days
        }
    
    def get_key_info(self, key_id: str) -> Optional[Dict]:
        """Get key metadata without the actual key"""
        
        key_name = f"{self.key_prefix}:{key_id}"
        key_data = self.redis.get(key_name)
        
        if not key_data:
            return None
        
        import json
        data = json.loads(key_data)
        
        # Return info without actual key
        return {
            "key_id": data["key_id"],
            "created_at": data["created_at"],
            "status": data["status"],
            "metadata": data.get("metadata", {})
        }