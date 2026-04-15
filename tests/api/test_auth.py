"""API tests: auth endpoints."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_login_invalid_credentials(client: TestClient, trust):
    resp = client.post("/api/v1/auth/login", json={
        "email": "nobody@test.nhs.uk",
        "password": "wrong",
    })
    assert resp.status_code == 401


def test_login_success(client: TestClient, admin_user):
    _, token = admin_user
    # Admin user was created in fixture — login with known password
    resp = client.post("/api/v1/auth/login", json={
        "email": "admin@test.nhs.uk",
        "password": "Test1234!",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_me_requires_auth(client: TestClient):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_me_with_valid_token(client: TestClient, admin_user):
    _, token = admin_user
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "admin@test.nhs.uk"
    assert "platform_admin" in data["roles"]


def test_invalid_token_rejected(client: TestClient):
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalidtoken.xyz.123"},
    )
    assert resp.status_code == 401
