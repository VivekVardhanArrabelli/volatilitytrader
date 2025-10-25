from __future__ import annotations
from typing import Dict, Optional, Tuple, List
from .types import Order, OrderType, Fill, Side
from .config import FILL_RULES


class ExecutionEngine:
    def __init__(self):
        self.open_orders: Dict[str, Order] = {}
        # Track OCO order groups for continuous monitoring
        self.open_oco_groups: Dict[str, Tuple[Order, Order]] = {}

    def place_order(self, order: Order) -> None:
        key = f"{order.symbol}:{id(order)}"
        self.open_orders[key] = order

    def cancel_oco_group(self, oco_group: str) -> None:
        self.open_orders = {k: o for k, o in self.open_orders.items() if o.oco_group != oco_group}
        if oco_group in self.open_oco_groups:
            del self.open_oco_groups[oco_group]

    def register_oco(self, stop_order: Order, tp_order: Order) -> None:
        if not stop_order.oco_group or not tp_order.oco_group:
            return
        self.open_oco_groups[stop_order.oco_group] = (stop_order, tp_order)
        # Also keep individual references if needed elsewhere
        self.place_order(stop_order)
        self.place_order(tp_order)

    def simulate_fill(self, order: Order, market: Dict[str, float]) -> Optional[Fill]:
        bid = market["bid"]
        ask = market["ask"]
        volume = market["volume"]
        spread = ask - bid
        t = int(market.get("time", 0))

        if order.order_type == OrderType.LIMIT:
            ref_price = order.price if order.price is not None else (ask if order.side == Side.BUY else bid)
            available = int(volume * FILL_RULES["volume_participation"])
            filled = min(order.quantity, available)
            if filled <= 0:
                return None
            slip = (FILL_RULES["slippage_bps"] / 10000) * ref_price
            if order.side == Side.BUY:
                # Buy limit: price should not exceed ask
                trade_price = min(ref_price, ask) + slip
            else:
                # Sell limit: price should not be below bid
                trade_price = max(ref_price, bid) - slip
            return Fill(order, filled, float(trade_price), t)

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

    def check_open_orders(self, market_by_symbol: Dict[str, Dict[str, float]]) -> List[Fill]:
        fills: List[Fill] = []
        # Copy keys to avoid mutation during iteration
        for group_id in list(self.open_oco_groups.keys()):
            stop_order, tp_order = self.open_oco_groups[group_id]
            symbol = stop_order.symbol
            market = market_by_symbol.get(symbol)
            if not market:
                continue
            last = market.get("last")
            # Prioritize stop before TP
            if last is not None and stop_order.price is not None and last <= stop_order.price:
                stop_fill = self.simulate_fill(stop_order, market)
                if stop_fill:
                    fills.append(stop_fill)
                    self.cancel_oco_group(group_id)
                    continue
            if last is not None and tp_order.price is not None and last >= tp_order.price:
                tp_fill = self.simulate_fill(tp_order, market)
                if tp_fill:
                    fills.append(tp_fill)
                    self.cancel_oco_group(group_id)
                    continue
        return fills
