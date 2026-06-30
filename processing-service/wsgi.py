"""
Processing Service — WSGI entrypoint for Gunicorn.
The Pub/Sub subscriber is started via gunicorn.conf.py post_fork hook.
"""
from app import create_app

app = create_app()
