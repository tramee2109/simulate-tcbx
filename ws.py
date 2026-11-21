"""WebSocket client for real-time Spot & Futures market data and order status."""

from __future__ import annotations

import json
import threading
import time
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlencode, urlparse, urlunparse

import websocket


MessageCallback = Callable[[Any], None]
ErrorCallback = Callable[[Exception], None]
OpenCallback = Callable[["WSStream"], None]


def _to_ws_base(base_url: str) -> str:
    parsed = urlparse(base_url.rstrip("/"))
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return urlunparse((scheme, parsed.netloc, parsed.path, "", "", "")).rstrip("/")


def _split_symbol_exchange(symbol: str, exchange: Optional[str] = None) -> tuple[str, str]:
    if exchange:
        return symbol, exchange
    parts = symbol.split("_")
    if len(parts) >= 3:
        return "_".join(parts[:-1]), parts[-1]
    return symbol, "binance"


class WSStream:
    """Managed single WebSocket connection running on a background daemon thread."""

    def __init__(
        self,
        url: str,
        on_message: MessageCallback,
        on_open: Optional[OpenCallback] = None,
        on_error: Optional[ErrorCallback] = None,
        auto_reconnect: bool = True,
        reconnect_delay: float = 2.0,
    ) -> None:
        self.url = url
        self.on_message = on_message
        self.on_open = on_open
        self.on_error = on_error
        self.auto_reconnect = auto_reconnect
        self.reconnect_delay = reconnect_delay

        self._stop = threading.Event()
        self._connected = threading.Event()
        self._ws: Optional[websocket.WebSocketApp] = None
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.is_set():
            def _handle_open(ws_app: websocket.WebSocketApp) -> None:
                self._connected.set()
                if self.on_open:
                    self.on_open(self)

            def _handle_message(ws_app: websocket.WebSocketApp, raw: str) -> None:
                try:
                    data = json.loads(raw)
                except Exception:
                    data = raw
                self.on_message(data)

            def _handle_error(ws_app: websocket.WebSocketApp, err: Any) -> None:
                if self.on_error and isinstance(err, Exception):
                    self.on_error(err)

            def _handle_close(ws_app: websocket.WebSocketApp, *_: Any) -> None:
                self._connected.clear()

            self._ws = websocket.WebSocketApp(
                self.url,
                on_open=_handle_open,
                on_message=_handle_message,
                on_error=_handle_error,
                on_close=_handle_close,
            )
            self._ws.run_forever(ping_interval=20, ping_timeout=10)
            self._connected.clear()

            if self._stop.is_set() or not self.auto_reconnect:
                break
            time.sleep(self.reconnect_delay)

    def wait_connected(self, timeout: float = 5.0) -> bool:
        return self._connected.wait(timeout=timeout)

    def send(self, payload: Dict[str, Any]) -> None:
        if self._ws is None or not self._connected.is_set():
            raise RuntimeError("WebSocket is not connected yet")
        self._ws.send(json.dumps(payload))

    def request(
        self,
        req_type: str,
        page: int = 1,
        page_size: int = 20,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        username: Optional[str] = None,
    ) -> None:
        """Send an order-status query (`open-orders`, `order-history`, `trade-history`)."""
        msg: Dict[str, Any] = {
            "type": req_type,
            "page": page,
            "pageSize": page_size,
        }
        if symbol:
            msg["symbol"] = symbol
        if strategy:
            msg["strategy"] = strategy
        if username:
            msg["username"] = username
        self.send(msg)

    def close(self) -> None:
        self._stop.set()
        self._connected.clear()
        if self._ws is not None:
            try:
                self._ws.close()
            except Exception:
                pass


