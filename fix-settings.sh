#!/bin/bash

echo "Applying settings.py fix..."

# Backup existing file
cp config/settings.py config/settings.py.backup

# Fix the Config class to ignore extra fields
sed -i '' 's/case_sensitive = False/case_sensitive = False\n        extra = "ignore"  # Ignore extra fields in .env file/' config/settings.py

echo "✓ Fix applied!"
echo ""
echo "Now restart Docker:"
echo "  docker compose down"
echo "  docker compose up -d"