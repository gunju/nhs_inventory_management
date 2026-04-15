"""
NHS Inventory Intelligence Copilot — realistic seed data generator.

Creates:
  - 1 trust (NHS North Thames)
  - 2 hospitals, 6 wards/departments
  - 150 products across categories
  - 6 months consumption history with realistic patterns
  - Variable lead times, some critical items
  - Deliberate anomalies: shortages, overstock, expiry risks
  - 4 users (admin, supply_chain_manager, ward_manager, analyst)

Run: python scripts/seed_data.py
"""
from __future__ import annotations

import random
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.org import Department, Hospital, Trust, Ward
from app.models.user import Role, User, UserRoleAssignment
from app.models.product import CatalogItem, Product, ProductCategory, Supplier, UOM
from app.models.inventory import (
    ConsumptionHistory, ExpiryBatchLot, InventoryLocation,
    LeadTimeProfile, ReorderPolicy, StockBalance,
)
from app.models.audit import PromptTemplateVersion
from app.copilot.prompts import PROMPT_VERSIONS, get_prompt

rng = random.Random(2024)
TODAY = date.today()
HISTORY_DAYS = 180


def _dt(d: date) -> datetime:
    return datetime.combine(d, datetime.min.time()).replace(tzinfo=timezone.utc)


def run() -> None:
    print("Creating tables...")
    import app.models  # noqa
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        _seed(db)
        db.commit()
        print("\nSeed complete.")
    except Exception as exc:
        db.rollback()
        print(f"Seed failed: {exc}")
        import traceback; traceback.print_exc()
        raise
    finally:
        db.close()


