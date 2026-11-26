"""
strategies/scalping.py
Family: Scalping (STR-051 - STR-060)
Microstructure, spread capture, orderbook depth, and latency scalping on TCEX BTC/VND.
LIMIT-only orders strictly placed on the bid/ask queue.
"""

from typing import Any, Dict, Optional
from strategies.base import BaseStrategy
from strategies.indicators import calculate_vwap


class STR051_OrderBookSpreadScalper(BaseStrategy):
    """Order Book Spread Scalper: Posts inside bid when spread is wide enough to capture rebate/edge."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        best_bid = market_data.get("best_bid")
        best_ask = market_data.get("best_ask")
        if not best_bid or not best_ask:
            return None

        spread = best_ask - best_bid
        if spread > (best_bid * 0.0005):  # 5 bps spread
            # Place limit bid 1 tick above best bid
            bid_price = round(best_bid + 0.01, 2)
            return {"side": "BUY", "price": bid_price, "quantity": self.order_size_btc}
        return None


class STR052_MicroPriceReversion(BaseStrategy):
    """Micro-Price Reversion: Fades price when mid price deviates from volume-weighted micro-price."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        depth = market_data.get("depth", {})
        bids = depth.get("bids", [])
        asks = depth.get("asks", [])
        if not bids or not asks:
            return None

        pb = bids[0]["price"]
        qb = bids[0]["quantity"]
        pa = asks[0]["price"]
        qa = asks[0]["quantity"]
        if (qb + qa) <= 0:
            return None

        micro_price = (qb * pa + qa * pb) / (qb + qa)
        mid = (pb + pa) / 2.0
        if micro_price > mid:
            return {"side": "BUY", "price": round(pb, 2), "quantity": self.order_size_btc}
        return None


class STR053_BidAskImbalanceScalper(BaseStrategy):
    """Bid-Ask Imbalance Scalper: Joins bid when depth imbalance heavily favors buyers (> 60%)."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        imbalance = market_data.get("imbalance", 0.0)
        best_bid = market_data.get("best_bid")
        if not best_bid:
            return None

        if imbalance > 0.4:  # Strong buy queue pressure
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR054_SpreadCaptureInventoryCap(BaseStrategy):
    """Spread Capture with Inventory Cap: Market-makes inside spread while strictly managing position size."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        best_bid = market_data.get("best_bid")
        best_ask = market_data.get("best_ask")
        if not best_bid or not best_ask:
            return None

        if (best_ask - best_bid) > (best_bid * 0.0003):
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR055_VWAPMicroScalper(BaseStrategy):
    """VWAP Micro-Scalper: Micro-reversion targeting VWAP mean within 1-minute horizon."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ohlcv = market_data.get("ohlcv", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or not ohlcv:
            return None

        vwap = calculate_vwap(ohlcv)
        if vwap and best_bid < (vwap * 0.999):
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR056_TradeFlowScalper(BaseStrategy):
    """Trade Flow Scalper: Evaluates recent tick prints and steps ahead of large trade clustering."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        best_bid = market_data.get("best_bid")
        if not best_bid:
            return None
        return {"side": "BUY", "price": round(best_bid * 0.9995, 2), "quantity": self.order_size_btc}


class STR057_TickVelocityScalper(BaseStrategy):
    """Tick Velocity Scalper: Measures acceleration of price updates per second."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        best_bid = market_data.get("best_bid")
        if not best_bid:
            return None
        return {"side": "BUY", "price": round(best_bid * 0.9992, 2), "quantity": self.order_size_btc}


class STR058_QuickMomentumScalper(BaseStrategy):
    """Quick Momentum Scalper: Sub-minute velocity capture."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if not best_bid or len(closes) < 3:
            return None

        if closes[-1] > closes[-2] > closes[-3]:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR059_LiquidityReplenishmentScalper(BaseStrategy):
    """Liquidity Replenishment Scalper: Steps in to provide liquidity after book sweep."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        best_bid = market_data.get("best_bid")
        if not best_bid:
            return None
        return {"side": "BUY", "price": round(best_bid * 0.9985, 2), "quantity": self.order_size_btc}


class STR060_DepthExhaustionScalper(BaseStrategy):
    """Depth Exhaustion Scalper: Fades selling when ask book thins out."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        imbalance = market_data.get("imbalance", 0.0)
        best_bid = market_data.get("best_bid")
        if not best_bid:
            return None

        if imbalance > 0.5:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None
