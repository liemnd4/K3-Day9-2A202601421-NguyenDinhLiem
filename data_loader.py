"""
data_loader.py — Người 1 sở hữu file này.
=========================================
Đọc 9 CSV trong data/, join theo claimed_order_id, trả về CaseData
(định nghĩa trong contracts.py) cho các agent khác dùng.

Cách dùng:
    from data_loader import load_case
    case = load_case("e2a03ccf5ea816036608b2d8c3ab8e60")

Yêu cầu: đặt 9 file CSV gốc (tên đúng như trên Kaggle) vào thư mục data/
cùng cấp với input/, output/ (theo đúng cấu trúc repo).
"""

import os
import pandas as pd

from contracts import CaseData, OrderInfo, ItemInfo, PaymentInfo

DATA_DIR = os.environ.get("OLIST_DATA_DIR", "data")

# ---------------------------------------------------------------------------
# Load & cache toàn bộ CSV 1 lần duy nhất (tránh đọc lại CSV cho mỗi case,
# rất chậm nếu chạy 50 case mà đọc lại file mỗi lần).
# ---------------------------------------------------------------------------

_orders_df = None
_items_df = None
_payments_df = None


def _ensure_loaded():
    global _orders_df, _items_df, _payments_df
    if _orders_df is not None:
        return

    orders_path = os.path.join(DATA_DIR, "olist_orders_dataset.csv")
    items_path = os.path.join(DATA_DIR, "olist_order_items_dataset.csv")
    payments_path = os.path.join(DATA_DIR, "olist_order_payments_dataset.csv")

    for p in (orders_path, items_path, payments_path):
        if not os.path.exists(p):
            raise FileNotFoundError(
                f"Không tìm thấy {p}. Kiểm tra biến OLIST_DATA_DIR hoặc "
                f"cấu trúc thư mục data/."
            )

    _orders_df = pd.read_csv(orders_path)
    _items_df = pd.read_csv(items_path)
    _payments_df = pd.read_csv(payments_path)


def _none_if_nan(value):
    """CSV rỗng -> pandas đọc thành NaN (float). Chuyển về None cho sạch."""
    if pd.isna(value):
        return None
    return value


def load_case(order_id: str) -> CaseData:
    """Trả về CaseData cho 1 order_id. Nếu order_id không tồn tại trong
    olist_orders_dataset.csv, trả về CaseData với order=None -- các agent
    khác phải tự kiểm tra và báo lỗi thay vì giả định order luôn có."""
    _ensure_loaded()

    order_rows = _orders_df[_orders_df["order_id"] == order_id]
    if order_rows.empty:
        return CaseData(order_id=order_id, order=None, items=[], payments=[])

    r = order_rows.iloc[0]
    order = OrderInfo(
        order_id=order_id,
        order_status=r["order_status"],
        order_purchase_timestamp=_none_if_nan(r["order_purchase_timestamp"]),
        order_approved_at=_none_if_nan(r["order_approved_at"]),
        order_delivered_carrier_date=_none_if_nan(r["order_delivered_carrier_date"]),
        order_delivered_customer_date=_none_if_nan(r["order_delivered_customer_date"]),
        order_estimated_delivery_date=_none_if_nan(r["order_estimated_delivery_date"]),
    )

    item_rows = _items_df[_items_df["order_id"] == order_id].sort_values("order_item_id")
    items = [
        ItemInfo(
            order_id=order_id,
            order_item_id=int(row["order_item_id"]),
            product_id=row["product_id"],
            seller_id=row["seller_id"],
            price=float(row["price"]),
            freight_value=float(row["freight_value"]),
            shipping_limit_date=row["shipping_limit_date"],
        )
        for _, row in item_rows.iterrows()
    ]

    payment_rows = _payments_df[_payments_df["order_id"] == order_id].sort_values("payment_sequential")
    payments = [
        PaymentInfo(
            order_id=order_id,
            payment_sequential=int(row["payment_sequential"]),
            payment_type=row["payment_type"],
            payment_value=float(row["payment_value"]),
            payment_installments=int(row.get("payment_installments", 0) or 0),
        )
        for _, row in payment_rows.iterrows()
    ]

    return CaseData(order_id=order_id, order=order, items=items, payments=payments)


if __name__ == "__main__":
    # Test nhanh: chạy `python data_loader.py <order_id>` để kiểm tra join
    import sys
    if len(sys.argv) < 2:
        print("Dùng: python data_loader.py <order_id>")
    else:
        c = load_case(sys.argv[1])
        print(c)
