# utils.py
from typing import List, Dict
import aiohttp


async def fetch_volume_data(interval: str) -> List[Dict[str, float]]:
    url = f"https://api.binance.com/api/v3/ticker?type=MINI"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            raw = await resp.json()

    volume_key = "quoteVolume" if interval == "24h" else "volume"

    result = []
    for item in raw:
        try:
            result.append({
                "symbol": item["symbol"],
                "volume": float(item[volume_key]),
                "interval": interval
            })
        except Exception:
            continue
    return result


def calculate_volume_increase(new_data: List[Dict],
                              old_data: Dict[str, float]) -> List[Dict]:
    result = []
    for entry in new_data:
        symbol = entry["symbol"]
        new_volume = entry["volume"]
        if symbol in old_data and old_data[symbol] > 0:
            change = ((new_volume - old_data[symbol]) / old_data[symbol]) * 100
            entry["change"] = change
            result.append(entry)
    return sorted(result, key=lambda x: x["change"], reverse=True)


def generate_markdown_table(title: str, data: List[Dict], min_pct: float,
                            max_pct: float) -> str:
    filtered = [x for x in data if min_pct <= x["change"] <= max_pct]
    if not filtered:
        return f"### {title}\nNo coins found.\n"

    lines = [
        f"### {title}\n| Symbol | Volume | Change (%) |",
        "|--------|--------|-------------|"
    ]
    for item in filtered:
        lines.append(
            f"| {item['symbol']} | {item['volume']:.2f} | {item['change']:.2f}% |"
        )
    return "\n".join(lines)
