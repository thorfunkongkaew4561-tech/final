# การพยากรณ์สภาวะตลาดและอัตราการเข้าพักล่วงหน้า

วัตถุประสงค์ข้อ 2: เพื่อพัฒนาโมเดลพยากรณ์สภาวะตลาดและอัตราการเข้าพักล่วงหน้า (Market & Occupancy Forecasting)

## ขอบเขตและผลลัพธ์

พยากรณ์ระดับโครงการรายสัปดาห์ โดยใช้ข้อมูลถึงวันออกรายงาน (forecast origin) และคาดการณ์ล่วงหน้า 1, 4 และ 12 สัปดาห์ สภาวะตลาดในรุ่นแรกหมายถึงจำนวนผู้ค้นหา (`n_searchers`), จำนวนประกาศเปิด (`n_listings_open`) และค่ามัธยฐานราคาเสนอเช่า (`median_asking_rent`) ส่วนอัตราการเข้าพักใช้ `occupancy` เป็นสัดส่วน 0–1 ผลแต่ละตัวแปรต้องรายงานแยกกัน ไม่ตีความเป็นดัชนีเศรษฐกิจทั้งหมด

## ข้อมูลและการเตรียมตาราง

- ใช้ `weekly_market_cleaned.csv` เป็นตารางหลัก หนึ่งแถวต่อ `project_id` และ `date`
- เชื่อม `projects_cleaned.csv` เพื่อเพิ่มคุณลักษณะโครงการ ส่วน `units` และ `leases` ใช้ตรวจสอบความหมายของจำนวนห้องและการเข้าพัก
- ตรวจสัปดาห์ที่ขาด แถวซ้ำ ค่า occupancy นอกช่วง และค่าจำนวน/ราคาที่ติดลบ ไม่เติมข้อมูลโดยใช้ค่าจากอนาคต
- ต้องยืนยันว่า occupancy มีตัวหารเป็นห้องที่พร้อมให้เช่าหรือห้องทั้งหมด และ `n_units_leased` หมายถึงห้องที่กำลังเช่าหรือสัญญาใหม่ ก่อนสร้าง target หรือคำนวณรายได้ ห้ามถือว่าคอลัมน์นี้เป็นจำนวนสัญญาใหม่โดยอัตโนมัติ
- สร้าง lag 1, 4, 12 สัปดาห์ และค่าเฉลี่ยย้อนหลังจากแต่ละโครงการ พร้อมฤดูกาลที่ทราบล่วงหน้า ทุก feature ใช้ข้อมูลที่มีอยู่ ณ forecast origin
- สร้าง target ของแต่ละ horizon จากวันที่จริง ไม่ใช้การเลื่อนแถวข้ามสัปดาห์ที่ขาด ตาราง modeling ต้องมี `forecast_origin`, `target_date`, `horizon_weeks`, `project_id`

## การทดลองและประเมิน

ทดลองรอบแรก 3 โมเดล: SARIMA, SARIMAX และ Random Forest Regressor พร้อม 2 baseline: Naïve และ Seasonal Naïve ใน Notebook 02 ส่วนที่ 3 ใช้พารามิเตอร์คงที่ที่ระบุใน `SETTINGS` ของ `src/kaverentai/models/market_occupancy_forecasting.py` ไม่ใช่ผลจูนพารามิเตอร์ครบถ้วน SARIMA/SARIMAX ใช้อนุกรมเวลาแยกโครงการ ส่วน Random Forest รวมข้อมูลหลายโครงการและใช้ lag features

ส่วนที่ 2 ของ Notebook หลัก เตรียมข้อมูลแล้วใน `../data/modeling/market_occupancy/` ทดลองฤดูกาล 52 สัปดาห์และเกณฑ์อย่างน้อย 104 จุดที่มี y สำหรับชุดเปรียบเทียบหลัก เกณฑ์นี้เป็นข้อกำหนดเริ่มต้นของโครงงานที่ยังต้องตรวจการลู่เข้าและ Validation ไม่ใช่มาตรฐานที่รับประกันผลของโมเดล ให้รายงานโครงการประวัติสั้นแยก และเปรียบเทียบทุกวิธีบนชุด project/origin/target/horizon เดียวกันที่ใช้ได้จริง

