# ผลเตรียมข้อมูลพยากรณ์ตลาดและอัตราการเข้าพัก

ใช้ weekly_market_cleaned.csv และ projects_cleaned.csv ซึ่งเป็นข้อมูลจำลอง

- ตารางรายสัปดาห์ 2,288 แถว 18 โครงการ
- ตาราง Random Forest 12 ชุด และ SARIMAX 12 ชุด สำหรับ 4 targets × 3 horizons
- Numeric features 33 ตัว และ categorical features 3 ตัว
- ราคา target ว่าง 3 แถว ไม่ถูกเติมเป็นคำตอบ
- origin แรกของ Validation ที่ h=12 คือ 2025-10-14; มี Train 165 แถวที่ยังไม่ทราบคำตอบและต้องกันออกจากรอบนี้
- ทดลองฤดูกาล 52 สัปดาห์ และเกณฑ์ชุดเปรียบเทียบหลัก 104 จุดที่มี y; เป็นค่าตั้งต้นของโครงงานที่ยังต้องประเมิน
- โมเดลที่ตกลงทดลอง: SARIMA, SARIMAX, Random Forest; baseline: Naïve, Seasonal Naïve
- ยังไม่ได้ fit imputer, encoder, scaler หรือโมเดล และยังไม่มี MAE/RMSE

ขั้นต่อไป: สร้าง baseline และฝึกแต่ละโมเดลใน rolling-origin โดย filter target_date <= origin ก่อน fit เสมอ
ใช้ชุดประเมินร่วมกันสำหรับเปรียบเทียบหลัก และแสดงกลุ่มประวัติสั้นแยกต่างหาก
