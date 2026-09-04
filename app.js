/* =========================================================================
   Shared data + rendering helpers for the screener site.

   Real data model:
   - dashboard_data.json  -> produced by export_for_web.py (your existing
     pipeline script). One object per stock: symbol, name, sector,
     current_price, ml_percentile, valuation_verdict, interpretation,
     pe_ratio, pb_ratio, roe, market_cap, week52_high, week52_low,
     dcf_upside, price_history.
   - live_prices.json -> NEW, produced by fetch_live_prices.py, refreshed
     every ~15 min during NSE hours by a GitHub Actions schedule (see
     .github/workflows/refresh-prices.yml). Adds day_change_pct and
     updated_at on top of the daily dashboard_data.json snapshot, so the
     "today" numbers can move during the day even though ML scores only
     update when you run your full refresh routine.

   When these files aren't present (e.g. testing locally without the real
   pipeline output), SAMPLE_STOCKS below is used instead and a banner says
   so -- so the page always shows a realistic working state, but never
   passes off sample numbers as real ones.
========================================================================= */

const SAMPLE_STOCKS = [
  {symbol:"RELIANCE", name:"Reliance Industries", sector:"Oil Gas & Consumable Fuels", current_price:2847.30, day_change_pct:0.64, ml_percentile:71, valuation_verdict:"Fair (PE, 4% vs sector)", interpretation:"Neutral / mixed signals", pe_ratio:24.8, pb_ratio:2.1, roe:9.2, market_cap:1927000, week52_high:3217.90, week52_low:2221.00},
  {symbol:"HDFCBANK", name:"HDFC Bank", sector:"Financial Services", current_price:1698.55, day_change_pct:-0.28, ml_percentile:64, valuation_verdict:"Fair (PB, -6% vs sector)", interpretation:"Neutral / mixed signals", pe_ratio:19.2, pb_ratio:2.8, roe:16.9, market_cap:1298000, week52_high:1880.00, week52_low:1426.00},
  {symbol:"TCS", name:"Tata Consultancy Services", sector:"Information Technology", current_price:3412.10, day_change_pct:1.12, ml_percentile:38, valuation_verdict:"Expensive (PE, 22% vs sector)", interpretation:"AVOID (weak signal + expensive)", pe_ratio:28.4, pb_ratio:12.6, roe:44.1, market_cap:1234000, week52_high:4592.25, week52_low:3056.00},
  {symbol:"INFY", name:"Infosys", sector:"Information Technology", current_price:1548.90, day_change_pct:0.85, ml_percentile:58, valuation_verdict:"Fair (PE, 3% vs sector)", interpretation:"Neutral / mixed signals", pe_ratio:24.1, pb_ratio:7.4, roe:30.8, market_cap:643000, week52_high:2006.45, week52_low:1358.35},
  {symbol:"ICICIBANK", name:"ICICI Bank", sector:"Financial Services", current_price:1289.40, day_change_pct:0.42, ml_percentile:82, valuation_verdict:"Cheap (PB, -18% vs sector)", interpretation:"STRONGEST CANDIDATE (good signal + cheap)", pe_ratio:17.6, pb_ratio:2.9, roe:17.3, market_cap:906000, week52_high:1362.35, week52_low:1023.75},
  {symbol:"BHARTIARTL", name:"Bharti Airtel", sector:"Telecommunication", current_price:1712.20, day_change_pct:-0.55, ml_percentile:76, valuation_verdict:"Fair (EV/EBITDA, 8% vs sector)", interpretation:"Neutral / mixed signals", pe_ratio:41.3, pb_ratio:9.8, roe:24.5, market_cap:1032000, week52_high:1815.00, week52_low:1234.05},
  {symbol:"BAJFINANCE", name:"Bajaj Finance", sector:"Financial Services", current_price:7614.85, day_change_pct:1.83, ml_percentile:69, valuation_verdict:"Fair (PB, 5% vs sector)", interpretation:"Neutral / mixed signals", pe_ratio:31.2, pb_ratio:5.9, roe:20.1, market_cap:472000, week52_high:8192.00, week52_low:6187.00},
  {symbol:"MARUTI", name:"Maruti Suzuki", sector:"Automobile and Auto Components", current_price:12684.50, day_change_pct:2.14, ml_percentile:88, valuation_verdict:"Cheap (PE, -14% vs sector)", interpretation:"STRONGEST CANDIDATE (good signal + cheap)", pe_ratio:22.9, pb_ratio:3.8, roe:17.2, market_cap:399000, week52_high:13720.00, week52_low:10405.00},
  {symbol:"ADANIPOWER", name:"Adani Power", sector:"Power", current_price:598.75, day_change_pct:3.42, ml_percentile:91, valuation_verdict:"Expensive (EV/EBITDA, 27% vs sector)", interpretation:"Priced-in momentum (good signal but expensive)", pe_ratio:14.1, pb_ratio:6.2, roe:48.3, market_cap:230000, week52_high:729.90, week52_low:412.10},
  {symbol:"ITC", name:"ITC Limited", sector:"Fast Moving Consumer Goods", current_price:468.30, day_change_pct:-0.18, ml_percentile:41, valuation_verdict:"Fair (PE, -2% vs sector)", interpretation:"Neutral / mixed signals", pe_ratio:27.1, pb_ratio:7.0, roe:26.2, market_cap:585000, week52_high:528.35, week52_low:399.35},
  {symbol:"TATASTEEL", name:"Tata Steel", sector:"Metals & Mining", current_price:172.60, day_change_pct:-1.24, ml_percentile:33, valuation_verdict:"Expensive (EV/EBITDA, 19% vs sector)", interpretation:"AVOID (weak signal + expensive)", pe_ratio:38.7, pb_ratio:2.1, roe:5.6, market_cap:216000, week52_high:184.60, week52_low:126.30},
  {symbol:"SUNPHARMA", name:"Sun Pharmaceutical", sector:"Healthcare", current_price:1824.15, day_change_pct:0.31, ml_percentile:73, valuation_verdict:"Fair (PE, 6% vs sector)", interpretation:"Neutral / mixed signals", pe_ratio:36.6, pb_ratio:8.9, roe:16.8, market_cap:438000, week52_high:1961.90, week52_low:1548.10},
  {symbol:"BHEL", name:"Bharat Heavy Electricals", sector:"Capital Goods", current_price:284.90, day_change_pct:4.87, ml_percentile:94, valuation_verdict:"Expensive (EV/EBITDA, 41% vs sector)", interpretation:"Priced-in momentum (good signal but expensive)", pe_ratio:62.4, pb_ratio:7.1, roe:11.3, market_cap:99000, week52_high:342.75, week52_low:178.90},
  {symbol:"WIPRO", name:"Wipro", sector:"Information Technology", current_price:298.45, day_change_pct:-0.72, ml_percentile:46, valuation_verdict:"Fair (PE, -4% vs sector)", interpretation:"Neutral / mixed signals", pe_ratio:22.6, pb_ratio:3.4, roe:15.2, market_cap:156000, week52_high:346.00, week52_low:239.05},
  {symbol:"NTPC", name:"NTPC", sector:"Power", current_price:352.10, day_change_pct:-0.41, ml_percentile:29, valuation_verdict:"Cheap (EV/EBITDA, -12% vs sector)", interpretation:"Potential value trap (cheap but weak signal)", pe_ratio:15.8, pb_ratio:1.9, roe:12.1, market_cap:341000, week52_high:448.45, week52_low:305.75},
  {symbol:"HINDUNILVR", name:"Hindustan Unilever", sector:"Fast Moving Consumer Goods", current_price:2412.70, day_change_pct:0.19, ml_percentile:52, valuation_verdict:"Expensive (PE, 16% vs sector)", interpretation:"Neutral / mixed signals", pe_ratio:52.3, pb_ratio:11.2, roe:21.4, market_cap:567000, week52_high:2769.00, week52_low:2172.05},
  {symbol:"PNB", name:"Punjab National Bank", sector:"Financial Services", current_price:106.85, day_change_pct:1.05, ml_percentile:79, valuation_verdict:"Cheap (PB, -24% vs sector)", interpretation:"STRONGEST CANDIDATE (good signal + cheap)", pe_ratio:8.9, pb_ratio:0.9, roe:12.6, market_cap:117000, week52_high:129.45, week52_low:85.10},
  {symbol:"IRFC", name:"Indian Railway Finance Corp", sector:"Financial Services", current_price:148.30, day_change_pct:-0.95, ml_percentile:85, valuation_verdict:"Fair (PB, 9% vs sector)", interpretation:"Neutral / mixed signals", pe_ratio:26.7, pb_ratio:3.6, roe:13.9, market_cap:194000, week52_high:229.00, week52_low:108.15},
  {symbol:"ASIANPAINT", name:"Asian Paints", sector:"Consumer Durables", current_price:2298.60, day_change_pct:-1.67, ml_percentile:22, valuation_verdict:"Expensive (PE, 31% vs sector)", interpretation:"AVOID (weak signal + expensive)", pe_ratio:54.8, pb_ratio:14.1, roe:24.9, market_cap:220000, week52_high:3422.85, week52_low:2124.00},
  {symbol:"DRREDDY", name:"Dr Reddy's Laboratories", sector:"Healthcare", current_price:1186.40, day_change_pct:0.58, ml_percentile:61, valuation_verdict:"Fair (PE, -1% vs sector)", interpretation:"Neutral / mixed signals", pe_ratio:19.4, pb_ratio:3.7, roe:18.6, market_cap:198000, week52_high:1420.00, week52_low:1050.05},
];