SARIMAX แบบแยก horizon h ใช้ตัวแปรตลาด ณ t−h ประกอบ y ณ t และตัวแปรปฏิทินที่รู้ล่วงหน้า ต้องส่ง exog ครบทุกก้าวตั้งแต่ origin+1 จนถึง origin+h โดยไม่ใช้ข้อมูลตลาดจริงหลัง origin คงราคา target ที่ว่างไว้ เติมราคาเฉพาะ input ด้วย forward fill ภายในโครงการ หากยังมี input ว่างให้ fit imputer เฉพาะชุดฝึกของแต่ละรอบ

ใช้ Train ถึงปี 2025, Validation มกราคม–มีนาคม 2026 และ Test เมษายน–มิถุนายน 2026 โดยจัดชุดตาม **target_date** ของแต่ละ horizon ทุก target ที่ใช้ฝึกต้องเกิดและทราบแล้ว ณ forecast origin ของรอบประเมิน การอยู่ใน Train ไม่ได้หมายความว่าใช้ได้ทันที: กรอง `target_date <= forecast_origin` ด้วย `training_available_at_origin` ก่อน fit อีกครั้ง โดยเฉพาะ origin ของ horizon ยาวที่อยู่ก่อนสิ้นปี 2025 แบ่งทุกโครงการตามช่วงวันเดียวกัน และใช้ rolling-origin validation ภายใน Train สำหรับจูน preprocessing ต้อง fit บน Train ที่ทราบแล้วของแต่ละรอบเท่านั้น

เลือกโมเดลจาก Validation MAE แยกตาม target และ horizon รายงาน MAE/RMSE เทียบ baseline และแยกโครงการ สำหรับ occupancy ให้รายงานความคลาดเคลื่อนเป็นจุดเปอร์เซ็นต์ หลีกเลี่ยง MAPE เมื่อ target เป็นศูนย์ เปิด Test หลังล็อกวิธีเท่านั้น ช่วงพยากรณ์จะแสดงได้เมื่อมีวิธีสร้างและตรวจ coverage แล้ว

ในการทดลองรอบแรก พารามิเตอร์ Validation fit จากข้อมูลที่ทราบถึง `min(origin, train_end)` ส่วน Test fit ถึง `min(origin, validation_end)` หลังล็อกโมเดลแล้ว ค่าจริงที่ทราบหลัง fit cutoff แต่ก่อน origin ใช้ update state ของอนุกรมเวลาและสร้าง RF input เท่านั้น ไม่ใช้ Test fit coefficients หรือ preprocessing เปรียบเทียบหลักเฉพาะแถวร่วมกันครบ 5 วิธี และบันทึก failures, convergence, จำนวนแถวที่ใช้ และการปรับผลเข้าสู่ขอบเขตเดียวกันทุกวิธี

การเลือกจาก Validation ทั้งชุดพร้อมใช้ ณ 31 มีนาคม 2026 ดังนั้น Test ต้องมี `forecast_origin >= 2026-03-31` เพิ่มจากกฎ target_date เพียงอย่างเดียว เพื่อไม่ใช้การเลือกโมเดลจากอนาคต โดยเฉพาะ horizon ยาว ในข้อมูลที่จบ 23 มิถุนายน 2026 ผล Test ของ horizon 12 สัปดาห์มี origin เดียว (31 มีนาคม) จึงยังประเมินความสม่ำเสมอข้ามเวลาไม่ได้ ต้องเพิ่มข้อมูลหลังมิถุนายนหรือออกแบบ nested rolling selection หากต้องการหลาย origin

