"""
policy_agent.py
===============
Policy Agent: Đóng vai trò "Thẩm phán" đưa ra quyết định xử lý khiếu nại (PolicyDecision).
Thuộc Task 3 (Người 3).

Nhận thông tin từ Delivery Agent và Payment Agent, chiếu theo thứ tự ưu tiên 6 quy tắc
đã được quy định trong Section 4 của README.
"""

from typing import List, Optional
from contracts import (
    CaseData,
    DeliveryFindings,
    PaymentFindings,
    PolicyDecision,
    RankedCause,
    ResponsibleParty,
    PrimaryIssue,
    CaseStatus,
    ResolutionAction,
    ev_policy,
)


class PolicyAgent:
    """Agent thẩm phán đưa ra quyết định xử lý khiếu nại theo bộ quy tắc EC_POLICY_V1."""

    def evaluate(
        self,
        case_id: str,
        case_data: CaseData,
        delivery_findings: DeliveryFindings,
        payment_findings: PaymentFindings,
    ) -> PolicyDecision:

        order_status = case_data.order.order_status if case_data.order else "unknown"

        # -------------------------------------------------------------------
        # ÁP DỤNG 6 QUY TẮC NGHIỆP VỤ THEO ĐÚNG THỨ TỰ ƯU TIÊN (PRIORITY 1 -> 6)
        # -------------------------------------------------------------------

        # Rule 1: canceled_order_paid
        if order_status == "canceled" and payment_findings.is_paid:
            primary_issue: PrimaryIssue = "canceled_order_paid"
            case_status: CaseStatus = "action_required"
            cause_code = "ORDER_CANCELED_AFTER_PAYMENT"
            responsible_parties = [
                ResponsibleParty(party_type="platform", party_id="OLIST_PLATFORM")
            ]
            refund_brl = payment_findings.payment_total
            actions: List[ResolutionAction] = ["issue_full_refund"]

        # Rule 2: unavailable_order_paid
        elif order_status == "unavailable" and payment_findings.is_paid:
            primary_issue: PrimaryIssue = "unavailable_order_paid"
            case_status: CaseStatus = "action_required"
            cause_code = "ORDER_UNAVAILABLE_AFTER_PAYMENT"
            responsible_parties = [
                ResponsibleParty(party_type="platform", party_id="OLIST_PLATFORM")
            ]
            refund_brl = payment_findings.payment_total
            actions: List[ResolutionAction] = ["issue_full_refund"]

        # Rule 3: late_delivery_seller
        elif (
            delivery_findings.is_delivery_late
            and delivery_findings.root_cause_hint == "SELLER_HANDOFF_AFTER_LIMIT"
        ):
            primary_issue: PrimaryIssue = "late_delivery_seller"
            case_status: CaseStatus = "action_required"
            cause_code = "SELLER_HANDOFF_AFTER_LIMIT"

            # Tìm seller_id bị vi phạm
            violating_seller_id = "UNKNOWN_SELLER"
            for sv in delivery_findings.seller_violations:
                if sv.is_late_handoff:
                    violating_seller_id = sv.seller_id
                    break
            if violating_seller_id == "UNKNOWN_SELLER" and case_data.items:
                violating_seller_id = case_data.items[0].seller_id

            responsible_parties = [
                ResponsibleParty(party_type="seller", party_id=violating_seller_id)
            ]
            refund_brl = payment_findings.freight_total
            actions: List[ResolutionAction] = ["refund_freight"]

        # Rule 4: late_delivery_logistics
        elif (
            delivery_findings.is_delivery_late
            and delivery_findings.root_cause_hint == "CARRIER_DELIVERED_AFTER_ESTIMATE"
        ):
            primary_issue: PrimaryIssue = "late_delivery_logistics"
            case_status: CaseStatus = "action_required"
            cause_code = "CARRIER_DELIVERED_AFTER_ESTIMATE"
            responsible_parties = [
                ResponsibleParty(
                    party_type="logistics_provider", party_id="LOGISTICS_PROVIDER"
                )
            ]
            refund_brl = payment_findings.freight_total
            actions: List[ResolutionAction] = ["refund_freight"]

        # Rule 5: valid_split_payment
        elif payment_findings.is_split_valid:
            primary_issue: PrimaryIssue = "valid_split_payment"
            case_status: CaseStatus = "no_action"
            cause_code = "MULTIPLE_PAYMENTS_RECONCILED"
            responsible_parties = []
            refund_brl = 0.0
            actions: List[ResolutionAction] = ["explain_valid_split_payment"]

        # Rule 6: unsupported_late_claim (Fallback)
        else:
            primary_issue: PrimaryIssue = "unsupported_late_claim"
            case_status: CaseStatus = "no_action"
            cause_code = "DELIVERY_WITHIN_ESTIMATE"
            responsible_parties = []
            refund_brl = 0.0
            actions: List[ResolutionAction] = ["reject_late_refund"]

        # -------------------------------------------------------------------
        # TỔNG HỢP AFFECTED ENTITIES VÀ EVIDENCE IDS
        # -------------------------------------------------------------------

        order_ids = [case_data.order_id] if case_data.order else []

        if case_data.items:
            item_ids = [f"{case_data.order_id}:{item.order_item_id}" for item in case_data.items]
            seller_ids = list(dict.fromkeys(item.seller_id for item in case_data.items))
            item_total_brl = payment_findings.item_total
            freight_total_brl = payment_findings.freight_total
        else:
            # Nếu order không có item row, item_ids & seller_ids để rỗng
            item_ids = []
            seller_ids = []
            item_total_brl = 0.0
            freight_total_brl = 0.0

        payment_ids = [
            f"{case_data.order_id}:{p.payment_sequential}"
            for p in case_data.payments
        ]

        # Evidence gộp từ Delivery + Payment + Policy
        raw_evidence = (
            delivery_findings.evidence
            + payment_findings.evidence
            + [ev_policy(cause_code)]
        )
        evidence_ids = list(dict.fromkeys(raw_evidence))

        return PolicyDecision(
            case_id=case_id,
            primary_issue=primary_issue,
            case_status=case_status,
            confidence=1.0,
            ranked_causes=[RankedCause(cause_code=cause_code, rank=1)],
            responsible_parties=responsible_parties,
            recommended_refund_brl=round(refund_brl, 2),
            resolution_actions=actions,
            evidence_ids=evidence_ids,
            order_ids=order_ids,
            item_ids=item_ids,
            seller_ids=seller_ids,
            payment_ids=payment_ids,
            item_total_brl=round(item_total_brl, 2),
            freight_total_brl=round(freight_total_brl, 2),
            payment_total_brl=round(payment_findings.payment_total, 2),
        )


