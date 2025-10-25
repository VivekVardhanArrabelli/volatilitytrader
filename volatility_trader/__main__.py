from __future__ import annotations
import random
import time
from .types import Bar
from .backtest import StrategyBacktester


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
    # Multi-symbol demo
    symbols = {
        "XYZ": make_dummy_bars("XYZ"),
        "ABC": make_dummy_bars("ABC"),
        "DEF": make_dummy_bars("DEF"),
    }
    bt = StrategyBacktester(account_equity=100_000)
    result = bt.run(symbols)
    print({
        "trades": len(result.trades),
        "days": len(result.dailies),
        **bt.summarize(),
    })


if __name__ == "__main__":
    main()
