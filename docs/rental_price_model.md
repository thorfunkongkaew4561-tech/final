# โมเดลพยากรณ์ราคาค่าเช่า

เอกสารนี้อธิบายส่วนงานพยากรณ์ราคาค่าเช่าของอาทิตยา โดยใช้ข้อมูลเดิม
จากตาราง `leases`, `units` และ `projects` และไม่สร้างข้อมูลจำลองเพิ่ม

## โมเดลที่เปรียบเทียบ

1. **Forward/Stepwise Multiple Linear Regression**
   - เพิ่ม Feature ทีละกลุ่ม
   - เลือก Feature ที่ทำให้ Rolling Validation MAE เฉลี่ยลดลงมากที่สุด
   - เหมาะสำหรับอธิบายว่าปัจจัยใดสัมพันธ์กับราคาค่าเช่า
2. **Gradient Boosting Regressor**
   - รวม Decision Tree ขนาดเล็กหลายต้นตามลำดับ
   - เหมาะสำหรับความสัมพันธ์ที่ไม่เป็นเส้นตรง
3. **Random Forest Regressor**
   - รวมผลจาก Decision Tree หลายต้นที่สร้างแบบ Bagging
   - ใช้เปรียบเทียบความสัมพันธ์ที่ไม่เป็นเส้นตรง
4. **K-Nearest Neighbors Regressor**
   - ทำนายราคาจากห้องที่มีลักษณะใกล้เคียงกัน
   - ปรับสเกล Feature ก่อนคำนวณระยะห่าง
5. **Artificial Neural Network**
   - ใช้ `MLPRegressor` เรียนรู้ความสัมพันธ์ที่ซับซ้อน
   - ปรับสเกลทั้ง Feature และราคาเช่าก่อนฝึก

การเลือก Feature และการจูนพารามิเตอร์ใช้ **Rolling Time Validation 4 Fold**
ภายในชุด Train จากนั้นเลือกโมเดลผู้ชนะจาก **Validation MAE หลัก** เท่านั้น
หลังเลือกเสร็จจึงประเมิน Test set หนึ่งครั้ง

## ลำดับการทำงาน

```text
สร้าง Feature
    ↓
แบ่ง Train / Validation / Test ตามเวลา
    ↓
สร้าง Rolling Validation 4 Fold ภายใน Train
    ↓
Forward Selection และจูน Gradient Boosting/Random Forest/KNN/ANN จาก MAE เฉลี่ย 4 Fold
    ↓
เลือกโมเดลจาก Validation MAE
    ↓
ฝึกใหม่ด้วย Train + Validation
    ↓
ประเมิน Test และบันทึก Pipeline
    ↓
คำนวณ Error Quantile จาก Validation และตรวจ Coverage บน Test
```

## Feature ที่ Stepwise เลือก

- `room_type`
- `project_name`
- `start_month`
- `view`
- `is_renewal`
- `furnished`
- `floor`

Forward Selection หยุดเมื่อการเพิ่ม Feature ถัดไปช่วยลด Rolling
Validation MAE เฉลี่ยน้อยกว่า 1 บาท

## Rolling Time Validation

| Fold | Train ถึง | Validation ถึง | Train rows | Validation rows |
|---|---|---|---:|---:|
| 2025 Q1 | 31 ธ.ค. 2024 | 31 มี.ค. 2025 | 23,898 | 2,546 |
| 2025 Q2 | 31 มี.ค. 2025 | 30 มิ.ย. 2025 | 26,444 | 6,614 |
| 2025 Q3 | 30 มิ.ย. 2025 | 30 ก.ย. 2025 | 33,058 | 3,001 |
| 2025 Q4 | 30 ก.ย. 2025 | 31 ธ.ค. 2025 | 36,059 | 4,521 |

Gradient Boosting ทดลอง 12 ชุดใน 4 Fold รวม 48 การทดลอง ชุดที่ชนะมี
Rolling Validation MAE เฉลี่ย 860.59 บาท และส่วนเบี่ยงเบนมาตรฐาน
124.13 บาท

Random Forest ทดลอง 10 ชุดใน 4 Fold รวม 40 การทดลอง ชุดที่ชนะมี
Rolling Validation MAE เฉลี่ย 861.86 บาท และส่วนเบี่ยงเบนมาตรฐาน
141.94 บาท

KNN ทดลอง 6 ชุดใน 4 Fold รวม 24 การทดลอง ชุดที่ชนะมี Rolling
Validation MAE เฉลี่ย 937.41 บาท และส่วนเบี่ยงเบนมาตรฐาน 116.48 บาท

ANN ทดลอง 5 ชุดใน 4 Fold รวม 20 การทดลอง ชุดที่ชนะมี Rolling
Validation MAE เฉลี่ย 874.16 บาท และส่วนเบี่ยงเบนมาตรฐาน 46.27 บาท

## Hyperparameters ของ Gradient Boosting ที่เลือก

```text
n_estimators = 350
learning_rate = 0.03
max_depth = 4
min_samples_leaf = 15
subsample = 0.9
random_state = 42
```

## Hyperparameters ของ Random Forest ที่เลือก

```text
n_estimators = 400
max_depth = 20
min_samples_split = 5
min_samples_leaf = 4
max_features = 0.7
random_state = 42
```

## Hyperparameters ของ KNN ที่เลือก

```text
n_neighbors = 10
weights = distance
p = 1 (Manhattan distance)
```

## Hyperparameters ของ ANN ที่เลือก

