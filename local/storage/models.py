"""
storage/models.py
Database data models and entity structures.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import time


@dataclass
class AccountRecord:
    account_id: str  # ACC-01 .. ACC-20
    username: str
    nickname: str
    label: str
    group_name: str
    scope: str
    initial_capital_vnd: float
    deployable_budget_vnd: float
    reserve_vnd: float
    actual_vnd: float = 0.0
    actual_btc: float = 0.0
    available_vnd: float = 0.0
    available_btc: float = 0.0
    reserved_vnd: float = 0.0
    reserved_btc: float = 0.0
    realized_pnl_vnd: float = 0.0
    unrealized_pnl_vnd: float = 0.0
    status: str = "INITIALIZED"  # INITIALIZED, VERIFIED, ACCOUNT_UNVERIFIED, DEGRADED
    updated_at: float = field(default_factory=time.time)


@dataclass
class StrategyRecord:
    strategy_id: str  # STR-001 .. STR-100
    name: str
    family: str
    account_id: str
    role: str
    allocated_capital_vnd: float
    status: str = "REGISTERED"  # REGISTERED, ACTIVE, PAUSED, DISABLED_DATA_REQUIREMENT, PAPER_ONLY
    realized_pnl_vnd: float = 0.0
    unrealized_pnl_vnd: float = 0.0
    total_trades: int = 0
    win_rate_pct: float = 0.0
    updated_at: float = field(default_factory=time.time)


@dataclass
class OrderRecord:
    order_id: str
    client_order_id: str
    account_id: str
    strategy_id: str
    symbol: str
    side: str  # BUY or SELL
    order_type: str  # LIMIT only
    price: float
    quantity: float
    filled_quantity: float = 0.0
    status: str = "NEW"  # NEW, PARTIALLY_FILLED, FILLED, CANCELED, REJECTED
    mode: str = "PAPER"  # PAPER or LIVE
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    notes: str = ""


@dataclass
class FillRecord:
    fill_id: str
    order_id: str
    account_id: str
    strategy_id: str
    symbol: str
    side: str
    price: float
    quantity: float
    fee_vnd: float
    pnl_vnd: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class CapitalReservationRecord:
    reservation_id: str
    account_id: str
    strategy_id: str
    asset: str  # VND or BTC
    amount: float
    reason: str
    status: str = "ACTIVE"  # ACTIVE, RELEASED, CONSUMED
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
