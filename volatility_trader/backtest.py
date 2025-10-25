from __future__ import annotations
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from .types import Bar, Order, OrderType, Side, Position
from .signals import evaluate_breakout, evaluate_reversal, BREAKOUT
from .scanner import build_signal_context
from .risk import calculate_shares, calculate_stop_loss, calculate_take_profit
from .execution import ExecutionEngine
from .account import AccountState, check_circuit_breakers
from .metrics import compute_metrics, Trade, Daily
from .config import RISK_RULES, FILL_RULES


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

    def _current_price(self, symbol: str, market_by_symbol: Dict[str, Dict[str, float]]) -> Optional[float]:
        m = market_by_symbol.get(symbol)
        return m.get("last") if m else None

    def _gross_exposure(self, market_by_symbol: Dict[str, Dict[str, float]]) -> float:
        gross = 0.0
        for sym, pos in self.positions.items():
            price = self._current_price(sym, market_by_symbol)
            if price is None:
                continue
            gross += abs(price * pos.quantity)
        return gross

    def _check_position_limits(self, symbol: str, new_qty: int, market_by_symbol: Dict[str, Dict[str, float]]) -> bool:
        price = self._current_price(symbol, market_by_symbol)
        if price is None:
            return False
        per_symbol_limit = RISK_RULES["per_symbol_max"]
        gross_limit = RISK_RULES["max_gross_exposure"]

        new_value = price * new_qty
        # Per-symbol limit
        if new_value > self.account.equity * per_symbol_limit:
            return False

        gross_now = self._gross_exposure(market_by_symbol)
        if gross_now + new_value > self.account.equity * gross_limit:
            return False
        return True

    def _recompute_equity(self, market_by_symbol: Dict[str, Dict[str, float]]) -> None:
        equity = self.account.cash
        for sym, pos in self.positions.items():
            m = market_by_symbol.get(sym)
            if not m:
                continue
            price = m.get("last")
            if price is None:
                continue
            equity += price * pos.quantity
        self.account.equity = equity

    def run(self, symbol_to_bars: Dict[str, List[Bar]]) -> BacktestResult:
        # Build a global timeline of all bar times
        all_times = sorted({b.time for bars in symbol_to_bars.values() for b in bars})
        # Index bars per symbol by time
        bars_by_symbol_time: Dict[str, Dict[int, Bar]] = {
            symbol: {b.time: b for b in bars}
            for symbol, bars in symbol_to_bars.items()
        }

        last_day: Optional[Tuple[int, int, int]] = None
        for t in all_times:
            # Construct per-symbol rolling history up to time t for indicators
            market_by_symbol: Dict[str, Dict[str, float]] = {}
            for symbol, bars in symbol_to_bars.items():
                # Build current history up to t
                history = [b for b in bars if b.time <= t]
                if len(history) < 200:
                    continue
                ctx = build_signal_context(history)
                if ctx is None:
                    continue

                # Prepare market snapshot for fills and OCO monitoring
                market_by_symbol[symbol] = {
                    "bid": ctx.price * 0.999,
                    "ask": ctx.price * 1.001,
                    "last": ctx.price,
                    "volume": 1_000_000,
                    "time": t,
                }

            # Recompute equity with the latest prices available
            self._recompute_equity(market_by_symbol)

            # After we have market snapshots, evaluate entries per symbol
            for symbol, bars in symbol_to_bars.items():
                history = [b for b in bars if b.time <= t]
                if len(history) < 200 or symbol not in market_by_symbol:
                    continue
                ctx = build_signal_context(history)
                if ctx is None:
                    continue
                now = datetime.fromtimestamp(t, tz=timezone.utc)
                status = check_circuit_breakers(self.account, self.positions, now)
                if status != "OK":
                    continue

                decision = evaluate_breakout(ctx, bb_width_is_20d_low=True, todays_volume_gt_yday=True)
                if not decision.should_enter:
                    decision = evaluate_reversal(ctx)

                if decision.should_enter and symbol not in self.positions:
                    atr = ctx.atr_percent * ctx.price / 100
                    stop = calculate_stop_loss(decision.signal_type or BREAKOUT, ctx.price, atr)
                    tp = calculate_take_profit(ctx.price, stop, decision.signal_type or BREAKOUT)
                    # Position size by risk and cash/exposure constraints
                    qty = calculate_shares(
                        self.account.equity,
                        ctx.price,
                        stop,
                        RISK_RULES.get("risk_fraction", 0.01),
                    )
                    # Cap by available cash using conservative fill estimate (ask + slippage)
                    ask = market_by_symbol[symbol]["ask"]
                    slip_factor = 1 + (FILL_RULES["slippage_bps"] / 10000)
                    est_fill_per_share = ask * slip_factor if ask > 0 else ctx.price
                    if est_fill_per_share > 0:
                        max_qty_by_cash = int(self.account.cash // est_fill_per_share)
                        qty = max(0, min(qty, max_qty_by_cash))
                    if qty <= 0:
                        continue
                    if not self._check_position_limits(symbol, qty, market_by_symbol):
                        continue

                    entry = Order(symbol=symbol, side=Side.BUY, quantity=qty, order_type=OrderType.MARKET)
                    fill = self.engine.simulate_fill(entry, market_by_symbol[symbol])
                    if not fill:
                        continue

                    # Open position
                    # Deduct cash for the purchase
                    self.account.cash -= fill.price * fill.filled_qty
                    self.positions[symbol] = Position(
                        symbol=symbol,
                        quantity=fill.filled_qty,
                        avg_price=fill.price,
                        stop_price=stop,
                        take_profit=tp,
                        entry_time=t,
                        bars_held=0,
                        peak_unrealized=0.0,
                        max_drawdown_unrealized=0.0,
                        time_in_drawdown_bars=0,
                        last_price=fill.price,
                    )
                    # Update trade history for cooldown logic
                    self.account.trade_history[symbol] = now
                    # Register OCO orders for continuous monitoring
                    oco_id = str(uuid.uuid4())
                    stop_order = Order(symbol=symbol, side=Side.SELL, quantity=qty, order_type=OrderType.LIMIT, price=stop, oco_group=oco_id)
                    tp_order = Order(symbol=symbol, side=Side.SELL, quantity=qty, order_type=OrderType.LIMIT, price=tp, oco_group=oco_id)
                    self.engine.register_oco(stop_order, tp_order)

            # Continuous monitoring of OCOs across symbols at this time step
            fills = self.engine.check_open_orders(market_by_symbol)
            for fill in fills:
                symbol = fill.order.symbol
                pos = self.positions.get(symbol)
                if not pos:
                    continue
                # Compute PnL, close position, record trade
                pnl = (fill.price - pos.avg_price) * pos.quantity
                trade = Trade(
                    pnl=pnl,
                    adhered_to_plan=True,
                    entry_time=pos.entry_time,
                    exit_time=fill.time,
                    duration_bars=pos.bars_held,
                    time_in_drawdown_bars=pos.time_in_drawdown_bars,
                )
                self.trades.append(trade)
                self.account.daily_pnl += pnl
                # Add back sale proceeds
                self.account.cash += fill.price * pos.quantity
                del self.positions[symbol]

            # Update open position metrics with latest market prices
            for symbol, pos in list(self.positions.items()):
                m = market_by_symbol.get(symbol)
                if not m:
                    continue
                last = m["last"]
                pos.bars_held += 1
                pos.last_price = last
                unrealized = (last - pos.avg_price) * pos.quantity
                pos.peak_unrealized = max(pos.peak_unrealized, unrealized)
                dd = pos.peak_unrealized - unrealized
                if dd > 0:
                    pos.time_in_drawdown_bars += 1
                    pos.max_drawdown_unrealized = max(pos.max_drawdown_unrealized, dd)

            # Daily rollover handling: record and reset when the day changes
            day_tuple = datetime.fromtimestamp(t, tz=timezone.utc).date().timetuple()[:3]
            if last_day is None:
                last_day = day_tuple
            elif day_tuple != last_day:
                self.dailies.append(Daily(pnl=self.account.daily_pnl))
                self.account.daily_pnl = 0.0
                last_day = day_tuple

        # Close out final day's daily PnL record
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
            "avg_trade_duration_bars": m.avg_trade_duration_bars,
            "avg_time_in_drawdown_bars": m.avg_time_in_drawdown_bars,
        }