def _seed(db) -> None:  # noqa: ANN001
    # Trust
    trust = Trust(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        name="NHS North Thames University Trust",
        ods_code="RAN01", region="London", is_active=True,
    )
    db.merge(trust); db.flush()
    print(f"  Trust: {trust.name}")

    # Hospitals
    hospitals = []
    for i, (name, ods) in enumerate([
        ("Royal Northern Hospital", "RAN01H1"),
        ("St Margaret's Community Hospital", "RAN01H2"),
    ]):
        h = Hospital(
            id=uuid.UUID(f"00000000-0000-0000-0000-00000000000{i+2}"),
            trust_id=trust.id, name=name, ods_code=ods, is_active=True,
        )
        db.merge(h); hospitals.append(h)
    db.flush()

    # Departments + Locations
    ward_defs = [
        ("ICU", "THEATRE", hospitals[0]),
        ("Ward A - General Medicine", "GENERAL", hospitals[0]),
        ("Ward B - Surgical", "GENERAL", hospitals[0]),
        ("Theatres", "THEATRE", hospitals[0]),
        ("Main Store", "STORE", hospitals[0]),
        ("Ward C - Elderly Care", "GENERAL", hospitals[1]),
    ]
    locations = []
    for i, (name, loc_type, hospital) in enumerate(ward_defs):
        dept = Department(
            id=uuid.UUID(f"10000000-0000-0000-0000-00000000000{i+1}"),
            trust_id=trust.id, hospital_id=hospital.id,
            name=name, department_type=loc_type,
        )
        db.merge(dept)
        ward = Ward(
            id=uuid.UUID(f"20000000-0000-0000-0000-00000000000{i+1}"),
            trust_id=trust.id, hospital_id=hospital.id, department_id=dept.id,
            name=name, ward_type=loc_type, bed_count=rng.randint(10, 40), is_active=True,
        )
        db.merge(ward)
        loc = InventoryLocation(
            id=uuid.UUID(f"30000000-0000-0000-0000-00000000000{i+1}"),
            trust_id=trust.id, hospital_id=hospital.id,
            ward_id=ward.id, department_id=dept.id,
            name=name, location_type=loc_type, is_active=True,
        )
        db.merge(loc); locations.append(loc)
    db.flush()
    print(f"  Locations: {len(locations)}")

    # UOMs
    uom_each = UOM(id=uuid.UUID("40000000-0000-0000-0000-000000000001"), code="EACH", name="Each")
    db.merge(uom_each); db.flush()

    # Supplier
    supplier = Supplier(
        id=uuid.UUID("50000000-0000-0000-0000-000000000001"),
        trust_id=trust.id, name="MediSupply UK Ltd", supplier_code="MSU001",
        lead_time_days=7, is_preferred=True,
    )
    db.merge(supplier); db.flush()

    # Categories
    cat_defs = [
        ("Cannulas & IV Access", "critical"),
        ("Syringes & Needles", "critical"),
        ("Wound Care", "standard"),
        ("PPE", "standard"),
        ("Theatre Consumables", "critical"),
        ("Ward Consumables", "standard"),
    ]
    categories = []
    for i, (name, criticality) in enumerate(cat_defs):
        cat = ProductCategory(
            id=uuid.UUID(f"60000000-0000-0000-0000-00000000000{i+1}"),
            trust_id=trust.id, name=name, criticality=criticality,
        )
        db.merge(cat); categories.append(cat)
    db.flush()

    # Products (build up to 150)
    templates = [
        ("IV Cannula 18G", "CANN18G", 0, True, 15),
        ("IV Cannula 20G", "CANN20G", 0, True, 20),
        ("IV Cannula 22G", "CANN22G", 0, True, 12),
        ("10ml Syringe", "SYR10", 1, True, 30),
        ("5ml Syringe", "SYR5", 1, True, 25),
        ("20ml Syringe", "SYR20", 1, True, 18),
        ("21G Needle", "NDL21G", 1, True, 25),
        ("Wound Dressing 10x10", "WD1010", 2, False, 12),
        ("Wound Dressing 20x20", "WD2020", 2, False, 8),
        ("Sterile Gauze 5x5", "GAUZ5", 2, False, 15),
        ("Nitrile Gloves S", "GLVS", 3, False, 50),
        ("Nitrile Gloves M", "GLVM", 3, False, 80),
        ("Nitrile Gloves L", "GLVL", 3, False, 60),
        ("Surgical Mask IIR", "MASK2R", 3, False, 100),
        ("N95 Respirator", "N95", 3, True, 20),
        ("Suture Silk 2/0", "SUT2S", 4, True, 6),
        ("Suture Vicryl 3/0", "SUT3V", 4, True, 8),
        ("Surgical Drain Blake", "DRNBLK", 4, True, 3),
        ("Foley Catheter 14FR", "CATH14", 5, False, 4),
        ("Foley Catheter 16FR", "CATH16", 5, False, 6),
        ("Urine Bag 2L", "URIBAG", 5, False, 8),
        ("Oxygen Mask High Conc", "OXYMSK", 5, True, 5),
        ("Blood Glucose Strip", "BGSTR", 5, True, 20),
        ("Alcohol Hand Gel 500ml", "HGEL5", 3, False, 8),
        ("Apron Disposable", "APRON", 3, False, 40),
    ]
    products: list[tuple[uuid.UUID, str, int]] = []
    prod_count = 0
    for base_name, sku_prefix, cat_idx, critical, base_usage in templates:
        for variant in range(6):
            if prod_count >= 150:
                break
            sku = f"{sku_prefix}" if variant == 0 else f"{sku_prefix}V{variant}"
            name = base_name if variant == 0 else f"{base_name} Pack{variant*10}"
            pid = uuid.uuid5(uuid.NAMESPACE_DNS, sku)
            p = Product(
                id=pid, trust_id=trust.id, category_id=categories[cat_idx].id,
                uom_id=uom_each.id, name=name, sku=sku,
                is_critical=critical, is_active=True,
            )
            db.merge(p)
            ci = CatalogItem(
                id=uuid.uuid5(uuid.NAMESPACE_DNS, f"ci_{sku}"),
                product_id=pid, supplier_id=supplier.id, trust_id=trust.id,
                pack_size=rng.choice([1, 10, 50, 100]),
                unit_price=round(rng.uniform(0.10, 25.0), 2),
                is_preferred=True,
            )
            db.merge(ci)
            lt = LeadTimeProfile(
                id=uuid.uuid5(uuid.NAMESPACE_DNS, f"lt_{sku}"),
                trust_id=trust.id, product_id=pid, supplier_id=supplier.id,
                mean_days=float(rng.choice([3, 5, 7, 10, 14])),
                std_days=1.5, min_days=2, max_days=14,
                sample_count=rng.randint(10, 50),
            )
            db.merge(lt)
            products.append((pid, sku, base_usage))
            prod_count += 1
        if prod_count >= 150:
            break
    db.flush()
    print(f"  Products: {prod_count}")

    # Stock balances
    for loc in locations:
        for pid, sku, base_usage in products[:30]:
            anomaly = rng.random()
            if anomaly < 0.05:
                qty = 0
            elif anomaly < 0.10:
                qty = rng.randint(1, 3)
            elif anomaly < 0.15:
                qty = rng.randint(500, 1000)
            else:
                qty = rng.randint(10, 200)
            sb = StockBalance(
                id=uuid.uuid5(uuid.NAMESPACE_DNS, f"sb_{loc.id}_{pid}"),
                trust_id=trust.id, location_id=loc.id, product_id=pid,
                quantity_on_hand=qty, quantity_reserved=0,
                quantity_on_order=rng.randint(0, 50) if anomaly < 0.1 else 0,
                balance_as_of=_dt(TODAY),
            )
            db.merge(sb)
            rp = ReorderPolicy(
                id=uuid.uuid5(uuid.NAMESPACE_DNS, f"rp_{loc.id}_{pid}"),
                trust_id=trust.id, location_id=loc.id, product_id=pid,
                min_stock=5, max_stock=200, reorder_point=20, reorder_quantity=100,
                is_active=True,
            )
            db.merge(rp)
    db.flush()
    print("  Stock balances + policies created")

    # Consumption history (6 months)
    hist_count = 0
    for loc in locations:
        for pid, sku, base_usage in products[:15]:
            for days_back in range(HISTORY_DAYS, 0, -1):
                d = TODAY - timedelta(days=days_back)
                dow_factor = 0.6 if d.weekday() >= 5 else 1.0
                spike = 3.0 if rng.random() < 0.02 else 1.0
                qty = max(0, int(base_usage * dow_factor * spike * rng.gauss(1.0, 0.25)))
                ch = ConsumptionHistory(
                    id=uuid.uuid5(uuid.NAMESPACE_DNS, f"ch_{loc.id}_{pid}_{d.isoformat()}"),
                    trust_id=trust.id, location_id=loc.id, product_id=pid,
                    consumption_date=d, quantity_consumed=qty, data_source="seed",
                )
                db.merge(ch)
                hist_count += 1
    db.flush()
    print(f"  Consumption history: {hist_count:,} records")

    # Expiry batch lots
    for loc in locations[:3]:
        for pid, sku, _ in products[:10]:
            days_offset = rng.choice([-5, 7, 14, 30, 60, 90])
            lot = ExpiryBatchLot(
                id=uuid.uuid5(uuid.NAMESPACE_DNS, f"lot_{loc.id}_{pid}"),
                trust_id=trust.id, location_id=loc.id, product_id=pid,
                batch_number=f"BATCH{rng.randint(1000, 9999)}",
                quantity=rng.randint(5, 50),
                expiry_date=TODAY + timedelta(days=days_offset),
                receipt_date=TODAY - timedelta(days=90),
            )
            db.merge(lot)
    db.flush()
    print("  Expiry lots created")

    # Roles + Users
    role_names = ["platform_admin", "trust_admin", "supply_chain_manager",
                  "ward_manager", "analyst", "read_only_user", "ai_reviewer"]
    roles: dict[str, Role] = {}
    for rn in role_names:
        role = Role(id=uuid.uuid5(uuid.NAMESPACE_DNS, f"role_{rn}"), name=rn)
        db.merge(role); roles[rn] = role
    db.flush()

    users_defs = [
        ("admin@nhs-north-thames.nhs.uk", "Admin1234!", "Admin User", "platform_admin", True),
        ("supply@nhs-north-thames.nhs.uk", "Supply1234!", "Sarah Supply", "supply_chain_manager", False),
        ("ward.a@nhs-north-thames.nhs.uk", "Ward1234!", "William Ward", "ward_manager", False),
        ("analyst@nhs-north-thames.nhs.uk", "Analyst1234!", "Anna Analyst", "analyst", False),
    ]
    for email, pwd, name, role_name, is_super in users_defs:
        uid = uuid.uuid5(uuid.NAMESPACE_DNS, email)
        user = User(
            id=uid, trust_id=trust.id, email=email,
            hashed_password=hash_password(pwd), full_name=name,
            is_active=True, is_superuser=is_super,
        )
        db.merge(user); db.flush()
        ura = UserRoleAssignment(
            id=uuid.uuid5(uuid.NAMESPACE_DNS, f"ura_{uid}_{role_name}"),
            user_id=uid, role_id=roles[role_name].id, trust_id=trust.id,
        )
        db.merge(ura)
    db.flush()
    print("  Users created")

    # Prompt templates
    for pt_name, version in PROMPT_VERSIONS.items():
        pt = PromptTemplateVersion(
            id=uuid.uuid5(uuid.NAMESPACE_DNS, f"pt_{pt_name}_{version}"),
            name=pt_name, version=version,
            template_text=get_prompt(pt_name),
            is_active=True, change_notes="Initial version",
        )
        db.merge(pt)
    db.flush()
    print("  Prompt templates seeded")

    print("\nLogin credentials:")
    for email, pwd, name, role_name, _ in users_defs:
        print(f"  {email:45s}  {pwd}  [{role_name}]")


if __name__ == "__main__":
    run()
