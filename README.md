# ⚡ CivicIQ — AI-Powered Civic Intelligence Platform

> Built for **Vibe2Ship Hackathon 2025**  
> AI-powered platform that transforms how citizens report civic issues and how municipal officers manage them — built entirely on Google Cloud.

---

## 🏗️ Architecture

```
Citizens/Officers (Browser)
        │
        ▼
Frontend (Static HTML/CSS/JS — served via nginx on Cloud Run)
        │
        ▼
Main Service (Flask — Cloud Run :5000)
├── POST /api/complaints    ──────►  Google Cloud Pub/Sub
│   ├── Validate form                       │
│   ├── Upload image → GCS                  ▼
│   ├── Store in Firestore         Processing Service (Flask — Cloud Run :5001)
│   └── Publish to Pub/Sub         ├── Subscribe to Pub/Sub
│                                  ├── Fetch complaint from Firestore
├── GET /api/complaints             ├── Download image from GCS
├── PATCH /api/complaints/:id/status├── Call Gemini AI API
├── POST /api/complaints/:id/assign → Twilio SMS
└── GET /api/stats/*                ├── Duplicate detection (Haversine geo)
                                    ├── Priority calculation (weighted formula)
                                    └── Update Firestore → Done
```

---

## 🚀 Tech Stack (Google Cloud Native)

| Layer | Technology |
|-------|-----------|
| **AI Classification** | Google Gemini AI (`gemini-1.5-flash`) |
| **Message Queue** | Google Cloud Pub/Sub |
| **Database** | Google Cloud Firestore |
| **Image Storage** | Google Cloud Storage (GCS) |
| **Compute** | Google Cloud Run (containerized Flask) |
| **Container Build** | Google Cloud Build |
| **Maps & Location** | Google Maps Platform + Places API |
| **SMS Notifications** | Twilio |
| **Backend Framework** | Python / Flask / Gunicorn |
| **Frontend** | Vanilla HTML5, CSS3, JavaScript (ES2020) |

> ❌ **No MySQL** · ❌ **No Apache Kafka** · ✅ **100% Google Cloud Native**

---

## 📁 Folder Structure

```
civic-intelligence-platform/
├── README.md
├── frontend/
│   ├── index.html                      ← Landing page
│   ├── citizen.html                    ← Report & track complaints
│   ├── officer.html                    ← Officer dashboard
│   ├── complaint-details.html          ← Complaint detail view
│   ├── dashboard.html                  ← Hotspot + predictive map
│   ├── Dockerfile                      ← nginx static server
│   ├── nginx.conf
│   ├── css/
│   │   ├── variables.css               ← Design tokens + dark mode
│   │   ├── main.css                    ← Global styles & components
│   │   ├── landing.css                 ← Hero & landing sections
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
│   ├── models.py                       ← Firestore collection helpers
│   ├── Dockerfile
│   ├── routes/
│   │   ├── complaints.py
│   │   ├── users.py
│   │   └── stats.py
│   └── services/
│       ├── storage.py                  ← GCS upload (ADC)
│       ├── pubsub_producer.py          ← Pub/Sub publish
│       └── twilio_service.py           ← SMS
└── processing-service/
    ├── app.py
    ├── config.py
    ├── models.py
    ├── consumer.py                     ← Pub/Sub subscriber pipeline
    ├── wsgi.py                         ← Gunicorn entrypoint
    ├── gunicorn.conf.py               ← post_fork subscriber hook
    ├── Dockerfile
    └── services/
        ├── gemini_service.py           ← Gemini AI + fallback classifier
        ├── duplicate_detector.py       ← Haversine geo-check (Firestore)
        ├── priority_calculator.py      ← Weighted scoring formula
        └── storage.py                  ← Image download from GCS
```

---

## 🔥 Firestore Data Model

### Collection: `complaints`
| Field | Type | Description |
|-------|------|-------------|
| id | string | UUID document ID |
| category | string | ROAD_DAMAGE \| WATER_LEAKAGE \| STREETLIGHT \| TRAFFIC_SIGNAL \| SEWERAGE \| GARBAGE \| TREE_FALL \| OTHER |
| department | string | ROADS \| WATER \| ELECTRICITY \| TRAFFIC \| SANITATION \| SEWER \| PARKS \| OTHER |
| description | string | Citizen's description |
| imageUrl | string | GCS public URL |
| latitude | number | GPS latitude |
| longitude | number | GPS longitude |
| priorityScore | number | 0–100 weighted priority |
| severityScore | number | 0–1 AI severity |
| communityValidation | number | 0–1 validation score |
| reporterCredibility | number | 0–1 credibility score |
| estimatedCost | number | INR estimate |
| estimatedDuration | string | e.g. "3-5 days" |
| summary | string | AI-generated summary |
| status | string | PROCESSING \| VALID \| IN_PROGRESS \| RESOLVED \| REJECTED |
| reporterName | string | |
| reporterPhone | string | |
| isDuplicate | boolean | |
| parentComplaintId | string | Reference to parent |
| createdAt | timestamp | |
| updatedAt | timestamp | |

### Collection: `users`
| Field | Type | Description |
|-------|------|-------------|
| phone | string | Document ID (unique) |
| name | string | |
| credibilityScore | number | Default 0.5 |
| validatedCount | number | Valid complaints filed |
| rejectedCount | number | Rejected complaints |

### Collection: `complaint_reporters`
| Field | Type | Description |
|-------|------|-------------|
| complaintId | string | Reference to complaint |
| userPhone | string | Reporter's phone |
| reportedAt | timestamp | |

---

## ⚡ Priority Formula

