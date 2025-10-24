# volatilitytrader

Build Rules
Core Principles
Quality over quantity - Only trade setups that meet all criteria

1% risk per trade - Never deviate from position sizing

1:3 risk-reward minimum - Let winners run, cut losers fast

Max 3 positions - Avoid overconcentration

Stop at -3% daily loss - Live to trade tomorrow

Signal Filters (MUST PASS ALL)
text
BREAKOUT:
  - RVOL > 1.8 (relative volume vs 20-day average)
  - ATR % > 4.0 (daily range as % of price)  
  - Price > Upper Bollinger Band
  - BB Width at 20-day low (consolidation)
  - Volume > previous day

REVERSAL:
  - RVOL > 1.8
  - ATR % > 4.0
  - RSI < 35 (oversold)
  - Price <= Lower Bollinger Band  
  - 50EMA > 200EMA (uptrend filter)
Trading Hours & Cadence
Scan: 9:45AM, 11:00AM, 1:00PM, 2:30PM ET

No new entries after 3:00PM ET

Close all positions by 3:45PM ET (no overnight holds)

Executor Physics Engine
Position Sizing
python
def calculate_shares(account_size, entry_price, stop_price):
    risk_amount = account_size * 0.01  # 1% risk
    price_risk = abs(entry_price - stop_price)
    return int(risk_amount / price_risk)
Stop Loss Rules
python
def calculate_stop_loss(signal_type, entry_price, atr):
    if signal_type == "BREAKOUT":
        return entry_price - (2.0 * atr)
    elif signal_type == "REVERSAL":
        return entry_price - (1.5 * atr)
Take Profit Rules
python
def calculate_take_profit(entry_price, stop_price, signal_type):
    risk = abs(entry_price - stop_price)
    if signal_type == "BREAKOUT":
        return entry_price + (3.0 * risk)
    else:  # REVERSAL
        return entry_price + (2.5 * risk)
Order Execution Physics
python
# Fill assumptions (conservative)
FILL_RULES = {
    'limit_offset_bps': 15,      # Place limits 15bps through expected price
    'slippage_bps': 5,           # Assume 5bps slippage on market orders
    'min_spread_bps': 3,         # Avoid symbols with spread > 3bps
    'volume_participation': 0.05 # Don't take more than 5% of current volume
}

# Position limits
RISK_RULES = {
    'max_gross_exposure': 0.30,  # Never use more than 30% of capital
    'per_symbol_max': 0.15,      # No more than 15% in one symbol
    'max_positions': 3,
    'daily_loss_halt': -0.03,    # Stop trading at -3% daily
}
Backtesting Assumptions
python
# Conservative fill modeling
def simulate_fill(order_type, symbol, quantity, price, data):
    if order_type == 'limit':
        # Get bid/ask spread
        spread = data['ask'] - data['bid']
        if spread > price * 0.001:  # >0.1% spread
            return None  # No fill due to wide spreads
        
        # Partial fills based on volume
        available_volume = data['volume'] * 0.05  # 5% participation
        filled_qty = min(quantity, available_volume)
        fill_price = price + (spread * 0.3)  # Slippage
        return filled_qty, fill_price
    
    elif order_type == 'market':
        # Market orders get worse fills
        fill_price = data['ask'] if quantity > 0 else data['bid']
        fill_price *= 1.0005  # 5bps slippage
        return quantity, fill_price
Risk Circuit Breakers
python
def check_circuit_breakers(account, positions):
    # Daily loss limit
    if account.daily_pnl / account.equity < -0.03:
        return "HALT: Daily loss limit"
    
    # Overconcentration
    if len(positions) >= 3:
        return "HALT: Max positions"
    
    # Symbol cooldown (avoid re-entering same symbol)
    for symbol, last_trade in account.trade_history:
        if (current_time - last_trade) < timedelta(hours=4):
            return f"HALT: {symbol} cooldown"
    
    return "OK"
Performance Metrics to Track
python
REQUIRED_METRICS = [
    'win_rate',                   # Target: >45%
    'profit_factor',              # Target: >1.5  
    'avg_win_loss_ratio',         # Target: >2.5
    'max_drawdown',               # Keep under 8%
    'sharpe_ratio',               # Target: >2.0
    'orders_per_day',             # Target: 2-4
    'plan_adherence',             # % of trades following rules
    'slippage_impact_bps'         # Keep under 10bps
]
Build priority:

Scanner with strict filters

Risk-based position sizing

OCO bracket orders (stop loss + take profit)

Circuit breakers and cooldowns

Performance tracking

The physics are designed to keep you safe while capturing volatility. Focus on execution quality, not frequency.
