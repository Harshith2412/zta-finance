#!/bin/bash

# Quick Fix Script for Missing Files
# This ensures all required files are present

echo "Checking for required files..."
echo ""

# Check Dockerfile
if [ ! -f "Dockerfile" ]; then
    echo "❌ Dockerfile is missing. Creating it..."
    cat > Dockerfile << 'EOF'
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Expose API port
EXPOSE 8000

# Run the application
CMD ["python", "-m", "src.api.gateway"]
EOF
    echo "✓ Dockerfile created"
else
    echo "✓ Dockerfile exists"
fi

# Check docker-compose.yml
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ docker-compose.yml is missing. Creating it..."
    cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    container_name: zta-mysql
    environment:
      MYSQL_DATABASE: zta_finance
      MYSQL_USER: zta_user
      MYSQL_PASSWORD: ${DB_PASSWORD:-change_me_in_production}
      MYSQL_ROOT_PASSWORD: ${DB_ROOT_PASSWORD:-change_me_in_production}
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
      - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - zta-network
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "zta_user", "-p${DB_PASSWORD:-change_me_in_production}"]
      interval: 10s
      timeout: 5s
      retries: 5
    command: --default-authentication-plugin=mysql_native_password

  redis:
    image: redis:7-alpine
    container_name: zta-redis
    command: redis-server --requirepass ${REDIS_PASSWORD:-change_me_in_production}
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - zta-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  zta-api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: zta-api
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      - DATABASE_URL=mysql://zta_user:${DB_PASSWORD:-change_me_in_production}@mysql:3306/zta_finance
      - REDIS_URL=redis://:${REDIS_PASSWORD:-change_me_in_production}@redis:6379/0
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    ports:
      - "8000:8000"
    volumes:
      - ./src:/app/src
      - ./config:/app/config
      - ./logs:/app/logs
    networks:
      - zta-network
    restart: unless-stopped

volumes:
  mysql_data:
  redis_data:

networks:
  zta-network:
    driver: bridge
EOF
    echo "✓ docker-compose.yml created"
else
    echo "✓ docker-compose.yml exists"
fi

# Check .env file
if [ ! -f ".env" ]; then
    echo "❌ .env file is missing. Running generate_keys.py..."
    python3 scripts/generate_keys.py
else
    echo "✓ .env file exists"
fi

echo ""
echo "All required files are present!"
echo ""
echo "Now you can run: docker compose up -d"