const SAMPLE_INDICES = [
  {name:"NIFTY 100", value:24812.35, change_pct:0.42},
  {name:"NIFTY 200", value:13108.60, change_pct:0.38},
  {name:"NIFTY BANK", value:52340.15, change_pct:-0.21},
  {name:"NIFTY IT", value:38904.70, change_pct:0.91},
];

let DATA_SOURCE_IS_SAMPLE = true;
let STOCKS = SAMPLE_STOCKS;
let LAST_UPDATED = null;

async function loadStockData() {
  try {
    const res = await fetch("dashboard_data.json", { cache: "no-store" });
    if (!res.ok) throw new Error("not found");
    const json = await res.json();
    if (Array.isArray(json) && json.length) {
      STOCKS = json.map(normalizeRecord);
      DATA_SOURCE_IS_SAMPLE = false;
    }
  } catch (e) { /* keep sample data */ }

  try {
    const res2 = await fetch("live_prices.json", { cache: "no-store" });
    if (res2.ok) {
      const live = await res2.json();
      const bySymbol = {};
      (live.prices || []).forEach(p => bySymbol[p.symbol] = p);
      STOCKS = STOCKS.map(s => bySymbol[s.symbol] ? { ...s, current_price: bySymbol[s.symbol].price, day_change_pct: bySymbol[s.symbol].day_change_pct } : s);
      LAST_UPDATED = live.updated_at || null;
    }
  } catch (e) { /* fine without it */ }

  return STOCKS;
}

