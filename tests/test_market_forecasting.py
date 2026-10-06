"""ทดสอบกฎประเมินและการใช้ข้อมูลที่รู้ ณ origin ไม่ทดสอบว่าโมเดลต้องชนะ."""
import numpy as np
import pandas as pd
import pytest

from kaverentai.models.market_occupancy_forecasting import (
    METHODS, ForecastExperiment, bounded_prediction, compare_complete_cases,
    score_predictions, select_from_validation,
)


def test_common_cases_excludes_missing_method_from_every_score():
    rows = []
    for week in [1, 2]:
        for method in METHODS:
            rows.append({'target': 'occupancy', 'horizon_weeks': 1, 'project_id': 0,
                         'forecast_origin': f'2025-01-{week:02d}', 'target_date': f'2025-02-{week:02d}',
                         'method': method, 'actual': 0.8, 'prediction': np.nan if week == 2 and method == 'SARIMA' else 0.7})
    common = compare_complete_cases(pd.DataFrame(rows))
    assert len(common) == 5
    assert common['target_date'].nunique() == 1


def test_occupancy_errors_are_reported_in_percentage_points():
    frame = pd.DataFrame({'target': ['occupancy'], 'horizon_weeks': [1], 'method': ['Naive'],
                          'split': ['Validation'], 'actual': [0.8], 'prediction': [0.77]})
    scores = score_predictions(frame)
    assert scores.iloc[0]['MAE'] == pytest.approx(3)
    assert scores.iloc[0]['mae_raw'] == pytest.approx(0.03)


def test_selection_rejects_test_scores():
    frame = pd.DataFrame({'target': ['occupancy'], 'horizon_weeks': [1], 'method': ['Naive'],
                          'split': ['Test'], 'mae_raw': [0.1], 'rmse_raw': [0.1]})
    with pytest.raises(ValueError, match='Validation'):
        select_from_validation(frame)


def test_parameter_fit_cutoff_is_fixed_before_test():
    experiment = ForecastExperiment()
    assert experiment.fit_cutoff('2026-02-01', 'Validation') == pd.Timestamp('2025-12-31')
    assert experiment.fit_cutoff('2025-10-14', 'Validation') == pd.Timestamp('2025-10-14')
    assert experiment.fit_cutoff('2026-06-01', 'Test') == pd.Timestamp('2026-03-31')


def test_test_origin_must_follow_the_validation_selection_date():
    experiment = ForecastExperiment()
    for horizon in [1, 4, 12]:
        cases = experiment.eligible_cases('occupancy', horizon, 'Test')
        assert not cases.empty
        assert cases['forecast_origin'].ge(pd.Timestamp('2026-03-31')).all()
    assert experiment.eligible_cases('occupancy', 12, 'Test')['forecast_origin'].nunique() == 1


def test_sarimax_future_exog_never_uses_unknown_future_values():
    experiment = ForecastExperiment()
    origin = pd.Timestamp('2025-12-30')
    cutoff = origin
    first = experiment.forecast_time_series('SARIMAX', 'occupancy', 4, 0, origin, cutoff)
    # เปลี่ยนทุกค่าตลาดและ y ที่จะทราบหลัง origin แล้วทำนายซ้ำ
    data = experiment.x_data[('occupancy', 4)]
    data.loc[data['forecast_origin'].gt(origin), experiment.x_columns['occupancy']] = 99999
    data.loc[data['target_date'].gt(origin), 'y'] = 99999
    experiment.series.loc[experiment.series['date'].gt(origin), 'occupancy'] = 99999
    second = experiment.forecast_time_series('SARIMAX', 'occupancy', 4, 0, origin, cutoff)
    assert first == pytest.approx(second)
    assert first == pytest.approx(0.92, abs=0.1)


def test_prediction_bounds_are_shared_by_all_methods():
    assert bounded_prediction(1.2, 'occupancy', 100) == 1
    assert bounded_prediction(-2, 'n_searchers', 100) == 0
    assert bounded_prediction(120, 'n_listings_open', 100) == 100
    assert np.isnan(bounded_prediction(np.nan, 'occupancy', 100))
