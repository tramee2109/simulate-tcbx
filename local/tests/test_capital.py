"""
tests/test_capital.py
Tests CapitalManager: central reservation ledger, strategy sleeves, account budgets, and double-spend prevention.
"""

import unittest
from engine.capital_manager import CapitalManager


class TestCapital(unittest.TestCase):

    def setUp(self):
        self.mgr = CapitalManager()
        # Register ACC-01 (150M initial, 90M deployable, 60M reserve)
        self.mgr.register_account("ACC-01", 150_000_000.0, 90_000_000.0, 60_000_000.0)
        # Register STR-001 (18M sleeve)
        self.mgr.register_strategy("STR-001", "ACC-01", 18_000_000.0, is_paper_only=False)
        # Register STR-091 (0 VND, paper only)
        self.mgr.register_strategy("STR-091", "ACC-01", 0.0, is_paper_only=True)

    def test_valid_reservation(self):
        ok, reason = self.mgr.reserve_capital(
            reservation_id="RES_1",
            account_id="ACC-01",
            strategy_id="STR-001",
            asset="VND",
            amount=15_000_000.0,
            available_balance=150_000_000.0,
        )
        self.assertTrue(ok, f"Reservation should succeed: {reason}")
        reserved = self.mgr.get_reserved_amounts("ACC-01")
        self.assertEqual(reserved["VND"], 15_000_000.0)

    def test_strategy_sleeve_limit_exceeded(self):
        # 18M sleeve limit: reserving 19M must fail
        ok, reason = self.mgr.reserve_capital(
            reservation_id="RES_FAIL_SLEEVE",
            account_id="ACC-01",
            strategy_id="STR-001",
            asset="VND",
            amount=19_000_000.0,
            available_balance=150_000_000.0,
        )
        self.assertFalse(ok)
        self.assertIn("sleeve exceeded", reason)

    def test_account_deployable_budget_limit(self):
        # Register 5 strategies with 18M each = 90M
        for i in range(2, 6):
            self.mgr.register_strategy(f"STR-00{i}", "ACC-01", 18_000_000.0)
            self.mgr.reserve_capital(f"RES_{i}", "ACC-01", f"STR-00{i}", "VND", 18_000_000.0, 150_000_000.0)

        # Now total reserved is 4 * 18M = 72M. Attempting to reserve 20M (72 + 20 = 92M > 90M cap) must fail
        ok, reason = self.mgr.reserve_capital(
            reservation_id="RES_CAP_EXCEEDED",
            account_id="ACC-01",
            strategy_id="STR-001",
            asset="VND",
            amount=19_000_000.0,
            available_balance=150_000_000.0,
        )
        self.assertFalse(ok)

    def test_btc_reservation_and_no_short_selling(self):
        # Account has 0.05 BTC. Reserving 0.02 BTC succeeds.
        ok, reason = self.mgr.reserve_capital(
            reservation_id="RES_BTC_1",
            account_id="ACC-01",
            strategy_id="STR-001",
            asset="BTC",
            amount=0.02,
            available_balance=0.05,
        )
        self.assertTrue(ok)

        # Attempting to reserve another 0.04 BTC (0.02 + 0.04 = 0.06 > 0.05) must fail (no short selling)
        ok2, reason2 = self.mgr.reserve_capital(
            reservation_id="RES_BTC_FAIL",
            account_id="ACC-01",
            strategy_id="STR-001",
            asset="BTC",
            amount=0.04,
            available_balance=0.05,
        )
        self.assertFalse(ok2)
        self.assertIn("Insufficient unreserved BTC", reason2)

    def test_release_reservation(self):
        self.mgr.reserve_capital("RES_REL", "ACC-01", "STR-001", "VND", 10_000_000.0, 150_000_000.0)
        self.assertEqual(self.mgr.get_reserved_amounts("ACC-01")["VND"], 10_000_000.0)

        released = self.mgr.release_reservation("RES_REL")
        self.assertTrue(released)
        self.assertEqual(self.mgr.get_reserved_amounts("ACC-01")["VND"], 0.0)


if __name__ == "__main__":
    unittest.main()
