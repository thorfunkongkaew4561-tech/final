# ผลจูน Market & Occupancy Forecasting

ใช้ข้อมูลจำลอง จูนพารามิเตอร์จาก TrainCV เท่านั้น แล้วเลือกโมเดลจาก Validation

- 3 โมเดล × 3 candidates × 4 targets × 3 horizons = 108 ชุดคะแนน CV
- CV origins: ['2024-12-31', '2025-04-01', '2025-07-01', '2025-09-02']; ทุก target_date ไม่เกิน 2025-12-31
- SARIMA/SARIMAX จูน p และ q โดยคง d=0, seasonal_order=(0,1,0,52)
- RF จูน n_estimators, max_depth, min_samples_leaf และ max_features
- Validation MAE ของ 36 งานโมเดล: ดีขึ้น 13, แย่ลง 10, เท่าเดิม 13
- ไม่ใช้ Test เลือกพารามิเตอร์ และไม่ประเมิน Test ของโมเดลจูนซ้ำในรอบนี้
- Test รอบแรกเคยถูกดูแล้ว จึงต้องมีข้อมูลอนาคตใหม่สำหรับ final holdout ที่เป็นอิสระ
- Validation origin ต้องไม่ก่อน 2025-11-25 เมื่อคำตอบ CV สุดท้ายทราบแล้ว

| Target | Horizon | วิธีที่เลือกหลังจูน | Validation MAE | หน่วย |
|---|---:|---|---:|---|
| median_asking_rent | 1 | Naive | 123.0769 | baht/month |
| median_asking_rent | 4 | RandomForest | 262.0789 | baht/month |
| median_asking_rent | 12 | RandomForest | 253.0383 | baht/month |
| n_listings_open | 1 | SARIMA | 3.9876 | count |
| n_listings_open | 4 | SARIMA | 8.5354 | count |
| n_listings_open | 12 | SeasonalNaive | 12.6912 | count |
| n_searchers | 1 | SARIMA | 4.4084 | count |
| n_searchers | 4 | RandomForest | 3.5657 | count |
| n_searchers | 12 | SARIMA | 3.5294 | count |
| occupancy | 1 | SARIMA | 0.4920 | percentage points |
| occupancy | 4 | SARIMAX | 0.9809 | percentage points |
| occupancy | 12 | SARIMAX | 1.3009 | percentage points |

รอบนี้เป็น small-grid search บน 4 origins ไม่ใช่การค้นหาพารามิเตอร์ครบทุกแบบ
ผลก่อน/หลังใช้แถวเดียวกันทั้ง 5 วิธีในทั้งสองรอบ และ candidate ที่คืนผลไม่ครบไม่ถูกเลือก
โมเดลรอบแรกยังอยู่ที่ models/market_occupancy ส่วนรอบจูนอยู่ใน models/market_occupancy/tuned