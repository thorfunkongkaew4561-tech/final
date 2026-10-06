# Notebooks

Notebook ใช้สำหรับ EDA การทดลอง และสรุปผล แต่โค้ดที่ต้องเรียกซ้ำควรย้ายไปไว้ใน `src/kaverentai/`

| ลำดับ | ชื่อไฟล์ | ผู้รับผิดชอบ |
|---|---|---|
| 1 | `01_common_data_quality.ipynb` | ทอฝัน |
| 2 | `02_market_occupancy_eda.ipynb` — EDA เตรียมข้อมูล ฝึก ประเมิน และจูนของข้อ 2 | ทอฝัน |
| 4 | `04_rental_price_eda.ipynb` | อาทิตยา |
| 6 | `06_final_results.ipynb` — สรุปข้อ 1 และข้อ 2 แยกส่วน | อาทิตยา และทอฝันช่วยตรวจ |

`02_market_occupancy_eda.ipynb` เป็น Notebook หลักสำหรับ Market & Occupancy Forecasting โดยรวมงานในไฟล์เดียวตามรูปแบบไฟล์ 04 ใช้ข้อมูลใน `data/processed/` และแบ่งเป็นสี่ส่วน:

- ส่วนที่ 1: ตรวจข้อมูลและทำ EDA จำนวน 12 ขั้นตอน
- ส่วนที่ 2: เตรียมข้อมูลสำหรับ SARIMA, SARIMAX และ Random Forest จำนวน 12 ขั้นตอน
- ส่วนที่ 3: ฝึกและประเมิน 3 โมเดลกับ 2 baseline จำนวน 12 ขั้นตอน พร้อมตาราง MAE/RMSE และกราฟ
- ส่วนที่ 4: จูนพารามิเตอร์ด้วย 4 origins ภายใน Train และเปรียบเทียบ Validation ก่อน/หลัง จำนวน 10 ขั้นตอน

Notebook 02 ปรับโค้ดสำหรับนักศึกษาปี 4 โดยแยก commands ที่ต่อกันยาวเป็นทีละบรรทัด ใช้เงื่อนไข `==`, `<=` และ for loop ที่เห็นลำดับชัดเจน เพิ่มคอมเมนต์และส่วนอธิบายศัพท์ก่อนเริ่ม รวม 61 code cells หลังแยก cell ที่ทำหลายงาน ผลข้อมูล modeling และตารางคะแนนตรงกับฉบับเดิม อ่าน [คู่มืออ่านโค้ดข้อ 2](../docs/objective2_code_guide.md) เพื่อไล่จาก Notebook ไปยังไฟล์ features/train/models/tuning

รันจากต้นจนจบด้วย Run All ได้ ทั้งการเปิดจากโฟลเดอร์หลักหรือ `notebooks/` ผลกราฟ ตาราง และสรุปอยู่ใน `reports/market_occupancy/eda/` การตรวจโครงสร้างครอบคลุมทั้งชุด แต่การสำรวจแนวโน้ม ฤดูกาล และความสัมพันธ์ใช้เฉพาะ Train

รันและบันทึกผลจาก command line ได้เช่นกัน:

```powershell
python scripts/analysis/run_market_occupancy_eda.py
```

ส่วนที่ 2 เตรียมชุดเปรียบเทียบ Naïve/Seasonal Naïve ด้วย โค้ดที่เรียกซ้ำอยู่ใน `src/kaverentai/features/market_occupancy_features.py` ข้อมูลที่สร้างอยู่ใน `data/modeling/market_occupancy/` และสรุปใน `reports/market_occupancy/features/`

ส่วนที่ 3 ใช้พารามิเตอร์คงที่สำหรับการทดลองรอบแรก ยังไม่ใช่ผลจูน Hyperparameters ครบถ้วน ช่วง 1/4/12 สัปดาห์และฤดูกาล 52 สัปดาห์เป็นค่าตั้งต้น ก่อน fit แต่ละรอบต้องจำกัดคำตอบให้ทราบแล้ว ณ origin และไม่เกิน cutoff ของชุดนั้น เลือกจาก Validation MAE บนแถวร่วมกันครบ 5 วิธี แล้วล็อกก่อน Test ใช้ Test ประเมินเท่านั้น ข้อมูลจริงที่ทยอยทราบถึง origin ใช้ update state/input ได้ แต่ไม่ใช้ Test fit coefficients

