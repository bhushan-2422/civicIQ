# Main Service — CivicIQ

Flask-based REST API for complaint submission and management.

## Responsibilities
- Receive and validate complaint form submissions
- Upload complaint images to Google Cloud Storage
- Store complaints in MySQL
- Publish `{complaintId}` events to Kafka topic
- Serve statistics, leaderboard, and complaint CRUD endpoints
- Handle status updates and Twilio SMS worker assignment

## Port
Runs on `http://localhost:5000`

## Setup

```bash
cd main-service
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
| POST | /api/complaints | Submit complaint |
| GET | /api/complaints | List complaints (filters, pagination) |
| GET | /api/complaints/:id | Get complaint by ID |
| PATCH | /api/complaints/:id/status | Update status |
| POST | /api/complaints/:id/assign | Assign worker + SMS |
| GET | /api/stats | Overall statistics |
| GET | /api/stats/department | Department distribution |
| GET | /api/stats/category | Category distribution |
| GET | /api/stats/hotspots | Map hotspot data |
| GET | /api/users/leaderboard | Top community heroes |
