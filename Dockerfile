# Dockerfile for Pipecat Bot - Sevalla Deployment
FROM python:3.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/app:$PATH"

# Install system dependencies including ffmpeg for audio/video processing
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make scripts executable
RUN chmod +x /app/start.sh

# Create logs directory
RUN mkdir -p /app/logs

# Expose port (dynamic based on environment)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/health || exit 1

# Start the application with correct host binding for Sevalla
CMD ["python", "runner.py", "--host", "0.0.0.0", "--transport", "daily"]