โค้ดฝึกที่ใช้ซ้ำอยู่ใน `src/kaverentai/models/market_occupancy_forecasting.py` ผลอยู่ใน `reports/market_occupancy/evaluation/` โมเดลอยู่ใน `models/market_occupancy/` คำสั่งแยกสำหรับรันส่วนฝึกหลังเตรียมข้อมูลแล้ว:

```powershell
python src/kaverentai/models/train_market_occupancy.py
```

Cache ตรวจ fingerprint ของโค้ด พารามิเตอร์ และข้อมูล หากตรงกันจะโหลดผลเดิมแทนการเปิด Test ซ้ำ

ไฟล์จูนข้อ 2 อยู่ข้างไฟล์จูนราคาเช่าใน `src/kaverentai/models/tune_market_occupancy.py`:

```powershell
python src/kaverentai/models/tune_market_occupancy.py
```

รอบจูนใช้ 3 candidates ต่อ family โดยคงฤดูกาล/differencing ไว้ เลือกพารามิเตอร์จาก TrainCV เท่านั้น ผลอยู่ใน `reports/market_occupancy/tuning/` และโมเดลรอบจูนใน `models/market_occupancy/tuned/` ผลก่อน/หลังใช้แถวเดียวกันและ origin ของ Validation ต้องเกิดหลังคำตอบ fold จูนสุดท้ายทราบแล้ว (25 พฤศจิกายน 2025) Test รอบแรกเคยถูกดูแล้ว ส่วนที่ 4 จึงไม่ประเมิน Test ของโมเดลจูนซ้ำโดยอัตโนมัติ และยังไม่มี final holdout ใหม่

Notebook 03 เดิมเก็บไว้ใน `archive/03_market_occupancy_features.ipynb` เพื่อรักษาฉบับก่อนรวม ให้ใช้และแก้ Notebook หลักสำหรับงานต่อไป

## สรุปผลข้อ 2 ในไฟล์ 06

ส่วนที่ 2 ของ `06_final_results.ipynb` มี 11 ขั้นตอน โหลดผลที่บันทึกไว้จากรอบฝึก/จูน ไม่ฝึกซ้ำ แสดง 5 วิธีบน Validation หลังจูน ผู้ชนะ 12 งาน พารามิเตอร์ TrainCV ผลก่อน/หลังบนแถวเดียวกัน กราฟ MAE และตัวอย่าง rolling-origin occupancy ผล Test แสดงแยกเป็นรอบแรกก่อนจูน โมเดลหลังจูนยังไม่มี final holdout ใหม่

ส่วนข้อ 2 ปรับให้อ่านทีละขั้นสำหรับนักศึกษาปี 4: แยกเตรียมเครื่องมือ กำหนดโฟลเดอร์ และโหลดตารางเป็นคนละ cell ใช้ชื่อตัวแปรตามข้อมูลที่เก็บ คำสั่งกรอง/เรียง/จับคู่แยกบรรทัด ใช้ for loop และ if/elif ในการอธิบายผลก่อน–หลัง มีคอมเมนต์ไทยและความหมายของ target/horizon/MAE รวม 15 code cells ในส่วนข้อ 2 รันทั้งไฟล์ได้ 21 code cells โดยคะแนนและตาราง CSV ตรงกับฉบับเดิม

ตาราง กราฟ และสรุปภาษาไทยส่งออกใน `reports/market_occupancy/final_results/` ถ้าไฟล์ราคาเช่าของส่วนที่ 1 ขาด Notebook จะแจ้งชื่อไฟล์และข้ามตาราง/กราฟส่วนนั้น ข้อความคะแนนราคาเช่าเดิมยังต้องตรวจจากไฟล์ผลจริง

```powershell
python scripts/analysis/run_market_occupancy_eda.py --notebook notebooks/06_final_results.ipynb
```

แต่ละคนสร้างและแก้เฉพาะ Notebook ของตัวเอง เพื่อลดปัญหา Git conflict
