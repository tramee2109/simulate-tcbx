"""
monitoring/metrics.py
Financial and strategy performance metrics tracking.
"""

import math
import time
from typing import Any, Dict, List, Optional


class PerformanceTracker:
    """Tracks realized PnL, unrealized PnL, win rate, trades, and drawdown for an entity."""

    def __init__(self, entity_id: str, initial_capital_vnd: float = 0.0):
        self.entity_id = entity_id
        self.initial_capital_vnd = initial_capital_vnd
        self.realized_pnl_vnd = 0.0
        self.unrealized_pnl_vnd = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.fees_paid_vnd = 0.0
        self.peak_balance_vnd = initial_capital_vnd
        self.max_drawdown_vnd = 0.0
        self.max_drawdown_pct = 0.0
        self.trade_history: List[Dict[str, Any]] = []
        self.daily_pnl_vnd: Dict[str, float] = {}

    def record_fill(
        self,
        symbol: str,
        side: str,
        price: float,
        quantity: float,
        fee_vnd: float,
        pnl_vnd: float = 0.0,
        timestamp: Optional[float] = None,
    ):
        ts = timestamp or time.time()
        self.total_trades += 1
        self.fees_paid_vnd += fee_vnd

        if pnl_vnd > 0:
            self.winning_trades += 1
        elif pnl_vnd < 0:
            self.losing_trades += 1

        self.realized_pnl_vnd += (pnl_vnd - fee_vnd)

        current_equity = self.initial_capital_vnd + self.realized_pnl_vnd + self.unrealized_pnl_vnd
        if current_equity > self.peak_balance_vnd:
            self.peak_balance_vnd = current_equity

        dd = self.peak_balance_vnd - current_equity
        if dd > self.max_drawdown_vnd:
            self.max_drawdown_vnd = dd
            if self.peak_balance_vnd > 0:
                self.max_drawdown_pct = (dd / self.peak_balance_vnd) * 100.0

        today_str = time.strftime("%Y-%m-%d", time.localtime(ts))
        self.daily_pnl_vnd[today_str] = self.daily_pnl_vnd.get(today_str, 0.0) + (pnl_vnd - fee_vnd)

        self.trade_history.append({
            "timestamp": ts,
            "symbol": symbol,
            "side": side,
            "price": price,
            "quantity": quantity,
            "fee_vnd": fee_vnd,
            "pnl_vnd": pnl_vnd,
            "net_pnl_vnd": pnl_vnd - fee_vnd,
        })

    def update_unrealized_pnl(self, current_price: float, position_qty: float, avg_entry_price: float):
        if abs(position_qty) < 1e-8 or avg_entry_price <= 0:
            self.unrealized_pnl_vnd = 0.0
        else:
            self.unrealized_pnl_vnd = (current_price - avg_entry_price) * position_qty

    def get_summary(self) -> Dict[str, Any]:
        win_rate = (self.winning_trades / self.total_trades * 100.0) if self.total_trades > 0 else 0.0
        today_str = time.strftime("%Y-%m-%d")
        daily_loss = min(0.0, self.daily_pnl_vnd.get(today_str, 0.0))

        return {
            "entity_id": self.entity_id,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate_pct": round(win_rate, 2),
            "realized_pnl_vnd": round(self.realized_pnl_vnd, 2),
            "unrealized_pnl_vnd": round(self.unrealized_pnl_vnd, 2),
            "total_pnl_vnd": round(self.realized_pnl_vnd + self.unrealized_pnl_vnd, 2),
            "fees_paid_vnd": round(self.fees_paid_vnd, 2),
            "max_drawdown_vnd": round(self.max_drawdown_vnd, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "daily_pnl_vnd": round(self.daily_pnl_vnd.get(today_str, 0.0), 2),
        }
