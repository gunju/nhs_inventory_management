from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.services.seed_service import seed_all


def main() -> None:
    settings = get_settings()
    init_db()
    with SessionLocal() as db:
        seed_all(db, settings.protocols_path)
    print("Seed complete")


if __name__ == "__main__":
    main()
