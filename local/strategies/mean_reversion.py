"""
strategies/mean_reversion.py
Family: Mean Reversion (STR-011 - STR-020)
Statistical and oscillator mean reversion strategies for TCEX BTC/VND.
"""

from typing import Any, Dict, Optional
from strategies.base import BaseStrategy
from strategies.indicators import (
    calculate_rsi,
    calculate_bollinger_bands,
    calculate_zscore,
    calculate_vwap,
    calculate_sma,
)


class STR011_RSIMeanReversion(BaseStrategy):
    """RSI Mean Reversion: Submits limit buy orders when RSI is oversold (< 30)."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 15:
            return None

        rsi = calculate_rsi(closes, period=14)
        if rsi and rsi < 32.0:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR012_BollingerBandFade(BaseStrategy):
    """Bollinger Band Fade: Places passive limit order at lower band on extreme divergence."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 20:
            return None

        upper, mean, lower = calculate_bollinger_bands(closes, period=20, num_std=2.2)
        if lower and best_bid <= lower:
            return {"side": "BUY", "price": round(lower, 2), "quantity": self.order_size_btc}
        return None


class STR013_VWAPMeanReversion(BaseStrategy):
    """VWAP Mean Reversion: Buys below VWAP when price stretches beyond standard threshold."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ohlcv = market_data.get("ohlcv", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or not ohlcv:
            return None

        vwap = calculate_vwap(ohlcv)
        if vwap and best_bid < (vwap * 0.996):
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR014_ZScoreSpread(BaseStrategy):
    """Z-Score Spread: Trades statistical extremes where Z-Score < -2.0."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 20:
            return None

        z = calculate_zscore(closes, period=20)
        if z and z < -2.0:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR015_StochasticOscillatorFade(BaseStrategy):
    """Stochastic Oscillator Fade: Fades oversold %K / %D crossovers."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 14:
            return None

        low14 = min(closes[-14:])
        high14 = max(closes[-14:])
        if high14 == low14:
            return None
        stoch_k = (closes[-1] - low14) / (high14 - low14) * 100.0

        if stoch_k < 20.0:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR016_MovingAverageDistance(BaseStrategy):
    """Moving Average Distance: Buys when distance to 50 SMA exceeds normal distribution tails."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 50:
            return None

        sma50 = calculate_sma(closes, period=50)
        if sma50 and best_bid < (sma50 * 0.993):
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR017_KeltnerChannelReversal(BaseStrategy):
    """Keltner Channel Reversal: Fades envelope touches below ATR-based lower channel."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 20:
            return None

        sma20 = calculate_sma(closes, 20)
        if sma20 and best_bid < (sma20 * 0.995):
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR018_StdDevEnvelope(BaseStrategy):
    """Standard Deviation Envelope: Places limit orders at 2.5 standard deviations from mean."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 25:
            return None

        upper, mean, lower = calculate_bollinger_bands(closes, period=25, num_std=2.5)
        if lower and best_bid <= lower:
            return {"side": "BUY", "price": round(lower, 2), "quantity": self.order_size_btc}
        return None


class STR019_CCIMeanReversion(BaseStrategy):
    """CCI Mean Reversion: Commodity Channel Index oversold (< -100) reversal."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 20:
            return None

        sma = calculate_sma(closes, 20)
        if sma:
            mean_dev = sum(abs(p - sma) for p in closes[-20:]) / 20.0
            if mean_dev > 0:
                cci = (closes[-1] - sma) / (0.015 * mean_dev)
                if cci < -100.0:
                    return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR020_HullMAReversal(BaseStrategy):
    """Hull MA Reversal: Rapid smoothing crossover mean-reversion filter."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 20:
            return None

        sma10 = calculate_sma(closes, 10)
        sma20 = calculate_sma(closes, 20)
        if sma10 and sma20 and best_bid < min(sma10, sma20) * 0.997:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None
