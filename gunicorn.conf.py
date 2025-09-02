# Gunicorn configuration for production
import multiprocessing

# Server socket
bind = "0.0.0.0:8080"
backlog = 2048

# Worker processes - start with 2 for testing
workers = 2  # You can increase this: multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Timeout for long-running WebRTC connections
timeout = 300  # 5 minutes for voice conversations
keepalive = 30

# Logging
loglevel = "info"
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr

# Process naming
proc_name = "pipecat_bot"

# Server mechanics
preload_app = False  # Don't preload for better isolation
# pidfile = "/tmp/gunicorn.pid"  # Disabled for container compatibility
user = None
group = None
tmp_upload_dir = None

# SSL (configure if needed)
keyfile = None
certfile = None
