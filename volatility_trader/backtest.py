from __future__ import annotations
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List

from .types import Bar, Order, OrderType, Side, Position
from .signals import evaluate_breakout, evaluate_reversal, BREAKOUT
from .scanner import build_signal_context
from .risk import calculate_shares, calculate_stop_loss, calculate_take_profit
from .execution import ExecutionEngine
from .account import AccountState, check_circuit_breakers
from .metrics import compute_metrics, Trade, Daily


@dataclass
class BacktestResult:
    trades: List[Trade]
    dailies: List[Daily]


class StrategyBacktester:
    def __init__(self, account_equity: float):
        self.engine = ExecutionEngine()
        self.account = AccountState(equity=account_equity, cash=account_equity)
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.dailies: List[Daily] = []
        self.slippage_samples: List[float] = []

    def run(self, symbol_to_bars: Dict[str, List[Bar]]) -> BacktestResult:
        for symbol, bars in symbol_to_bars.items():
            if len(bars) < 200:
                continue
            ctx = build_signal_context(bars)
            if ctx is None:
                continue
            now = datetime.fromtimestamp(bars[-1].time, tz=timezone.utc)
            status = check_circuit_breakers(self.account, self.positions, now)
            if status != "OK":
                continue

            decision = evaluate_breakout(ctx, bb_width_is_20d_low=True, todays_volume_gt_yday=True)
            if not decision.should_enter:
                decision = evaluate_reversal(ctx)
            if not decision.should_enter:
                continue

            atr = ctx.atr_percent * ctx.price / 100
            stop = calculate_stop_loss(decision.signal_type or BREAKOUT, ctx.price, atr)
            tp = calculate_take_profit(ctx.price, stop, decision.signal_type or BREAKOUT)
            qty = calculate_shares(self.account.equity, ctx.price, stop)
            if qty <= 0:
                continue

            entry = Order(symbol=symbol, side=Side.BUY, quantity=qty, order_type=OrderType.MARKET)
            fill = self.engine.simulate_fill(entry, {"bid": ctx.price * 0.999, "ask": ctx.price * 1.001, "volume": 1_000_000, "time": bars[-1].time})
            if not fill:
                continue

            oco_id = str(uuid.uuid4())
            stop_order = Order(symbol=symbol, side=Side.SELL, quantity=qty, order_type=OrderType.LIMIT, price=stop, oco_group=oco_id)
            tp_order = Order(symbol=symbol, side=Side.SELL, quantity=qty, order_type=OrderType.LIMIT, price=tp, oco_group=oco_id)
            stop_fill, tp_fill = self.engine.process_oco(stop_order, tp_order, {"bid": ctx.price * 0.999, "ask": ctx.price * 1.001, "volume": 1_000_000, "last": ctx.price})

            if stop_fill or tp_fill:
                exit_fill = stop_fill or tp_fill
                pnl = (exit_fill.price - fill.price) * qty
                self.trades.append(Trade(pnl=pnl, adhered_to_plan=True))
                self.account.daily_pnl += pnl
                self.account.cash += pnl

            self.dailies.append(Daily(pnl=self.account.daily_pnl))

        return BacktestResult(trades=self.trades, dailies=self.dailies)

    def summarize(self) -> dict:
        m = compute_metrics(self.trades, self.dailies, self.slippage_samples)
        return {
            "win_rate": m.win_rate,
            "profit_factor": m.profit_factor,
            "avg_win_loss_ratio": m.avg_win_loss_ratio,
            "max_drawdown": m.max_drawdown,
            "sharpe_ratio": m.sharpe_ratio,
            "orders_per_day": m.orders_per_day,
            "plan_adherence": m.plan_adherence,
            "slippage_impact_bps": m.slippage_impact_bps,
        }
