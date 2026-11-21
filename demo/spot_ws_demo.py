"""Spot WebSocket streaming demo for The20 Simulation SDK."""

import os
import threading

from _sdk_loader import load_sdk

sdk = load_sdk()
SpotClient = sdk.SpotClient

BASE_URL = os.getenv("THE20_BASE_URL", "http://localhost:8083")
USERNAME = os.getenv("THE20_USERNAME", "client")
PASSWORD = os.getenv("THE20_PASSWORD", "client123")
SESSION_KEY = os.getenv("THE20_SESSION_KEY", "dbukjqfiralc73cbcme0")
SYMBOL = os.getenv("THE20_SYMBOL", "BTC_USDT_binance")


def main() -> None:
    client = SpotClient(
        base_url=BASE_URL,
        username=USERNAME,
        password=PASSWORD,
        session_key=SESSION_KEY,
    )

    done = threading.Event()

    def on_orderbook(msg):
        if isinstance(msg, dict) and "bids" in msg:
            bids = msg.get("bids")
            asks = msg.get("asks")
            top_bid = next(iter(bids.items()), None) if isinstance(bids, dict) else (bids[0] if bids else None)
            top_ask = next(iter(asks.items()), None) if isinstance(asks, dict) else (asks[0] if asks else None)
            print(f"[ORDERBOOK] {msg.get('symbol')} bid={top_bid} ask={top_ask}")

    def on_order_status(msg):
        if isinstance(msg, dict):
            req = msg.get("request")
            total = msg.get("total")
            first = (msg.get("data") or [None])[0]
            print(f"[ORDER_STATUS] request={req} total={total} first={first}")
            if req == "trade-history":
                done.set()

    with client.ws() as ws:
        ws.subscribe_orderbook(SYMBOL, on_message=on_orderbook)
        ws.subscribe_trades(SYMBOL, on_message=lambda m: print("[TRADE]", m))
        ws.subscribe_order_status(on_message=on_order_status)

        # Wait up to 5 seconds for snapshots, then exit cleanly
        done.wait(timeout=5.0)


if __name__ == "__main__":
    main()