function normalizeRecord(r) {
  // Real export_for_web.py output has a couple of raw-data quirks a
  // first-time visitor should never see: a ".NS" (NSE) suffix on the
  // symbol, market cap in plain rupees instead of Crores, and ROE as
  // a 0-1 fraction instead of a percent. Clean those up here, once,
  // so every page downstream can just display the numbers directly.
  const symbol = (r.symbol || "").replace(/\.NS$/i, "");
  const roe = r.roe != null ? (Math.abs(r.roe) <= 1.5 ? r.roe * 100 : r.roe) : null;
  const marketCap = r.market_cap != null ? r.market_cap / 1e7 : null; // paise->Cr not needed, rupees->Cr = /1e7
  return {
    symbol, name: r.name || symbol, sector: r.sector,
    current_price: r.current_price, day_change_pct: r.day_change_pct ?? 0,
    ml_percentile: r.ml_percentile != null ? Math.round(r.ml_percentile) : null,
    valuation_verdict: r.valuation_verdict,
    interpretation: r.interpretation,
    pe_ratio: r.pe_ratio != null ? Math.round(r.pe_ratio * 10) / 10 : null,
    pb_ratio: r.pb_ratio != null ? Math.round(r.pb_ratio * 10) / 10 : null,
    roe: roe != null ? Math.round(roe * 10) / 10 : null,
    market_cap: marketCap, week52_high: r.week52_high, week52_low: r.week52_low,
    price_history: r.price_history || null,
    // Summary block fields (see generate_dashboard_data.py) — passed
    // through as-is, no unit conversion needed.
    research_status: r.research_status || "pipeline",
    summary: r.summary || null,
    has_deck: !!r.has_deck,
  };
}

