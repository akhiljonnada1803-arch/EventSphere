import os

# Number of worker processes
# On Render free tier (512 MB RAM), 1 worker prevents OOM crashes
workers = int(os.environ.get('WEB_CONCURRENCY', 1))

# Worker class — 'sync' is default; stable for SQLite + SQLAlchemy
worker_class = 'sync'

# Bind address — Render injects $PORT
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

# Timeout — Render default is 30s; increase for slow DB connections
timeout = 120

# Keep-alive for persistent connections
keepalive = 5

# Logging
accesslog = '-'   # stdout
errorlog = '-'    # stderr
loglevel = 'info'

# Preload the app once before forking workers (faster startup, shared memory)
preload_app = True
