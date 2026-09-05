"""
compute_auto_scores.py
-------------------------------------------------------------------
Computes, for ALL 200 stocks (not just the ones with a PDF deck):
  - valuation_verdict  (Cheap/Fair/Expensive vs sector peers, using
    the same sector-relative ratio logic as full_valuation_ratios.py)
  - interpretation      (a plain-language one-line read combining
    valuation + profitability, replacing "Full valuation model not
    yet run for this stock")
  - ml_percentile        (an automated 0-100 score blending sector-
    relative valuation and ROE — an interim, fully automated
    stand-in for the real ML model, which needs a technical-
    indicators feed (RSI/moving averages/price history) that isn't
    part of the daily refresh yet. Clearly labelled as automated in
    the site copy, not a human-reviewed opinion.)

Nothing here depends on whether a company has a PDF research deck.
That's the whole point of this script -- has_deck stays a totally
separate flag that only controls the PDF download button.
"""
import json
import statistics

DASH_PATH = "dashboard_data.json"
FUND_ALL_PATH = "fundamentals_all.json"

SECTOR_RATIO_PRIORITY = {
    "Financial Services": ["pb_ratio", "pe_ratio"],
    "Technology": ["pe_ratio"],
    "Consumer Defensive": ["pe_ratio"],
    "Consumer Cyclical": ["pe_ratio", "price_to_sales"],
    "Healthcare": ["pe_ratio"],
    "Industrials": ["ev_ebitda", "pe_ratio"],
    "Basic Materials": ["ev_ebitda", "pb_ratio"],
    "Energy": ["ev_ebitda", "pb_ratio"],
    "Utilities": ["ev_ebitda", "pb_ratio"],
    "Real Estate": ["pb_ratio", "ev_ebitda"],
    "Communication Services": ["ev_ebitda", "price_to_sales"],
}
RATIO_LABELS = {"pe_ratio": "P/E", "pb_ratio": "P/B", "ev_ebitda": "EV/EBITDA", "price_to_sales": "Price/Sales"}


