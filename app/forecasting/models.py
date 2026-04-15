"""
Forecasting models: moving average, exponential smoothing, LightGBM.
Returns standardised ForecastResult objects.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Protocol

import numpy as np
import pandas as pd


@dataclass
class ForecastPoint:
    forecast_date: date
    q10: float
    q50: float
    q90: float
    model_used: str
    confidence: float


@dataclass
class ForecastResult:
    location_id: str
    product_id: str
    points: list[ForecastPoint]
    model_used: str
    wape: float  # weighted absolute percentage error
    confidence: float
    feature_importance: dict[str, float] = field(default_factory=dict)


class ForecastModel(Protocol):
    def fit_predict(
        self,
        history: pd.DataFrame,  # columns: consumption_date, quantity_consumed
        horizon_days: int,
        location_id: str,
        product_id: str,
    ) -> ForecastResult:
        ...


class MovingAverageModel:
    """Simple windowed moving average with empirical confidence bands."""
    name = "moving_average"
    window = 14

    def fit_predict(self, history: pd.DataFrame, horizon_days: int,
                    location_id: str, product_id: str) -> ForecastResult:
        if history.empty:
            return self._zero_result(location_id, product_id, horizon_days)

        series = history.sort_values("consumption_date")["quantity_consumed"].astype(float)
        tail = series.tail(self.window)
        mean = float(tail.mean()) if len(tail) > 0 else 0.0
        std = float(tail.std(ddof=0)) if len(tail) > 1 else max(mean * 0.2, 1.0)

        # backtest wape on last 7 days
        if len(series) >= 7:
            actuals = series.iloc[-7:].values
            preds = np.full(7, mean)
            denom = max(actuals.sum(), 1)
            wape = float(np.abs(actuals - preds).sum() / denom)
        else:
            wape = 0.5

        confidence = max(0.3, min(0.9, 1.0 - wape))
        last_date = pd.to_datetime(series.index[-1] if series.index.dtype != object
                                   else history.sort_values("consumption_date")["consumption_date"].iloc[-1]).date() \
            if not history.empty else date.today()
        last_date = history.sort_values("consumption_date")["consumption_date"].iloc[-1]
        if isinstance(last_date, str):
            last_date = date.fromisoformat(last_date)

        points = []
        for offset in range(1, horizon_days + 1):
            fdate = last_date + timedelta(days=offset)
            points.append(ForecastPoint(
                forecast_date=fdate,
                q10=max(0.0, mean - 1.28 * std),
                q50=max(0.0, mean),
                q90=max(0.0, mean + 1.28 * std),
                model_used=self.name,
                confidence=confidence,
            ))

        return ForecastResult(
            location_id=location_id, product_id=product_id,
            points=points, model_used=self.name, wape=wape, confidence=confidence,
        )

    def _zero_result(self, location_id: str, product_id: str, horizon_days: int) -> ForecastResult:
        today = date.today()
        points = [
            ForecastPoint(today + timedelta(days=i), 0, 0, 0, self.name, 0.1)
            for i in range(1, horizon_days + 1)
        ]
        return ForecastResult(location_id, product_id, points, self.name, 1.0, 0.1)


class ExponentialSmoothingModel:
    """Simple exponential smoothing (Holt) with trend."""
    name = "exp_smoothing"
    alpha = 0.3
    beta = 0.1

    def fit_predict(self, history: pd.DataFrame, horizon_days: int,
                    location_id: str, product_id: str) -> ForecastResult:
        if history.empty or len(history) < 3:
            return MovingAverageModel().fit_predict(history, horizon_days, location_id, product_id)

        series = history.sort_values("consumption_date")["quantity_consumed"].astype(float).values
        # Single exponential smoothing
        level = series[0]
        trend = series[1] - series[0] if len(series) > 1 else 0.0
        for val in series[1:]:
            prev_level = level
            level = self.alpha * val + (1 - self.alpha) * (level + trend)
            trend = self.beta * (level - prev_level) + (1 - self.beta) * trend

        # backtest wape
        if len(series) >= 7:
            actuals = series[-7:]
            preds = np.array([max(0.0, level + trend * i) for i in range(1, 8)])
            denom = max(actuals.sum(), 1)
            wape = float(np.abs(actuals - preds).sum() / denom)
        else:
            wape = 0.4

        confidence = max(0.3, min(0.9, 1.0 - wape))
        residuals = np.abs(series - np.roll(series, 1))
        std_estimate = float(np.std(residuals)) if len(residuals) > 1 else 1.0

        last_date = history.sort_values("consumption_date")["consumption_date"].iloc[-1]
        if isinstance(last_date, str):
            last_date = date.fromisoformat(last_date)

        points = []
        for offset in range(1, horizon_days + 1):
            fdate = last_date + timedelta(days=offset)
            q50 = max(0.0, level + trend * offset)
            points.append(ForecastPoint(
                forecast_date=fdate,
                q10=max(0.0, q50 - 1.28 * std_estimate),
                q50=q50,
                q90=q50 + 1.28 * std_estimate,
                model_used=self.name,
                confidence=confidence,
            ))

        return ForecastResult(
            location_id=location_id, product_id=product_id,
            points=points, model_used=self.name, wape=wape, confidence=confidence,
        )


class LightGBMModel:
    """Gradient-boosted forecast with lag + calendar features."""
    name = "lightgbm"

    def fit_predict(self, history: pd.DataFrame, horizon_days: int,
                    location_id: str, product_id: str) -> ForecastResult:
        try:
            import lightgbm as lgb
        except ImportError:
            return ExponentialSmoothingModel().fit_predict(history, horizon_days, location_id, product_id)

        if len(history) < 30:
            return ExponentialSmoothingModel().fit_predict(history, horizon_days, location_id, product_id)

        df = history.sort_values("consumption_date").copy()
        df["consumption_date"] = pd.to_datetime(df["consumption_date"])
        df = df.set_index("consumption_date").asfreq("D", fill_value=0)
        df = df.rename(columns={"quantity_consumed": "y"})

        # lag features
        for lag in [1, 2, 3, 7, 14]:
            df[f"lag_{lag}"] = df["y"].shift(lag)

        # calendar features
        df["dow"] = df.index.dayofweek
        df["month"] = df.index.month
        df["rolling_7"] = df["y"].shift(1).rolling(7).mean()
        df["rolling_14"] = df["y"].shift(1).rolling(14).mean()

        df = df.dropna()
        if len(df) < 10:
            return ExponentialSmoothingModel().fit_predict(history, horizon_days, location_id, product_id)

        feature_cols = [c for c in df.columns if c != "y"]
        X, y = df[feature_cols].values, df["y"].values

        split = max(1, int(len(X) * 0.8))
        X_train, X_val = X[:split], X[split:]
        y_train, y_val = y[:split], y[split:]

        params = {
            "objective": "regression_l1",
            "num_leaves": 15,
            "learning_rate": 0.05,
            "n_estimators": 200,
            "verbose": -1,
        }
        model = lgb.LGBMRegressor(**params)
        model.fit(X_train, y_train,
                  eval_set=[(X_val, y_val)] if len(X_val) > 0 else None,
                  callbacks=[lgb.early_stopping(20, verbose=False)] if len(X_val) > 0 else None)

        # feature importance
        importance = dict(zip(feature_cols, model.feature_importances_.tolist()))

        # wape
        if len(X_val) > 0:
            preds_val = model.predict(X_val)
            denom = max(y_val.sum(), 1)
            wape = float(np.abs(y_val - preds_val).sum() / denom)
        else:
            wape = 0.35
        confidence = max(0.3, min(0.95, 1.0 - wape))

        # recursive prediction
        last_row = df.iloc[-1].copy()
        points = []
        last_date = df.index[-1].date()

        for offset in range(1, horizon_days + 1):
            fdate = last_date + timedelta(days=offset)
            row_feats = np.array([[
                last_row.get(f"lag_{l}", 0) for l in [1, 2, 3, 7, 14]
            ] + [fdate.weekday(), fdate.month,
                 last_row.get("rolling_7", 0), last_row.get("rolling_14", 0)]
            ])
            q50 = max(0.0, float(model.predict(row_feats)[0]))
            std_est = q50 * 0.25
            points.append(ForecastPoint(
                forecast_date=fdate,
                q10=max(0.0, q50 - 1.28 * std_est),
                q50=q50,
                q90=q50 + 1.28 * std_est,
                model_used=self.name,
                confidence=confidence,
            ))

        return ForecastResult(
            location_id=location_id, product_id=product_id,
            points=points, model_used=self.name, wape=wape,
            confidence=confidence, feature_importance=importance,
        )


def select_best_model(history: pd.DataFrame) -> ForecastModel:
    """Pick model based on data volume."""
    n = len(history)
    if n >= 60:
        return LightGBMModel()
    if n >= 14:
        return ExponentialSmoothingModel()
    return MovingAverageModel()
