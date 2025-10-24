from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, time
from typing import List, Optional

from .types import Bar, SignalContext
from .indicators import ema as ema_series, rsi as rsi_series, atr as atr_series, bollinger, rvol as rvol_series
from .config import TRADING_SCHEDULE


ET_SCAN_TIMES = [time.fromisoformat(t) for t in TRADING_SCHEDULE["scan_times_et"]]
NO_NEW_AFTER = time.fromisoformat(TRADING_SCHEDULE["no_new_after_et"])
CLOSE_ALL_BY = time.fromisoformat(TRADING_SCHEDULE["close_all_by_et"])


@dataclass
class ComputedSeries:
    ema50: float
    ema200: float
    rsi: float
    atr_percent: float
    bb_upper: float
    bb_lower: float
    bb_width: float
    rvol: float


def build_signal_context(bars: List[Bar]) -> Optional[SignalContext]:
    if len(bars) < 200:
        return None

    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    vols = [b.volume for b in bars]

    ema50_series = ema_series(closes, 50)
    ema200_series = ema_series(closes, 200)
    rsi_vals = rsi_series(closes, 14)
    atr_vals = atr_series(highs, lows, closes, 14)
    bb_lower, bb_ma, bb_upper = bollinger(closes, 20, 2.0)
    rvol_vals = rvol_series(vols, 20)

    latest_price = closes[-1]
    ema50 = ema50_series[-1] if len(ema50_series) > 0 else latest_price
    ema200 = ema200_series[-1] if len(ema200_series) > 0 else latest_price
    rsi = rsi_vals[-1] if len(rsi_vals) > 0 else 50.0
    atr = atr_vals[-1] if len(atr_vals) > 0 else 0.0
    bb_u = bb_upper[-1] if len(bb_upper) > 0 else latest_price
    bb_l = bb_lower[-1] if len(bb_lower) > 0 else latest_price
    bb_w = (bb_u - bb_l) / bb_l * 100 if bb_l != 0 else 0.0
    rvol = rvol_vals[-1] if len(rvol_vals) > 0 else 0.0

    atr_percent = (atr / latest_price) * 100 if latest_price != 0 else 0.0

    return SignalContext(
        rvol=rvol,
        atr_percent=atr_percent,
        rsi=rsi,
        price=latest_price,
        bb_upper=bb_u,
        bb_lower=bb_l,
        bb_width=bb_w,
        ema50=ema50,
        ema200=ema200,
    )


def is_scan_time_et(now_et: datetime) -> bool:
    t = now_et.time()
    return any(abs((datetime.combine(now_et.date(), st) - now_et).total_seconds()) <= 60 for st in ET_SCAN_TIMES)


def within_entry_window(now_et: datetime) -> bool:
    return now_et.time() < NO_NEW_AFTER


def close_all_time(now_et: datetime) -> bool:
    return now_et.time() >= CLOSE_ALL_BY
