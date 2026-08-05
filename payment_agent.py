from contracts import CaseData, PaymentFindings, ev_payment


class PaymentAgent:
    """Agent phụ trách phân tích và đối soát tài chính của đơn hàng."""

    def analyze(self, case: CaseData) -> PaymentFindings:
        # Tính tổng giá trị thanh toán của tất cả payment rows
        payment_total = sum(p.payment_value for p in case.payments)

        # Tính tổng tiền hàng (item price) và tổng tiền cước phí vận chuyển (freight_value)
        item_total = sum(i.price for i in case.items)
        freight_total = sum(i.freight_value for i in case.items)

        # Kiểm tra xem đơn hàng đã được thanh toán tiền chưa (> 0 BRL)
        is_paid = payment_total > 0

        # Kiểm tra điều kiện Valid Split Payment:
        # 1. Có từ 2 dòng thanh toán trở lên (len(payments) >= 2)
        # 2. Tổng payment khớp với tổng (tiền hàng + phí ship) trong khoảng sai số <= 0.10 BRL
        is_split_valid = False
        if len(case.payments) >= 2:
            expected_total = item_total + freight_total
            if abs(payment_total - expected_total) <= 0.10 + 1e-9:
                is_split_valid = True

        # Thu thập danh sách Evidence ID dạng "payment:<order_id>:<payment_sequential>"
        evidence = [
            ev_payment(case.order_id, p.payment_sequential)
            for p in case.payments
        ]

        return PaymentFindings(
            order_id=case.order_id,
            payment_total=round(payment_total, 2),
            item_total=round(item_total, 2),
            freight_total=round(freight_total, 2),
            is_split_valid=is_split_valid,
            is_paid=is_paid,
            evidence=evidence,
        )


def analyze_payment(case: CaseData) -> PaymentFindings:
    """Helper function cho PaymentAgent."""
    agent = PaymentAgent()
    return agent.analyze(case)


if __name__ == "__main__":
    from mock_case_data import (
        get_mock_case_late_seller,
        get_mock_case_split_payment,
    )

    agent = PaymentAgent()
    print("--- Test PaymentAgent với Case Late Seller ---")
    res1 = agent.analyze(get_mock_case_late_seller())
    print(res1)

    print("\n--- Test PaymentAgent với Case Split Payment ---")
    res2 = agent.analyze(get_mock_case_split_payment())
    print(res2)
