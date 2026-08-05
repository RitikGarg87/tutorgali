# Gunicorn configuration for TutorGali
# Place this file at: /home/ubuntu/tutorgali/deploy/gunicorn.conf.py

import multiprocessing

# Bind to Unix socket (Nginx will proxy to this)
bind = 'unix:/run/tutorgali.sock'

# Workers: (2 × CPU cores) + 1  is the standard formula
workers = multiprocessing.cpu_count() * 2 + 1

# Worker class
worker_class = 'sync'

# Timeouts
timeout       = 120
keepalive     = 5
graceful_timeout = 30

# Logging
accesslog = '/home/ubuntu/tutorgali/logs/gunicorn_access.log'
errorlog  = '/home/ubuntu/tutorgali/logs/gunicorn_error.log'
loglevel  = 'warning'

# Process naming
proc_name = 'tutorgali'

# Reload on code change (disable in production)
reload = False