```text
hidden_layer_sizes = (64,)
activation = relu
alpha = 0.0001
learning_rate_init = 0.001
random_state = 42
```

## ผลการเปรียบเทียบ

| Model | Split | MAE | RMSE | R² |
|---|---|---:|---:|---:|
| Stepwise MLR | Validation | 770.84 | 1,051.46 | 0.7186 |
| Gradient Boosting | Validation | 759.60 | 1,021.25 | 0.7345 |
| Random Forest | Validation | **713.92** | **955.94** | **0.7674** |
| KNN | Validation | 808.07 | 1,111.78 | 0.6854 |
| ANN | Validation | 870.11 | 1,143.05 | 0.6674 |
| Stepwise MLR | Test | 1,113.72 | 1,395.80 | 0.5854 |
| Gradient Boosting | Test | 1,032.37 | 1,314.12 | 0.6325 |
| Random Forest | Test | **1,020.73** | 1,330.66 | 0.6232 |
| KNN | Test | 1,117.42 | 1,439.12 | 0.5592 |
| ANN | Test | 1,069.96 | 1,356.02 | 0.6086 |

Random Forest เป็นผู้ชนะจากการเปรียบเทียบทั้ง 5 โมเดลตามเกณฑ์ที่กำหนดไว้
ล่วงหน้า เพราะมี Validation MAE ต่ำที่สุด และมี Test MAE ต่ำที่สุดเช่นกัน
อย่างไรก็ตาม Gradient Boosting
มี Test RMSE ต่ำกว่าและ R² สูงกว่าเล็กน้อย จึงควรรายงานหลาย Metric ควบคู่กัน
ไม่ควรสรุปว่า Random Forest ดีกว่าในทุกมิติ

ผล Test ที่ลดลงจาก Validation แสดงว่ารูปแบบราคาในช่วงเวลาล่าสุดเปลี่ยนไป
ควรระบุประเด็นนี้เป็นข้อจำกัดในรายงาน

## ช่วงความคลาดเคลื่อนอ้างอิง

หลังเลือกโมเดลผู้ชนะ ระบบคำนวณ Absolute Error Quantile จาก Validation:

| Quantile | Absolute Error |
|---|---:|
| P50 | 545.99 บาท |
| P75 | 990.23 บาท |
| P90 | 1,533.93 บาท |

ระบบใช้ P75 เป็น Margin อ้างอิงและบันทึกไว้ใน Metadata โดยไม่เขียนตัวเลข
ตายตัวใน Price Engine อย่างไรก็ตาม เมื่อนำ P75 Margin ไปตรวจบน Test พบว่า
ครอบคลุมจริง 58.80% ต่ำกว่าเป้าหมาย 75% สะท้อนว่าความคลาดเคลื่อนในช่วง
Test สูงกว่า Validation จึงต้องแสดง Test Coverage ควบคู่กับช่วงราคา และยัง
ไม่ควรเรียกช่วงนี้ว่า Prediction Interval หรือช่วงความเชื่อมั่น

ข้อมูลช่วงความคลาดเคลื่อนยังถูกส่งกลับเพื่อใช้วิเคราะห์ภายใน แต่ผลลัพธ์
สำหรับผู้ใช้งานทั่วไปแสดงเฉพาะราคาแนะนำและข้อความกำกับ:

```text
ราคาเช่าที่แนะนำ: 9,930 บาท/เดือน
ราคาเช่านี้เป็นค่าประมาณ
ควรพิจารณาสภาพห้องและตลาดเพิ่มเติม
```

## ไฟล์สำคัญ

- `src/kaverentai/features/rental_price_features.py` — สร้าง Feature
- `src/kaverentai/models/rental_price_models.py` — สร้าง Pipeline และเลือก Feature
- `src/kaverentai/models/rental_price_uncertainty.py` — คำนวณและตรวจ Error Reference
- `src/kaverentai/models/tune_rental_price.py` — ปรับ Gradient Boosting, Random Forest, KNN และ ANN
- `src/kaverentai/models/train_rental_price.py` — ฝึกและเปรียบเทียบโมเดล
- `src/kaverentai/recommendation/price_engine.py` — โหลดโมเดลผู้ชนะไปใช้งาน
- `tests/test_rental_price.py` — Unit Tests

## วิธีรัน

```powershell
.venv\Scripts\python.exe -m kaverentai.models.train_rental_price
.venv\Scripts\python.exe -m kaverentai.recommendation.price_engine
.venv\Scripts\python.exe -m pytest -q
```

## เอกสารอ้างอิงหลัก

- แบบจำลองพยากรณ์อัตราค่าเช่าที่อยู่อาศัยประเภทหอพักหรืออพาร์ตเมนต์
  ในพื้นที่โดยรอบสถาบันการศึกษา กรณีศึกษา มหาวิทยาลัยธรรมศาสตร์
  ศูนย์รังสิต — ใช้อ้างอิงแนวทาง Stepwise Multiple Linear Regression
- Hernes, M., Tutak, M., & Siewiera, A. (2024). *Prediction of residential
  real estate price on primary market using machine learning*.
  Procedia Computer Science, 246, 3142–3147.
  DOI: 10.1016/j.procs.2024.09.358 — ใช้อ้างอิง Gradient Boosting
- *A Machine Learning Approach Using Spatially Explicit K-Nearest Neighbors
  for House Price Predictions* — ใช้อ้างอิง KNN และ ANN
- *Appropriate Rental Price Prediction for Condominiums in Pattaya,
  Thailand Using Artificial Neural Network Approach* — ใช้อ้างอิง ANN
