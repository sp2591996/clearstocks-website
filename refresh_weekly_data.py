"""
refresh_weekly_data.py
-------------------------------------------------------------------
The weekly "keep the numbers honest" refresh. Runs once a week (see
.github/workflows/refresh-weekly.yml) and updates:

  1. fundamentals_history/<SYMBOL>_fundamentals.csv  — one row per
     fiscal year, for all 200 stocks: Total Revenue, Net Income,
     EBIT, EBITDA, Total Debt, Stockholders Equity, Cash & Equivalents,
     Total Assets, Free Cash Flow, Operating Cash Flow, Capital
     Expenditure, ROE. Pulled from each company's own reported
     financial statements via yfinance — not a market price, so it's
     safe and meaningful to refresh automatically.
  2. fundamentals_all.json + company_facts.json — rebuilt from those
     CSVs (and from nifty200_list.csv), same shape the site already
     reads.
  3. dashboard_data.json — for ALL 200 stocks, refreshes `roe` from
     the latest fundamentals year (fundamentals-only, no live price
     needed). For ONLY the 10 already-researched ("full") stocks, ALSO
     refreshes pe_ratio, pb_ratio, market_cap, week52_high/low from
     current market data, since those 10 are the ones a person has
     actually reviewed and the site is comfortable showing valuation
     ratios for.

     Deliberately NOT touched, for any stock: symbol, name, sector,
     research_status, valuation_verdict, interpretation, summary,
     has_deck, current_price, day_change_pct — those are either
     curated research text (only a human should change them) or owned
     by the 15-minute live-price job. And for the other 190
     ("pipeline") stocks, pe_ratio/pb_ratio/market_cap/week52 STAY
     null on purpose — showing "Not yet scored" for a stock nobody has
     actually reviewed is the honest state, not a bug to "fix" here.
  4. status.json — records when this last ran successfully, so the
     website's "Refresh now" panel can show it.

This script only ever WRITES these files locally — the GitHub Actions
workflow that calls it is the one that opens a Pull Request with the
result, so a human (you) reviews the diff before it goes live. That's
different from the 15-minute price job, which pushes directly since a
wrong price is low-stakes and self-corrects in 15 minutes; a bad
fundamentals fetch is worth a second look first.

Run manually:
    python refresh_weekly_data.py
"""
import csv
import glob
import json
import os
import time
from datetime import datetime, timezone, timedelta

import pandas as pd
import yfinance as yf

IST = timezone(timedelta(hours=5, minutes=30))

FUND_DIR = "fundamentals_history"
DASH_PATH = "dashboard_data.json"
FUND_ALL_PATH = "fundamentals_all.json"
FACTS_PATH = "company_facts.json"
STATUS_PATH = "status.json"
LIST_CSV = "nifty200_list.csv"

# The exact statement rows the site's Financials tab already expects
# (see stock.html's renderFinancialsTable/renderCommonSize/renderLeverage) —
# keep these names identical to what's already in fundamentals_all.json.
INCOME_ROWS = ["Total Revenue", "Net Income", "EBIT", "EBITDA"]
BALANCE_ROWS = ["Total Debt", "Stockholders Equity", "Cash And Cash Equivalents", "Total Assets"]
CASHFLOW_ROWS = ["Free Cash Flow", "Operating Cash Flow", "Capital Expenditure"]
ALL_METRIC_ROWS = INCOME_ROWS + BALANCE_ROWS + CASHFLOW_ROWS


def fetch_statement_rows(ticker, statement, rows):
    """Returns {period_end_date_str: {row_name: value}} for the requested
    rows out of a yfinance annual statement (a DataFrame: rows=line items,
    columns=period-end dates). Missing rows/periods are just absent from
    the result — every metric is read defensively since not every
    statement carries every line (banks have no EBITDA, etc.)."""
    out = {}
    if statement is None or statement.empty:
        return out
    for row_name in rows:
        if row_name not in statement.index:
            continue
        series = statement.loc[row_name]
        for period, value in series.items():
            date_str = period.strftime("%Y-%m-%d") if hasattr(period, "strftime") else str(period)
            out.setdefault(date_str, {})[row_name] = value
    return out


