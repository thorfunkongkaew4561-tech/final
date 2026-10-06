"""จูนข้อ 2 ด้วย rolling-origin ภายใน Train แล้วประเมิน Validation.

ไม่อ่านคะแนน Test เพื่อเลือกพารามิเตอร์ และไม่เปิด Test รอบเดิมซ้ำโดยอัตโนมัติ.
Notebook 02 ส่วนที่ 4 เรียกฟังก์ชันเหล่านี้ทีละขั้นตอน.
"""
import hashlib
import json
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
from kaverentai.models.market_occupancy_forecasting import (
    ForecastExperiment, SETTINGS, METHODS, KEYS, SARIMAX,
    bounded_prediction, score_predictions, select_from_validation,
)

# origin จริงบนตารางวันอังคาร ทุก target ของ h<=12 ยังอยู่ใน Train ถึงสิ้นปี 2025
CV_ORIGINS = ['2024-12-31', '2025-04-01', '2025-07-01', '2025-09-02']
TS_PARAMETER_SETS = [
    {'order': [1, 0, 0], 'seasonal_order': [0, 1, 0, 52]},
    {'order': [2, 0, 0], 'seasonal_order': [0, 1, 0, 52]},
    {'order': [1, 0, 1], 'seasonal_order': [0, 1, 0, 52]},
]
RF_PARAMETER_SETS = [
    {'n_estimators': 100, 'max_depth': 8, 'min_samples_leaf': 4, 'max_features': 1.0},
    {'n_estimators': 200, 'max_depth': 12, 'min_samples_leaf': 2, 'max_features': 0.7},
    {'n_estimators': 200, 'max_depth': None, 'min_samples_leaf': 8, 'max_features': 1.0},
]
GRIDS = {'SARIMA': TS_PARAMETER_SETS, 'SARIMAX': TS_PARAMETER_SETS, 'RandomForest': RF_PARAMETER_SETS}


def parameter_key(method, target, horizon):
    """สร้างชื่อของงานหนึ่งงาน เช่น SARIMA|occupancy|4 สำหรับเก็บพารามิเตอร์"""
    return f'{method}|{target}|{horizon}'


def training_cv_cases(dataset, origins=CV_ORIGINS, train_end='2025-12-31'):
    """เลือกกรณีจูนที่อยู่ใน Train และตรงกับ CV origins ที่กำหนด
    
    ต้องมีประวัติพอ และ target_date ไม่เกิน Train end
    แต่ละ fold จะ fit ถึง origin ของตัวเองเมื่อเรียก tune_on_train"""
    dates = pd.to_datetime(origins)
    # & หมายถึงต้องผ่านทุกเงื่อนไขพร้อมกัน จึงจะเก็บแถวนั้น
    keep = (
        dataset['split'].eq('Train')
        & dataset['seasonal_trial_ready']
        & dataset['forecast_origin'].isin(dates)
        & dataset['target_date'].le(pd.Timestamp(train_end))
    )
    return dataset.loc[keep].copy()


def choose_parameters(cv_scores):
    """เลือก candidate ที่ MAE เฉลี่ย TrainCV ต่ำสุดของแต่ละงาน
    
    ตัด candidate ที่คืนคำทำนายไม่ครบออกก่อน เพื่อไม่ให้ชนะจากการข้ามกรณียาก
    จากนั้นเรียง MAE, RMSE, candidate_id แล้วเก็บหนึ่งแถวต่อ method/target/horizon"""
    if not cv_scores['split'].eq('TrainCV').all():
        raise ValueError('จูนด้วย TrainCV เท่านั้น ห้ามใช้ Validation/Test เลือกพารามิเตอร์')
    valid = cv_scores.loc[cv_scores['coverage'].eq(1) & cv_scores['n_folds'].ge(3)]
    winners = (valid.sort_values(['cv_mae_raw', 'cv_rmse_raw', 'candidate_id'])
               .drop_duplicates(['method', 'target', 'horizon_weeks']).reset_index(drop=True))
    expected = cv_scores[['method', 'target', 'horizon_weeks']].drop_duplicates()
    if len(winners) != len(expected):
        raise ValueError('มีงานที่ยังไม่มี candidate ลู่เข้า/คืนผลครบ ต้องตรวจ cv_failures ก่อน')
    return winners


