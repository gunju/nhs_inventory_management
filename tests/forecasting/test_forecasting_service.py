from app.services.forecasting_service import ForecastingService


def test_forecast_output_schema(db_session):
    service = ForecastingService(db_session)
    result = service.run("site_01", 7)

    assert result.site_id == "site_01"
    assert result.horizon_days == 7
    assert result.series
    assert {"q10", "q50", "q90"} <= result.series[0].model_dump().keys()
