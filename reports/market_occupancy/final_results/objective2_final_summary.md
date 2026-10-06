# สรุปผลวัตถุประสงค์ข้อ 2

เพื่อพัฒนาโมเดลพยากรณ์สภาวะตลาดและอัตราการเข้าพักล่วงหน้า (Market & Occupancy Forecasting)

ทดลอง SARIMA, SARIMAX และ Random Forest พร้อม Naive และ Seasonal Naive บนข้อมูลจำลองของโครงงาน
เลือกพารามิเตอร์ด้วย rolling-origin ภายใน Train แล้วเลือก family ด้วย Validation MAE แยก target/horizon

จูนได้ 108 ชุดคะแนน CV ผล Validation ของ 36 งานดีขึ้น 13 งาน แย่ลง 10 งาน และเท่าเดิม 13 งาน

| Target | Horizon (สัปดาห์) | วิธีที่เลือก | Validation MAE หลังจูน | RMSE | หน่วย | จำนวนกรณี |
|---|---:|---|---:|---:|---|---:|
| median_asking_rent | 1 | Naive | 123.0769 | 196.0262 | baht/month | 156 |
| median_asking_rent | 4 | RandomForest | 262.0789 | 321.6435 | baht/month | 148 |
| median_asking_rent | 12 | RandomForest | 253.0383 | 320.7927 | baht/month | 68 |
| n_listings_open | 1 | SARIMA | 3.9876 | 5.2691 | count | 156 |
| n_listings_open | 4 | SARIMA | 8.5354 | 10.8008 | count | 148 |
| n_listings_open | 12 | SeasonalNaive | 12.6912 | 16.6225 | count | 68 |
| n_searchers | 1 | SARIMA | 4.4084 | 6.0526 | count | 156 |
| n_searchers | 4 | RandomForest | 3.5657 | 4.6855 | count | 148 |
| n_searchers | 12 | SARIMA | 3.5294 | 4.6873 | count | 68 |
| occupancy | 1 | SARIMA | 0.4920 | 0.6339 | percentage points | 156 |
| occupancy | 4 | SARIMAX | 0.9809 | 1.2673 | percentage points | 148 |
| occupancy | 12 | SARIMAX | 1.3009 | 1.6639 | percentage points | 68 |

ข้อสรุปและข้อจำกัด:

- baseline ชนะบางงาน จึงไม่มีโมเดลเดียวดีที่สุดทุก target/horizon
- ก่อน/หลังจูนเปรียบเทียบบนแถวเดียวกัน; Validation origin หลังจูนไม่ก่อน 25 พฤศจิกายน 2025
- การจูนเป็น small-grid search: 3 candidates ต่อ family และ 4 origins ไม่ใช่ exhaustive search
- ผล Test ใน Notebook เป็นรอบแรกก่อนจูนเท่านั้น; โมเดลหลังจูนยังไม่มี final holdout ใหม่
- Test h=12 รอบแรกมี origin เดียว; ต้องเพิ่มข้อมูลเพื่อประเมินความสม่ำเสมอข้ามเวลา
- ใช้ข้อมูลจำลอง ไม่อ้างเป็นประสิทธิภาพที่ยืนยันในธุรกิจจริง
- ยังไม่มี Prediction Interval ที่ตรวจสอบแล้ว และยังไม่เชื่อม Web/What-if รายสัปดาห์ครบ 1–12

โมเดลหลังจูน: models/market_occupancy/tuned/selected_models.joblib
แหล่งผล: reports/market_occupancy/tuning และ evaluation