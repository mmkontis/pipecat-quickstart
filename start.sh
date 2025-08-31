#!/bin/bash
# Production startup script for Sevalla

echo "🚀 Starting Pipecat Bot in Production Mode"
echo "📊 Workers: $(nproc)"
echo "🌐 Port: 7860"

# Set production environment
export PYTHONPATH=/app
export PYTHONUNBUFFERED=1

# Start with Gunicorn
exec gunicorn \
    --config gunicorn.conf.py \
    --log-config logging.conf \
    bot:app
