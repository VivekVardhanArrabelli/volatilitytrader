from __future__ import annotations

import argparse
import os
import random
import time

from .types import Bar
from .backtest import StrategyBacktester
from .polygon_data import fetch_polygon_bars


def make_dummy_bars(symbol: str, days: int = 220) -> list[Bar]:
    bars: list[Bar] = []
    price = 100.0
    for i in range(days):
        change = random.uniform(-1.0, 1.0)
        open_ = price
        high = open_ + abs(change) * 1.5
        low = open_ - abs(change) * 1.5
        close = open_ + change
        volume = 1_000_000 + random.randint(-50_000, 50_000)
        price = close
        bars.append(
            Bar(
                symbol=symbol,
                time=int(time.time()) + i * 86400,
                open=open_,
                high=high,
                low=low,
                close=close,
                volume=volume,
            )
        )
    return bars


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the VolatilityTrader backtest.")
    parser.add_argument("--polygon", action="store_true", help="Fetch historical bars from Polygon.")
    parser.add_argument("--symbols", default="XYZ,ABC,DEF", help="Comma-separated list of symbols.")
    parser.add_argument("--start", default="2023-01-01", help="Start date for Polygon backtest (YYYY-MM-DD).")
    parser.add_argument("--end", default="2023-06-30", help="End date for Polygon backtest (YYYY-MM-DD).")
    parser.add_argument("--timespan", default="minute", help="Polygon timespan (minute, hour, day).")
    parser.add_argument("--multiplier", type=int, default=1, help="Polygon timespan multiplier.")
    parser.add_argument("--equity", type=float, default=100_000, help="Starting account equity.")
    parser.add_argument(
        "--respect-schedule",
        action="store_true",
        default=False,
        help="Enforce scan times and close-out schedule (default off for dummy data).",
    )
    args = parser.parse_args()

    symbol_list = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if args.polygon:
        api_key = os.environ.get("POLYGON_API_KEY", "")
        if not api_key:
            raise SystemExit("POLYGON_API_KEY is not set. Add it to your environment before running.")
        symbols = fetch_polygon_bars(
            symbol_list,
            start=args.start,
            end=args.end,
            api_key=api_key,
            multiplier=args.multiplier,
            timespan=args.timespan,
        )
        bt = StrategyBacktester(account_equity=args.equity, respect_schedule=True)
    else:
        symbols = {symbol: make_dummy_bars(symbol) for symbol in symbol_list}
        bt = StrategyBacktester(account_equity=args.equity, respect_schedule=args.respect_schedule)

    result = bt.run(symbols)
    print({
        "trades": len(result.trades),
        "days": len(result.dailies),
        **bt.summarize(),
    })


if __name__ == "__main__":
    main()
