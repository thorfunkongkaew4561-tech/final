"""ระบบแนะนำราคาค่าเช่าจากโมเดลที่ฝึกไว้."""

from pathlib import Path

import joblib
import pandas as pd

from kaverentai.features.rental_price_features import (
    prepare_rental_price_input,
)
from kaverentai.models.rental_price_uncertainty import (
    load_prediction_error_reference,
)
from kaverentai.paths import MODEL_DIR


MODEL_PATH = MODEL_DIR / "rental_price_model.joblib"
METADATA_PATH = MODEL_DIR / "rental_price" / "rental_price_metadata.json"


def _resolve_metadata_path(model_path: Path, metadata_path) -> Path:
    """ใช้ Metadata หลัก หรือค้นหาไฟล์ข้างโมเดลที่ผู้เรียกกำหนดเอง."""

    if metadata_path is not None:
        return Path(metadata_path)
    if model_path == Path(MODEL_PATH):
        return Path(METADATA_PATH)
    return model_path.with_name("rental_price_metadata.json")


def recommend_rental_price(
    room_data,
    model_path=MODEL_PATH,
    metadata_path=None,
):
    """ทำนายและแนะนำราคาค่าเช่าจากรายละเอียดห้องหนึ่งห้อง."""

    # 1. ตรวจสอบว่ามีไฟล์โมเดลอยู่จริง
    model_path = Path(model_path)
    if not model_path.is_file():
        raise FileNotFoundError(
            f"ไม่พบโมเดลราคาเช่า: {model_path}"
        )

    metadata_path = _resolve_metadata_path(model_path, metadata_path)
    error_reference = load_prediction_error_reference(metadata_path)

    # 2. คัดลอกข้อมูลเพื่อไม่แก้ไข Dictionary ต้นฉบับ
    prepared_data = room_data.copy()

    # 3. ตรวจสอบและแปลงวันที่เริ่มสัญญา
    if "date_start" not in prepared_data:
        raise KeyError("กรุณาระบุ date_start")

    start_date = pd.to_datetime(
        prepared_data["date_start"],
        errors="coerce",
    )
    if pd.isna(start_date):
        raise ValueError("date_start ไม่ใช่วันที่ที่ถูกต้อง")

    # 4. สร้าง Feature ปีและเดือนให้เหมือนตอนฝึกโมเดล
    prepared_data["start_year"] = start_date.year
    prepared_data["start_month"] = start_date.month

    # 5. แปลงข้อมูลหนึ่งห้องให้เป็นตารางหนึ่งแถว
    input_data = pd.DataFrame([prepared_data])
    input_data = prepare_rental_price_input(input_data)

    # 6. โหลด Pipeline ซึ่งรวมทั้งขั้นเตรียมข้อมูลและโมเดลไว้แล้ว
    model = joblib.load(model_path)
    predicted_rent = float(model.predict(input_data)[0])

    # ราคาค่าเช่าไม่ควรติดลบ และปัดเป็นจำนวนเต็มเพื่อให้อ่านง่าย
    recommended_rent = max(0, round(predicted_rent))
    error_margin = max(0, round(float(error_reference["error_margin_baht"])))
    lower_rent = max(0, recommended_rent - error_margin)
    upper_rent = recommended_rent + error_margin
    coverage_target = float(error_reference["reference_coverage_target"])
    test_coverage = float(error_reference["test_coverage"])

    return {
        "predicted_rent": predicted_rent,
        "recommended_rent": recommended_rent,
        "error_margin_baht": error_margin,
        "lower_rent": lower_rent,
        "upper_rent": upper_rent,
        "reference_quantile": error_reference["reference_quantile"],
        "reference_coverage_target": coverage_target,
        "test_coverage": test_coverage,
        "coverage_meets_target": test_coverage >= coverage_target,
    }


def main():
    """ทดลองแนะนำราคาด้วยข้อมูลห้องตัวอย่าง."""

    sample_room = {
        "floor": 7,
        "size_sqm": 25.8,
        "room_type": "studio",
        "view": "city",
        "furnished": True,
        "lease_months": 12,
        "is_renewal": False,
        "project_name": "Kave Condo",
        "university": "ม.กรุงเทพ",
        "distance_to_campus_m": 100,
        "facility_count": 20,
        "date_start": "2026-08-20",
    }

    result = recommend_rental_price(sample_room)

    print("ราคาที่โมเดลทำนาย:", round(result["predicted_rent"], 2), "บาท")
    print("ราคาเช่าที่แนะนำ:", result["recommended_rent"], "บาท/เดือน")
    print("ราคาเช่านี้เป็นค่าประมาณ")
    print("ควรพิจารณาสภาพห้องและตลาดเพิ่มเติม")


if __name__ == "__main__":
    main()
