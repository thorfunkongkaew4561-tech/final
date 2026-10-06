import pandas as pd
import pytest

from kaverentai.simulation.revenue_calculator import calculate_estimated_revenue
from kaverentai.simulation.what_if import simulate_price_scenarios


def forecast():
    return pd.DataFrame({
        'project_id': [0, 0],
        'forecast_origin': ['2026-01-01'] * 2,
        'target_date': ['2026-01-08', '2026-01-15'],
        'predicted_occupancy': [0.5, 1.0],
    })


def test_revenue_uses_occupied_unit_weeks():
    result = calculate_estimated_revenue(13000, 10, [0.5, 1], 1000)
    assert result['revenue_before_discount'] == pytest.approx(45000)
    assert result['estimated_revenue'] == pytest.approx(44000)
    assert result['estimated_vacancy_loss'] == pytest.approx(15000)


def test_price_scenarios_keep_occupancy_fixed():
    result = simulate_price_scenarios(forecast(), 13000, 10, [-10, 0, 10])
    assert result['estimated_revenue'].tolist() == pytest.approx([40500, 45000, 49500])
    assert result['mean_predicted_occupancy'].tolist() == [0.75] * 3


@pytest.mark.parametrize('values', [[-0.1], [1.1], [float('nan')], []])
def test_invalid_occupancy_is_rejected(values):
    with pytest.raises(ValueError):
        calculate_estimated_revenue(10000, 10, values)


def test_sparse_horizons_cannot_be_summed_as_weekly_revenue():
    data = forecast()
    data.loc[1, 'target_date'] = '2026-01-29'
    with pytest.raises(ValueError, match='ต่อเนื่อง'):
        simulate_price_scenarios(data, 10000, 10)


def test_multiple_projects_cannot_be_combined():
    data = forecast()
    data.loc[1, 'project_id'] = 1
    with pytest.raises(ValueError, match='โครงการเดียว'):
        simulate_price_scenarios(data, 10000, 10)
