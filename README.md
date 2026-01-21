# VolatilityTrader

A systematic, rule-driven intraday strategy designed to capture volatility while enforcing strict risk management and execution discipline. This document formalizes the trading plan, execution “physics,” and measurement framework.

> Educational and documentation purposes only. Not financial advice.

---

## Core Principles

- Quality over quantity: Only take setups that satisfy all criteria
- Risk 1% per trade: Maintain consistent position sizing discipline
- Minimum 1:3 risk-reward: Let winners run, cut losers quickly
- Max 3 concurrent positions: Avoid over-concentration
- Daily loss stop at -3%: Halt trading and protect capital

---

## Signal Filters (all must pass)

### BREAKOUT
- RVOL > 1.8 (relative volume vs 20-day average)
- ATR% > 4.0 (daily range as % of price)
- Price > Upper Bollinger Band
- Bollinger Band width at 20-day low (consolidation)
- Today’s volume > previous day

### REVERSAL
- RVOL > 1.8
- ATR% > 4.0
- RSI < 35 (oversold)
- Price ≤ Lower Bollinger Band
- 50 EMA > 200 EMA (uptrend filter)

---

## Trading Hours & Cadence

- Scans at: 9:45 AM, 11:00 AM, 1:00 PM, 2:30 PM ET
- No new entries after 3:00 PM ET
- Close all positions by 3:45 PM ET (no overnight holds)

---

## Execution Physics (Strategy Engine)

These code snippets are reference implementations/pseudocode to clarify intent. Integrate and adapt within your actual engine.

### Position Sizing
```python
def calculate_shares(account_equity: float, entry_price: float, stop_price: float, risk_fraction: float = 0.01) -> int:
    """Risk 1% (default) of equity per trade, sized to stop.
    Returns whole-share quantity.
    """
    price_risk = abs(entry_price - stop_price)
    if price_risk <= 0:
        return 0
    risk_amount = account_equity * risk_fraction
    return int(risk_amount / price_risk)
```

### Stop Loss Rules
```python
def calculate_stop_loss(signal_type: str, entry_price: float, atr: float) -> float:
    if signal_type == "BREAKOUT":
        return entry_price - (2.0 * atr)
    elif signal_type == "REVERSAL":
        return entry_price - (1.5 * atr)
    else:
        raise ValueError("Unknown signal_type")
```

### Take Profit Rules
```python
def calculate_take_profit(entry_price: float, stop_price: float, signal_type: str) -> float:
    risk = abs(entry_price - stop_price)
    if risk <= 0:
        return entry_price
    if signal_type == "BREAKOUT":
        return entry_price + (3.0 * risk)
    elif signal_type == "REVERSAL":
        return entry_price + (2.5 * risk)
    else:
        raise ValueError("Unknown signal_type")
```

### Order Execution Physics
```python
# Fill assumptions (conservative)
FILL_RULES = {
    "limit_offset_bps": 15,      # Place limits 15 bps through expected price
    "slippage_bps": 5,           # Assume 5 bps slippage on market orders
    "min_spread_bps": 3,         # Avoid symbols with spread > 3 bps
    "volume_participation": 0.05 # Do not take more than 5% of current volume
}

# Position and risk limits
RISK_RULES = {
    "max_gross_exposure": 0.30,  # Never use more than 30% of capital
    "per_symbol_max": 0.15,      # No more than 15% in one symbol
    "max_positions": 3,
    "daily_loss_halt": -0.03,    # Stop trading at -3% daily
}
```

### Backtesting Assumptions (Fills)
```python
def simulate_fill(order_type: str, symbol: str, quantity: int, price: float, data: dict):
    """Conservative fill modeling for backtests.
    data expects keys: bid, ask, volume
    """
    spread = data["ask"] - data["bid"]

    if order_type == "limit":
        if spread > price * 0.001:  # > 0.1% spread
            return None  # no fill due to wide spreads
        # Partial fills based on conservative participation
        available_volume = data["volume"] * FILL_RULES["volume_participation"]
        filled_qty = min(quantity, int(available_volume))
        if filled_qty <= 0:
            return None
        fill_price = price + (spread * 0.3)  # slippage component
        return filled_qty, fill_price

    elif order_type == "market":
        # Market orders get worse fills
        side_ask = data["ask"] if quantity > 0 else data["bid"]
        fill_price = side_ask * (1 + FILL_RULES["slippage_bps"] / 10000)
        return quantity, fill_price

    else:
        raise ValueError("Unknown order_type")
```

### Risk Circuit Breakers
```python
from datetime import timedelta
from typing import Dict

# account.daily_pnl, account.equity, account.trade_history (symbol -> last_trade_time)

def check_circuit_breakers(account, open_positions: Dict[str, object], current_time) -> str:
    # Daily loss limit
    if account.equity > 0 and (account.daily_pnl / account.equity) < RISK_RULES["daily_loss_halt"]:
        return "HALT: Daily loss limit"

    # Over-concentration
    if len(open_positions) >= RISK_RULES["max_positions"]:
        return "HALT: Max positions"

    # Symbol cooldown (avoid re-entering same symbol too soon)
    for symbol, last_trade_time in getattr(account, "trade_history", {}).items():
        if (current_time - last_trade_time) < timedelta(hours=4):
            return f"HALT: {symbol} cooldown"

    return "OK"
```

---

## Performance Metrics to Track

Target thresholds are illustrative and should be validated empirically.

```python
REQUIRED_METRICS = [
    "win_rate",                  # Target: > 45%
    "profit_factor",             # Target: > 1.5
    "avg_win_loss_ratio",        # Target: > 2.5
    "max_drawdown",              # Keep under 8%
    "sharpe_ratio",              # Target: > 2.0
    "orders_per_day",            # Target: 2–4
    "plan_adherence",            # % of trades following rules
    "slippage_impact_bps",       # Keep under 10 bps
]
```

---

## Build Roadmap (Priority)

1. Scanner with strict filters
2. Risk-based position sizing
3. OCO bracket orders (stop loss + take profit)
4. Circuit breakers and cooldowns
5. Performance tracking

---

## Backtesting with Polygon data

You can run the backtest against Polygon historical aggregates by setting your API key
locally and passing the `--polygon` flag. The tool reads `POLYGON_API_KEY` from your
environment (no key is stored in the repo).

```bash
export POLYGON_API_KEY="your_key_here"
python -m volatility_trader --polygon --symbols AAPL,MSFT --start 2023-01-01 --end 2023-06-30 --timespan minute
```

For offline experimentation, omit `--polygon` and the script will generate dummy data.

---

## Contributing

- Propose changes via pull request with a clear rationale, test plan, and impact
- Keep code clear and explicit; prefer readability over cleverness
- Document any changes to risk rules, signal filters, or execution assumptions

---

## License

License not yet specified. If you plan to use or distribute this, add a `LICENSE` file and update this section accordingly.
