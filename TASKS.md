# งานโครงงานระบบ AI และระบบสนับสนุนการตัดสินใจสำหรับการปล่อยเช่าคอนโดมิเนียม

ไฟล์นี้ใช้ดูว่าใครต้องทำอะไร และงานแต่ละส่วนเสร็จถึงไหนแล้ว

เปลี่ยนวัตถุประสงค์ข้อ 2 เป็น Market & Occupancy Forecasting งานโมเดลใหม่นับเป็น Todo ไม่ยกสถานะงานเดิมมาเป็นผลของโมเดลใหม่ ดูรายละเอียดใน `docs/market_occupancy_forecasting.md`

## ความหมายของสถานะ

- `Todo` — ยังไม่เริ่ม
- `Doing` — กำลังทำ
- `Review` — ทำเสร็จแล้ว รออีกคนตรวจ
- `Done` — ตรวจแล้วและใช้งานได้

## เพื่อนร่วมโครงงาน: Data และ Market & Occupancy Forecasting

| งาน | ไฟล์หลัก | สถานะ |
|---|---|---|
| ตรวจคุณภาพข้อมูลทั้ง 5 ตาราง | `notebooks/01_common_data_quality.ipynb` | Review |
| ตรวจโค้ดโหลดข้อมูลที่เตรียมไว้ | `src/kaverentai/data/load_data.py` | Done |
| ตรวจโค้ดตรวจสอบข้อมูลที่เตรียมไว้ | `src/kaverentai/data/validate_data.py` | Done |
| EDA ตลาดและอัตราการเข้าพักรายสัปดาห์ | `notebooks/02_market_occupancy_eda.ipynb` | Review |
| สร้าง lag features และ targets ล่วงหน้า 1/4/12 สัปดาห์ | `notebooks/02_market_occupancy_eda.ipynb`, `src/kaverentai/features/market_occupancy_features.py` | Review |
| ฝึก SARIMA, SARIMAX, Random Forest และ 2 baseline | Notebook 02 ส่วนที่ 3, `src/kaverentai/models/train_market_occupancy.py`, `market_occupancy_forecasting.py` | Review |
| ประเมิน rolling-origin แยก target และ horizon เทียบ baseline | `reports/market_occupancy/evaluation/` — ล็อก Validation ก่อน Test origin | Review |
| จูนพารามิเตอร์ข้อ 2 ด้วย TrainCV และเทียบ Validation ก่อน/หลัง | `src/kaverentai/models/tune_market_occupancy.py`, Notebook 02 ส่วนที่ 4 | Review |
| สรุปผลวัตถุประสงค์ข้อ 2 สำหรับรายงาน | Notebook 06 ส่วนที่ 2, `reports/market_occupancy/final_results/` | Review |
| ปรับโค้ดข้อ 2 ให้อ่านตามขั้นตอนสำหรับนักศึกษาปี 4 | Notebook 02/06, features/train/models/tuning, `docs/objective2_code_guide.md` | Review |
| ส่งมอบ pipeline, metadata และตารางผลพยากรณ์ | `models/integration/` (วางแผน) | Todo |

## อาทิตยา: วัตถุประสงค์ข้อ 1 และ Decision System

| งาน | ไฟล์หลัก | สถานะ |
|---|---|---|
| ตรวจโค้ดแบ่ง Train/Validation/Test ที่เตรียมไว้ | `src/kaverentai/data/split_data.py` | Done |
| EDA ราคาค่าเช่า | `notebooks/04_rental_price_eda.ipynb` | Done |
| สร้าง Feature ราคาค่าเช่า | `src/kaverentai/features/rental_price_features.py` | Done |
| สร้างและเปรียบเทียบโมเดลราคาเช่า 5 โมเดล | `src/kaverentai/models/train_rental_price.py` | Done |
| สร้างตัวประเมินโมเดล Regression | `src/kaverentai/models/evaluate_regression.py` | Done |
| สร้างระบบแนะนำราคา | `src/kaverentai/recommendation/price_engine.py` | Done |
| สร้างระบบโปรโมชั่นด้านราคา | `src/kaverentai/recommendation/promotion_engine.py` | Review |
| สร้าง What-if Simulation | `src/kaverentai/simulation/what_if.py` | Review |
| สร้างตัวคำนวณรายได้ประมาณการ | `src/kaverentai/simulation/revenue_calculator.py` | Review |
| สร้าง Web Application | `app/` | Todo |
| รวมผลลัพธ์สำหรับรายงาน | `notebooks/06_final_results.ipynb` | Done |

## ไฟล์ที่ต้องตกลงกันก่อนแก้

ไฟล์ต่อไปนี้เป็นไฟล์ส่วนกลาง หากต้องแก้ให้แจ้งอีกคนก่อน

- `README.md`
- `TASKS.md`
- `requirements.txt`
- `configs/model_config.yaml`
- `docs/project_scope.md`

## วิธีเริ่มงานแต่ละครั้ง

1. เปิด `TASKS.md`
2. หางานที่มีชื่อตัวเอง
3. เปลี่ยนสถานะของงานเป็น `Doing`
4. สร้างหรือแก้เฉพาะไฟล์ที่ระบุ
5. ทำเสร็จแล้วเปลี่ยนสถานะเป็น `Review`
6. ให้อีกคนตรวจ เมื่อผ่านแล้วจึงเปลี่ยนเป็น `Done`

## กติกาง่าย ๆ

- ไม่แก้ Notebook ไฟล์เดียวกันพร้อมกัน
- ดึงงานล่าสุดด้วย `git pull` ก่อนเริ่มทำ
- หนึ่งงานใช้หนึ่ง branch
- ทำงานเสร็จให้เปิด Pull Request เพื่อให้อีกคนตรวจ
- ห้ามแก้ CSV ใน `data/raw/` ด้วยมือ
