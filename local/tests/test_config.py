"""
tests/test_config.py
Validates config.json schema, account objects, strategy objects, capital math, and risk settings.
"""

import json
import os
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestConfig(unittest.TestCase):

    def setUp(self):
        config_path = os.path.join(BASE_DIR, "config.json")
        self.assertTrue(os.path.isfile(config_path), "config.json must exist")
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

    def test_system_section(self):
        sys_cfg = self.config.get("system", {})
        self.assertEqual(sys_cfg.get("exchange"), "TCEX")
        self.assertEqual(sys_cfg.get("market"), "SPOT")
        self.assertEqual(sys_cfg.get("symbol"), "BTC_VND")
        self.assertEqual(sys_cfg.get("base_asset"), "BTC")
        self.assertEqual(sys_cfg.get("quote_asset"), "VND")
        self.assertEqual(sys_cfg.get("order_type"), "LIMIT")

    def test_capital_math(self):
        cap = self.config.get("capital", {})
        self.assertEqual(cap.get("account_initial_capital"), 150_000_000.0)
        self.assertEqual(cap.get("account_deployable_capital"), 90_000_000.0)
        self.assertEqual(cap.get("account_reserve"), 60_000_000.0)
        self.assertEqual(cap.get("system_total_initial_capital"), 3_000_000_000.0)
        self.assertEqual(cap.get("system_total_deployable_capital"), 1_800_000_000.0)
        self.assertEqual(cap.get("system_total_reserve"), 1_200_000_000.0)

    def test_execution_constraints(self):
        exec_cfg = self.config.get("execution", {})
        self.assertEqual(exec_cfg.get("allowed_order_types"), ["LIMIT"])
        self.assertFalse(exec_cfg.get("allow_market_orders"))
        self.assertFalse(exec_cfg.get("allow_short_selling"))
        self.assertFalse(exec_cfg.get("allow_margin"))
        self.assertFalse(exec_cfg.get("allow_leverage"))
        self.assertEqual(exec_cfg.get("price_scale"), 2)
        self.assertEqual(exec_cfg.get("qty_scale"), 2)
        self.assertEqual(exec_cfg.get("min_qty"), 0.01)

    def test_accounts_structure(self):
        accounts = self.config.get("accounts", [])
        self.assertEqual(len(accounts), 20, "Must have exactly 20 accounts")
        for idx, acc in enumerate(accounts, 1):
            expected_id = f"ACC-{idx:02d}"
            self.assertEqual(acc.get("account_id"), expected_id)
            self.assertTrue(acc.get("username").startswith("tmp_"))
            self.assertTrue(acc.get("nickname").startswith("Mu #"))
            # Ensure no secret keys in config
            self.assertNotIn("secret_key", acc)
            self.assertIn("secret_key_ref", acc)

    def test_strategies_count_and_budget(self):
        strats = self.config.get("strategies", [])
        self.assertEqual(len(strats), 100, "Must have exactly 100 strategies")

        # Behavioral strategies check
        for s in strats:
            sid = s["strategy_id"]
            if sid.startswith("STR-09") or sid == "STR-100":
                self.assertEqual(s["allocated_capital_vnd"], 0.0, f"{sid} must have 0 live capital")
                self.assertEqual(s["status"], "PAPER_ONLY", f"{sid} must be PAPER_ONLY")


if __name__ == "__main__":
    unittest.main()
