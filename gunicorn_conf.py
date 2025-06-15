import multiprocessing

# Bind to all interfaces on port 8000
bind = "0.0.0.0:5002"

# Use a number of workers based on CPU cores (2 * cores + 1)
workers = 1

# Preload application to save memory on worker forks
# Disabled due to SIGSEGV issues with certain C-extensions.
# Each worker initializes its own application instance to avoid faults.
preload_app = False

# Maximum time to wait for a worker response (in seconds)
timeout = 120

# Log to stdout/stderr so systemd/journalctl can capture it
accesslog = "-"
errorlog = "-"

# Enable keep-alive connections
keepalive = 2
