from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List
from .types import Bar


@dataclass
class InMemoryData:
    symbol_to_bars: Dict[str, List[Bar]]

    def get_bars(self, symbol: str) -> List[Bar]:
        return self.symbol_to_bars.get(symbol, [])