def evaluate_policy(
    case_id: str,
    case_data: CaseData,
    delivery_findings: DeliveryFindings,
    payment_findings: PaymentFindings,
) -> PolicyDecision:
    """Helper function cho PolicyAgent."""
    agent = PolicyAgent()
    return agent.evaluate(case_id, case_data, delivery_findings, payment_findings)


if __name__ == "__main__":
    from mock_case_data import (
        get_mock_case_late_seller,
        get_mock_case_canceled_paid,
        get_mock_case_split_payment,
    )
    from delivery_agent import analyze_delivery
    from payment_agent import analyze_payment

    policy_agent = PolicyAgent()

    # Test 1: Late seller
    c1 = get_mock_case_late_seller()
    d1 = analyze_delivery(c1)
    p1 = analyze_payment(c1)
    res1 = policy_agent.evaluate("EC_TEST_1", c1, d1, p1)
    print("=== Test 1: Late Seller ===")
    print(res1)

    # Test 2: Canceled paid
    c2 = get_mock_case_canceled_paid()
    d2 = analyze_delivery(c2)
    p2 = analyze_payment(c2)
    res2 = policy_agent.evaluate("EC_TEST_2", c2, d2, p2)
    print("\n=== Test 2: Canceled Paid ===")
    print(res2)
