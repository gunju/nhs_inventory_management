from datetime import date

from pydantic import BaseModel


class ForecastPoint(BaseModel):
    sku_id: str
    date: date
    q10: int
    q50: int
    q90: int


class ForecastModelMetadata(BaseModel):
    type: str
    features_used: list[str]
    last_train_date: str


class ForecastEvaluation(BaseModel):
    backtest_wape: float
    coverage_q90: float


class ForecastResponse(BaseModel):
    forecast_run_id: str
    site_id: str
    horizon_days: int
    series: list[ForecastPoint]
    model: ForecastModelMetadata
    evaluation_snapshot: ForecastEvaluation
