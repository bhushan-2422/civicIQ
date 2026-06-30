# Processing Service — CivicIQ

Kafka consumer that orchestrates AI processing pipeline for civic complaints.

## Responsibilities
- Consume `{complaintId}` events from Kafka
- Fetch complaint from MySQL
- Download image from GCS URL
- Call Google Gemini API for analysis
- Perform geo-based duplicate detection
- Calculate weighted priority score (0–100)
- Update complaint in MySQL
- Serve `/api/predictions` for predictive maintenance

## Port
Runs on `http://localhost:5001`

## Processing Pipeline

```
Kafka message → Fetch DB → Download image → Gemini AI
→ Duplicate check → Priority calc → Update DB → Done
```

## Setup

```bash
cd processing-service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
python app.py
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/health | Health check |
| GET | /api/predictions | Predictive maintenance data |
