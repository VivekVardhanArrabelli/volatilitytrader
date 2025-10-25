from dataclasses import dataclass, field
from typing import Literal

FILL_RULES = {
    "limit_offset_bps": 15,
    "slippage_bps": 5,
    "min_spread_bps": 3,
    "volume_participation": 0.05,
}

RISK_RULES = {
    "risk_fraction": 0.01,
    "max_gross_exposure": 0.30,
    "per_symbol_max": 0.15,
    "max_positions": 3,
    "daily_loss_halt": -0.03,
}

TRADING_SCHEDULE = {
    "scan_times_et": ["09:45", "11:00", "13:00", "14:30"],
    "no_new_after_et": "15:00",
    "close_all_by_et": "15:45",
}


@dataclass(frozen=True)
class Config:
    fill_rules: dict = field(default_factory=lambda: FILL_RULES.copy())
    risk_rules: dict = field(default_factory=lambda: RISK_RULES.copy())
    trading_schedule: dict = field(default_factory=lambda: TRADING_SCHEDULE.copy())
    timezone: Literal["US/Eastern"] = "US/Eastern"
