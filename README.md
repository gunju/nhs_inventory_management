# NHS Care Operations Copilot

NHS Care Operations Copilot is a portfolio-grade B2B healthcare AI MVP for NHS-style provider workflows. It is designed as a clinical operations decision-support system, not an autonomous clinical system. The product connects patient pathway signals to protocol-backed inventory recommendations, short-horizon demand forecasting, and referral triage drafting with citations and audit trails.

## Why this exists

Current market tooling is fragmented. Inventory platforms handle stock visibility and scanning, virtual ward tools handle monitoring, and referral systems handle routing. The missing layer is the operational copilot that links:

- patient pathway signals
- approved protocol evidence
- recommended inventory bundles
- demand risk
- referral triage drafting

This MVP addresses that gap for a bounded synthetic NHS-style workflow: `Virtual Ward Support + Inventory Copilot`.

## Scope and safety

- Decision support only
- Synthetic or pseudonymised data only
- Human approval required for every recommendation
- No autonomous diagnosis
- No appointment booking
- No prescribing
- No autonomous referral submission
- No recommendations without provenance

## Architecture

Backend stack:

- FastAPI
- Python 3.11
- PostgreSQL via SQLAlchemy
- FAISS vector retrieval with LangChain
- Pydantic schemas
- Deterministic inventory mapping and risk rules
- Structured forecasting without LLMs

Frontend stack:

- React
- TypeScript
- Vite
- Tailwind CSS
- Recharts

AI stack:

- LangChain for document ingestion, chunking, embeddings, vector retrieval, and evidence handling
- Open base model plus LoRA adapters for structured patient requirement extraction and referral triage classification

Project layout:

```text
app/
├── api/
├── audit/
├── core/
├── db/
├── finetuning/
├── forecasting/
├── models/
├── rag/
├── schemas/
├── services/
└── utils/
frontend/
data/
scripts/
tests/
```

## Current MVP features

- Document upload and re-index endpoints
- LangChain-based protocol ingestion and retrieval
- First vertical slice:
  patient case input -> patient need extraction -> protocol retrieval -> deterministic inventory recommendation with citations -> audit log
- Baseline 7/14/28 day inventory forecasting with q10/q50/q90 bands
- Referral triage draft generation with required human approval
- Synthetic NHS-style seed data
- Offline evaluation harness
- OpenAPI docs from FastAPI

## Database models

Implemented tables:

- documents
- document_chunks
- inventory_catalog
- inventory_levels
- inventory_consumption_history
- pathway_events
- patient_cases
- referral_notes
- recommendation_runs
- forecast_runs
- audit_logs

## Setup

1. Copy `.env.example` to `.env`.
2. Start PostgreSQL and the app stack:

```bash
docker-compose up --build
```

3. Seed synthetic data:

```bash
python scripts/seed_data.py
```

4. Open:

- API docs: `http://localhost:8000/docs`
- Frontend: `http://localhost:5173`

## LoRA fine-tuning

Synthetic training datasets are included in [data/seed/extraction_train.jsonl](/c:/Users/gunja/Documents/nhs_inventory_management/data/seed/extraction_train.jsonl) and [data/seed/triage_train.jsonl](/c:/Users/gunja/Documents/nhs_inventory_management/data/seed/triage_train.jsonl).

Train an adapter:

```bash
python app/finetuning/lora_train.py \
  --base-model TinyLlama/TinyLlama-1.1B-Chat-v1.0 \
  --dataset data/seed/extraction_train.jsonl \
  --output-dir artifacts/lora/extraction
```

Run a triage adapter:

```bash
python app/finetuning/lora_train.py \
  --base-model TinyLlama/TinyLlama-1.1B-Chat-v1.0 \
  --dataset data/seed/triage_train.jsonl \
  --output-dir artifacts/lora/triage
```

If no adapter is present, the app falls back to deterministic heuristics so the local MVP still runs.

## Example API calls

Inventory recommendation:

```bash
curl -X POST http://localhost:8000/api/v1/copilot/inventory-recommendation \
  -H "Content-Type: application/json" \
  -d '{
    "patient_pseudo_id":"P001",
    "case_summary":"Patient on virtual ward with COPD exacerbation and declining oxygen saturation over 48 hours.",
    "site_id":"site_01",
    "user_role":"virtual_ward_coordinator"
  }'
```

Forecast:

```bash
curl "http://localhost:8000/api/v1/forecasting/run?site_id=site_01&horizon_days=14"
```

Referral draft:

```bash
curl "http://localhost:8000/api/v1/referral/draft?patient_pseudo_id=P001&specialty_requested=respiratory"
```

## Evaluation

Run the offline evaluation harness:

```bash
python scripts/evaluate.py
```

Checks include:

- retrieval recall-like coverage
- citation coverage
- refusal behaviour when evidence is absent
- unsupported claim rate
- forecasting WAPE
- schema validity rate

## Limitations

- Synthetic data only
- FAISS is used for the MVP vector index rather than pgvector
- Baseline forecasting is intentionally simple
- LoRA datasets are illustrative and should be expanded before any serious benchmarking
- No EHR or NHS e-RS integration in this version

## Future roadmap

- EHR integration
- NHS e-RS integration
- GS1 barcode scan ingestion
- role-based access controls
- trust-specific policy packs
- advanced forecasting models
- DTAC-style evidence pack
- FDP compatibility exploration

