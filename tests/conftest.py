"""
Test fixtures: in-memory SQLite engine, seeded test data, FastAPI test client.
"""
from __future__ import annotations

import os
os.environ.setdefault("TESTING", "1")

import uuid
from datetime import date, datetime, timezone
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.org import Department, Hospital, Trust, Ward
from app.models.user import Role, User, UserRoleAssignment
from app.models.product import CatalogItem, Product, ProductCategory, Supplier, UOM
from app.models.inventory import (
    ConsumptionHistory, InventoryLocation, ReorderPolicy, StockBalance,
)

TEST_DB_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

TestSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)

TRUST_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
HOSPITAL_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
LOC_ID = uuid.UUID("30000000-0000-0000-0000-000000000001")
PRODUCT_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
ADMIN_USER_ID = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000001")
SUPPLY_USER_ID = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    import app.models  # noqa
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db() -> Generator[Session, None, None]:
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)
    # Use nested transaction (savepoint) so service-level commits don't escape
    nested = connection.begin_nested()

    from sqlalchemy import event as sa_event

    @sa_event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def trust(db: Session) -> Trust:
    t = Trust(id=TRUST_ID, name="Test Trust", ods_code="TEST01", is_active=True)
    db.merge(t); db.flush()
    return t


@pytest.fixture
def hospital(db: Session, trust: Trust) -> Hospital:
    h = Hospital(id=HOSPITAL_ID, trust_id=TRUST_ID, name="Test Hospital", is_active=True)
    db.merge(h); db.flush()
    return h


@pytest.fixture
def location(db: Session, hospital: Hospital) -> InventoryLocation:
    dept = Department(
        id=uuid.UUID("10000000-0000-0000-0000-000000000001"),
        trust_id=TRUST_ID, hospital_id=HOSPITAL_ID, name="Test Ward",
    )
    db.merge(dept)
    ward = Ward(
        id=uuid.UUID("20000000-0000-0000-0000-000000000001"),
        trust_id=TRUST_ID, hospital_id=HOSPITAL_ID, department_id=dept.id,
        name="Test Ward", ward_type="GENERAL", is_active=True,
    )
    db.merge(ward)
    loc = InventoryLocation(
        id=LOC_ID, trust_id=TRUST_ID, hospital_id=HOSPITAL_ID,
        ward_id=ward.id, department_id=dept.id,
        name="Test Ward", location_type="GENERAL", is_active=True,
    )
    db.merge(loc); db.flush()
    return loc


@pytest.fixture
def product(db: Session, trust: Trust) -> Product:
    cat = ProductCategory(
        id=uuid.UUID("60000000-0000-0000-0000-000000000001"),
        trust_id=TRUST_ID, name="Test Cat", criticality="standard",
    )
    db.merge(cat)
    uom = UOM(id=uuid.UUID("40000000-0000-0000-0000-000000000001"), code="EACH", name="Each")
    db.merge(uom)
    p = Product(
        id=PRODUCT_ID, trust_id=TRUST_ID, category_id=cat.id, uom_id=uom.id,
        name="Test Cannula 18G", sku="TEST-CANN18G", is_critical=True, is_active=True,
    )
    db.merge(p); db.flush()
    return p


@pytest.fixture
def stock_balance(db: Session, location: InventoryLocation, product: Product) -> StockBalance:
    sb = StockBalance(
        id=uuid.UUID("cccccccc-0000-0000-0000-000000000001"),
        trust_id=TRUST_ID, location_id=LOC_ID, product_id=PRODUCT_ID,
        quantity_on_hand=50, quantity_reserved=0, quantity_on_order=0,
        balance_as_of=datetime.now(tz=timezone.utc),
    )
    db.merge(sb)
    rp = ReorderPolicy(
        id=uuid.UUID("dddddddd-0000-0000-0000-000000000001"),
        trust_id=TRUST_ID, location_id=LOC_ID, product_id=PRODUCT_ID,
        min_stock=5, max_stock=200, reorder_point=20, reorder_quantity=100, is_active=True,
    )
    db.merge(rp); db.flush()
    return sb


@pytest.fixture
def consumption_history(db: Session, location: InventoryLocation, product: Product) -> list[ConsumptionHistory]:
    from datetime import timedelta
    items = []
    for i in range(30):
        d = date.today() - timedelta(days=i + 1)
        ch = ConsumptionHistory(
            id=uuid.uuid5(uuid.NAMESPACE_DNS, f"ch_{d}"),
            trust_id=TRUST_ID, location_id=LOC_ID, product_id=PRODUCT_ID,
            consumption_date=d, quantity_consumed=15 + (i % 5), data_source="test",
        )
        db.add(ch); items.append(ch)
    db.flush()
    return items


def _make_user(db: Session, user_id: uuid.UUID, email: str, role_name: str,
               is_super: bool = False) -> tuple[User, str]:
    role = Role(id=uuid.uuid5(uuid.NAMESPACE_DNS, f"role_{role_name}"), name=role_name)
    db.merge(role)
    user = User(
        id=user_id, trust_id=TRUST_ID, email=email,
        hashed_password=hash_password("Test1234!"),
        full_name="Test User", is_active=True, is_superuser=is_super,
    )
    db.merge(user); db.flush()
    ura = UserRoleAssignment(
        id=uuid.uuid5(uuid.NAMESPACE_DNS, f"ura_{user_id}_{role_name}"),
        user_id=user_id, role_id=role.id, trust_id=TRUST_ID,
    )
    db.merge(ura); db.flush()
    token = create_access_token(str(user_id), {"trust_id": str(TRUST_ID), "roles": [role_name]})
    return user, token


@pytest.fixture
def admin_user(db: Session, trust: Trust) -> tuple[User, str]:
    return _make_user(db, ADMIN_USER_ID, "admin@test.nhs.uk", "platform_admin", is_super=True)


@pytest.fixture
def supply_user(db: Session, trust: Trust) -> tuple[User, str]:
    return _make_user(db, SUPPLY_USER_ID, "supply@test.nhs.uk", "supply_chain_manager")
