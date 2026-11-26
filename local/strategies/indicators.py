"""
strategies/indicators.py
Technical indicators and mathematical models for TCEX BTC/VND strategy logic.
"""

import math
from typing import Dict, List, Optional, Tuple


def calculate_sma(prices: List[float], period: int) -> Optional[float]:
    if len(prices) < period or period <= 0:
        return None
    return sum(prices[-period:]) / period


def calculate_ema(prices: List[float], period: int) -> Optional[float]:
    if len(prices) < period or period <= 0:
        return None
    multiplier = 2.0 / (period + 1)
    ema = sum(prices[:period]) / period
    for p in prices[period:]:
        ema = (p - ema) * multiplier + ema
    return ema


def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
    if len(prices) < period + 1:
        return None

    gains = []
    losses = []
    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]
        if change > 0:
            gains.append(change)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(change))

    if len(gains) < period:
        return None

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def calculate_bollinger_bands(
    prices: List[float], period: int = 20, num_std: float = 2.0
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    if len(prices) < period:
        return None, None, None

    subset = prices[-period:]
    mean = sum(subset) / period
    variance = sum((x - mean) ** 2 for x in subset) / period
    std = math.sqrt(variance)

    upper = mean + (num_std * std)
    lower = mean - (num_std * std)
    return upper, mean, lower


def calculate_atr(ohlcv: List[Dict[str, float]], period: int = 14) -> Optional[float]:
    if len(ohlcv) < period + 1:
        return None

    true_ranges = []
    for i in range(1, len(ohlcv)):
        high = ohlcv[i]["high"]
        low = ohlcv[i]["low"]
        prev_close = ohlcv[i - 1]["close"]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        true_ranges.append(tr)

    if len(true_ranges) < period:
        return None
    return sum(true_ranges[-period:]) / period


def calculate_macd(
    prices: List[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    if len(prices) < slow_period + signal_period:
        return None, None, None

    fast_ema = calculate_ema(prices, fast_period)
    slow_ema = calculate_ema(prices, slow_period)
    if fast_ema is None or slow_ema is None:
        return None, None, None

    macd_line = fast_ema - slow_ema
    # Approximate signal line
    signal_line = macd_line * 0.9  # smoothed approximation
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def calculate_zscore(prices: List[float], period: int = 20) -> Optional[float]:
    if len(prices) < period:
        return None
    subset = prices[-period:]
    mean = sum(subset) / period
    variance = sum((x - mean) ** 2 for x in subset) / period
    std = math.sqrt(variance)
    if std <= 1e-8:
        return 0.0
    return (prices[-1] - mean) / std


def calculate_vwap(ohlcv: List[Dict[str, float]]) -> Optional[float]:
    if not ohlcv:
        return None
    cum_pv = 0.0
    cum_vol = 0.0
    for bar in ohlcv:
        typical_price = (bar["high"] + bar["low"] + bar["close"]) / 3.0
        vol = bar["volume"]
        cum_pv += typical_price * vol
        cum_vol += vol

    if cum_vol <= 0:
        return None
    return cum_pv / cum_vol
