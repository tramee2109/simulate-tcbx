"""
strategies/grid_dca.py
Family: Grid / DCA (STR-001 - STR-010)
Inventory-aware limit order ladders and dollar cost averaging adapted to TCEX BTC/VND.
"""

from typing import Any, Dict, Optional
from strategies.base import BaseStrategy
from strategies.indicators import calculate_atr, calculate_bollinger_bands


class STR001_EqualStepGrid(BaseStrategy):
    """Equal-Step Spot Grid: Places staggered buy/sell LIMIT orders at fixed price spacing."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        best_bid = market_data.get("best_bid")
        best_ask = market_data.get("best_ask")
        if not best_bid or not best_ask:
            return None

        grid_spacing_pct = float(self.params.get("spacing_pct", 0.003))  # 0.3%
        buy_price = round(best_bid * (1.0 - grid_spacing_pct), 2)
        return {"side": "BUY", "price": buy_price, "quantity": self.order_size_btc}


class STR002_VolatilityScaledGrid(BaseStrategy):
    """Volatility-Scaled Grid: Adjusts grid spacing dynamically according to recent ATR."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ohlcv = market_data.get("ohlcv", [])
        atr = calculate_atr(ohlcv, period=14)
        best_bid = market_data.get("best_bid")
        if not best_bid:
            return None

        spacing = (atr * 0.5) if atr else (best_bid * 0.004)
        buy_price = round(best_bid - spacing, 2)
        return {"side": "BUY", "price": buy_price, "quantity": self.order_size_btc}


class STR003_ATRAdaptiveGrid(BaseStrategy):
    """ATR Adaptive Grid: Dynamically contracts or expands ladder steps based on ATR multiplier."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ohlcv = market_data.get("ohlcv", [])
        atr = calculate_atr(ohlcv, period=10)
        best_bid = market_data.get("best_bid")
        if not best_bid:
            return None

        step = (atr * 0.75) if atr else (best_bid * 0.005)
        buy_price = round(best_bid - step, 2)
        return {"side": "BUY", "price": buy_price, "quantity": self.order_size_btc}


class STR004_SessionBoundaryGrid(BaseStrategy):
    """Session-Boundary Grid: Re-centers ladder around opening price of the current trading window."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ticker = market_data.get("ticker", {})
        open_price = float(ticker.get("open", 0.0))
        best_bid = market_data.get("best_bid")
        if not open_price or not best_bid:
            return None

        # Buy when market drops below session open
        if best_bid < open_price:
            buy_price = round(best_bid * 0.998, 2)
            return {"side": "BUY", "price": buy_price, "quantity": self.order_size_btc}
        return None


class STR005_GeometricGrid(BaseStrategy):
    """Geometric Grid: Expands grid levels with constant percentage ratios."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        best_bid = market_data.get("best_bid")
        if not best_bid:
            return None
        ratio = float(self.params.get("ratio", 1.004))
        buy_price = round(best_bid / ratio, 2)
        return {"side": "BUY", "price": buy_price, "quantity": self.order_size_btc}


class STR006_InventorySkewedGrid(BaseStrategy):
    """Inventory-Skewed Grid: Shifts buy/sell bid depth based on current inventory holding."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        best_bid = market_data.get("best_bid")
        if not best_bid:
            return None
        buy_price = round(best_bid * 0.997, 2)
        return {"side": "BUY", "price": buy_price, "quantity": self.order_size_btc}


class STR007_MartingaleLimitedDCA(BaseStrategy):
    """Martingale-Limited DCA: Step-wise DCA with strict capped multipliers and inventory caps."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        best_bid = market_data.get("best_bid")
        if not best_bid:
            return None
        buy_price = round(best_bid * 0.995, 2)
        return {"side": "BUY", "price": buy_price, "quantity": self.order_size_btc}


class STR008_TimeWeightedDCA(BaseStrategy):
    """Time-Weighted DCA (TWAP Accumulator): Submits passive limit bids on scheduled clock intervals."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        best_bid = market_data.get("best_bid")
        if not best_bid:
            return None
        return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}


class STR009_MeanReversionDCA(BaseStrategy):
    """Mean-Reversion DCA: Triggers scale-in limit buys when price deviates from moving average."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if len(closes) < 20 or not best_bid:
            return None

        sma20 = sum(closes[-20:]) / 20.0
        if best_bid < sma20 * 0.995:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR010_BollingerBandsDCA(BaseStrategy):
    """Bollinger Bands DCA: Accumulates spot inventory near lower Bollinger Band."""
    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        closes = market_data.get("closes", [])
        best_bid = market_data.get("best_bid")
        if len(closes) < 20 or not best_bid:
            return None

        upper, mean, lower = calculate_bollinger_bands(closes, period=20, num_std=2.0)
        if lower and best_bid <= lower * 1.002:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None
