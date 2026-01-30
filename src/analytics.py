from __future__ import annotations

from typing import List, Dict, Any
import numpy as np
import pandas as pd

PRICE_BINS = [
    (0.0, 0.05, "$0 - $0.05"),
    (0.05, 0.5, "$0.05 - $0.5"),
    (0.5, 5.0, "$0.5 - $5"),
    (5.0, 50.0, "$5 - $50"),
    (50.0, float("inf"), ">$50"),
]


def add_derived_columns(df):
    out = df.copy()

    column_map = {
        "pct_1h": ["pct_1h", "Change_1h", "price_change_percentage_1h_in_currency"],
        "pct_24h": ["pct_24h", "Change_24h", "price_change_percentage_24h"],
        "pct_7d": ["pct_7d", "Change_7d", "price_change_percentage_7d_in_currency"],
    }

    for standard_col, candidates in column_map.items():
        found = None
        for c in candidates:
            if c in out.columns:
                found = c
                break

        if found:
            out[standard_col] = pd.to_numeric(out[found], errors="coerce")
        else:
            out[standard_col] = 0.0

    out["avg_downfall"] = (
        out["pct_1h"].abs() + out["pct_24h"].abs() + out["pct_7d"].abs()
    ) / 3

    return out

def filter_by_price_ranges(df: pd.DataFrame, selected_ranges: List[str]) -> pd.DataFrame:
    if not selected_ranges:
        return df.iloc[0:0].copy()
    return df[df["price_range"].isin(selected_ranges)].copy()


def kpi_least_avg_downfall(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty:
        return {"coin_name": None, "coin_symbol": None, "price": None, "avg_downfall_pct": None, "count": 0}
    best = df.sort_values("avg_downfall_pct", ascending=True).iloc[0]
    return {
        "coin_name": best["coin_name"],
        "coin_symbol": best["coin_symbol"],
        "price": float(best["price"]),
        "avg_downfall_pct": float(best["avg_downfall_pct"]),
        "count": int(df.shape[0]),
    }


def top10_for_range_0_5_prev_prices(df: pd.DataFrame) -> pd.DataFrame:
    d = df[(df["price"] >= 0) & (df["price"] <= 5)].copy()
    d = d.sort_values("prev_price_1h", ascending=False).head(10)
    return d[["coin_name", "coin_symbol", "price", "prev_price_24h", "prev_price_7d", "prev_price_1h", "pct_1h", "pct_24h", "pct_7d"]]


def top10_price_increase(df: pd.DataFrame, price_category: str) -> pd.DataFrame:
    d = df.copy()
    if price_category in [">= $10", "< $10"]:
        d = d[d["price_category_10"] == price_category].copy()
    d["price_change_1h"] = d["price"] - d["prev_price_1h"]
    d = d.sort_values("price_change_1h", ascending=False).head(10)
    return d[["coin_name", "coin_symbol", "prev_price_1h", "price", "price_change_1h"]]


def filter_name_prefix(df: pd.DataFrame) -> pd.DataFrame:
    prefixes = tuple(list("AEIOUaeiou") + ["B", "C", "D", "b", "c", "d"])
    return df[df["coin_name"].astype(str).str.startswith(prefixes)].copy()


def top10_by_volume(df: pd.DataFrame) -> pd.DataFrame:
    d = df.sort_values("volume_24h", ascending=False).head(10).copy()
    return d[["coin_name", "coin_symbol", "volume_24h", "price"]]


def compare_two_coins(df: pd.DataFrame, name1: str, name2: str) -> Dict[str, Any]:
    d = df.copy()
    d["coin_name_norm"] = d["coin_name"].astype(str).str.lower().str.strip()
    r1 = d[d["coin_name_norm"] == name1.lower().strip()]
    r2 = d[d["coin_name_norm"] == name2.lower().strip()]
    if r1.empty or r2.empty:
        return {"ok": False, "error": "One or both coin names not found in the current dataset."}

    a = r1.iloc[0]
    b = r2.iloc[0]

    def pack(row):
        return {
            "Coin Name": row["coin_name"],
            "Symbol": row["coin_symbol"],
            "Price": float(row["price"]),
            "Volume(24h)": float(row["volume_24h"]),
            "Market Cap": float(row["market_cap"]),
            "Circulating Supply": float(row["circulating_supply"]),
        }

    diff = {
        "Volume(24h) Diff": float(a["volume_24h"] - b["volume_24h"]),
        "Circulating Supply Diff": float(a["circulating_supply"] - b["circulating_supply"]),
        "Market Cap Diff": float(a["market_cap"] - b["market_cap"]),
    }

    return {"ok": True, "coin1": pack(a), "coin2": pack(b), "diff": diff}


def pie_top5_volume_with_others(df: pd.DataFrame, price_cat: str) -> pd.DataFrame:
    d = df.copy()
    if price_cat in ["$0 - $50", ">$50"]:
        d = d[d["price_category_0_50"] == price_cat].copy()

    d = d.sort_values("volume_24h", ascending=False)
    top5 = d.head(5).copy()
    others = d.iloc[5:].copy()

    rows = [{"coin_name": r["coin_name"], "volume_24h": float(r["volume_24h"])} for _, r in top5.iterrows()]
    if not others.empty:
        rows.append({"coin_name": "Others", "volume_24h": float(others["volume_24h"].sum())})

    return pd.DataFrame(rows)

def market_overview(df_latest: pd.DataFrame) -> dict:
    df = df_latest.copy()
    df["is_green_24h"] = df["pct_24h"].fillna(0) > 0
    df["is_red_24h"] = df["pct_24h"].fillna(0) < 0

    return {
        "coins_tracked": int(len(df)),
        "green_24h": int(df["is_green_24h"].sum()),
        "red_24h": int(df["is_red_24h"].sum()),
        "total_mcap": float(df["market_cap"].fillna(0).sum()),
        "total_volume_24h": float(df["volume_24h"].fillna(0).sum()),
        "avg_change_24h": float(df["pct_24h"].fillna(0).mean()),
    }


def top_movers(
    df_latest: pd.DataFrame, metric: str, n: int = 10, ascending: bool = False
) -> pd.DataFrame:
    df = df_latest.copy()
    df = df.dropna(subset=[metric])
    df = df.sort_values(metric, ascending=ascending).head(n)
    return df


def top_volume(df_latest: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    df = df_latest.copy()
    df = df.dropna(subset=["volume_24h"])
    df = df.sort_values("volume_24h", ascending=False).head(n)
    return df


def coin_history(df_hist: pd.DataFrame, symbol: str) -> pd.DataFrame:
    df = df_hist[df_hist["coin_symbol"].str.upper() == symbol.upper()].copy()
    df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
    df = df.dropna(subset=["ts"]).sort_values("ts")
    return df