SARIMA/SARIMAX ทดลอง `(1,0,0)(0,1,0)[52]` ด้วย `simple_differencing=True` เพื่อใช้ state-space ขนาดเล็ก คืนผลพยากรณ์จากความต่างรายปีเป็นหน่วยจริงด้วย anchor ที่ target_date−52 สัปดาห์ซึ่งทราบแล้ว ณ origin วิธีนี้รองรับ horizon ไม่เกิน 52 สัปดาห์ใน implementation รอบนี้ ไม่ใช้ output ความต่างไปคิดคะแนนแทนระดับจริง

## การจูนพารามิเตอร์

Notebook 02 ส่วนที่ 4 และ `src/kaverentai/models/tune_market_occupancy.py` จูน SARIMA, SARIMAX และ Random Forest ด้วย 4 forecast origins ภายใน Train: 31 ธันวาคม 2024, 1 เมษายน 2025, 1 กรกฎาคม 2025 และ 2 กันยายน 2025 แต่ละรอบใช้คำตอบที่ทราบแล้ว ณ origin เท่านั้น เลือกจากค่าเฉลี่ย MAE ของ 4 folds โดย candidate ต้องคืนผลครบ แล้วเลือก family อีกครั้งจาก Validation บนแถวร่วมกันครบ 5 วิธี

ทดลอง 3 candidates ต่อ family รวม 108 ชุดคะแนน SARIMA/SARIMAX ทดลอง order `(1,0,0)`, `(2,0,0)`, `(1,0,1)` โดยคง seasonal order `(0,1,0,52)` ส่วน Random Forest เปรียบเทียบชุด n_estimators, max_depth, min_samples_leaf และ max_features ที่กำหนดไว้ใน GRIDS เป็นการค้นหาแบบจำกัด ไม่ใช่ exhaustive search

คำตอบ CV สุดท้ายสำหรับ horizon 12 สัปดาห์ทราบวันที่ 25 พฤศจิกายน 2025 จึงกรอง Validation ให้ origin ไม่ก่อนวันนั้น การเปรียบเทียบก่อน/หลังใช้แถวเดียวกันทั้งสองรอบ โดย horizon 12 มี 68 กรณีต่อ target เมื่อทุกวิธีคืนผลครบ ผล Validation ของ 36 งานโมเดลดีขึ้น 13 งาน แย่ลง 10 งาน และเท่าเดิม 13 งาน การจูนจึงไม่ได้รับประกันว่าจะดีขึ้นทุกงาน ผู้ชนะ occupancy คือ SARIMA ที่ 1 สัปดาห์ และ SARIMAX ที่ 4/12 สัปดาห์ มี MAE 0.4920, 0.9809 และ 1.3009 จุดเปอร์เซ็นต์ตามลำดับ

ผลอยู่ใน `reports/market_occupancy/tuning/` โมเดลรอบจูนใน `models/market_occupancy/tuned/` เก็บแยกจากรอบแรก Test รอบแรกเคยถูกดูแล้ว รอบจูนจึงไม่ประเมิน tuned Test ซ้ำโดยอัตโนมัติ และยังต้องมีข้อมูลอนาคตใหม่สำหรับ final holdout ที่เป็นอิสระ

## การส่งมอบและการเชื่อมระบบ

เพื่อนร่วมโครงงานรับผิดชอบการฝึกและประเมินวัตถุประสงค์ข้อ 2 เช่นเดิม ส่ง pipeline ใน `models/integration/market_occupancy_model.joblib`, metadata ใน `models/integration/market_occupancy_metadata.json` และผลใน `reports/market_occupancy/` โดย metadata ระบุ targets, features, horizons, cutoff, หน่วย, นิยาม occupancy, วิธีประเมิน และเวอร์ชัน

ผลการทดลองปัจจุบันบันทึกใน `reports/market_occupancy/evaluation/` โมเดลที่เลือกอยู่ใน `models/market_occupancy/selected_models.joblib` และ metadata ในโฟลเดอร์เดียวกัน พารามิเตอร์ fit ถึง Validation end ไม่ใช้ Test fit coefficients bundle เก็บทั้ง pipeline/พารามิเตอร์อนุกรมเวลา/กฎ baseline ตามผู้ชนะ และยังไม่ใช่ API สำหรับเว็บ ตำแหน่ง `integration/` ยังเป็นงานส่งมอบขั้นถัดไป