def f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main():
    with open(DASH_PATH, encoding="utf-8") as fh:
        records = json.load(fh)
    with open(FUND_ALL_PATH, encoding="utf-8") as fh:
        fund_all = json.load(fh)

    # Pull each stock's most recent fundamentals year for EV/EBITDA and Price/Sales.
    latest_fund = {}
    for symbol, rows in fund_all.items():
        if not rows:
            continue
        latest_fund[symbol] = rows[-1]

    for r in records:
        symbol = r["symbol"]
        lf = latest_fund.get(symbol, {})
        market_cap = f(r.get("market_cap"))
        total_debt = f(lf.get("Total Debt"))
        cash = f(lf.get("Cash And Cash Equivalents"))
        ebitda = f(lf.get("EBITDA"))
        revenue = f(lf.get("Total Revenue"))

        ev = None
        if market_cap is not None and total_debt is not None and cash is not None:
            ev = market_cap + total_debt - cash
        r["_ev_ebitda"] = (ev / ebitda) if (ev is not None and ebitda not in (None, 0) and ebitda > 0) else None
        r["_price_to_sales"] = (market_cap / revenue) if (market_cap is not None and revenue not in (None, 0) and revenue > 0) else None
        r["_pe_ratio"] = f(r.get("pe_ratio"))
        r["_pb_ratio"] = f(r.get("pb_ratio"))
        r["_roe"] = f(r.get("roe"))

    # Sector medians for each ratio (only over positive, real values).
    by_sector = {}
    for r in records:
        by_sector.setdefault(r.get("sector") or "Unknown", []).append(r)

    sector_median = {}
    for sector, rows in by_sector.items():
        sector_median[sector] = {}
        for key in ("_pe_ratio", "_pb_ratio", "_ev_ebitda", "_price_to_sales"):
            vals = [row[key] for row in rows if row.get(key) is not None and row[key] > 0]
            sector_median[sector][key] = statistics.median(vals) if vals else None

    key_map = {"pe_ratio": "_pe_ratio", "pb_ratio": "_pb_ratio", "ev_ebitda": "_ev_ebitda", "price_to_sales": "_price_to_sales"}

    PLACEHOLDER_VERDICTS = {
        None, "Not yet scored",
        "Valuation pending, updates once live price sync runs",
    }

    updated = 0
    for r in records:
        if r.get("research_status") == "full" and r.get("valuation_verdict") not in PLACEHOLDER_VERDICTS:
            # Already has a human-researched, curated verdict/interpretation
            # from the flagship deck process -- never overwrite that with
            # the automated version.
            continue
        r["_auto_processed"] = True
        sector = r.get("sector") or "Unknown"
        priority = SECTOR_RATIO_PRIORITY.get(sector, ["pe_ratio", "pb_ratio"])
        med = sector_median.get(sector, {})
        verdict = None
        for ratio_name in priority:
            key = key_map[ratio_name]
            val = r.get(key)
            m = med.get(key)
            if val is not None and m:
                pct = (val - m) / m * 100
                label = RATIO_LABELS[ratio_name]
                if pct < -20:
                    verdict = f"Cheap vs peers ({label}, {pct:+.0f}%)"
                elif pct > 20:
                    verdict = f"Expensive vs peers ({label}, {pct:+.0f}%)"
                else:
                    verdict = f"Fairly valued vs peers ({label}, {pct:+.0f}%)"
                break
        if verdict is None:
            # No real ratio to compare yet for this stock/sector combo -- stay honest.
            continue

        r["valuation_verdict"] = verdict
        updated += 1

        # Plain-language interpretation, combining the valuation read with
        # profitability (ROE) where we have it -- purely mechanical, no
        # human judgement involved, which is exactly why it's safe to show
        # for every stock regardless of deck status.
        roe = r.get("_roe")
        cheap = verdict.startswith("Cheap")
        expensive = verdict.startswith("Expensive")
        if roe is not None and roe >= 15 and cheap:
            interp = "Strong profitability (ROE) trading below its sector's typical valuation."
        elif roe is not None and roe >= 15 and expensive:
            interp = "Strong profitability (ROE), but priced above its sector's typical valuation."
        elif roe is not None and roe < 8 and expensive:
            interp = "Weak profitability (ROE) and priced above its sector's typical valuation."
        elif roe is not None and roe < 8 and cheap:
            interp = "Cheap versus peers, but profitability (ROE) is also weaker than the sector."
        elif cheap:
            interp = "Trading below its sector's typical valuation on this metric."
        elif expensive:
            interp = "Trading above its sector's typical valuation on this metric."
        else:
            interp = "Valuation is in line with its sector peers on this metric."
        r["interpretation"] = interp

        # Automated 0-100 score: 60% valuation percentile (cheaper = higher),
        # 40% ROE percentile within sector. This is NOT the technical ML
        # model (that needs a daily price-history/indicators feed we don't
        # have yet) -- it's an interim, fully automated, sector-relative
        # fundamentals score. Site copy must label it "Automated" until the
        # real model is wired up.
        val_key = key_map[priority[0]] if priority else "_pe_ratio"
        val_val = r.get(val_key)
        val_med = med.get(val_key)
        val_score = None
        if val_val is not None and val_med:
            pct = (val_val - val_med) / val_med
            val_score = max(0, min(100, 50 - pct * 100))  # cheaper (negative pct) -> higher score
        r["_val_score_component"] = val_score

    # ROE percentile within sector, for the score blend.
    for sector, rows in by_sector.items():
        roes = sorted((row["_roe"], i) for i, row in enumerate(rows) if row.get("_roe") is not None)
        n = len(roes)
        for rank, (_, idx) in enumerate(roes):
            rows[idx]["_roe_pctile"] = (rank / (n - 1) * 100) if n > 1 else 50.0

    for r in records:
        if not r.pop("_auto_processed", False):
            for k in ("_ev_ebitda", "_price_to_sales", "_pe_ratio", "_pb_ratio", "_roe", "_val_score_component", "_roe_pctile"):
                r.pop(k, None)
            continue
        val_score = r.get("_val_score_component")
        roe_pctile = r.get("_roe_pctile")
        if val_score is not None and roe_pctile is not None:
            r["ml_percentile"] = round(0.6 * val_score + 0.4 * roe_pctile, 1)
        elif val_score is not None:
            r["ml_percentile"] = round(val_score, 1)
        elif roe_pctile is not None:
            r["ml_percentile"] = round(roe_pctile, 1)
        # else: leave as None -- genuinely no data to score this stock on.

        # Refresh the summary line to stop implying a deck/analyst review is
        # required for the numbers above it to be trustworthy.
        if r.get("research_status") != "full":
            has_verdict = r.get("ml_percentile") is not None
            if has_verdict:
                r["summary"] = (
                    f"{r['name']} — automated valuation and score below are calculated fresh from "
                    f"real market and financial data (updated daily), not yet paired with an analyst's "
                    f"written company review. A full deep-dive report may be added later; the numbers "
                    f"here don't wait on that."
                )
            else:
                r["summary"] = (
                    f"{r['name']} doesn't yet have enough fresh market data to compute a score or "
                    f"verdict — this fills in automatically once its numbers are available."
                )

        # Clean up scratch keys.
        for k in ("_ev_ebitda", "_price_to_sales", "_pe_ratio", "_pb_ratio", "_roe", "_val_score_component", "_roe_pctile"):
            r.pop(k, None)

    with open(DASH_PATH, "w", encoding="utf-8") as fh:
        json.dump(records, fh, indent=2)

    scored = sum(1 for r in records if r.get("ml_percentile") is not None)
    verdicted = sum(1 for r in records if r.get("valuation_verdict") not in (None, "Not yet scored"))
    print(f"Verdicts computed: {verdicted}/{len(records)}")
    print(f"Scores computed:   {scored}/{len(records)}")


if __name__ == "__main__":
    main()
