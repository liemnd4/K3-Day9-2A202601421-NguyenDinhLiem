"""
order_delivery/order_delivery_agent.py
======================================
Module cho Người 2: Order & Delivery Agent.
Nhiệm vụ: Phân tích order và items từ CaseData để đánh giá:
- Trạng thái giao hàng (giao trễ hay không)
- Các vi phạm hạn bàn giao của seller (shipping_limit_date)
- Gợi ý nguyên nhân gốc (root_cause_hint)
- Thu thập evidence IDs (order:xxx, item:xxx:y, seller:zzz)

Đầu vào: CaseData (chỉ đọc case_data.order và case_data.items)
Đầu ra: DeliveryFindings (theo contracts.py)

Model sử dụng cho Groq LLM: llama-3.1-8b-instant (≤ 10B parameters)
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional

# Thêm directory cha vào sys.path để import contracts từ root repo nếu cần
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from contracts import (
    CaseData,
    DeliveryFindings,
    SellerViolation,
    ev_order,
    ev_item,
    ev_seller,
)

# Khai báo model name rõ ràng trong source code theo yêu cầu đề bài (Model ≤ 10B)
GROQ_MODEL_NAME = "llama-3.1-8b-instant"


def parse_dt(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse chuỗi ngày tháng ISO hoặc định dạng Olist chuẩn về object datetime.
    Xử lý linh hoạt khoảng trắng và ký tự T."""
    if not dt_str:
        return None
    s = dt_str.strip().replace(" ", "T")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(dt_str.strip(), fmt)
            except ValueError:
                pass
    return None


