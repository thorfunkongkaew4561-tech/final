"""ตรวจว่าการจูนใช้ Train และเทียบก่อน/หลังบนแถวเดียวกัน."""
import numpy as np
import pandas as pd
import pytest

from kaverentai.models.market_occupancy_forecasting import METHODS
from kaverentai.models.tune_market_occupancy import (
    CV_ORIGINS, TS_PARAMETER_SETS, TunedForecastExperiment,
    before_after_comparison, choose_parameters, training_cv_cases,
)


def test_cv_cases_never_include_holdout_targets():
    frame = pd.DataFrame({
        'split': ['Train', 'Train', 'Validation', 'Test'],
        'seasonal_trial_ready': [True] * 4,
        'forecast_origin': pd.to_datetime([CV_ORIGINS[0]] * 4),
        'target_date': pd.to_datetime(['2025-01-07', '2026-01-06', '2026-01-06', '2026-04-07']),
    })
    selected = training_cv_cases(frame)
    assert len(selected) == 1
    assert selected['target_date'].max() <= pd.Timestamp('2025-12-31')


def cv_candidates():
    return pd.DataFrame({
        'method': ['SARIMA'] * 2, 'target': ['occupancy'] * 2, 'horizon_weeks': [1] * 2,
        'candidate_id': [0, 1], 'split': ['TrainCV'] * 2,
        'cv_mae_raw': [0.001, 0.01], 'cv_rmse_raw': [0.001, 0.01],
        'coverage': [0.5, 1.0], 'n_folds': [4, 4],
    })


def test_failed_candidates_do_not_win_by_omitting_hard_cases():
    assert choose_parameters(cv_candidates()).iloc[0]['candidate_id'] == 1


def test_tuning_rejects_validation_or_test_as_parameter_selection_data():
    for split in ['Validation', 'Test']:
        scores = cv_candidates().assign(split=split)
        with pytest.raises(ValueError, match='TrainCV'):
            choose_parameters(scores)


def test_before_after_comparison_removes_missing_case_from_both_rounds():
    rows = []
    for date in ['2026-01-06', '2026-01-13']:
        for method in METHODS:
            rows.append({'split': 'Validation', 'target': 'occupancy', 'horizon_weeks': 1,
                         'project_id': 0, 'forecast_origin': pd.Timestamp(date) - pd.Timedelta(weeks=1),
                         'target_date': pd.Timestamp(date), 'method': method, 'actual': 0.8, 'prediction': 0.75})
    before = pd.DataFrame(rows)
    after = before.copy()
    after.loc[after['method'].eq('SARIMA') & after['target_date'].eq(pd.Timestamp('2026-01-13')), 'prediction'] = np.nan
    common, comparison, _ = before_after_comparison(before, after)
    assert len(common) == 10
    assert comparison['n_predictions_before'].eq(1).all()
    assert comparison['n_predictions_after'].eq(1).all()


def test_tuned_sarimax_uses_no_future_observations():
    experiment = TunedForecastExperiment(parameters={'SARIMAX|occupancy|4': TS_PARAMETER_SETS[1]})
    origin = pd.Timestamp('2025-12-30')
    first = experiment.forecast_time_series('SARIMAX', 'occupancy', 4, 0, origin, origin)
    data = experiment.x_data[('occupancy', 4)]
    data.loc[data['forecast_origin'].gt(origin), experiment.x_columns['occupancy']] = 99999
    data.loc[data['target_date'].gt(origin), 'y'] = 99999
    second = experiment.forecast_time_series('SARIMAX', 'occupancy', 4, 0, origin, origin)
    assert first == pytest.approx(second)


def test_tuning_entry_does_not_reopen_seen_test_automatically():
    with pytest.raises(ValueError, match='Test'):
        TunedForecastExperiment().run_or_load('Test', METHODS)


def test_validation_origin_follows_parameter_selection_availability():
    experiment = TunedForecastExperiment()
    date = experiment.parameter_selection_date()
    assert date == pd.Timestamp('2025-11-25')
    cases = experiment.eligible_cases('occupancy', 12, 'Validation')
    assert not cases.empty
    assert cases['forecast_origin'].ge(date).all()
    assert cases['target_date'].min() == pd.Timestamp('2026-02-17')
