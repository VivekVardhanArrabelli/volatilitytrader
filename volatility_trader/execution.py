from __future__ import annotations
from typing import Dict, Optional, Tuple
from .types import Order, OrderType, Fill, Side
from .config import FILL_RULES


class ExecutionEngine:
    def __init__(self):
        self.open_orders: Dict[str, Order] = {}

    def place_order(self, order: Order) -> None:
        key = f"{order.symbol}:{id(order)}"
        self.open_orders[key] = order

    def cancel_oco_group(self, oco_group: str) -> None:
        self.open_orders = {k: o for k, o in self.open_orders.items() if o.oco_group != oco_group}

    def simulate_fill(self, order: Order, market: Dict[str, float]) -> Optional[Fill]:
        bid = market["bid"]
        ask = market["ask"]
        volume = market["volume"]
        spread = ask - bid
        t = int(market.get("time", 0))

        if order.order_type == OrderType.LIMIT:
            ref_price = order.price if order.price is not None else ask
            if spread > ref_price * 0.001:
                return None
            available = int(volume * FILL_RULES["volume_participation"])
            filled = min(order.quantity, available)
            if filled <= 0:
                return None
            fill_price = ref_price + spread * 0.3
            return Fill(order, filled, float(fill_price), t)

        if order.order_type == OrderType.MARKET:
            ref = ask if order.side == Side.BUY else bid
            fill_price = ref * (1 + FILL_RULES["slippage_bps"] / 10000)
            return Fill(order, order.quantity, float(fill_price), t)

        return None

    def process_oco(
        self,
        stop_order: Order,
        tp_order: Order,
        market: Dict[str, float],
    ) -> Tuple[Optional[Fill], Optional[Fill]]:
        last = market.get("last")
        if last is not None and stop_order.price is not None and last <= stop_order.price:
            stop_fill = self.simulate_fill(stop_order, market)
            if stop_fill:
                self.cancel_oco_group(stop_order.oco_group or "")
                return stop_fill, None
        if last is not None and tp_order.price is not None and last >= tp_order.price:
            tp_fill = self.simulate_fill(tp_order, market)
            if tp_fill:
                self.cancel_oco_group(tp_order.oco_group or "")
                return None, tp_fill
        return None, None
