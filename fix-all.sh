#!/bin/bash

echo "=============================================="
echo "Applying All Fixes for ZTA-Finance"
echo "=============================================="
echo ""

# Fix 1: Update data_encryptor.py
echo "1. Fixing PBKDF2 import in data_encryptor.py..."
sed -i '' 's/from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2/from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC/' src/encryption/data_encryptor.py
sed -i '' 's/kdf = PBKDF2(/kdf = PBKDF2HMAC(/g' src/encryption/data_encryptor.py
echo "✓ Fixed PBKDF2 import"

# Fix 2: Update settings.py (if not already done)
echo ""
echo "2. Fixing settings.py to allow extra fields..."
if ! grep -q 'extra = "ignore"' config/settings.py; then
    sed -i '' 's/case_sensitive = False/case_sensitive = False\n        extra = "ignore"  # Ignore extra fields in .env file/' config/settings.py
    echo "✓ Fixed settings.py"
else
    echo "✓ settings.py already fixed"
fi

echo ""
echo "=============================================="
echo "✓ All fixes applied!"
echo "=============================================="
echo ""
echo "Now rebuild and restart Docker:"
echo "  docker compose down"
echo "  docker compose up -d --build"
echo ""