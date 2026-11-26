"""
strategies/behavioral.py
Family: Behavioral / Gambling Benchmark (STR-091 - STR-100)
Benchmark strategies modeling human behavioral biases, gambler fallacy, FOMO, and panic.
MANDATORY CONSTRAINT (Section 4 & 7):
Paper trading only! Live capital = 0 VND.
These strategies never submit live capital orders.
"""

from typing import Any, Dict, Optional
from strategies.base import BaseStrategy
from strategies.indicators import calculate_rsi


class BehavioralBase(BaseStrategy):
    """Base class for behavioral benchmark strategies (strictly PAPER_ONLY, 0 LIVE capital)."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Force PAPER_ONLY status and zero live capital allocation
        self.status = "PAPER_ONLY"
        self.allocated_capital_vnd = 0.0


class STR091_MartingaleGamblerBenchmark(BehavioralBase):
    """Martingale Gambler Benchmark: Doubles down on consecutive adverse ticks (paper benchmark)."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        best_bid = market_data.get("best_bid")
        if not best_bid:
            return None
        return {"side": "BUY", "price": round(best_bid * 0.999, 2), "quantity": self.order_size_btc}


class STR092_GamblersFallacyReversal(BehavioralBase):
    """Gambler's Fallacy Reversal: Bets on immediate reversal after streak of down candles."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 5:
            return None

        # 4 consecutive red ticks -> gambler bets on green
        if closes[-1] < closes[-2] < closes[-3] < closes[-4]:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR093_HotHandChaseBenchmark(BehavioralBase):
    """Hot Hand Chase Benchmark: Chases winning streaks assuming persistent luck."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 4:
            return None

        if closes[-1] > closes[-2] > closes[-3]:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR094_LossAversionSkew(BehavioralBase):
    """Loss Aversion Skew: Reluctance to realize losses, asymmetrical inventory holding."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        best_bid = market_data.get("best_bid")
        if not best_bid:
            return None
        return {"side": "BUY", "price": round(best_bid * 0.998, 2), "quantity": self.order_size_btc}


class STR095_OverconfidenceMomentum(BehavioralBase):
    """Overconfidence Momentum: Excessive position sizing following winning streaks."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        best_bid = market_data.get("best_bid")
        if not best_bid:
            return None
        return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}


class STR096_DispositionEffectBenchmark(BehavioralBase):
    """Disposition Effect Benchmark: Premature profit-taking and holding onto losing positions."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        best_bid = market_data.get("best_bid")
        if not best_bid:
            return None
        return {"side": "BUY", "price": round(best_bid * 0.999, 2), "quantity": self.order_size_btc}


class STR097_SunkCostAnchor(BehavioralBase):
    """Sunk Cost Anchor: Anchoring decisions on historical entry prices."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        best_bid = market_data.get("best_bid")
        if not best_bid:
            return None
        return {"side": "BUY", "price": round(best_bid * 0.9985, 2), "quantity": self.order_size_btc}


class STR098_FOMOSurgeChaser(BehavioralBase):
    """FOMO Surge Chaser: Aggressively buys parabolic green candles out of fear of missing out."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 15:
            return None

        rsi = calculate_rsi(closes, 14)
        if rsi and rsi > 70.0:  # Buys overbought FOMO
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR099_PanicSellReversion(BehavioralBase):
    """Panic Sell Reversion: Simulates retail capitulation selling at absolute bottom."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 15:
            return None

        rsi = calculate_rsi(closes, 14)
        if rsi and rsi < 25.0:  # Panics and dumps at bottom
            return {"side": "BUY", "price": round(best_bid * 0.995, 2), "quantity": self.order_size_btc}
        return None


class STR100_RandomWalkBenchmark(BehavioralBase):
    """Random Walk Benchmark: Pure stochastic baseline against which alpha is evaluated."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        best_bid = market_data.get("best_bid")
        if not best_bid:
            return None
        return {"side": "BUY", "price": round(best_bid * 0.999, 2), "quantity": self.order_size_btc}
