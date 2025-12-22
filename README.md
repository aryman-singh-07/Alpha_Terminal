# 📈 Crypto Dashboard — Trading Style (Streamlit + Python)

A live **Crypto Trading Dashboard** that fetches top 200 coins, computes investor-focused KPIs, and provides slicer-driven insights.

## ✅ Features (from your requirement image)
- Power Query / Pivot / Slicers mindset (Excel export companion)
- Charts (Plotly + Matplotlib-ready)
- Conditional formatting style KPIs
- Automation with Schedule/Cron-style logger
- Requests + BeautifulSoup (optional scrape)
- Pandas / NumPy processing
- APIs, JSON parsing
- SQLite logging for historical snapshots
- Excel export via OpenPyXL/XlsxWriter
- VBA macro (Excel) for working-hours security

## 🚀 Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## 🕒 Real-time logging (optional)
```bash
python logger.py --source coingecko --per_page 200 --every_minutes 15
```

## 📌 Your 6 requirements
Implemented in 6 tabs inside the app:
1) Budget KPIs + 5-range price slicer (least avg downfall + counts)
2) $0–$5 range, top 10 by 1h-before price; chart shows 24h-before & 7d-before
3) Top 10 price change vs prev 1h with slicer (>=10 / <10) + table
4) Prefix filter + working-hours security (Streamlit + Excel VBA option)
5) Compare 2 coins + validation + diff KPIs
6) Liquidity pie (top 5 + others) with price category slicer (0–50 / >50)

## 🧾 Excel companion
See `excel/README_excel.md` and `excel/security_vba.bas`
