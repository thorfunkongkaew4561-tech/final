# การรัน EDA และเตรียมข้อมูลตลาดกับอัตราการเข้าพัก

โค้ดวิเคราะห์หลักอยู่ใน `../../notebooks/02_market_occupancy_eda.ipynb` รวม EDA และการเตรียมข้อมูลไว้ในไฟล์เดียว อ่านและรันทีละขั้นตอนหรือ Run All ผ่าน Jupyter ได้

สคริปต์นี้ใช้ตรวจการรันทุก code cell ตามลำดับและบันทึกตาราง/กราฟลง outputs ของ Notebook โดยไม่ต้องมี Jupyter kernel เพิ่ม:

```powershell
python scripts/analysis/run_market_occupancy_eda.py
```

คำสั่งเดียวรันทั้งสี่ส่วนและบันทึก outputs ใน Notebook หลัก ข้อมูลที่เตรียมอยู่ใน `data/modeling/market_occupancy/` สรุปเตรียมข้อมูลใน `reports/market_occupancy/features/` ผลประเมินใน `reports/market_occupancy/evaluation/` และผลจูนใน `reports/market_occupancy/tuning/`

รันเฉพาะส่วนฝึกหลังเตรียมข้อมูลแล้ว:

```powershell
python src/kaverentai/models/train_market_occupancy.py
```

ต้องมี statsmodels ตาม requirements.txt โค้ดรองรับแพ็กเกจที่ติดตั้งเฉพาะโปรเจกต์ใน `.runtime-packages/` ด้วย ผล cache ตรวจ fingerprint ก่อนโหลด และต้องล็อก Validation ที่ตรงกันก่อนเปิด Test

จูนข้อ 2 ด้วย TrainCV และประเมินเฉพาะ Validation ในรอบจูน:

```powershell
python src/kaverentai/models/tune_market_occupancy.py
```

ผลจูนเก็บแยกใน `reports/market_occupancy/tuning/` และโมเดลใน `models/market_occupancy/tuned/` เพื่อรักษาผลทดลองรอบแรก

รัน Notebook สรุปผลข้อ 1 และข้อ 2 จากไฟล์ผลที่บันทึกไว้:

```powershell
python scripts/analysis/run_market_occupancy_eda.py --notebook notebooks/06_final_results.ipynb
```

ส่วนข้อ 2 ส่งออกใน `reports/market_occupancy/final_results/` ส่วนข้อ 1 จะแจ้งและข้ามตาราง/กราฟเมื่อไฟล์ผลราคาเช่าขาด โดยไม่ฝึกโมเดลซ้ำ ต้องมี dependencies วิเคราะห์ข้อมูลตาม `requirements.txt` และ IPython
