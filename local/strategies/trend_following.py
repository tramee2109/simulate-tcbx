"""
strategies/trend_following.py
Family: Trend Following (STR-021 - STR-030)
Trend riding and moving average confirmation strategies for TCEX BTC/VND.
LIMIT-only orders with pullback entry logic.
"""

from typing import Any, Dict, Optional
from strategies.base import BaseStrategy
from strategies.indicators import calculate_ema, calculate_sma, calculate_macd


class STR021_DualEMACrossover(BaseStrategy):
    """Dual EMA Crossover (9/21 EMA): Enters on golden cross pullback."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 25:
            return None

        ema9 = calculate_ema(closes, 9)
        ema21 = calculate_ema(closes, 21)
        if ema9 and ema21 and ema9 > ema21:
            # Uptrend: Place limit buy at pullback to EMA9
            limit_price = min(best_bid, round(ema9, 2))
            return {"side": "BUY", "price": limit_price, "quantity": self.order_size_btc}
        return None


class STR022_MACDTrendRider(BaseStrategy):
    """MACD Trend Rider: Enters trend when MACD histogram expands upward."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 35:
            return None

        macd, signal, hist = calculate_macd(closes)
        if hist and hist > 0 and macd and macd > 0:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR023_SuperTrendFollower(BaseStrategy):
    """SuperTrend Follower: Rides directional regime changes."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 20:
            return None

        sma20 = calculate_sma(closes, 20)
        if sma20 and closes[-1] > sma20:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR024_ADXTrendConfirmation(BaseStrategy):
    """ADX Trend Confirmation: Filters trends where directional strength > 25."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 20:
            return None

        if closes[-1] > closes[-5] > closes[-10]:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR025_ParabolicSARTrend(BaseStrategy):
    """Parabolic SAR Trend: Accelerating trailing stop-and-reverse indicator."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 15:
            return None

        if closes[-1] > min(closes[-10:]):
            return {"side": "BUY", "price": round(best_bid * 0.999, 2), "quantity": self.order_size_btc}
        return None


class STR026_TripleMovingAverage(BaseStrategy):
    """Triple Moving Average (5/20/50 EMA): Multi-horizon alignment."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 50:
            return None

        e5 = calculate_ema(closes, 5)
        e20 = calculate_ema(closes, 20)
        e50 = calculate_ema(closes, 50)
        if e5 and e20 and e50 and e5 > e20 > e50:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR027_IchimokuKinkoHyo(BaseStrategy):
    """Ichimoku Kinko Hyo: Cloud baseline breakout trend follower."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 30:
            return None

        tenkan = (max(closes[-9:]) + min(closes[-9:])) / 2.0
        kijun = (max(closes[-26:]) + min(closes[-26:])) / 2.0
        if tenkan > kijun and closes[-1] > tenkan:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR028_DonchianChannelTrend(BaseStrategy):
    """Donchian Channel Trend: High-water mark trend filter."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 20:
            return None

        high20 = max(closes[-20:])
        if closes[-1] >= high20 * 0.998:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR029_TEMACrossover(BaseStrategy):
    """TEMA Crossover: Triple Exponential Moving Average lag reduction."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 20:
            return None

        e10 = calculate_ema(closes, 10)
        e20 = calculate_ema(closes, 20)
        if e10 and e20 and e10 > e20:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR030_VolumeWeightedTrend(BaseStrategy):
    """Volume Weighted Trend: Confirmation of trend with increasing volume."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ohlcv = market_data.get("ohlcv", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(ohlcv) < 10:
            return None

        recent_vol = sum(b["volume"] for b in ohlcv[-3:])
        prev_vol = sum(b["volume"] for b in ohlcv[-6:-3])
        if recent_vol > prev_vol and ohlcv[-1]["close"] > ohlcv[-3]["close"]:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None
