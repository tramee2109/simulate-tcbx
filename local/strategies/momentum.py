"""
strategies/momentum.py
Family: Momentum (STR-031 - STR-040)
Velocity, acceleration, and relative strength momentum strategies for TCEX BTC/VND.
"""

from typing import Any, Dict, Optional
from strategies.base import BaseStrategy
from strategies.indicators import calculate_rsi, calculate_macd


class STR031_RateOfChangeMomentum(BaseStrategy):
    """Rate of Change Momentum: Measures percentage price velocity over N periods."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 12:
            return None

        roc = (closes[-1] - closes[-12]) / closes[-12] * 100.0
        if roc > 0.8:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR032_StochasticMomentumIndex(BaseStrategy):
    """Stochastic Momentum Index: Double-smoothed momentum relative to midpoint."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 14:
            return None

        h = max(closes[-14:])
        l = min(closes[-14:])
        mid = (h + l) / 2.0
        diff = closes[-1] - mid
        if diff > 0 and (h - l) > 0:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR033_RSIMomentumSurge(BaseStrategy):
    """RSI Momentum Surge: Enters when RSI crosses above 55 with positive acceleration."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 16:
            return None

        rsi = calculate_rsi(closes, period=14)
        if rsi and rsi > 55.0 and closes[-1] > closes[-2]:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR034_MACDHistogramAcceleration(BaseStrategy):
    """MACD Histogram Acceleration: Measures second derivative of MACD."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 35:
            return None

        macd, sig, hist = calculate_macd(closes)
        if hist and hist > 0:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR035_TrendIntensityIndex(BaseStrategy):
    """Trend Intensity Index: Measures percentage of prices above 30-period SMA."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 30:
            return None

        sma30 = sum(closes[-30:]) / 30.0
        above_count = sum(1 for p in closes[-30:] if p > sma30)
        if above_count > 20:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR036_ChandeMomentumOscillator(BaseStrategy):
    """Chande Momentum Oscillator: Unsmoothed ratio of higher closes vs lower closes."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 15:
            return None

        up_sum = sum(max(0, closes[i] - closes[i - 1]) for i in range(-14, 0))
        down_sum = sum(max(0, closes[i - 1] - closes[i]) for i in range(-14, 0))
        total = up_sum + down_sum
        if total > 0:
            cmo = (up_sum - down_sum) / total * 100.0
            if cmo > 25.0:
                return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR037_MomentumCompressionRelease(BaseStrategy):
    """Momentum Compression Release: Catches violent expansion out of low volatility."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 20:
            return None

        range_recent = max(closes[-5:]) - min(closes[-5:])
        range_prior = max(closes[-20:-5]) - min(closes[-20:-5])
        if range_prior > 0 and (range_recent / range_prior) < 0.4 and closes[-1] > closes[-2]:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR038_RelativeMomentumIndex(BaseStrategy):
    """Relative Momentum Index: RSI variation with lookback intervals."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 20:
            return None

        if closes[-1] > closes[-5] > closes[-10]:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR039_WilliamsPercentRMomentum(BaseStrategy):
    """Williams %R Momentum: Catches momentum breakout above -20."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 14:
            return None

        h14 = max(closes[-14:])
        l14 = min(closes[-14:])
        if h14 > l14:
            wr = (h14 - closes[-1]) / (h14 - l14) * -100.0
            if wr > -25.0:
                return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR040_MultiTimeframeMomentum(BaseStrategy):
    """Multi-Timeframe Momentum: Composite alignment of fast and slow velocities."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 30:
            return None

        fast_mom = closes[-1] - closes[-5]
        slow_mom = closes[-1] - closes[-20]
        if fast_mom > 0 and slow_mom > 0:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None
