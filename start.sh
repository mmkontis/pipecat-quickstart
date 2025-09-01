#!/bin/bash
# Production startup script for Sevalla

echo "🚀 Starting Pipecat Bot in Production Mode"
echo "📊 Workers: $(nproc)"
echo "🌐 Port: 7860"

# Set production environment
export PYTHONPATH=/app
export PYTHONUNBUFFERED=1

# Create logs directory (skip if read-only)
mkdir -p /app/logs 2>/dev/null || mkdir -p ./logs 2>/dev/null || true

# Start with the ultra-simple test app
exec uvicorn \
    simple_test:app \
    --host 0.0.0.0 \
    --port 7860 \
    --workers 1 \
    --log-level info \
    --access-log
