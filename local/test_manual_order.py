#!/usr/bin/env python3
"""
test_manual_order.py
Quick utility to test placing, checking, and canceling a live LIMIT order
for any account in the TCEX session.

Usage:
    python test_manual_order.py --account ACC-01 --side BUY --price 1200000000 --qty 0.01
    python test_manual_order.py --account ACC-01 --open-orders
    python test_manual_order.py --account ACC-01 --cancel-all
"""

import argparse
import json
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from exchange.tcex_adapter import TCEXSpotAdapter
from engine.account_manager import AccountManager
from monitoring.logger import setup_logger, get_logger

logger = setup_logger("manual_order_test")


def main():
    parser = argparse.ArgumentParser(description="Test Manual LIMIT Order on TCEX Session")
    parser.add_argument("--account", type=str, default="ACC-01", help="Target account ID (e.g. ACC-01 .. ACC-20)")
    parser.add_argument("--side", type=str, choices=["BUY", "SELL"], default=None, help="Order side: BUY or SELL")
    parser.add_argument("--price", type=float, default=None, help="LIMIT price in VND")
    parser.add_argument("--qty", type=float, default=0.01, help="Quantity in BTC (min: 0.01)")
    parser.add_argument("--open-orders", action="store_true", help="View current open orders on exchange")
    parser.add_argument("--cancel-all", action="store_true", help="Cancel all open orders for this account")
    parser.add_argument("--session", type=str, default=None, help="Override session key")

    args = parser.parse_args()

    # Load config
    config_file = os.path.join(BASE_DIR, "config.json")
    with open(config_file, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    session_key = args.session or cfg.get("system", {}).get("session_key", "dc1tpbu76rkff8gccfug")
    base_url = cfg.get("system", {}).get("base_url", "https://simulation.the20.sg")
    csv_path = os.path.join(BASE_DIR, "new-temp-accounts-global (1).csv")

    account_mgr = AccountManager(csv_path=csv_path, base_url=base_url, session_key=session_key)
    account_mgr.load_accounts()

    acc = account_mgr.accounts.get(args.account)
    if not acc:
        print(f"Error: Account {args.account} not found in CSV.")
        sys.exit(1)

    adapter = account_mgr.get_adapter(args.account)
    if not adapter:
        print(f"Error: Could not initialize adapter for {args.account}.")
        sys.exit(1)

    print("=" * 70)
    print(f"TCEX MANUAL SESSION ORDER TOOL")
    print(f"Account   : {args.account} ({acc.get('nickname')})")
    print(f"Session   : {session_key}")
    print(f"Base URL  : {base_url}")
    print("=" * 70)

    # 1. Check balances
    balances = adapter.get_balances()
    print(f"Current Balance : VND = {balances.get('VND', 0.0):,.2f} | BTC = {balances.get('BTC', 0.0):.4f}")

    # 2. View open orders
    if args.open_orders:
        orders = adapter.get_open_orders()
        print(f"\nOpen Orders Count: {len(orders)}")
        for o in orders:
            print(f"  - OrderID: {o.get('orderId')} | Side: {o.get('side')} | Qty: {o.get('origQty') or o.get('quantity')} BTC | Price: {float(o.get('price', 0)):,.2f} VND | Status: {o.get('status')}")
        print("=" * 70)
        return

    # 3. Cancel all open orders
    if args.cancel_all:
        orders = adapter.get_open_orders()
        print(f"\nCanceling {len(orders)} open orders for {args.account}...")
        for o in orders:
            oid = o.get("orderId")
            cl_oid = o.get("clientOrderId")
            try:
                adapter.cancel_order(symbol="BTC_VND", order_id=oid, client_order_id=cl_oid)
                print(f"  [CANCELED] OrderId: {oid}")
            except Exception as e:
                print(f"  [FAIL] OrderId: {oid}: {e}")
        print("Done.")
        print("=" * 70)
        return

    # 4. Place order if requested
    if args.side and args.price:
        side = args.side.upper()
        price = args.price
        qty = args.qty
        notional = price * qty

        print(f"\n[SENDING ORDER] {side} {qty:.4f} BTC @ {price:,.2f} VND (Notional: {notional:,.2f} VND)...")
        try:
            cl_oid = f"MANUAL_{args.account}_{int(time.time()*1000)}"
            res = adapter.place_limit_order(
                symbol="BTC_VND",
                side=side,
                quantity=qty,
                price=price,
                client_order_id=cl_oid,
                strategy_name="MANUAL_TEST",
            )
            print(f"RESULT SUCCESS: Order submitted to exchange!")
            print(f"Response: {res}")
            print("\nKiểm tra trên giao diện Web TCEX (Mục Open Orders) để thấy lệnh xuất hiện!")
        except Exception as e:
            print(f"ORDER FAILED: {e}")
    else:
        print("\nTip: Để đặt lệnh test, chạy:")
        print(f"  python test_manual_order.py --account {args.account} --side BUY --price 1200000000 --qty 0.01")
        print("Để xem danh sách lệnh đang mở:")
        print(f"  python test_manual_order.py --account {args.account} --open-orders")
        print("Để hủy toàn bộ lệnh đang mở:")
        print(f"  python test_manual_order.py --account {args.account} --cancel-all")
    print("=" * 70)


if __name__ == "__main__":
    main()
