"""
strategies/base.py
Base strategy abstract class for TCEX BTC/VND execution.
LIMIT-only order generation, inventory checks, performance tracking, and lifecycle management.
"""

import time
from typing import Any, Dict, List, Optional
from monitoring.logger import get_logger

logger = get_logger("strategy")


class BaseStrategy:
    """Base class for all TCEX BTC/VND trading strategies."""

    def __init__(
        self,
        strategy_id: str,
        name: str,
        family: str,
        account_id: str,
        role: str,
        allocated_capital_vnd: float,
        params: Optional[Dict[str, Any]] = None,
        status: str = "ACTIVE",
    ):
        self.strategy_id = strategy_id
        self.name = name
        self.family = family
        self.account_id = account_id
        self.role = role
        self.allocated_capital_vnd = allocated_capital_vnd
        self.params = params or {}
        self.status = status  # ACTIVE, REGISTERED, DISABLED_DATA_REQUIREMENT, PAPER_ONLY

        # Strategy runtime state
        self.open_orders: List[str] = []
        self.last_signal_time: float = 0.0
        self.signal_cooldown_sec: float = float(self.params.get("cooldown_sec", 10.0))

        # Minimum order size on TCEX (0.01 BTC)
        self.min_order_qty_btc = float(self.params.get("min_order_qty_btc", 0.01))
        self.order_size_btc = float(self.params.get("order_size_btc", 0.01))

    def on_tick(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Evaluate market conditions on each tick.
        Must return None or signal dict:
        {
            "side": "BUY" or "SELL",
            "price": float (LIMIT price in VND),
            "quantity": float (BTC quantity >= 0.01)
        }
        """
        if self.status not in ("ACTIVE", "REGISTERED", "PAPER_ONLY"):
            return None

        # Respect signal cooldown
        now = time.time()
        if (now - self.last_signal_time) < self.signal_cooldown_sec:
            return None

        signal = self.generate_signal(market_data)
        if signal:
            self.last_signal_time = now
        return signal

    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """To be implemented by concrete strategy class."""
        raise NotImplementedError

    def on_order_submitted(self, client_order_id: str, side: str, price: float, quantity: float):
        self.open_orders.append(client_order_id)

    def on_order_filled(self, client_order_id: str):
        if client_order_id in self.open_orders:
            self.open_orders.remove(client_order_id)

    def on_order_canceled(self, client_order_id: str):
        if client_order_id in self.open_orders:
            self.open_orders.remove(client_order_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "family": self.family,
            "account_id": self.account_id,
            "role": self.role,
            "allocated_capital_vnd": self.allocated_capital_vnd,
            "status": self.status,
            "params": self.params,
        }