class The20WSClient:
    """High-level WebSocket manager for Spot and Futures trading streams."""

    def __init__(
        self,
        base_url: str = "http://localhost:8083",
        token: str = "",
        session_key: str = "",
        market: str = "spot",
        user_id: Optional[int] = None,
        auto_reconnect: bool = True,
    ) -> None:
        self.ws_base_url = _to_ws_base(base_url)
        self.token = token
        self.session_key = session_key
        self.market = market.lower()
        self.user_id = user_id
        self.auto_reconnect = auto_reconnect
        self._streams: List[WSStream] = []

    def __enter__(self) -> "The20WSClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close_all()

    def _build_url(self, path: str, params: Dict[str, Any]) -> str:
        query = {k: v for k, v in params.items() if v is not None and v != ""}
        if self.token:
            query["token"] = self.token
        return f"{self.ws_base_url}{path}?{urlencode(query)}"

    def _connect(
        self,
        path: str,
        params: Dict[str, Any],
        on_message: MessageCallback,
        on_open: Optional[OpenCallback] = None,
        on_error: Optional[ErrorCallback] = None,
    ) -> WSStream:
        url = self._build_url(path, params)
        stream = WSStream(
            url=url,
            on_message=on_message,
            on_open=on_open,
            on_error=on_error,
            auto_reconnect=self.auto_reconnect,
        )
        self._streams.append(stream)
        return stream

    def subscribe_orderbook(
        self,
        symbol: str,
        on_message: MessageCallback,
        exchange: Optional[str] = None,
        session_key: Optional[str] = None,
        on_error: Optional[ErrorCallback] = None,
    ) -> WSStream:
        sym, ex = _split_symbol_exchange(symbol, exchange)
        path = (
            "/api/v1/simulation/ws/trader/futures/orderbook"
            if self.market == "future"
            else "/api/v1/simulation/ws/trader/orderbook"
        )
        return self._connect(
            path,
            {"symbol": sym, "exchange": ex, "session_key": session_key or self.session_key},
            on_message=on_message,
            on_error=on_error,
        )

    def subscribe_candles(
        self,
        symbol: str,
        interval: str = "1m",
        on_message: Optional[MessageCallback] = None,
        exchange: Optional[str] = None,
        session_key: Optional[str] = None,
        on_error: Optional[ErrorCallback] = None,
    ) -> WSStream:
        if on_message is None:
            raise ValueError("on_message callback is required")
        sym, ex = _split_symbol_exchange(symbol, exchange)
        path = (
            "/api/v1/simulation/ws/trader/futures/candles"
            if self.market == "future"
            else "/api/v1/simulation/ws/trader/candles"
        )
        return self._connect(
            path,
            {"symbol": sym, "exchange": ex, "interval": interval, "session_key": session_key or self.session_key},
            on_message=on_message,
            on_error=on_error,
        )

    def subscribe_ticker(
        self,
        symbol: str,
        on_message: MessageCallback,
        exchange: Optional[str] = None,
        session_key: Optional[str] = None,
        on_error: Optional[ErrorCallback] = None,
    ) -> WSStream:
        sym, ex = _split_symbol_exchange(symbol, exchange)
        path = (
            "/api/v1/simulation/ws/trader/futures/ticker/24hr"
            if self.market == "future"
            else "/api/v1/simulation/ws/trader/ticker/24hr"
        )
        return self._connect(
            path,
            {"symbol": sym, "exchange": ex, "session_key": session_key or self.session_key},
            on_message=on_message,
            on_error=on_error,
        )

    def subscribe_trades(
        self,
        symbol: str,
        on_message: MessageCallback,
        exchange: Optional[str] = None,
        session_key: Optional[str] = None,
        on_error: Optional[ErrorCallback] = None,
    ) -> WSStream:
        sym, ex = _split_symbol_exchange(symbol, exchange)
        path = "/api/v1/simulation/ws/futures/trades" if self.market == "future" else "/api/v1/simulation/ws/trades"
        return self._connect(
            path,
            {"symbol": sym, "exchange": ex, "session_key": session_key or self.session_key},
            on_message=on_message,
            on_error=on_error,
        )

    def subscribe_order_status(
        self,
        on_message: MessageCallback,
        session_key: Optional[str] = None,
        user_id: Optional[int] = None,
        symbol: Optional[str] = None,
        on_open: Optional[OpenCallback] = None,
        on_error: Optional[ErrorCallback] = None,
    ) -> WSStream:
        path = (
            "/api/v1/simulation/ws/trader/order-status-futures"
            if self.market == "future"
            else "/api/v1/simulation/ws/trader/order-status"
        )
        uid = user_id if user_id is not None else self.user_id

        def _default_open(stream: WSStream) -> None:
            if on_open:
                on_open(stream)
            else:
                stream.request("open-orders", symbol=symbol)
                stream.request("order-history", symbol=symbol)
                stream.request("trade-history", symbol=symbol)

        return self._connect(
            path,
            {
                "session_key": session_key or self.session_key,
                "user_id": uid if uid is not None else "",
                "type": "all",
            },
            on_message=on_message,
            on_open=_default_open,
            on_error=on_error,
        )

    def close_all(self) -> None:
        for stream in self._streams:
            stream.close()
        self._streams.clear()
