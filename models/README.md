# Model Artifacts

ไฟล์โมเดลที่ฝึกแล้ว (`.joblib`) ไม่ถูกเก็บใน Git

- `rental_price/` เก็บ Stepwise MLR, Gradient Boosting, Random Forest,
  KNN, ANN และ metadata ของ Rental Price Recommendation
- `integration/market_occupancy_model.joblib` เป็นตำแหน่งสำหรับรับไฟล์โมเดล Market & Occupancy Forecasting จากเพื่อนร่วมโครงงานเมื่อรวมระบบ
- `integration/market_occupancy_metadata.json` ระบุ features, targets, horizons, cutoff, หน่วย และนิยาม occupancy ตำแหน่งทั้งสองยังเป็นแผนการส่งมอบ ไม่มีโมเดล forecast ที่ฝึกแล้ว

`market_occupancy/selected_models.joblib` เก็บโมเดลที่เลือกจาก Validation แยก target/horizon และ `market_occupancy/model_metadata.json` เก็บตัวเลือก พารามิเตอร์ และ cutoff โมเดลอนุกรมเวลาเก็บพารามิเตอร์/ตัวแปลงสำหรับ update state ตามข้อมูลที่รู้ ณ origin ส่วน baseline เก็บประวัติและกฎพยากรณ์ ไม่ใช่ sklearn pipeline เดียวที่รับ predict ได้ทุกกรณี

ไฟล์สั่ง train อยู่ใน `src/kaverentai/models/train_market_occupancy.py` ตามรูปแบบเดียวกับ `train_rental_price.py` ส่วนฟังก์ชันฝึก/ประเมินอยู่ใน `src/kaverentai/models/market_occupancy_forecasting.py` และเรียกทีละขั้นใน Notebook 02 ส่วนที่ 3 การทดลองรอบแรกยังไม่จูนพารามิเตอร์ครบถ้วน และ bundle นี้ยังไม่เชื่อม Web Application ตำแหน่ง `integration/` ยังเป็นแผนการส่งมอบสำหรับเว็บ

รอบจูนเก็บแยกใน `market_occupancy/tuned/selected_models.joblib` และ `model_metadata.json` ของโฟลเดอร์เดียวกัน พารามิเตอร์มาจาก TrainCV และ family มาจาก Validation ยังไม่มี final holdout ใหม่หลังจูน ใช้ `src/kaverentai/models/tune_market_occupancy.py` หรือ Notebook 02 ส่วนที่ 4
