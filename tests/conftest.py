from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture()
def db_session(tmp_path: Path) -> Session:
    os.environ["VECTOR_STORE_DIR"] = str(tmp_path / "vectorstore")
    os.environ["PROTOCOLS_DIR"] = str(tmp_path / "protocols")
    from app.core.config import get_settings
    from app.db.base import Base
    from app.services.seed_service import seed_all

    get_settings.cache_clear()
    engine = create_engine("sqlite:///:memory:", future=True)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)
    with TestingSession() as session:
        seed_all(session, tmp_path / "protocols")
        yield session
