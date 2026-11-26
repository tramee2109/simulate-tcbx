"""
tests/test_execution.py
Tests ExecutionEngine: paper matching against live orderbook, order placement, and fills.
"""

import unittest
from engine.capital_manager import CapitalManager
from engine.portfolio_manager import PortfolioManager
from engine.risk_manager import RiskManager
from engine.execution_engine import ExecutionEngine


class TestExecution(unittest.TestCase):

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
            duplicate_window_sec=0.0,  # disable for testing fills
        )

        self.exec_engine = ExecutionEngine(
            mode="PAPER",
            capital_manager=self.cap_mgr,
            portfolio_manager=self.port_mgr,
            risk_manager=self.risk_mgr,
        )

    def test_paper_order_matching_and_fill(self):
        # Current mock depth
        market_depth = {
            "bids": [{"price": 1_510_000_000.0, "quantity": 0.5}],
            "asks": [{"price": 1_512_000_000.0, "quantity": 0.5}],
        }

        # Submit limit buy above ask -> immediate match
        success, cl_oid, msg = self.exec_engine.submit_limit_order(
            account_id="ACC-01",
            strategy_id="STR-001",
            symbol="BTC_VND",
            side="BUY",
            price=1_512_000_000.0,
            quantity=0.01,
            current_market_depth=market_depth,
        )

        self.assertTrue(success)
        self.assertNotIn(cl_oid, self.exec_engine.open_orders, "Matched order should be filled and removed from open orders")

        # Portfolio should now reflect BTC increase
        p = self.port_mgr.get_account_portfolio("ACC-01")
        self.assertAlmostEqual(p["actual_btc"], 0.11, places=4)

    def test_cancel_order(self):
        market_depth = {
            "bids": [{"price": 1_510_000_000.0, "quantity": 0.5}],
            "asks": [{"price": 1_515_000_000.0, "quantity": 0.5}],
        }

        # Passive buy well below market
        success, cl_oid, msg = self.exec_engine.submit_limit_order(
            account_id="ACC-01",
            strategy_id="STR-001",
            symbol="BTC_VND",
            side="BUY",
            price=1_500_000_000.0,
            quantity=0.01,
            current_market_depth=market_depth,
        )

        self.assertTrue(success)
        self.assertIn(cl_oid, self.exec_engine.open_orders)

        canceled = self.exec_engine.cancel_order(cl_oid)
        self.assertTrue(canceled)
        self.assertNotIn(cl_oid, self.exec_engine.open_orders)


if __name__ == "__main__":
    unittest.main()
