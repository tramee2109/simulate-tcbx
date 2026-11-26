"""
strategies/breakout.py
Family: Breakout (STR-041 - STR-050)
Channel, fractal, range, and volatility squeeze breakout strategies for TCEX BTC/VND.
LIMIT-only orders with retest or boundary placement.
"""

from typing import Any, Dict, Optional
from strategies.base import BaseStrategy
from strategies.indicators import calculate_bollinger_bands, calculate_atr


class STR041_DonchianRangeBreakout(BaseStrategy):
    """Donchian Range Breakout: Places limit order near 20-period upper channel."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 20:
            return None

        h20 = max(closes[-20:-1])
        if closes[-1] >= h20:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR042_VolatilitySqueezeBreakout(BaseStrategy):
    """Volatility Squeeze Breakout: Detects Bollinger Band contraction inside Keltner channels."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 20:
            return None

        upper, mean, lower = calculate_bollinger_bands(closes, 20, 2.0)
        if upper and lower and (upper - lower) / mean < 0.008 and closes[-1] > mean:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR043_PivotPointsBreakout(BaseStrategy):
    """Pivot Points Breakout: Breaks through R1 resistance with volume confirmation."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ohlcv = market_data.get("ohlcv", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(ohlcv) < 5:
            return None

        last_bar = ohlcv[-2]
        pivot = (last_bar["high"] + last_bar["low"] + last_bar["close"]) / 3.0
        r1 = 2 * pivot - last_bar["low"]
        if market_data.get("best_ask", 0) >= r1:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR044_HighLowFractalBreakout(BaseStrategy):
    """High/Low Fractal Breakout: Bill Williams 5-bar fractal swing breakout."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 10:
            return None

        fractal_high = max(closes[-7:-2])
        if closes[-1] > fractal_high:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR045_ATRExpansionBreakout(BaseStrategy):
    """ATR Expansion Breakout: Enters when true range expands by > 1.5x rolling ATR."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ohlcv = market_data.get("ohlcv", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(ohlcv) < 15:
            return None

        atr = calculate_atr(ohlcv, period=14)
        current_range = ohlcv[-1]["high"] - ohlcv[-1]["low"]
        if atr and current_range > (1.5 * atr) and ohlcv[-1]["close"] > ohlcv[-1]["open"]:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR046_OpeningRangeBreakout(BaseStrategy):
    """Opening Range Breakout: Breaks 15-minute high from session open."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 15:
            return None

        high15 = max(closes[-15:])
        if closes[-1] >= high15 * 0.999:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR047_VolumeSpikeBreakout(BaseStrategy):
    """Volume Spike Breakout: Requires 2.0x 20-period average volume on upward bar."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ohlcv = market_data.get("ohlcv", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(ohlcv) < 20:
            return None

        avg_vol = sum(b["volume"] for b in ohlcv[-20:-1]) / 19.0
        if avg_vol > 0 and ohlcv[-1]["volume"] > (2.0 * avg_vol) and ohlcv[-1]["close"] > ohlcv[-1]["open"]:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR048_NarrowRange7Breakout(BaseStrategy):
    """Narrow Range 7 (NR7) Breakout: Toby Crabel contraction compression breakout."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ohlcv = market_data.get("ohlcv", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(ohlcv) < 8:
            return None

        ranges = [b["high"] - b["low"] for b in ohlcv[-8:]]
        # If previous bar was NR7 and current bar breaks upward
        if ranges[-2] == min(ranges[-8:-1]) and ohlcv[-1]["close"] > ohlcv[-2]["high"]:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR049_DoubleTopBottomBreakout(BaseStrategy):
    """Double Top / Bottom Breakout: Neckline break of structural swing pattern."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 25:
            return None

        lows = [closes[i] for i in range(-25, 0, 5)]
        if len(lows) >= 3 and abs(lows[0] - lows[2]) / lows[0] < 0.003 and closes[-1] > max(lows):
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR050_TrianglePatternBreakout(BaseStrategy):
    """Triangle Pattern Breakout: Ascending triangle upper resistance breach."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 20:
            return None

        h = max(closes[-20:-5])
        if closes[-1] > h and closes[-2] <= h:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None
