"""ตรวจความเสี่ยงข้อมูลอนาคตรั่ว และการจับคู่สัปดาห์ข้ามโครงการ."""
import numpy as np
import pandas as pd

from kaverentai.features.market_occupancy_features import (
    TARGETS, prepare_weekly_panel, build_origin_features, build_forecast_pairs,
    label_time_splits, training_available_at_origin,
)


def sample_data():
    dates = pd.date_range('2025-01-07', periods=24, freq='7D')
    rows = []
    for project_id in [0, 1]:
        for week, date in enumerate(dates):
            rows.append({
                'project_id': project_id, 'date': date, 'week': week,
                'season': 'normal', 'occupancy': 0.5 + project_id * 0.2 + week / 100,
                'n_searchers': week + project_id * 100,
                'n_listings_open': 100 - week,
                'median_asking_rent': 10000 + project_id * 2000 + week * 100,
            })
    projects = pd.DataFrame({
        'project_id': [0, 1], 'project_name': ['A', 'B'], 'university': ['U', 'U'],
        'total_units': [100, 200], 'distance_to_campus_m': [50, 100], 'facility_count': [10, 20],
    })
    return pd.DataFrame(rows), projects


def test_future_changes_cannot_change_origin_features():
    weekly, projects = sample_data()
    origin = pd.Timestamp('2025-04-01')
    first, numeric, categorical = build_origin_features(prepare_weekly_panel(weekly, projects))
    changed = weekly.copy()
    changed.loc[changed['date'].gt(origin), TARGETS] = 999999
    second, _, _ = build_origin_features(prepare_weekly_panel(changed, projects))
    pd.testing.assert_frame_equal(
        first.loc[first['date'].le(origin), numeric + categorical].reset_index(drop=True),
        second.loc[second['date'].le(origin), numeric + categorical].reset_index(drop=True),
    )


def test_lags_stay_in_their_project_and_rolling_excludes_current():
    weekly, projects = sample_data()
    features, _, _ = build_origin_features(prepare_weekly_panel(weekly, projects))
    first_b = features.loc[features['project_id'].eq(1)].iloc[0]
    assert pd.isna(first_b['occupancy_lag_1'])
    row = features.loc[features['project_id'].eq(0)].iloc[12]
    assert row['occupancy_lag_12'] == 0.5
    assert np.isclose(row['occupancy_rolling_mean_4'], np.mean([0.58, 0.59, 0.60, 0.61]))
    assert bool(row['history_complete_12'])


def test_missing_week_is_not_skipped_by_lag_or_target():
    weekly, projects = sample_data()
    weekly = weekly.loc[~(weekly['project_id'].eq(0) & weekly['week'].eq(5))]
    panel = prepare_weekly_panel(weekly, projects)
    features, _, _ = build_origin_features(panel)
    row = features.loc[features['project_id'].eq(0) & features['week'].eq(6)].iloc[0]
    assert pd.isna(row['occupancy_lag_1'])
    assert not row['history_complete_12']
    pairs = build_forecast_pairs(features, panel, 1)
    before_gap = pairs.loc[pairs['project_id'].eq(0) & pairs['week'].eq(4)].iloc[0]
    assert pd.isna(before_gap['y_occupancy'])


def test_price_input_uses_only_past_and_target_remains_missing():
    weekly, projects = sample_data()
    weekly.loc[weekly['project_id'].eq(0) & weekly['week'].isin([0, 5]), 'median_asking_rent'] = np.nan
    panel = prepare_weekly_panel(weekly, projects)
    features, _, _ = build_origin_features(panel)
    a = features.loc[features['project_id'].eq(0)]
    assert pd.isna(a.iloc[0]['asking_rent_input'])
    assert a.iloc[5]['asking_rent_input'] == 10400
    assert pd.isna(a.iloc[5]['median_asking_rent'])
    pairs = build_forecast_pairs(features, panel, 1)
    row = pairs.loc[pairs['project_id'].eq(0) & pairs['week'].eq(4)].iloc[0]
    assert pd.isna(row['y_median_asking_rent'])
    assert pd.notna(row['y_occupancy'])


def test_train_split_does_not_allow_labels_after_current_origin():
    weekly, projects = sample_data()
    panel = prepare_weekly_panel(weekly, projects)
    features, _, _ = build_origin_features(panel)
    pairs = build_forecast_pairs(features, panel, 4)
    split = label_time_splits(pairs, '2025-04-15', '2025-05-15', '2025-07-01')
    origin = pd.Timestamp('2025-03-25')
    training = training_available_at_origin(split, origin)
    assert not training.empty
    assert training['target_date'].le(origin).all()
    assert len(training) < split['split'].eq('Train').sum()
    assert split.loc[split['target_date'].gt(pd.Timestamp('2025-04-15')), 'split'].ne('Train').all()


def test_sarimax_shifted_exog_path_never_needs_future_observations():
    weekly, projects = sample_data()
    panel = prepare_weekly_panel(weekly, projects)
    features, _, _ = build_origin_features(panel)
    pairs = build_forecast_pairs(features, panel, 4)
    origin = pd.Timestamp('2025-04-01')
    target_dates = pd.date_range(origin + pd.Timedelta(weeks=1), periods=4, freq='7D')
    path = pairs.loc[pairs['project_id'].eq(0) & pairs['target_date'].isin(target_dates)]
    assert len(path) == 4
    assert path['forecast_origin'].le(origin).all()
    expected = weekly.loc[weekly['project_id'].eq(0)].set_index('date')['n_searchers']
    for row in path.itertuples():
        assert row.n_searchers_current == expected.loc[row.target_date - pd.Timedelta(weeks=4)]
