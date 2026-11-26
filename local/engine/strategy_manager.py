"""
engine/strategy_manager.py
Orchestrates 100 strategies, lifecycle states, ticks, data routing, and performance monitoring.
Guarantees failure in one strategy never crashes other strategies or accounts.
"""

import time
from typing import Any, Dict, List, Optional
from monitoring.logger import get_logger
from monitoring.health import HealthMonitor

logger = get_logger("strategy_manager")


class StrategyManager:
    """Manages 100 strategy instances across 20 accounts."""

    def __init__(
        self,
        execution_engine: Any,
        market_data_manager: Any,
        health_monitor: Optional[HealthMonitor] = None,
    ):
        self.execution_engine = execution_engine
        self.market_data = market_data_manager
        self.health_monitor = health_monitor or HealthMonitor()
        self.strategies: Dict[str, Any] = {}
        self.strategy_stats: Dict[str, Dict[str, Any]] = {}

    def register_strategy(self, strategy_instance: Any):
        sid = strategy_instance.strategy_id
        self.strategies[sid] = strategy_instance
        self.strategy_stats[sid] = {
            "strategy_id": sid,
            "name": strategy_instance.name,
            "family": strategy_instance.family,
            "account_id": strategy_instance.account_id,
            "status": strategy_instance.status,
            "signals_generated": 0,
            "orders_placed": 0,
            "errors": 0,
        }
        logger.info(
            f"Registered strategy [{sid}] {strategy_instance.name} ({strategy_instance.family}) "
            f"on {strategy_instance.account_id} [Status: {strategy_instance.status}]"
        )

    def tick_all(self, market_data_context: Dict[str, Any]):
        """Run one evaluation tick across all registered strategies with failure isolation."""
        depth = self.market_data.get_orderbook_depth()
        age_sec = time.time() - self.market_data._last_update_ts

        for sid, strat in self.strategies.items():
            stats = self.strategy_stats[sid]

            # Only tick enabled / active strategies
            if strat.status not in ("ACTIVE", "REGISTERED", "PAPER_ONLY"):
                continue

            def _run_strat_tick():
                signal = strat.on_tick(market_data_context)
                if signal:
                    stats["signals_generated"] += 1
                    side = signal.get("side")
                    price = signal.get("price")
                    quantity = signal.get("quantity")

                    if side and price and quantity:
                        success, cl_oid, msg = self.execution_engine.submit_limit_order(
                            account_id=strat.account_id,
                            strategy_id=sid,
                            symbol="BTC_VND",
                            side=side,
                            price=price,
                            quantity=quantity,
                            market_data_age_sec=age_sec,
                            current_market_depth=depth,
                        )
                        if success:
                            stats["orders_placed"] += 1
                            strat.on_order_submitted(cl_oid, side, price, quantity)

            # Error containment: failure in one strategy is isolated and reported
            try:
                self.health_monitor.safe_execute(f"strat.{sid}", _run_strat_tick)
            except Exception as e:
                stats["errors"] += 1
                logger.error(f"Isolated exception in strategy [{sid}]: {e}")

    def get_strategy_summary(self) -> List[Dict[str, Any]]:
        return list(self.strategy_stats.values())
