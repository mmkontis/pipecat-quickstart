#!/bin/bash
# Production startup script for Sevalla

echo "🚀 Starting Pipecat Bot in Production Mode"
echo "📊 Workers: $(nproc)"
echo "🌐 Port: 7860"

# Set production environment
export PYTHONPATH=/app
export PYTHONUNBUFFERED=1

# Create logs directory
mkdir -p /app/logs

# Start with Gunicorn using production.py
exec gunicorn \
    --config gunicorn.conf.py \
    --log-level info \
    production:app
