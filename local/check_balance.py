#!/usr/bin/env python3
"""
check_balance.py
Script to check account balances for The20 Simulation sessions with dynamic asset detection.
"""

import argparse
import csv
import importlib.util
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional


def load_sdk():
    """Load `the20_simulate_sdk` module from parent directory."""
    sdk_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if "the20_simulate_sdk" in sys.modules:
        return sys.modules["the20_simulate_sdk"]
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


def check_with_retry(fn, max_retries: int = 3, delay: float = 0.5):
    last_err = None
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            last_err = e
            if "recvWindow" in str(e) or "Timestamp" in str(e) or "timeout" in str(e).lower():
                time.sleep(delay * (attempt + 1))
                continue
            raise
    raise last_err


def check_account_balance(
    sdk: Any,
    base_url: str,
    session_key: str,
    account: Dict[str, str],
    market: str = "spot",
) -> Dict[str, Any]:
    username = account.get("username", "")
    nickname = account.get("nickname", "")
    api_key = account.get("api_key", "")
    secret_key = account.get("secret_key", "")

    result: Dict[str, Any] = {
        "username": username,
        "nickname": nickname,
        "spot_total": None,
        "spot_assets": {},  # e.g. {"VND": 150000000.0, "BTC": 0.0}
        "fut_balance": None,
        "fut_available": None,
        "fut_unpnl": None,
        "status": "OK",
        "error": None,
    }

    if not api_key or not secret_key:
        result["status"] = "ERROR"
        result["error"] = "Missing api_key or secret_key"
        return result

    # Check Spot Balance & Assets
    if market in ("both", "spot"):
        try:
            spot_client = sdk.SpotClient(
                base_url=base_url,
                api_key=api_key,
                api_secret=secret_key,
                session_key=session_key,
            )
            spot_res = check_with_retry(lambda: spot_client.get_balance())
            data = spot_res.get("data", {})
            result["spot_total"] = float(data.get("Total", 0))

            # Parse each asset in data (ignoring the "Total" aggregate key)
            assets = {}
            for asset_name, asset_val in data.items():
                if asset_name == "Total":
                    continue
                if isinstance(asset_val, dict):
                    assets[asset_name] = float(asset_val.get("amount", 0))
                elif isinstance(asset_val, (int, float, str)):
                    assets[asset_name] = float(asset_val)
            result["spot_assets"] = assets
        except Exception as e:
            result["status"] = "PARTIAL/ERROR"
            result["error"] = f"Spot: {e}"

    # Check Futures Balance
    if market in ("both", "futures"):
        try:
            fut_client = sdk.FuturesClient(
                base_url=base_url,
                api_key=api_key,
                api_secret=secret_key,
                session_key=session_key,
            )
            fut_res = check_with_retry(lambda: fut_client.get_balance())
            if isinstance(fut_res, list) and len(fut_res) > 0:
                first_asset = fut_res[0]
                result["fut_balance"] = float(first_asset.get("balance", 0))
                result["fut_available"] = float(first_asset.get("availableBalance", 0))
                result["fut_unpnl"] = float(first_asset.get("crossUnPnl", 0))
            elif isinstance(fut_res, dict):
                result["fut_balance"] = float(fut_res.get("balance", 0))
        except Exception as e:
            err = f"Futures: {e}"
            result["status"] = "PARTIAL/ERROR" if result["status"] == "OK" else "ERROR"
            result["error"] = f"{result['error']}; {err}" if result["error"] else err

    return result


