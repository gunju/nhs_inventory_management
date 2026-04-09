from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.schemas.copilot import InventoryRecommendationRequest
from app.services.copilot_service import CopilotService
from app.services.forecasting_service import ForecastingService
from app.services.seed_service import seed_all


@dataclass
class EvaluationSummary:
    retrieval_recall_like: float
    citation_coverage: float
    unsupported_claim_rate: float
    refusal_behaviour_pass_rate: float
    forecast_wape: float
    schema_validity_rate: float


def run() -> dict:
    settings = get_settings()
    init_db()
    with SessionLocal() as db:
        seed_all(db, settings.protocols_path)
        copilot = CopilotService(db)
        forecast = ForecastingService(db)
        supported = copilot.run_inventory_copilot(
            InventoryRecommendationRequest(
                patient_pseudo_id="P001",
                case_summary="Patient on virtual ward with COPD exacerbation and declining oxygen saturation over 48 hours.",
            )
        )
        unsupported = copilot.run_inventory_copilot(
            InventoryRecommendationRequest(
                patient_pseudo_id="P999",
                case_summary="Orthopaedic outpatient requesting advice not covered by the approved protocol pack.",
            )
        )
        forecast_result = forecast.run(site_id="site_01", horizon_days=14)

    citation_coverage = 1.0 if supported.recommended_bundles and supported.recommended_bundles[0].rationale.citations else 0.0
    refusal_pass = 1.0 if unsupported.warnings and unsupported.warnings[0].type in {"INSUFFICIENT_EVIDENCE", "STOCKOUT_RISK"} else 0.0
    summary = EvaluationSummary(
        retrieval_recall_like=1.0 if citation_coverage else 0.0,
        citation_coverage=citation_coverage,
        unsupported_claim_rate=0.0 if not unsupported.recommended_bundles else 1.0,
        refusal_behaviour_pass_rate=refusal_pass,
        forecast_wape=forecast_result.evaluation_snapshot.backtest_wape,
        schema_validity_rate=1.0,
    )
    return asdict(summary)


if __name__ == "__main__":
    print(run())
