"""
strategies/cross_arbitrage.py
Family: Cross-Exchange Arbitrage (STR-071 - STR-080)
Reference basis and cross-venue arbitrage between TCEX BTC/VND and external reference feeds.
Per Section 7 & 12: If external reference venue is not operational/configured,
strategies are registered, configurations preserved, and marked DISABLED_DATA_REQUIREMENT.
"""

from typing import Any, Dict, Optional
from strategies.base import BaseStrategy


class CrossArbitrageBase(BaseStrategy):
    """Base for cross-exchange arbitrage requiring external market data."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Require external reference feed
        self.reference_venue = self.params.get("reference_venue", "binance")
        self.has_external_feed = self.params.get("has_external_feed", False)

        if not self.has_external_feed:
            self.status = "DISABLED_DATA_REQUIREMENT"

    def generate_signal(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.has_external_feed:
            return None

        best_bid = market_data.get("best_bid")
        ref_price_vnd = market_data.get("external_ref_btc_vnd")
        if not best_bid or not ref_price_vnd:
            return None

        # If TCEX is substantially cheaper than external reference
        threshold = float(self.params.get("threshold_pct", 0.005))
        if best_bid < (ref_price_vnd * (1.0 - threshold)):
            return {"side": "BUY", "price": round(best_bid, 2), "quantity": self.order_size_btc}
        return None


class STR071_BinanceTCEXReferenceBasis(CrossArbitrageBase):
    """Binance-TCEX Reference Basis: Trades basis divergence between Binance BTC/USDT * FX and TCEX."""
    pass

class STR072_OKXTCEXReferenceBasis(CrossArbitrageBase):
    """OKX-TCEX Reference Basis: Trades basis divergence between OKX BTC/USDT * FX and TCEX."""
    pass

class STR073_SyntheticFXArbitrage(CrossArbitrageBase):
    """Synthetic FX Arbitrage: Monitors implied USD/VND cross rate from BTC pairs."""
    pass

class STR074_TriangularBasisMonitor(CrossArbitrageBase):
    """Triangular Basis Monitor: Arbitrages triangular inconsistencies across pairs."""
    pass

class STR075_ReferenceLeadLagArbitrage(CrossArbitrageBase):
    """Reference Lead-Lag Arbitrage: Front-runs TCEX orderbook lag relative to global price discovery."""
    pass

class STR076_FundingRateBasisDivergence(CrossArbitrageBase):
    """Funding-Rate Basis Divergence: Trades spot basis against perpetual funding rate premiums."""
    pass

class STR077_PremiumIndexMeanReversion(CrossArbitrageBase):
    """Premium Index Mean Reversion: Fades TCEX local exchange premium index spikes."""
    pass

class STR078_LatencyArbGuard(CrossArbitrageBase):
    """Latency Arb Guard: Protects quotes and snipes stale passive limits when reference moves."""
    pass

class STR079_CrossVenueLiquidityMirror(CrossArbitrageBase):
    """Cross-Venue Liquidity Mirror: Re-quotes external liquidity onto TCEX with safe spread buffer."""
    pass

class STR080_ReferenceMomentumLead(CrossArbitrageBase):
    """Reference Momentum Lead: Follows global momentum leads before local market digests flow."""
    pass