ตารางผลที่ใช้ร่วมกันมี `project_id`, `forecast_origin`, `target_date`, `horizon_weeks`, `predicted_occupancy`, `predicted_n_searchers`, `predicted_n_listings_open`, `predicted_median_asking_rent` ประเมินจุดหลักที่ horizon 1, 4 และ 12 สัปดาห์ แต่ผลสำหรับ What-if ต้องส่ง occupancy ทุกสัปดาห์ตั้งแต่ 1 จนถึงสิ้นสุดกรอบจำลอง เป็นเส้นทางต่อเนื่องของโครงการเดียว ไม่รวม horizon ที่เว้นช่วงมาบวกเป็นรายได้

Price Engine แสดงตลาดล่วงหน้าเป็นบริบทประกอบราคา การนำค่าพยากรณ์เข้าโมเดลราคาโดยตรงต้องสร้าง feature และฝึกใหม่ก่อน ส่วน What-if ใช้ราคา × จำนวนห้องพร้อมให้เช่า × occupancy ที่พยากรณ์ × สัดส่วนเดือนของแต่ละสัปดาห์ หักส่วนลดรวมที่ผู้ใช้ระบุเพื่อประมาณรายได้ในกรอบเวลาเดียวกัน

การเปลี่ยนราคาในรุ่นแรกใช้ occupancy เส้นทางเดิม จึงเป็นการคำนวณรายได้ภายใต้สมมติฐาน occupancy คงเดิมระหว่างสถานการณ์ หากต้องการให้ occupancy เปลี่ยนตามราคา ต้องพัฒนาและตรวจสอบแบบจำลองการตอบสนองต่อราคาเพิ่ม ไม่แปลง occupancy เป็นระยะเวลาปล่อยเช่าของห้องรายตัว

Web Application วางโครงสร้างเป็นหน้าแนะนำราคา หน้าพยากรณ์ตลาดและอัตราการเข้าพัก หน้า What-if และหน้าสรุปผล โดยหน้า forecast แสดงโครงการ วันออกรายงาน ช่วงพยากรณ์ แนวโน้มแต่ละตัวแปร และข้อจำกัดของข้อมูลจำลอง

## สถานะ

Notebook หลัก `../notebooks/02_market_occupancy_eda.ipynb` รวมสี่ส่วน: EDA เตรียมข้อมูล ฝึก/ประเมิน และจูนพารามิเตอร์ รวม 61 code cells หลังปรับให้อ่านทีละขั้นสำหรับนักศึกษาปี 4 ผล EDA อยู่ใน `../reports/market_occupancy/eda/` ผลเตรียมข้อมูลใน `../reports/market_occupancy/features/` ผลรอบแรกใน `../reports/market_occupancy/evaluation/` และผลจูนใน `../reports/market_occupancy/tuning/` ชุดเปรียบเทียบหลักครอบคลุมแถวที่ทั้ง 5 วิธีคืนผลครบ และมีรายงานกลุ่มประวัติสั้นแยก การเชื่อมเว็บและเส้นทาง occupancy ทุกสัปดาห์ 1–12 สำหรับ What-if ยังเป็นงาน Todo

การตรวจข้อมูลครั้งนี้พบว่า occupancy ตรงกับ `n_units_leased / total_units` ทุกแถว และ `n_units_leased` หมายถึงห้องที่มีผู้เช่าอยู่ตาม Data Dictionary ใน Notebook 01 ส่วนการนับจาก leases ยังไม่ตรง snapshot ตลาดบางช่วง จึงไม่ใช้ leases สร้าง target ทดแทนก่อนยืนยันที่มาของข้อมูล นอกจากนี้โครงการ 8, 16 และ 18 มี Train เพียงหนึ่งสัปดาห์ ต้องกำหนดวิธีรองรับประวัติสั้นในขั้นฝึกโมเดล
