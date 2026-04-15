# NHS Inventory Intelligence Copilot — Documentation

## Overview

NHS Inventory Intelligence Copilot is an operational decision-support platform for NHS trusts. It provides:

- Real-time inventory visibility across trusts, hospitals, wards, and locations
- Demand forecasting (moving average, exponential smoothing, LightGBM)
- Shortage and overstock risk scoring
- AI-assisted reorder and redistribution recommendations (human-in-the-loop approval)
- LLM Copilot with RAG-grounded Q&A (no hallucination by design)
- Full audit trail for DSPT/DTAC compliance

**This system is NOT a clinical decision support tool. All AI recommendations require human review before action.**

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         FastAPI Application                       │
│  ┌─────────┐ ┌──────────┐ ┌────────────┐ ┌────────────────────┐ │
│  │  Auth   │ │Inventory │ │Forecasting │ │  Copilot / RAG     │ │
│  │  RBAC   │ │  CRUD    │ │  Service   │ │  LLM + grounding   │ │
│  └─────────┘ └──────────┘ └────────────┘ └────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │               SQLAlchemy 2.x ORM (PostgreSQL + pgvector)     │ │
│  └──────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
         │                          │
    ┌────┴────┐               ┌─────┴──────┐
    │ Celery  │               │  Redis     │
    │ Workers │               │  (broker)  │
    │ + Beat  │               └────────────┘
    └─────────┘
```

### Domain Model

```
Trust
 └── Hospital
      └── Department
           └── Ward
                └── InventoryLocation
                     ├── StockBalance       (current stock level)
                     ├── StockMovement      (append-only ledger)
                     ├── ConsumptionHistory (daily aggregate, forecasting input)
                     ├── ReorderPolicy      (min/max/reorder_point)
                     └── ExpiryBatchLot     (batch tracking)

Product
 ├── ProductCategory
 ├── UOM
 ├── CatalogItem + Supplier
 └── BarcodeIdentifier

AI Layer
 ├── ForecastRun → DemandForecast
 ├── ShortageRisk / OverstockRisk
 ├── ReorderRecommendation (→ RecommendationDecision)
 ├── RedistributionRecommendation
 └── AnomalyEvent / InsightSummary

RAG Layer
 ├── DocumentSource → DocumentChunk → EmbeddingIndexRef
 └── ConversationSession → ConversationMessage → CopilotAnswer

Audit
 ├── AuditLog
 ├── DataAccessLog
 ├── IntegrationRun / FailedIntegrationEvent
 ├── ModelDecisionLog
 └── PromptTemplateVersion
```

---

## Local Setup

### Prerequisites

- Python 3.12+
- PostgreSQL 16 with pgvector extension (or Docker)
- Redis 7

### Quick Start with Docker

```bash
docker compose up -d
```

This starts: PostgreSQL + pgvector, Redis, API server, Celery worker, Celery beat.

### Manual Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env: DATABASE_URL, SECRET_KEY, etc.

# Run migrations
alembic upgrade head

# Seed reference data
python scripts/seed_data.py

# Start API
uvicorn app.main:app --reload --port 8000
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://...` | PostgreSQL connection string |
| `SECRET_KEY` | `CHANGE_ME...` | JWT signing secret (change in production) |
| `APP_ENV` | `development` | `development` / `staging` / `production` |
| `LLM_PROVIDER` | `mock` | `mock` / `openai` / `azure_openai` |
| `EMBEDDING_PROVIDER` | `mock` | `mock` / `openai` / `local` |
| `OPENAI_API_KEY` | *(empty)* | Required if `LLM_PROVIDER=openai` |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Redis broker URL |
| `ENABLE_PGVECTOR` | `true` | Enable vector embeddings |
| `ENABLE_CELERY` | `true` | Enable background task processing |

---

## API Reference

Interactive docs available at `/docs` (Swagger UI) and `/redoc` (ReDoc) when running.

### Key Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/auth/login` | Obtain JWT tokens |
| GET | `/api/v1/auth/me` | Current user info |
| GET | `/api/v1/inventory/stock-balances` | Stock levels (filtered) |
| POST | `/api/v1/inventory/stock-adjustments` | Manual stock correction |
| POST | `/api/v1/forecast/run` | Trigger demand forecast |
| GET | `/api/v1/recommendations/reorder` | Pending reorder recommendations |
| POST | `/api/v1/recommendations/reorder/{id}/decide` | Approve/reject recommendation |
| POST | `/api/v1/copilot/ask` | Ask the copilot a question |
| GET | `/api/v1/audit/logs` | Audit trail |

---

## RBAC Roles

| Role | Permissions |
|---|---|
| `platform_admin` | Full access, user management |
| `trust_admin` | Trust-scoped admin |
| `supply_chain_manager` | Inventory, forecasting, recommendations |
| `ward_manager` | Read inventory, create adjustments |
| `analyst` | Read-only + forecasting |
| `ai_reviewer` | Review and approve AI recommendations |
| `read_only_user` | Read-only across all domains |

---

## Forecasting Models

Three models selected automatically based on data volume:

| Model | Data Requirement | Notes |
|---|---|---|
| `MovingAverageModel` | ≥ 1 day | 14-day window, always available |
| `ExponentialSmoothingModel` | ≥ 14 days | Holt double-exponential smoothing |
| `LightGBMModel` | ≥ 60 days | Lag features + calendar, recursive prediction |

`select_best_model()` chooses the highest-capability model available.

---

## AI Decision Trace

Every copilot answer includes:

```json
{
  "answer": "Ward A ICU has 12 units of 18G Cannula on hand...",
  "confidence": 0.9,
  "reason_codes": ["STOCK_FACT_AVAILABLE"],
  "evidence": [
    {
      "source": "stock_balance",
      "product": "18G Cannula",
      "location": "Ward A ICU",
      "value": "12 units",
      "as_of": "2024-01-15T09:00:00Z"
    }
  ],
  "recommended_actions": [],
  "follow_up_questions": ["What is the daily consumption rate?"],
  "grounded": true
}
```

`grounded: false` indicates the copilot could not find sufficient evidence — it will say so explicitly rather than hallucinate.

---

## Running Tests

```bash
# All tests (41 total)
pytest

# By category
pytest tests/unit/       # Pure unit tests (no DB)
pytest tests/api/        # API endpoint tests (SQLite in-memory)
pytest tests/integration/ # Service integration tests (SQLite in-memory)

# Verbose
pytest -v --tb=short
```

---

## Background Jobs (Celery)

| Task | Schedule | Description |
|---|---|---|
| `run_daily_forecast` | 02:00 UTC daily | Forecast all active products |
| `run_epr_sync` | 01:00 UTC daily | Sync from EPR integration adapter |

Workers managed by Docker Compose services `worker` and `beat`.
