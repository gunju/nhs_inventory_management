"""Unit tests: prompt templates."""
from __future__ import annotations

import pytest

from app.copilot.prompts import PROMPT_VERSIONS, get_prompt


def test_all_prompt_templates_loadable():
    for name in PROMPT_VERSIONS:
        text = get_prompt(name)
        assert isinstance(text, str)
        assert len(text) > 50


def test_grounded_answer_prompt_has_required_placeholders():
    prompt = get_prompt("grounded_inventory_answer_prompt")
    assert "{context}" in prompt
    assert "{question}" in prompt


def test_recommendation_explainer_prompt_has_fields():
    prompt = get_prompt("recommendation_explainer_prompt")
    for field in ["{rec_type}", "{product_name}", "{location_name}", "{quantity}", "{confidence}"]:
        assert field in prompt


def test_unknown_prompt_raises():
    with pytest.raises(KeyError):
        get_prompt("nonexistent_prompt_xyz")


def test_system_prompt_contains_safety_rules():
    prompt = get_prompt("chat_qa_system_prompt")
    assert "ONLY answer using" in prompt or "ONLY" in prompt
    assert "fabricat" in prompt.lower() or "invent" in prompt.lower() or "NEVER" in prompt


def test_executive_summary_prompt_has_period_placeholders():
    prompt = get_prompt("executive_summary_prompt")
    assert "{period_start}" in prompt
    assert "{period_end}" in prompt