def before_after_comparison(before, after):
    """จับคู่กรณีเดียวกันในสองรอบ แล้วเทียบ MAE ก่อน/หลัง
    
    แถวร่วมต้องมีผลครบทั้ง 5 วิธีในทั้งสองรอบ รวมเป็น 10 คอลัมน์
    คืน 3 ตาราง: คำทำนายร่วม, คะแนนก่อน/หลัง, คะแนนหลังจูน"""
    combined = pd.concat([before.assign(round='initial'), after.assign(round='tuned')], ignore_index=True)
    combined['series_key'] = combined['round'] + '_' + combined['method']
    expected = [f'{phase}_{method}' for phase in ['initial', 'tuned'] for method in METHODS]
    wide = combined.pivot(index=KEYS, columns='series_key', values='prediction').reindex(columns=expected)
    common_keys = wide.loc[wide.notna().all(axis=1)].reset_index()[KEYS]
    common = combined.merge(common_keys, on=KEYS, validate='many_to_one')
    initial_scores = score_predictions(common.loc[common['round'].eq('initial')])
    tuned_scores = score_predictions(common.loc[common['round'].eq('tuned')])
    comparison = initial_scores.merge(tuned_scores, on=['target', 'horizon_weeks', 'method'], suffixes=('_before', '_after'))
    comparison['mae_improvement'] = comparison['MAE_before'] - comparison['MAE_after']
    return common, comparison, tuned_scores


