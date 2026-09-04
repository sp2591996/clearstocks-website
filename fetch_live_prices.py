"""
fetch_live_prices.py
-------------------------------------------------------------------
Produces live_prices.json (at the repo root, next to index.html) —
the small, fast file that lets the site show a delayed-intraday price
+ today's % change on top of your normal (manual) fundamentals
refresh, without re-running the whole ML pipeline.

This is intentionally CHEAP: it only pulls each stock's current price
and previous close (via yfinance's lightweight `fast_info`, not the
much heavier `.info` call your other fetch scripts use), so it's safe
to run every 10-15 minutes during market hours.

Output shape (read by app.js -> loadStockData()):
{
  "updated_at": "2026-09-03T10:15:00+05:30",
  "prices": [
    {"symbol": "RELIANCE", "price": 2851.10, "day_change_pct": 0.78},
    ...
  ]
}

Run manually:
    python fetch_live_prices.py

This is also the script the GitHub Actions workflow
(.github/workflows/refresh-prices.yml) runs on a schedule once the
site is published to GitHub Pages — see that file for the schedule.
-------------------------------------------------------------------
"""

import json
import time
from datetime import datetime, timezone, timedelta

import pandas as pd
import yfinance as yf

IST = timezone(timedelta(hours=5, minutes=30))


def fetch_live_prices(list_csv="nifty200_list.csv", out_path="website/live_prices.json"):
    stock_list = pd.read_csv(list_csv)
    symbols = stock_list["yfinance_symbol"].tolist()

    prices = []
    failed = []
    total = len(symbols)

    for i, yf_symbol in enumerate(symbols, 1):
        clean_symbol = yf_symbol.replace(".NS", "")
        try:
            ticker = yf.Ticker(yf_symbol)
            fi = ticker.fast_info
            # yfinance's FastInfo exposes both snake_case attributes and
            # camelCase dict keys depending on version - try attribute
            # access first (most reliable across recent yfinance releases).
            last_price = getattr(fi, "last_price", None)
            prev_close = getattr(fi, "previous_close", None)
            if last_price is None:
                try:
                    last_price = fi["lastPrice"]
                except Exception:
                    pass
            if prev_close is None:
                try:
                    prev_close = fi["previousClose"]
                except Exception:
                    pass

            if last_price is None:
                failed.append(clean_symbol)
                continue

            day_change_pct = None
            if prev_close:
                day_change_pct = round((last_price - prev_close) / prev_close * 100, 2)

            prices.append({
                "symbol": clean_symbol,
                "price": round(float(last_price), 2),
                "day_change_pct": day_change_pct,
            })
        except Exception as e:
            print(f"  ! {clean_symbol}: {e}")
            failed.append(clean_symbol)

        if i % 20 == 0:
            print(f"  [{i}/{total}] fetched...")
        time.sleep(0.15)  # be polite to Yahoo Finance

    payload = {
        "updated_at": datetime.now(IST).strftime("%Y-%m-%d %H:%M IST"),
        "prices": prices,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f)

    print(f"\nWrote {len(prices)}/{total} live prices to {out_path}")
    if failed:
        print(f"Failed ({len(failed)}): {failed[:15]}{'...' if len(failed) > 15 else ''}")
    return payload


def _within_nse_hours(now_ist: datetime) -> bool:
    """Mon-Fri, 9:15am-3:30pm IST. Doesn't know about NSE holidays -
    on a market holiday this just fetches unchanged prices, which is
    harmless, just a wasted run."""
    if now_ist.weekday() >= 5:  # Sat=5, Sun=6
        return False
    minutes = now_ist.hour * 60 + now_ist.minute
    return (9 * 60 + 15) <= minutes <= (15 * 60 + 30)


if __name__ == "__main__":
    import os
    import sys
    list_csv = sys.argv[1] if len(sys.argv) > 1 else "nifty200_list.csv"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "live_prices.json"

    now_ist = datetime.now(IST)
    if "--force" not in sys.argv and not _within_nse_hours(now_ist):
        print(f"Outside NSE market hours ({now_ist.strftime('%Y-%m-%d %H:%M IST')}, "
              f"{now_ist.strftime('%A')}) - skipping fetch. Pass --force to run anyway.")
        sys.exit(0)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    fetch_live_prices(list_csv, out_path)
