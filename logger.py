from __future__ import annotations

import argparse
import datetime as dt
import time
import schedule

from src.data import FetchConfig, fetch_coingecko_markets
from src.storage import append_snapshot


def job(per_page):
    try:
        print(f"[{dt.datetime.now()}] Fetching {per_page} coins...")
        cfg = FetchConfig(per_page=per_page)
        df = fetch_coingecko_markets(cfg)
        ts = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        append_snapshot(df, ts)
        print(f"[{dt.datetime.now()}] Snapshot saved successfully")
    except Exception as e:
        print(f"[{dt.datetime.now()}] Error: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="coingecko", choices=["coingecko", "coinmarketcap_scrape"])
    ap.add_argument("--per_page", type=int, default=200)
    ap.add_argument("--every_minutes", type=int, default=15)
    args = ap.parse_args()

    print(f"Starting logger: fetching {args.per_page} coins every {args.every_minutes} minutes")
    job(args.per_page)
    schedule.every(args.every_minutes).minutes.do(job, args.per_page)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
