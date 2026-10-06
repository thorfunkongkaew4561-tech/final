"""คำนวณราคาและมูลค่าสัญญาหลังใช้โปรโมชั่น."""


SUPPORTED_PROMOTIONS = [
    "percentage_discount",
    "fixed_discount",
    "free_months",
    "introductory_discount",
    "renewal_discount",
    "keep_previous_rent",
]


def calculate_promotion(
    base_rent,
    lease_months,
    promotion_type,
    discount_value=0,
    promotion_months=0,
    is_renewal=False,
    previous_rent=None,
):
    """คำนวณส่วนลดและมูลค่าสัญญาหลังใช้โปรโมชั่น."""

    # 1. แปลงค่าที่ใช้คำนวณให้เป็นตัวเลข
    try:
        base_rent = float(base_rent)
        lease_months = int(lease_months)
        discount_value = float(discount_value)
        promotion_months = int(promotion_months)
    except (TypeError, ValueError) as error:
        raise ValueError("ราคา จำนวนเดือน และส่วนลดต้องเป็นตัวเลข") from error

    # 2. ตรวจสอบข้อมูลพื้นฐาน
    if base_rent <= 0:
        raise ValueError("base_rent ต้องมากกว่า 0")

    if lease_months <= 0:
        raise ValueError("lease_months ต้องมากกว่า 0")

    if promotion_type not in SUPPORTED_PROMOTIONS:
        raise ValueError(
            f"ไม่รองรับ promotion_type: {promotion_type}"
        )

    if discount_value < 0:
        raise ValueError("discount_value ต้องไม่ติดลบ")

    if promotion_months < 0:
        raise ValueError("promotion_months ต้องไม่ติดลบ")

    # 3. คำนวณมูลค่าสัญญาก่อนใช้โปรโมชั่น
    original_contract_value = base_rent * lease_months
    total_discount = 0.0

    # 4. คำนวณส่วนลดตามประเภทโปรโมชั่น
    if promotion_type == "percentage_discount":
        if discount_value > 100:
            raise ValueError("ส่วนลดเปอร์เซ็นต์ต้องไม่เกิน 100")

        total_discount = (
            original_contract_value
            * discount_value
            / 100
        )

    elif promotion_type == "fixed_discount":
        if discount_value > base_rent:
            raise ValueError("ส่วนลดต่อเดือนต้องไม่เกินค่าเช่าต่อเดือน")

        total_discount = discount_value * lease_months

    elif promotion_type == "free_months":
        if promotion_months <= 0:
            raise ValueError("กรุณาระบุจำนวนเดือนฟรี")

        if promotion_months > lease_months:
            raise ValueError("จำนวนเดือนฟรีต้องไม่เกินอายุสัญญา")

        total_discount = base_rent * promotion_months

    elif promotion_type == "introductory_discount":
        if discount_value > 100:
            raise ValueError("ส่วนลดเปอร์เซ็นต์ต้องไม่เกิน 100")

        if promotion_months <= 0:
            raise ValueError("กรุณาระบุจำนวนเดือนที่ให้ส่วนลด")

        if promotion_months > lease_months:
            raise ValueError("จำนวนเดือนที่ลดต้องไม่เกินอายุสัญญา")

        discount_per_month = (
            base_rent
            * discount_value
            / 100
        )
        total_discount = discount_per_month * promotion_months

    elif promotion_type == "renewal_discount":
        if not is_renewal:
            raise ValueError("โปรโมชั่นนี้ใช้ได้เฉพาะการต่อสัญญา")

        if discount_value > 100:
            raise ValueError("ส่วนลดเปอร์เซ็นต์ต้องไม่เกิน 100")

        total_discount = (
            original_contract_value
            * discount_value
            / 100
        )

    elif promotion_type == "keep_previous_rent":
        if not is_renewal:
            raise ValueError("โปรโมชั่นนี้ใช้ได้เฉพาะการต่อสัญญา")

        if previous_rent is None:
            raise ValueError("กรุณาระบุ previous_rent")

        try:
            previous_rent = float(previous_rent)
        except (TypeError, ValueError) as error:
            raise ValueError("previous_rent ต้องเป็นตัวเลข") from error

        if previous_rent <= 0:
            raise ValueError("previous_rent ต้องมากกว่า 0")

        if previous_rent > base_rent:
            raise ValueError(
                "ราคาเดิมสูงกว่าราคาแนะนำ จึงไม่ควรใช้โปรโมชั่นนี้"
            )

        total_discount = (
            base_rent - previous_rent
        ) * lease_months

    # 5. คำนวณมูลค่าสัญญาและค่าเช่าเฉลี่ยหลังหักส่วนลด
    final_contract_value = (
        original_contract_value - total_discount
    )
    effective_monthly_rent = (
        final_contract_value / lease_months
    )

    # 6. ส่งผลลัพธ์กลับไปใช้ในระบบส่วนอื่น
    return {
        "promotion_type": promotion_type,
        "base_rent": round(base_rent, 2),
        "lease_months": lease_months,
        "original_contract_value": round(original_contract_value, 2),
        "total_discount": round(total_discount, 2),
        "final_contract_value": round(final_contract_value, 2),
        "effective_monthly_rent": round(effective_monthly_rent, 2),
    }


def main():
    """ทดลองคำนวณโปรโมชั่นด้วยข้อมูลตัวอย่าง."""

    result = calculate_promotion(
        base_rent=10000,
        lease_months=12,
        promotion_type="free_months",
        promotion_months=1,
    )

    print("มูลค่าสัญญาก่อนลด:", result["original_contract_value"], "บาท")
    print("ส่วนลดทั้งหมด:", result["total_discount"], "บาท")
    print("มูลค่าสัญญาหลังลด:", result["final_contract_value"], "บาท")
    print("ค่าเช่าเฉลี่ยต่อเดือน:", result["effective_monthly_rent"], "บาท")


if __name__ == "__main__":
    main()
