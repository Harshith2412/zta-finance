# ZTA-Finance: Zero Trust Architecture for Financial Systems

A production-ready Zero Trust Architecture implementation for financial services, providing comprehensive security controls including identity verification, continuous authentication, policy enforcement, and end-to-end encryption.

## Features

- **Multi-Factor Authentication (MFA)**: TOTP-based second factor
- **Continuous Verification**: Real-time device and session monitoring
- **Policy-Based Access Control**: Attribute-based access control (ABAC)
- **End-to-End Encryption**: AES-256-GCM encryption for sensitive data
- **Comprehensive Audit Logging**: All security events tracked and analyzed
- **Risk-Based Authentication**: Dynamic risk scoring and adaptive controls
- **API Gateway**: Centralized enforcement point with rate limiting

## Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL 13+
- Redis 6+

### Installation

```bash
# Clone and setup
cd zta-finance
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your configuration

# Initialize database
python scripts/setup_db.py

# Generate encryption keys
python scripts/generate_keys.py

# Run the application
python -m src.api.gateway
```

### Using Docker

```bash
docker-compose up -d
```

## Architecture

This implementation follows NIST SP 800-207 Zero Trust Architecture guidelines:

1. **Never Trust, Always Verify**: Every request is authenticated and authorized
2. **Least Privilege Access**: Minimal permissions granted per request
3. **Assume Breach**: Microsegmentation and continuous monitoring
4. **Verify Explicitly**: Multi-factor authentication and device verification
5. **Encrypt Everything**: End-to-end encryption for data in transit and at rest

## API Usage

```python
import requests

# Authenticate
response = requests.post('http://localhost:8000/api/v1/auth/login', json={
    'username': 'user@example.com',
    'password': 'secure_password',
    'mfa_token': '123456'
})
token = response.json()['access_token']

# Access protected resource
headers = {'Authorization': f'Bearer {token}'}
response = requests.get('http://localhost:8000/api/v1/transactions', headers=headers)
```

## Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Security Considerations

- All passwords are hashed using Argon2
- JWTs expire after 15 minutes (configurable)
- MFA required for sensitive operations
- All API calls are rate-limited
- Device fingerprinting prevents token theft
- Audit logs are immutable and encrypted

## License

MIT License - See LICENSE file for details