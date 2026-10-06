"""หน้าหลักของเว็บแอปพลิเคชันระบบสนับสนุนการตัดสินใจ."""

import streamlit as st


PROJECT_NAME = (
    "การพัฒนาระบบปัญญาประดิษฐ์และระบบสนับสนุนการตัดสินใจ"
    "สำหรับการบริหารการปล่อยเช่าคอนโดมิเนียมในรูปแบบเว็บแอปพลิเคชัน"
)

st.set_page_config(
    page_title="ระบบ AI สำหรับการบริหารการปล่อยเช่าคอนโดมิเนียม",
    page_icon="📈",
    layout="wide",
)

st.title(PROJECT_NAME)
st.caption("ชื่อแพ็กเกจภายในระบบ: KaveRentAI")
st.info(
    "ระบบรุ่นแรกอยู่ระหว่างการพัฒนา และใช้ข้อมูลจำลองเพื่อการศึกษาเท่านั้น"
)

left, right = st.columns(2)
with left:
    st.markdown("### แบบจำลอง")
    st.markdown(
        "1. Rental Price Recommendation\n"
        "2. Market & Occupancy Forecasting (พัฒนาโดยเพื่อนร่วมโครงงาน)"
    )

with right:
    st.markdown("### ระบบสนับสนุนการตัดสินใจ")
    st.markdown(
        "- Price Recommendation\n"
        "- Price-based Promotions\n"
        "- What-if Simulation\n"
        "- Estimated Revenue"
    )