def fetch_one_stock_fundamentals(yf_symbol):
    """Returns a list of yearly rows (oldest first), each a dict with
    the same keys fundamentals_history CSVs already use, or [] on
    failure (that stock's existing CSV is simply left untouched by the
    caller in that case, rather than wiped)."""
    ticker = yf.Ticker(yf_symbol)
    merged = {}
    for statement, rows in (
        (ticker.income_stmt, INCOME_ROWS),
        (ticker.balance_sheet, BALANCE_ROWS),
        (ticker.cashflow, CASHFLOW_ROWS),
    ):
        for date_str, values in fetch_statement_rows(ticker, statement, rows).items():
            merged.setdefault(date_str, {}).update(values)

    def clean(v):
        """None AND pandas/NumPy NaN both mean "missing" here -- yfinance
        returns actual NaN floats (not None) for a period a company didn't
        report a line item for for. Treating only `is None` as missing let
        real NaNs through as the literal text "nan" in the CSV (found by
        the user reviewing the first real Pull Request this produced --
        e.g. 360ONE's 2022 row: every field literally read "nan")."""
        return None if v is None or (isinstance(v, float) and pd.isna(v)) else v

    rows_out = []
    for date_str in sorted(merged.keys()):
        r = merged[date_str]
        cleaned = {key: clean(r.get(key)) for key in ALL_METRIC_ROWS}
        # A period where every single line item is missing (some yfinance
        # tickers return a placeholder column with no real data at all)
        # isn't a real fiscal year -- writing it out just adds a blank row
        # for the site to render as a wall of "--". Skip it entirely.
        if all(v is None for v in cleaned.values()):
            continue
        net_income, equity = cleaned.get("Net Income"), cleaned.get("Stockholders Equity")
        roe = (net_income / equity) if (net_income is not None and equity not in (None, 0)) else None
        row = {"Year": date_str}
        for key in ALL_METRIC_ROWS:
            v = cleaned[key]
            row[key] = "" if v is None else str(float(v))
        row["ROE"] = "" if roe is None else str(float(roe))
        rows_out.append(row)
    return rows_out


def refresh_fundamentals_history(symbols_map):
    """symbols_map: {clean_symbol: yfinance_symbol}. Writes/overwrites
    fundamentals_history/<SYMBOL>_fundamentals.csv for every stock that
    fetched successfully; leaves the existing file alone for any stock
    that failed, so a transient Yahoo error never wipes good data."""
    os.makedirs(FUND_DIR, exist_ok=True)
    ok, failed = 0, []
    total = len(symbols_map)
    for i, (symbol, yf_symbol) in enumerate(symbols_map.items(), 1):
        try:
            rows = fetch_one_stock_fundamentals(yf_symbol)
            if rows:
                path = os.path.join(FUND_DIR, f"{symbol}_fundamentals.csv")
                with open(path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=["Year"] + ALL_METRIC_ROWS + ["ROE"])
                    writer.writeheader()
                    writer.writerows(rows)
                ok += 1
            else:
                failed.append(symbol)
        except Exception as e:
            print(f"  ! {symbol} fundamentals: {e}")
            failed.append(symbol)
        if i % 20 == 0:
            print(f"  [{i}/{total}] fundamentals fetched...")
        time.sleep(0.3)
    print(f"\nFundamentals: refreshed {ok}/{total} stocks" + (f" (failed: {failed[:15]}{'...' if len(failed) > 15 else ''})" if failed else ""))
    return ok, failed


