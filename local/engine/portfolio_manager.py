"""
engine/portfolio_manager.py
Portfolio and wallet balance state tracker for all 20 accounts.
Calculates positions, total equity, available vs reserved balances, realized & unrealized PnL in VND.
"""

import threading
from typing import Any, Dict, List, Optional
from monitoring.logger import get_logger

logger = get_logger("portfolio_manager")


class PortfolioManager:
    """Manages multi-account portfolios, positions, and live equity in VND."""

    def __init__(self, capital_manager: Any):
        self.capital_manager = capital_manager
        self._lock = threading.Lock()

        # Account portfolios: account_id -> {actual_vnd, actual_btc, avg_btc_entry_price, realized_pnl, ...}
        self._portfolios: Dict[str, Dict[str, Any]] = {}

    def init_account(self, account_id: str, initial_vnd: float = 150_000_000.0):
        with self._lock:
            self._portfolios[account_id] = {
                "account_id": account_id,
                "initial_capital_vnd": initial_vnd,
                "actual_vnd": initial_vnd,
                "actual_btc": 0.0,
                "avg_btc_entry_price": 0.0,
                "realized_pnl_vnd": 0.0,
                "unrealized_pnl_vnd": 0.0,
                "open_orders_count": 0,
            }

    def update_actual_balances(self, account_id: str, actual_vnd: float, actual_btc: float):
        with self._lock:
            p = self._portfolios.setdefault(account_id, {
                "account_id": account_id,
                "initial_capital_vnd": 150_000_000.0,
                "actual_vnd": actual_vnd,
                "actual_btc": actual_btc,
                "avg_btc_entry_price": 0.0,
                "realized_pnl_vnd": 0.0,
                "unrealized_pnl_vnd": 0.0,
                "open_orders_count": 0,
            })
            p["actual_vnd"] = actual_vnd
            p["actual_btc"] = actual_btc

    def record_fill(
        self,
        account_id: str,
        strategy_id: str,
        side: str,
        price: float,
        quantity: float,
        fee_vnd: float,
    ):
        with self._lock:
            p = self._portfolios.get(account_id)
            if not p:
                return

            side_upper = side.upper()
            cost_vnd = price * quantity

            if side_upper == "BUY":
                # Increase BTC, decrease VND
                old_btc = p["actual_btc"]
                old_avg = p["avg_btc_entry_price"]
                new_btc = old_btc + quantity
                if new_btc > 0:
                    p["avg_btc_entry_price"] = ((old_btc * old_avg) + cost_vnd) / new_btc
                p["actual_btc"] = new_btc
                p["actual_vnd"] -= (cost_vnd + fee_vnd)

            elif side_upper == "SELL":
                # Realize PnL
                entry_cost = p["avg_btc_entry_price"] * quantity
                trade_pnl = (cost_vnd - entry_cost) - fee_vnd
                p["realized_pnl_vnd"] += trade_pnl
                p["actual_btc"] = max(0.0, p["actual_btc"] - quantity)
                p["actual_vnd"] += (cost_vnd - fee_vnd)
                if p["actual_btc"] <= 1e-8:
                    p["avg_btc_entry_price"] = 0.0

    def update_market_price(self, btc_vnd_mid_price: float):
        """Update unrealized PnL for all accounts based on latest mid price."""
        if not btc_vnd_mid_price or btc_vnd_mid_price <= 0:
            return

        with self._lock:
            for p in self._portfolios.values():
                btc_qty = p["actual_btc"]
                avg_entry = p["avg_btc_entry_price"]
                if btc_qty > 0 and avg_entry > 0:
                    p["unrealized_pnl_vnd"] = (btc_vnd_mid_price - avg_entry) * btc_qty
                else:
                    p["unrealized_pnl_vnd"] = 0.0

    def get_account_portfolio(self, account_id: str, btc_vnd_price: float = 0.0) -> Dict[str, Any]:
        with self._lock:
            p = dict(self._portfolios.get(account_id, {}))
            reserved = self.capital_manager.get_reserved_amounts(account_id)

            actual_vnd = p.get("actual_vnd", 0.0)
            actual_btc = p.get("actual_btc", 0.0)
            res_vnd = reserved.get("VND", 0.0)
            res_btc = reserved.get("BTC", 0.0)

            avail_vnd = max(0.0, actual_vnd - res_vnd)
            avail_btc = max(0.0, actual_btc - res_btc)

            btc_value_vnd = actual_btc * btc_vnd_price if btc_vnd_price > 0 else 0.0
            total_equity_vnd = actual_vnd + btc_value_vnd

            return {
                "account_id": account_id,
                "actual_vnd": actual_vnd,
                "actual_btc": actual_btc,
                "reserved_vnd": res_vnd,
                "reserved_btc": res_btc,
                "available_vnd": avail_vnd,
                "available_btc": avail_btc,
                "btc_value_vnd": btc_value_vnd,
                "total_equity_vnd": total_equity_vnd,
                "realized_pnl_vnd": p.get("realized_pnl_vnd", 0.0),
                "unrealized_pnl_vnd": p.get("unrealized_pnl_vnd", 0.0),
            }

    def get_system_portfolio_summary(self, btc_vnd_price: float = 0.0) -> Dict[str, Any]:
        total_vnd = 0.0
        total_btc = 0.0
        total_equity = 0.0
        total_realized_pnl = 0.0
        total_unrealized_pnl = 0.0

        for acc_id in sorted(self._portfolios.keys()):
            p = self.get_account_portfolio(acc_id, btc_vnd_price)
            total_vnd += p["actual_vnd"]
            total_btc += p["actual_btc"]
            total_equity += p["total_equity_vnd"]
            total_realized_pnl += p["realized_pnl_vnd"]
            total_unrealized_pnl += p["unrealized_pnl_vnd"]

        return {
            "total_accounts": len(self._portfolios),
            "total_actual_vnd": round(total_vnd, 2),
            "total_actual_btc": round(total_btc, 4),
            "total_equity_vnd": round(total_equity, 2),
            "total_realized_pnl_vnd": round(total_realized_pnl, 2),
            "total_unrealized_pnl_vnd": round(total_unrealized_pnl, 2),
            "reference_btc_price_vnd": btc_vnd_price,
        }
