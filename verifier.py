"""
verifier.py
===========
Module thuộc sở hữu của Người 4.
Nhiệm vụ:
- Kiểm tra tính hợp lệ của evidence IDs (regex).
- Kiểm tra giới hạn số lượng theo đúng đề bài README (mục 6):
  + order_ids <= 5
  + item_ids <= 5
  + seller_ids <= 5
  + payment_ids <= 5
  + evidence_ids <= 10
  + ranked_causes <= 3
  + responsible_parties <= 3
  + resolution_actions <= 5
  + confidence ∈ [0.0, 1.0]
- Đảm bảo case_status tương thích với recommended_refund_brl:
  + Nếu recommended_refund_brl > 0 -> action_required
  + Nếu recommended_refund_brl == 0 -> no_action
"""

import re
from typing import Tuple, List
from contracts import PolicyDecision

# Evidence ID regex patterns according to README section 5
PATTERNS = [
    re.compile(r"^order:[a-zA-Z0-9_\-]+$"),
    re.compile(r"^item:[a-zA-Z0-9_\-]+:\d+$"),
    re.compile(r"^payment:[a-zA-Z0-9_\-]+:\d+$"),
    re.compile(r"^seller:[a-zA-Z0-9_\-]+$"),
    re.compile(r"^policy:(SELLER_HANDOFF_AFTER_LIMIT|CARRIER_DELIVERED_AFTER_ESTIMATE|ORDER_CANCELED_AFTER_PAYMENT|ORDER_UNAVAILABLE_AFTER_PAYMENT|MULTIPLE_PAYMENTS_RECONCILED|DELIVERY_WITHIN_ESTIMATE)$"),
]


def verify_evidence_id(evidence_id: str) -> bool:
    """Check if an evidence_id conforms to allowed patterns."""
    return any(p.match(str(evidence_id)) for p in PATTERNS)


def verify_policy_decision(decision: PolicyDecision) -> Tuple[PolicyDecision, List[str]]:
    """Sanitize and verify PolicyDecision object according to rules.
    Returns (sanitized_decision, list_of_warnings)."""
    warnings = []

    # 1. Check confidence interval [0.0, 1.0]
    conf = decision.confidence
    if not isinstance(conf, (int, float)):
        conf = 1.0
        warnings.append(f"Confidence value {decision.confidence} is not numeric. Reset to 1.0.")
    elif conf < 0.0:
        conf = 0.0
        warnings.append(f"Confidence value {decision.confidence} < 0. Fixed to 0.0.")
    elif conf > 1.0:
        conf = 1.0
        warnings.append(f"Confidence value {decision.confidence} > 1. Fixed to 1.0.")
    decision.confidence = conf

    # 2. Filter evidence IDs based on regex validity and remove duplicates preserving order
    valid_evidence = []
    seen = set()
    for ev in decision.evidence_ids:
        if verify_evidence_id(ev):
            if ev not in seen:
                valid_evidence.append(ev)
                seen.add(ev)
        else:
            warnings.append(f"Invalid evidence ID format skipped: '{ev}'")

    decision.evidence_ids = valid_evidence[:10]

    # 3. Enforce maximum array size constraints
    decision.order_ids = decision.order_ids[:5]
    decision.item_ids = decision.item_ids[:5]
    decision.seller_ids = decision.seller_ids[:5]
    decision.payment_ids = decision.payment_ids[:5]
    decision.ranked_causes = decision.ranked_causes[:3]
    decision.responsible_parties = decision.responsible_parties[:3]
    decision.resolution_actions = decision.resolution_actions[:5]

    # Handle edge case: if no items, item_ids and seller_ids must be empty, item_total and freight_total must be 0.0
    if len(decision.item_ids) == 0:
        decision.seller_ids = []
        decision.item_total_brl = 0.0
        decision.freight_total_brl = 0.0

    # 4. Enforce case_status consistency with recommended_refund_brl
    if decision.recommended_refund_brl > 0:
        if decision.case_status != "action_required":
            decision.case_status = "action_required"
            warnings.append("Updated case_status to 'action_required' because recommended_refund_brl > 0.")
    else:
        if decision.case_status != "no_action":
            decision.case_status = "no_action"
            warnings.append("Updated case_status to 'no_action' because recommended_refund_brl == 0.")

    # 5. Round financial values to 2 decimal places
    decision.item_total_brl = round(decision.item_total_brl, 2)
    decision.freight_total_brl = round(decision.freight_total_brl, 2)
    decision.payment_total_brl = round(decision.payment_total_brl, 2)
    decision.recommended_refund_brl = round(decision.recommended_refund_brl, 2)

    return decision, warnings


if __name__ == "__main__":
    # Unit test for verifier
    test_evs = [
        "order:abc123",
        "item:abc123:1",
        "payment:abc123:2",
        "seller:sel456",
        "policy:SELLER_HANDOFF_AFTER_LIMIT",
        "invalid_ev_123",
    ]
    for ev in test_evs:
        print(f"Evidence '{ev}': {verify_evidence_id(ev)}")

