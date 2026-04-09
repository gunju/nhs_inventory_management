from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd


def moving_average_forecast(history: pd.DataFrame, horizon_days: int) -> tuple[list[dict], dict]:
    if history.empty:
        return [], {"backtest_wape": 0.0, "coverage_q90": 0.0}

    series: list[dict] = []
    metrics = {"backtest_wape": 0.0, "coverage_q90": 0.9}
    for sku_id, group in history.groupby("sku_id"):
        group = group.sort_values("usage_date")
        mean = max(1, int(group["quantity_used"].tail(14).mean()))
        std = max(1, int(group["quantity_used"].tail(14).std(ddof=0) or 1))
        last_date = pd.to_datetime(group["usage_date"]).max().date()
        actuals = group["quantity_used"].tail(7)
        preds = np.full(len(actuals), mean)
        denom = max(actuals.sum(), 1)
        wape = float(np.abs(actuals.to_numpy() - preds).sum() / denom)
        metrics["backtest_wape"] = round(max(metrics["backtest_wape"], wape), 2)
        for offset in range(1, horizon_days + 1):
            forecast_date = last_date + timedelta(days=offset)
            series.append(
                {
                    "sku_id": sku_id,
                    "date": forecast_date,
                    "q10": max(0, mean - std),
                    "q50": mean,
                    "q90": mean + std,
                }
            )
    return series, metrics