def format_table(rows: List[Dict[str, Any]], market: str) -> str:
    # Discover all distinct spot asset currencies
    all_assets = set()
    for r in rows:
        all_assets.update(r.get("spot_assets", {}).keys())
    sorted_assets = sorted(all_assets, key=lambda x: (x != "VND", x != "USDT", x))

    headers = ["#", "Nickname", "Username"]

    if market in ("both", "spot"):
        for a in sorted_assets:
            headers.append(f"Spot {a}")
        headers.append("Spot Total")

    if market in ("both", "futures"):
        headers.extend(["Fut Balance", "Fut Available", "Fut UnPnL"])

    headers.extend(["Status", "Notes/Error"])

    table_data = []
    total_spot_sum = 0.0
    asset_totals = {a: 0.0 for a in sorted_assets}
    total_fut = 0.0

    for idx, r in enumerate(rows, start=1):
        row = [str(idx), r["nickname"], r["username"]]

        if market in ("both", "spot"):
            for a in sorted_assets:
                val = r.get("spot_assets", {}).get(a)
                if val is not None:
                    row.append(f"{val:,.2f}")
                    asset_totals[a] += val
                else:
                    row.append("-")

            tot = r["spot_total"]
            if tot is not None:
                row.append(f"{tot:,.2f}")
                total_spot_sum += tot
            else:
                row.append("-")

        if market in ("both", "futures"):
            fut_str = f"{r['fut_balance']:,.2f}" if r["fut_balance"] is not None else "-"
            avail_str = f"{r['fut_available']:,.2f}" if r["fut_available"] is not None else "-"
            pnl_str = f"{r['fut_unpnl']:,.2f}" if r["fut_unpnl"] is not None else "-"
            if r["fut_balance"] is not None:
                total_fut += r["fut_balance"]
            row.extend([fut_str, avail_str, pnl_str])

        row.extend([r["status"], r["error"] or ""])
        table_data.append(row)

    try:
        from tabulate import tabulate
        table_str = tabulate(table_data, headers=headers, tablefmt="github", disable_numparse=True)
    except ImportError:
        table_str = "\t".join(headers) + "\n"
        for row in table_data:
            table_str += "\t".join(str(c) for c in row) + "\n"

    summary_lines = [
        table_str,
        "",
        "--- TỔNG KẾT (SUMMARY) ---",
        f"Tổng số tài khoản : {len(rows)}",
    ]
    if market in ("both", "spot"):
        for a in sorted_assets:
            summary_lines.append(f"Tổng Spot {a:<8}: {asset_totals[a]:,.2f}")
        summary_lines.append(f"Tổng Spot Total   : {total_spot_sum:,.2f}")
    if market in ("both", "futures"):
        summary_lines.append(f"Tổng Futures      : {total_fut:,.2f}")

    return "\n".join(summary_lines)


def main():
    default_dir = os.path.dirname(os.path.abspath(__file__))
    default_csv = os.path.abspath(os.path.join(default_dir, "..", "new-temp-accounts-global (1).csv"))

    parser = argparse.ArgumentParser(description="Check The20 Simulation account balances.")
    parser.add_argument(
        "--csv",
        type=str,
        default=default_csv,
        help="Path to CSV account file (default: %(default)s)",
    )
    parser.add_argument(
        "--session",
        type=str,
        default="dc1tpbu76rkff8gccfug",
        help="Session key to access (default: %(default)s)",
    )
    parser.add_argument(
        "--url",
        type=str,
        default="https://simulation.the20.sg",
        help="Base URL for simulation API (default: %(default)s)",
    )
    parser.add_argument(
        "--market",
        choices=["both", "spot", "futures"],
        default="spot",
        help="Market balance to check (default: %(default)s)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Number of concurrent worker threads (default: %(default)s)",
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default=None,
        help="Optional path to export balances to a CSV file",
    )

    args = parser.parse_args()

    if not os.path.isfile(args.csv):
        print(f"Error: CSV file not found: {args.csv}")
        sys.exit(1)

    print("Loading The20 SDK...")
    sdk = load_sdk()

    print(f"Reading accounts from: {args.csv}")
    accounts = []
    with open(args.csv, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            accounts.append(row)

    print(f"Checking {len(accounts)} accounts for Session: {args.session} (URL: {args.url}, Mode: {args.market.upper()})...\n")

    results: List[Dict[str, Any]] = [None] * len(accounts)

    if args.workers > 1:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_to_idx = {
                executor.submit(
                    check_account_balance,
                    sdk,
                    args.url,
                    args.session,
                    acc,
                    args.market,
                ): i
                for i, acc in enumerate(accounts)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                results[idx] = future.result()
    else:
        for i, acc in enumerate(accounts):
            results[i] = check_account_balance(
                sdk,
                args.url,
                args.session,
                acc,
                args.market,
            )

    print(format_table(results, args.market))

    if args.output_csv:
        output_path = os.path.abspath(args.output_csv)
        fieldnames = ["username", "nickname", "spot_total", "spot_assets", "fut_balance", "fut_available", "fut_unpnl", "status", "error"]
        with open(output_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        print(f"\nExported balance results to: {output_path}")


if __name__ == "__main__":
    main()
