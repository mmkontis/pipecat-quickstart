#!/bin/bash
# Production startup script for Sevalla

echo "🚀 Starting Pipecat Bot in Production Mode"
echo "📊 Workers: $(nproc)"
echo "🌐 Port: ${PORT:-8080}"
echo "🚗 Transport: ${TRANSPORT:-daily}"

# Set production environment
export PYTHONPATH=/app
export PYTHONUNBUFFERED=1

# Create logs directory (skip if read-only)
mkdir -p /app/logs 2>/dev/null || mkdir -p ./logs 2>/dev/null || true

# Start the actual Pipecat runner (not the test app)
exec python runner.py \
    --host 0.0.0.0 \
    --port ${PORT:-8080} \
    --transport ${TRANSPORT:-daily}
