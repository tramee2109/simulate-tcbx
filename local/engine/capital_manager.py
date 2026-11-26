"""
engine/capital_manager.py
Central capital management, per-strategy sleeves, and strict reservation ledger.
Guarantees strategies within an account cannot double-spend VND or sell the same BTC.
"""

import threading
import time
from typing import Any, Dict, List, Optional, Tuple
from monitoring.logger import get_logger

logger = get_logger("capital_manager")


class CapitalManager:
    """
    Central capital ledger and reservation authority.
    Manages 150M VND per account (90M deployable, 60M reserve).
    Enforces per-strategy sleeves (18M or 22.5M) and tracks active reservations.
    """

    def __init__(self):
        self._lock = threading.Lock()

        # Account allocations: account_id -> {initial, deployable, reserve}
        self._account_capital: Dict[str, Dict[str, float]] = {}

        # Strategy allocations: strategy_id -> {account_id, budget_vnd, spent_vnd, role}
        self._strategy_capital: Dict[str, Dict[str, Any]] = {}

        # Active reservations: reservation_id -> record
        self._reservations: Dict[str, Dict[str, Any]] = {}

        # Total reserved per account: account_id -> {VND: float, BTC: float}
        self._account_reserved: Dict[str, Dict[str, float]] = {}

    def register_account(
        self,
        account_id: str,
        initial_vnd: float = 150_000_000.0,
        deployable_vnd: float = 90_000_000.0,
        reserve_vnd: float = 60_000_000.0,
    ):
        with self._lock:
            self._account_capital[account_id] = {
                "initial_vnd": initial_vnd,
                "deployable_vnd": deployable_vnd,
                "reserve_vnd": reserve_vnd,
            }
            self._account_reserved.setdefault(account_id, {"VND": 0.0, "BTC": 0.0})

    def register_strategy(
        self,
        strategy_id: str,
        account_id: str,
        budget_vnd: float,
        is_paper_only: bool = False,
    ):
        with self._lock:
            # Behavioral benchmark strategies STR-091..100 have zero live capital
            allocated = 0.0 if is_paper_only else budget_vnd
            self._strategy_capital[strategy_id] = {
                "strategy_id": strategy_id,
                "account_id": account_id,
                "allocated_vnd": allocated,
                "active_reserved_vnd": 0.0,
                "spent_vnd": 0.0,
                "is_paper_only": is_paper_only,
            }

    def reserve_capital(
        self,
        reservation_id: str,
        account_id: str,
        strategy_id: str,
        asset: str,
        amount: float,
        available_balance: float,
        reason: str = "OPEN_LIMIT_ORDER",
    ) -> Tuple[bool, str]:
        """
        Reserve capital before order placement.
        Validates:
        1. Strategy sleeve budget (for VND buys)
        2. Account deployable budget limit (total active reservations <= 90M)
        3. Actual available balance in wallet
        """
        with self._lock:
            if amount <= 0:
                return False, f"Invalid reservation amount: {amount}"

            acc_cap = self._account_capital.get(account_id)
            if not acc_cap:
                return False, f"Account {account_id} not registered in CapitalManager"

            strat_cap = self._strategy_capital.get(strategy_id)
            if not strat_cap:
                return False, f"Strategy {strategy_id} not registered in CapitalManager"

            asset_upper = asset.upper()

            if asset_upper == "VND":
                # Check paper-only behavioral rule
                if strat_cap["is_paper_only"]:
                    # Paper-only strategies do not consume live capital
                    pass
                else:
                    # 1. Strategy sleeve limit check
                    new_strat_reserved = strat_cap["active_reserved_vnd"] + amount
                    if new_strat_reserved > strat_cap["allocated_vnd"]:
                        return False, (
                            f"Strategy {strategy_id} sleeve exceeded: requested {amount:,.2f} VND, "
                            f"already reserved {strat_cap['active_reserved_vnd']:,.2f} VND "
                            f"(Sleeve limit: {strat_cap['allocated_vnd']:,.2f} VND)"
                        )

                    # 2. Account deployable limit check (90M cap)
                    current_acc_reserved = self._account_reserved[account_id]["VND"]
                    if (current_acc_reserved + amount) > acc_cap["deployable_vnd"]:
                        return False, (
                            f"Account {account_id} deployable budget exceeded: requested {amount:,.2f} VND, "
                            f"already reserved {current_acc_reserved:,.2f} VND "
                            f"(Deployable cap: {acc_cap['deployable_vnd']:,.2f} VND)"
                        )

                # 3. Available balance check
                current_acc_reserved = self._account_reserved[account_id]["VND"]
                unreserved_vnd = available_balance - current_acc_reserved
                if amount > unreserved_vnd:
                    return False, (
                        f"Insufficient unreserved VND in account {account_id}: "
                        f"requested {amount:,.2f} VND, available unreserved {unreserved_vnd:,.2f} VND"
                    )

                # Record reservation
                self._account_reserved[account_id]["VND"] += amount
                strat_cap["active_reserved_vnd"] += amount

            elif asset_upper == "BTC":
                # Validate unreserved BTC ownership (strict no short selling)
                current_acc_reserved_btc = self._account_reserved[account_id]["BTC"]
                unreserved_btc = available_balance - current_acc_reserved_btc
                if amount > unreserved_btc:
                    return False, (
                        f"Insufficient unreserved BTC in account {account_id}: "
                        f"requested {amount:.4f} BTC, available unreserved {unreserved_btc:.4f} BTC"
                    )

                self._account_reserved[account_id]["BTC"] += amount

            else:
                return False, f"Unsupported asset for reservation: {asset}"

            self._reservations[reservation_id] = {
                "reservation_id": reservation_id,
                "account_id": account_id,
                "strategy_id": strategy_id,
                "asset": asset_upper,
                "amount": amount,
                "reason": reason,
                "timestamp": time.time(),
            }

            logger.info(
                f"Reserved {amount:,.2f} {asset_upper} for [{strategy_id}@{account_id}] (ResID: {reservation_id})"
            )
            return True, "OK"

    def release_reservation(self, reservation_id: str) -> bool:
        """Release a reservation (e.g. order canceled, rejected, or completed)."""
        with self._lock:
            res = self._reservations.pop(reservation_id, None)
            if not res:
                return False

            acc_id = res["account_id"]
            strat_id = res["strategy_id"]
            asset = res["asset"]
            amount = res["amount"]

            if asset == "VND":
                self._account_reserved[acc_id]["VND"] = max(0.0, self._account_reserved[acc_id]["VND"] - amount)
                if strat_id in self._strategy_capital:
                    self._strategy_capital[strat_id]["active_reserved_vnd"] = max(
                        0.0, self._strategy_capital[strat_id]["active_reserved_vnd"] - amount
                    )
            elif asset == "BTC":
                self._account_reserved[acc_id]["BTC"] = max(0.0, self._account_reserved[acc_id]["BTC"] - amount)

            logger.info(f"Released reservation {reservation_id}: {amount} {asset}")
            return True

    def get_reserved_amounts(self, account_id: str) -> Dict[str, float]:
        with self._lock:
            return dict(self._account_reserved.get(account_id, {"VND": 0.0, "BTC": 0.0}))

    def get_strategy_allocation(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return dict(self._strategy_capital.get(strategy_id, {}))
