"""
mock_case_data.py
==================
Data giả để Người 2 và Người 3 code + test agent của mình MÀ KHÔNG CẦN
CHỜ data_loader.py thật xong. Khi Người 1 xong, chỉ cần đổi import
từ `mock_case_data.get_mock_case()` sang `data_loader.load_case(order_id)`
-- không phải sửa logic gì trong agent vì shape (CaseData) giống hệt nhau.

Chạy thử: python mock_case_data.py
"""

from contracts import CaseData, OrderInfo, ItemInfo, PaymentInfo


def get_mock_case_late_seller() -> CaseData:
    """Case mẫu: seller bàn giao trễ -> late_delivery_seller"""
    return CaseData(
        order_id="MOCK_ORDER_1",
        order=OrderInfo(
            order_id="MOCK_ORDER_1",
            order_status="delivered",
            order_purchase_timestamp="2018-01-01T10:00:00",
            order_approved_at="2018-01-01T11:00:00",
            order_delivered_carrier_date="2018-01-10T00:00:00",   # trễ so với hạn seller
            order_delivered_customer_date="2018-01-15T00:00:00",
            order_estimated_delivery_date="2018-01-12T00:00:00",  # giao khách sau ngày ước tính -> late
        ),
        items=[
            ItemInfo(
                order_id="MOCK_ORDER_1", order_item_id=1,
                product_id="prod_1", seller_id="seller_A",
                price=100.0, freight_value=15.0,
                shipping_limit_date="2018-01-05T00:00:00",   # seller phải giao trước ngày này
            ),
        ],
        payments=[
            PaymentInfo(order_id="MOCK_ORDER_1", payment_sequential=1,
                        payment_type="credit_card", payment_value=115.0),
        ],
    )


def get_mock_case_canceled_paid() -> CaseData:
    """Case mẫu: order bị hủy nhưng đã thanh toán -> canceled_order_paid"""
    return CaseData(
        order_id="MOCK_ORDER_2",
        order=OrderInfo(
            order_id="MOCK_ORDER_2",
            order_status="canceled",
            order_purchase_timestamp="2018-02-01T10:00:00",
            order_approved_at="2018-02-01T11:00:00",
            order_delivered_carrier_date=None,
            order_delivered_customer_date=None,
            order_estimated_delivery_date="2018-02-15T00:00:00",
        ),
        items=[
            ItemInfo(
                order_id="MOCK_ORDER_2", order_item_id=1,
                product_id="prod_2", seller_id="seller_B",
                price=50.0, freight_value=10.0,
                shipping_limit_date="2018-02-05T00:00:00",
            ),
        ],
        payments=[
            PaymentInfo(order_id="MOCK_ORDER_2", payment_sequential=1,
                        payment_type="boleto", payment_value=60.0),
        ],
    )


def get_mock_case_split_payment() -> CaseData:
    """Case mẫu: nhiều dòng thanh toán, khớp tổng -> valid_split_payment"""
    return CaseData(
        order_id="MOCK_ORDER_3",
        order=OrderInfo(
            order_id="MOCK_ORDER_3",
            order_status="delivered",
            order_purchase_timestamp="2018-03-01T10:00:00",
            order_approved_at="2018-03-01T11:00:00",
            order_delivered_carrier_date="2018-03-03T00:00:00",
            order_delivered_customer_date="2018-03-08T00:00:00",
            order_estimated_delivery_date="2018-03-12T00:00:00",  # giao sớm hơn dự kiến -> không late
        ),
        items=[
            ItemInfo(
                order_id="MOCK_ORDER_3", order_item_id=1,
                product_id="prod_3", seller_id="seller_C",
                price=80.0, freight_value=12.0,
                shipping_limit_date="2018-03-04T00:00:00",
            ),
        ],
        payments=[
            PaymentInfo(order_id="MOCK_ORDER_3", payment_sequential=1,
                        payment_type="credit_card", payment_value=50.0),
            PaymentInfo(order_id="MOCK_ORDER_3", payment_sequential=2,
                        payment_type="voucher", payment_value=42.0),
        ],
    )


def get_mock_case_no_item() -> CaseData:
    """Edge case: order không có item row -> item_ids/seller_ids phải rỗng"""
    return CaseData(
        order_id="MOCK_ORDER_4",
        order=OrderInfo(
            order_id="MOCK_ORDER_4",
            order_status="unavailable",
            order_purchase_timestamp="2018-04-01T10:00:00",
            order_approved_at=None,
            order_delivered_carrier_date=None,
            order_delivered_customer_date=None,
            order_estimated_delivery_date="2018-04-15T00:00:00",
        ),
        items=[],
        payments=[
            PaymentInfo(order_id="MOCK_ORDER_4", payment_sequential=1,
                        payment_type="credit_card", payment_value=90.0),
        ],
    )


ALL_MOCK_CASES = [
    get_mock_case_late_seller(),
    get_mock_case_canceled_paid(),
    get_mock_case_split_payment(),
    get_mock_case_no_item(),
]

if __name__ == "__main__":
    for c in ALL_MOCK_CASES:
        print(c)
