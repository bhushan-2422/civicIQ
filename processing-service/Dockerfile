FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Cloud Run sets PORT env var — default to 5001
ENV PORT=5001
ENV FLASK_ENV=production

EXPOSE $PORT

# Start gunicorn (Flask HTTP) + Pub/Sub subscriber in same process
# The subscriber thread is started inside app.py __main__ block,
# so we use a custom entrypoint that runs python directly
CMD exec gunicorn \
    --config gunicorn.conf.py \
    wsgi:app
