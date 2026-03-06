# add_media_forecasts_and_plot_markers.py
# - Appends media-quoted gold targets to your forecasts CSV (idempotent).
# - Plots 2010–2025 gold with markers only (no annotations).

import os, re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import yfinance as yf

# ---------------- Config ----------------
SINCE_DATE       = pd.Timestamp("2000-01-01")
UNTIL_DATE       = pd.Timestamp("2026-12-31")
FORECASTS_CSV    = "bank_gold_forecasts_2010_2025.csv"
SAVE_PNG         = "gold_with_bank_forecasts_markers.png"

PRIMARY_TICKER   = "XAUUSD=X"            # Spot gold
PRIMARY_TICKER   = "TSLA"            # tesla

FALLBACKS        = ["GC=F", "XAU=X", "IAU"]
LOG_SCALE        = False
FIGSIZE          = (14, 8)
DPI              = 180
AUTOFILL_WINDOW_DAYS = 7                 # only fill truly blank price cells
SHOW_GUIDE_LINES = True                 # faint dotted horizontals at forecast level

# Banks/styles (media variants included)
BANK_STYLE = {
    "Goldman Sachs":           dict(color="#d97600", marker="o"),
    "Goldman Sachs (media)":   dict(color="#d97600", marker="o"),
    "J.P. Morgan":             dict(color="#1f77b4", marker="s"),
    "J.P. Morgan (media)":     dict(color="#1f77b4", marker="s"),
    "HSBC":                    dict(color="#2ca02c", marker="^"),
    "HSBC (media)":            dict(color="#2ca02c", marker="^"),
    "Citi (media)":            dict(color="#9467bd", marker="D"),
}

# ✅ Media-quoted entries to add if missing
#    (Edit freely; date is when the projection was widely quoted)
MEDIA_ENTRIES = [
    {"bank": "Goldman Sachs (media)", "date": "2023-05-01", "price": "5000", "label": "media-quoted long-term projection"},
    {"bank": "J.P. Morgan (media)",   "date": "2025-12-31", "price": "2900", "label": "media-quoted 2025 target"},
    {"bank": "Citi (media)",          "date": "2024-06-30", "price": "3000", "label": "media-quoted 2024 scenario"},
]

