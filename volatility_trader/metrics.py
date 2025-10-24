from __future__ import annotations
from dataclasses import dataclass
from math import sqrt
from typing import List


@dataclass
class Trade:
    pnl: float
    adhered_to_plan: bool


@dataclass
class Daily:
    pnl: float


@dataclass
class Metrics:
    win_rate: float
    profit_factor: float
    avg_win_loss_ratio: float
    max_drawdown: float
    sharpe_ratio: float
    orders_per_day: float
    plan_adherence: float
    slippage_impact_bps: float


def compute_metrics(trades: List[Trade], dailies: List[Daily], slippage_bps_samples: List[float]) -> Metrics:
    wins = [t.pnl for t in trades if t.pnl > 0]
    losses = [-t.pnl for t in trades if t.pnl < 0]

    win_rate = (len(wins) / len(trades)) if trades else 0.0
    profit_factor = (sum(wins) / sum(losses)) if losses else (float("inf") if wins else 0.0)
    avg_win = (sum(wins) / len(wins)) if wins else 0.0
    avg_loss = (sum(losses) / len(losses)) if losses else 0.0
    avg_win_loss_ratio = (avg_win / avg_loss) if avg_loss > 0 else (float("inf") if avg_win > 0 else 0.0)

    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for d in dailies:
        equity += d.pnl
        peak = max(peak, equity)
        if peak > 0:
            dd = (equity - peak) / peak
            max_dd = min(max_dd, dd)
    max_drawdown = abs(max_dd)

    daily_returns = [d.pnl for d in dailies]
    if len(daily_returns) > 1:
        mean = sum(daily_returns) / len(daily_returns)
        var = sum((x - mean) ** 2 for x in daily_returns) / (len(daily_returns) - 1)
        std = sqrt(var) if var > 0 else 0.0
        sharpe = (mean / std) * sqrt(252) if std > 0 else 0.0
    else:
        sharpe = 0.0

    orders_per_day = (len(trades) / len(dailies)) if dailies else 0.0
    plan_adherence = (sum(1 for t in trades if t.adhered_to_plan) / len(trades)) if trades else 0.0
    slippage_impact_bps = sum(slippage_bps_samples) / len(slippage_bps_samples) if slippage_bps_samples else 0.0

    return Metrics(
        win_rate=win_rate,
        profit_factor=profit_factor,
        avg_win_loss_ratio=avg_win_loss_ratio,
        max_drawdown=max_drawdown,
        sharpe_ratio=sharpe,
        orders_per_day=orders_per_day,
        plan_adherence=plan_adherence,
        slippage_impact_bps=slippage_impact_bps,
    )
