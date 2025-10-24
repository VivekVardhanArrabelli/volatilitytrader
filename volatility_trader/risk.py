from __future__ import annotations


def calculate_shares(account_equity: float, entry_price: float, stop_price: float, risk_fraction: float = 0.01) -> int:
    price_risk = abs(entry_price - stop_price)
    if price_risk <= 0:
        return 0
    risk_amount = account_equity * risk_fraction
    return int(risk_amount / price_risk)


def calculate_stop_loss(signal_type: str, entry_price: float, atr: float) -> float:
    if signal_type == "BREAKOUT":
        return entry_price - (2.0 * atr)
    if signal_type == "REVERSAL":
        return entry_price - (1.5 * atr)
    raise ValueError("Unknown signal_type")


def calculate_take_profit(entry_price: float, stop_price: float, signal_type: str) -> float:
    risk = abs(entry_price - stop_price)
    if risk <= 0:
        return entry_price
    if signal_type == "BREAKOUT":
        return entry_price + (3.0 * risk)
    if signal_type == "REVERSAL":
        return entry_price + (2.5 * risk)
    raise ValueError("Unknown signal_type")
