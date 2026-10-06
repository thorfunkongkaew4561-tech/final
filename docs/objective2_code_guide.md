# วิธีอ่านโค้ดวัตถุประสงค์ข้อ 2

เริ่มจาก `notebooks/02_market_occupancy_eda.ipynb` แล้วอ่านตามลำดับ 4 ส่วน ไม่ต้องเริ่มจาก class ในไฟล์โมเดล ส่วนสรุปผลอยู่ใน `notebooks/06_final_results.ipynb` ส่วนที่ 2

## ไฟล์ไหนทำอะไร

| ไฟล์ | สิ่งที่ทำ | เริ่มอ่านตรงไหน |
|---|---|---|
| Notebook 02 ส่วนที่ 1 | ตรวจข้อมูลและ EDA เฉพาะ Train | โหลดตาราง → ตรวจคุณภาพ → ดูกราฟ |
| Notebook 02 ส่วนที่ 2 | สร้าง lag/rolling และคำตอบล่วงหน้า | panel → origin_features → pairs_by_horizon |
| `src/kaverentai/features/market_occupancy_features.py` | รายละเอียดการเตรียมข้อมูล | `prepare_weekly_panel`, `build_origin_features`, `build_forecast_pairs` |
| Notebook 02 ส่วนที่ 3 | ฝึกและประเมินรอบแรก | Validation → เลือกโมเดล → Test |
| `src/kaverentai/models/train_market_occupancy.py` | เรียกขั้นตอนฝึกทั้งหมดจากคำสั่งเดียว | `main()` ขั้นที่ 1–5 |
| `src/kaverentai/models/market_occupancy_forecasting.py` | วิธี fit/predict และกฎเวลา | `fit_rf`, `fit_time_series`, `forecast_time_series` |
| Notebook 02 ส่วนที่ 4 | จูนพารามิเตอร์ใน Train แล้วเทียบ Validation | GRIDS → TrainCV → parameter_map → Validation |
| `src/kaverentai/models/tune_market_occupancy.py` | รายละเอียดการทดลอง candidates | `training_cv_cases`, `choose_parameters`, `tune_on_train` |
| Notebook 06 ส่วนที่ 2 | อ่านผลเดิมและสรุปสำหรับรายงาน | คะแนน → ผู้ชนะ → กราฟ → ข้อสรุป |

## ตัวแปรสำคัญ

| ชื่อ | ความหมาย |
|---|---|
| target | ตัวแปรที่จะพยากรณ์ เช่น occupancy |
| horizon | พยากรณ์ล่วงหน้ากี่สัปดาห์ |
| forecast_origin | วันที่เริ่มพยากรณ์ ใช้ได้เฉพาะข้อมูลที่ทราบถึงวันนี้ |
| target_date | วันที่ของคำตอบที่ต้องการพยากรณ์ |
| cutoff | วันสุดท้ายที่อนุญาตให้ข้อมูลเข้า fit ในรอบนั้น |
| y / actual | คำตอบจริง |
| prediction | ค่าที่โมเดลพยากรณ์ |
| exog | ข้อมูลประกอบ SARIMAX เช่นจำนวนผู้ค้นหาที่ทราบแล้ว |
| candidate | ชุดพารามิเตอร์หนึ่งชุดที่นำมาทดลอง |

## อ่านคำสั่ง pandas

```python
# 1. สร้างเงื่อนไข True/False ของแต่ละแถว
is_train = data["split"] == "Train"
known_answer = data["target_date"] <= origin

# 2. เก็บเฉพาะแถวที่ผ่านทั้งสองเงื่อนไข
training_data = data.loc[is_train & known_answer].copy()

# 3. เรียงก่อนอ่านหรือคำนวณประวัติ
training_data = training_data.sort_values(["project_id", "target_date"])
```

`&` คือผ่านทั้งสองเงื่อนไข, `|` คือผ่านอย่างน้อยหนึ่งเงื่อนไข, `~` คือกลับ True/False ส่วน `copy()` ทำตารางใหม่เพื่อแก้ข้อมูลโดยไม่เปลี่ยนตารางต้นทาง `groupby("project_id")` คำนวณแยกโครงการ และ `merge()` จับคู่ตารางด้วยคอลัมน์ที่กำหนด

## lag กับ rolling

```python
previous_values = values.shift(1)  # เลื่อนหนึ่งสัปดาห์ ไม่ใช้สัปดาห์ปัจจุบัน
rolling_values = previous_values.rolling(4, min_periods=4)
mean_of_past_four_weeks = rolling_values.mean()
```

ที่สัปดาห์ t สูตรนี้ใช้ t−1 ถึง t−4 หากประวัติไม่ครบ ค่ายังคงเป็น NaN ไม่ใช้ค่าจากอนาคตเติม ตัวอย่างนี้เป็นรูปแบบเดียวกับ `past_rolling_mean` ในไฟล์ features

## class และ Pipeline ในไฟล์โมเดล

`experiment = ForecastExperiment()` สร้างตัวช่วยที่เก็บข้อมูลและฟังก์ชันทดลองไว้ด้วยกัน `self` ใน class หมายถึง experiment นี้ เช่น `self.rf_data` คือชุดข้อมูลของ Random Forest และ `self.fit_log` คือบันทึกการฝึก `cache` เก็บผลที่คำนวณแล้วเพื่อเรียกซ้ำได้เมื่อข้อมูลและค่าตั้งต้นตรงกัน

`Pipeline` ของ Random Forest มีสองขั้น: prepare แปลง features และ regressor ฝึกโมเดล ทั้งสองขั้น fit จากข้อมูลฝึกเดียวกัน ตัวเลขเติม median ส่วนหมวดหมู่แปลงเป็น one-hot

`TunedForecastExperiment` ใช้การพยากรณ์และกฎเวลาเดียวกับรอบแรก แต่เลือกพารามิเตอร์แยกแต่ละงาน `super()` เรียกขั้นตอนของ class เดิม เพื่อไม่เขียนวิธีพยากรณ์ซ้ำ

## ผลที่แต่ละขั้นส่งกลับ

```python
origin_features, numeric_features, categorical_features = build_origin_features(panel)
# ตาราง features / รายชื่อคอลัมน์ตัวเลข / รายชื่อคอลัมน์หมวดหมู่

cv_scores, chosen_parameters, parameter_map = tuner.tune_on_train()
# คะแนนทุก candidate / ตารางชุดที่เลือก / dict พารามิเตอร์สำหรับโมเดล
```

`fit_time_series` คืน dict ของพารามิเตอร์และตัวแปลงข้อมูล ส่วน `forecast_time_series` คืนค่าพยากรณ์หนึ่งค่า ขั้น forecast ใช้ params เดิมกับประวัติที่ทราบถึง origin และคืนผล seasonal difference กลับเป็นหน่วยจริง รายละเอียดนี้สำคัญต่อความถูกต้องของ SARIMA/SARIMAX

## วิธีอ่านผล

MAE และ RMSE ยิ่งต่ำยิ่งดี แต่ต้องอ่านแยก target เพราะหน่วยต่างกัน occupancy คูณ 100 เพื่อรายงานเป็นจุดเปอร์เซ็นต์ การเปรียบเทียบทุกโมเดลใช้กรณีเดียวกัน และ before/after ใช้แถวตรงกันทั้งสองรอบ

พารามิเตอร์เลือกจาก TrainCV โมเดลเลือกจาก Validation ผล Test ใน Notebook เป็นรอบแรกก่อนจูน โมเดลหลังจูนยังไม่มีผล final holdout ใหม่ และข้อมูลของโครงงานเป็นข้อมูลจำลอง
