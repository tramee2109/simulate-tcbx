"""
storage/database.py
SQLite database manager for persistent state, order histories, and audit records.
"""

import os
import sqlite3
import threading
from typing import Any, Dict, List, Optional
from storage.models import AccountRecord, StrategyRecord, OrderRecord, FillRecord, CapitalReservationRecord
from monitoring.logger import get_logger

logger = get_logger("database")


class DatabaseManager:
    """Thread-safe SQLite manager for all engine states and transactions."""

    def __init__(self, db_path: str = "data/tcex_engine.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._lock = threading.Lock()
        self._init_tables()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Accounts
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS accounts (
                        account_id TEXT PRIMARY KEY,
                        username TEXT,
                        nickname TEXT,
                        label TEXT,
                        group_name TEXT,
                        scope TEXT,
                        initial_capital_vnd REAL,
                        deployable_budget_vnd REAL,
                        reserve_vnd REAL,
                        actual_vnd REAL,
                        actual_btc REAL,
                        available_vnd REAL,
                        available_btc REAL,
                        reserved_vnd REAL,
                        reserved_btc REAL,
                        realized_pnl_vnd REAL,
                        unrealized_pnl_vnd REAL,
                        status TEXT,
                        updated_at REAL
                    )
                """)

                # Strategies
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS strategies (
                        strategy_id TEXT PRIMARY KEY,
                        name TEXT,
                        family TEXT,
                        account_id TEXT,
                        role TEXT,
                        allocated_capital_vnd REAL,
                        status TEXT,
                        realized_pnl_vnd REAL,
                        unrealized_pnl_vnd REAL,
                        total_trades INTEGER,
                        win_rate_pct REAL,
                        updated_at REAL
                    )
                """)

                # Orders
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS orders (
                        order_id TEXT PRIMARY KEY,
                        client_order_id TEXT UNIQUE,
                        account_id TEXT,
                        strategy_id TEXT,
                        symbol TEXT,
                        side TEXT,
                        order_type TEXT,
                        price REAL,
                        quantity REAL,
                        filled_quantity REAL,
                        status TEXT,
                        mode TEXT,
                        created_at REAL,
                        updated_at REAL,
                        notes TEXT
                    )
                """)

                # Fills
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS fills (
                        fill_id TEXT PRIMARY KEY,
                        order_id TEXT,
                        account_id TEXT,
                        strategy_id TEXT,
                        symbol TEXT,
                        side TEXT,
                        price REAL,
                        quantity REAL,
                        fee_vnd REAL,
                        pnl_vnd REAL,
                        timestamp REAL
                    )
                """)

                # Capital Reservations
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS reservations (
                        reservation_id TEXT PRIMARY KEY,
                        account_id TEXT,
                        strategy_id TEXT,
                        asset TEXT,
                        amount REAL,
                        reason TEXT,
                        status TEXT,
                        created_at REAL,
                        updated_at REAL
                    )
                """)

                # System Snapshots
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS system_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL,
                        mode TEXT,
                        total_equity_vnd REAL,
                        total_realized_pnl_vnd REAL,
                        total_unrealized_pnl_vnd REAL,
                        active_strategies INTEGER,
                        open_orders INTEGER
                    )
                """)

                conn.commit()

    def upsert_account(self, acc: AccountRecord):
        with self._lock:
            with self._get_connection() as conn:
                conn.cursor().execute("""
                    INSERT INTO accounts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(account_id) DO UPDATE SET
                        username=excluded.username,
                        nickname=excluded.nickname,
                        label=excluded.label,
                        actual_vnd=excluded.actual_vnd,
                        actual_btc=excluded.actual_btc,
                        available_vnd=excluded.available_vnd,
                        available_btc=excluded.available_btc,
                        reserved_vnd=excluded.reserved_vnd,
                        reserved_btc=excluded.reserved_btc,
                        realized_pnl_vnd=excluded.realized_pnl_vnd,
                        unrealized_pnl_vnd=excluded.unrealized_pnl_vnd,
                        status=excluded.status,
                        updated_at=excluded.updated_at
                """, (
                    acc.account_id, acc.username, acc.nickname, acc.label, acc.group_name, acc.scope,
                    acc.initial_capital_vnd, acc.deployable_budget_vnd, acc.reserve_vnd,
                    acc.actual_vnd, acc.actual_btc, acc.available_vnd, acc.available_btc,
                    acc.reserved_vnd, acc.reserved_btc, acc.realized_pnl_vnd, acc.unrealized_pnl_vnd,
                    acc.status, acc.updated_at
                ))
                conn.commit()

    def upsert_strategy(self, strat: StrategyRecord):
        with self._lock:
            with self._get_connection() as conn:
                conn.cursor().execute("""
                    INSERT INTO strategies VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(strategy_id) DO UPDATE SET
                        name=excluded.name,
                        family=excluded.family,
                        account_id=excluded.account_id,
                        role=excluded.role,
                        allocated_capital_vnd=excluded.allocated_capital_vnd,
                        status=excluded.status,
                        realized_pnl_vnd=excluded.realized_pnl_vnd,
                        unrealized_pnl_vnd=excluded.unrealized_pnl_vnd,
                        total_trades=excluded.total_trades,
                        win_rate_pct=excluded.win_rate_pct,
                        updated_at=excluded.updated_at
                """, (
                    strat.strategy_id, strat.name, strat.family, strat.account_id, strat.role,
                    strat.allocated_capital_vnd, strat.status, strat.realized_pnl_vnd, strat.unrealized_pnl_vnd,
                    strat.total_trades, strat.win_rate_pct, strat.updated_at
                ))
                conn.commit()

    def insert_order(self, order: OrderRecord):
        with self._lock:
            with self._get_connection() as conn:
                conn.cursor().execute("""
                    INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(order_id) DO UPDATE SET
                        filled_quantity=excluded.filled_quantity,
                        status=excluded.status,
                        updated_at=excluded.updated_at,
                        notes=excluded.notes
                """, (
                    order.order_id, order.client_order_id, order.account_id, order.strategy_id,
                    order.symbol, order.side, order.order_type, order.price, order.quantity,
                    order.filled_quantity, order.status, order.mode, order.created_at, order.updated_at, order.notes
                ))
                conn.commit()

    def insert_fill(self, fill: FillRecord):
        with self._lock:
            with self._get_connection() as conn:
                conn.cursor().execute("""
                    INSERT INTO fills VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    fill.fill_id, fill.order_id, fill.account_id, fill.strategy_id,
                    fill.symbol, fill.side, fill.price, fill.quantity, fill.fee_vnd,
                    fill.pnl_vnd, fill.timestamp
                ))
                conn.commit()

    def get_all_accounts(self) -> List[Dict[str, Any]]:
        with self._lock:
            with self._get_connection() as conn:
                rows = conn.cursor().execute("SELECT * FROM accounts").fetchall()
                return [dict(r) for r in rows]

    def get_all_strategies(self) -> List[Dict[str, Any]]:
        with self._lock:
            with self._get_connection() as conn:
                rows = conn.cursor().execute("SELECT * FROM strategies").fetchall()
                return [dict(r) for r in rows]

    def get_open_orders(self, account_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            with self._get_connection() as conn:
                if account_id:
                    rows = conn.cursor().execute(
                        "SELECT * FROM orders WHERE account_id=? AND status IN ('NEW', 'PARTIALLY_FILLED')",
                        (account_id,)
                    ).fetchall()
                else:
                    rows = conn.cursor().execute(
                        "SELECT * FROM orders WHERE status IN ('NEW', 'PARTIALLY_FILLED')"
                    ).fetchall()
                return [dict(r) for r in rows]
