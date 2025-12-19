#!/bin/bash

echo "=============================================="
echo "ZTA-Finance Diagnostic Tool"
echo "=============================================="
echo ""

echo "1. Checking Docker containers status..."
docker compose ps
echo ""

echo "2. Checking API logs (last 30 lines)..."
echo "----------------------------------------"
docker compose logs --tail=30 zta-api
echo ""

echo "3. Checking .env file..."
if [ -f ".env" ]; then
    echo "✓ .env file exists"
    echo "Checking required variables:"
    for var in JWT_SECRET_KEY ENCRYPTION_KEY DB_PASSWORD REDIS_PASSWORD; do
        if grep -q "^${var}=" .env; then
            echo "  ✓ $var is set"
        else
            echo "  ✗ $var is missing!"
        fi
    done
else
    echo "✗ .env file not found!"
fi
echo ""

echo "4. Checking if API container can start manually..."
echo "Running: docker compose run --rm zta-api python -c 'import sys; print(sys.version)'"
docker compose run --rm zta-api python -c "import sys; print(sys.version)"
echo ""

echo "5. Checking if config can be imported..."
docker compose run --rm zta-api python -c "from config.settings import settings; print('Config OK')" 2>&1
echo ""

echo "6. Testing database connection..."
docker compose exec mysql mysql -u zta_user -p$(grep DB_PASSWORD .env | cut -d'=' -f2) -e "SHOW DATABASES;" 2>&1 | grep -q zta_finance && echo "✓ Database accessible" || echo "✗ Database not accessible"
echo ""

echo "=============================================="
echo "Diagnostic complete!"
echo "=============================================="