"""
NHS Inventory Intelligence Copilot — FastAPI application entry point.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.middleware.request_id import RequestIDMiddleware
from app.api.routes import (
    audit, auth, copilot, forecasting, integrations,
    inventory, org, recommendations,
)
from app.core.config import get_settings
from app.core.errors import global_exception_handler, http_exception_handler
from app.core.logging import configure_logging, log
from app.db.base import Base
from app.db.session import engine

settings = get_settings()

configure_logging("DEBUG" if settings.app_env == "development" else "INFO")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=(
            "NHS Inventory Intelligence Copilot — operational decision-support platform. "
            "All AI recommendations require human review before action. "
            "This system is NOT a clinical decision support tool."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.app_env == "development" else [],
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    # ── Exception handlers ────────────────────────────────────────────────────
    app.add_exception_handler(Exception, global_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)

    # ── Routers ───────────────────────────────────────────────────────────────
    prefix = settings.api_prefix
    app.include_router(auth.router,            prefix=f"{prefix}/auth",            tags=["Auth"])
    app.include_router(org.router,             prefix=f"{prefix}",                 tags=["Org & Master Data"])
    app.include_router(inventory.router,       prefix=f"{prefix}/inventory",       tags=["Inventory"])
    app.include_router(forecasting.router,     prefix=f"{prefix}/forecast",        tags=["Forecasting"])
    app.include_router(recommendations.router, prefix=f"{prefix}/recommendations", tags=["Recommendations"])
    app.include_router(copilot.router,         prefix=f"{prefix}/copilot",         tags=["Copilot"])
    app.include_router(integrations.router,    prefix=f"{prefix}/integrations",    tags=["Integrations"])
    app.include_router(audit.router,           prefix=f"{prefix}/audit",           tags=["Audit & Governance"])

    # ── Startup ───────────────────────────────────────────────────────────────
    @app.on_event("startup")
    def on_startup() -> None:
        import os
        import app.models  # noqa — ensure all models are imported
        if not os.getenv("TESTING"):
            try:
                Base.metadata.create_all(bind=engine)
            except Exception as exc:
                log.warning("startup_create_all_skipped", reason=str(exc))
        log.info("app_started", env=settings.app_env, version="1.0.0")

    # ── Health ────────────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"])
    def health() -> dict:
        return {"status": "ok", "service": settings.app_name, "version": "1.0.0"}

    @app.get("/metrics", tags=["Health"])
    def metrics() -> dict:
        """Placeholder metrics endpoint — wire to Prometheus in production."""
        return {"note": "Wire to prometheus_client or OpenTelemetry in production."}

    return app


app = create_app()
