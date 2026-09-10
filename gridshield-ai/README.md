# GridShield AI
### Agentic AI Electricity Fraud Detection & Investigation Platform
**Problem Statement #18 – AI Agent for Electricity Bill Fraud Detection**

---

## Overview

GridShield AI is a fully functional, end-to-end electricity fraud detection and investigation platform. It analyzes real electricity billing and consumption data to detect anomalies, assess fraud risk, and support investigator workflows using an IBM watsonx.ai–powered multi-agent pipeline.

**Core capability stack:**
```
Real Data → Validation → Consumption Analysis → 5-Agent AI Pipeline →
Risk Score (0-100) → Explainable Evidence → Case Management → PDF Report
```

---

## Architecture

```
Frontend (React + Vite)          Backend (FastAPI + Python)
──────────────────────           ──────────────────────────
Dashboard                        /api/data      ← ingestion, validation
Investigate Workspace   ←API→    /api/analysis  ← profiling, anomaly detection
Anomaly List                     /api/agents    ← IBM watsonx.ai agent pipeline
Case Management                  /api/cases     ← case CRUD + timeline
Report Download                  /api/reports   ← PDF + JSON report generation

                    IBM watsonx.ai (granite-13b-chat-v2)
                    ├── DataAnalysisAgent
                    ├── AnomalyDetectionAgent
                    ├── FraudInvestigationAgent
                    ├── ExplainabilityAgent
                    └── DecisionSupportAgent

                    SQLite (dev) / PostgreSQL (prod)
```

---

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env          # edit to add IBM credentials
python -m uvicorn main:app --reload --port 8000
```

Or use the batch script (Windows):
```
start_backend.bat
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Or:
```
start_frontend.bat
```

Frontend: **http://localhost:5173**  
Backend API docs: **http://localhost:8000/docs**

### 3. Load Test Data

```
load_sample_data.bat
```

This generates 200 test consumers (18 months each) with realistic consumption patterns including simulated fraud scenarios, uploads them, and runs batch anomaly detection.

> **WARNING:** Sample data is for system testing only and is clearly labeled `SAMPLE_TESTING_DATA_NOT_REAL`.  
> Replace with real electricity billing data for production use.

---

## IBM watsonx.ai Configuration

Edit `backend/.env`:

```
IBM_WATSONX_API_KEY=your_ibm_cloud_api_key
IBM_WATSONX_PROJECT_ID=your_watsonx_project_id
IBM_WATSONX_URL=https://us-south.ml.cloud.ibm.com
```

Get credentials at: https://cloud.ibm.com/catalog/services/watson-machine-learning

**Without credentials:** All statistical anomaly detection, risk scoring, and case management work fully. Only the AI narrative text (agent reasoning paragraphs) requires IBM watsonx.ai. The system clearly labels when AI narratives are unavailable.

---

## Real Dataset Sources

| Dataset | Description | URL |
|---------|-------------|-----|
| SGCC Electricity Theft | Labeled fraud/normal – State Grid Corp of China | https://www.kaggle.com/datasets/dvnguyen/electricity-theft-detection |
| UCI Household Power | 4-year household consumption at 1-min resolution | https://archive.ics.uci.edu/dataset/235 |
| Open Gov Portals | data.gov, data.gov.in, country-specific open data | https://data.gov |

Upload any CSV/Excel file via **Data Management → Upload** in the UI, or `POST /api/data/upload`.  
Columns are auto-mapped from 50+ common real-world naming variants.

**Minimum required column:** `consumer_id` (or any alias: account_no, meter_no, cust_id…)

---

## Anomaly Detection

Statistical detectors (all data-driven, no hardcoded thresholds beyond configurable env vars):

| Detector | What it finds |
|----------|---------------|
| `SUDDEN_DROP` | Consumption drops ≥40% in one period |
| `SUDDEN_SPIKE` | Consumption ≥2.5× historical mean |
| `HIGH_ZSCORE` | z-score > 2.5 std deviations from personal mean |
| `BILLING_MISMATCH` | Billed units vs consumed units > 10% discrepancy |
| `METER_GAP` | Meter reading difference ≠ recorded consumption |
| `ZERO_CONSUMPTION` | Near-zero usage while historically active |
| `HIGH_VARIABILITY` | Coefficient of variation > 80% |

