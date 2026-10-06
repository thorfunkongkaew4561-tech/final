# Data

## `raw/`

ข้อมูลต้นฉบับจำนวน 5 ตาราง ห้ามแก้ไฟล์ด้วยมือ หากต้องทำความสะอาดให้เขียนโค้ดแล้วบันทึกผลไปที่ `processed/`

## `processed/`

ข้อมูลที่ผ่านการทำความสะอาดแล้ว ใช้เป็นจุดเริ่มต้นของ EDA และการสร้าง Feature

## `modeling/`

ตารางที่เตรียมไว้สำหรับโมเดลราคาเช่าและการพยากรณ์ตลาด ไฟล์ในโฟลเดอร์นี้สร้างใหม่ได้จากโค้ดและจะไม่ถูกเก็บใน Git

`modeling/market_occupancy/` สร้างจาก ส่วนที่ 2 ของ Notebook หลัก:

- `sarima_weekly_series.csv` — อนุกรมเวลารายสัปดาห์แยกโครงการ คงค่า target ที่ว่าง
- `rf_<target>_h<horizon>.csv` — ตาราง features/คำตอบสำหรับ Random Forest แยก 4 targets × 3 horizons
- `sarimax_<target>_h<horizon>.csv` — ตาราง y กับตัวแปรภายนอกที่เลื่อนให้ทราบแล้ว ณ forecast origin
- `forecast_feature_metadata.json` — รายการ features วันแบ่งชุด และนโยบายค่าว่าง/ประวัติสั้น

ไฟล์เหล่านี้มีคำตอบ Validation/Test สำหรับการประเมิน ก่อน fit ต้องเลือกเฉพาะ Train ที่ target_date เกิดแล้ว ณ origin ของรอบนั้น ส่วน SARIMA ต้องตัด series ที่ date <= origin ใช้ `training_available_at_origin` ช่วยกรองตารางได้ ห้าม fit imputer/encoder/scaler จากทั้งไฟล์

ข้อมูลทั้งหมดในโปรเจกต์นี้เป็นข้อมูลจำลอง ไม่ใช่ผลประกอบการจริงของบริษัท

## ข้อมูลสำหรับวัตถุประสงค์ข้อ 2

ใช้ `processed/weekly_market_cleaned.csv` ระดับโครงการรายสัปดาห์ สร้างตาราง modeling แยก target และ horizon โดยมี forecast origin และ target date ก่อนฝึกต้องยืนยันนิยาม occupancy และ n_units_leased ดู `../docs/market_occupancy_forecasting.md`
