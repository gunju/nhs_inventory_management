from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.documents import Document
from app.models.documents import DocumentChunk
from app.models.inventory import InventoryCatalog, InventoryConsumptionHistory, InventoryLevel, PathwayEvent
from app.models.patient import PatientCase, ReferralNote
from app.rag.ingestion import ingest_file_to_store, reindex_documents
from app.rag.langchain_pipeline import load_vector_store


def seed_all(db: Session, protocols_dir: Path) -> None:
    if db.query(InventoryCatalog).first():
        _ensure_incremental_seed_updates(db)
        documents = db.query(Document).all()
        if documents and (db.query(DocumentChunk).count() == 0 or load_vector_store() is None):
            reindex_documents(db, documents)
        return

    protocols_dir.mkdir(parents=True, exist_ok=True)
    protocol_path = protocols_dir / "virtual_ward_respiratory_protocol.md"
    protocol_path.write_text(
        "# Virtual Ward Respiratory Protocol\n"
        "Approved for use in synthetic NHS-style demo workflow.\n"
        "Patients on the virtual ward respiratory pathway should receive pulse oximetry monitoring and blood pressure monitoring where clinically appropriate.\n"
        "Escalate for specialist advice when oxygen saturation declines over 48 hours despite home monitoring.\n"
        "Discharge-to-home kits should include thermometer support when infection or acute deterioration is a concern.\n",
        encoding="utf-8",
    )
    document = Document(
        title="Virtual Ward Respiratory Protocol",
        source_path=str(protocol_path),
        source_type="md",
        organization="Synthetic NHS Trust",
        pathway="virtual_ward_respiratory",
        version_date=date(2026, 3, 1),
        jurisdiction="UK",
        approved_for_use=True,
    )
    db.add(document)

    db.add_all(
        [
            InventoryCatalog(sku_id="OX001", item_name="Pulse Oximeter", category="monitoring", unit="each", pathway="virtual_ward_respiratory", substitution_group="oximeter", reorder_point=6, lead_time_days=5, default_bundle="Respiratory Monitoring Kit"),
            InventoryCatalog(sku_id="OX009", item_name="Pulse Oximeter Premium", category="monitoring", unit="each", pathway="virtual_ward_respiratory", substitution_group="oximeter", reorder_point=2, lead_time_days=7, default_bundle="Respiratory Monitoring Kit"),
            InventoryCatalog(sku_id="BP002", item_name="Home Blood Pressure Cuff", category="monitoring", unit="each", pathway="virtual_ward_respiratory", substitution_group="bp_cuff", reorder_point=4, lead_time_days=6, default_bundle="Respiratory Monitoring Kit"),
            InventoryCatalog(sku_id="TH003", item_name="Digital Thermometer", category="monitoring", unit="each", pathway="virtual_ward_respiratory", substitution_group="thermometer", reorder_point=5, lead_time_days=4, default_bundle="Respiratory Monitoring Kit"),
            InventoryCatalog(sku_id="WS004", item_name="Connected Weight Scale", category="monitoring", unit="each", pathway="virtual_ward_general", substitution_group="weight_scale", reorder_point=3, lead_time_days=5, default_bundle="Heart Failure Support Kit"),
        ]
    )
    db.add_all(
        [
            InventoryLevel(site_id="site_01", sku_id="OX001", quantity_on_hand=4),
            InventoryLevel(site_id="site_01", sku_id="BP002", quantity_on_hand=8),
            InventoryLevel(site_id="site_01", sku_id="TH003", quantity_on_hand=3),
            InventoryLevel(site_id="site_01", sku_id="OX009", quantity_on_hand=2),
            InventoryLevel(site_id="site_01", sku_id="WS004", quantity_on_hand=5),
        ]
    )
    today = date(2026, 4, 9)
    for day_offset in range(35):
        usage_date = today - timedelta(days=day_offset)
        db.add(InventoryConsumptionHistory(site_id="site_01", sku_id="OX001", usage_date=usage_date, quantity_used=6 + (day_offset % 3), pathway="virtual_ward_respiratory"))
        db.add(InventoryConsumptionHistory(site_id="site_01", sku_id="BP002", usage_date=usage_date, quantity_used=4 + (day_offset % 2), pathway="virtual_ward_respiratory"))
        db.add(InventoryConsumptionHistory(site_id="site_01", sku_id="TH003", usage_date=usage_date, quantity_used=3 + (day_offset % 2), pathway="virtual_ward_respiratory"))
        db.add(InventoryConsumptionHistory(site_id="site_01", sku_id="WS004", usage_date=usage_date, quantity_used=1 + (day_offset % 2), pathway="virtual_ward_general"))
    db.add_all(
        [
            PatientCase(
                patient_pseudo_id="P001",
                case_summary="Patient on virtual ward with COPD exacerbation. Oxygen saturation has declined from 94% to 91% over 48 hours with increased breathlessness.",
                pathway_hint="virtual_ward_respiratory",
                acuity_hint="urgent",
            ),
            PatientCase(
                patient_pseudo_id="P002",
                case_summary="Patient recovering at home after respiratory admission. Stable but requires routine remote observations.",
                pathway_hint="virtual_ward_respiratory",
                acuity_hint="routine",
            ),
        ]
    )
    db.add(
        ReferralNote(
            patient_pseudo_id="P001",
            specialty_requested="respiratory",
            note_text="Virtual ward patient with worsening oxygen saturation trends over 48 hours despite home monitoring. Advice requested on escalation threshold.",
        )
    )
    db.add_all(
        [
            PathwayEvent(patient_pseudo_id="P001", pathway_id="virtual_ward_respiratory", event_date=today - timedelta(days=1), event_type="enrolment", severity_score=0.7),
            PathwayEvent(patient_pseudo_id="P002", pathway_id="virtual_ward_respiratory", event_date=today - timedelta(days=2), event_type="enrolment", severity_score=0.4),
        ]
    )
    db.commit()
    db.refresh(document)
    ingest_file_to_store(db, document)


def _ensure_incremental_seed_updates(db: Session) -> None:
    catalog_defaults = [
        InventoryCatalog(sku_id="WS004", item_name="Connected Weight Scale", category="monitoring", unit="each", pathway="virtual_ward_general", substitution_group="weight_scale", reorder_point=3, lead_time_days=5, default_bundle="Heart Failure Support Kit"),
    ]
    level_defaults = [
        InventoryLevel(site_id="site_01", sku_id="WS004", quantity_on_hand=5),
    ]
    for row in catalog_defaults:
        if db.get(InventoryCatalog, row.sku_id) is None:
            db.add(row)
    for row in level_defaults:
        exists = (
            db.query(InventoryLevel)
            .filter(InventoryLevel.site_id == row.site_id, InventoryLevel.sku_id == row.sku_id)
            .first()
        )
        if exists is None:
            db.add(row)
    db.commit()
