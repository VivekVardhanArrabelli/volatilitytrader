from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict
from .types import Position
from .config import RISK_RULES


@dataclass
class AccountState:
    equity: float
    cash: float
    daily_pnl: float = 0.0
    trade_history: Dict[str, datetime] = field(default_factory=dict)


def check_circuit_breakers(account: AccountState, open_positions: Dict[str, Position], current_time: datetime) -> str:
    if account.equity > 0 and (account.daily_pnl / account.equity) < RISK_RULES["daily_loss_halt"]:
        return "HALT: Daily loss limit"
    if len(open_positions) >= RISK_RULES["max_positions"]:
        return "HALT: Max positions"
    for symbol, last_trade_time in account.trade_history.items():
        if (current_time - last_trade_time) < timedelta(hours=4):
            return f"HALT: {symbol} cooldown"
    return "OK"
