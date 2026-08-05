"""
coordinator.py
==============
Module thuộc sở hữu của Người 4.
Nhiệm vụ:
- Đọc file input JSON (EC_xxx.json)
- Lấy claimed_order_id và điều phối luồng xử lý qua các Agent:
  1. Data Loader (Người 1) -> CaseData
  2. Order/Seller Agent + Delivery Agent (Người 2) -> DeliveryFindings
  3. Payment Agent (Người 3) -> PaymentFindings
  4. Policy Agent (Người 3) -> PolicyDecision
  5. Verifier (Người 4) -> Sanitized PolicyDecision
- Cung cấp fallback trực tiếp nếu các module của Người 1, 2, 3 chưa có mặt.
"""

import os
import json
import csv
from typing import Tuple, List, Dict, Any, Optional

from contracts import (
    CaseData, OrderInfo, ItemInfo, PaymentInfo,
    DeliveryFindings, SellerViolation, PaymentFindings,
    PolicyDecision, RankedCause, ResponsibleParty,
    ev_order, ev_item, ev_payment, ev_seller, ev_policy
)
from verifier import verify_policy_decision


# --- Fallback CSV loader (nếu data_loader.py chưa được tạo) ---
_CSV_CACHE: Dict[str, List[Dict[str, str]]] = {}

def _read_csv(file_name: str) -> List[Dict[str, str]]:
    if file_name in _CSV_CACHE:
        return _CSV_CACHE[file_name]
    file_path = os.path.join("data", file_name)
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    _CSV_CACHE[file_name] = rows
    return rows


def _fallback_load_case(order_id: str) -> CaseData:
    orders_csv = _read_csv("olist_orders_dataset.csv")
    order_row = next((r for r in orders_csv if r.get("order_id") == order_id), None)
    
    if not order_row:
        return CaseData(order_id=order_id, order=None, items=[], payments=[])

    order_info = OrderInfo(
        order_id=order_id,
        order_status=order_row.get("order_status", ""),
        order_purchase_timestamp=order_row.get("order_purchase_timestamp") or None,
        order_approved_at=order_row.get("order_approved_at") or None,
        order_delivered_carrier_date=order_row.get("order_delivered_carrier_date") or None,
        order_delivered_customer_date=order_row.get("order_delivered_customer_date") or None,
        order_estimated_delivery_date=order_row.get("order_estimated_delivery_date") or None,
    )

    items_csv = _read_csv("olist_order_items_dataset.csv")
    item_rows = [r for r in items_csv if r.get("order_id") == order_id]
    items = []
    for r in item_rows:
        try:
            item_seq = int(r.get("order_item_id", "1"))
            price = float(r.get("price", "0"))
            freight = float(r.get("freight_value", "0"))
        except ValueError:
            item_seq, price, freight = 1, 0.0, 0.0
        items.append(
            ItemInfo(
                order_id=order_id,
                order_item_id=item_seq,
                product_id=r.get("product_id", ""),
                seller_id=r.get("seller_id", ""),
                price=price,
                freight_value=freight,
                shipping_limit_date=r.get("shipping_limit_date", ""),
            )
        )

    payments_csv = _read_csv("olist_order_payments_dataset.csv")
    payment_rows = [r for r in payments_csv if r.get("order_id") == order_id]
    payments = []
    for r in payment_rows:
        try:
            seq = int(r.get("payment_sequential", "1"))
            val = float(r.get("payment_value", "0"))
            inst = int(r.get("payment_installments", "1"))
        except ValueError:
            seq, val, inst = 1, 0.0, 1
        payments.append(
            PaymentInfo(
                order_id=order_id,
                payment_sequential=seq,
                payment_type=r.get("payment_type", ""),
                payment_value=val,
                payment_installments=inst,
            )
        )

    return CaseData(order_id=order_id, order=order_info, items=items, payments=payments)


def _fallback_delivery_agent(case_data: CaseData) -> DeliveryFindings:
    if not case_data.order:
        return DeliveryFindings(order_id=case_data.order_id, order_status="unknown", is_delivery_late=False)

    order = case_data.order
    cust_date = order.order_delivered_customer_date
    est_date = order.order_estimated_delivery_date
    carrier_date = order.order_delivered_carrier_date

    is_late = False
    if cust_date and est_date and cust_date > est_date:
        is_late = True

    seller_violations = []
    evidence = [ev_order(case_data.order_id)]

    for it in case_data.items:
        evidence.append(ev_item(case_data.order_id, it.order_item_id))
        if it.seller_id and ev_seller(it.seller_id) not in evidence:
            evidence.append(ev_seller(it.seller_id))

        is_late_handoff = False
        if carrier_date and it.shipping_limit_date and carrier_date > it.shipping_limit_date:
            is_late_handoff = True

        if is_late_handoff:
            seller_violations.append(
                SellerViolation(
                    seller_id=it.seller_id,
                    order_item_id=it.order_item_id,
                    shipping_limit_date=it.shipping_limit_date,
                    delivered_to_carrier_date=carrier_date,
                    is_late_handoff=True,
                )
            )

    root_hint = "DELIVERY_WITHIN_ESTIMATE"
    if is_late:
        if len(seller_violations) > 0:
            root_hint = "SELLER_HANDOFF_AFTER_LIMIT"
        else:
            root_hint = "CARRIER_DELIVERED_AFTER_ESTIMATE"

    return DeliveryFindings(
        order_id=case_data.order_id,
        order_status=order.order_status,
        is_delivery_late=is_late,
        seller_violations=seller_violations,
        root_cause_hint=root_hint,
        evidence=evidence,
    )


