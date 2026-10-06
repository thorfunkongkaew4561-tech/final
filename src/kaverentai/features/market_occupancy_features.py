"""เตรียมข้อมูลพยากรณ์ โดยใช้เฉพาะข้อมูลที่มีถึง forecast origin.

ยังไม่ fit preprocessing หรือโมเดล ค่า price target ที่ว่างคงเป็น NaN.
"""
import numpy as np
import pandas as pd

TARGETS = ['occupancy', 'n_searchers', 'n_listings_open', 'median_asking_rent']
LAGS = [1, 4, 12]
WINDOWS = [4, 12]
PROJECT_COLUMNS = ['project_id', 'project_name', 'university', 'total_units',
                   'distance_to_campus_m', 'facility_count']


def past_rolling_mean(values, window):
    """เฉลี่ยย้อนหลัง window สัปดาห์ โดยไม่รวมสัปดาห์ปัจจุบัน.

    เช่น window=4 ที่วันที่ t ใช้ค่าจาก t-1, t-2, t-3, t-4
    ใช้กับ groupby.transform เพื่อคำนวณแยกแต่ละโครงการ
    """
    previous_values = values.shift(1)
    rolling_values = previous_values.rolling(window, min_periods=window)
    return rolling_values.mean()


def has_twelve_past_weeks(values):
    """คืน True เมื่อ 12 สัปดาห์ก่อนวันปัจจุบันมี occupancy ครบ."""
    previous_values = values.shift(1)
    observed_counts = previous_values.rolling(12, min_periods=12).count()
    return observed_counts == 12


def prepare_weekly_panel(weekly, projects):
    """รับ weekly_market และ projects แล้วคืนตารางรายสัปดาห์ที่เชื่อมกัน.

    ตรวจแถวซ้ำ → เติมตำแหน่งสัปดาห์ที่ขาด → เชื่อมข้อมูลโครงการ
    สัปดาห์ที่ขาดมีค่า NaN; ไม่เติมคำตอบจากอนาคต
    """
    weekly = weekly.copy()
    weekly['date'] = pd.to_datetime(weekly['date'], errors='raise')
    if weekly[['project_id', 'date']].isna().any().any():
        raise ValueError('project_id/date ต้องไม่ว่าง')
    if weekly.duplicated(['project_id', 'date']).any():
        raise ValueError('project_id/date ซ้ำ')
    if not weekly['project_id'].isin(projects['project_id']).all():
        raise ValueError('มี project_id ที่ไม่พบใน projects')
    parts = []
    for project_id, frame in weekly.groupby('project_id'):
        dates = pd.date_range(frame['date'].min(), frame['date'].max(), freq='7D')
        if not frame['date'].isin(dates).all():
            raise ValueError('วันที่ไม่อยู่บนตารางสัปดาห์เดียวกัน')
        frame = frame.set_index('date')
        frame = frame.sort_index()
        frame['is_observed_week'] = True
        frame = frame.reindex(dates)
        frame.index.name = 'date'
        frame['project_id'] = project_id
        frame['is_observed_week'] = frame['is_observed_week'].fillna(False).astype(bool)
        parts.append(frame.reset_index())
    panel = pd.concat(parts, ignore_index=True)
    # แต่ละโครงการมีหลายสัปดาห์ จึงจับคู่แบบ many_to_one กับตาราง projects
    panel = panel.merge(projects[PROJECT_COLUMNS], on='project_id', how='left', validate='many_to_one')
    return panel


