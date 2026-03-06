#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gold monthly returns dashboard (last 30 years)
- Robust yfinance fetch with fallbacks
- Calendar-month average returns bar chart
- Cumulative price (log optional)
- Monthly return heatmap
- Saves one PNG
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.colors import TwoSlopeNorm
import yfinance as yf

# ---------------- Config ----------------
TICKER_CANDIDATES = ["GC=F", "XAUUSD=X", "IAU"]   # futures, spot, ETF fallback
YEARS_BACK = 30
USE_LOG_PRICE = True
OUTFILE = "gold_monthly_returns_30y.png"

# ---------------- Helpers ----------------
def _as_close_series(df, name="Gold"):
    """Normalize yfinance df to a single Close-price Series with clean DatetimeIndex."""
    if df is None or df.empty:
        return None
    close = df.get("Close", None)
    if close is None:
        close = df.get("Adj Close", None)
        if close is None:
            return None
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0] if close.shape[1] > 1 else close.squeeze("columns")
    s = pd.Series(close).dropna().astype(float)
    s.index = pd.to_datetime(s.index)
    s = s[~s.index.duplicated(keep="last")].sort_index()
    s.name = name
    return s if not s.empty else None

def download_gold():
    end = pd.Timestamp.today().normalize()
    start = end - pd.DateOffset(years=YEARS_BACK)
    for t in TICKER_CANDIDATES:
        try:
            print(f"Trying {t} …", flush=True)
            df = yf.download(
                t, start=start, end=end + pd.Timedelta(days=1),
                interval="1d", auto_adjust=True, progress=False,
                group_by="column", threads=False
            )
            s = _as_close_series(df, name="Gold")
            if s is not None and len(s) > 200:
                print(f"Using {t} (rows={len(s)})")
                return s
            else:
                print(f"Skipped {t}: empty or too few rows")
        except Exception as e:
            print(f"Failed {t}: {type(e).__name__}: {e}")
            continue
    raise RuntimeError("No gold data available from Yahoo Finance")

def monthly_returns(series: pd.Series) -> pd.Series:
    m = series.resample("MS").last().dropna()   # month-start stamps
    return m.pct_change().dropna()

def build_month_table(ret_m: pd.Series) -> (pd.DataFrame, pd.Series):
    df = ret_m.to_frame("ret")
    df["Year"] = df.index.year
    df["Month"] = df.index.month
    heat = df.pivot(index="Year", columns="Month", values="ret").sort_index()
    avg_by_month = heat.mean(axis=0).rename("avg")
    return heat, avg_by_month

# ---------------- Main ----------------
def main():
    gold = download_gold()

    # Monthly % returns
    ret_m = monthly_returns(gold)
    if ret_m.empty:
        raise RuntimeError("Monthly returns are empty — not enough data?")

    heat, avg_by_month = build_month_table(ret_m)

    # Align the price panel to the returns window (use ret_m index which is datetime)
    price = gold[gold.index >= ret_m.index.min()].copy()

    # -------- Plotting --------
    plt.close("all")
    fig = plt.figure(figsize=(14, 10), dpi=160)
    gs = fig.add_gridspec(3, 1, height_ratios=[1.1, 1.3, 1.6], hspace=0.18)

    # (1) Calendar-month average returns bar
    ax1 = fig.add_subplot(gs[0, 0])
    months = range(1, 13)
    month_labels = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    avg_vals = (avg_by_month.reindex(months).values * 100.0)
    bars = ax1.bar(months, avg_vals, width=0.8)
    ax1.axhline(0, color="black", linewidth=0.8, alpha=0.6)
    ax1.set_xticks(months, month_labels, rotation=0)
    ax1.set_ylabel("Avg monthly return (%)")
    ax1.set_title(f"Gold — Average calendar-month return (last {YEARS_BACK} years)")
    for b in bars:
        b.set_color("#2ca02c" if b.get_height() >= 0 else "#d62728")

    # (2) Cumulative price
    ax2 = fig.add_subplot(gs[1, 0])
    if USE_LOG_PRICE:
        ax2.set_yscale("log")
        ax2.set_ylabel("Gold (USD/oz) [log]")
    else:
        ax2.set_ylabel("Gold (USD/oz)")
    ax2.plot(price.index, price.values, color="goldenrod", lw=1.8)
    ax2.set_title("Gold cumulative price")
    ax2.grid(True, alpha=0.25)
    ax2.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax2.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax2.xaxis.get_major_locator()))

    # (3) Heatmap of monthly returns by year
    ax3 = fig.add_subplot(gs[2, 0])
    heat_disp = heat.reindex(columns=range(1, 13))
    norm = TwoSlopeNorm(
        vmin=np.nanpercentile(heat_disp.values, 5),
        vcenter=0.0,
        vmax=np.nanpercentile(heat_disp.values, 95)
    )
    im = ax3.imshow(heat_disp.values * 100.0, aspect="auto", cmap="RdYlGn", norm=norm)
    ax3.set_xticks(np.arange(12))
    ax3.set_xticklabels(month_labels, rotation=0)
    years = heat_disp.index.values
    ax3.set_yticks(np.arange(len(years)))
    ax3.set_yticklabels(years)
    ax3.set_xlabel("Month")
    ax3.set_title("Gold monthly returns heatmap (%)")
    cbar = fig.colorbar(im, ax=ax3, orientation="vertical", fraction=0.025, pad=0.02)
    cbar.set_label("% return")

    fig.suptitle(f"Gold monthly statistics — {YEARS_BACK} years", fontsize=14, y=0.99)
    plt.tight_layout()
    plt.savefig(OUTFILE, dpi=200)
    plt.show()
    print(f"Saved plot → {OUTFILE}")

if __name__ == "__main__":
    main()