"""
strategies package initialization and 100-strategy registry factory.
"""

from typing import Any, Dict, List, Optional, Type
from strategies.base import BaseStrategy

# Import all 10 family modules
from strategies.grid_dca import (
    STR001_EqualStepGrid,
    STR002_VolatilityScaledGrid,
    STR003_ATRAdaptiveGrid,
    STR004_SessionBoundaryGrid,
    STR005_GeometricGrid,
    STR006_InventorySkewedGrid,
    STR007_MartingaleLimitedDCA,
    STR008_TimeWeightedDCA,
    STR009_MeanReversionDCA,
    STR010_BollingerBandsDCA,
)
from strategies.mean_reversion import (
    STR011_RSIMeanReversion,
    STR012_BollingerBandFade,
    STR013_VWAPMeanReversion,
    STR014_ZScoreSpread,
    STR015_StochasticOscillatorFade,
    STR016_MovingAverageDistance,
    STR017_KeltnerChannelReversal,
    STR018_StdDevEnvelope,
    STR019_CCIMeanReversion,
    STR020_HullMAReversal,
)
from strategies.trend_following import (
    STR021_DualEMACrossover,
    STR022_MACDTrendRider,
    STR023_SuperTrendFollower,
    STR024_ADXTrendConfirmation,
    STR025_ParabolicSARTrend,
    STR026_TripleMovingAverage,
    STR027_IchimokuKinkoHyo,
    STR028_DonchianChannelTrend,
    STR029_TEMACrossover,
    STR030_VolumeWeightedTrend,
)
from strategies.momentum import (
    STR031_RateOfChangeMomentum,
    STR032_StochasticMomentumIndex,
    STR033_RSIMomentumSurge,
    STR034_MACDHistogramAcceleration,
    STR035_TrendIntensityIndex,
    STR036_ChandeMomentumOscillator,
    STR037_MomentumCompressionRelease,
    STR038_RelativeMomentumIndex,
    STR039_WilliamsPercentRMomentum,
    STR040_MultiTimeframeMomentum,
)
from strategies.breakout import (
    STR041_DonchianRangeBreakout,
    STR042_VolatilitySqueezeBreakout,
    STR043_PivotPointsBreakout,
    STR044_HighLowFractalBreakout,
    STR045_ATRExpansionBreakout,
    STR046_OpeningRangeBreakout,
    STR047_VolumeSpikeBreakout,
    STR048_NarrowRange7Breakout,
    STR049_DoubleTopBottomBreakout,
    STR050_TrianglePatternBreakout,
)
from strategies.scalping import (
    STR051_OrderBookSpreadScalper,
    STR052_MicroPriceReversion,
    STR053_BidAskImbalanceScalper,
    STR054_SpreadCaptureInventoryCap,
    STR055_VWAPMicroScalper,
    STR056_TradeFlowScalper,
    STR057_TickVelocityScalper,
    STR058_QuickMomentumScalper,
    STR059_LiquidityReplenishmentScalper,
    STR060_DepthExhaustionScalper,
)
from strategies.order_flow import (
    STR061_OrderFlowImbalance,
    STR062_CumulativeDeltaDivergence,
    STR063_TradeSizeSkew,
    STR064_LiquidityAbsorptionDetector,
    STR065_DepthPressureIndex,
    STR066_VolumeProfilePOCFade,
    STR067_OrderBookHeatmapPull,
    STR068_IcebergOrderDetector,
    STR069_ImbalancePersistence,
    STR070_AggressiveSweepReversal,
)
from strategies.cross_arbitrage import (
    STR071_BinanceTCEXReferenceBasis,
    STR072_OKXTCEXReferenceBasis,
    STR073_SyntheticFXArbitrage,
    STR074_TriangularBasisMonitor,
    STR075_ReferenceLeadLagArbitrage,
    STR076_FundingRateBasisDivergence,
    STR077_PremiumIndexMeanReversion,
    STR078_LatencyArbGuard,
    STR079_CrossVenueLiquidityMirror,
    STR080_ReferenceMomentumLead,
)
from strategies.news_event import (
    STR081_MacroCPIVolatilityBracket,
    STR082_InterestRateAnnouncementDrift,
    STR083_HalvingCycleEventDrift,
    STR084_ETFInflowSentimentDrift,
    STR085_WeekendGapMeanReversion,
    STR086_MidnightResetDrift,
    STR087_WhaleWalletAlertDrift,
    STR088_RegulatorySentimentFade,
    STR089_ExchangeOutageArbitrage,
    STR090_HashrateFluctuationDrift,
)
from strategies.behavioral import (
    STR091_MartingaleGamblerBenchmark,
    STR092_GamblersFallacyReversal,
    STR093_HotHandChaseBenchmark,
    STR094_LossAversionSkew,
    STR095_OverconfidenceMomentum,
    STR096_DispositionEffectBenchmark,
    STR097_SunkCostAnchor,
    STR098_FOMOSurgeChaser,
    STR099_PanicSellReversion,
    STR100_RandomWalkBenchmark,
)

