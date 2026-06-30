# ⚡ CivicIQ — AI-Powered Civic Intelligence Platform

> Built for **Vibe2Ship Hackathon 2024**  
> AI-powered platform that transforms how citizens report civic issues and how municipal officers manage them.

---

## 🏗️ Architecture

```
Citizens/Officers (Browser)
        │
        ▼
Frontend (Static HTML/CSS/JS — served via any HTTP server)
        │
        ▼
Main Service (Flask :5000)           Processing Service (Flask :5001)
├── POST /api/complaints    ──────►  Kafka consumer thread
│   ├── Validate form                ├── Fetch complaint from DB
│   ├── Upload image → GCS           ├── Download image from GCS
│   ├── Store in MySQL               ├── Call Gemini API
│   └── Publish to Kafka             ├── Duplicate detection (geo)
│                                    ├── Priority calculation
├── GET /api/complaints               └── Update MySQL
├── PATCH /api/complaints/:id/status
├── POST /api/complaints/:id/assign → Twilio SMS
└── GET /api/stats/*
```

---

## 📁 Folder Structure

```
civic-intelligence-platform/
├── README.md
├── init_db.sql                         ← Run this first!
├── frontend/
│   ├── index.html                      ← Landing page
│   ├── citizen.html                    ← Report & track complaints
│   ├── officer.html                    ← Officer dashboard
│   ├── complaint-details.html          ← Complaint detail view
│   ├── dashboard.html                  ← Hotspot + predictive map
│   ├── css/
│   │   ├── variables.css
│   │   ├── main.css
│   │   ├── landing.css
│   │   ├── citizen.css
│   │   ├── officer.css
│   │   ├── dashboard.css
│   │   └── complaint-details.css
│   └── js/
│       ├── api.js                      ← Shared API client
│       ├── utils.js                    ← Shared UI utilities
│       ├── maps.js                     ← Google Maps helper
│       ├── landing.js
│       ├── citizen.js
│       ├── officer.js
│       ├── dashboard.js
│       └── complaint-details.js
├── main-service/
│   ├── app.py
│   ├── config.py
│   ├── models.py
│   ├── routes/
│   │   ├── complaints.py
│   │   ├── users.py
│   │   └── stats.py
│   ├── services/
│   │   ├── storage.py                  ← GCS upload
│   │   ├── kafka_producer.py           ← Kafka publish
│   │   └── twilio_service.py           ← SMS
│   ├── requirements.txt
│   ├── .env.example
│   └── .env                            ← Your actual credentials
└── processing-service/
    ├── app.py
    ├── config.py
    ├── models.py
    ├── consumer.py                     ← Kafka consumer pipeline
    ├── services/
    │   ├── gemini_service.py           ← Gemini AI
    │   ├── duplicate_detector.py       ← Haversine geo check
    │   ├── priority_calculator.py      ← Weighted formula
    │   └── storage.py                  ← Image download
    ├── requirements.txt
    ├── .env.example
    └── .env                            ← Your actual credentials
```

---

## 🗄️ Database Schema

### complaints
| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR(36) | UUID primary key |
| category | ENUM | ROAD_DAMAGE, WATER_LEAKAGE, STREETLIGHT, TRAFFIC_SIGNAL, SEWERAGE, GARBAGE, TREE_FALL, OTHER |
| department | ENUM | ROADS, WATER, ELECTRICITY, TRAFFIC, SANITATION, SEWER, PARKS, OTHER |
| description | TEXT | Citizen's description |
| imageUrl | TEXT | GCS public URL |
| latitude | DECIMAL(10,8) | GPS latitude |
| longitude | DECIMAL(11,8) | GPS longitude |
| priorityScore | DECIMAL(5,2) | 0–100 priority score |
| severityScore | DECIMAL(4,3) | 0–1 AI severity |
| communityValidation | DECIMAL(4,3) | 0–1 validation score |
| reporterCredibility | DECIMAL(4,3) | 0–1 credibility |
| estimatedCost | INT | INR estimate |
| estimatedDuration | VARCHAR(100) | e.g. "3-5 days" |
| summary | TEXT | AI summary |
| status | ENUM | PROCESSING, VALID, IN_PROGRESS, RESOLVED, REJECTED |
| reporterName | VARCHAR(255) | |
| reporterPhone | VARCHAR(20) | |
| isDuplicate | BOOLEAN | |
| parentComplaintId | VARCHAR(36) | FK → complaints.id |
| createdAt | DATETIME | |
| updatedAt | DATETIME | |

