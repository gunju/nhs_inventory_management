"""API tests: copilot chat endpoint."""
from __future__ import annotations

import uuid
import pytest
from fastapi.testclient import TestClient

from tests.conftest import TRUST_ID


def test_chat_requires_auth(client: TestClient):
    resp = client.post("/api/v1/copilot/chat", json={"message": "hello"})
    assert resp.status_code == 401


def test_chat_returns_structured_response(client: TestClient, admin_user, trust):
    _, token = admin_user
    resp = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Show stock levels for cannulas", "trust_id": str(TRUST_ID)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "session_id" in data
    assert "evidence" in data
    assert isinstance(data["evidence"], list)


def test_chat_creates_session(client: TestClient, admin_user, trust):
    _, token = admin_user
    resp = client.post(
        "/api/v1/copilot/chat",
        json={"message": "What are the top shortage risks?", "trust_id": str(TRUST_ID)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]
    assert uuid.UUID(session_id)


def test_chat_continues_session(client: TestClient, admin_user, trust):
    _, token = admin_user
    headers = {"Authorization": f"Bearer {token}"}
    # First turn
    resp1 = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Show expiry risks", "trust_id": str(TRUST_ID)},
        headers=headers,
    )
    session_id = resp1.json()["session_id"]
    # Second turn in same session
    resp2 = client.post(
        "/api/v1/copilot/chat",
        json={"message": "What actions should I take?", "session_id": session_id, "trust_id": str(TRUST_ID)},
        headers=headers,
    )
    assert resp2.status_code == 200
    assert resp2.json()["session_id"] == session_id


def test_chat_message_too_long(client: TestClient, admin_user, trust):
    _, token = admin_user
    resp = client.post(
        "/api/v1/copilot/chat",
        json={"message": "x" * 4001, "trust_id": str(TRUST_ID)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422  # validation error
