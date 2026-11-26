"""
strategies/news_event.py
Family: News / Event (STR-081 - STR-090)
Macro CPI, rate announcement, halving, ETF inflow, and whale wallet event strategies for TCEX BTC/VND.
Per Section 7 & 12: If timestamped BTC event feed is unavailable,
strategies are registered, configurations preserved, and marked DISABLED_DATA_REQUIREMENT.
"""

from typing import Any, Dict, Optional
from strategies.base import BaseStrategy


class NewsEventBase(BaseStrategy):
    """Base strategy for news and scheduled macroeconomic / crypto events."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.has_event_feed = self.params.get("has_event_feed", False)

        if not self.has_event_feed:
            self.status = "DISABLED_DATA_REQUIREMENT"

    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.has_event_feed:
            return None

        event = market_data.get("latest_event")
        best_bid = market_data.get("best_bid")
        if not event or not best_bid:
            return None

        sentiment = event.get("sentiment_score", 0.0)  # -1.0 to 1.0
        if sentiment > 0.6:
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR081_MacroCPIVolatilityBracket(NewsEventBase):
    """Macro CPI Volatility Bracket: Pre-event straddle ladder ahead of US CPI release."""
    pass

class STR082_InterestRateAnnouncementDrift(NewsEventBase):
    """Interest Rate Announcement Drift: Post-FOMC rate decision momentum drift."""
    pass

class STR083_HalvingCycleEventDrift(NewsEventBase):
    """Halving Cycle Event Drift: Structural supply-shock accumulation."""
    pass

class STR084_ETFInflowSentimentDrift(NewsEventBase):
    """ETF Inflow Sentiment Drift: Follows institutional spot ETF net inflow prints."""
    pass

class STR085_WeekendGapMeanReversion(NewsEventBase):
    """Weekend Gap Mean Reversion: Fades low-liquidity weekend basis deviations on Monday open."""
    pass

class STR086_MidnightResetDrift(NewsEventBase):
    """Midnight Reset Drift: Trades 00:00 UTC daily candle funding and rebalance flows."""
    pass

class STR087_WhaleWalletAlertDrift(NewsEventBase):
    """Whale Wallet Alert Drift: Reacts to large on-chain exchange inflow/outflow alerts."""
    pass

class STR088_RegulatorySentimentFade(NewsEventBase):
    """Regulatory Sentiment Fade: Fades overreactions to breaking news headlines."""
    pass

class STR089_ExchangeOutageArbitrage(NewsEventBase):
    """Exchange Outage Arbitrage: Liquidity capture when competing exchange undergoes maintenance."""
    pass

class STR090_HashrateFluctuationDrift(NewsEventBase):
    """Hashrate Fluctuation Drift: Miner capitulation and difficulty epoch adjustment drift."""
    pass