/* ---------- formatting ---------- */
function fmtPrice(v) { return v == null ? "—" : "₹" + v.toLocaleString("en-IN", { maximumFractionDigits: 2 }); }
function fmtPct(v) { if (v == null) return "—"; const s = v >= 0 ? "+" : ""; return `${s}${v.toFixed(2)}%`; }
function fmtCap(v) { if (v == null) return "—"; if (v >= 100000) return "₹" + (v / 100000).toFixed(2) + "L Cr"; return "₹" + v.toLocaleString("en-IN") + " Cr"; }
function chgClass(v) { return v >= 0 ? "pos" : "neg"; }
function verdictClass(v) {
  if (!v) return "neutral";
  if (v.startsWith("Cheap")) return "pos";
  if (v.startsWith("Expensive")) return "neg";
  return "neutral";
}

// Table/list rows need a short, single-line verdict — the researched
// flagship stocks carry a full-sentence reasoning (e.g. "Expensive vs
// Cipla and Dr. Reddy's, priced for the pending Organon acquisition") that
// looks fine on the stock's own page but breaks the compact pill shape in
// a list (found via user report). Cut to the clause before the first
// comma/semicolon, capped at 28 characters; the full text is still
// available as the pill's hover tooltip.
function verdictShort(v) {
  if (!v) return "—";
  let s = v.split(" (")[0].split(",")[0].split(";")[0];
  if (s.length > 28) s = s.slice(0, 27).trimEnd() + "…";
  return s;
}

/* ---------- nav / search (shared across pages) ----------
   wireSearchBox() drives any search input + its results dropdown. Used for
   the small nav-bar search box AND the big homepage hero search box, which
   previously had no id/results element/listener at all — typing in it did
   nothing (found via user report). Both boxes now share this one function
   so a fix here applies everywhere. */
function wireSearchBox(input, results) {
  if (!input || !results) return;
  input.addEventListener("input", () => {
    const q = input.value.trim().toUpperCase();
    if (!q) { results.style.display = "none"; results.innerHTML = ""; return; }
    const matches = STOCKS.filter(s => s.symbol.includes(q) || s.name.toUpperCase().includes(q)).slice(0, 8);
    if (!matches.length) {
      results.style.display = "block";
      results.innerHTML = `<div style="padding:14px 16px;color:var(--text-muted);font-size:13px;">No matches for "${input.value.trim()}"</div>`;
      return;
    }
    results.innerHTML = matches.map(s => `
      <div class="search-row" data-symbol="${s.symbol}">
        <span class="sym">${s.symbol}</span>
        <span class="company-name">${s.name}</span>
        <span class="num">${fmtPrice(s.current_price)}</span>
      </div>`).join("");
    results.style.display = "block";
  });
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".search-box") && !e.target.closest(".hero-search") && !results.contains(e.target)) {
      results.style.display = "none";
    }
  });
}

function initNav() {
  wireSearchBox(document.getElementById("global-search"), document.getElementById("search-results"));
  wireSearchBox(document.getElementById("hero-search-input"), document.getElementById("hero-search-results"));
  initMobileNav();
  initDataStatus();
}

// Populates the footer's "Live prices" / "Full data" timestamps. Fetches
// its own data independently (rather than relying on loadStockData()
// having already run) so the footer widget works the same way on every
// page, including ones like Contact/Disclaimer that never call
// loadStockData(). The "Refresh now" links next to these times are plain
// <a> tags straight to each GitHub Actions workflow's page (see the HTML)
// -- a static site has no server to safely trigger those jobs itself.
async function initDataStatus() {
  const priceEl = document.getElementById("ds-price-time");
  const dataEl = document.getElementById("ds-data-time");
  if (!priceEl && !dataEl) return;

  if (priceEl) {
    try {
      const res = await fetch("live_prices.json", { cache: "no-store" });
      if (res.ok) {
        const live = await res.json();
        priceEl.textContent = live.updated_at || "not yet run";
      } else {
        priceEl.textContent = "not yet run";
      }
    } catch (e) {
      priceEl.textContent = "not yet run";
    }
  }

  if (dataEl) {
    try {
      const res = await fetch("status.json", { cache: "no-store" });
      if (res.ok) {
        const status = await res.json();
        dataEl.textContent = status.last_data_refresh || "not yet run";
      } else {
        dataEl.textContent = "not yet run";
      }
    } catch (e) {
      dataEl.textContent = "not yet run";
    }
  }
}

