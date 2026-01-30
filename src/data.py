from __future__ import annotations

import requests
import pandas as pd
from dataclasses import dataclass
import time
import requests

USER_AGENT = "Mozilla/5.0 (AlphaTerminal; +https://streamlit.io)"


@dataclass
class FetchConfig:
    vs_currency: str = "usd"
    per_page: int = 200
    page: int = 1
    timeout: int = 30


def fetch_coingecko_markets(cfg):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": cfg.vs_currency,
        "order": "market_cap_desc",
        "per_page": cfg.per_page,
        "page": cfg.page,
        "sparkline": "false",
        "price_change_percentage": "1h,24h,7d",
    }

    headers = {"User-Agent": "AlphaTerminal/1.0"}
    r = requests.get(url, params=params, headers=headers, timeout=20)
    r.raise_for_status()

    data = r.json()
    df = pd.DataFrame(data)

    return pd.DataFrame(
        {
            "coin_name": df["name"],
            "coin_symbol": df["symbol"].str.upper(),
            "price": df["current_price"],
            "pct_1h": df["price_change_percentage_1h_in_currency"],
            "pct_24h": df["price_change_percentage_24h_in_currency"],
            "pct_7d": df["price_change_percentage_7d_in_currency"],
            "volume_24h": df["total_volume"],
            "market_cap": df["market_cap"],
            "circulating_supply": df["circulating_supply"],
            "last_updated": df["last_updated"],
        }
    )