# Registry mapping Strategy ID to implementation class
STRATEGY_REGISTRY: Dict[str, Type[BaseStrategy]] = {
    # Grid / DCA (001 - 010)
    "STR-001": STR001_EqualStepGrid,
    "STR-002": STR002_VolatilityScaledGrid,
    "STR-003": STR003_ATRAdaptiveGrid,
    "STR-004": STR004_SessionBoundaryGrid,
    "STR-005": STR005_GeometricGrid,
    "STR-006": STR006_InventorySkewedGrid,
    "STR-007": STR007_MartingaleLimitedDCA,
    "STR-008": STR008_TimeWeightedDCA,
    "STR-009": STR009_MeanReversionDCA,
    "STR-010": STR010_BollingerBandsDCA,

    # Mean Reversion (011 - 020)
    "STR-011": STR011_RSIMeanReversion,
    "STR-012": STR012_BollingerBandFade,
    "STR-013": STR013_VWAPMeanReversion,
    "STR-014": STR014_ZScoreSpread,
    "STR-015": STR015_StochasticOscillatorFade,
    "STR-016": STR016_MovingAverageDistance,
    "STR-017": STR017_KeltnerChannelReversal,
    "STR-018": STR018_StdDevEnvelope,
    "STR-019": STR019_CCIMeanReversion,
    "STR-020": STR020_HullMAReversal,

    # Trend Following (021 - 030)
    "STR-021": STR021_DualEMACrossover,
    "STR-022": STR022_MACDTrendRider,
    "STR-023": STR023_SuperTrendFollower,
    "STR-024": STR024_ADXTrendConfirmation,
    "STR-025": STR025_ParabolicSARTrend,
    "STR-026": STR026_TripleMovingAverage,
    "STR-027": STR027_IchimokuKinkoHyo,
    "STR-028": STR028_DonchianChannelTrend,
    "STR-029": STR029_TEMACrossover,
    "STR-030": STR030_VolumeWeightedTrend,

    # Momentum (031 - 040)
    "STR-031": STR031_RateOfChangeMomentum,
    "STR-032": STR032_StochasticMomentumIndex,
    "STR-033": STR033_RSIMomentumSurge,
    "STR-034": STR034_MACDHistogramAcceleration,
    "STR-035": STR035_TrendIntensityIndex,
    "STR-036": STR036_ChandeMomentumOscillator,
    "STR-037": STR037_MomentumCompressionRelease,
    "STR-038": STR038_RelativeMomentumIndex,
    "STR-039": STR039_WilliamsPercentRMomentum,
    "STR-040": STR040_MultiTimeframeMomentum,

    # Breakout (041 - 050)
    "STR-041": STR041_DonchianRangeBreakout,
    "STR-042": STR042_VolatilitySqueezeBreakout,
    "STR-043": STR043_PivotPointsBreakout,
    "STR-044": STR044_HighLowFractalBreakout,
    "STR-045": STR045_ATRExpansionBreakout,
    "STR-046": STR046_OpeningRangeBreakout,
    "STR-047": STR047_VolumeSpikeBreakout,
    "STR-048": STR048_NarrowRange7Breakout,
    "STR-049": STR049_DoubleTopBottomBreakout,
    "STR-050": STR050_TrianglePatternBreakout,

    # Scalping (051 - 060)
    "STR-051": STR051_OrderBookSpreadScalper,
    "STR-052": STR052_MicroPriceReversion,
    "STR-053": STR053_BidAskImbalanceScalper,
    "STR-054": STR054_SpreadCaptureInventoryCap,
    "STR-055": STR055_VWAPMicroScalper,
    "STR-056": STR056_TradeFlowScalper,
    "STR-057": STR057_TickVelocityScalper,
    "STR-058": STR058_QuickMomentumScalper,
    "STR-059": STR059_LiquidityReplenishmentScalper,
    "STR-060": STR060_DepthExhaustionScalper,

    # Order Flow (061 - 070)
    "STR-061": STR061_OrderFlowImbalance,
    "STR-062": STR062_CumulativeDeltaDivergence,
    "STR-063": STR063_TradeSizeSkew,
    "STR-064": STR064_LiquidityAbsorptionDetector,
    "STR-065": STR065_DepthPressureIndex,
    "STR-066": STR066_VolumeProfilePOCFade,
    "STR-067": STR067_OrderBookHeatmapPull,
    "STR-068": STR068_IcebergOrderDetector,
    "STR-069": STR069_ImbalancePersistence,
    "STR-070": STR070_AggressiveSweepReversal,

    # Cross-Exchange Arbitrage (071 - 080)
    "STR-071": STR071_BinanceTCEXReferenceBasis,
    "STR-072": STR072_OKXTCEXReferenceBasis,
    "STR-073": STR073_SyntheticFXArbitrage,
    "STR-074": STR074_TriangularBasisMonitor,
    "STR-075": STR075_ReferenceLeadLagArbitrage,
    "STR-076": STR076_FundingRateBasisDivergence,
    "STR-077": STR077_PremiumIndexMeanReversion,
    "STR-078": STR078_LatencyArbGuard,
    "STR-079": STR079_CrossVenueLiquidityMirror,
    "STR-080": STR080_ReferenceMomentumLead,

    # News / Event (081 - 090)
    "STR-081": STR081_MacroCPIVolatilityBracket,
    "STR-082": STR082_InterestRateAnnouncementDrift,
    "STR-083": STR083_HalvingCycleEventDrift,
    "STR-084": STR084_ETFInflowSentimentDrift,
    "STR-085": STR085_WeekendGapMeanReversion,
    "STR-086": STR086_MidnightResetDrift,
    "STR-087": STR087_WhaleWalletAlertDrift,
    "STR-088": STR088_RegulatorySentimentFade,
    "STR-089": STR089_ExchangeOutageArbitrage,
    "STR-090": STR090_HashrateFluctuationDrift,

    # Behavioral / Gambling Benchmark (091 - 100)
    "STR-091": STR091_MartingaleGamblerBenchmark,
    "STR-092": STR092_GamblersFallacyReversal,
    "STR-093": STR093_HotHandChaseBenchmark,
    "STR-094": STR094_LossAversionSkew,
    "STR-095": STR095_OverconfidenceMomentum,
    "STR-096": STR096_DispositionEffectBenchmark,
    "STR-097": STR097_SunkCostAnchor,
    "STR-098": STR098_FOMOSurgeChaser,
    "STR-099": STR099_PanicSellReversion,
    "STR-100": STR100_RandomWalkBenchmark,
}


def create_strategy(
    strategy_id: str,
    name: str,
    family: str,
    account_id: str,
    role: str,
    allocated_capital_vnd: float,
    params: Optional[Dict[str, Any]] = None,
    status: Optional[str] = None,
) -> BaseStrategy:
    """Instantiate a strategy by its ID."""
    cls = STRATEGY_REGISTRY.get(strategy_id)
    if not cls:
        raise ValueError(f"Unknown strategy ID: {strategy_id}")

    # Set default status if not provided
    default_status = "PAPER_ONLY" if strategy_id.startswith("STR-09") or strategy_id == "STR-100" else "ACTIVE"
    strat_status = status or default_status

    return cls(
        strategy_id=strategy_id,
        name=name,
        family=family,
        account_id=account_id,
        role=role,
        allocated_capital_vnd=allocated_capital_vnd,
        params=params or {},
        status=strat_status,
    )
