# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENABLE_GOOGLE=true \
    ENABLE_SQUARE=true \
    SYNC_INTERVAL=1800 \
    PORT=7173

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose the Flask/Webhook listener port
EXPOSE 7173

# Single unified start command
ENTRYPOINT ["python", "main.py", "serve"]
