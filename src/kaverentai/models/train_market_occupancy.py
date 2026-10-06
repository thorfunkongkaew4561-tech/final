"""รันการทดลองครบ 5 วิธี และบันทึกผลให้ Notebook ส่วนที่ 3 อ่านต่อได้."""
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))

from kaverentai.models.market_occupancy_forecasting import (
    ForecastExperiment, METHODS, compare_complete_cases, score_predictions,
)


def main():
    """อ่านขั้นตอนฝึกตามหมายเลข 1–5; รายละเอียดโมเดลอยู่ใน ForecastExperiment."""
    # 1. โหลดตารางที่ Notebook 02 ส่วนเตรียมข้อมูลสร้างไว้
    experiment = ForecastExperiment(ROOT)

    # 2. ประเมิน Validation ทีละกลุ่มโมเดล
    validation_parts = []
    for methods in [['Naive', 'SeasonalNaive'], ['SARIMA'], ['SARIMAX'], ['RandomForest']]:
        predictions = experiment.run_or_load('Validation', methods)
        validation_parts.append(predictions)
    validation = pd.concat(validation_parts, ignore_index=True)

    # 3. ใช้กรณีเดียวกันครบ 5 วิธี แล้วเลือกผู้ชนะจาก Validation
    common_validation = compare_complete_cases(validation)
    scores = score_predictions(common_validation)
    scores.to_csv(experiment.report_dir / 'validation_metrics.csv', index=False, encoding='utf-8-sig')
    validation.to_csv(experiment.report_dir / 'validation_all_predictions.csv', index=False, encoding='utf-8-sig')
    winners = experiment.lock_selection(scores)
    print('Locked from Validation:', winners[['target', 'horizon_weeks', 'method']].to_string(index=False), flush=True)

    # 4. ประเมิน Test ของรอบแรก หลังบันทึกผู้ชนะแล้ว
    test = experiment.run_or_load('Test', METHODS)
    common_test = compare_complete_cases(test)
    test_scores = score_predictions(common_test)
    project_scores = score_predictions(common_test, per_project=True)
    test_scores.to_csv(experiment.report_dir / 'test_metrics.csv', index=False, encoding='utf-8-sig')
    project_scores.to_csv(experiment.report_dir / 'test_metrics_by_project.csv', index=False, encoding='utf-8-sig')
    experiment.save_selected_models(winners)

    # 5. รายงานกลุ่มประวัติสั้นแยกจากชุดเปรียบเทียบหลัก
    for split in ['Validation', 'Test']:
        short = experiment.run_or_load(split, ['Naive', 'RandomForest'], cohort='short_history')
        if not short.empty:
            successful_predictions = short.dropna(subset=['prediction'])
            short_scores = score_predictions(successful_predictions)
            output_path = experiment.report_dir / f'{split.lower()}_short_history_metrics.csv'
            short_scores.to_csv(output_path, index=False, encoding='utf-8-sig')
    print('Finished:', experiment.report_dir, flush=True)


if __name__ == '__main__':
    main()