// Drives the hamburger button + dropdown panel that replace the nav links
// on mobile (see styles.css .mobile-toggle / .mobile-nav-panel — the CSS
// for these existed already but no button or menu logic did, so mobile
// visitors had no way to navigate at all; found via user report).
function initMobileNav() {
  const toggle = document.getElementById("mobile-toggle");
  const panel = document.getElementById("mobile-nav-panel");
  if (!toggle || !panel) return;
  toggle.addEventListener("click", () => panel.classList.toggle("open"));
  panel.querySelectorAll("a").forEach(a => a.addEventListener("click", () => panel.classList.remove("open")));
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".mobile-toggle") && !e.target.closest(".mobile-nav-panel")) {
      panel.classList.remove("open");
    }
  });
}

function sampleBanner() {
  return DATA_SOURCE_IS_SAMPLE
    ? `<div class="sample-banner">&#9432; You're viewing sample numbers while the site is being set up. Real prices and scores will appear here automatically once it's live.</div>`
    : "";
}

/* ---------- Insight Score (renamed from "ML Score") ---------- */
// Plain-language tiers for the score so a first-time visitor understands
// the number without needing to read the methodology page.
function insightTier(pct) {
  if (pct == null) return { label: "—", cls: "neutral" };
  if (pct >= 80) return { label: "Strong", cls: "pos" };
  if (pct >= 55) return { label: "Above average", cls: "pos" };
  if (pct >= 40) return { label: "Average", cls: "neutral" };
  return { label: "Weak", cls: "neg" };
}

function scoreBadge(pct, size) {
  const tier = insightTier(pct);
  const val = pct == null ? "—" : pct;
  return `<span class="score-badge" style="--pct:${pct ?? 0}"><span class="dial"></span>${val}<span style="font-weight:500;color:var(--text-muted);font-size:11.5px;">/100</span></span>`;
}

// Builds a plain-language sentence explaining WHY a stock is tagged the
// way it is (e.g. "Strongest Candidate"), instead of leaving the label
// unexplained.
function explainVerdict(s) {
  const tier = insightTier(s.ml_percentile);
  const val = (s.valuation_verdict || "");
  const cheap = val.startsWith("Cheap");
  const expensive = val.startsWith("Expensive");
  const strongScore = s.ml_percentile != null && s.ml_percentile >= 70;
  const weakScore = s.ml_percentile != null && s.ml_percentile < 40;

  if (strongScore && cheap) {
    return `${s.symbol} scores <b>${s.ml_percentile}/100</b> on our Insight Score (${tier.label.toLowerCase()}, meaning the model's history-based signals line up well) <b>and</b> its current price looks cheap versus other companies in the same sector. Both checks pointing the same way is why it's flagged as a strongest candidate — it does not mean the price will rise.`;
  }
  if (weakScore && expensive) {
    return `${s.symbol} scores <b>${s.ml_percentile}/100</b> (weak) <b>and</b> looks expensive versus its sector right now. Both checks pointing the same way is why it's flagged to avoid on this screen — it does not mean the price will fall.`;
  }
  if (strongScore && expensive) {
    return `${s.symbol} scores well (<b>${s.ml_percentile}/100</b>) but already looks expensive versus its sector — the good signal may already be "priced in" by other investors.`;
  }
  if (weakScore && cheap) {
    return `${s.symbol} looks cheap versus its sector, but scores weakly (<b>${s.ml_percentile}/100</b>) — sometimes a stock is cheap for a real reason. Worth extra research before assuming it's a bargain.`;
  }
  return `${s.symbol}'s Insight Score and valuation check don't point strongly the same way, so it's treated as neutral — worth a closer look rather than a clear signal either way.`;
}
