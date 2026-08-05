"""
contracts.py
============
File dùng CHUNG cho cả nhóm. Định nghĩa "hình dạng" (shape) dữ liệu
mà mỗi agent nhận vào / trả ra, để 4 người code song song không phải
chờ nhau. AI CŨNG IMPORT FILE NÀY, KHÔNG AI ĐƯỢC TỰ Ý SỬA MỘT MÌNH.

Nếu cần đổi field nào -> báo cả nhóm trước, sửa ở đây, rồi mọi người
pull về sync lại.

Dùng dataclass (không phải dict tay) để nếu ai gõ sai tên field,
Python sẽ báo lỗi ngay thay vì fail âm thầm lúc chấm điểm.
"""

from dataclasses import dataclass, field
from typing import Literal, Optional


# ---------------------------------------------------------------------------
# 1) OUTPUT CỦA DATA LAYER (Người 1 implement) -> input cho Người 2 & Người 3
# ---------------------------------------------------------------------------

@dataclass
class OrderInfo:
    order_id: str
    order_status: str                      # vd: "delivered", "canceled", "unavailable", "shipped"...
    order_purchase_timestamp: Optional[str]
    order_approved_at: Optional[str]
    order_delivered_carrier_date: Optional[str]
    order_delivered_customer_date: Optional[str]
    order_estimated_delivery_date: Optional[str]


@dataclass
class ItemInfo:
    order_id: str
    order_item_id: int
    product_id: str
    seller_id: str
    price: float
    freight_value: float
    shipping_limit_date: str               # hạn seller phải bàn giao cho carrier


@dataclass
class PaymentInfo:
    order_id: str
    payment_sequential: int
    payment_type: str
    payment_value: float
    payment_installments: int = 0


@dataclass
class CaseData:
    """Object duy nhất mà data_loader.py trả về cho 1 claimed_order_id.
    Đây là input chung cho MỌI agent khác."""
    order_id: str
    order: Optional[OrderInfo]              # None nếu order_id không tồn tại trong CSV
    items: list[ItemInfo] = field(default_factory=list)     # rỗng nếu order không có item row
    payments: list[PaymentInfo] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 2) OUTPUT CỦA ORDER/SELLER AGENT + DELIVERY AGENT (Người 2)
#    -> input cho Policy Agent (Người 3)
# ---------------------------------------------------------------------------

@dataclass
class SellerViolation:
    seller_id: str
    order_item_id: int
    shipping_limit_date: str
    delivered_to_carrier_date: Optional[str]
    is_late_handoff: bool                  # True nếu carrier nhận hàng sau shipping_limit_date


@dataclass
class DeliveryFindings:
    order_id: str
    order_status: str
    is_delivery_late: bool                 # True nếu giao khách sau estimated_delivery_date
    seller_violations: list[SellerViolation] = field(default_factory=list)
    # root_cause_hint gợi ý cho Policy Agent, KHÔNG phải quyết định cuối cùng
    root_cause_hint: Optional[
        Literal[
            "SELLER_HANDOFF_AFTER_LIMIT",
            "CARRIER_DELIVERED_AFTER_ESTIMATE",
            "DELIVERY_WITHIN_ESTIMATE",
        ]
    ] = None
    evidence: list[str] = field(default_factory=list)   # vd: ["order:xxx", "item:xxx:1", "seller:xxx"]


# ---------------------------------------------------------------------------
# 3) OUTPUT CỦA PAYMENT AGENT (Người 3) -> input cho Policy Agent
# ---------------------------------------------------------------------------

@dataclass
class PaymentFindings:
    order_id: str
    payment_total: float
    item_total: float
    freight_total: float
    is_split_valid: bool                   # >=2 payment row, tổng khớp item+freight (sai số 0.10 BRL)
    is_paid: bool                          # payment_total > 0
    evidence: list[str] = field(default_factory=list)   # vd: ["payment:xxx:1", "payment:xxx:2"]


