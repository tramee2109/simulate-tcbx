#!/usr/bin/env python3
"""
export_snapshot.py
Quick manual or scheduled trigger to query all 20 accounts on TCEX and
update reports/balance_snapshot_latest.json with live equity and PnL.
"""

import json
import os
import sys
import time
from tabulate import tabulate

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from engine.account_manager import AccountManager
from exchange.market_data import MarketDataManager


def generate_snapshot():
    csv_file = os.path.join(BASE_DIR, "new-temp-accounts-global (1).csv")
    config_file = os.path.join(BASE_DIR, "config.json")
    with open(config_file, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    session_key = cfg.get("system", {}).get("session_key", "dc1tpbu76rkff8gccfug")
    base_url = cfg.get("system", {}).get("base_url", "https://simulation.the20.sg")

    am = AccountManager(csv_file, base_url, session_key)
    am.load_accounts()

    first_adapter = am.get_adapter("ACC-01")
    md = MarketDataManager(spot_client=first_adapter.client)
    md.refresh()
    mid = md.get_mid_price() or 1517000000.0

    now = time.time()
    dt_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
    file_dt = time.strftime("%Y%m%d_%H%M%S", time.localtime(now))
    reports_dir = os.path.join(BASE_DIR, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    accounts_data = []
    total_vnd = 0.0
    total_btc = 0.0
    total_equity = 0.0

    table_rows = []

    for acc_id in sorted(am.accounts.keys()):
        adapter = am.get_adapter(acc_id)
        acc_meta = am.accounts[acc_id]
        actual_vnd = 0.0
        actual_btc = 0.0
        open_orders_cnt = 0
        try:
            bals = adapter.get_balances()
            actual_vnd = bals.get("VND", 0.0)
            actual_btc = bals.get("BTC", 0.0)
            orders = adapter.get_open_orders()
            open_orders_cnt = len(orders)
        except Exception as e:
            print(f"Error checking {acc_id}: {e}")

        equity_vnd = actual_vnd + (actual_btc * mid)
        total_vnd += actual_vnd
        total_btc += actual_btc
        total_equity += equity_vnd
        pnl_vnd = equity_vnd - 150_000_000.0
        pnl_pct = round((pnl_vnd / 150_000_000.0) * 100, 2)

        accounts_data.append({
            "account_id": acc_id,
            "nickname": acc_meta.get("nickname", ""),
            "username": acc_meta.get("username", ""),
            "actual_vnd": actual_vnd,
            "actual_btc": actual_btc,
            "equity_vnd": equity_vnd,
            "initial_capital_vnd": 150000000.0,
            "deployable_budget_vnd": 90000000.0,
            "pnl_vnd": pnl_vnd,
            "pnl_pct": pnl_pct,
            "open_orders_count": open_orders_cnt,
        })

        table_rows.append([
            acc_id,
            acc_meta.get("nickname", ""),
            f"{actual_vnd:>14,.2f}",
            f"{actual_btc:>8.4f}",
            f"{equity_vnd:>14,.2f}",
            f"{pnl_vnd:>+12,.2f}",
            f"{pnl_pct:>+6.2f}%",
            open_orders_cnt,
        ])

    system_initial = 3_000_000_000.0
    system_pnl_vnd = total_equity - system_initial
    system_pnl_pct = round((system_pnl_vnd / system_initial) * 100, 2)

    snapshot = {
        "snapshot_timestamp": now,
        "snapshot_datetime": dt_str,
        "session_key": session_key,
        "venue": "TCEX Spot BTC/VND",
        "market_mid_price_vnd": mid,
        "execution_mode": "LIVE",
        "total_accounts": len(accounts_data),
        "system_initial_capital_vnd": system_initial,
        "system_total_actual_vnd": total_vnd,
        "system_total_actual_btc": total_btc,
        "system_total_equity_vnd": total_equity,
        "system_total_pnl_vnd": system_pnl_vnd,
        "system_total_pnl_pct": system_pnl_pct,
        "accounts": accounts_data,
    }

    latest_path = os.path.join(reports_dir, "balance_snapshot_latest.json")
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)

    history_path = os.path.join(reports_dir, f"balance_snapshot_{file_dt}.json")
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)

    headers = ["Account", "Nickname", "VND Balance", "BTC Balance", "Equity (VND)", "PnL (VND)", "PnL %", "Open Orders"]
    print(tabulate(table_rows, headers=headers, tablefmt="github"))
    print("\n" + "=" * 70)
    print(f"SNAPSHOT SAVED: {latest_path}")
    print(f"Timestamp    : {dt_str}")
    print(f"BTC/VND Price: {mid:,.2f} VND")
    print(f"Total VND    : {total_vnd:,.2f} VND")
    print(f"Total BTC    : {total_btc:.4f} BTC")
    print(f"Total Equity : {total_equity:,.2f} VND")
    print(f"System PnL   : {system_pnl_vnd:+,.2f} VND ({system_pnl_pct:+.2f}%)")
    print("=" * 70)


if __name__ == "__main__":
    generate_snapshot()