def _fallback_payment_agent(case_data: CaseData) -> PaymentFindings:
    payment_total = sum(p.payment_value for p in case_data.payments)
    item_total = sum(i.price for i in case_data.items)
    freight_total = sum(i.freight_value for i in case_data.items)

    is_split_valid = (
        len(case_data.payments) >= 2
        and abs(payment_total - (item_total + freight_total)) <= 0.10
    )
    is_paid = payment_total > 0
    evidence = [ev_payment(case_data.order_id, p.payment_sequential) for p in case_data.payments]

    return PaymentFindings(
        order_id=case_data.order_id,
        payment_total=payment_total,
        item_total=item_total,
        freight_total=freight_total,
        is_split_valid=is_split_valid,
        is_paid=is_paid,
        evidence=evidence,
    )


def _fallback_policy_agent(
    case_id: str,
    case_data: CaseData,
    del_findings: DeliveryFindings,
    pay_findings: PaymentFindings,
) -> PolicyDecision:
    order_status = case_data.order.order_status if case_data.order else "unknown"
    order_id = case_data.order_id

    order_ids = [order_id] if case_data.order else []
    item_ids = [f"{order_id}:{it.order_item_id}" for it in case_data.items]
    seller_ids = list(dict.fromkeys(it.seller_id for it in case_data.items if it.seller_id))
    payment_ids = [f"{order_id}:{p.payment_sequential}" for p in case_data.payments]

    item_total = pay_findings.item_total
    freight_total = pay_findings.freight_total
    payment_total = pay_findings.payment_total

    # Base evidence collected from agents
    base_evidence = list(dict.fromkeys(del_findings.evidence + pay_findings.evidence))

    # Apply priority rules according to README section 4
    if order_status == "canceled" and pay_findings.is_paid:
        cause = "ORDER_CANCELED_AFTER_PAYMENT"
        return PolicyDecision(
            case_id=case_id,
            primary_issue="canceled_order_paid",
            case_status="action_required",
            confidence=0.95,
            ranked_causes=[RankedCause(cause_code=cause, rank=1)],
            responsible_parties=[ResponsibleParty(party_type="platform", party_id="OLIST_PLATFORM")],
            recommended_refund_brl=payment_total,
            resolution_actions=["issue_full_refund"],
            evidence_ids=base_evidence + [ev_policy(cause)],
            order_ids=order_ids,
            item_ids=item_ids,
            seller_ids=seller_ids,
            payment_ids=payment_ids,
            item_total_brl=item_total,
            freight_total_brl=freight_total,
            payment_total_brl=payment_total,
        )

    if order_status == "unavailable" and pay_findings.is_paid:
        cause = "ORDER_UNAVAILABLE_AFTER_PAYMENT"
        return PolicyDecision(
            case_id=case_id,
            primary_issue="unavailable_order_paid",
            case_status="action_required",
            confidence=0.95,
            ranked_causes=[RankedCause(cause_code=cause, rank=1)],
            responsible_parties=[ResponsibleParty(party_type="platform", party_id="OLIST_PLATFORM")],
            recommended_refund_brl=payment_total,
            resolution_actions=["issue_full_refund"],
            evidence_ids=base_evidence + [ev_policy(cause)],
            order_ids=order_ids,
            item_ids=item_ids,
            seller_ids=seller_ids,
            payment_ids=payment_ids,
            item_total_brl=item_total,
            freight_total_brl=freight_total,
            payment_total_brl=payment_total,
        )

    if del_findings.is_delivery_late:
        if len(del_findings.seller_violations) > 0:
            cause = "SELLER_HANDOFF_AFTER_LIMIT"
            resp_seller = del_findings.seller_violations[0].seller_id if del_findings.seller_violations else (seller_ids[0] if seller_ids else "UNKNOWN_SELLER")
            return PolicyDecision(
                case_id=case_id,
                primary_issue="late_delivery_seller",
                case_status="action_required",
                confidence=0.92,
                ranked_causes=[RankedCause(cause_code=cause, rank=1)],
                responsible_parties=[ResponsibleParty(party_type="seller", party_id=resp_seller)],
                recommended_refund_brl=freight_total,
                resolution_actions=["refund_freight"],
                evidence_ids=base_evidence + [ev_policy(cause)],
                order_ids=order_ids,
                item_ids=item_ids,
                seller_ids=seller_ids,
                payment_ids=payment_ids,
                item_total_brl=item_total,
                freight_total_brl=freight_total,
                payment_total_brl=payment_total,
            )
        else:
            cause = "CARRIER_DELIVERED_AFTER_ESTIMATE"
            return PolicyDecision(
                case_id=case_id,
                primary_issue="late_delivery_logistics",
                case_status="action_required",
                confidence=0.90,
                ranked_causes=[RankedCause(cause_code=cause, rank=1)],
                responsible_parties=[ResponsibleParty(party_type="logistics_provider", party_id="LOGISTICS_PROVIDER")],
                recommended_refund_brl=freight_total,
                resolution_actions=["refund_freight"],
                evidence_ids=base_evidence + [ev_policy(cause)],
                order_ids=order_ids,
                item_ids=item_ids,
                seller_ids=seller_ids,
                payment_ids=payment_ids,
                item_total_brl=item_total,
                freight_total_brl=freight_total,
                payment_total_brl=payment_total,
            )

    if pay_findings.is_split_valid:
        cause = "MULTIPLE_PAYMENTS_RECONCILED"
        return PolicyDecision(
            case_id=case_id,
            primary_issue="valid_split_payment",
            case_status="no_action",
            confidence=0.95,
            ranked_causes=[RankedCause(cause_code=cause, rank=1)],
            responsible_parties=[],
            recommended_refund_brl=0.0,
            resolution_actions=["explain_valid_split_payment"],
            evidence_ids=base_evidence + [ev_policy(cause)],
            order_ids=order_ids,
            item_ids=item_ids,
            seller_ids=seller_ids,
            payment_ids=payment_ids,
            item_total_brl=item_total,
            freight_total_brl=freight_total,
            payment_total_brl=payment_total,
        )

    # Default / unsupported late claim
    cause = "DELIVERY_WITHIN_ESTIMATE"
    return PolicyDecision(
        case_id=case_id,
        primary_issue="unsupported_late_claim",
        case_status="no_action",
        confidence=0.95,
        ranked_causes=[RankedCause(cause_code=cause, rank=1)],
        responsible_parties=[],
        recommended_refund_brl=0.0,
        resolution_actions=["reject_late_refund"],
        evidence_ids=base_evidence + [ev_policy(cause)],
        order_ids=order_ids,
        item_ids=item_ids,
        seller_ids=seller_ids,
        payment_ids=payment_ids,
        item_total_brl=item_total,
        freight_total_brl=freight_total,
        payment_total_brl=payment_total,
    )