# ---------------------------------------------------------------------------
# 4) OUTPUT CỦA POLICY AGENT (Người 3) -> input cho Verifier (Người 4)
# ---------------------------------------------------------------------------

PrimaryIssue = Literal[
    "canceled_order_paid",
    "unavailable_order_paid",
    "late_delivery_seller",
    "late_delivery_logistics",
    "valid_split_payment",
    "unsupported_late_claim",
]

CaseStatus = Literal["action_required", "no_action"]

ResolutionAction = Literal[
    "issue_full_refund",
    "refund_freight",
    "explain_valid_split_payment",
    "reject_late_refund",
]


@dataclass
class RankedCause:
    cause_code: str
    rank: int


@dataclass
class ResponsibleParty:
    party_type: Literal["platform", "seller", "logistics_provider"]
    party_id: str


@dataclass
class PolicyDecision:
    case_id: str
    primary_issue: PrimaryIssue
    case_status: CaseStatus
    confidence: float                      # 0..1
    ranked_causes: list[RankedCause]
    responsible_parties: list[ResponsibleParty]
    recommended_refund_brl: float
    resolution_actions: list[ResolutionAction]
    evidence_ids: list[str]                # gộp evidence từ tất cả agent + "policy:<cause_code>"
    order_ids: list[str]
    item_ids: list[str]                    # format "order_id:order_item_id"
    seller_ids: list[str]
    payment_ids: list[str]                 # format "order_id:payment_sequential"
    item_total_brl: float
    freight_total_brl: float
    payment_total_brl: float


# ---------------------------------------------------------------------------
# 5) OUTPUT CUỐI CÙNG SAU KHI VERIFIER DUYỆT (Người 4) -> ghi ra output/EC_xxx.json
#    Đây phải khớp CHÍNH XÁC schema mục 6 trong README của đề bài.
# ---------------------------------------------------------------------------

def to_output_json(decision: PolicyDecision) -> dict:
    """Chuyển PolicyDecision (đã qua Verifier duyệt) thành đúng JSON schema
    mà README yêu cầu nộp trong output/EC_xxx.json. Người 4 sở hữu hàm này."""
    return {
        "case_id": decision.case_id,
        "assessment": {
            "primary_issue": decision.primary_issue,
            "case_status": decision.case_status,
            "confidence": decision.confidence,
        },
        "affected_entities": {
            "order_ids": decision.order_ids[:5],
            "item_ids": decision.item_ids[:5],
            "seller_ids": decision.seller_ids[:5],
            "payment_ids": decision.payment_ids[:5],
        },
        "root_cause_analysis": {
            "ranked_causes": [
                {"cause_code": c.cause_code, "rank": c.rank}
                for c in decision.ranked_causes[:3]
            ],
            "responsible_parties": [
                {"party_type": p.party_type, "party_id": p.party_id}
                for p in decision.responsible_parties[:3]
            ],
        },
        "evidence_ids": decision.evidence_ids[:10],
        "financial_resolution": {
            "currency": "BRL",
            "item_total_brl": round(decision.item_total_brl, 2),
            "freight_total_brl": round(decision.freight_total_brl, 2),
            "payment_total_brl": round(decision.payment_total_brl, 2),
            "recommended_refund_brl": round(decision.recommended_refund_brl, 2),
        },
        "resolution_actions": decision.resolution_actions[:5],
    }


# ---------------------------------------------------------------------------
# 6) EVIDENCE ID HELPERS (dùng chung, tránh mỗi người tự viết format khác nhau)
# ---------------------------------------------------------------------------

def ev_order(order_id: str) -> str:
    return f"order:{order_id}"

def ev_item(order_id: str, order_item_id: int) -> str:
    return f"item:{order_id}:{order_item_id}"

def ev_payment(order_id: str, payment_sequential: int) -> str:
    return f"payment:{order_id}:{payment_sequential}"

def ev_seller(seller_id: str) -> str:
    return f"seller:{seller_id}"

def ev_policy(cause_code: str) -> str:
    return f"policy:{cause_code}"
