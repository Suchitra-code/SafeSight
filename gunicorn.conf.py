"""
Gunicorn configuration for SafeSight AI production deployment on Render.

Render Free Tier Memory Optimization:
- 1 worker: Stays within Render's 512MB RAM ceiling (~387MB steady RSS).
  Running multiple workers would duplicate the PyTorch/YOLO process and cause OOM kills.
- gthread worker class: Multi-threaded request concurrency sharing a single model instance.
- threads=4: Serves concurrent HTTP requests, assets, and streams with minimal memory overhead.
- timeout=300: Gives ample headroom for cold starts and deep learning inference.
- graceful_timeout=30: Allows in-flight requests to finish during worker reloads.
- preload_app=False: Lets worker load application after binding, preventing arbiter boot timeouts.
- max_requests=150 (jitter=20): Regularly recycles worker to clear CPython heap fragmentation.
- worker_tmp_dir='/dev/shm': Uses RAM-backed tmpfs for worker heartbeats on Linux.
"""
import os

# Server socket - binds dynamically to Render's assigned $PORT
port = os.environ.get("PORT", "10000")
bind = f"0.0.0.0:{port}"

# Worker processes & threading
workers = 1
worker_class = "gthread"
threads = 4

# Timeouts (in seconds)
timeout = 300
graceful_timeout = 30
keepalive = 5

# App loading
preload_app = False

# Worker recycling
max_requests = 150
max_requests_jitter = 20

# Worker heartbeat directory (safe fallback for non-Linux or read-only /dev/shm)
if os.path.exists("/dev/shm") and os.access("/dev/shm", os.W_OK):
    worker_tmp_dir = "/dev/shm"

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Reverse proxy trust
forwarded_allow_ips = "*"
