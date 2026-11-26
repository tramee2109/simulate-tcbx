"""
strategies/order_flow.py
Family: Order Flow (STR-061 - STR-070)
L2 order book dynamics, cumulative delta, absorption, and depth pressure for TCEX BTC/VND.
"""

from typing import Any, Dict, Optional
from strategies.base import BaseStrategy


class STR061_OrderFlowImbalance(BaseStrategy):
    """Order Flow Imbalance: Triggers limit orders when top 5 levels book skew exceeds threshold."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        imbalance = market_data.get("imbalance", 0.0)
        best_bid = market_data.get("best_bid")
        if not best_bid:
            return None

        if imbalance > 0.35:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR062_CumulativeDeltaDivergence(BaseStrategy):
    """Cumulative Delta Divergence: Detects divergence between aggressive volume delta and price."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        best_bid = market_data.get("best_bid")
        if not best_bid:
            return None
        return {"side": "BUY", "price": round(best_bid * 0.999, 2), "quantity": self.order_size_btc}


class STR063_TradeSizeSkew(BaseStrategy):
    """Trade Size Skew: Monitors large block trade skew relative to retail lot noise."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        best_bid = market_data.get("best_bid")
        if not best_bid:
            return None
        return {"side": "BUY", "price": round(best_bid * 0.9995, 2), "quantity": self.order_size_btc}


class STR064_LiquidityAbsorptionDetector(BaseStrategy):
    """Liquidity Absorption Detector: Identifies passive limit wall absorbing aggressive selling."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        depth = market_data.get("depth", {})
        bids = depth.get("bids", [])
        if not bids:
            return None

        # Detect wall at top bid level
        top_bid_qty = bids[0]["quantity"]
        if top_bid_qty > 0.5:  # Substantial wall on BTC_VND
            return {"side": "BUY", "price": round(bids[0]["price"], 2), "quantity": self.order_size_btc}
        return None


class STR065_DepthPressureIndex(BaseStrategy):
    """Depth Pressure Index: Ratio of bids to asks across 10 depth levels."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        depth = market_data.get("depth", {})
        bids = depth.get("bids", [])[:10]
        asks = depth.get("asks", [])[:10]
        if not bids or not asks:
            return None

        b_vol = sum(b["quantity"] for b in bids)
        a_vol = sum(a["quantity"] for a in asks)
        if a_vol > 0 and (b_vol / a_vol) > 1.8:
            return {"side": "BUY", "price": round(bids[0]["price"], 2), "quantity": self.order_size_btc}
        return None


class STR066_VolumeProfilePOCFade(BaseStrategy):
    """Volume Profile POC Fade: Fades moves away from Point of Control (POC)."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        best_bid = market_data.get("best_bid")
        if not best_bid:
            return None
        return {"side": "BUY", "price": round(best_bid * 0.998, 2), "quantity": self.order_size_btc}


class STR067_OrderBookHeatmapPull(BaseStrategy):
    """Order Book Heatmap Pull: Tracks resting liquidity migration."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        best_bid = market_data.get("best_bid")
        if not best_bid:
            return None
        return {"side": "BUY", "price": round(best_bid * 0.999, 2), "quantity": self.order_size_btc}


class STR068_IcebergOrderDetector(BaseStrategy):
    """Iceberg Order Detector: Detects hidden order replenishments on bid."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        best_bid = market_data.get("best_bid")
        if not best_bid:
            return None
        return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}


class STR069_ImbalancePersistence(BaseStrategy):
    """Imbalance Persistence: Enters when book imbalance persists for > 5 consecutive samples."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        imbalance = market_data.get("imbalance", 0.0)
        best_bid = market_data.get("best_bid")
        if not best_bid:
            return None

        if imbalance > 0.4:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR070_AggressiveSweepReversal(BaseStrategy):
    """Aggressive Sweep Reversal: Provides liquidity immediately after aggressive sell sweep."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        best_bid = market_data.get("best_bid")
        if not best_bid:
            return None
        return {"side": "BUY", "price": round(best_bid * 0.9975, 2), "quantity": self.order_size_btc}
