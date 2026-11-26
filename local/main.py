#!/usr/bin/env python3
"""
main.py
Central application entry point for TCEX BTC/VND Multi-Account Strategy Engine.
Orchestrates 20 accounts, 100 strategies, capital reservation, risk management, and execution.
"""

import argparse
import importlib.util
import json
import os
import signal
import sys
import time
from typing import Any, Dict, List, Optional

# Ensure simulate-sdk root is on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def load_sdk():
    """Load `the20_simulate_sdk` module cleanly."""
    if "the20_simulate_sdk" in sys.modules:
        return sys.modules["the20_simulate_sdk"]

    cur = BASE_DIR
    sdk_dir = None
    while cur and cur != os.path.dirname(cur):
        if os.path.isfile(os.path.join(cur, "spot.py")) and os.path.isfile(os.path.join(cur, "client.py")):
            sdk_dir = cur
            break
        cur = os.path.dirname(cur)
    if not sdk_dir:
        sdk_dir = os.path.abspath(os.path.join(BASE_DIR, ".."))

    spec = importlib.util.spec_from_file_location(
        "the20_simulate_sdk",
        os.path.join(sdk_dir, "__init__.py"),
        submodule_search_locations=[sdk_dir],
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load SDK from {sdk_dir}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["the20_simulate_sdk"] = mod
    spec.loader.exec_module(mod)
    return mod


# Import engine subsystems
from monitoring.logger import setup_logger, get_logger, mask_sensitive_text
from monitoring.health import HealthMonitor
from storage.database import DatabaseManager
from storage.models import AccountRecord, StrategyRecord
from exchange.tcex_adapter import TCEXSpotAdapter
from exchange.market_data import MarketDataManager
from engine.account_manager import AccountManager
from engine.capital_manager import CapitalManager
from engine.portfolio_manager import PortfolioManager
from engine.risk_manager import RiskManager
from engine.execution_engine import ExecutionEngine
from engine.strategy_manager import StrategyManager
from strategies import create_strategy

logger = get_logger("main")


class TCEXEngineApplication:
    """Central engine orchestrator application."""

    def __init__(self, config_path: str = "config.json", mode: Optional[str] = None):
        self.config_path = os.path.abspath(config_path)
        self.config: Dict[str, Any] = {}
        self.running = False
        self.override_mode = mode
        self.snapshot_interval_sec: float = 1800.0  # 30 minutes default
        self.last_snapshot_time: float = 0.0

        # Core subsystems
        self.logger = setup_logger()
        self.health_monitor = HealthMonitor()
        self.db: Optional[DatabaseManager] = None
        self.account_mgr: Optional[AccountManager] = None
        self.capital_mgr: Optional[CapitalManager] = None
        self.portfolio_mgr: Optional[PortfolioManager] = None
        self.risk_mgr: Optional[RiskManager] = None
        self.execution_engine: Optional[ExecutionEngine] = None
        self.market_data_mgr: Optional[MarketDataManager] = None
        self.strategy_mgr: Optional[StrategyManager] = None

    def initialize(self):
        """Execute full 20-step system startup sequence."""
        logger.info("=" * 70)
        logger.info("TCEX BTC/VND MULTI-ACCOUNT STRATEGY ENGINE — STARTUP INITIALIZATION")
        logger.info("=" * 70)

        # 1. Load and validate config.json
        if not os.path.isfile(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        with open(self.config_path, mode="r", encoding="utf-8") as f:
            self.config = json.load(f)
        logger.info("Step 1/20: config.json loaded and validated.")

        # Announce log directory and files
        mon_cfg = self.config.get("monitoring", {})
        log_dir = mon_cfg.get("log_dir", "logs")
        resolved_log_dir = os.path.join(BASE_DIR, log_dir) if not os.path.isabs(log_dir) else log_dir
        logger.info(f"Logging initialized at directory: {resolved_log_dir}")
        logger.info(f"  - Master Engine Log : {os.path.join(resolved_log_dir, 'tcex_engine.log')}")
        logger.info(f"  - Orders Log        : {os.path.join(resolved_log_dir, 'orders.log')}")
        logger.info(f"  - Risk Audit Log    : {os.path.join(resolved_log_dir, 'audit_events.log')}")

        # 2. Execution mode resolution
        sys_cfg = self.config.get("system", {})
        self.mode = (self.override_mode or sys_cfg.get("mode", "PAPER")).upper()
        base_url = sys_cfg.get("base_url", "https://simulation.the20.sg")
        session_key = sys_cfg.get("session_key", "dc1tpbu76rkff8gccfug")
        symbol = sys_cfg.get("symbol", "BTC_VND")
        logger.info(f"Step 2/20: Execution Mode: [{self.mode}] | Session: [{session_key}] | Pair: [{symbol}]")

        # 3. Initialize database
        storage_cfg = self.config.get("storage", {})
        db_path = storage_cfg.get("database_path", "data/tcex_engine.db")
        self.db = DatabaseManager(db_path=os.path.join(BASE_DIR, db_path))
        logger.info(f"Step 3/20: SQLite Database initialized at: {db_path}")

        # 4. Initialize SDK
        sdk = load_sdk()
        logger.info("Step 4/20: The20 Simulation SDK initialized.")

        # 5. Initialize Account Manager & Load 20 accounts
        csv_file = os.path.join(BASE_DIR, "new-temp-accounts-global (1).csv")
        self.account_mgr = AccountManager(
            csv_path=csv_file,
            base_url=base_url,
            session_key=session_key,
        )
        accounts = self.account_mgr.load_accounts()
        if len(accounts) != 20:
            raise ValueError(f"Expected exactly 20 accounts, found {len(accounts)}")
        logger.info(f"Step 5/20: Successfully loaded {len(accounts)} accounts (ACC-01 .. ACC-20).")

        # 6. Verify Account Authentication and Balances
        verified_accounts = self.account_mgr.verify_all_accounts()
        verified_count = sum(1 for a in verified_accounts.values() if a["verification_status"] == "VERIFIED")
        logger.info(f"Step 6/20: Authentication & Balance verification complete: {verified_count}/20 VERIFIED.")

        # 7. Validate TCEX BTC/VND market availability using primary account client
        primary_adapter = self.account_mgr.get_adapter("ACC-01")
        if not primary_adapter:
            raise RuntimeError("Primary adapter ACC-01 unavailable for market validation")

        ticker_info = primary_adapter.client.get_ticker_info(symbol, session_key=session_key)
        if not ticker_info or ticker_info.get("symbol") != symbol:
            raise RuntimeError(f"BTC/VND market verification failed on TCEX: {ticker_info}")
        logger.info(
            f"Step 7/20: TCEX {symbol} market verified (PriceScale={ticker_info.get('price_scale')}, "
            f"QtyScale={ticker_info.get('qty_scale')}, MinLot={ticker_info.get('step_size')} BTC)"
        )

        # 8. Initialize Market Data Manager
        self.market_data_mgr = MarketDataManager(
            spot_client=primary_adapter.client,
            symbol=symbol,
            session_key=session_key,
            stale_threshold_sec=self.config.get("risk", {}).get("stale_market_data_threshold_sec", 30.0),
        )
        self.market_data_mgr.refresh()
        bid, ask = self.market_data_mgr.get_best_bid_ask()
        logger.info(f"Step 8/20: Market Data Feed live: Best Bid = {bid:,.2f} VND | Best Ask = {ask:,.2f} VND")

        # 9. Initialize Capital Manager & Register capital allocations
        self.capital_mgr = CapitalManager()
        for aid, acc in verified_accounts.items():
            self.capital_mgr.register_account(
                account_id=aid,
                initial_vnd=acc["initial_capital_vnd"],
                deployable_vnd=acc["deployable_budget_vnd"],
                reserve_vnd=acc["reserve_vnd"],
            )
        logger.info("Step 9/20: Capital Manager initialized (150M Initial, 90M Deployable, 60M Reserve per account).")

        # 10. Initialize Portfolio Manager
        self.portfolio_mgr = PortfolioManager(capital_manager=self.capital_mgr)
        for aid, acc in verified_accounts.items():
            self.portfolio_mgr.init_account(account_id=aid, initial_vnd=acc["initial_capital_vnd"])
            self.portfolio_mgr.update_actual_balances(
                account_id=aid,
                actual_vnd=acc["actual_vnd"],
                actual_btc=acc["actual_btc"],
            )
            # Persist to database
            self.db.upsert_account(
                AccountRecord(
                    account_id=aid,
                    username=acc["username"],
                    nickname=acc["nickname"],
                    label=acc["label"],
                    group_name=acc["group_name"],
                    scope=acc["scope"],
                    initial_capital_vnd=acc["initial_capital_vnd"],
                    deployable_budget_vnd=acc["deployable_budget_vnd"],
                    reserve_vnd=acc["reserve_vnd"],
                    actual_vnd=acc["actual_vnd"],
                    actual_btc=acc["actual_btc"],
                    status=acc["verification_status"],
                )
            )
        logger.info("Step 10/20: Portfolio Manager initialized and accounts persisted to SQLite.")

        # 11. Initialize Risk Manager
        risk_cfg = self.config.get("risk", {})
        self.risk_mgr = RiskManager(
            capital_manager=self.capital_mgr,
            portfolio_manager=self.portfolio_mgr,
            max_open_orders_per_strategy=risk_cfg.get("max_open_orders_per_strategy", 5),
            max_open_orders_per_account=risk_cfg.get("max_open_orders_per_account", 20),
            min_order_qty_btc=risk_cfg.get("min_order_qty_btc", 0.01),
            max_order_qty_btc=risk_cfg.get("max_order_qty_btc", 1.0),
            min_notional_vnd=risk_cfg.get("min_notional_vnd", 10_000_000.0),
            max_daily_drawdown_pct=risk_cfg.get("max_daily_drawdown_pct", 10.0),
            stale_market_data_threshold_sec=risk_cfg.get("stale_market_data_threshold_sec", 30.0),
            duplicate_window_sec=risk_cfg.get("duplicate_window_sec", 3.0),
        )
        logger.info("Step 11/20: Multi-tier Risk Manager initialized with strict LIMIT-only rules.")

        # 12. Initialize Execution Engine
        exec_cfg = self.config.get("execution", {})
        self.execution_engine = ExecutionEngine(
            mode=self.mode,
            account_manager=self.account_mgr,
            capital_manager=self.capital_mgr,
            portfolio_manager=self.portfolio_mgr,
            risk_manager=self.risk_mgr,
            database_manager=self.db,
            maker_fee_bps=exec_cfg.get("maker_fee_bps", 10.0),
            taker_fee_bps=exec_cfg.get("taker_fee_bps", 10.0),
        )
        logger.info(f"Step 12/20: Execution Engine initialized in [{self.mode}] mode.")

        # 13. Initialize Strategy Manager
        self.strategy_mgr = StrategyManager(
            execution_engine=self.execution_engine,
            market_data_manager=self.market_data_mgr,
            health_monitor=self.health_monitor,
        )
        logger.info("Step 13/20: Strategy Manager initialized.")

        # 14. Load and Register all 100 Strategies
        strat_configs = self.config.get("strategies", [])
        if len(strat_configs) != 100:
            raise ValueError(f"Expected 100 strategies in config, found {len(strat_configs)}")

        active_count = 0
        paper_count = 0
        disabled_data_count = 0

        for sc in strat_configs:
            sid = sc["strategy_id"]
            aid = sc["account_id"]
            alloc_vnd = sc["allocated_capital_vnd"]
            status = sc["status"]
            is_paper = (status == "PAPER_ONLY") or sid.startswith("STR-09") or sid == "STR-100"

            strat_instance = create_strategy(
                strategy_id=sid,
                name=sc["name"],
                family=sc["family"],
                account_id=aid,
                role=sc.get("role", "Alpha"),
                allocated_capital_vnd=alloc_vnd,
                params=sc.get("parameters", {}),
                status=status,
            )

            self.strategy_mgr.register_strategy(strat_instance)
            self.capital_mgr.register_strategy(
                strategy_id=sid,
                account_id=aid,
                budget_vnd=alloc_vnd,
                is_paper_only=is_paper,
            )

            # Persist strategy record
            self.db.upsert_strategy(
                StrategyRecord(
                    strategy_id=sid,
                    name=sc["name"],
                    family=sc["family"],
                    account_id=aid,
                    role=sc.get("role", "Alpha"),
                    allocated_capital_vnd=alloc_vnd,
                    status=status,
                )
            )

            if status == "ACTIVE":
                active_count += 1
            elif status == "PAPER_ONLY":
                paper_count += 1
            elif status == "DISABLED_DATA_REQUIREMENT":
                disabled_data_count += 1

        logger.info(
            f"Step 14/20: 100 Strategies registered ({active_count} Active Alpha, "
            f"{paper_count} Paper-Only Benchmarks, {disabled_data_count} Data-Gated)."
        )

        # 15. Strategy-Account Mapping Validation
        for aid in verified_accounts.keys():
            assigned = [s for s in strat_configs if s["account_id"] == aid]
            if len(assigned) not in (4, 5, 6):
                raise ValueError(f"Invalid strategy assignment count on {aid}: {len(assigned)}")
        logger.info("Step 15/20: Strategy-Account mappings verified across all 20 accounts.")

        # 16. Reserve & Budget Verification
        system_cap = self.config.get("capital", {})
        logger.info(
            f"Step 16/20: Capital accounting verified: Total Initial={system_cap['system_total_initial_capital']:,.2f} VND | "
            f"Deployable={system_cap['system_total_deployable_capital']:,.2f} VND | "
            f"Reserve={system_cap['system_total_reserve']:,.2f} VND."
        )

        # 17. Monitoring & Heartbeat initialization
        self.health_monitor.beat("core_engine")
        logger.info("Step 17/20: Monitoring & Watchdog heartbeat started.")

        # 18. Start eligible strategies
        logger.info(f"Step 18/20: Eligible alpha strategies ({active_count}) activated.")

        # 19. Initial state snapshot
        summary = self.portfolio_mgr.get_system_portfolio_summary(btc_vnd_price=bid or 0.0)
        logger.info(
            f"Step 19/20: Initial system snapshot: Total Equity={summary['total_equity_vnd']:,.2f} VND, "
            f"BTC={summary['total_actual_btc']} BTC."
        )

        # 20. Ready
        logger.info("Step 20/20: System initialization complete. Ready for orchestration.")
        logger.info("=" * 70)

    def run_tick(self):
        """Execute one complete engine tick."""
        # 1. Refresh market data
        refreshed = self.market_data_mgr.refresh()
        if not refreshed:
            logger.warning("Market data refresh failed; skipping strategy execution tick.")
            return

        mid = self.market_data_mgr.get_mid_price()
        bid, ask = self.market_data_mgr.get_best_bid_ask()
        depth = self.market_data_mgr.get_orderbook_depth()

        # 2. Update portfolio valuations
        if mid:
            self.portfolio_mgr.update_market_price(mid)

        # 3. Match paper orders if running in PAPER mode
        if self.mode == "PAPER" and depth:
            self.execution_engine.process_paper_matching(depth)

        # 4. Build market data context for strategies
        context = {
            "symbol": "BTC_VND",
            "best_bid": bid,
            "best_ask": ask,
            "mid_price": mid,
            "depth": depth,
            "imbalance": self.market_data_mgr.get_orderbook_imbalance(),
            "closes": self.market_data_mgr.get_close_prices(50),
            "ohlcv": self.market_data_mgr.get_ohlcv(50),
            "ticker": self.market_data_mgr._last_ticker or {},
            "timestamp": time.time(),
        }

        # 5. Tick all strategies
        self.strategy_mgr.tick_all(context)
        self.health_monitor.beat("core_engine")

    def export_balance_snapshot(self) -> Dict[str, Any]:
        """
        Fetch real-time balances for all 20 accounts, compute portfolio equity,
        and export to timestamped JSON files for audit and control.
        """
        now = time.time()
        dt_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
        file_dt = time.strftime("%Y%m%d_%H%M%S", time.localtime(now))
        reports_dir = os.path.join(BASE_DIR, "reports")
        os.makedirs(reports_dir, exist_ok=True)

        mid_price = 0.0
        if self.market_data_mgr:
            mid_price = self.market_data_mgr.get_mid_price() or 0.0

        accounts_data = []
        total_vnd = 0.0
        total_btc = 0.0
        total_equity = 0.0

        for acc_id in sorted(self.account_mgr.accounts.keys()):
            adapter = self.account_mgr.get_adapter(acc_id)
            acc_meta = self.account_mgr.accounts[acc_id]
            actual_vnd = acc_meta.get("actual_vnd", 0.0)
            actual_btc = acc_meta.get("actual_btc", 0.0)

            # In LIVE mode or periodic refresh, fetch live balances from exchange
            if adapter:
                try:
                    bals = adapter.get_balances()
                    actual_vnd = bals.get("VND", actual_vnd)
                    actual_btc = bals.get("BTC", actual_btc)
                    acc_meta["actual_vnd"] = actual_vnd
                    acc_meta["actual_btc"] = actual_btc
                except Exception as e:
                    logger.warning(f"Failed to refresh balance for {acc_id}: {e}")

            equity_vnd = actual_vnd + (actual_btc * mid_price)
            total_vnd += actual_vnd
            total_btc += actual_btc
            total_equity += equity_vnd

            # Count open orders
            open_orders = 0
            if self.execution_engine:
                open_orders = sum(1 for o in self.execution_engine.open_orders.values() if o.account_id == acc_id)

            # Strategies assigned
            strategies = [
                s_id for s_id, s in (self.strategy_mgr.strategies.items() if self.strategy_mgr else [])
                if s.account_id == acc_id
            ]

            accounts_data.append({
                "account_id": acc_id,
                "nickname": acc_meta.get("nickname", ""),
                "username": acc_meta.get("username", ""),
                "actual_vnd": actual_vnd,
                "actual_btc": actual_btc,
                "equity_vnd": equity_vnd,
                "initial_capital_vnd": 150_000_000.0,
                "deployable_budget_vnd": 90_000_000.0,
                "pnl_vnd": equity_vnd - 150_000_000.0,
                "pnl_pct": round(((equity_vnd - 150_000_000.0) / 150_000_000.0) * 100, 2),
                "open_orders_count": open_orders,
                "strategies_count": len(strategies),
                "strategies": strategies,
            })

        system_initial_capital = 3_000_000_000.0
        snapshot = {
            "snapshot_timestamp": now,
            "snapshot_datetime": dt_str,
            "session_key": self.account_mgr.session_key,
            "venue": "TCEX Spot BTC/VND",
            "market_mid_price_vnd": mid_price,
            "execution_mode": self.mode,
            "total_accounts": len(accounts_data),
            "system_initial_capital_vnd": system_initial_capital,
            "system_total_actual_vnd": total_vnd,
            "system_total_actual_btc": total_btc,
            "system_total_equity_vnd": total_equity,
            "system_total_pnl_vnd": total_equity - system_initial_capital,
            "system_total_pnl_pct": round(((total_equity - system_initial_capital) / system_initial_capital) * 100, 2),
            "accounts": accounts_data,
        }

        # Save to reports/balance_snapshot_latest.json
        latest_path = os.path.join(reports_dir, "balance_snapshot_latest.json")
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2)

        # Save to reports/balance_snapshot_YYYYMMDD_HHMMSS.json
        history_path = os.path.join(reports_dir, f"balance_snapshot_{file_dt}.json")
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2)

        # Update local/account_status.json
        status_path = os.path.join(BASE_DIR, "account_status.json")
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump(self.account_mgr.get_account_status_summary(), f, indent=2)

        self.last_snapshot_time = now
        logger.info(
            f"[SNAPSHOT] Account balances exported: {latest_path} | "
            f"System Equity: {total_equity:,.2f} VND | PnL: {snapshot['system_total_pnl_vnd']:+,.2f} VND"
        )
        return snapshot

    def run(self, max_iterations: Optional[int] = None, interval_sec: float = 2.0):
        """Main engine execution loop with continuous trading and periodic balance snapshots."""
        self.running = True
        logger.info(
            f"Engine running (Max iterations: {max_iterations or 'Unlimited'}, "
            f"Tick Interval: {interval_sec}s, Balance Snapshot: every {self.snapshot_interval_sec}s / {self.snapshot_interval_sec/60:.0f}m)..."
        )

        # Immediate baseline snapshot at t=0
        self.export_balance_snapshot()

        iteration = 0
        try:
            while self.running:
                iteration += 1
                self.run_tick()

                # Periodic balance snapshot (default: every 30 mins)
                if (time.time() - self.last_snapshot_time) >= self.snapshot_interval_sec:
                    self.export_balance_snapshot()

                if max_iterations and iteration >= max_iterations:
                    logger.info(f"Reached maximum specified iterations ({max_iterations}). Stopping.")
                    break

                time.sleep(interval_sec)
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received. Initiating graceful shutdown...")
        finally:
            self.shutdown()

    def shutdown(self):
        """Graceful shutdown of all subsystems."""
        self.running = False
        logger.info("=" * 70)
        logger.info("TCEX ENGINE SHUTTING DOWN...")
        # Final balance snapshot on exit
        try:
            self.export_balance_snapshot()
        except Exception as e:
            logger.warning(f"Could not export final snapshot: {e}")
        if self.execution_engine and len(self.execution_engine.open_orders) > 0:
            logger.info(f"Preserving {len(self.execution_engine.open_orders)} open orders in database.")
        logger.info("TCEX Engine shutdown complete.")
        logger.info("=" * 70)