def build_origin_features(panel):
    """รับตารางรายสัปดาห์ แล้วคืน features พร้อมชื่อคอลัมน์ตัวเลข/หมวดหมู่.

    lag คือค่าที่เลื่อนจากอดีต; rolling คือค่าเฉลี่ยของช่วงก่อนวันปัจจุบัน
    groupby(project_id) ทำให้ประวัติแต่ละโครงการไม่ปะปนกัน
    """
    features = panel.sort_values(['project_id', 'date'])
    features = features.copy()
    numeric_columns = ['total_units', 'distance_to_campus_m', 'facility_count']

    # เติมราคาเฉพาะฝั่ง input จากอดีตของโครงการเดียวกัน target เดิมไม่เปลี่ยน
    features['asking_rent_input'] = features.groupby('project_id')['median_asking_rent'].ffill()
    features['asking_rent_missing_at_origin'] = features['median_asking_rent'].isna().astype(int)
    numeric_columns.append('asking_rent_missing_at_origin')

    for target in TARGETS:
        if target == 'median_asking_rent':
            input_column = 'asking_rent_input'
        else:
            input_column = target
        current_column = f'{target}_current'
        features[current_column] = features[input_column]
        numeric_columns.append(current_column)

        for lag in LAGS:
            name = f'{target}_lag_{lag}'
            features[name] = features.groupby('project_id')[input_column].shift(lag)
            numeric_columns.append(name)

        for window in WINDOWS:
            name = f'{target}_rolling_mean_{window}'
            # shift(1) ทำให้ rolling ใช้เฉพาะสัปดาห์ก่อน origin
            project_values = features.groupby('project_id')[input_column]
            features[name] = project_values.transform(past_rolling_mean, window=window)
            numeric_columns.append(name)

    # history_complete ไม่รวมราคา เพราะค่าว่างราคาไม่ได้หมายถึงสัปดาห์หาย
    observed_occupancy = features['occupancy'].where(features['is_observed_week'])
    occupancy_by_project = observed_occupancy.groupby(features['project_id'])
    features['history_complete_12'] = occupancy_by_project.transform(has_twelve_past_weeks)
    features['observed_weeks_at_origin'] = features.groupby('project_id')['is_observed_week'].cumsum()
    features['project_key'] = features['project_id'].astype(str)
    features['origin_month'] = features['date'].dt.month
    features['origin_year'] = features['date'].dt.year
    numeric_columns += ['observed_weeks_at_origin', 'origin_month', 'origin_year']
    categorical_columns = ['project_key', 'university', 'season']
    return features, numeric_columns, categorical_columns


def build_forecast_pairs(features, panel, horizon_weeks):
    """สร้างหนึ่งแถวต่อโครงการ/วันเริ่มพยากรณ์/horizon.

    เช่น origin=1 มกราคม, horizon=4: target_date=29 มกราคม
    คืน features ณ origin พร้อมคำตอบ y จาก target_date ที่จับคู่ด้วยวันที่จริง
    """
    if not isinstance(horizon_weeks, int) or horizon_weeks <= 0:
        raise ValueError('horizon_weeks ต้องเป็นจำนวนเต็มบวก')
    pairs = features.rename(columns={'date': 'forecast_origin'})
    pairs = pairs.copy()
    pairs['horizon_weeks'] = horizon_weeks
    pairs['target_date'] = pairs['forecast_origin'] + pd.Timedelta(weeks=horizon_weeks)
    future = panel[['project_id', 'date'] + TARGETS]
    future_column_names = {'date': 'target_date'}
    for target in TARGETS:
        future_column_names[target] = f'y_{target}'
    future = future.rename(columns=future_column_names)
    pairs = pairs.merge(future, on=['project_id', 'target_date'], how='left', validate='one_to_one')
    month_angle = 2 * np.pi * (pairs['target_date'].dt.month - 1) / 12
    pairs['target_month_sin'] = np.sin(month_angle)
    pairs['target_month_cos'] = np.cos(month_angle)
    return pairs


def label_time_splits(pairs, train_end='2025-12-31', validation_end='2026-03-31', test_end='2026-06-30'):
    """แบ่งตาม target_date โดยไม่ใช้วัน origin แทนวันที่ของคำตอบ."""
    if not pd.Timestamp(train_end) < pd.Timestamp(validation_end) < pd.Timestamp(test_end):
        raise ValueError('วันแบ่งชุดต้องเรียง Train < Validation < Test')
    result = pairs.copy()
    result['split'] = 'outside_period'
    dates = result['target_date']
    # แบ่งตามวันที่ของคำตอบ ไม่ใช่วันที่เริ่มพยากรณ์
    in_train = dates <= pd.Timestamp(train_end)
    in_validation = (dates > pd.Timestamp(train_end)) & (dates <= pd.Timestamp(validation_end))
    in_test = (dates > pd.Timestamp(validation_end)) & (dates <= pd.Timestamp(test_end))
    result.loc[in_train, 'split'] = 'Train'
    result.loc[in_validation, 'split'] = 'Validation'
    result.loc[in_test, 'split'] = 'Test'
    return result


def training_available_at_origin(dataset, forecast_origin):
    """กัน label leakage: ใช้ Train ที่คำตอบเกิดและทราบแล้ว ณ origin เท่านั้น."""
    origin = pd.Timestamp(forecast_origin)
    target_dates = pd.to_datetime(dataset['target_date'])
    is_train = dataset['split'] == 'Train'
    known_targets = target_dates <= origin
    available_rows = dataset.loc[is_train & known_targets].copy()
    return available_rows