### users
| Column | Type | Description |
|--------|------|-------------|
| id | INT | Auto-increment PK |
| name | VARCHAR(255) | |
| phone | VARCHAR(20) | Unique |
| credibilityScore | DECIMAL(4,3) | Default 0.5 |
| validatedCount | INT | Complaints validated |
| rejectedCount | INT | Complaints rejected |

### complaint_reporters
| Column | Type | Description |
|--------|------|-------------|
| id | INT | PK |
| complaintId | VARCHAR(36) | FK → complaints |
| userId | INT | FK → users |
| reportedAt | DATETIME | |

---

## 📊 ER Diagram

```
users (1) ──────< complaint_reporters >────── (N) complaints
                                                     │
                                               parentComplaintId
                                                     │
                                               complaints (self-ref)
```

---

## ⚡ Priority Formula

```
Praw = wS×S + wC×C + wR×R + wU×U + wV×V
P = clip(100 × E × Praw, 0, 100)

S  = AI severity score (0–1)         wS = 0.35
C  = Criticality — nearby infra (0–1) wC = 0.20
R  = Recurrence / hotspot (0–1)      wR = 0.15
U  = Reporter credibility (0–1)       wU = 0.15
V  = Community validation (0–1)       wV = 0.15
E  = Equity multiplier               default = 1.0
```

---

## 🔄 Kafka Flow

```
Main Service
  └── producer.send("complaints", {"complaintId": "uuid"})
        │
        ▼
Processing Service
  └── consumer.poll() → process_complaint(complaintId)
```

---

## 🚀 Quick Start (Local)

### 1. Prerequisites

- Python 3.10+
- MySQL 8.0+ (local, user: bhushan, password: 161176)
- Apache Kafka (local, port 9092)
- Google Cloud account (for GCS + Maps + Gemini)
- Twilio account (for SMS)

### 2. Create Kafka Topic

```bash
# Start Zookeeper (if not running)
bin/zookeeper-server-start.sh config/zookeeper.properties &

# Start Kafka broker
bin/kafka-server-start.sh config/server.properties &

# Create topic
bin/kafka-topics.sh --create \
  --topic complaints \
  --bootstrap-server localhost:9092 \
  --partitions 1 \
  --replication-factor 1
```

### 3. Initialize Database

```bash
mysql -u bhushan -p161176 < init_db.sql
```

### 4. Install Main Service

```bash
cd main-service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Edit .env — add GCS_BUCKET_NAME, GOOGLE_MAPS_API_KEY, Twilio keys
nano .env

python app.py
# → Running on http://localhost:5000
```

### 5. Install Processing Service

```bash
cd processing-service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Edit .env — add GEMINI_API_KEY, GCS_BUCKET_NAME, GOOGLE_MAPS_API_KEY
nano .env

python app.py
# → Running on http://localhost:5001 + Kafka consumer active
```

### 6. Serve Frontend

```bash
# Using Python (simplest)
cd frontend
python -m http.server 5500
# → http://localhost:5500

# Or using VS Code Live Server extension (right-click index.html → Open with Live Server)
```

### 7. Configure Frontend API Keys

Edit `frontend/index.html` (and all other HTML files) — find the `<script>` block:
```js
window.CIVIC_CONFIG = {
  MAIN_SERVICE_URL: 'http://localhost:5000',
  PROCESSING_SERVICE_URL: 'http://localhost:5001',
  GOOGLE_MAPS_API_KEY: 'your-maps-api-key-here',  // ← Add this
};
```

---

## 🔑 Environment Variable Checklist

### main-service/.env
- [ ] `MYSQL_HOST` = localhost
- [ ] `MYSQL_USER` = bhushan
- [ ] `MYSQL_PASSWORD` = 161176
- [ ] `MYSQL_DATABASE` = civic_platform
- [ ] `KAFKA_BROKER` = localhost:9092
- [ ] `KAFKA_TOPIC` = complaints
- [ ] `GCS_BUCKET_NAME` = **YOUR GCS BUCKET**
- [ ] `GCS_CREDENTIALS_PATH` = **PATH TO SERVICE ACCOUNT JSON**
- [ ] `GOOGLE_MAPS_API_KEY` = **YOUR MAPS API KEY**
- [ ] `TWILIO_ACCOUNT_SID` = **YOUR TWILIO SID**
- [ ] `TWILIO_AUTH_TOKEN` = **YOUR TWILIO TOKEN**
- [ ] `TWILIO_PHONE_NUMBER` = **YOUR TWILIO NUMBER**