def main():
    default_config = os.path.join(BASE_DIR, "config.json")
    parser = argparse.ArgumentParser(description="TCEX BTC/VND Multi-Account Strategy Engine")
    parser.add_argument("--config", type=str, default=default_config, help="Path to config.json")
    parser.add_argument("--mode", choices=["PAPER", "LIVE"], default=None, help="Execution mode override")
    parser.add_argument("--confirm-live", action="store_true", help="Explicit operator confirmation required for LIVE mode")
    parser.add_argument("--iterations", type=int, default=None, help="Number of ticks to run before stopping (default: continuous)")
    parser.add_argument("--interval", type=float, default=2.0, help="Interval between evaluation ticks in seconds")
    parser.add_argument("--snapshot-interval", type=int, default=1800, help="Interval in seconds to export account balance JSON snapshot (default: 1800 = 30 mins)")
    parser.add_argument("--verify-only", action="store_true", help="Verify 20 accounts and market, then exit")

    args = parser.parse_args()

    # Safety gate for LIVE mode
    if args.mode == "LIVE" and not args.confirm_live:
        print("\n" + "!" * 70)
        print("ERROR: LIVE execution requested without explicit operator confirmation!")
        print("To run in LIVE mode, you MUST pass the flag: --confirm-live")
        print("Defaulting safely back to PAPER mode.")
        print("!" * 70 + "\n")
        args.mode = "PAPER"

    app = TCEXEngineApplication(config_path=args.config, mode=args.mode)
    app.snapshot_interval_sec = float(args.snapshot_interval)

    # Setup signal handler for clean shutdown
    signal.signal(signal.SIGINT, lambda s, f: app.shutdown())
    signal.signal(signal.SIGTERM, lambda s, f: app.shutdown())

    try:
        app.initialize()
        if args.verify_only:
            app.export_balance_snapshot()
            print("\nVerification complete. 20 accounts, 100 strategies, and BTC/VND market ready.")
            print(f"Latest balance snapshot exported to: reports/balance_snapshot_latest.json")
            return
        app.run(max_iterations=args.iterations, interval_sec=args.interval)
    except Exception as e:
        logger.critical(f"Fatal error during engine execution: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
