#!/usr/bin/env python3
"""
Generate encryption keys and JWT secrets for ZTA-Finance
"""

import secrets
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def generate_jwt_secret(length: int = 64) -> str:
    """Generate a secure JWT secret key"""
    return secrets.token_urlsafe(length)


def generate_encryption_key() -> str:
    """Generate AES-256 encryption key"""
    key = AESGCM.generate_key(bit_length=256)
    return base64.b64encode(key).decode('utf-8')


def generate_redis_password(length: int = 32) -> str:
    """Generate Redis password"""
    return secrets.token_urlsafe(length)


def generate_db_password(length: int = 32) -> str:
    """Generate database password"""
    return secrets.token_urlsafe(length)


def main():
    print("=" * 70)
    print("ZTA-Finance Security Key Generation")
    print("=" * 70)
    print()
    
    print("Copy these values to your .env file:")
    print()
    
    # JWT Secret
    jwt_secret = generate_jwt_secret()
    print(f"JWT_SECRET_KEY={jwt_secret}")
    print()
    
    # Encryption Key
    encryption_key = generate_encryption_key()
    print(f"ENCRYPTION_KEY={encryption_key}")
    print()
    
    # Redis Password
    redis_password = generate_redis_password()
    print(f"REDIS_PASSWORD={redis_password}")
    print()
    
    # Database Passwords
    db_password = generate_db_password()
    db_root_password = generate_db_password()
    print(f"DB_PASSWORD={db_password}")
    print(f"DB_ROOT_PASSWORD={db_root_password}")
    print()
    
    print("=" * 70)
    print("IMPORTANT: Store these values securely and never commit to Git!")
    print("=" * 70)
    print()
    
    # Save to a file
    with open('.env', 'w') as f:
        f.write("# ZTA-Finance Environment Variables\n")
        f.write("# Generated: " + str(__import__('datetime').datetime.now()) + "\n\n")
        
        f.write("# Application\n")
        f.write("APP_NAME=ZTA-Finance\n")
        f.write("APP_ENV=development\n")
        f.write("DEBUG=True\n")
        f.write("LOG_LEVEL=INFO\n\n")
        
        f.write("# API Configuration\n")
        f.write("API_HOST=0.0.0.0\n")
        f.write("API_PORT=8000\n")
        f.write("API_PREFIX=/api/v1\n\n")
        
        f.write("# Database (MySQL)\n")
        f.write(f"DB_PASSWORD={db_password}\n")
        f.write(f"DB_ROOT_PASSWORD={db_root_password}\n")
        f.write(f"DATABASE_URL=mysql://zta_user:{db_password}@localhost:3306/zta_finance\n\n")
        
        f.write("# Redis\n")
        f.write(f"REDIS_PASSWORD={redis_password}\n")
        f.write(f"REDIS_URL=redis://:{redis_password}@localhost:6379/0\n\n")
        
        f.write("# Security\n")
        f.write(f"JWT_SECRET_KEY={jwt_secret}\n")
        f.write("JWT_ALGORITHM=HS256\n")
        f.write("JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15\n")
        f.write("JWT_REFRESH_TOKEN_EXPIRE_DAYS=7\n\n")
        
        f.write("# Encryption\n")
        f.write(f"ENCRYPTION_KEY={encryption_key}\n")
        f.write("ENCRYPTION_ALGORITHM=AES-256-GCM\n\n")
        
        f.write("# MFA\n")
        f.write("MFA_ISSUER=ZTA-Finance\n")
        f.write("MFA_REQUIRED=True\n\n")
        
        f.write("# Rate Limiting\n")
        f.write("RATE_LIMIT_PER_MINUTE=60\n")
        f.write("RATE_LIMIT_PER_HOUR=1000\n\n")
        
        f.write("# Session Management\n")
        f.write("SESSION_TIMEOUT_MINUTES=30\n")
        f.write("MAX_FAILED_LOGIN_ATTEMPTS=5\n")
        f.write("ACCOUNT_LOCKOUT_DURATION_MINUTES=30\n\n")
        
        f.write("# Risk Scoring\n")
        f.write("RISK_THRESHOLD_LOW=30\n")
        f.write("RISK_THRESHOLD_MEDIUM=60\n")
        f.write("RISK_THRESHOLD_HIGH=80\n\n")
        
        f.write("# Audit Logging\n")
        f.write("AUDIT_LOG_RETENTION_DAYS=365\n")
        f.write("AUDIT_LOG_ENCRYPTION=True\n\n")
        
        f.write("# Device Verification\n")
        f.write("DEVICE_FINGERPRINT_REQUIRED=True\n")
        f.write("TRUSTED_DEVICE_DURATION_DAYS=30\n")
    
    print("✓ Keys saved to .env file")
    print()


if __name__ == "__main__":
    main()