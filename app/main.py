from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import audit, copilot, documents, forecasting, referral
from app.core.config import get_settings
from app.db.init_db import init_db


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Decision-support only. Synthetic/pseudonymised data only. "
        "Clinician review and approval required for all recommendations."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(copilot.router, prefix="/api/v1/copilot", tags=["copilot"])
app.include_router(forecasting.router, prefix="/api/v1/forecasting", tags=["forecasting"])
app.include_router(referral.router, prefix="/api/v1/referral", tags=["referral"])
app.include_router(audit.router, prefix="/api/v1/audit", tags=["audit"])


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
