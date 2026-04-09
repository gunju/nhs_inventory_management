from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_jsonl(records: list[dict[str, Any]], target_path: str) -> Path:
    path = Path(target_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")
    return path


EXTRACTION_DATASET_SCHEMA = {
    "instruction": "Extract pathway, monitoring needs, urgency, specialist review likelihood, and care context.",
    "input": "Synthetic referral or case note text.",
    "output": {
        "pathway_id": "virtual_ward_respiratory",
        "likely_monitoring_needs": ["pulse_oximetry", "blood_pressure"],
        "urgency_level": "urgent",
        "specialist_review_likelihood": "moderate",
        "recommended_care_context": "virtual ward",
    },
}


TRIAGE_DATASET_SCHEMA = {
    "instruction": "Classify NHS-style referral routing from the note and protocol context.",
    "input": "Referral note text plus approved protocol snippets.",
    "output": {
        "route": "A_AND_G",
        "reasoning": "Advice and guidance appropriate before routine referral.",
    },
}
