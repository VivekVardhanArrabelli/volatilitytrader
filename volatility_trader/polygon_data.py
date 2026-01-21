from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional
from urllib.parse import urlencode
from urllib.request import urlopen

from .types import Bar


@dataclass(frozen=True)
class PolygonRequest:
    symbol: str
    start: str
    end: str
    multiplier: int = 1
    timespan: str = "minute"
    adjusted: bool = True
    limit: int = 50000


def fetch_polygon_bars(
    symbols: Iterable[str],
    start: str,
    end: str,
    api_key: str,
    multiplier: int = 1,
    timespan: str = "minute",
    adjusted: bool = True,
) -> Dict[str, List[Bar]]:
    if not api_key:
        raise ValueError("Polygon API key is required.")
    results: Dict[str, List[Bar]] = {}
    for symbol in symbols:
        request = PolygonRequest(
            symbol=symbol,
            start=start,
            end=end,
            multiplier=multiplier,
            timespan=timespan,
            adjusted=adjusted,
        )
        results[symbol] = _fetch_polygon_bars_for_symbol(request, api_key)
    return results


def _fetch_polygon_bars_for_symbol(request: PolygonRequest, api_key: str) -> List[Bar]:
    base_url = (
        f"https://api.polygon.io/v2/aggs/ticker/{request.symbol}/range/"
        f"{request.multiplier}/{request.timespan}/{request.start}/{request.end}"
    )
    params = {
        "adjusted": "true" if request.adjusted else "false",
        "sort": "asc",
        "limit": str(request.limit),
        "apiKey": api_key,
    }
    url = f"{base_url}?{urlencode(params)}"
    bars: List[Bar] = []
    while url:
        payload = _load_json(url)
        for row in payload.get("results", []):
            timestamp_ms = int(row.get("t", 0))
            bars.append(
                Bar(
                    symbol=request.symbol,
                    time=timestamp_ms // 1000,
                    open=float(row.get("o", 0)),
                    high=float(row.get("h", 0)),
                    low=float(row.get("l", 0)),
                    close=float(row.get("c", 0)),
                    volume=float(row.get("v", 0)),
                )
            )
        url = _next_url(payload.get("next_url"), api_key)
    return bars


def _load_json(url: str) -> dict:
    with urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


def _next_url(next_url: Optional[str], api_key: str) -> Optional[str]:
    if not next_url:
        return None
    if "apiKey=" in next_url:
        return next_url
    separator = "&" if "?" in next_url else "?"
    return f"{next_url}{separator}apiKey={api_key}"
