FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p logs

EXPOSE 8000

# Run uvicorn directly instead of python -m
CMD ["uvicorn", "src.api.gateway:app", "--host", "0.0.0.0", "--port", "8000"]
