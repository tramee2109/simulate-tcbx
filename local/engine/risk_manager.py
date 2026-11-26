"""
engine/risk_manager.py
Comprehensive multi-tier risk control engine.
Enforces LIMIT-only, balance validation, reservation ledger, max deployment,
duplicate order prevention, stale data rejection, and account/strategy isolation.
"""

import hashlib
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
from monitoring.logger import get_logger, log_audit_event

logger = get_logger("risk_manager")


class RiskManager:
    """
    Risk validation engine enforcing hard controls before any order reaches execution.
    A failure or limit breach isolates only the affected strategy or account.
    """

    def __init__(
        self,
        capital_manager: Any,
        portfolio_manager: Any,
        max_open_orders_per_strategy: int = 5,
        max_open_orders_per_account: int = 20,
        min_order_qty_btc: float = 0.01,
        max_order_qty_btc: float = 1.0,
        min_notional_vnd: float = 10_000_000.0,
        max_daily_drawdown_pct: float = 10.0,
        stale_market_data_threshold_sec: float = 30.0,
        duplicate_window_sec: float = 3.0,
    ):
        self.capital_manager = capital_manager
        self.portfolio_manager = portfolio_manager
        self.max_open_orders_per_strategy = max_open_orders_per_strategy
        self.max_open_orders_per_account = max_open_orders_per_account
        self.min_order_qty_btc = min_order_qty_btc
        self.max_order_qty_btc = max_order_qty_btc
        self.min_notional_vnd = min_notional_vnd
        self.max_daily_drawdown_pct = max_daily_drawdown_pct
        self.stale_threshold_sec = stale_market_data_threshold_sec
        self.duplicate_window_sec = duplicate_window_sec

        self._emergency_stop = False
        self._disabled_accounts: Dict[str, str] = {}
        self._disabled_strategies: Dict[str, str] = {}
        self._recent_orders_hash: Dict[str, float] = {}
        self._open_orders_by_strategy: Dict[str, int] = {}
        self._open_orders_by_account: Dict[str, int] = {}
        self._lock = threading.Lock()

    def set_emergency_stop(self, stop: bool = True, reason: str = "Operator manual stop"):
        with self._lock:
            self._emergency_stop = stop
            if stop:
                logger.critical(f"EMERGENCY STOP ACTIVATED: {reason}. All new order submissions blocked.")
                log_audit_event("EMERGENCY_STOP", "*", "*", reason)
            else:
                logger.info(f"EMERGENCY STOP DEACTIVATED: {reason}.")
                log_audit_event("EMERGENCY_STOP_OFF", "*", "*", reason)

    def disable_account(self, account_id: str, reason: str):
        with self._lock:
            self._disabled_accounts[account_id] = reason
            logger.warning(f"Account [{account_id}] disabled by RiskManager: {reason}")
            log_audit_event("DISABLE_ACCOUNT", account_id, "*", reason)

    def disable_strategy(self, strategy_id: str, reason: str):
        with self._lock:
            self._disabled_strategies[strategy_id] = reason
            logger.warning(f"Strategy [{strategy_id}] disabled by RiskManager: {reason}")
            log_audit_event("DISABLE_STRATEGY", "*", strategy_id, reason)

    def _reject(
        self,
        account_id: str,
        strategy_id: str,
        reason: str,
        details: str = "",
    ) -> Tuple[bool, str]:
        log_audit_event("RISK_REJECTED", account_id, strategy_id, reason, details)
        return False, reason

    def validate_order(
        self,
        account_id: str,
        strategy_id: str,
        symbol: str,
        side: str,
        order_type: str,
        price: float,
        quantity: float,
        market_data_age_sec: float = 0.0,
    ) -> Tuple[bool, str]:
        """
        Perform all risk checks before order submission.
        Returns (is_valid, rejection_reason).
        """
        with self._lock:
            details = f"Symbol={symbol} Side={side} Price={price:,.2f} Qty={quantity:.4f}"

            # 1. Global emergency stop check
            if self._emergency_stop:
                return self._reject(account_id, strategy_id, "RISK_REJECTED: Global emergency stop is active", details)

            # 2. Account isolation check
            if account_id in self._disabled_accounts:
                return self._reject(account_id, strategy_id, f"RISK_REJECTED: Account {account_id} is disabled ({self._disabled_accounts[account_id]})", details)

            # 3. Strategy isolation check
            if strategy_id in self._disabled_strategies:
                return self._reject(account_id, strategy_id, f"RISK_REJECTED: Strategy {strategy_id} is disabled ({self._disabled_strategies[strategy_id]})", details)

            # 4. Symbol restriction (BTC_VND only)
            if symbol != "BTC_VND":
                return self._reject(account_id, strategy_id, f"RISK_REJECTED: Forbidden symbol {symbol}. Venue strictly restricted to BTC_VND", details)

            # 5. Order type enforcement (LIMIT only)
            if order_type.upper() != "LIMIT":
                return self._reject(account_id, strategy_id, f"RISK_REJECTED: Order type {order_type} forbidden. Strict LIMIT-only venue enforcement", details)

            # 6. Stale market data rejection
            if market_data_age_sec > self.stale_threshold_sec:
                return self._reject(account_id, strategy_id, f"RISK_REJECTED: Market data stale ({market_data_age_sec:.1f}s > {self.stale_threshold_sec}s)", details)

            # 7. Quantity & Lot size checks
            if quantity < self.min_order_qty_btc:
                return self._reject(account_id, strategy_id, f"RISK_REJECTED: Quantity {quantity} below minimum {self.min_order_qty_btc} BTC", details)
            if quantity > self.max_order_qty_btc:
                return self._reject(account_id, strategy_id, f"RISK_REJECTED: Quantity {quantity} exceeds maximum allowable {self.max_order_qty_btc} BTC", details)

            # 8. Price & Notional checks
            if price <= 0:
                return self._reject(account_id, strategy_id, f"RISK_REJECTED: Price must be positive, got {price}", details)
            notional = price * quantity
            if notional < self.min_notional_vnd:
                return self._reject(account_id, strategy_id, f"RISK_REJECTED: Order notional {notional:,.2f} VND below minimum {self.min_notional_vnd:,.2f} VND", details)

            # 9. Duplicate order prevention
            now = time.time()
            order_hash = hashlib.sha256(
                f"{strategy_id}:{account_id}:{side}:{round(price, 2)}:{round(quantity, 4)}".encode()
            ).hexdigest()
            last_time = self._recent_orders_hash.get(order_hash, 0.0)
            if (now - last_time) < self.duplicate_window_sec:
                return self._reject(account_id, strategy_id, f"RISK_REJECTED: Duplicate order detected within {self.duplicate_window_sec}s window", details)
            self._recent_orders_hash[order_hash] = now

            # Clean up old hashes
            if len(self._recent_orders_hash) > 500:
                cutoff = now - (self.duplicate_window_sec * 5)
                self._recent_orders_hash = {k: v for k, v in self._recent_orders_hash.items() if v > cutoff}

            # 10. Maximum open orders check
            strat_orders = self._open_orders_by_strategy.get(strategy_id, 0)
            if strat_orders >= self.max_open_orders_per_strategy:
                return self._reject(account_id, strategy_id, f"RISK_REJECTED: Strategy max open orders ({self.max_open_orders_per_strategy}) reached", details)

            acc_orders = self._open_orders_by_account.get(account_id, 0)
            if acc_orders >= self.max_open_orders_per_account:
                return self._reject(account_id, strategy_id, f"RISK_REJECTED: Account max open orders ({self.max_open_orders_per_account}) reached", details)

            # 11. Balance & Reservation check via CapitalManager & PortfolioManager
            portfolio = self.portfolio_manager.get_account_portfolio(account_id, price)
            side_upper = side.upper()

            if side_upper == "BUY":
                # Validate available VND
                available_vnd = portfolio["available_vnd"]
                res_id = f"RES_BUY_{strategy_id}_{int(now*1000)}"
                can_reserve, reason = self.capital_manager.reserve_capital(
                    reservation_id=res_id,
                    account_id=account_id,
                    strategy_id=strategy_id,
                    asset="VND",
                    amount=notional,
                    available_balance=portfolio["actual_vnd"],
                    reason="LIMIT_BUY_ORDER",
                )
                if not can_reserve:
                    return self._reject(account_id, strategy_id, f"RISK_REJECTED: Capital reservation failed ({reason})", details)

            elif side_upper == "SELL":
                # Validate owned unreserved BTC (strict no short selling)
                res_id = f"RES_SELL_{strategy_id}_{int(now*1000)}"
                can_reserve, reason = self.capital_manager.reserve_capital(
                    reservation_id=res_id,
                    account_id=account_id,
                    strategy_id=strategy_id,
                    asset="BTC",
                    amount=quantity,
                    available_balance=portfolio["actual_btc"],
                    reason="LIMIT_SELL_ORDER",
                )
                if not can_reserve:
                    return self._reject(account_id, strategy_id, f"RISK_REJECTED: BTC reservation failed ({reason})", details)

            # Increment open orders
            self._open_orders_by_strategy[strategy_id] = strat_orders + 1
            self._open_orders_by_account[account_id] = acc_orders + 1

            return True, "PASSED"

    def order_closed(self, account_id: str, strategy_id: str):
        """Decrement open order counts when order fills or cancels."""
        with self._lock:
            if strategy_id in self._open_orders_by_strategy:
                self._open_orders_by_strategy[strategy_id] = max(0, self._open_orders_by_strategy[strategy_id] - 1)
            if account_id in self._open_orders_by_account:
                self._open_orders_by_account[account_id] = max(0, self._open_orders_by_account[account_id] - 1)
