"""
delivery_agent.py
=================
Re-export module cho Người 2 (Order & Delivery Agent).
Được coordinator.py trực tiếp import: `from delivery_agent import analyze_delivery`
"""

from order_delivery import OrderDeliveryAgent, analyze_delivery

__all__ = ["OrderDeliveryAgent", "analyze_delivery"]


if __name__ == "__main__":
    from mock_case_data import ALL_MOCK_CASES

    print("=== Testing Delivery Agent (Person 2) ===")
    agent = OrderDeliveryAgent(use_llm=False)
    for case in ALL_MOCK_CASES:
        res = agent.process(case)
        print(f"Case {case.order_id}: is_delivery_late={res.is_delivery_late}, hint={res.root_cause_hint}")
