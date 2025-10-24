from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Dict


class Side(Enum):
    BUY = auto()
    SELL = auto()


class OrderType(Enum):
    MARKET = auto()
    LIMIT = auto()


@dataclass
class Bar:
    symbol: str
    time: int  # epoch seconds
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Order:
    symbol: str
    side: Side
    quantity: int
    order_type: OrderType
    price: Optional[float] = None
    oco_group: Optional[str] = None


@dataclass
class Fill:
    order: Order
    filled_qty: int
    price: float
    time: int


@dataclass
class Position:
    symbol: str
    quantity: int
    avg_price: float
    stop_price: Optional[float] = None
    take_profit: Optional[float] = None


@dataclass
class Account:
    equity: float
    cash: float
    daily_pnl: float = 0.0
    trade_history: Dict[str, int] = None


@dataclass
class SignalContext:
    rvol: float
    atr_percent: float
    rsi: float
    price: float
    bb_upper: float
    bb_lower: float
    bb_width: float
    ema50: float
    ema200: float


@dataclass
class Decision:
    should_enter: bool
    reason: str
    signal_type: Optional[str] = None
    entry_price: Optional[float] = None