### processing-service/.env
- [ ] Same MySQL + Kafka settings
- [ ] `GEMINI_API_KEY` = **YOUR GEMINI API KEY**
- [ ] Same GCS + Maps settings
- [ ] Priority weights (defaults are pre-configured)

---

## 📡 API Reference

### POST /api/complaints
Submit a new civic complaint.

**Request:** `multipart/form-data`
```
name        string   Reporter's full name
phone       string   Reporter's phone number
description string   Complaint description (min 20 chars)
latitude    float    GPS latitude
longitude   float    GPS longitude
image       file     (optional) Complaint photo
```

**Response 201:**
```json
{
  "success": true,
  "complaintId": "uuid-string",
  "status": "PROCESSING",
  "message": "Complaint submitted successfully."
}
```

---

### GET /api/complaints
List complaints with filters and pagination.

**Query Params:**
```
status      string   PROCESSING|VALID|IN_PROGRESS|RESOLVED|REJECTED
department  string   ROADS|WATER|ELECTRICITY|...
category    string   ROAD_DAMAGE|WATER_LEAKAGE|...
search      string   Full-text search
sort        string   createdAt|priorityScore|status (default: createdAt)
order       string   asc|desc (default: desc)
page        int      (default: 1)
per_page    int      (default: 20, max: 100)
```

---

### PATCH /api/complaints/:id/status
Update complaint status.

**Request JSON:**
```json
{ "status": "VALID" }
```

**Valid values:** `VALID`, `IN_PROGRESS`, `RESOLVED`, `REJECTED`

---

### POST /api/complaints/:id/assign
Assign worker and send Twilio SMS.

**Request JSON:**
```json
{
  "workerName": "Rajesh Kumar",
  "workerPhone": "+919876543210"
}
```

---

### GET /api/predictions (Processing Service :5001)
Rule-based predictive maintenance analysis.

**Response 200:**
```json
{
  "success": true,
  "data": [
    {
      "category": "ROAD_DAMAGE",
      "complaintCount": 8,
      "probability": 0.40,
      "riskLevel": "MEDIUM",
      "recommendation": "Schedule preventive road inspection...",
      "centerLat": 18.5204,
      "centerLng": 73.8567
    }
  ]
}
```

---

## 📚 Libraries Used

### Backend (both services)
| Library | Version | Purpose |
|---------|---------|---------|
| Flask | 3.0.3 | Web framework |
| Flask-CORS | 4.0.1 | Cross-origin requests |
| SQLAlchemy | 2.0.30 | ORM |
| PyMySQL | 1.1.1 | MySQL driver |
| kafka-python | 2.0.2 | Kafka producer/consumer |
| google-cloud-storage | 2.17.0 | GCS image upload |
| google-generativeai | 0.7.2 | Gemini AI (processing only) |
| python-dotenv | 1.0.1 | .env loading |
| requests | 2.32.3 | HTTP client |
| Pillow | 10.3.0 | Image handling |
| gunicorn | 22.0.0 | Production WSGI |
| twilio | 9.2.3 | SMS (main only) |

### Frontend
- Pure HTML5, CSS3 (with CSS Custom Properties)
- Vanilla JavaScript (ES2020)
- Google Fonts (Inter)
- Google Maps JavaScript API

---

## 🤖 Google Technologies Used

1. **Google Gemini API** (`gemini-1.5-flash`) — Complaint classification and severity analysis
2. **Google Cloud Storage** — Complaint image hosting
3. **Google Maps Platform** — Location picker, heatmap, and criticality scoring via Places API

---

## 🔒 Security Notes

- Never commit `.env` files (gitignored)
- GCS credentials via service account JSON
- All secrets loaded from environment variables
- No hardcoded passwords

---

## ⚠️ Known Limitations

1. **No authentication** — As per project spec, officer portal has no login
2. **Google Maps API key** — Required for map features; degrade gracefully without it
3. **Kafka must be running** — Complaints are saved even if Kafka is down, but won't be processed until Kafka is available

---

*Made with ❤️ for smarter cities — Vibe2Ship Hackathon 2026*
