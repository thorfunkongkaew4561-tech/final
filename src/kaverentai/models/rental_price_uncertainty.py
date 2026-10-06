"""เครื่องมือคำนวณและตรวจช่วงความคลาดเคลื่อนของโมเดลราคาเช่า."""

import json
import math
from pathlib import Path

import numpy as np


ERROR_QUANTILE_LEVELS = {
    "p50": 0.50,
    "p75": 0.75,
    "p90": 0.90,
}
REFERENCE_ERROR_QUANTILE = "p75"


def _as_finite_arrays(y_true, y_pred) -> tuple[np.ndarray, np.ndarray]:
    """แปลงค่าจริงและค่าทำนายเป็น Array พร้อมตรวจรูปแบบพื้นฐาน."""

    actual = np.asarray(y_true, dtype=float)
    predictions = np.asarray(y_pred, dtype=float)

    if actual.shape != predictions.shape:
        raise ValueError("y_true และ y_pred ต้องมีขนาดเท่ากัน")
    if actual.size == 0:
        raise ValueError("ต้องมีข้อมูลอย่างน้อย 1 รายการ")
    if not np.isfinite(actual).all() or not np.isfinite(predictions).all():
        raise ValueError("y_true และ y_pred ต้องเป็นตัวเลขที่มีค่าจำกัด")

    return actual, predictions


def calculate_absolute_error_quantiles(
    y_true,
    y_pred,
) -> dict[str, float]:
    """สรุปการกระจายของ Absolute Error สำหรับใช้อ้างอิงช่วงราคา."""

    actual, predictions = _as_finite_arrays(y_true, y_pred)
    absolute_errors = np.abs(actual - predictions)

    return {
        name: float(np.quantile(absolute_errors, level))
        for name, level in ERROR_QUANTILE_LEVELS.items()
    }


def calculate_error_margin_coverage(
    y_true,
    y_pred,
    error_margin: float,
) -> float:
    """คำนวณสัดส่วนรายการที่ Absolute Error ไม่เกิน Margin ที่กำหนด."""

    if error_margin < 0 or not np.isfinite(error_margin):
        raise ValueError("error_margin ต้องเป็นตัวเลขที่ไม่ติดลบ")

    actual, predictions = _as_finite_arrays(y_true, y_pred)
    absolute_errors = np.abs(actual - predictions)

    return float(np.mean(absolute_errors <= error_margin))


def validate_prediction_error_reference(reference: dict) -> dict:
    """ตรวจ Schema และคืนข้อมูล Coverage ที่แปลงเป็นชนิดตัวเลขแล้ว."""

    required_fields = [
        "error_margin_baht",
        "reference_quantile",
        "reference_coverage_target",
        "test_coverage",
    ]
    missing_fields = [
        field for field in required_fields if field not in reference
    ]
    if missing_fields:
        raise ValueError(
            "ข้อมูลช่วงความคลาดเคลื่อนไม่ครบ: "
            f"{missing_fields}"
        )

    normalized = dict(reference)
    normalized["error_margin_baht"] = float(reference["error_margin_baht"])
    normalized["reference_coverage_target"] = float(
        reference["reference_coverage_target"]
    )
    normalized["test_coverage"] = float(reference["test_coverage"])

    if (
        normalized["error_margin_baht"] < 0
        or not math.isfinite(normalized["error_margin_baht"])
    ):
        raise ValueError("error_margin_baht ต้องเป็นตัวเลขที่ไม่ติดลบ")
    if not 0 <= normalized["reference_coverage_target"] <= 1:
        raise ValueError("reference_coverage_target ต้องอยู่ระหว่าง 0 และ 1")
    if not 0 <= normalized["test_coverage"] <= 1:
        raise ValueError("test_coverage ต้องอยู่ระหว่าง 0 และ 1")

    return normalized


def build_prediction_error_reference(
    validation_error_quantiles: dict[str, float],
    test_reference_coverage: float,
) -> dict:
    """สร้างข้อมูล Metadata สำหรับ Margin อ้างอิงจาก Validation."""

    missing_quantiles = [
        name
        for name in ERROR_QUANTILE_LEVELS
        if name not in validation_error_quantiles
    ]
    if missing_quantiles:
        raise ValueError(f"ข้อมูล Error Quantile ไม่ครบ: {missing_quantiles}")

    reference = {
        "source_split": "official_validation",
        "absolute_error_quantiles_baht": validation_error_quantiles,
        "reference_quantile": REFERENCE_ERROR_QUANTILE,
        "reference_coverage_target": ERROR_QUANTILE_LEVELS[
            REFERENCE_ERROR_QUANTILE
        ],
        "error_margin_baht": validation_error_quantiles[
            REFERENCE_ERROR_QUANTILE
        ],
        "test_coverage": test_reference_coverage,
        "description": (
            "ช่วงความคลาดเคลื่อนอ้างอิงจาก Absolute Error "
            "บน Validation และตรวจ Coverage บน Test"
        ),
    }

    return validate_prediction_error_reference(reference)


def load_prediction_error_reference(metadata_path: str | Path) -> dict:
    """โหลด Prediction Error Reference จาก Metadata ของโมเดล."""

    metadata_path = Path(metadata_path)
    if not metadata_path.is_file():
        raise FileNotFoundError(
            f"ไม่พบ Metadata ของโมเดลราคาเช่า: {metadata_path}"
        )

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    reference = metadata.get("prediction_error_reference")
    if not isinstance(reference, dict):
        raise ValueError(
            "Metadata ไม่มี prediction_error_reference "
            "กรุณาฝึกโมเดลราคาเช่าใหม่"
        )

    return validate_prediction_error_reference(reference)
