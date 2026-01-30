from __future__ import annotations

import re
import io
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

from src.data import FetchConfig, fetch_coingecko_markets
from src.analytics import market_overview, top_movers, top_volume

st.set_page_config(page_title="Alpha Terminal", page_icon="⚡", layout="wide")

COINBASE_CSS = """
<style>
:root{
  --bg:#050A14;
  --panel:#0B1220;
  --panel2:#0F1C33;
  --stroke:#1C2B45;
  --text:#EAF2FF;
  --muted:#9BB3D3;
  --blue:#2F81F7;
  --green:#00E396;
  --red:#FF4560;
}
html, body, [class*="css"] {
  background:
    radial-gradient(1200px 500px at 15% 10%, rgba(47,129,247,.12), transparent 55%),
    radial-gradient(900px 400px at 85% 15%, rgba(0,227,150,.08), transparent 55%),
    linear-gradient(180deg, #040812, var(--bg)) !important;
  color: var(--text) !important;
}
header, footer { visibility: hidden; }
.block-container{ max-width: 1400px; padding-top: 1rem; }
[data-testid="stSidebar"]{
  background: linear-gradient(180deg, rgba(11,18,32,.98), rgba(5,10,20,.98)) !important;
  border-right: 1px solid var(--stroke);
}
.kpi-wrap{
  display:grid;
  grid-template-columns: repeat(5, minmax(0,1fr));
  gap: 14px;
  margin: 14px 0 8px 0;
}
.kpi{
  background: linear-gradient(180deg, rgba(15,28,51,.85), rgba(11,18,32,.9));
  border: 1px solid var(--stroke);
  border-radius: 18px;
  padding: 16px 18px;
  box-shadow: 0 18px 50px rgba(0,0,0,.55);
  transition: all .25s ease;
}
.kpi:hover{
  transform: translateY(-3px);
  box-shadow: 0 0 28px rgba(47,129,247,.35);
}
.kpi .label{
  font-size: 12px;
  color: var(--muted);
  font-weight: 700;
  letter-spacing: .4px;
}
.kpi .value{
  font-size: 22px;
  font-weight: 900;
  margin-top: 6px;
}
.sticky-header{
  position: sticky;
  top: 0;
  z-index: 999;
  background: linear-gradient(180deg, rgba(5,10,20,.96), rgba(5,10,20,.88));
  backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--stroke);
  padding-bottom: 10px;
}
[data-testid="stDataFrame"]{
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0,0,0,.6);
}
@keyframes pulseGreen {
  0% { box-shadow: 0 0 0 rgba(0,227,150,0); }
  50% { box-shadow: 0 0 18px rgba(0,227,150,.6); }
  100% { box-shadow: 0 0 0 rgba(0,227,150,0); }
}
@keyframes pulseRed {
  0% { box-shadow: 0 0 0 rgba(255,69,96,0); }
  50% { box-shadow: 0 0 18px rgba(255,69,96,.6); }
  100% { box-shadow: 0 0 0 rgba(255,69,96,0); }
}
.kpi.green { animation: pulseGreen 2s infinite; }
.kpi.red { animation: pulseRed 2s infinite; }
.kpi.green .value{
  color: var(--green);
}

.kpi.red .value{
  color: var(--red);
}
.kpi.green .value{
  color: var(--green);
}

.kpi.red .value{
  color: var(--red);
}

.kpi.green .label{
  color: var(--green);
}

.kpi.red .label{
  color: var(--red);
}
</style>
"""
st.markdown(COINBASE_CSS, unsafe_allow_html=True)


def fmt_usd(x):
    if pd.isna(x):
        return "—"
    return f"${x:,.6f}" if x < 1 else f"${x:,.2f}"


def valid_name(s):
    return bool(re.fullmatch(r"[A-Za-z]{3,10}", (s or "").strip()))


@st.cache_data(ttl=120)
def load_live(per_page):
    cfg = FetchConfig(per_page=per_page)
    return fetch_coingecko_markets(cfg)


def ensure_prev_prices(df):
    df = df.copy()
    for c in ["prev_price_1h", "prev_price_24h", "prev_price_7d"]:
        if c not in df.columns:
            df[c] = np.nan
    if {"pct_1h", "pct_24h", "pct_7d"}.issubset(df.columns):
        df["prev_price_1h"] = df["price"] / (1 + df["pct_1h"] / 100)
        df["prev_price_24h"] = df["price"] / (1 - df["pct_24h"] / 100)
        df["prev_price_7d"] = df["price"] / (1 + df["pct_7d"] / 100)
    return df


def load_portfolio(file):
    df = pd.read_csv(file)
    df.columns = [c.lower().strip() for c in df.columns]

    def find(keys):
        for k in keys:
            for c in df.columns:
                if k in c:
                    return c
        return None

    price_col = find(["price", "cost", "rate", "avg", "value"])
    qty_col = find(["qty", "quantity", "amount", "units", "balance"])
    name_col = find(["name", "coin", "asset"])
    symbol_col = find(["symbol", "ticker"])

    if price_col is None:
        nums = df.select_dtypes(include="number").columns
        price_col = nums[0] if len(nums) else None
        if price_col is None:
            st.stop()

    if qty_col is None:
        df["quantity"] = 1
        qty_col = "quantity"

    df["price"] = pd.to_numeric(df[price_col], errors="coerce")
    df["quantity"] = pd.to_numeric(df[qty_col], errors="coerce").fillna(1)

    df["coin_name"] = df[name_col] if name_col else df.get(symbol_col, "—")
    df["coin_symbol"] = (
        df[symbol_col].astype(str).str.upper()
        if symbol_col
        else df["coin_name"].astype(str).str[:5].str.upper()
    )

    df["portfolio_value"] = df["price"] * df["quantity"]
    df = ensure_prev_prices(df)

    return df