def load_env_groq_key() -> Optional[str]:
    """Lấy GROQ_API_KEY từ os.environ hoặc đọc từ file .env ở root repo."""
    key = os.environ.get("GROQ_API_KEY")
    if key:
        return key

    # Tìm file .env ở root repo (parent directory) hoặc current directory
    for search_dir in (parent_dir, os.path.dirname(__file__)):
        env_path = os.path.join(search_dir, ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GROQ_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            return val
    return None


def analyze_delivery_deterministic(case_data: CaseData) -> DeliveryFindings:
    """Phân tích logic chuẩn xác 100% dựa trên quy định nghiệp vụ và timestamps."""
    order_id = case_data.order_id

    # Edge case: Order không tồn tại trong CSV
    if case_data.order is None:
        return DeliveryFindings(
            order_id=order_id,
            order_status="unknown",
            is_delivery_late=False,
            seller_violations=[],
            root_cause_hint=None,
            evidence=[],
        )

    order_status = case_data.order.order_status
    carrier_dt = parse_dt(case_data.order.order_delivered_carrier_date)
    customer_dt = parse_dt(case_data.order.order_delivered_customer_date)
    estimated_dt = parse_dt(case_data.order.order_estimated_delivery_date)

    # 1. Đánh giá is_delivery_late (Giao cho khách sau ngày ước tính)
    is_delivery_late = False
    if customer_dt and estimated_dt:
        is_delivery_late = customer_dt > estimated_dt

    # 2. Kiểm tra vi phạm bàn giao của seller cho từng item
    seller_violations: list[SellerViolation] = []
    evidence: list[str] = [ev_order(order_id)]
    seen_evidence = set(evidence)

    for item in case_data.items:
        # Thêm evidence item & seller
        item_ev = ev_item(order_id, item.order_item_id)
        if item_ev not in seen_evidence:
            evidence.append(item_ev)
            seen_evidence.add(item_ev)

        seller_ev = ev_seller(item.seller_id)
        if seller_ev not in seen_evidence:
            evidence.append(seller_ev)
            seen_evidence.add(seller_ev)

        # So sánh ngày carrier nhận hàng với hạn bàn giao của seller
        shipping_limit_dt = parse_dt(item.shipping_limit_date)
        if carrier_dt and shipping_limit_dt:
            is_late_handoff = carrier_dt > shipping_limit_dt
            if is_late_handoff:
                seller_violations.append(
                    SellerViolation(
                        seller_id=item.seller_id,
                        order_item_id=item.order_item_id,
                        shipping_limit_date=item.shipping_limit_date,
                        delivered_to_carrier_date=case_data.order.order_delivered_carrier_date,
                        is_late_handoff=True,
                    )
                )

    # 3. Gợi ý root_cause_hint
    root_cause_hint = None
    if order_status in ("canceled", "unavailable"):
        root_cause_hint = None
    elif is_delivery_late:
        if len(seller_violations) > 0:
            root_cause_hint = "SELLER_HANDOFF_AFTER_LIMIT"
        else:
            root_cause_hint = "CARRIER_DELIVERED_AFTER_ESTIMATE"
    else:
        root_cause_hint = "DELIVERY_WITHIN_ESTIMATE"

    return DeliveryFindings(
        order_id=order_id,
        order_status=order_status,
        is_delivery_late=is_delivery_late,
        seller_violations=seller_violations,
        root_cause_hint=root_cause_hint,
        evidence=evidence,
    )


def analyze_delivery_llm(case_data: CaseData, api_key: str) -> Optional[DeliveryFindings]:
    """Gọi Groq API (dùng model llama-3.1-8b-instant ≤ 10B parameters) 
    để phân tích Order & Delivery."""
    if case_data.order is None:
        return None

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    items_summary = [
        {
            "order_item_id": item.order_item_id,
            "seller_id": item.seller_id,
            "shipping_limit_date": item.shipping_limit_date,
        }
        for item in case_data.items
    ]

    prompt = f"""You are an expert E-Commerce Order & Delivery Investigation Agent.
Analyze the following order and delivery data:

Order ID: {case_data.order_id}
Order Status: {case_data.order.order_status}
Carrier Delivery Date (order_delivered_carrier_date): {case_data.order.order_delivered_carrier_date}
Customer Delivery Date (order_delivered_customer_date): {case_data.order.order_delivered_customer_date}
Estimated Delivery Date (order_estimated_delivery_date): {case_data.order.order_estimated_delivery_date}

Items:
{json.dumps(items_summary, indent=2)}

Rules:
1. is_delivery_late is true IF order_delivered_customer_date > order_estimated_delivery_date.
2. A seller is late handoff IF order_delivered_carrier_date > shipping_limit_date for that item.
3. root_cause_hint should be:
   - "SELLER_HANDOFF_AFTER_LIMIT" if late delivery and at least one seller was late handoff.
   - "CARRIER_DELIVERED_AFTER_ESTIMATE" if late delivery and sellers were on time.
   - "DELIVERY_WITHIN_ESTIMATE" if delivery was on time.
   - null if order is canceled or unavailable.

Return JSON strictly in this format:
{{
  "is_delivery_late": bool,
  "root_cause_hint": string or null
}}
"""

    payload = {
        "model": GROQ_MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You output strictly valid JSON."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }

    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)

            # Reconstruct DeliveryFindings using deterministic baseline + LLM validation
            findings = analyze_delivery_deterministic(case_data)
            if "is_delivery_late" in parsed:
                findings.is_delivery_late = bool(parsed["is_delivery_late"])
            if parsed.get("root_cause_hint") in (
                "SELLER_HANDOFF_AFTER_LIMIT",
                "CARRIER_DELIVERED_AFTER_ESTIMATE",
                "DELIVERY_WITHIN_ESTIMATE",
                None,
            ):
                findings.root_cause_hint = parsed["root_cause_hint"]

            return findings
    except Exception:
        # Soft failure: return None to trigger deterministic fallback cleanly
        return None


class OrderDeliveryAgent:
    """Class chính của Agent cho Người 2."""

    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm
        self.api_key = load_env_groq_key() if use_llm else None

    def process(self, case_data: CaseData) -> DeliveryFindings:
        """Xử lý case_data, ưu tiên LLM qua Groq API, tự động fallback về deterministic logic."""
        if self.use_llm and self.api_key:
            llm_result = analyze_delivery_llm(case_data, self.api_key)
            if llm_result is not None:
                return llm_result

        return analyze_delivery_deterministic(case_data)


# Hàm helper tiện ích cho việc gọi trực tiếp
def analyze_delivery(case_data: CaseData, use_llm: bool = True) -> DeliveryFindings:
    agent = OrderDeliveryAgent(use_llm=use_llm)
    return agent.process(case_data)


if __name__ == "__main__":
    from mock_case_data import ALL_MOCK_CASES

    print("=== Testing Order & Delivery Agent (Folder: order_delivery) ===")
    agent = OrderDeliveryAgent(use_llm=True)
    for mock_case in ALL_MOCK_CASES:
        res = agent.process(mock_case)
        print(f"\n[Case: {mock_case.order_id}] Status: {res.order_status}")
        print(f"  is_delivery_late: {res.is_delivery_late}")
        print(f"  root_cause_hint:  {res.root_cause_hint}")
        print(f"  seller_violations: {res.seller_violations}")
        print(f"  evidence:         {res.evidence}")
