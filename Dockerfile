# Dockerfile for Pipecat Bot - Sevalla Deployment
FROM python:3.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/app:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy minimal requirements first for better caching
COPY requirements_minimal.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements_minimal.txt

# Copy application code
COPY . .

# Make scripts executable
RUN chmod +x /app/start.sh

# Create logs directory
RUN mkdir -p /app/logs

# Expose port
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# Start the application using uvicorn directly
CMD ["uvicorn", "simple_test:app", "--host", "0.0.0.0", "--port", "7860", "--log-level", "info"]