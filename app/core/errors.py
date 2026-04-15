"""
Consistent error envelope for all API responses.
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    field: str | None = None


class ErrorEnvelope(BaseModel):
    request_id: str | None = None
    error: ErrorDetail


def http_error(status_code: int, code: str, message: str, field: str | None = None) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message, "field": field},
    )


def not_found(resource: str) -> HTTPException:
    return http_error(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"{resource} not found")


def forbidden(message: str = "Insufficient permissions") -> HTTPException:
    return http_error(status.HTTP_403_FORBIDDEN, "FORBIDDEN", message)


def unprocessable(message: str, field: str | None = None) -> HTTPException:
    return http_error(status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", message, field)


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    from app.api.middleware.request_id import get_request_id

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "request_id": get_request_id(),
            "error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"},
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    from app.api.middleware.request_id import get_request_id

    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "HTTP_ERROR", "message": str(exc.detail)}
    return JSONResponse(
        status_code=exc.status_code,
        content={"request_id": get_request_id(), "error": detail},
    )
