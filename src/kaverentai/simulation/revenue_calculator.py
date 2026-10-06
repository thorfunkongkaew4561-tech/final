"""ประมาณรายได้ระดับโครงการจาก occupancy รายสัปดาห์."""
from math import isfinite

WEEKS_PER_MONTH = 52 / 12


def calculate_estimated_revenue(monthly_rent, available_units, predicted_occupancy, total_discount=0):
    """occupancy แต่ละค่าแทนหนึ่งสัปดาห์ ส่วนลดเป็นยอดรวมทั้งโครงการ."""
    monthly_rent = float(monthly_rent)
    available_units = float(available_units)
    total_discount = float(total_discount)
    occupancy = [float(value) for value in predicted_occupancy]
    if not isfinite(monthly_rent) or monthly_rent <= 0:
        raise ValueError('monthly_rent ต้องเป็นจำนวนบวกที่มีค่าจำกัด')
    if not isfinite(available_units) or available_units <= 0 or not available_units.is_integer():
        raise ValueError('available_units ต้องเป็นจำนวนเต็มบวก')
    if not occupancy or any(not isfinite(value) or not 0 <= value <= 1 for value in occupancy):
        raise ValueError('predicted_occupancy ต้องมีค่ารายสัปดาห์ในช่วง 0–1')
    if not isfinite(total_discount) or total_discount < 0:
        raise ValueError('total_discount ต้องไม่ติดลบและมีค่าจำกัด')
    full = monthly_rent * available_units * len(occupancy) / WEEKS_PER_MONTH
    occupied = monthly_rent * available_units * sum(occupancy) / WEEKS_PER_MONTH
    if total_discount > occupied:
        raise ValueError('ส่วนลดต้องไม่เกินรายได้ก่อนหักส่วนลด')
    return {
        'monthly_rent': round(monthly_rent, 2),
        'available_units': int(available_units),
        'forecast_weeks': len(occupancy),
        'mean_predicted_occupancy': sum(occupancy) / len(occupancy),
        'full_capacity_revenue': round(full, 2),
        'estimated_vacancy_loss': round(full - occupied, 2),
        'revenue_before_discount': round(occupied, 2),
        'total_discount': round(total_discount, 2),
        'estimated_revenue': round(occupied - total_discount, 2),
    }
