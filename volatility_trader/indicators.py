from __future__ import annotations
from typing import List, Tuple


def ema(values: List[float], period: int) -> List[float]:
    if period <= 0 or not values:
        return []
    k = 2 / (period + 1)
    result: List[float] = []
    ema_val = values[0]
    for v in values:
        ema_val = (v * k) + (ema_val * (1 - k))
        result.append(ema_val)
    return result


def rsi(values: List[float], period: int = 14) -> List[float]:
    if len(values) < period + 1:
        return []
    gains: List[float] = []
    losses: List[float] = []
    for i in range(1, period + 1):
        change = values[i] - values[i - 1]
        gains.append(max(change, 0))
        losses.append(abs(min(change, 0)))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    rsis: List[float] = []
    for i in range(period + 1, len(values)):
        change = values[i] - values[i - 1]
        gain = max(change, 0)
        loss = abs(min(change, 0))
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss == 0:
            rsis.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsis.append(100 - (100 / (1 + rs)))
    return rsis


def atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> List[float]:
    if len(highs) != len(lows) or len(lows) != len(closes) or len(highs) < period + 1:
        return []
    trs: List[float] = []
    for i in range(1, len(highs)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        trs.append(tr)
    atrs: List[float] = []
    first_atr = sum(trs[:period]) / period
    atrs.append(first_atr)
    alpha = 1 / period
    for tr in trs[period:]:
        next_atr = atrs[-1] * (1 - alpha) + tr * alpha
        atrs.append(next_atr)
    return atrs


def bollinger(values: List[float], period: int = 20, num_std: float = 2.0) -> Tuple[List[float], List[float], List[float]]:
    if len(values) < period:
        return [], [], []
    ma: List[float] = []
    upper: List[float] = []
    lower: List[float] = []
    for i in range(period, len(values) + 1):
        window = values[i - period:i]
        m = sum(window) / period
        var = sum((x - m) ** 2 for x in window) / period
        sd = var ** 0.5
        ma.append(m)
        upper.append(m + num_std * sd)
        lower.append(m - num_std * sd)
    return lower, ma, upper


def rvol(volumes: List[float], lookback_days: int = 20) -> List[float]:
    if len(volumes) < lookback_days + 1:
        return []
    result: List[float] = []
    for i in range(lookback_days, len(volumes)):
        avg = sum(volumes[i - lookback_days:i]) / lookback_days
        result.append(volumes[i] / avg if avg > 0 else 0.0)
    return result
