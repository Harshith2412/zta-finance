import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import secrets
from typing import Tuple

from config.settings import settings
from config.logging import get_logger

logger = get_logger(__name__)


class DataEncryptor:
    """End-to-end encryption for sensitive data"""
    
    def __init__(self):
        # Decode base64 encryption key from settings
        self.key = base64.b64decode(settings.encryption_key)
        self.aesgcm = AESGCM(self.key)
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt data using AES-256-GCM
        
        Returns:
            Base64-encoded encrypted data with nonce
        """
        
        if not plaintext:
            return ""
        
        # Generate random nonce (96 bits for GCM)
        nonce = secrets.token_bytes(12)
        
        # Convert plaintext to bytes
        plaintext_bytes = plaintext.encode('utf-8')
        
        # Encrypt
        ciphertext = self.aesgcm.encrypt(nonce, plaintext_bytes, None)
        
        # Combine nonce + ciphertext and encode as base64
        encrypted_data = base64.b64encode(nonce + ciphertext).decode('utf-8')
        
        return encrypted_data
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt AES-256-GCM encrypted data
        
        Args:
            encrypted_data: Base64-encoded nonce + ciphertext
        
        Returns:
            Decrypted plaintext
        """
        
        if not encrypted_data:
            return ""
        
        try:
            # Decode from base64
            data = base64.b64decode(encrypted_data)
            
            # Extract nonce (first 12 bytes) and ciphertext
            nonce = data[:12]
            ciphertext = data[12:]
            
            # Decrypt
            plaintext_bytes = self.aesgcm.decrypt(nonce, ciphertext, None)
            
            return plaintext_bytes.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise ValueError("Failed to decrypt data")
    
    def encrypt_dict(self, data: dict, fields_to_encrypt: list[str]) -> dict:
        """
        Encrypt specific fields in a dictionary
        
        Args:
            data: Dictionary containing data
            fields_to_encrypt: List of field names to encrypt
        
        Returns:
            Dictionary with encrypted fields
        """
        
        encrypted_data = data.copy()
        
        for field in fields_to_encrypt:
            if field in encrypted_data and encrypted_data[field]:
                encrypted_data[field] = self.encrypt(str(encrypted_data[field]))
        
        return encrypted_data
    
    def decrypt_dict(self, data: dict, fields_to_decrypt: list[str]) -> dict:
        """
        Decrypt specific fields in a dictionary
        
        Args:
            data: Dictionary containing encrypted data
            fields_to_decrypt: List of field names to decrypt
        
        Returns:
            Dictionary with decrypted fields
        """
        
        decrypted_data = data.copy()
        
        for field in fields_to_decrypt:
            if field in decrypted_data and decrypted_data[field]:
                try:
                    decrypted_data[field] = self.decrypt(decrypted_data[field])
                except Exception as e:
                    logger.error(f"Failed to decrypt field {field}: {str(e)}")
                    decrypted_data[field] = None
        
        return decrypted_data
    
    @staticmethod
    def generate_key() -> str:
        """Generate a new encryption key (for key rotation)"""
        key = AESGCM.generate_key(bit_length=256)
        return base64.b64encode(key).decode('utf-8')
    
    @staticmethod
    def hash_password(password: str, salt: bytes = None) -> Tuple[str, str]:
        """
        Hash password using PBKDF2HMAC
        
        Returns:
            (hashed_password, salt) both as base64 strings
        """
        
        if salt is None:
            salt = secrets.token_bytes(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = kdf.derive(password.encode())
        
        return (
            base64.b64encode(key).decode('utf-8'),
            base64.b64encode(salt).decode('utf-8')
        )
    
    @staticmethod
    def verify_password(password: str, hashed_password: str, salt: str) -> bool:
        """Verify password against hash"""
        
        try:
            salt_bytes = base64.b64decode(salt)
            expected_hash = base64.b64decode(hashed_password)
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt_bytes,
                iterations=100000,
            )
            
            kdf.verify(password.encode(), expected_hash)
            return True
            
        except Exception:
            return False