"""
Gunicorn configuration for processing-service.
The Pub/Sub subscriber thread must be started AFTER the worker forks,
not in the master process. Use the post_fork hook for this.
"""
import os

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '5001')}"

# Workers — MUST be 1 so only one subscriber thread runs
workers = 1
threads = 4
timeout = 120
worker_class = "gthread"

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"


def post_fork(server, worker):
    """
    Called after each worker is forked.
    This is where we start the Pub/Sub subscriber thread inside the worker process.
    Starting it in the master process then forking would kill the thread.
    """
    from consumer import start_subscriber_thread
    start_subscriber_thread()
    server.log.info("Pub/Sub subscriber thread started in worker pid=%d", worker.pid)
