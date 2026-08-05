"""
test_data_loader.py — Người 1 chạy file này SAU KHI đặt 9 CSV thật vào data/.
================================================================================
Load thử cả 50 claimed_order_id trong input/EC_001.json -> EC_050.json,
báo cáo order_id nào lỗi/không tìm thấy để phát hiện sớm vấn đề dữ liệu,
TRƯỚC khi giao cho Người 2, 3, 4 dùng.

Chạy: python test_data_loader.py
"""

import glob
import json

from data_loader import load_case

INPUT_DIR = "input"


def main():
    files = sorted(glob.glob(f"{INPUT_DIR}/EC_*.json"))
    print(f"Tìm thấy {len(files)} file input.\n")

    n_ok, n_missing, n_no_items, n_no_payments = 0, 0, 0, 0

    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        case_id = data["case_id"]
        order_id = data["customer_request"]["claimed_order_id"]

        try:
            case = load_case(order_id)
        except Exception as e:
            print(f"[EXCEPTION] {case_id} ({order_id}): {e}")
            continue

        if case.order is None:
            print(f"[MISSING] {case_id}: order_id={order_id} không có trong CSV")
            n_missing += 1
            continue

        n_ok += 1
        if not case.items:
            print(f"[CẢNH BÁO] {case_id}: order_id={order_id} không có item nào")
            n_no_items += 1
        if not case.payments:
            print(f"[CẢNH BÁO] {case_id}: order_id={order_id} không có payment nào")
            n_no_payments += 1

    print(f"\n--- Tổng kết ---")
    print(f"OK: {n_ok}/{len(files)}")
    print(f"Order_id không tìm thấy trong CSV: {n_missing}")
    print(f"Case không có item: {n_no_items}")
    print(f"Case không có payment: {n_no_payments}")

    if n_missing > 0:
        print("\n⚠️  Có order_id không tìm thấy -- báo ngay cho nhóm trước khi code tiếp,")
        print("   khả năng cao là lỗi đọc CSV (sai path/tên cột) chứ không phải data thiếu thật.")


if __name__ == "__main__":
    main()
