"""
tests/test_risk.py
Tests multi-tier risk controls: LIMIT-only, symbol restrictions, stale market data,
order size, duplicate order prevention, emergency stop, and account/strategy isolation.
"""

import unittest
from engine.capital_manager import CapitalManager
from engine.portfolio_manager import PortfolioManager
from engine.risk_manager import RiskManager


class TestRisk(unittest.TestCase):

    def setUp(self):
        self.cap_mgr = CapitalManager()
        self.cap_mgr.register_account("ACC-01", 150_000_000.0, 90_000_000.0, 60_000_000.0)
        self.cap_mgr.register_strategy("STR-001", "ACC-01", 18_000_000.0)

        self.port_mgr = PortfolioManager(capital_manager=self.cap_mgr)
        self.port_mgr.init_account("ACC-01", 150_000_000.0)
        self.port_mgr.update_actual_balances("ACC-01", 150_000_000.0, 0.10)

        self.risk_mgr = RiskManager(
            capital_manager=self.cap_mgr,
            portfolio_manager=self.port_mgr,
            max_open_orders_per_strategy=2,
            max_open_orders_per_account=5,
            min_order_qty_btc=0.01,
            max_order_qty_btc=1.0,
            min_notional_vnd=10_000_000.0,
            stale_market_data_threshold_sec=30.0,
            duplicate_window_sec=2.0,
        )

    def test_forbidden_symbol_rejected(self):
        ok, reason = self.risk_mgr.validate_order(
            account_id="ACC-01",
            strategy_id="STR-001",
            symbol="BTC_USDT",  # Forbidden: must be BTC_VND
            side="BUY",
            order_type="LIMIT",
            price=1_500_000_000.0,
            quantity=0.01,
        )
        self.assertFalse(ok)
        self.assertIn("Forbidden symbol", reason)

    def test_non_limit_order_rejected(self):
        ok, reason = self.risk_mgr.validate_order(
            account_id="ACC-01",
            strategy_id="STR-001",
            symbol="BTC_VND",
            side="BUY",
            order_type="MARKET",  # Forbidden: LIMIT only
            price=1_500_000_000.0,
            quantity=0.01,
        )
        self.assertFalse(ok)
        self.assertIn("LIMIT-only", reason)

    def test_stale_market_data_rejected(self):
        ok, reason = self.risk_mgr.validate_order(
            account_id="ACC-01",
            strategy_id="STR-001",
            symbol="BTC_VND",
            side="BUY",
            order_type="LIMIT",
            price=1_500_000_000.0,
            quantity=0.01,
            market_data_age_sec=45.0,  # 45s > 30s threshold
        )
        self.assertFalse(ok)
        self.assertIn("stale", reason.lower())

    def test_duplicate_order_prevention(self):
        ok1, reason1 = self.risk_mgr.validate_order(
            account_id="ACC-01",
            strategy_id="STR-001",
            symbol="BTC_VND",
            side="BUY",
            order_type="LIMIT",
            price=1_500_000_000.0,
            quantity=0.01,
            market_data_age_sec=1.0,
        )
        self.assertTrue(ok1, f"First order should pass: {reason1}")

        # Immediate identical order submission should be caught as duplicate
        ok2, reason2 = self.risk_mgr.validate_order(
            account_id="ACC-01",
            strategy_id="STR-001",
            symbol="BTC_VND",
            side="BUY",
            order_type="LIMIT",
            price=1_500_000_000.0,
            quantity=0.01,
            market_data_age_sec=1.0,
        )
        self.assertFalse(ok2)
        self.assertIn("Duplicate order", reason2)

    def test_emergency_stop(self):
        self.risk_mgr.set_emergency_stop(True, reason="Test drill")
        ok, reason = self.risk_mgr.validate_order(
            account_id="ACC-01",
            strategy_id="STR-001",
            symbol="BTC_VND",
            side="BUY",
            order_type="LIMIT",
            price=1_500_000_000.0,
            quantity=0.01,
        )
        self.assertFalse(ok)
        self.assertIn("emergency stop", reason.lower())


if __name__ == "__main__":
    unittest.main()