# --- Coordinator Orchestration ---

def process_case_input(case_input: Dict[str, Any]) -> Tuple[PolicyDecision, Dict[str, Any], List[str]]:
    """Process a single case input dictionary end-to-end.
    Returns (verified_decision, trace_info, warnings)."""
    case_id = case_input.get("case_id", "UNKNOWN_CASE")
    customer_req = case_input.get("customer_request", {})
    claimed_order_id = customer_req.get("claimed_order_id", "")

    # 1. Load Data
    data_loaded = False
    try:
        import data_loader  # type: ignore
        case_data = data_loader.load_case(claimed_order_id)
        data_loaded = True
    except Exception:
        case_data = _fallback_load_case(claimed_order_id)

    # 2. Delivery Analysis
    try:
        import order_seller_agent  # type: ignore
        import delivery_agent  # type: ignore
        del_findings = delivery_agent.analyze_delivery(case_data)
    except Exception:
        del_findings = _fallback_delivery_agent(case_data)

    # 3. Payment Analysis
    try:
        import payment_agent  # type: ignore
        pay_findings = payment_agent.analyze_payments(case_data)
    except Exception:
        pay_findings = _fallback_payment_agent(case_data)

    # 4. Policy Decision
    try:
        import policy_agent  # type: ignore
        raw_decision = policy_agent.evaluate_policy(case_id, case_data, del_findings, pay_findings)
    except Exception:
        raw_decision = _fallback_policy_agent(case_id, case_data, del_findings, pay_findings)

    # 5. Verifier Audit
    verified_decision, warnings = verify_policy_decision(raw_decision)

    trace_info = {
        "case_id": case_id,
        "claimed_order_id": claimed_order_id,
        "order_status": case_data.order.order_status if case_data.order else None,
        "primary_issue": verified_decision.primary_issue,
        "recommended_refund_brl": verified_decision.recommended_refund_brl,
        "case_status": verified_decision.case_status,
        "warnings_count": len(warnings),
        "data_loaded_via": "data_loader.py" if data_loaded else "fallback_csv",
    }

    return verified_decision, trace_info, warnings


def process_case_file(file_path: str) -> Tuple[PolicyDecision, Dict[str, Any], List[str]]:
    with open(file_path, "r", encoding="utf-8") as f:
        case_input = json.load(f)
    return process_case_input(case_input)


if __name__ == "__main__":
    test_input = {
        "case_id": "EC_TEST",
        "customer_request": {"claimed_order_id": "e2a03ccf5ea816036608b2d8c3ab8e60"},
    }
    decision, trace, warnings = process_case_input(test_input)
    print("Decision:", decision)
    print("Trace:", trace)
    print("Warnings:", warnings)