Thresholds configurable in `backend/.env`:
```
ANOMALY_ZSCORE_THRESHOLD=2.5
SUDDEN_DROP_THRESHOLD=0.40
SUDDEN_SPIKE_THRESHOLD=2.50
```

---

## Risk Score

Fraud risk score **0–100** is computed dynamically from:
- Anomaly type weights (meter gaps and billing mismatches weighted highest)
- Severity multipliers (Critical → 1.5×, High → 1.2×)
- Frequency adjustment (proportion of affected periods)
- Confidence modifier (based on months of data available)

Risk levels:
- **Low** (0–29): Monitor only
- **Medium** (30–54): Remote record review
- **High** (55–74): Schedule field visit
- **Critical** (75–100): Immediate inspection + meter audit

> All risk scores are labeled **"AI-assisted fraud risk / investigation priority"**  
> and are **not** a legal determination of fraud.

---

## Workflow

```
Upload Data  →  Run Batch Analysis  →  Review Dashboard
     ↓                                        ↓
Investigate Consumer  →  Run AI Investigation  →  Create Case
     ↓                                        ↓
Update Case Status  →  Add Notes  →  Download PDF Report
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/data/upload` | Upload CSV/Excel billing file |
| GET | `/api/data/consumers` | List all consumers |
| GET | `/api/data/consumers/{id}/records` | Billing records for consumer |
| GET | `/api/data/stats` | Dataset statistics |
| GET | `/api/analysis/consumer/{id}/profile` | Consumption profile |
| GET | `/api/analysis/consumer/{id}/anomalies` | Anomaly detection results |
| POST | `/api/analysis/run-batch` | Batch analyze all consumers |
| GET | `/api/analysis/dashboard` | Dashboard KPIs |
| GET | `/api/analysis/anomaly-list` | All anomaly results |
| POST | `/api/agents/investigate/{id}` | Run 5-agent AI pipeline |
| GET | `/api/agents/status` | watsonx.ai connectivity |
| POST | `/api/cases/` | Create investigation case |
| GET | `/api/cases/` | List cases |
| GET | `/api/cases/{id}` | Get case + timeline |
| PATCH | `/api/cases/{id}` | Update status/assignment |
| POST | `/api/cases/{id}/events` | Add case event/note |
| GET | `/api/reports/{id}/pdf` | Download PDF report |
| GET | `/api/reports/{id}/json` | Get JSON report |

Full interactive docs at: **http://localhost:8000/docs**

---

## Project Structure

```
gridshield-ai/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── requirements.txt
│   ├── .env.example               # Environment variable template
│   ├── agents/
│   │   └── watsonx_agents.py      # 5-agent IBM watsonx.ai pipeline
│   ├── models/
│   │   └── db_models.py           # SQLAlchemy ORM models
│   ├── routes/
│   │   ├── data.py                # Data ingestion API
│   │   ├── analysis.py            # Anomaly detection API
│   │   ├── cases.py               # Case management API
│   │   ├── agents.py              # AI investigation API
│   │   └── reports.py             # Report generation API
│   └── services/
│       ├── database.py            # SQLAlchemy async DB
│       ├── ingestion.py           # Data validation + cleaning
│       ├── analysis.py            # Consumption profiling
│       ├── anomaly_detection.py   # Statistical anomaly detectors
│       └── report_service.py      # PDF report generation
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── DashboardPage.tsx
│       │   ├── InvestigatePage.tsx
│       │   ├── AnomalyListPage.tsx
│       │   ├── CasesPage.tsx
│       │   ├── CaseDetailPage.tsx
│       │   └── DataPage.tsx
│       ├── components/
│       │   ├── Layout.tsx
│       │   └── shared.tsx
│       ├── services/
│       │   └── api.ts             # Axios API client
│       ├── types/
│       │   └── index.ts
│       └── utils/
│           └── formatting.ts
└── data/
    ├── generate_sample.py         # Sample dataset generator
    └── sample/                    # Generated test data (not committed)
```

---

## Disclaimer

GridShield AI is an **investigative support tool**. All fraud risk scores and AI assessments are clearly labeled as "AI-assisted investigation priority" and do not constitute a legal determination of fraud. Decisions on enforcement actions must follow applicable regulatory and legal processes.  cd backend && pip install -r requirements.txt && python -m uvicorn main:app --reload --port 8000
cd frontend && npm install && npm run dev
