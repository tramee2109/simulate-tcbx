#!/usr/bin/env python3
"""
view_logs.py
Convenient CLI log viewer and real-time log monitor for TCEX BTC/VND Multi-Account Engine.

Usage:
    python view_logs.py                   # View recent 30 lines of engine log
    python view_logs.py -f                # Follow live engine log (tail -f)
    python view_logs.py --orders          # View orders & fills log (orders.log)
    python view_logs.py --orders -f       # Follow live orders and fills
    python view_logs.py --audit           # View risk & safety audit log (audit_events.log)
    python view_logs.py --account ACC-01  # Filter logs for ACC-01
    python view_logs.py --strategy STR-01 # Filter logs for STR-001
    python view_logs.py --status          # View log files overview and disk sizes
"""

import argparse
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, "logs")

MASTER_LOG = os.path.join(LOGS_DIR, "tcex_engine.log")
ORDERS_LOG = os.path.join(LOGS_DIR, "orders.log")
AUDIT_LOG = os.path.join(LOGS_DIR, "audit_events.log")

# ANSI color codes
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def colorize_line(line: str) -> str:
    """Add syntax highlighting to log messages."""
    clean = line.rstrip()
    if "FILLED" in clean or "[PAPER_FILL]" in clean:
        return f"{GREEN}{clean}{RESET}"
    elif "REJECTED" in clean or "CRITICAL" in clean or "ERROR" in clean:
        return f"{RED}{clean}{RESET}"
    elif "WARNING" in clean or "CANCELED" in clean:
        return f"{YELLOW}{clean}{RESET}"
    elif "SUBMITTED" in clean:
        return f"{CYAN}{clean}{RESET}"
    elif "STEP " in clean.upper() or "===" in clean:
        return f"{BOLD}{clean}{RESET}"
    return clean


def tail_file(file_path: str, n_lines: int = 30) -> list:
    """Read the last n lines from a file."""
    if not os.path.isfile(file_path):
        return []
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
        return lines[-n_lines:] if len(lines) > n_lines else lines


def follow_file(file_path: str, filter_keyword: str = ""):
    """Stream file updates in real time (tail -f)."""
    if not os.path.isfile(file_path):
        print(f"{YELLOW}Log file not found yet: {file_path}. Waiting for engine to create it...{RESET}")
        while not os.path.isfile(file_path):
            time.sleep(1)

    print(f"{CYAN}--- Streaming live log: {file_path} (Press Ctrl+C to stop) ---{RESET}\n")
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        # Seek to end
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if line:
                if not filter_keyword or filter_keyword.lower() in line.lower():
                    print(colorize_line(line))
            else:
                time.sleep(0.5)


def show_status():
    """Display summary and sizes of all log files."""
    print("=" * 70)
    print("TCEX BTC/VND MULTI-ACCOUNT ENGINE — LOG FILES STATUS")
    print("=" * 70)
    print(f"Logs Directory: {LOGS_DIR}\n")

    files = [
        ("Master Engine Log", MASTER_LOG, "All system operations, ticks, and signals"),
        ("Orders & Fills Log", ORDERS_LOG, "Order placements, matching, fills, cancellations"),
        ("Risk Audit Log", AUDIT_LOG, "Emergency stops, risk rejections, safety controls"),
    ]

    for label, path, desc in files:
        exists = os.path.isfile(path)
        size_kb = os.path.getsize(path) / 1024.0 if exists else 0.0
        line_count = 0
        if exists:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    line_count = sum(1 for _ in f)
            except Exception:
                pass
        status_str = f"{GREEN}ACTIVE{RESET}" if exists else f"{DIM}PENDING{RESET}"
        print(f"{BOLD}[{label}]{RESET} - Status: {status_str}")
        print(f"  Path  : {path}")
        print(f"  Size  : {size_kb:,.1f} KB ({line_count:,} lines)")
        print(f"  Role  : {desc}\n")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="TCEX Strategy Engine Log Viewer")
    parser.add_argument("-n", "--lines", type=int, default=30, help="Number of recent lines to display (default: 30)")
    parser.add_argument("-f", "--follow", action="store_true", help="Follow live log stream in real time (tail -f)")
    parser.add_argument("-o", "--orders", action="store_true", help="View orders & fills log (orders.log)")
    parser.add_argument("-a", "--audit", action="store_true", help="View risk audit log (audit_events.log)")
    parser.add_argument("-e", "--engine", action="store_true", help="View master engine log (tcex_engine.log)")
    parser.add_argument("--account", type=str, default="", help="Filter lines by account ID (e.g. ACC-01)")
    parser.add_argument("--strategy", type=str, default="", help="Filter lines by strategy ID (e.g. STR-001)")
    parser.add_argument("--status", action="store_true", help="Show overview of log files and disk sizes")

    args = parser.parse_args()

    if args.status:
        show_status()
        return

    # Choose target file
    if args.orders:
        target_file = ORDERS_LOG
        title = "ORDERS & FILLS LOG"
    elif args.audit:
        target_file = AUDIT_LOG
        title = "RISK AUDIT LOG"
    else:
        target_file = MASTER_LOG
        title = "MASTER ENGINE LOG"

    filter_kw = args.account or args.strategy

    if args.follow:
        try:
            follow_file(target_file, filter_keyword=filter_kw)
        except KeyboardInterrupt:
            print(f"\n{YELLOW}Stopped log stream.{RESET}")
            sys.exit(0)
    else:
        print("=" * 70)
        print(f"TCEX LOG VIEWER — {title} (Last {args.lines} lines)")
        print(f"File: {target_file}")
        if filter_kw:
            print(f"Filter keyword: [{filter_kw}]")
        print("=" * 70)

        lines = tail_file(target_file, n_lines=args.lines * 3 if filter_kw else args.lines)
        if filter_kw:
            lines = [l for l in lines if filter_kw.lower() in l.lower()][-args.lines :]

        if not lines:
            print(f"{DIM}No log entries found.{RESET}")
        else:
            for line in lines:
                print(colorize_line(line))
        print("=" * 70)
        print(f"Tip: Use 'python view_logs.py -f' to stream live logs, or '--orders' for orders.")


if __name__ == "__main__":
    main()
