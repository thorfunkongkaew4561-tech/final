# ผลฝึกและประเมิน Market & Occupancy Forecasting

ใช้ข้อมูลจำลอง ทดลองพารามิเตอร์รอบแรกคงที่ ไม่ใช่ผลจูนพารามิเตอร์ครบถ้วน
เลือกจาก Validation MAE บนแถวร่วมกันครบ 5 วิธี แล้วล็อกก่อนประเมิน Test

| Target | Horizon | วิธีที่เลือก | Validation MAE | Test MAE | หน่วย |
|---|---:|---|---:|---:|---|
| median_asking_rent | 1 | Naive | 123.0769 | 216.0764 | baht/month |
| median_asking_rent | 4 | RandomForest | 263.7193 | 332.4035 | baht/month |
| median_asking_rent | 12 | RandomForest | 291.0398 | 521.4356 | baht/month |
| n_listings_open | 1 | SARIMA | 3.9876 | 6.7370 | count |
| n_listings_open | 4 | SARIMA | 8.5354 | 15.8782 | count |
| n_listings_open | 12 | SeasonalNaive | 9.9310 | 7.5000 | count |
| n_searchers | 1 | SARIMA | 4.3562 | 9.8734 | count |
| n_searchers | 4 | RandomForest | 3.5566 | 11.6749 | count |
| n_searchers | 12 | RandomForest | 4.8007 | 6.7442 | count |
| occupancy | 1 | SARIMA | 0.4920 | 0.8721 | percentage points |
| occupancy | 4 | SARIMAX | 0.9809 | 1.8175 | percentage points |
| occupancy | 12 | SARIMAX | 0.9907 | 2.1641 | percentage points |

แถวที่ไม่คืนผลพยากรณ์: 0 ตรวจ forecast_failures.csv และ fit_diagnostics.csv

ผลหลักใช้ประวัติอย่างน้อย 104 จุดที่มี y และแถวที่ครบทุกวิธี กลุ่มประวัติสั้นแสดงแยกใน short_history_metrics
ค่าที่ทราบหลัง fit cutoff แต่ก่อน origin ใช้ update state/inputs เท่านั้น ไม่ใช้ Test fit coefficients
โมเดลเลือกต่างกันได้ตาม target/horizon และ baseline สามารถชนะได้ ไม่มีวิธีที่ดีที่สุดทุกกรณี
ยังไม่เชื่อม Web Application และยังไม่สร้างเส้นทาง occupancy ทุกสัปดาห์ 1–12 สำหรับ What-if
Test origin เริ่มหลังวันล็อก Validation (31 มีนาคม 2026); horizon 12 มี origin เดียว จึงต้องเพิ่มข้อมูลเพื่อประเมินความสม่ำเสมอ
ไม่มีการอ้างผลจากข้อมูลจำลองเป็นประสิทธิภาพในธุรกิจจริง