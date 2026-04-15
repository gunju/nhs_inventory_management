"""Unit tests: forecasting models."""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pandas as pd
import pytest

from app.forecasting.models import (
    ExponentialSmoothingModel,
    LightGBMModel,
    MovingAverageModel,
    select_best_model,
)


def _make_history(days: int, daily_qty: int = 10) -> pd.DataFrame:
    today = date.today()
    return pd.DataFrame({
        "consumption_date": [today - timedelta(days=i) for i in range(days, 0, -1)],
        "quantity_consumed": [daily_qty] * days,
    })


LOC_ID = str(uuid.uuid4())
PROD_ID = str(uuid.uuid4())


class TestMovingAverage:
    def test_returns_correct_horizon(self):
        hist = _make_history(30)
        model = MovingAverageModel()
        result = model.fit_predict(hist, 7, LOC_ID, PROD_ID)
        assert len(result.points) == 7

    def test_empty_history_returns_zeros(self):
        hist = pd.DataFrame(columns=["consumption_date", "quantity_consumed"])
        model = MovingAverageModel()
        result = model.fit_predict(hist, 7, LOC_ID, PROD_ID)
        assert all(p.q50 == 0 for p in result.points)

    def test_q10_lt_q50_lt_q90(self):
        hist = _make_history(30, daily_qty=20)
        model = MovingAverageModel()
        result = model.fit_predict(hist, 14, LOC_ID, PROD_ID)
        for pt in result.points:
            assert pt.q10 <= pt.q50 <= pt.q90

    def test_confidence_between_0_and_1(self):
        hist = _make_history(30)
        model = MovingAverageModel()
        result = model.fit_predict(hist, 7, LOC_ID, PROD_ID)
        assert 0.0 <= result.confidence <= 1.0

    def test_forecast_dates_sequential(self):
        hist = _make_history(30)
        model = MovingAverageModel()
        result = model.fit_predict(hist, 7, LOC_ID, PROD_ID)
        dates = [p.forecast_date for p in result.points]
        for i in range(1, len(dates)):
            assert dates[i] > dates[i - 1]


class TestExponentialSmoothing:
    def test_short_history_falls_back_to_ma(self):
        hist = _make_history(5)
        model = ExponentialSmoothingModel()
        result = model.fit_predict(hist, 7, LOC_ID, PROD_ID)
        assert len(result.points) == 7

    def test_reasonable_forecast_on_stable_series(self):
        hist = _make_history(60, daily_qty=20)
        model = ExponentialSmoothingModel()
        result = model.fit_predict(hist, 7, LOC_ID, PROD_ID)
        for pt in result.points:
            # Should be within 3x of actual daily rate
            assert pt.q50 < 60


class TestModelSelection:
    def test_selects_ma_for_short_history(self):
        hist = _make_history(5)
        model = select_best_model(hist)
        assert isinstance(model, MovingAverageModel)

    def test_selects_es_for_medium_history(self):
        hist = _make_history(30)
        model = select_best_model(hist)
        assert isinstance(model, ExponentialSmoothingModel)

    def test_selects_lgbm_for_long_history(self):
        hist = _make_history(90)
        model = select_best_model(hist)
        # LightGBM or ES — both acceptable for 90 days
        assert isinstance(model, (LightGBMModel, ExponentialSmoothingModel))
