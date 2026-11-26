"""
exchange/market_data.py
Market Data Manager for TCEX BTC/VND spot pair.
Provides price feeds, orderbook depths, klines, technical indicators, and stale data checks.
"""

import math
import time
from typing import Any, Dict, List, Optional, Tuple
from monitoring.logger import get_logger

logger = get_logger("market_data")


class MarketDataManager:
    """Manages real-time market data, indicators, and stale data checks for BTC_VND."""

    def __init__(
        self,
        spot_client: Any,
        symbol: str = "BTC_VND",
        session_key: str = "",
        stale_threshold_sec: float = 30.0,
    ):
        self.client = spot_client
        self.symbol = symbol
        self.session_key = session_key
        self.stale_threshold_sec = stale_threshold_sec

        self._last_ticker: Optional[Dict[str, Any]] = None
        self._last_orderbook: Optional[Dict[str, Any]] = None
        self._last_klines: List[List[Any]] = []
        self._last_update_ts: float = 0.0

    def refresh(self) -> bool:
        """Fetch latest market data from TCEX."""
        try:
            # 1. Fetch 24hr ticker
            ticker = self.client.get_ticker_24hr(self.symbol, session_key=self.session_key)
            if ticker and isinstance(ticker, dict):
                self._last_ticker = ticker

            # 2. Fetch orderbook
            ob = self.client.get_orderbook(self.symbol, session_key=self.session_key, limit=20)
            if ob and isinstance(ob, dict):
                self._last_orderbook = ob

            # 3. Fetch klines (1m default for fast signals)
            klines = self.client.get_klines(self.symbol, interval="1m", session_key=self.session_key, limit=100)
            if isinstance(klines, dict) and "candle" in klines:
                self._last_klines = klines["candle"]
            elif isinstance(klines, list):
                self._last_klines = klines

            self._last_update_ts = time.time()
            return True
        except Exception as e:
            logger.error(f"Market data refresh failed: {e}")
            return False

    def is_stale(self) -> bool:
        """Check if market data is older than threshold."""
        if self._last_update_ts == 0.0:
            return True
        return (time.time() - self._last_update_ts) > self.stale_threshold_sec

    def get_best_bid_ask(self) -> Tuple[Optional[float], Optional[float]]:
        """Return (best_bid, best_ask) in VND."""
        if self.is_stale():
            return None, None

        best_bid = None
        best_ask = None

        if self._last_ticker:
            best_bid = float(self._last_ticker.get("bestBid") or self._last_ticker.get("bidPr") or 0.0)
            best_ask = float(self._last_ticker.get("bestAsk") or self._last_ticker.get("askPr") or 0.0)

        # Fallback to orderbook if ticker values are zero
        if (best_bid is None or best_bid <= 0 or best_ask is None or best_ask <= 0) and self._last_orderbook:
            bids = self._last_orderbook.get("bids", {})
            asks = self._last_orderbook.get("asks", {})
            if isinstance(bids, dict) and len(bids) > 0:
                best_bid = max(float(p) for p in bids.keys())
            if isinstance(asks, dict) and len(asks) > 0:
                best_ask = min(float(p) for p in asks.keys())

        return (best_bid if best_bid and best_bid > 0 else None,
                best_ask if best_ask and best_ask > 0 else None)

    def get_mid_price(self) -> Optional[float]:
        """Return mid price (best_bid + best_ask) / 2."""
        bid, ask = self.get_best_bid_ask()
        if bid and ask:
            return (bid + ask) / 2.0
        if bid:
            return bid
        if ask:
            return ask
        if self._last_ticker:
            last = float(self._last_ticker.get("last") or self._last_ticker.get("lastPr") or 0.0)
            if last > 0:
                return last
        return None

    def get_orderbook_depth(self) -> Dict[str, Any]:
        """Return parsed orderbook with top levels."""
        if not self._last_orderbook or self.is_stale():
            return {"bids": [], "asks": []}

        raw_bids = self._last_orderbook.get("bids", {})
        raw_asks = self._last_orderbook.get("asks", {})

        bids = []
        if isinstance(raw_bids, dict):
            for p, q in sorted([(float(k), float(v)) for k, v in raw_bids.items()], key=lambda x: x[0], reverse=True):
                bids.append({"price": p, "quantity": q})

        asks = []
        if isinstance(raw_asks, dict):
            for p, q in sorted([(float(k), float(v)) for k, v in raw_asks.items()], key=lambda x: x[0]):
                asks.append({"price": p, "quantity": q})

        return {"bids": bids, "asks": asks}

    def get_orderbook_imbalance(self, levels: int = 5) -> float:
        """
        Calculate orderbook bid/ask volume imbalance ratio.
        Positive = more buyers, Negative = more sellers (-1.0 to 1.0).
        """
        depth = self.get_orderbook_depth()
        bids = depth["bids"][:levels]
        asks = depth["asks"][:levels]

        total_bid_vol = sum(b["quantity"] for b in bids)
        total_ask_vol = sum(a["quantity"] for a in asks)
        total_vol = total_bid_vol + total_ask_vol

        if total_vol <= 0:
            return 0.0
        return (total_bid_vol - total_ask_vol) / total_vol

    def get_close_prices(self, count: int = 50) -> List[float]:
        """Return close prices from historical klines."""
        if not self._last_klines:
            return []
        closes = []
        for c in self._last_klines:
            # candle format: [open_time, open, high, low, close, volume, ...]
            if len(c) > 4:
                closes.append(float(c[4]))
        return closes[-count:]

    def get_ohlcv(self, count: int = 50) -> List[Dict[str, float]]:
        """Return structured OHLCV bars."""
        bars = []
        for c in self._last_klines:
            if len(c) > 5:
                bars.append({
                    "timestamp": float(c[0]),
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4]),
                    "volume": float(c[5]),
                })
        return bars[-count:]
