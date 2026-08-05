"""
order_delivery/test_order_delivery_agent.py
============================================
Unit Test Suite cho Order & Delivery Agent (Người 2).
Chạy: python order_delivery/test_order_delivery_agent.py
"""

import os
import sys
import unittest

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from contracts import CaseData, OrderInfo, ItemInfo, PaymentInfo
from mock_case_data import (
    get_mock_case_late_seller,
    get_mock_case_canceled_paid,
    get_mock_case_split_payment,
    get_mock_case_no_item,
)
from order_delivery.order_delivery_agent import OrderDeliveryAgent


class TestOrderDeliveryAgent(unittest.TestCase):

    def setUp(self):
        self.agent_deterministic = OrderDeliveryAgent(use_llm=False)
        self.agent_llm = OrderDeliveryAgent(use_llm=True)

    def test_mock_case_1_late_seller(self):
        case = get_mock_case_late_seller()
        res = self.agent_deterministic.process(case)

        self.assertEqual(res.order_id, "MOCK_ORDER_1")
        self.assertEqual(res.order_status, "delivered")
        self.assertTrue(res.is_delivery_late)
        self.assertEqual(res.root_cause_hint, "SELLER_HANDOFF_AFTER_LIMIT")
        self.assertEqual(len(res.seller_violations), 1)
        self.assertEqual(res.seller_violations[0].seller_id, "seller_A")
        self.assertTrue(res.seller_violations[0].is_late_handoff)

        expected_evidence = ["order:MOCK_ORDER_1", "item:MOCK_ORDER_1:1", "seller:seller_A"]
        self.assertEqual(res.evidence, expected_evidence)

    def test_mock_case_2_canceled_paid(self):
        case = get_mock_case_canceled_paid()
        res = self.agent_deterministic.process(case)

        self.assertEqual(res.order_id, "MOCK_ORDER_2")
        self.assertEqual(res.order_status, "canceled")
        self.assertFalse(res.is_delivery_late)
        self.assertIsNone(res.root_cause_hint)
        self.assertEqual(len(res.seller_violations), 0)
        self.assertEqual(res.evidence, ["order:MOCK_ORDER_2", "item:MOCK_ORDER_2:1", "seller:seller_B"])

    def test_mock_case_3_on_time_delivery(self):
        case = get_mock_case_split_payment()
        res = self.agent_deterministic.process(case)

        self.assertEqual(res.order_id, "MOCK_ORDER_3")
        self.assertEqual(res.order_status, "delivered")
        self.assertFalse(res.is_delivery_late)
        self.assertEqual(res.root_cause_hint, "DELIVERY_WITHIN_ESTIMATE")
        self.assertEqual(len(res.seller_violations), 0)

    def test_mock_case_4_no_items(self):
        case = get_mock_case_no_item()
        res = self.agent_deterministic.process(case)

        self.assertEqual(res.order_id, "MOCK_ORDER_4")
        self.assertEqual(res.order_status, "unavailable")
        self.assertFalse(res.is_delivery_late)
        self.assertIsNone(res.root_cause_hint)
        self.assertEqual(res.evidence, ["order:MOCK_ORDER_4"])

    def test_carrier_late_delivery_seller_on_time(self):
        case = CaseData(
            order_id="CARRIER_LATE_ORDER",
            order=OrderInfo(
                order_id="CARRIER_LATE_ORDER",
                order_status="delivered",
                order_purchase_timestamp="2018-01-01T10:00:00",
                order_approved_at="2018-01-01T11:00:00",
                order_delivered_carrier_date="2018-01-03T00:00:00",
                order_delivered_customer_date="2018-01-15T00:00:00",
                order_estimated_delivery_date="2018-01-12T00:00:00",
            ),
            items=[
                ItemInfo(
                    order_id="CARRIER_LATE_ORDER",
                    order_item_id=1,
                    product_id="prod_X",
                    seller_id="seller_X",
                    price=100.0,
                    freight_value=20.0,
                    shipping_limit_date="2018-01-05T00:00:00",
                )
            ],
            payments=[
                PaymentInfo(
                    order_id="CARRIER_LATE_ORDER",
                    payment_sequential=1,
                    payment_type="credit_card",
                    payment_value=120.0,
                )
            ],
        )

        res = self.agent_deterministic.process(case)
        self.assertTrue(res.is_delivery_late)
        self.assertEqual(res.root_cause_hint, "CARRIER_DELIVERED_AFTER_ESTIMATE")
        self.assertEqual(len(res.seller_violations), 0)

    def test_missing_order_none(self):
        case = CaseData(
            order_id="MISSING_ORDER",
            order=None,
            items=[],
            payments=[],
        )

        res = self.agent_deterministic.process(case)
        self.assertEqual(res.order_status, "unknown")
        self.assertFalse(res.is_delivery_late)
        self.assertIsNone(res.root_cause_hint)
        self.assertEqual(res.evidence, [])

    def test_groq_llm_mode_fallback_or_success(self):
        case = get_mock_case_late_seller()
        res = self.agent_llm.process(case)
        self.assertEqual(res.order_id, "MOCK_ORDER_1")
        self.assertTrue(res.is_delivery_late)
        self.assertEqual(res.root_cause_hint, "SELLER_HANDOFF_AFTER_LIMIT")


if __name__ == "__main__":
    unittest.main()
