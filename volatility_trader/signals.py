from __future__ import annotations
from .types import SignalContext, Decision

BREAKOUT = "BREAKOUT"
REVERSAL = "REVERSAL"

REQUIRED_RVOL = 1.8
REQUIRED_ATR_PCT = 4.0


def evaluate_breakout(
    ctx: SignalContext,
    bb_width_is_20d_low: bool,
    todays_volume_gt_yday: bool,
) -> Decision:
    if ctx.rvol <= REQUIRED_RVOL:
        return Decision(False, "RVOL fail")
    if ctx.atr_percent <= REQUIRED_ATR_PCT:
        return Decision(False, "ATR% fail")
    if ctx.price <= ctx.bb_upper:
        return Decision(False, "Price not > upper BB")
    if not bb_width_is_20d_low:
        return Decision(False, "BB width not at 20d low")
    if not todays_volume_gt_yday:
        return Decision(False, "Volume not > yesterday")
    return Decision(True, "BREAKOUT pass", BREAKOUT, ctx.price)


def evaluate_reversal(ctx: SignalContext) -> Decision:
    if ctx.rvol <= REQUIRED_RVOL:
        return Decision(False, "RVOL fail")
    if ctx.atr_percent <= REQUIRED_ATR_PCT:
        return Decision(False, "ATR% fail")
    if ctx.rsi >= 35:
        return Decision(False, "RSI not < 35")
    if ctx.price > ctx.bb_lower:
        return Decision(False, "Price not ≤ lower BB")
    if ctx.ema50 <= ctx.ema200:
        return Decision(False, "Trend filter fail (50<=200)")
    return Decision(True, "REVERSAL pass", REVERSAL, ctx.price)