def rebuild_fundamentals_all_and_facts():
    out = {}
    for f in glob.glob(os.path.join(FUND_DIR, "*_fundamentals.csv")):
        symbol = os.path.basename(f).replace("_fundamentals.csv", "")
        rows = []
        with open(f, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row.get("Year"):
                    rows.append(row)
        rows.sort(key=lambda r: r["Year"])
        out[symbol] = rows
    with open(FUND_ALL_PATH, "w", encoding="utf-8") as fh:
        json.dump(out, fh)
    print(f"Wrote {FUND_ALL_PATH} ({len(out)} stocks)")

    facts = {}
    with open(LIST_CSV, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            yf_sym = (row.get("yfinance_symbol") or "").replace(".NS", "")
            if yf_sym:
                facts[yf_sym] = {
                    "company_name": row.get("Company Name"),
                    "industry": row.get("Industry"),
                    "isin": row.get("ISIN Code"),
                }
    with open(FACTS_PATH, "w", encoding="utf-8") as fh:
        json.dump(facts, fh)
    print(f"Wrote {FACTS_PATH} ({len(facts)} stocks)")
    return out


def latest_roe_pct(fund_rows):
    """Most recent year's ROE as a 0-100 percent (matching how
    dashboard_data.json already stores it), or None."""
    if not fund_rows:
        return None
    last = fund_rows[-1]
    try:
        roe = float(last.get("ROE") or "")
    except (TypeError, ValueError):
        return None
    return round(roe * 100, 1)


def fetch_market_snapshot(yf_symbol):
    """PE/PB/market cap/52-week range for the flagship stocks only —
    uses the heavier `.info` call (fine at 10 stocks/week, unlike the
    200-stock 15-min job which deliberately avoids it)."""
    ticker = yf.Ticker(yf_symbol)
    info = ticker.info or {}
    return {
        "pe_ratio": info.get("trailingPE"),
        "pb_ratio": info.get("priceToBook"),
        "market_cap": info.get("marketCap"),
        "week52_high": info.get("fiftyTwoWeekHigh"),
        "week52_low": info.get("fiftyTwoWeekLow"),
    }


def refresh_dashboard_data(fund_all, symbols_map):
    with open(DASH_PATH, encoding="utf-8") as f:
        records = json.load(f)

    updated, market_failed = 0, []
    for r in records:
        symbol = r["symbol"]
        fund_rows = fund_all.get(symbol)
        if fund_rows:
            roe = latest_roe_pct(fund_rows)
            if roe is not None:
                r["roe"] = roe
                updated += 1

        if r.get("research_status") == "full":
            yf_symbol = symbols_map.get(symbol)
            if not yf_symbol:
                continue
            try:
                snap = fetch_market_snapshot(yf_symbol)
                for key, value in snap.items():
                    if value is not None:
                        r[key] = value
            except Exception as e:
                print(f"  ! {symbol} market snapshot: {e}")
                market_failed.append(symbol)
            time.sleep(0.3)

    with open(DASH_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f)
    print(f"\n{DASH_PATH}: refreshed ROE on {updated} stocks" + (f", market snapshot failed for {market_failed}" if market_failed else ", market snapshot refreshed on all 10 researched stocks"))


def write_status():
    status = {}
    if os.path.exists(STATUS_PATH):
        try:
            with open(STATUS_PATH, encoding="utf-8") as f:
                status = json.load(f)
        except Exception:
            status = {}
    status["last_data_refresh"] = datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")
    with open(STATUS_PATH, "w", encoding="utf-8") as f:
        json.dump(status, f)
    print(f"Wrote {STATUS_PATH}")


def main():
    stock_list = pd.read_csv(LIST_CSV)
    symbols_map = {
        row["yfinance_symbol"].replace(".NS", ""): row["yfinance_symbol"]
        for _, row in stock_list.iterrows()
    }

    print("Step 1/3: refreshing per-stock fundamentals history...")
    refresh_fundamentals_history(symbols_map)

    print("\nStep 2/3: rebuilding fundamentals_all.json + company_facts.json...")
    fund_all = rebuild_fundamentals_all_and_facts()

    print("\nStep 3/3: refreshing dashboard_data.json (ROE for all, valuation ratios for the 10 researched stocks)...")
    refresh_dashboard_data(fund_all, symbols_map)

    write_status()
    print("\nDone.")


if __name__ == "__main__":
    main()
