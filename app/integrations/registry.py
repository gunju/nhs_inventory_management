"""
Adapter registry — maps adapter_name to class.
"""
from __future__ import annotations

from app.integrations.csv_inventory import CSVInventoryAdapter
from app.integrations.mock_epr import MockEPRActivityAdapter

ADAPTER_REGISTRY: dict[str, type] = {
    CSVInventoryAdapter.adapter_name: CSVInventoryAdapter,
    MockEPRActivityAdapter.adapter_name: MockEPRActivityAdapter,
}


def get_adapter(name: str):
    adapter_cls = ADAPTER_REGISTRY.get(name)
    if not adapter_cls:
        raise KeyError(f"Unknown adapter: {name}. Available: {list(ADAPTER_REGISTRY)}")
    return adapter_cls