class TunedForecastExperiment(ForecastExperiment):
    """การทดลองจูนที่ต่อยอดจาก ForecastExperiment
    
    ใช้กฎเวลา/การพยากรณ์เดิม แต่เปลี่ยนพารามิเตอร์ตาม target/horizon
    super() เรียกขั้นตอนจาก class เดิม; self.active_parameters คือ candidate ที่กำลังลอง
    self.parameters เก็บชุดที่ชนะ TrainCV แล้ว; ผลอยู่โฟลเดอร์ tuning แยกจากรอบแรก"""

    def __init__(self, root=ROOT, parameters=None):
        """โหลดข้อมูลเหมือนรอบแรก แล้วกำหนดโฟลเดอร์และพารามิเตอร์ของรอบจูน
        
        parameters=None ใช้ตอนทดลอง candidates; ส่ง parameter_map หลังเลือกจาก CV แล้ว"""
        super().__init__(root)
        self.report_dir = self.root / 'reports/market_occupancy/tuning'
        self.model_dir = self.root / 'models/market_occupancy/tuned'
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.parameters = parameters or {}
        self.active_parameters = None
        digest = hashlib.sha256(self.signature.encode())
        digest.update(Path(__file__).read_bytes())
        digest.update(json.dumps({'grids': GRIDS, 'cv_origins': CV_ORIGINS, 'parameters': self.parameters}, sort_keys=True).encode())
        self.signature = digest.hexdigest()

    def parameters_for(self, method, target, horizon):
        """หาพารามิเตอร์ที่เลือกของ method/target/horizon
        
        ขณะ TrainCV ใช้ candidate ปัจจุบัน; หลัง CV ใช้ชุดที่เลือกจาก parameter_map"""
        key = parameter_key(method, target, horizon)
        if key in self.parameters:
            return self.parameters[key]
        if self.active_parameters is not None:
            return self.active_parameters
        raise ValueError(f'ยังไม่เลือกพารามิเตอร์จาก CV สำหรับ {key}')

    def fit_rf(self, target, horizon, cutoff):
        """ฝึก Random Forest หนึ่งงาน (target, horizon) ถึงวัน cutoff
        
        อ่านตามลำดับ: เลือกข้อมูลที่ทราบแล้ว → เตรียมตัวเลข/หมวดหมู่ → fit pipeline
        คืน pipeline ที่ใช้ predict ได้; cache เก็บ pipeline เดิมเมื่อใช้ cutoff เดียวกัน"""
        parameters = self.parameters_for('RandomForest', target, horizon)
        key = ('RandomForest', target, horizon, str(cutoff), json.dumps(parameters, sort_keys=True))
        if key not in self.cache:
            data = self.rf_data[(target, horizon)]
            train = data.loc[data['target_date'].le(cutoff)]
            if train.empty:
                raise ValueError('ไม่มีคำตอบที่ทราบ ณ cutoff สำหรับ RF')
            # 1. ตัวเลขเติม median; หมวดหมู่แปลงเป็น one-hot โดย fit เฉพาะข้อมูลฝึก
            transform = ColumnTransformer([
                ('numeric', SimpleImputer(strategy='median', add_indicator=True), self.numeric),
                ('category', OneHotEncoder(handle_unknown='ignore', sparse_output=False), self.categorical),
            ])
            model = Pipeline([('prepare', transform), ('regressor', RandomForestRegressor(
                **parameters, random_state=42, n_jobs=1,
            ))])
            # 2. ฝึก preprocessing และ Random Forest พร้อมกันผ่าน Pipeline
            model.fit(self.rf_input(train), train['y'])
            self.cache[key] = model
            self.fit_log.append({'method': 'RandomForest', 'target': target, 'horizon_weeks': horizon,
                                 'cutoff': str(cutoff), 'max_label_date': str(train['target_date'].max()),
                                 'train_rows': len(train), 'parameters': json.dumps(parameters), 'converged': True})
        return self.cache[key]

    def fit_time_series(self, method, target, horizon, project_id, cutoff):
        """ฝึก SARIMA หรือ SARIMAX ของโครงการเดียวถึงวัน cutoff
        
        อ่านตามลำดับ: เลือกอนุกรมเวลา → ปรับสเกล → เตรียม exog → fit → ตรวจการลู่เข้า
        คืน dict ของ params, center, scale และตัวแปลงข้อมูล สำหรับพยากรณ์ภายหลัง"""
        parameters = self.parameters_for(method, target, horizon)
        cache_horizon = horizon if method == 'SARIMAX' else 0
        key = (method, target, cache_horizon, project_id, str(cutoff), json.dumps(parameters, sort_keys=True))
        if key in self.cache:
            return self.cache[key]
        train = self.time_series_frame(target, horizon, project_id, cutoff, method)
        if train['y'].notna().sum() < 70:
            raise ValueError('ข้อมูลหลังเลื่อน exog ไม่พอสำหรับ fit')
        # 1. หาค่าเฉลี่ย/ส่วนเบี่ยงเบนจากข้อมูลฝึกเท่านั้น เพื่อปรับ y ให้อยู่บนสเกลใกล้กัน
        center = float(train['y'].mean())
        scale = float(train['y'].std())
        scale = scale if scale > 1e-8 else 1.0
        y = (train['y'] - center) / scale
        imputer = scaler = x = None
        # SARIMAX มีข้อมูลประกอบ (exog); SARIMA ใช้เฉพาะประวัติ y
        if method == 'SARIMAX':
            imputer = SimpleImputer(strategy='median')
            scaler = StandardScaler()
            x = scaler.fit_transform(imputer.fit_transform(train[self.x_columns[target]]))
        specification = dict(
            order=tuple(parameters['order']),
            seasonal_order=tuple(parameters['seasonal_order']),
            simple_differencing=True,
            enforce_stationarity=True,
            enforce_invertibility=True,
            trend='n',
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            model = SARIMAX(y, exog=x, **specification)
            fitted = model.fit(disp=False, maxiter=150)
            if not fitted.mle_retvals.get('converged', False):
                fitted = model.fit(disp=False, method='powell', maxiter=250)
        # 3. converged=True หมายถึงตัวหาค่าพารามิเตอร์ลู่เข้า จึงใช้ผลนี้ต่อได้
        converged = bool(fitted.mle_retvals.get('converged', False))
        self.fit_log.append({'method': method, 'target': target, 'horizon_weeks': cache_horizon,
                             'project_id': project_id, 'cutoff': str(cutoff), 'max_label_date': str(train.index.max()),
                             'train_rows': int(train['y'].notna().sum()), 'parameters': json.dumps(parameters),
                             'converged': converged, 'warnings': len(caught)})
        if not converged or not np.isfinite(fitted.params).all():
            raise ValueError('candidate ไม่ลู่เข้า ไม่ใช้แทนด้วย baseline')
        artifact = {'params': fitted.params, 'center': center, 'scale': scale,
                    'imputer': imputer, 'scaler': scaler, 'specification': specification}
        self.cache[key] = artifact
        return artifact

    def tune_on_train(self):
        """ทดลอง method → candidate → target → horizon → CV origin
        
        1. พยากรณ์แต่ละ candidate ด้วยข้อมูลที่รู้ ณ origin
        2. คำนวณ MAE ของแต่ละ fold แล้วเฉลี่ย folds เท่ากัน
        3. เลือกชุดที่ชนะและบันทึกผล
        คืน cv_scores, selected_parameters และ parameter_map สำหรับขั้น Validation"""
        raw_path = self.report_dir / 'cv_predictions.csv'
        stamp = self.report_dir / 'cv_cache.json'
        if raw_path.exists() and stamp.exists() and json.loads(stamp.read_text())['signature'] == self.signature:
            predictions = pd.read_csv(raw_path, parse_dates=['forecast_origin', 'target_date', 'fit_cutoff'])
        else:
            rows = []
            # ขั้น 1: ทดลองแต่ละ family และแต่ละชุดพารามิเตอร์ที่กำหนด
            for method, candidates in GRIDS.items():
                for candidate_id, parameters in enumerate(candidates):
                    self.active_parameters = parameters
                    print(f'TrainCV {method}, candidate {candidate_id}: {parameters}', file=sys.stderr, flush=True)
                    for target in self.metadata['targets']:
                        for horizon in self.metadata['horizons_weeks']:
                            cases = training_cv_cases(self.rf_data[(target, horizon)], train_end=self.metadata['train_end'])
                            print(f'  {target}, h={horizon}, {len(cases)} cases', file=sys.stderr, flush=True)
                            # ประเมินทีละวันเริ่มพยากรณ์; batch คือทุกโครงการในวันนั้น
                            for origin, batch in cases.groupby('forecast_origin'):
                                if method == 'RandomForest':
                                    forest = self.fit_rf(target, horizon, origin)
                                    forest_predictions = forest.predict(self.rf_input(batch))
                                for index, (_, row) in enumerate(batch.iterrows()):
                                    reason = ''
                                    try:
                                        raw = forest_predictions[index] if method == 'RandomForest' else self.forecast_time_series(
                                            method, target, horizon, int(row['project_id']), origin, origin,
                                        )
                                        prediction = bounded_prediction(raw, target, float(row['total_units']))
                                        if not np.isfinite(prediction):
                                            reason = 'missing anchor or nonfinite forecast'
                                    except (ValueError, IndexError, np.linalg.LinAlgError) as error:
                                        prediction = np.nan
                                        reason = str(error)
                                    rows.append({
                                        'split': 'TrainCV',
                                        'method': method,
                                        'target': target,
                                        'horizon_weeks': horizon,
                                        'candidate_id': candidate_id,
                                        'project_id': int(row['project_id']),
                                        'forecast_origin': origin,
                                        'target_date': row['target_date'],
                                        'fit_cutoff': origin,
                                        'actual': float(row['y']),
                                        'prediction': prediction,
                                        'failure_reason': reason,
                                    })
            predictions = pd.DataFrame(rows)
            predictions.to_csv(raw_path, index=False, encoding='utf-8-sig')
            stamp.write_text(json.dumps({'signature': self.signature}), encoding='utf-8')
            pd.DataFrame(self.fit_log).to_csv(self.report_dir / 'cv_fit_diagnostics.csv', index=False, encoding='utf-8-sig')
        assert predictions['target_date'].le(pd.Timestamp(self.metadata['train_end'])).all()
        assert predictions['fit_cutoff'].le(predictions['forecast_origin']).all()
        # ขั้น 2: สรุปคะแนน CV ของแต่ละ candidate ก่อนเลือกพารามิเตอร์
        scores = []
        for key, frame in predictions.groupby(['method', 'target', 'horizon_weeks', 'candidate_id']):
            valid = frame.dropna(subset=['prediction']).copy()
            fold_mae = valid.assign(error=(valid['actual'] - valid['prediction']).abs()).groupby('forecast_origin')['error'].mean()
            error = valid['actual'] - valid['prediction']
            scores.append({'method': key[0], 'target': key[1], 'horizon_weeks': key[2], 'candidate_id': key[3],
                           'split': 'TrainCV', 'cv_mae_raw': float(fold_mae.mean()),
                           'cv_rmse_raw': float(np.sqrt(np.mean(error ** 2))),
                           'n_predictions': len(valid), 'expected_predictions': len(frame),
                           'n_folds': len(fold_mae), 'coverage': len(valid) / len(frame)})
        scores = pd.DataFrame(scores)
        # ขั้น 3: เลือกพารามิเตอร์ด้วย TrainCV เท่านั้น
        selected = choose_parameters(scores)
        parameters = {
            parameter_key(row.method, row.target, int(row.horizon_weeks)): GRIDS[row.method][int(row.candidate_id)]
            for row in selected.itertuples()
        }
        scores.to_csv(self.report_dir / 'cv_metrics.csv', index=False, encoding='utf-8-sig')
        selected.to_csv(self.report_dir / 'selected_cv_parameters.csv', index=False, encoding='utf-8-sig')
        predictions.loc[predictions['prediction'].isna()].to_csv(self.report_dir / 'cv_failures.csv', index=False, encoding='utf-8-sig')
        (self.report_dir / 'selected_hyperparameters.json').write_text(json.dumps({
            'chosen_from': 'TrainCV only', 'cv_origins': CV_ORIGINS, 'parameters': parameters,
            'seasonal_period_and_differencing_fixed': True, 'test_used_for_tuning': False,
        }, ensure_ascii=False, indent=2), encoding='utf-8')
        return scores, selected, parameters

    def parameter_selection_date(self):
        """คืนวันที่ทราบคำตอบของ CV fold สุดท้ายครบทุก horizon
        
        ใช้กำหนดว่า Validation origin ใดเริ่มใช้พารามิเตอร์ที่เลือกได้"""
        return max(pd.to_datetime(CV_ORIGINS)) + pd.Timedelta(weeks=max(self.metadata['horizons_weeks']))

    def eligible_cases(self, target, horizon, split, cohort='main'):
        """เลือกกรณีเหมือนรอบแรก แล้วตัด Validation origin ที่ยังเลือกพารามิเตอร์ไม่ได้"""
        cases = super().eligible_cases(target, horizon, split, cohort)
        if split == 'Validation':
            cases = cases.loc[cases['forecast_origin'].ge(self.parameter_selection_date())]
        return cases.copy()

    def run_or_load(self, split, methods, cohort='main'):
        # Test ชุดเดิมเคยถูกเปิดแล้ว รอบจูนนี้จึงประเมิน Validation และเก็บไว้รอข้อมูลใหม่
        """โหลด/ประเมิน Validation รอบจูน ไม่ประเมิน Test เดิมซ้ำโดยอัตโนมัติ"""
        if split == 'Test':
            raise ValueError('รอบจูนนี้ไม่เปิด Test ที่เคยเห็นแล้วซ้ำโดยอัตโนมัติ ให้ใช้ข้อมูลอนาคตใหม่สำหรับ final holdout')
        return super().run_or_load(split, methods, cohort)

    def save_selected_models(self, winners):
        """ฝึกผู้ชนะรอบจูนถึง Validation end และบันทึกแยกจากโมเดลรอบแรก
        
        การเลือกโครงการใช้ประวัติที่รู้ถึง cutoff เท่านั้น ไม่ใช้ Test"""
        cutoff = pd.Timestamp(self.metadata['validation_end'])
        artifacts = {}
        for row in winners.itertuples():
            target, horizon, method = row.target, int(row.horizon_weeks), row.method
            if method == 'RandomForest':
                artifacts[(target, horizon)] = {'method': method, 'pipeline': self.fit_rf(target, horizon, cutoff)}
            else:
                history = self.series.loc[self.series['date'].le(cutoff)]
                counts = history.groupby('project_id')[target].count()
                projects = counts[counts.ge(self.metadata['min_seasonal_trial_points'])].index
                models = {}
                if method in ['SARIMA', 'SARIMAX']:
                    for project_id in projects:
                        models[int(project_id)] = self.fit_time_series(method, target, horizon, int(project_id), cutoff)
                artifacts[(target, horizon)] = {'method': method, 'project_models': models}
        bundle = {'status': 'tuned_and_validation_selected_not_new_holdout_tested',
                  'trained_through': str(cutoff.date()), 'artifacts': artifacts,
                  'metadata': self.metadata, 'tuned_parameters': self.parameters,
                  'baseline_history': self.series.loc[self.series['date'].le(cutoff)], 'signature': self.signature}
        joblib.dump(bundle, self.model_dir / 'selected_models.joblib')
        manifest = {'status': bundle['status'], 'trained_through': bundle['trained_through'],
                    'signature': self.signature, 'tuned_parameters': self.parameters,
                    'winners': winners.to_dict('records'), 'test_reopened': False}
        (self.model_dir / 'model_metadata.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        pd.DataFrame(self.fit_log).to_csv(self.report_dir / 'tuned_fit_diagnostics.csv', index=False, encoding='utf-8-sig')


def main():
    """ลำดับรันไฟล์นี้: จูนใน Train → ประเมิน Validation → เทียบรอบแรก → บันทึกผู้ชนะ"""
    tuner = TunedForecastExperiment()
    _, _, parameters = tuner.tune_on_train()
    tuned = TunedForecastExperiment(parameters=parameters)
    validation = tuned.run_or_load('Validation', METHODS)
    before = pd.read_csv(ROOT / 'reports/market_occupancy/evaluation/validation_all_predictions.csv',
                         parse_dates=['forecast_origin', 'target_date'])
    common, comparison, scores = before_after_comparison(before, validation)
    if len(comparison) != 60:
        raise ValueError('ชุดเปรียบเทียบก่อน/หลังยังไม่ครบ 4 targets × 3 horizons × 5 วิธี')
    comparison.to_csv(tuned.report_dir / 'validation_before_after.csv', index=False, encoding='utf-8-sig')
    scores.to_csv(tuned.report_dir / 'tuned_validation_metrics.csv', index=False, encoding='utf-8-sig')
    winners = tuned.lock_selection(scores)
    tuned.save_selected_models(winners)
    print('Tuned winners from Validation:', winners[['target', 'horizon_weeks', 'method', 'MAE']].to_string(index=False))
    print('Finished tuning without reopening Test:', tuned.report_dir)


if __name__ == '__main__':
    main()
