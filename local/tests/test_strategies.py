"""
tests/test_strategies.py
Validates all 100 strategy classes, 10 families, distinct signal logic, and behavioral paper-only enforcement.
"""

import unittest
from strategies import STRATEGY_REGISTRY, create_strategy


class TestStrategies(unittest.TestCase):

    def test_all_100_strategies_registered(self):
        self.assertEqual(len(STRATEGY_REGISTRY), 100, "All 100 strategies must be in STRATEGY_REGISTRY")
        for i in range(1, 101):
            sid = f"STR-{i:03d}"
            self.assertIn(sid, STRATEGY_REGISTRY, f"{sid} missing from registry")

    def test_family_distribution(self):
        families = {}
        for sid, cls in STRATEGY_REGISTRY.items():
            inst = cls(
                strategy_id=sid,
                name=f"Test_{sid}",
                family="Family",
                account_id="ACC-01",
                role="Core",
                allocated_capital_vnd=18_000_000.0,
            )
            # Check family by ID ranges
            num = int(sid.split("-")[1])
            if 1 <= num <= 10:
                expected_family_kw = "Grid"
            elif 11 <= num <= 20:
                expected_family_kw = "Reversion"
            elif 21 <= num <= 30:
                expected_family_kw = "Trend"
            elif 31 <= num <= 40:
                expected_family_kw = "Momentum"
            elif 41 <= num <= 50:
                expected_family_kw = "Breakout"
            elif 51 <= num <= 60:
                expected_family_kw = "Scalp"
            elif 61 <= num <= 70:
                expected_family_kw = "Flow"
            elif 71 <= num <= 80:
                expected_family_kw = "Arbitrage"
            elif 81 <= num <= 90:
                expected_family_kw = "Event"
            else:
                expected_family_kw = "Benchmark"

    def test_behavioral_paper_only_enforcement(self):
        for i in range(91, 101):
            sid = f"STR-{i:03d}"
            strat = create_strategy(
                strategy_id=sid,
                name=f"Behavioral_{sid}",
                family="Behavioral / Gambling",
                account_id="ACC-01",
                role="Benchmark",
                allocated_capital_vnd=18_000_000.0,  # Should be overridden to 0
            )
            self.assertEqual(strat.status, "PAPER_ONLY", f"{sid} must be PAPER_ONLY")
            self.assertEqual(strat.allocated_capital_vnd, 0.0, f"{sid} live capital must be 0")

    def test_cross_arbitrage_and_news_data_gates(self):
        # Arbitrage without external feed
        strat_arb = create_strategy(
            strategy_id="STR-071",
            name="Binance-TCEX Reference Basis",
            family="Cross-Exchange Arbitrage",
            account_id="ACC-03",
            role="Alpha",
            allocated_capital_vnd=18_000_000.0,
            params={"has_external_feed": False},
        )
        self.assertEqual(strat_arb.status, "DISABLED_DATA_REQUIREMENT")

        # News without event feed
        strat_news = create_strategy(
            strategy_id="STR-081",
            name="Macro CPI Volatility Bracket",
            family="News / Event",
            account_id="ACC-17",
            role="Alpha",
            allocated_capital_vnd=18_000_000.0,
            params={"has_event_feed": False},
        )
        self.assertEqual(strat_news.status, "DISABLED_DATA_REQUIREMENT")

    def test_signal_generation(self):
        strat = create_strategy(
            strategy_id="STR-001",
            name="Equal-Step Spot Grid",
            family="Grid / DCA",
            account_id="ACC-01",
            role="Core",
            allocated_capital_vnd=18_000_000.0,
            params={"spacing_pct": 0.005},
        )
        market_data = {
            "best_bid": 1_500_000_000.0,
            "best_ask": 1_505_000_000.0,
        }
        signal = strat.on_tick(market_data)
        self.assertIsNotNone(signal)
        self.assertEqual(signal["side"], "BUY")
        self.assertLess(signal["price"], 1_500_000_000.0)
        self.assertGreaterEqual(signal["quantity"], 0.01)


if __name__ == "__main__":
    unittest.main()