```
Praw = wS×S + wC×C + wR×R + wU×U + wV×V
P = clip(100 × E × Praw, 0, 100)

S  = AI severity score (0–1)          wS = 0.35
C  = Criticality — nearby infra (0–1)  wC = 0.20
R  = Recurrence / hotspot (0–1)        wR = 0.15
U  = Reporter credibility (0–1)        wU = 0.15
V  = Community validation (0–1)        wV = 0.15
E  = Equity multiplier                 default = 1.0
```

---

## 🔄 Pub/Sub Pipeline

```
Main Service
  └── pubsub_client.publish("complaint-created", {"complaintId": "uuid"})
                    │
                    ▼  [Google Cloud Pub/Sub]
Processing Service (civic-processing-service)
  └── subscriber.subscribe("complaint-created-sub", callback)
      └── process_complaint(complaintId)
          ├── Fetch from Firestore
          ├── Download image from GCS
          ├── Gemini AI → category/severity/cost/summary
          ├── Duplicate detection (Haversine, Python-filtered Firestore)
          ├── Priority calculation
          └── Update Firestore → status: VALID
```

---

## 🚀 Quick Start (Local)

### Prerequisites
- Python 3.10+
- Google Cloud account
- `gcloud` CLI authenticated (`gcloud auth application-default login`)
- Firestore database created (`civiclens-db`)
- Pub/Sub topic + subscription created (`complaint-created` / `complaint-created-sub`)
- GCS bucket created

### 1. Run Main Service

```bash
cd main-service
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

export GCP_PROJECT_ID=your-project-id
export FIRESTORE_DATABASE=civiclens-db
export GCS_BUCKET_NAME=your-bucket
export PUBSUB_TOPIC=complaint-created
export GOOGLE_MAPS_API_KEY=your-maps-key
export TWILIO_ACCOUNT_SID=your-sid
export TWILIO_AUTH_TOKEN=your-token
export TWILIO_PHONE_NUMBER=+1xxxxxxxxxx

python app.py
# → Running on http://localhost:5000
```

### 2. Run Processing Service

```bash
cd processing-service
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

export GCP_PROJECT_ID=your-project-id
export FIRESTORE_DATABASE=civiclens-db
export GCS_BUCKET_NAME=your-bucket
export PUBSUB_SUBSCRIPTION=complaint-created-sub
export GEMINI_API_KEY=your-gemini-key
export GOOGLE_MAPS_API_KEY=your-maps-key

python app.py
# → Running on http://localhost:5001 + Pub/Sub subscriber active
```

### 3. Serve Frontend

```bash
cd frontend
python -m http.server 5500
# → http://localhost:5500
```

Update `window.CIVIC_CONFIG` in each HTML file to point to your local services.

---

## ☁️ Deployed Infrastructure

| Service | URL |
|---------|-----|
| **Frontend** | https://civic-frontend-437836275542.asia-south1.run.app |
| **Main API** | https://civic-main-service-437836275542.asia-south1.run.app |
| **Processing API** | https://civic-processing-service-437836275542.asia-south1.run.app |

Deployed on **Google Cloud Run** (asia-south1) via `gcloud run deploy --source`.

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

### GET /api/complaints
List complaints with filters and pagination.

```
status      string   PROCESSING|VALID|IN_PROGRESS|RESOLVED|REJECTED
department  string   ROADS|WATER|ELECTRICITY|...
category    string   ROAD_DAMAGE|WATER_LEAKAGE|...
search      string   Full-text search (Python-side)
sort        string   createdAt|priorityScore|status (default: createdAt)
order       string   asc|desc (default: desc)
page        int      (default: 1)
per_page    int      (default: 20, max: 100)
```

### PATCH /api/complaints/:id/status
```json
{ "status": "VALID" }
```

### POST /api/complaints/:id/assign
```json
{ "workerName": "Rajesh Kumar", "workerPhone": "+919876543210" }
```

### GET /api/predictions (Processing Service)
Rule-based predictive maintenance analysis.

---

## 📚 Libraries Used

### Backend
| Library | Purpose |
|---------|---------|
| Flask 3.x | Web framework |
| Flask-CORS | Cross-origin requests |
| google-cloud-firestore | Firestore client |
| google-cloud-pubsub | Pub/Sub producer & subscriber |
| google-cloud-storage | GCS image upload |
| google-generativeai | Gemini AI classification |
| python-dotenv | Environment variable loading |
| requests | HTTP client (Places API) |
| gunicorn | Production WSGI server |
| twilio | SMS notifications |

### Frontend
- Pure HTML5, CSS3 (Custom Properties, dark/light mode)
- Vanilla JavaScript (ES2020)
- Google Fonts: Inter + Outfit
- Google Maps JavaScript API

---

## 🤖 Google Technologies Used

1. **Google Gemini AI** (`gemini-1.5-flash`) — Complaint image + text classification
2. **Google Cloud Pub/Sub** — Async event pipeline between services
3. **Google Cloud Firestore** — NoSQL document database
4. **Google Cloud Storage** — Complaint image hosting
5. **Google Cloud Run** — Serverless container deployment
6. **Google Cloud Build** — Remote Docker image building
7. **Google Maps Platform** — Location picker, heatmap, criticality scoring

---

## 🔒 Security Notes

- All secrets loaded from environment variables or Cloud Run env vars
- GCS uses Application Default Credentials (ADC) in Cloud Run
- No hardcoded credentials in source code
- `.env` files are gitignored

---

## ⚠️ Known Limitations

1. **No authentication** — Officer portal has no login (as per project spec)
2. **Firestore queries** — Multi-field filters done in Python to avoid composite index requirements
3. **Gemini fallback** — If Gemini API fails, keyword-based fallback classifier is used

---

*Made for smarter cities — Vibe2Ship Hackathon 2026*
