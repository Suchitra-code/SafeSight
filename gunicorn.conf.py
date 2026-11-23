"""
Gunicorn configuration for SafeSight AI production deployment on Render.

Key decisions:
- 1 worker: Render free tier has 512MB RAM. YOLO alone uses ~300MB.
  Multiple workers would OOM-kill immediately.
- gthread worker class: allows concurrent requests without forking
  (no memory duplication), handles SSE + MJPEG streams without blocking.
- threads=6: 6 concurrent requests per worker. Handles API, assets, and streams.
- timeout=300: YOLO model loads in ~30-90s on a cold Render boot.
  300s gives ample headroom for slow cold starts and deep learning inference.
- graceful_timeout=30: gives in-flight requests 30s to finish during reloads.
- preload_app=False: CRITICAL. Prevents arbiter boot timeout during model load.
- max_requests=250: Recycles worker periodically to prevent memory accumulation.
- worker_tmp_dir='/dev/shm': Uses RAM-backed tmpfs for worker heartbeat
  files on Linux, preventing disk I/O from causing false timeout kills.
"""
import os

# Server socket - binds dynamically to Render's assigned $PORT
port = os.environ.get("PORT", "10000")
bind = f"0.0.0.0:{port}"

# Worker processes & threading
workers = 1
worker_class = "gthread"
threads = 6

# Timeouts (in seconds)
timeout = 300
graceful_timeout = 30
keepalive = 5

# App loading
preload_app = False

# Worker recycling
max_requests = 250
max_requests_jitter = 25

# Worker heartbeat directory (safe fallback for non-Linux or read-only /dev/shm)
if os.path.exists("/dev/shm") and os.access("/dev/shm", os.W_OK):
    worker_tmp_dir = "/dev/shm"

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Reverse proxy trust
forwarded_allow_ips = "*"
