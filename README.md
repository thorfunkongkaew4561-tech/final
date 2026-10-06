# การพัฒนาระบบปัญญาประดิษฐ์และระบบสนับสนุนการตัดสินใจสำหรับการบริหารการปล่อยเช่าคอนโดมิเนียมในรูปแบบเว็บแอปพลิเคชัน

โครงงานนี้พัฒนาระบบสนับสนุนการตัดสินใจสำหรับการบริหารการปล่อยเช่าคอนโดมิเนียม โดยใช้ข้อมูลจำลองเพื่อพัฒนาแบบจำลองทางสถิติ โมเดลแนะนำราคาค่าเช่า ระบบจำลองสถานการณ์ และเว็บแอปพลิเคชัน ชื่อ `KaveRentAI` ยังคงใช้เป็นชื่อแพ็กเกจภายในโค้ดเพื่อไม่ให้กระทบการ import เดิม

> ข้อมูลทั้งหมดเป็นข้อมูลจำลอง ห้ามอ้างอิงตัวเลขในชุดข้อมูลว่าเป็นผลประกอบการจริงของบริษัท

## วัตถุประสงค์

1. เพื่อพัฒนาโมเดลแนะนำราคาค่าเช่าที่เหมาะสม (Rental Price Recommendation) โดยพิจารณาจากปัจจัยแวดล้อมและสภาวะตลาด
2. เพื่อพัฒนาโมเดลพยากรณ์สภาวะตลาดและอัตราการเข้าพักล่วงหน้า (Market & Occupancy Forecasting)
3. เพื่อพัฒนาระบบ What-if Simulation สำหรับจำลองสถานการณ์การปรับราคาและประเมินผลกระทบต่อรายได้
4. เพื่อพัฒนาระบบสนับสนุนการตัดสินใจด้วย AI ผ่าน Web Application

## ขอบเขตโค้ดใน Repository นี้

Repository นี้มีทั้งส่วน Rental Price Recommendation และ Market & Occupancy Forecasting วัตถุประสงค์ข้อ 2 รวม EDA เตรียมข้อมูล ฝึก/ประเมิน และจูนไว้ใน `notebooks/02_market_occupancy_eda.ipynb` โค้ดเรียกซ้ำอยู่ใน `src/kaverentai/models/market_occupancy_forecasting.py` และไฟล์จูน `src/kaverentai/models/tune_market_occupancy.py` ทดลอง SARIMA, SARIMAX, Random Forest และสอง baseline รอบจูนเลือกพารามิเตอร์จาก TrainCV และเลือก family จาก Validation ผลรอบจูนยังไม่มี final holdout ใหม่ การเชื่อมผลพยากรณ์ทุกสัปดาห์เข้ากับ What-if/Web Application เป็นขั้นถัดไป

โมเดลราคาเช่าที่เปรียบเทียบมี 5 วิธี ได้แก่ Stepwise Multiple Linear Regression, Gradient Boosting Regressor, Random Forest Regressor, K-Nearest Neighbors Regressor และ Artificial Neural Network โดยใช้ Validation MAE เป็นเกณฑ์หลักในการเลือกโมเดล

## โครงสร้างโปรเจกต์

```text
KaveRentAI/
|-- data/
|   |-- raw/              # ข้อมูลต้นฉบับ ห้ามแก้โดยตรง
|   |-- processed/        # ข้อมูลที่ทำความสะอาดแล้ว
|   `-- modeling/         # ตารางที่สร้างเพื่อฝึกโมเดล
|-- notebooks/            # EDA และการทดลอง
|-- src/kaverentai/       # โค้ดที่เรียกใช้ซ้ำ
|-- configs/              # ค่าตั้งต้นของโมเดลและการแบ่งข้อมูล
|-- models/               # โมเดลราคาเช่าและโมเดล forecast (ไม่เก็บไฟล์ joblib ใน Git)
|-- reports/              # กราฟ คะแนน และตารางที่สร้างจากโค้ด
|-- references/           # เปเปอร์และแบบฟอร์มที่ใช้อ้างอิง
|-- deliverables/         # รายงานฉบับปัจจุบัน
|-- scripts/reporting/    # สคริปต์สร้างรายงาน
|-- app/                  # Streamlit Web Application
|-- tests/                # การทดสอบโค้ด
`-- docs/                 # คู่มือข้อมูลและเอกสารโครงการ
```

## การติดตั้ง

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -e .
```

## เริ่มใช้งาน

ก่อนเริ่มพัฒนา ให้เปิด [TASKS.md](TASKS.md) เพื่อดูงาน ผู้รับผิดชอบ และสถานะล่าสุด

โหลดข้อมูลที่ทำความสะอาดแล้ว:

```python
from kaverentai.data.load_data import load_all_data

data = load_all_data(cleaned=True)
listings = data["listings"]
leases = data["leases"]
```

ตรวจสอบโครงสร้างข้อมูล:

```powershell
python -m kaverentai.data.validate_data
```

เปิด Web Application:

```powershell
streamlit run app/Home.py
```

รันทดสอบ:

```powershell
pytest
```

## การแบ่งข้อมูลตามเวลา

- Train: ปี 2023-2025
- Validation: มกราคม-มีนาคม 2026
- Test: เมษายน-มิถุนายน 2026

ห้ามใช้ Test ระหว่างเลือกโมเดลหรือปรับพารามิเตอร์

## การแบ่งงาน

- เพื่อนร่วมโครงงาน: Data Quality และ Market & Occupancy Forecasting
- อาทิตยา: Time Split, Rental Price Recommendation, Price Engine, What-if Integration และ Web Application

ทั้งสองคนทำ EDA ใน Notebook แยกกัน และนำโค้ดที่ต้องใช้ร่วมกันมาไว้ใน `src/kaverentai/`

## เอกสารเพิ่มเติม

- [รายการงานและผู้รับผิดชอบ](TASKS.md)
- [วิธีทำงานร่วมกันผ่าน Git](CONTRIBUTING.md)
- [คำอธิบายโฟลเดอร์ข้อมูล](data/README.md)
- [คำอธิบาย Notebook และผู้รับผิดชอบ](notebooks/README.md)
- [ขอบเขตและกติกาการทำงาน](docs/project_scope.md)
- [รายการเอกสารทั้งหมด](docs/README.md)
- [รายงานโครงงานฉบับปัจจุบัน](deliverables/Condo_Rental_AI_Project_Report.docx)
- [เปเปอร์ที่ใช้อ้างอิง](references/papers/rental_price/)

## โครงสร้างตามวัตถุประสงค์ใหม่

ข้อมูลรายสัปดาห์ → Market & Occupancy Forecasting → แนวโน้มตลาดและ occupancy ล่วงหน้า → What-if รายได้ระดับโครงการ → Web Application โดย Rental Price Recommendation เป็นอีกส่วนที่ใช้ประกอบการตัดสินใจ

ดู [ขอบเขต ข้อมูล การประเมิน และการเชื่อมระบบ](docs/market_occupancy_forecasting.md) โมเดล forecast ยังต้องพัฒนา What-if รุ่นนี้รับผลพยากรณ์รายสัปดาห์ที่ส่งเข้ามา และใช้ occupancy คงเดิมเมื่อเปลี่ยนราคา จนกว่าจะมีแบบจำลองการตอบสนองต่อราคาที่ผ่านการตรวจสอบ
