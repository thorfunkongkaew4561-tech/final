"""ฝึกและประเมิน 5 วิธี โดยกำหนดข้อมูลที่รู้จริง ณ แต่ละ origin.

พารามิเตอร์รอบแรกคงที่ ไม่จูนจาก Test. อ่านขั้นตอนการเรียกใช้ใน Notebook 02 ส่วนที่ 3.
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

# รองรับแพ็กเกจที่ติดตั้งเฉพาะโปรเจกต์นี้ โดยไม่เปลี่ยน environment ส่วนกลาง
ROOT = Path(__file__).resolve().parents[3]
if (ROOT / '.runtime-packages').is_dir():
    sys.path.insert(0, str(ROOT / '.runtime-packages'))
from statsmodels.tsa.statespace.sarimax import SARIMAX

METHODS = ['Naive', 'SeasonalNaive', 'SARIMA', 'SARIMAX', 'RandomForest']
KEYS = ['target', 'horizon_weeks', 'project_id', 'forecast_origin', 'target_date']
SETTINGS = {
    'order': [1, 0, 0], 'seasonal_order': [0, 1, 0, 52],
    'simple_differencing': True, 'maxiter': 150,
    'rf': {'n_estimators': 100, 'max_depth': 8, 'min_samples_leaf': 4,
           'random_state': 42, 'n_jobs': 1},
    'selection': 'Validation MAE on identical complete cases across all 5 methods',
    'coefficient_policy': 'Validation fit labels through min(origin, Train end); Test through min(origin, Validation end). Known observations after fit cutoff update state/inputs only, not coefficients.',
}


def bounded_prediction(value, target, total_units):
    """จำกัดคำทำนายตามความหมายของ target
    
    occupancy อยู่ระหว่าง 0–1, จำนวนประกาศไม่เกินห้องทั้งหมด
    จำนวนผู้ค้นหาและราคาไม่ติดลบ; ถ้าคำนวณไม่ได้คืน NaN"""
    if not np.isfinite(value):
        return np.nan
    upper = (
        1 if target == 'occupancy'
        else total_units if target == 'n_listings_open'
        else np.inf
    )
    return float(np.clip(value, 0, upper))


def compare_complete_cases(predictions):
    """เก็บเฉพาะกรณีที่ทั้ง 5 วิธีมีคำทำนาย เพื่อเปรียบเทียบอย่างเท่าเทียม
    
    รับตารางคำทำนายหลายโมเดล คืนตารางรูปแบบเดิมที่เหลือแต่กรณีครบ
    KEYS ระบุว่าเป็นโครงการ/วันเริ่มพยากรณ์/target/horizon เดียวกัน"""
    wide = predictions.pivot(index=KEYS, columns='method', values='prediction')
    common = wide.reindex(columns=METHODS).notna().all(axis=1)
    common_keys = common[common].reset_index()[KEYS]
    return predictions.merge(common_keys, on=KEYS, how='inner', validate='many_to_one')


def score_predictions(predictions, per_project=False):
    """คำนวณ MAE และ RMSE แยก target, horizon และโมเดล
    
    MAE = ค่าเฉลี่ย abs(ค่าจริง − คำทำนาย)
    RMSE = รากที่สองของค่าเฉลี่ย (ค่าจริง − คำทำนาย)^2
    per_project=True เพิ่มการแยกโครงการ; occupancy คูณ 100 เป็นจุดเปอร์เซ็นต์"""
    if 'split' in predictions and predictions['split'].nunique() > 1:
        raise ValueError('ห้ามรวม Validation กับ Test ในคะแนนเดียวกัน')
    rows = []
    groups = ['target', 'horizon_weeks', 'method']
    if per_project:
        groups.append('project_id')
    for key, frame in predictions.groupby(groups):
        error = frame['actual'] - frame['prediction']
        mae = float(error.abs().mean())
        rmse = float(np.sqrt(np.mean(error ** 2)))
        target = key[0]
        factor = 100 if target == 'occupancy' else 1
        # groups/key เก็บชื่อกลุ่มและค่าของกลุ่ม เช่น target=occupancy, horizon=4
        rows.append({
            **dict(zip(groups, key)),
            'split': frame['split'].iloc[0] if 'split' in frame else '',
            'n_predictions': len(frame),
            'mae_raw': mae,
            'rmse_raw': rmse,
            'MAE': mae * factor,
            'RMSE': rmse * factor,
            'unit': (
                'percentage points' if target == 'occupancy'
                else 'baht/month' if target == 'median_asking_rent'
                else 'count'
            ),
        })
    return pd.DataFrame(rows)


def select_from_validation(scores):
    """เลือก MAE ต่ำสุดของแต่ละ target/horizon จาก Validation
    
    หาก MAE เท่ากัน ใช้ RMSE แล้วชื่อโมเดลตัดสินตามลำดับ
    รับตารางคะแนน คืนตารางผู้ชนะ; ไม่รับคะแนน Test"""
    if 'split' not in scores or not scores['split'].eq('Validation').all():
        raise ValueError('เลือกโมเดลจาก Validation เท่านั้น')
    return (scores.sort_values(['mae_raw', 'rmse_raw', 'method'])
            .drop_duplicates(['target', 'horizon_weeks']).reset_index(drop=True))


class ForecastExperiment:
    """ตัวช่วยเก็บข้อมูลและเรียกขั้นตอนทดลองใน Notebook 02 ส่วนที่ 3
    
    class คือการรวมข้อมูลและฟังก์ชันที่ใช้ข้อมูลเดียวกันไว้ด้วยกัน
    self หมายถึงการทดลองที่สร้างด้วย experiment = ForecastExperiment()
    self.series: อนุกรมเวลารายโครงการ; self.rf_data: ตาราง features/คำตอบ
    self.cache: โมเดลที่ fit แล้ว; self.fit_log: ประวัติการฝึก
    ลำดับใช้งาน: run_or_load → score_predictions → lock_selection → save_selected_models"""

    def __init__(self, root=ROOT):
        """เตรียมโฟลเดอร์ โหลดข้อมูล และสร้างรหัสตรวจสอบผลที่บันทึกไว้
        
        ถูกเรียกอัตโนมัติเมื่อสร้าง ForecastExperiment(root)
        root คือโฟลเดอร์โปรเจกต์; ขั้นตอนนี้ยังไม่ฝึกโมเดล"""
        self.root = Path(root)
        self.data_dir = self.root / 'data/modeling/market_occupancy'
        self.report_dir = self.root / 'reports/market_occupancy/evaluation'
        self.model_dir = self.root / 'models/market_occupancy'
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.metadata = json.loads((self.data_dir / 'forecast_feature_metadata.json').read_text(encoding='utf-8'))
        if self.metadata['seasonal_period_weeks'] != 52 or max(self.metadata['horizons_weeks']) > 52:
            raise ValueError('การคืน seasonal difference รอบนี้รองรับ s=52 และ horizon ไม่เกิน 52 สัปดาห์')
        self.series = pd.read_csv(self.data_dir / 'sarima_weekly_series.csv', parse_dates=['date'])
        self.rf_data = {}
        self.x_data = {}
        for target in self.metadata['targets']:
            for horizon in self.metadata['horizons_weeks']:
                key = (target, horizon)
                self.rf_data[key] = pd.read_csv(self.data_dir / f'rf_{target}_h{horizon}.csv', parse_dates=['forecast_origin', 'target_date'])
                self.x_data[key] = pd.read_csv(self.data_dir / f'sarimax_{target}_h{horizon}.csv', parse_dates=['forecast_origin', 'target_date'])
        self.cache = {}
        self.fit_log = []
        self.x_columns = self.metadata['sarimax_features_by_target']
        self.numeric = self.metadata['rf_numeric_features']
        self.categorical = self.metadata['rf_categorical_features']
        # รหัสตรวจโค้ด/ข้อมูลสำหรับ cache: อ่านผ่านได้เมื่อศึกษาเฉพาะหลักการโมเดล
        digest = hashlib.sha256(json.dumps(SETTINGS, sort_keys=True).encode())
        digest.update(Path(__file__).read_bytes())
        for path in sorted(self.data_dir.glob('*')):
            if path.is_file():
                digest.update(path.name.encode())
                digest.update(path.read_bytes())
        self.signature = digest.hexdigest()

    def fit_cutoff(self, origin, split):
        """หาวันสุดท้ายที่ใช้ fit ได้ในรอบนี้
        
        Validation ใช้ถึง Train end; Test ใช้ถึง Validation end
        ทั้งสองกรณีต้องไม่เกิน origin ซึ่งเป็นวันที่เริ่มพยากรณ์"""
        end = self.metadata['train_end'] if split == 'Validation' else self.metadata['validation_end']
        return min(pd.Timestamp(origin), pd.Timestamp(end))

    def eligible_cases(self, target, horizon, split, cohort='main'):
        """เลือกกรณีประเมินของ target/horizon/split ที่ระบุ
        
        cohort=main ใช้ประวัติอย่างน้อย 104 จุด; short_history ใช้กลุ่มอื่น
        Test origin ต้องไม่ก่อนวันที่เลือกโมเดลจาก Validation เสร็จ"""
        candidates = self.rf_data[(target, horizon)]
        ready = candidates['seasonal_trial_ready'] if cohort == 'main' else ~candidates['seasonal_trial_ready']
        keep = candidates['split'].eq(split) & ready
        if split == 'Test':
            keep &= candidates['forecast_origin'].ge(pd.Timestamp(self.metadata['validation_end']))
        return candidates.loc[keep].copy()

    def rf_input(self, data):
        """เลือกคอลัมน์ที่ Random Forest ใช้และทำหมวดหมู่ให้เป็นข้อความ
        
        รับ DataFrame แล้วคืน DataFrame ของ features โดยไม่มีคอลัมน์คำตอบ y"""
        frame = data[self.numeric + self.categorical].copy()
        for column in self.categorical:
            frame[column] = frame[column].fillna('unknown').astype(str)
        return frame

    def fit_rf(self, target, horizon, cutoff):
        """ฝึก Random Forest หนึ่งงาน (target, horizon) ถึงวัน cutoff
        
        อ่านตามลำดับ: เลือกข้อมูลที่ทราบแล้ว → เตรียมตัวเลข/หมวดหมู่ → fit pipeline
        คืน pipeline ที่ใช้ predict ได้; cache เก็บ pipeline เดิมเมื่อใช้ cutoff เดียวกัน"""
        key = ('RandomForest', target, horizon, str(cutoff))
        if key not in self.cache:
            data = self.rf_data[(target, horizon)]
            train = data.loc[data['target_date'].le(cutoff)]
            if train.empty:
                raise ValueError('ไม่มีคำตอบที่ทราบแล้วสำหรับฝึก Random Forest')
            # 1. ตัวเลขเติม median; หมวดหมู่แปลงเป็น one-hot โดย fit เฉพาะข้อมูลฝึก
            transform = ColumnTransformer([
                ('numeric', SimpleImputer(strategy='median', add_indicator=True), self.numeric),
                ('category', OneHotEncoder(handle_unknown='ignore', sparse_output=False), self.categorical),
            ])
            model = Pipeline([('prepare', transform), ('regressor', RandomForestRegressor(**SETTINGS['rf']))])
            # 2. ฝึก preprocessing และ Random Forest พร้อมกันผ่าน Pipeline
            model.fit(self.rf_input(train), train['y'])
            self.cache[key] = model
            self.fit_log.append({'method': 'RandomForest', 'target': target, 'horizon_weeks': horizon,
                                 'cutoff': str(cutoff), 'train_rows': len(train), 'max_label_date': str(train['target_date'].max()), 'converged': True})
        return self.cache[key]

    def time_series_frame(self, target, horizon, project_id, end, method):
        """เตรียมอนุกรมเวลาของโครงการเดียว โดยตัดข้อมูลถึงวัน end
        
        SARIMA ใช้ y อย่างเดียว; SARIMAX ใช้ y และคอลัมน์ exog
        asfreq(7D) ทำให้ index เป็นรายสัปดาห์ สัปดาห์ที่ขาดคงเป็น NaN"""
        if method == 'SARIMA':
            data = self.series.loc[self.series['project_id'].eq(project_id), ['date', target]]
            return data.loc[data['date'].le(end)].set_index('date').asfreq('7D').rename(columns={target: 'y'})
        data = self.x_data[(target, horizon)]
        data = data.loc[data['project_id'].eq(project_id) & data['target_date'].le(end)]
        return data.set_index('target_date')[['y'] + self.x_columns[target]].sort_index().asfreq('7D')

    def fit_time_series(self, method, target, horizon, project_id, cutoff):
        # SARIMA ไม่ใช้ horizon ในการ fit จึงใช้ cache ร่วมกันได้
        """ฝึก SARIMA หรือ SARIMAX ของโครงการเดียวถึงวัน cutoff
        
        อ่านตามลำดับ: เลือกอนุกรมเวลา → ปรับสเกล → เตรียม exog → fit → ตรวจการลู่เข้า
        คืน dict ของ params, center, scale และตัวแปลงข้อมูล สำหรับพยากรณ์ภายหลัง"""
        cache_horizon = horizon if method == 'SARIMAX' else 0
        key = (method, target, cache_horizon, project_id, str(cutoff))
        if key in self.cache:
            return self.cache[key]
        train = self.time_series_frame(target, horizon, project_id, cutoff, method)
        if train['y'].notna().sum() < 70:
            raise ValueError('ข้อมูลที่ใช้ fit หลังเลื่อน exog มีน้อยกว่า 70 จุด')
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
            order=tuple(SETTINGS['order']),
            seasonal_order=tuple(SETTINGS['seasonal_order']),
            simple_differencing=True,
            enforce_stationarity=True,
            enforce_invertibility=True,
            trend='n',
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            model = SARIMAX(y, exog=x, **specification)
            fitted = model.fit(disp=False, maxiter=SETTINGS['maxiter'])
            if not fitted.mle_retvals.get('converged', False):
                fitted = model.fit(disp=False, method='powell', maxiter=250)
        # 3. converged=True หมายถึงตัวหาค่าพารามิเตอร์ลู่เข้า จึงใช้ผลนี้ต่อได้
        converged = bool(fitted.mle_retvals.get('converged', False))
        self.fit_log.append({'method': method, 'target': target, 'horizon_weeks': cache_horizon,
                             'project_id': project_id, 'cutoff': str(cutoff), 'max_label_date': str(train.index.max()),
                             'train_rows': int(train['y'].notna().sum()), 'converged': converged, 'warnings': len(caught)})
        if not converged or not np.isfinite(fitted.params).all():
            raise ValueError('โมเดลอนุกรมเวลาไม่ลู่เข้า จะไม่ใช้ค่าทำนายแทนผลที่สำเร็จ')
        artifact = {'params': fitted.params, 'center': center, 'scale': scale,
                    'imputer': imputer, 'scaler': scaler, 'specification': specification}
        self.cache[key] = artifact
        return artifact

    def forecast_time_series(self, method, target, horizon, project_id, origin, cutoff):
        """พยากรณ์จากข้อมูลที่ทราบถึง origin โดยใช้ params ที่ fit ถึง cutoff
        
        SARIMAX ต้องมี exog ครบทุกก้าวถึง horizon และไม่มีข้อมูลหลัง origin
        filter อัปเดตสถานะด้วย params เดิม ไม่ fit coefficients ใหม่
        ผล model เป็นความต่างรายปี จึงบวกค่าปีที่แล้วกลับเพื่อคืนหน่วยจริง"""
        artifact = self.fit_time_series(method, target, horizon, project_id, cutoff)
        known = self.time_series_frame(target, horizon, project_id, origin, method)
        y = (known['y'] - artifact['center']) / artifact['scale']
        x = future_x = None
        # SARIMAX มีข้อมูลประกอบ (exog); SARIMA ใช้เฉพาะประวัติ y
        if method == 'SARIMAX':
            columns = self.x_columns[target]
            transform = lambda values: artifact['scaler'].transform(artifact['imputer'].transform(values))
            x = transform(known[columns])
            future_dates = pd.date_range(origin + pd.Timedelta(weeks=1), periods=horizon, freq='7D')
            data = self.x_data[(target, horizon)]
            path = data.loc[
                data['project_id'].eq(project_id)
                & data['target_date'].isin(future_dates)
            ].sort_values('target_date')
            if len(path) != horizon or not path['forecast_origin'].le(origin).all():
                raise ValueError('future exog ไม่ครบหรือใช้ข้อมูลหลัง origin')
            future_x = transform(path[columns])
        # อัปเดต state ด้วยค่าที่รู้ถึง origin แต่ไม่ fit พารามิเตอร์จาก Validation/Test ใหม่
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', category=UserWarning)
            filtered = SARIMAX(y, exog=x, **artifact['specification']).filter(artifact['params'])
            difference_forecast = np.asarray(filtered.forecast(horizon, exog=future_x))[-1]
        # simple_differencing=True คืนผลบนสเกล y[t]-y[t-52] ต้องบวกปีที่แล้วกลับ
        target_date = origin + pd.Timedelta(weeks=horizon)
        anchor_date = target_date - pd.Timedelta(weeks=52)
        history = self.series.loc[self.series['project_id'].eq(project_id)].set_index('date')[target]
        anchor = history.get(anchor_date, np.nan)
        return float(anchor + difference_forecast * artifact['scale'])

    def run_backtest(self, split, methods, cohort='main'):
        """วนพยากรณ์ target → horizon → origin → project → model
        
        แต่ละ origin จำกัดข้อมูล fit ด้วย cutoff ก่อนเรียกโมเดล
        คืนตาราง actual/prediction พร้อมวันและเหตุผลเมื่อพยากรณ์ไม่ได้"""
        if split not in ['Validation', 'Test']:
            raise ValueError('ประเมินเฉพาะ Validation หรือ Test')
        if split == 'Test':
            locked_path = self.report_dir / 'locked_selection.json'
            if not locked_path.exists():
                raise ValueError('ต้องเลือกจาก Validation และล็อกโมเดลก่อนเปิด Test')
            locked = json.loads(locked_path.read_text(encoding='utf-8'))
            if locked['signature'] != self.signature:
                raise ValueError('ค่าตั้งต้นหรือข้อมูลเปลี่ยนหลังล็อก ต้องทำ Validation ใหม่ก่อน')
        output_rows = []
        for target in self.metadata['targets']:
            for horizon in self.metadata['horizons_weeks']:
                key = (target, horizon)
                cases = self.eligible_cases(target, horizon, split, cohort)
                if cases.empty:
                    continue
                print(f'{split}: {target}, h={horizon}, {len(cases)} cases, {methods}', file=sys.stderr, flush=True)
                # ประเมินทีละวันเริ่มพยากรณ์; batch คือทุกโครงการในวันนั้น
                for origin, batch in cases.groupby('forecast_origin'):
                    cutoff = self.fit_cutoff(origin, split)
                    rf_model = None
                    if 'RandomForest' in methods:
                        rf_model = self.fit_rf(target, horizon, cutoff)
                    rf_values = rf_model.predict(self.rf_input(batch)) if rf_model is not None else [np.nan] * len(batch)
                    for row_index, (_, row) in enumerate(batch.iterrows()):
                        project_id = int(row['project_id'])
                        history = self.series.loc[self.series['project_id'].eq(project_id) & self.series['date'].le(origin)].set_index('date')[target]
                        total_units = float(row['total_units'])
                        for method in methods:
                            reason = ''
                            try:
                                if method == 'Naive':
                                    raw = history.dropna().iloc[-1]
                                elif method == 'SeasonalNaive':
                                    raw = history.get(row['target_date'] - pd.Timedelta(weeks=52), np.nan)
                                elif method == 'RandomForest':
                                    raw = rf_values[row_index]
                                else:
                                    raw = self.forecast_time_series(method, target, horizon, project_id, origin, cutoff)
                                prediction = bounded_prediction(raw, target, total_units)
                                if not np.isfinite(prediction):
                                    reason = 'missing seasonal anchor or nonfinite forecast'
                            except (ValueError, np.linalg.LinAlgError, IndexError) as error:
                                raw = prediction = np.nan
                                reason = str(error)
                            output_rows.append({
                                'split': split, 'target': target, 'horizon_weeks': horizon,
                                'project_id': project_id, 'forecast_origin': origin, 'target_date': row['target_date'],
                                'actual': float(row['y']), 'method': method, 'raw_prediction': raw,
                                'prediction': prediction, 'fit_cutoff': cutoff,
                                'was_clipped': bool(np.isfinite(raw) and raw != prediction), 'failure_reason': reason,
                            })
        return pd.DataFrame(output_rows)

    def run_or_load(self, split, methods, cohort='main'):
        """โหลดผลเดิมเมื่อข้อมูล/โค้ด/พารามิเตอร์ตรงกัน มิฉะนั้นเรียก run_backtest
        
        คืนตารางคำทำนายที่ใช้คำนวณคะแนนต่อได้
        ส่วนตรวจ signature เป็นการตรวจผลบันทึก ไม่ใช่ขั้นตอนเรียนรู้ของโมเดล"""
        if split == 'Test':
            lock = self.report_dir / 'locked_selection.json'
            if not lock.exists() or json.loads(lock.read_text(encoding='utf-8'))['signature'] != self.signature:
                raise ValueError('ต้องล็อกผล Validation ที่ตรงข้อมูล/โค้ดก่อนอ่านหรือรัน Test')
        name = '_'.join(methods) + ('_short_history' if cohort != 'main' else '')
        path = self.report_dir / f'{split.lower()}_{name}.csv'
        stamp = path.with_suffix('.json')
        if path.exists() and stamp.exists():
            if json.loads(stamp.read_text())['signature'] == self.signature:
                return pd.read_csv(path, parse_dates=['forecast_origin', 'target_date', 'fit_cutoff'])
        predictions = self.run_backtest(split, methods, cohort)
        predictions.to_csv(path, index=False, encoding='utf-8-sig')
        stamp.write_text(json.dumps({'signature': self.signature}), encoding='utf-8')
        pd.DataFrame(self.fit_log).to_csv(self.report_dir / 'fit_diagnostics.csv', index=False, encoding='utf-8-sig')
        return predictions

    def lock_selection(self, scores):
        """บันทึกผู้ชนะจาก Validation ก่อนประเมิน Test
        
        รับตารางคะแนน Validation คืนตารางผู้ชนะและบันทึก locked_selection.json"""
        winners = select_from_validation(scores)
        if len(winners) != len(self.metadata['targets']) * len(self.metadata['horizons_weeks']):
            raise ValueError('มี target/horizon ที่ยังไม่มีชุดเปรียบเทียบครบทุกวิธี')
        content = {'signature': self.signature, 'settings': SETTINGS, 'selection_available_on': self.metadata['validation_end'],
                   'chosen_from': 'Validation only', 'winners': winners.to_dict('records')}
        (self.report_dir / 'locked_selection.json').write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding='utf-8')
        return winners

    def save_selected_models(self, winners):
        """ฝึกผู้ชนะถึง Validation end แล้วบันทึกโมเดลและ metadata
        
        เก็บทั้ง pipeline ของ RF, params ของ time series และประวัติสำหรับ baseline
        ยังต้องอัปเดตข้อมูลที่ทราบ ณ วันพยากรณ์เมื่อนำไปใช้งาน"""
        cutoff = pd.Timestamp(self.metadata['validation_end'])
        artifacts = {}
        for row in winners.itertuples():
            target, horizon, method = row.target, int(row.horizon_weeks), row.method
            if method == 'RandomForest':
                artifacts[(target, horizon)] = {'method': method, 'pipeline': self.fit_rf(target, horizon, cutoff)}
            else:
                projects = self.rf_data[(target, horizon)].loc[
                    self.rf_data[(target, horizon)]['split'].eq('Test') & self.rf_data[(target, horizon)]['seasonal_trial_ready'], 'project_id'].unique()
                models = {}
                for project_id in projects:
                    if method in ['SARIMA', 'SARIMAX']:
                        models[int(project_id)] = self.fit_time_series(method, target, horizon, int(project_id), cutoff)
                artifacts[(target, horizon)] = {'method': method, 'project_models': models}
        bundle = {'status': 'selected_evaluation_models_not_web_integrated', 'trained_through': str(cutoff.date()),
                  'artifacts': artifacts, 'metadata': self.metadata, 'settings': SETTINGS,
                  'baseline_history': self.series.loc[self.series['date'].le(cutoff)], 'signature': self.signature}
        joblib.dump(bundle, self.model_dir / 'selected_models.joblib')
        manifest = {'status': bundle['status'], 'trained_through': bundle['trained_through'],
                    'signature': self.signature, 'settings': SETTINGS, 'winners': winners.to_dict('records'),
                    'integration_note': 'Requires known-history state update and horizon-specific exog; not a single sklearn predict API.'}
        (self.model_dir / 'model_metadata.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
