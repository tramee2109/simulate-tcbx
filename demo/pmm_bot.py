"""Pure Market Making (PMM) strategy using The20 Simulation SDK and Binance WS mid price."""

from __future__ import annotations

import json
import os
import signal
import sys
import threading
import time
from typing import Optional

import websocket  # websocket-client

from _sdk_loader import load_sdk

sdk = load_sdk()
SpotClient = sdk.SpotClient
The20APIError = sdk.The20APIError

BINANCE_WS_URL = os.getenv(
    "BINANCE_WS_URL", "wss://stream.binance.com:9443/ws/btcusdt@bookTicker"
)
BASE_URL = os.getenv("THE20_BASE_URL", "https://simulation.the20.sg")
API_KEY = os.getenv("THE20_API_KEY", "")
API_SECRET = os.getenv("THE20_API_SECRET", "")
SESSION_KEY = os.getenv("THE20_SESSION_KEY", "")
SYMBOL = os.getenv("THE20_SYMBOL", "BTC_VND")

LEVELS_PER_SIDE = int(os.getenv("PMM_LEVELS", "3"))
REFRESH_INTERVAL_SEC = float(os.getenv("PMM_REFRESH_SEC", "5"))
SIDE_NOTIONAL_USDT = float(os.getenv("PMM_SIDE_NOTIONAL_USDT", "10000"))
BASE_SPREAD_BPS = float(os.getenv("PMM_SPREAD_BPS", "5"))
LEVEL_STEP_BPS = float(os.getenv("PMM_STEP_BPS", "5"))


class BinanceMidPriceFeed:
    """Background Binance bookTicker WebSocket feed tracking live mid price."""

    def __init__(self, ws_url: str = BINANCE_WS_URL) -> None:
        self.ws_url = ws_url
        self._lock = threading.Lock()
        self._mid_price: Optional[float] = None
        self._best_bid: Optional[float] = None
        self._best_ask: Optional[float] = None
        self._updated_at: float = 0.0
        self._stop_event = threading.Event()
        self._ws: Optional[websocket.WebSocketApp] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._ws is not None:
            try:
                self._ws.close()
            except Exception:
                pass

    def get_mid(self) -> tuple[Optional[float], Optional[float], Optional[float], float]:
        with self._lock:
            return self._mid_price, self._best_bid, self._best_ask, self._updated_at

    def _on_message(self, _ws: websocket.WebSocketApp, message: str) -> None:
        try:
            data = json.loads(message)
            bid = float(data["b"])
            ask = float(data["a"])
            if bid > 0 and ask > 0:
                with self._lock:
                    self._best_bid = bid
                    self._best_ask = ask
                    self._mid_price = (bid + ask) / 2.0
                    self._updated_at = time.time()
        except Exception:
            pass

    def _on_error(self, _ws: websocket.WebSocketApp, error: Exception) -> None:
        print(f"[BinanceWS] error: {error}", file=sys.stderr, flush=True)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self._ws = websocket.WebSocketApp(
                self.ws_url,
                on_message=self._on_message,
                on_error=self._on_error,
            )
            self._ws.run_forever(ping_interval=20, ping_timeout=10)
            if not self._stop_event.is_set():
                time.sleep(1.0)


def main() -> None:
    if not API_KEY or not API_SECRET or not SESSION_KEY:
        raise SystemExit(
            "THE20_API_KEY, THE20_API_SECRET, and THE20_SESSION_KEY env vars are required."
        )

    client = SpotClient(
        base_url=BASE_URL,
        api_key=API_KEY,
        api_secret=API_SECRET,
        session_key=SESSION_KEY,
    )

    ticker_info = client.get_ticker_info(SYMBOL)
    price_scale = int(ticker_info.get("price_scale", 2))
    qty_scale = int(ticker_info.get("qty_scale", 2))
    min_qty = 10 ** (-qty_scale)
    per_order_notional = SIDE_NOTIONAL_USDT / LEVELS_PER_SIDE

    print(
        f"[PMM] Starting on {BASE_URL} | session={SESSION_KEY} | symbol={SYMBOL} | "
        f"levels={LEVELS_PER_SIDE}/side | side_notional={SIDE_NOTIONAL_USDT} | "
        f"refresh={REFRESH_INTERVAL_SEC}s | scales=({price_scale}, {qty_scale})",
        flush=True,
    )

    feed = BinanceMidPriceFeed()
    feed.start()

    stop_event = threading.Event()

    def _handle_signal(_sig: int, _frame: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    # Wait briefly for initial Binance mid price
    while not stop_event.is_set():
        mid, bid, ask, _ = feed.get_mid()
        if mid is not None:
            print(f"[PMM] Initial Binance BTCUSDT mid={mid:.2f} (bid={bid}, ask={ask})", flush=True)
            break
        time.sleep(0.2)

    try:
        while not stop_event.is_set():
            cycle_start = time.time()
            mid, bid, ask, updated_at = feed.get_mid()
            if mid is None or (time.time() - updated_at) > 15.0:
                print("[PMM] Waiting for fresh Binance WS mid price...", flush=True)
                stop_event.wait(1.0)
                continue

            # Cancel existing open orders before replacing
            try:
                client.cancel_all_orders(SYMBOL)
            except The20APIError as exc:
                print(f"[PMM] cancel_all_orders warning: {exc}", file=sys.stderr, flush=True)

            placed_bids = []
            placed_asks = []
            for idx in range(LEVELS_PER_SIDE):
                offset_bps = BASE_SPREAD_BPS + idx * LEVEL_STEP_BPS
                bid_px = round(mid * (1.0 - offset_bps / 10_000.0), price_scale)
                ask_px = round(mid * (1.0 + offset_bps / 10_000.0), price_scale)

                bid_qty = max(min_qty, round(per_order_notional / bid_px, qty_scale))
                ask_qty = max(min_qty, round(per_order_notional / ask_px, qty_scale))

                try:
                    b_res = client.limit_buy(
                        SYMBOL, quantity=bid_qty, price=bid_px, strategy_name="pmm"
                    )
                    placed_bids.append((bid_px, bid_qty, b_res.get("orderId")))
                except The20APIError as exc:
                    print(f"[PMM] limit_buy L{idx + 1} error: {exc}", file=sys.stderr, flush=True)

                try:
                    a_res = client.limit_sell(
                        SYMBOL, quantity=ask_qty, price=ask_px, strategy_name="pmm"
                    )
                    placed_asks.append((ask_px, ask_qty, a_res.get("orderId")))
                except The20APIError as exc:
                    print(f"[PMM] limit_sell L{idx + 1} error: {exc}", file=sys.stderr, flush=True)

            bid_total = sum(px * q for px, q, _ in placed_bids)
            ask_total = sum(px * q for px, q, _ in placed_asks)
            print(
                f"[PMM] mid={mid:.2f} | bids={len(placed_bids)} (~${bid_total:,.2f}) "
                f"{[(px, q) for px, q, _ in placed_bids]} | "
                f"asks={len(placed_asks)} (~${ask_total:,.2f}) "
                f"{[(px, q) for px, q, _ in placed_asks]}",
                flush=True,
            )

            elapsed = time.time() - cycle_start
            wait_sec = max(0.0, REFRESH_INTERVAL_SEC - elapsed)
            stop_event.wait(wait_sec)
    finally:
        feed.stop()
        try:
            client.cancel_all_orders(SYMBOL)
            print("[PMM] Cleaned up open orders on exit.", flush=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
