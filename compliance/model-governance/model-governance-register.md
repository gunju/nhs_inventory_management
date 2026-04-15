# AI/ML Model Governance Register — NHS Inventory Intelligence Copilot

> **Status:** ACTIVE — update when models are retrained or changed

## Register

| Model ID | Model Name | Type | Version | Owner | Last Reviewed | Status |
|---|---|---|---|---|---|---|
| M-001 | MovingAverageModel | Forecasting | 1.0 | Data Science | 2024-01 | Active |
| M-002 | ExponentialSmoothingModel | Forecasting | 1.0 | Data Science | 2024-01 | Active |
| M-003 | LightGBMModel | Forecasting | 1.0 | Data Science | 2024-01 | Active |
| M-004 | CopilotGroundedAnswer | LLM (RAG) | 1.0 | AI Team | 2024-01 | Active |

---

## M-001: MovingAverageModel

| Field | Value |
|---|---|
| Purpose | Short-term demand forecasting when limited historical data exists |
| Input features | Daily consumption history (≥ 1 day) |
| Output | q10, q50, q90 demand forecasts for horizon_days |
| Algorithm | Simple 14-day moving average with ±20% confidence bands |
| Training | No training required — deterministic calculation |
| Validation | Compared against held-out last 7 days of history |
| Limitations | Cannot capture trends or seasonality |
| Intended use | Fallback model; locations with < 14 days history |
| Decision impact | Informs reorder recommendations (requires human approval) |

## M-002: ExponentialSmoothingModel

| Field | Value |
|---|---|
| Purpose | Trend-aware demand forecasting |
| Input features | Daily consumption history (≥ 14 days) |
| Output | q10, q50, q90 demand forecasts |
| Algorithm | Holt's double exponential smoothing |
| Training | Parameters fit per product-location pair at runtime |
| Validation | MAPE on held-out test period |
| Limitations | Assumes linear trend; may overfit with noisy data |
| Intended use | Products with 14–59 days of history |
| Decision impact | Informs reorder recommendations (requires human approval) |

## M-003: LightGBMModel

| Field | Value |
|---|---|
| Purpose | High-accuracy demand forecasting with feature engineering |
| Input features | Lag features (1,7,14,28 days), day-of-week, month, rolling means |
| Output | Point forecast per day; confidence intervals from quantile regression |
| Algorithm | LightGBM gradient boosted trees |
| Training | Per product-location pair using all available history |
| Validation | RMSE and MAE on hold-out test period; feature importance logged |
| Limitations | Requires ≥ 60 days of history; not suitable for new products |
| Intended use | Products with ≥ 60 days of history |
| Decision impact | Informs reorder recommendations (requires human approval) |
| Retraining trigger | Monthly or when MAPE degrades > 15% |

## M-004: CopilotGroundedAnswer (LLM)

| Field | Value |
|---|---|
| Purpose | Natural language Q&A about inventory data |
| Type | Retrieval-Augmented Generation (RAG) |
| LLM backbone | Configurable: `mock` (default), `openai/gpt-4o`, `azure_openai` |
| Grounding mechanism | System prompt enforces: only answer from provided context |
| Output format | Structured JSON: `answer`, `confidence`, `evidence`, `grounded` flag |
| Hallucination control | `grounded: false` when insufficient evidence; explicit "I don't know" |
| Prompt versioning | Prompt templates versioned in `PromptTemplateVersion` table |
| Decision impact | Advisory only; no automated actions taken |
| Bias monitoring | Monitor for systematic errors in stock level queries |

---

## Governance Process

### Model Change Control

1. Document proposed change in this register
2. Validate new model against held-out test set
3. Get approval from model owner
4. Deploy with version bump
5. Monitor performance for 30 days post-deployment

### Performance Monitoring

| Metric | Target | Alert Threshold |
|---|---|---|
| Moving Average MAPE | < 25% | > 35% |
| Exp. Smoothing MAPE | < 20% | > 30% |
| LightGBM RMSE | < 15% of mean | > 25% of mean |
| Copilot grounded rate | > 90% | < 80% |
| Recommendation approval rate | > 60% | < 40% |

### Incident Response

If a model produces demonstrably wrong outputs:
1. Disable automatic recommendations (set `enable_celery=false`)
2. Investigate root cause using `model_decision_logs` table
3. Apply fix and re-validate before re-enabling

---

*This register must be updated whenever a model is retrained, replaced, or deprecated.*