# ---------------- Helpers ----------------
def download_gold_series():
    """Robust downloader with fallbacks + explicit date range."""
    start = SINCE_DATE
    end   = UNTIL_DATE + pd.Timedelta(days=1)  # Yahoo end exclusive

    def try_dl(ticker):
        df = yf.download(
            ticker, start=start, end=end,
            interval="1d", auto_adjust=True, progress=False,
            group_by="column", threads=False
        )
        if df is None or df.empty or "Close" not in df.columns:
            return None
        close = df["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.squeeze("columns")
        s = close.dropna().astype(float)
        return s.rename("Gold")

    s = try_dl(PRIMARY_TICKER)
    if s is not None and not s.empty:
        print(f"[Gold] using {PRIMARY_TICKER} (rows={len(s)})"); return s
    for t in FALLBACKS:
        s = try_dl(t)
        if s is not None and not s.empty:
            print(f"[Gold] fallback used: {t} (rows={len(s)})"); return s
    raise RuntimeError("Unable to download gold prices via any ticker.")

def ensure_template_csv():
    """Create a simple template if missing."""
    if os.path.exists(FORECASTS_CSV):
        return False
    rows = []
    for bank in ["Goldman Sachs","J.P. Morgan","HSBC"]:
        for y in range(2010, 2026):
            rows.append({"bank": bank, "date": f"{y}-12-31", "price": "", "label": ""})
    pd.DataFrame(rows, columns=["bank","date","price","label"]).to_csv(FORECASTS_CSV, index=False)
    print(f"Template created → {FORECASTS_CSV}")
    return True

def load_csv():
    created = ensure_template_csv()
    df = pd.read_csv(FORECASTS_CSV, dtype=str)
    for col in ["bank","date","price","label"]:
        if col not in df.columns: df[col] = ""
    df["bank"] = df["bank"].fillna("").str.strip()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["label"] = df["label"].fillna("")
    if created:
        print("Tip: you can type prices as 2500, 2,500, or $2,500.")
    return df

def append_media_rows_if_missing(df: pd.DataFrame):
    """Append MEDIA_ENTRIES if not present (same bank+date considered duplicate)."""
    before = len(df)
    df2 = df.copy()
    # normalize for comparison
    df2["_key"] = df2["bank"].str.strip() + "|" + df2["date"].dt.strftime("%Y-%m-%d")
    for row in MEDIA_ENTRIES:
        bank = row["bank"].strip()
        d    = pd.to_datetime(row["date"], errors="coerce")
        key  = f"{bank}|{d:%Y-%m-%d}"
        if key not in set(df2["_key"].dropna()):
            df2 = pd.concat([df2, pd.DataFrame([{
                "bank": bank, "date": d, "price": str(row["price"]), "label": row.get("label","")
            }])], ignore_index=True)
    df2 = df2.drop(columns=["_key"], errors="ignore")
    if len(df2) != before:
        df2.to_csv(FORECASTS_CSV, index=False, date_format="%Y-%m-%d")
        print(f"Appended {len(df2)-before} media-quoted forecast row(s) → {FORECASTS_CSV}")
    return df2

_price_cleaner = re.compile(r"[^0-9.\-]")  # keep digits/dot/minus

def parse_price(s: str) -> float:
    if s is None: return np.nan
    t = str(s).strip()
    if t == "":  return np.nan
    t2 = _price_cleaner.sub("", t)
    if not re.search(r"[0-9]", t2): return np.nan
    try: return float(t2)
    except: return np.nan

def nearest_close(series: pd.Series, target: pd.Timestamp, window_days=7):
    if pd.isna(target): return None, None
    start, end = target - pd.Timedelta(days=window_days), target + pd.Timedelta(days=window_days)
    clip = series.loc[(series.index >= start) & (series.index <= end)]
    if clip.empty: return None, None
    idx = clip.index[np.argmin(np.abs(clip.index - target))]
    return idx, float(clip.loc[idx])

def autofill_only_blanks(df: pd.DataFrame, gold: pd.Series):
    """Fill only truly blank price cells from market close near date."""
    out = df.copy()
    filled = 0
    for i, row in out.iterrows():
        p = parse_price(row.get("price",""))
        if not np.isnan(p):
            out.at[i,"price"] = f"{p:.2f}"
            continue
        d = row["date"]
        nd, npv = nearest_close(gold, d, AUTOFILL_WINDOW_DAYS)
        if nd is not None:
            out.at[i,"price"] = f"{npv:.2f}"
            if not out.at[i,"label"]:
                out.at[i,"label"] = "autofilled from market"
            filled += 1
    if filled:
        out.to_csv(FORECASTS_CSV, index=False, date_format="%Y-%m-%d")
        print(f"Autofilled {filled} blank price(s) from Yahoo → {FORECASTS_CSV}")
    return out

# ---------------- Run ----------------
gold = download_gold_series()
df   = load_csv()
df   = append_media_rows_if_missing(df)

# filter to window and keep usable rows
df = df[(df["date"] >= SINCE_DATE) & (df["date"] <= UNTIL_DATE)]
df = autofill_only_blanks(df, gold)

# numeric price
df["price_num"] = df["price"].apply(parse_price)
forecasts = df.dropna(subset=["price_num"]).sort_values("date")

# ---------------- Plot (markers only) ----------------
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI, layout="constrained")
if LOG_SCALE: ax.set_yscale("log")

ax.plot(gold.index, gold, lw=1.8, color="goldenrod", label="Gold (USD/oz)")
ax.set_xlim(SINCE_DATE, UNTIL_DATE)
ax.set_title("Gold Price (2010–2025) — Bank & Media-Quoted Forecast Markers")
ax.set_xlabel("Date")
ax.set_ylabel(f"Gold (USD/oz){' [log]' if LOG_SCALE else ''}")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

ax.xaxis.set_major_locator(mdates.AutoDateLocator())
ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
ax.grid(True, color="lightgray", linestyle="--", alpha=0.5)

# plot markers; no text
legend_handles = {}
for _, row in forecasts.iterrows():
    bank, d, price = row["bank"], row["date"], float(row["price_num"])
    style = BANK_STYLE.get(bank, dict(color="crimson", marker="o"))
    c, m  = style["color"], style["marker"]
    sc = ax.scatter([d], [price], color=c, edgecolor="black", s=52, marker=m, zorder=5)
    ax.annotate(
        f"{price:.0f}",
        xy=(d, price),
        xytext=(0, 10),
        textcoords="offset points",
        color=c,
        fontsize=10,
        ha="center",
        zorder=6
        )    
    if SHOW_GUIDE_LINES:
        xmin = max(gold.index.min(), d - pd.DateOffset(years=2))
        ax.hlines(price, xmin=xmin, xmax=d, colors=c, linestyles=":", alpha=0.35, linewidth=1.0)
    if bank not in legend_handles:
        legend_handles[bank] = sc

if legend_handles:
    ax.legend(legend_handles.values(), legend_handles.keys(),
              loc="upper left", title="Sources (bank / media)")

plt.savefig(SAVE_PNG, dpi=DPI)
plt.show()

print(f"Saved chart → {SAVE_PNG}")
print(f"Forecast markers plotted: {len(forecasts)}")
print(f"CSV used → {FORECASTS_CSV}")