def merge_live_prices(df):
    live = fetch_coingecko_markets(FetchConfig(per_page=250))
    live = live[["coin_symbol", "price"]].rename(columns={"price": "live_price"})
    return df.merge(live, on="coin_symbol", how="left")


def add_pnl(df):
    df = df.copy()
    if "live_price" not in df.columns:
        return df
    df["current_value"] = df["live_price"] * df["quantity"]
    df["cost_value"] = df["price"] * df["quantity"]
    df["pnl_abs"] = df["current_value"] - df["cost_value"]
    df["pnl_pct"] = (df["pnl_abs"] / df["cost_value"]) * 100
    return df


with st.sidebar:
    uploaded = st.file_uploader("Import portfolio CSV", type=["csv"])
    per_page = st.slider("Coins to fetch", 50, 250, 200, 10)
    mover_metric = st.selectbox("Mover metric", ["pct_1h", "pct_24h", "pct_7d"])
    top_n = st.slider("Top N", 5, 50, 10, 5)

portfolio_mode = uploaded is not None

if portfolio_mode:
    df = add_pnl(merge_live_prices(load_portfolio(uploaded)))
    kpis = {}
else:
    df = ensure_prev_prices(load_live(per_page))
    kpis = market_overview(df)

st.markdown("<div class='sticky-header'>", unsafe_allow_html=True)
st.markdown("## ⚡ Alpha Terminal")

st.markdown(
    f"""
<div class="kpi-wrap">
<div class="kpi"><div class="label">Coins</div><div class="value">{len(df)}</div></div>
<div class="kpi"><div class="label">Green</div><div class="value">{kpis.get("green_24h", "—")}</div></div>
<div class="kpi"><div class="label">Red</div><div class="value">{kpis.get("red_24h", "—")}</div></div>
<div class="kpi"><div class="label">Market Cap</div><div class="value">{fmt_usd(kpis.get("total_mcap", np.nan))}</div></div>
<div class="kpi"><div class="label">Volume</div><div class="value">{fmt_usd(kpis.get("total_volume_24h", np.nan))}</div></div>
</div>
""",
    unsafe_allow_html=True,
)
st.markdown("</div>", unsafe_allow_html=True)

tabs = st.tabs(
    [
        "Alpha Dashboard",
        "Budget KPIs",
        "$0–$5 Top",
        "Top Increase",
        "Prefix Filter",
        "Compare",
        "Liquidity Pie",
    ]
)

with tabs[0]:
    if portfolio_mode:
        st.dataframe(
            df.sort_values("current_value", ascending=False), use_container_width=True
        )
    else:
        st.dataframe(top_movers(df, mover_metric, top_n, False))
        st.dataframe(top_movers(df, mover_metric, top_n, True))
        st.dataframe(top_volume(df, top_n))

with tabs[1]:
    if portfolio_mode:
        total_cost = df["cost_value"].sum()
        total_now = df["current_value"].sum()
        pnl = df["pnl_abs"].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Invested", fmt_usd(total_cost))
        c2.metric("Current Value", fmt_usd(total_now))
        c3.metric("PnL", fmt_usd(pnl), f"{(pnl / total_cost * 100):.2f}%")

with tabs[2]:
    d = df[df["price"] <= 5].sort_values("price", ascending=False).head(10)
    st.plotly_chart(
        px.bar(
            d,
            x="coin_name",
            y=["prev_price_7d", "prev_price_24h", "price"],
            barmode="group",
        ),
        use_container_width=True,
    )

with tabs[3]:
    if not portfolio_mode:
        st.dataframe(df.sort_values("pct_1h", ascending=False).head(10))

with tabs[4]:
    st.dataframe(df[df["coin_name"].str.match(r"^[AEIOUBCDaeioubcd]")].head(10))

with tabs[5]:
    c1, c2 = st.columns(2)
    n1 = c1.text_input("Coin 1", "Bitcoin")
    n2 = c2.text_input("Coin 2", "Ethereum")
    if valid_name(n1) and valid_name(n2):
        a = df[df["coin_name"].str.lower() == n1.lower()]
        b = df[df["coin_name"].str.lower() == n2.lower()]
        if not a.empty and not b.empty:
            st.dataframe(pd.DataFrame({"A": a.iloc[0], "B": b.iloc[0]}))

with tabs[6]:
    if portfolio_mode:
        st.plotly_chart(
            px.pie(df, names="coin_name", values="current_value"),
            use_container_width=True,
        )
    else:
        d = df.sort_values("volume_24h", ascending=False)
        pie = pd.concat(
            [
                d.head(5),
                pd.DataFrame(
                    [
                        {
                            "coin_name": "Others",
                            "volume_24h": d.iloc[5:]["volume_24h"].sum(),
                        }
                    ]
                ),
            ]
        )
        st.plotly_chart(
            px.pie(pie, names="coin_name", values="volume_24h"),
            use_container_width=True,
        )

with st.sidebar:
    st.markdown("### Export")
    if st.button("Prepare Excel"):
        buf = io.BytesIO()
        df.to_excel(buf, index=False, engine="xlsxwriter")
        buf.seek(0)
        st.download_button("⬇ Download Excel", buf, "alpha_terminal_export.xlsx")
