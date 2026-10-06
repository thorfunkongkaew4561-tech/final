"""เปรียบเทียบราคาโดยใช้ occupancy forecast คงเดิมระหว่างสถานการณ์."""
from math import isfinite
import pandas as pd
from kaverentai.simulation.revenue_calculator import calculate_estimated_revenue

DEFAULT_PRICE_CHANGES = [-10, -5, 0, 5, 10]


def simulate_price_scenarios(forecast_data, base_rent, available_units, price_changes=None, total_discount=0):
    """รับเส้นทางรายสัปดาห์โครงการเดียว ยังไม่ประเมิน occupancy ที่เปลี่ยนตามราคา."""
    data = pd.DataFrame(forecast_data).copy()
    required = ['project_id', 'forecast_origin', 'target_date', 'predicted_occupancy']
    missing = [column for column in required if column not in data]
    if missing:
        raise KeyError(f'ข้อมูล forecast ไม่ครบ: {missing}')
    if data.empty or data[required].isna().any().any():
        raise ValueError('forecast ต้องไม่ว่างและไม่มีค่าสูญหาย')
    for column in ['forecast_origin', 'target_date']:
        data[column] = pd.to_datetime(data[column], errors='raise')
    if data['project_id'].nunique() != 1 or data['forecast_origin'].nunique() != 1:
        raise ValueError('ใช้โครงการเดียวและ forecast origin เดียวต่อการจำลอง')
    data = data.sort_values('target_date')
    origin = data['forecast_origin'].iloc[0]
    expected_dates = pd.date_range(origin + pd.Timedelta(weeks=1), periods=len(data), freq='7D')
    if list(data['target_date']) != list(expected_dates):
        raise ValueError('target_date ต้องต่อเนื่องทุกสัปดาห์ เริ่มหนึ่งสัปดาห์หลัง forecast origin')
    base_rent = float(base_rent)
    if not isfinite(base_rent) or base_rent <= 0:
        raise ValueError('base_rent ต้องเป็นจำนวนบวกที่มีค่าจำกัด')
    changes = [float(value) for value in (DEFAULT_PRICE_CHANGES if price_changes is None else price_changes)]
    if not changes or any(not isfinite(value) or value <= -100 for value in changes):
        raise ValueError('price_changes ต้องไม่ว่าง มีค่าจำกัด และมากกว่า -100%')
    results = []
    for change in changes:
        rent = base_rent * (1 + change / 100)
        revenue = calculate_estimated_revenue(rent, available_units, data['predicted_occupancy'], total_discount)
        results.append({
            'project_id': data['project_id'].iloc[0],
            'forecast_origin': origin,
            'price_change_percent': change,
            'asking_rent': round(rent, 2),
            'rent_difference': round(rent - base_rent, 2),
            **revenue,
            'occupancy_assumption': 'คงเดิมระหว่างสถานการณ์ราคา',
        })
    return pd.DataFrame(results)
