"""
test_task3.py
=============
Unit test cho Task 3 (PaymentAgent & PolicyAgent).
Kiểm tra đối soát tài chính và áp dụng 6 quy tắc ưu tiên.
"""

import unittest
from mock_case_data import (
    get_mock_case_late_seller,
    get_mock_case_canceled_paid,
    get_mock_case_split_payment,
    get_mock_case_no_item,
)
from delivery_agent import analyze_delivery
from payment_agent import PaymentAgent
from policy_agent import PolicyAgent


class TestTask3(unittest.TestCase):
    def setUp(self):
        self.payment_agent = PaymentAgent()
        self.policy_agent = PolicyAgent()

    def test_mock_case_late_seller(self):
        case = get_mock_case_late_seller()
        delivery_findings = analyze_delivery(case)
        payment_findings = self.payment_agent.analyze(case)

        # Payment checks
        self.assertEqual(payment_findings.payment_total, 115.0)
        self.assertEqual(payment_findings.item_total, 100.0)
        self.assertEqual(payment_findings.freight_total, 15.0)
        self.assertTrue(payment_findings.is_paid)

        # Policy checks
        decision = self.policy_agent.evaluate("EC_TEST_LATE", case, delivery_findings, payment_findings)
        self.assertEqual(decision.primary_issue, "late_delivery_seller")
        self.assertEqual(decision.case_status, "action_required")
        self.assertEqual(decision.recommended_refund_brl, 15.0)
        self.assertEqual(decision.resolution_actions, ["refund_freight"])
        self.assertEqual(decision.responsible_parties[0].party_type, "seller")
        self.assertEqual(decision.responsible_parties[0].party_id, "seller_A")

    def test_mock_case_canceled_paid(self):
        case = get_mock_case_canceled_paid()
        delivery_findings = analyze_delivery(case)
        payment_findings = self.payment_agent.analyze(case)

        decision = self.policy_agent.evaluate("EC_TEST_CANCEL", case, delivery_findings, payment_findings)
        self.assertEqual(decision.primary_issue, "canceled_order_paid")
        self.assertEqual(decision.case_status, "action_required")
        self.assertEqual(decision.recommended_refund_brl, 60.0)
        self.assertEqual(decision.resolution_actions, ["issue_full_refund"])
        self.assertEqual(decision.responsible_parties[0].party_type, "platform")

    def test_mock_case_split_payment(self):
        case = get_mock_case_split_payment()
        delivery_findings = analyze_delivery(case)
        payment_findings = self.payment_agent.analyze(case)

        self.assertTrue(payment_findings.is_split_valid)

        decision = self.policy_agent.evaluate("EC_TEST_SPLIT", case, delivery_findings, payment_findings)
        self.assertEqual(decision.primary_issue, "valid_split_payment")
        self.assertEqual(decision.case_status, "no_action")
        self.assertEqual(decision.recommended_refund_brl, 0.0)
        self.assertEqual(decision.resolution_actions, ["explain_valid_split_payment"])
        self.assertEqual(len(decision.responsible_parties), 0)

    def test_mock_case_no_item(self):
        case = get_mock_case_no_item()
        delivery_findings = analyze_delivery(case)
        payment_findings = self.payment_agent.analyze(case)

        decision = self.policy_agent.evaluate("EC_TEST_NO_ITEM", case, delivery_findings, payment_findings)
        self.assertEqual(decision.primary_issue, "unavailable_order_paid")
        self.assertEqual(decision.case_status, "action_required")
        self.assertEqual(decision.item_ids, [])
        self.assertEqual(decision.seller_ids, [])
        self.assertEqual(decision.item_total_brl, 0.0)
        self.assertEqual(decision.freight_total_brl, 0.0)


if __name__ == "__main__":
    unittest.main()
