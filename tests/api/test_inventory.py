"""API tests: inventory endpoints."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_stock_levels_requires_auth(client: TestClient):
    resp = client.get("/api/v1/inventory/stock-levels")
    assert resp.status_code == 401


def test_stock_levels_returns_list(client: TestClient, supply_user, stock_balance):
    _, token = supply_user
    resp = client.get(
        "/api/v1/inventory/stock-levels",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_stock_levels_shows_balance(client: TestClient, supply_user, stock_balance):
    _, token = supply_user
    resp = client.get(
        "/api/v1/inventory/stock-levels",
        headers={"Authorization": f"Bearer {token}"},
    )
    items = resp.json()
    assert any(item["quantity_on_hand"] == 50 for item in items)


def test_movements_returns_paged(client: TestClient, supply_user, location, product):
    _, token = supply_user
    resp = client.get(
        "/api/v1/inventory/movements",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


def test_expiring_returns_list(client: TestClient, supply_user, trust):
    _, token = supply_user
    resp = client.get(
        "/api/v1/inventory/expiring?days_ahead=60",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_below_reorder_filter(client: TestClient, supply_user, stock_balance):
    """Stock of 50 with reorder_point=20 — should NOT appear in below_reorder list."""
    _, token = supply_user
    resp = client.get(
        "/api/v1/inventory/stock-levels?below_reorder_only=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    items = resp.json()
    # qty=50 > reorder_point=20, so item should not be in list
    assert not any(item["quantity_on_hand"] == 50 and item["is_below_reorder"] for item in items)
