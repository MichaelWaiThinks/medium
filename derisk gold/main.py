#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gold: 2011–2012 vs Recent (normalized overlay) + Blow-off Risk + Partial De-risk Plan

What this script does:
1) Downloads daily gold data (GC=F by default)
2) Compares:
   - 2011–2012 window (reference mania-ish era)
   - Recent window (last N calendar days ending at END_DATE)
3) Normalizes both windows to the same scale and overlays them by "days since window start"
4) Builds a "Blow-off Risk" indicator from:
   - Return acceleration (slope z-score)
   - Distance-from-trend (price vs MA z-score)
   - Trend persistence (share of up-days)
   - Optional: RSI (overbought pressure)
5) Ties risk score to a simple partial de-risking plan (sell % tiers)

Notes:
- This is quantitative pattern analysis, not financial advice.
- If Yahoo data has gaps, windows may have fewer points.

Change END_DATE below to e.g. "2012-12-31" or leave None for today.
"""

import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

# ---------------------- CONFIG ----------------------
TICKER = "GC=F"

# Comparison windows
HIST_START = "2011-01-01"
HIST_END   = "2012-12-31"

END_DATE = "2026-01-20"   # <-- change this (e.g. "2012-12-31"); set None for today
RECENT_DAYS = 365         # calendar days to include for "recent" window

# Indicator parameters
MA_LEN = 50               # moving average for "distance-from-trend"
SLOPE_Z_WIN = 60          # rolling window for slope z-score
DIST_Z_WIN = 60           # rolling window for distance z-score
UPDAY_WIN = 20            # rolling window for up-day persistence
RSI_LEN = 14              # RSI length

# Risk score weights (sum doesn't need to be 1; we normalize)
W_SLOPE = 0.35
W_DIST  = 0.35
W_UPDAY = 0.15
W_RSI   = 0.15

# De-risk tiers (risk score 0..1)
DERISK_TIERS = [
    (0.85, 0.30),  # risk >= 0.85 -> sell 30% of remaining position
    (0.75, 0.20),  # risk >= 0.75 -> sell 20%
    (0.65, 0.10),  # risk >= 0.65 -> sell 10%
    (0.55, 0.05),  # risk >= 0.55 -> sell  5%
]

# Plot
FIGSIZE = (14, 10)
SAVE_PNG = "gold_2011_vs_recent_normalized_blowoff_derisk.png"
# ----------------------------------------------------


# ---------------------- Helpers ----------------------
def download_close(ticker: str, start: str, end: str | None) -> pd.Series:
    end_ts = pd.Timestamp.today().normalize() if end is None else pd.Timestamp(end)
    df = yf.download(ticker, start=start, end=end_ts + pd.Timedelta(days=1), progress=False)
    if df is None or df.empty or "Close" not in df.columns:
        raise RuntimeError("No data returned from Yahoo Finance.")

    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    s = close.dropna().astype(float)
    s.index = pd.to_datetime(s.index)
    return s.sort_index().rename("Close")


def zscore_rolling(x: pd.Series, win: int) -> pd.Series:
    mu = x.rolling(win, min_periods=max(10, win//3)).mean()
    sd = x.rolling(win, min_periods=max(10, win//3)).std(ddof=0)
    return (x - mu) / (sd.replace(0, np.nan))


def rsi(series: pd.Series, length: int = 14) -> pd.Series:
    d = series.diff()
    up = d.clip(lower=0.0)
    dn = (-d).clip(lower=0.0)
    # Wilder's smoothing (EMA alpha=1/length)
    roll_up = up.ewm(alpha=1/length, adjust=False).mean()
    roll_dn = dn.ewm(alpha=1/length, adjust=False).mean()
    rs = roll_up / roll_dn.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def normalize_to_100(s: pd.Series) -> pd.Series:
    if s.empty:
        return s
    return (s / float(s.iloc[0]) * 100.0).rename(s.name)


def window_by_calendar_days(df: pd.DataFrame, end_dt: pd.Timestamp, days: int) -> pd.DataFrame:
    start_dt = end_dt - pd.Timedelta(days=days)
    return df.loc[start_dt:end_dt].copy()


def overlay_by_day_index(s: pd.Series) -> pd.Series:
    """
    Return a Series indexed by integer day-from-start (0..n-1), values = series values.
    """
    vals = s.to_numpy()
    idx = np.arange(len(vals))
    out = pd.Series(vals, index=idx, name=s.name)
    return out


def squash_to_0_1(x: pd.Series, clip_lo=-3.0, clip_hi=3.0) -> pd.Series:
    """
    Convert roughly z-score-like series into 0..1.
    """
    z = x.clip(clip_lo, clip_hi)
    return (z - clip_lo) / (clip_hi - clip_lo)


def build_blowoff_risk(df: pd.DataFrame) -> pd.DataFrame:
    """
    Inputs df must contain Close.
    Adds:
      - Slope (delta)
      - Pct (daily %)
      - Dist (Close/MA - 1)
      - z-scores
      - UpDay persistence
      - RSI
      - BlowOffRisk (0..1)
    """
    out = df.copy()

    out["Slope"] = out["Close"].diff()
    out["Pct"] = out["Close"].pct_change() * 100.0

    out["MA"] = out["Close"].rolling(MA_LEN, min_periods=max(10, MA_LEN//3)).mean()
    out["Dist"] = (out["Close"] / out["MA"] - 1.0) * 100.0  # % above MA

    out["Slope_z"] = zscore_rolling(out["Slope"], SLOPE_Z_WIN)
    out["Dist_z"]  = zscore_rolling(out["Dist"],  DIST_Z_WIN)

    upday = (out["Close"].diff() > 0).astype(float)
    out["UpDayRate"] = upday.rolling(UPDAY_WIN, min_periods=max(5, UPDAY_WIN//2)).mean()  # 0..1

    out["RSI"] = rsi(out["Close"], RSI_LEN)

    # Convert components to 0..1 risk sub-scores
    # 1) slope accel risk (high positive slope_z -> higher risk)
    slope_r = squash_to_0_1(out["Slope_z"])

    # 2) distance-from-trend risk (far above MA -> higher risk)
    dist_r = squash_to_0_1(out["Dist_z"])

    # 3) persistence risk (many up days in a row -> "blow-off" feel)
    # Map UpDayRate: 0.5 is neutral; 0.8 is high.
    up_r = ((out["UpDayRate"] - 0.50) / (0.85 - 0.50)).clip(0, 1)

    # 4) RSI risk: 50 neutral; 80 high.
    rsi_r = ((out["RSI"] - 50.0) / (80.0 - 50.0)).clip(0, 1)

    # Weighted blend
    wsum = (W_SLOPE + W_DIST + W_UPDAY + W_RSI)
    out["BlowOffRisk"] = (
        W_SLOPE * slope_r +
        W_DIST  * dist_r +
        W_UPDAY * up_r +
        W_RSI   * rsi_r
    ) / (wsum if wsum != 0 else 1.0)

    return out


def derisk_recommendation(risk: float) -> str:
    """
    Suggest how much to sell of remaining position right now based on risk.
    """
    for thr, sell_frac in DERISK_TIERS:
        if risk >= thr:
            return f"Risk {risk:.2f} ≥ {thr:.2f}: sell {int(sell_frac*100)}% of remaining position"
    return f"Risk {risk:.2f}: no forced sell (or keep small trimming rule)"


# ---------------------- Main ----------------------
def main():
    end_ts = pd.Timestamp.today().normalize() if END_DATE is None else pd.Timestamp(END_DATE)
    start_ts = pd.Timestamp(HIST_START)

    close = download_close(TICKER, start=str(start_ts.date()), end=str(end_ts.date()))
    df = close.to_frame()

    # Windows
    hist = df.loc[pd.Timestamp(HIST_START):pd.Timestamp(HIST_END)].copy()
    recent = window_by_calendar_days(df, end_ts, RECENT_DAYS)

    if hist.empty:
        raise RuntimeError("Historical window is empty. Check HIST_START/HIST_END.")
    if recent.empty:
        raise RuntimeError("Recent window is empty. Check END_DATE/RECENT_DAYS.")

    # Build indicators per window
    hist_i = build_blowoff_risk(hist)
    recent_i = build_blowoff_risk(recent)

    # Normalize prices to same starting point and overlay by day-index
    hist_norm = normalize_to_100(hist_i["Close"]).rename("Hist (2011–2012) normalized")
    recent_norm = normalize_to_100(recent_i["Close"]).rename("Recent normalized")

    hist_overlay = overlay_by_day_index(hist_norm)
    recent_overlay = overlay_by_day_index(recent_norm)

    # For a comparable "speed" overlay, normalize slope by starting price (bps-ish)
    # slope_norm = (delta / start_price) * 100 => % of start price per day
    hist_slope_norm = (hist_i["Slope"] / float(hist_i["Close"].iloc[0]) * 100.0).rename("Hist slope (% of start)")
    recent_slope_norm = (recent_i["Slope"] / float(recent_i["Close"].iloc[0]) * 100.0).rename("Recent slope (% of start)")

    hist_slope_overlay = overlay_by_day_index(hist_slope_norm.dropna())
    recent_slope_overlay = overlay_by_day_index(recent_slope_norm.dropna())

    # Latest risk + de-risk plan
    latest_risk = float(recent_i["BlowOffRisk"].dropna().iloc[-1]) if recent_i["BlowOffRisk"].notna().any() else np.nan
    plan_text = derisk_recommendation(latest_risk) if np.isfinite(latest_risk) else "Risk unavailable (insufficient data)"

    # Compare distributions (optional quick stats)
    stats = {
        "Hist avg risk": float(hist_i["BlowOffRisk"].mean()),
        "Recent avg risk": float(recent_i["BlowOffRisk"].mean()),
        "Recent latest risk": float(latest_risk),
        "Hist max risk": float(hist_i["BlowOffRisk"].max()),
        "Recent max risk": float(recent_i["BlowOffRisk"].max()),
    }

    # ---------------------- Plot ----------------------
    fig, axes = plt.subplots(4, 1, figsize=FIGSIZE, sharex=False)

    # 1) Raw price with highlighted windows
    axes[0].plot(df.index, df["Close"], lw=1.6, label="Gold (Close)")
    axes[0].axvspan(pd.Timestamp(HIST_START), pd.Timestamp(HIST_END), alpha=0.18, label="2011–2012 window")
    axes[0].axvspan(recent.index.min(), recent.index.max(), alpha=0.10, label=f"Recent {RECENT_DAYS}d window")
    axes[0].set_title(f"{TICKER} Gold Price + Windows (END_DATE={end_ts.date()})")
    axes[0].set_ylabel("USD/oz")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="upper left")

    # 2) Normalized overlay (same scale)
    axes[1].plot(hist_overlay.index, hist_overlay.values, lw=1.8, label="2011–2012 (start=100)")
    axes[1].plot(recent_overlay.index, recent_overlay.values, lw=1.8, label="Recent (start=100)")
    axes[1].set_title("Normalized Overlay by Days-from-Start (same scale)")
    axes[1].set_ylabel("Normalized (start=100)")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="upper left")

    # 3) Normalized slope overlay (speed)
    axes[2].plot(hist_slope_overlay.index, hist_slope_overlay.values, lw=1.2, alpha=0.9, label="2011–2012 daily delta (% of start)")
    axes[2].plot(recent_slope_overlay.index, recent_slope_overlay.values, lw=1.2, alpha=0.9, label="Recent daily delta (% of start)")
    axes[2].axhline(0, lw=1.0, linestyle="--", alpha=0.6)
    axes[2].set_title("Normalized Daily Slope Overlay (speed proxy)")
    axes[2].set_ylabel("% of start price/day")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend(loc="upper left")

    # 4) Blow-off risk in each window (0..1) + plan
    axes[3].plot(hist_i.index, hist_i["BlowOffRisk"], lw=1.4, label="Hist blow-off risk (0..1)")
    axes[3].plot(recent_i.index, recent_i["BlowOffRisk"], lw=1.8, label="Recent blow-off risk (0..1)")
    for thr, _sell in DERISK_TIERS:
        axes[3].axhline(thr, linestyle="--", lw=1.0, alpha=0.5)
        axes[3].annotate(f"Tier {thr:.2f}", xy=(recent_i.index.max(), thr),
                         xytext=(-6, 0), textcoords="offset points",
                         ha="right", va="center", fontsize=8,
                         bbox=dict(fc="white", ec="none", alpha=0.6))
    axes[3].set_ylim(-0.05, 1.05)
    axes[3].set_title("Blow-off Risk Indicator (0..1) + De-risk tiers")
    axes[3].set_ylabel("Risk score")
    axes[3].grid(True, alpha=0.3)
    axes[3].legend(loc="upper left")

    # Add plan text box
    axes[3].annotate(
        f"Partial de-risk plan (today):\n{plan_text}",
        xy=(0.01, 0.05), xycoords="axes fraction",
        ha="left", va="bottom", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="black", alpha=0.85)
    )

    plt.tight_layout()
    plt.savefig(SAVE_PNG, dpi=180)
    plt.show()

    # ---------------------- Console output ----------------------
    print("\n=== Quick stats ===")
    for k, v in stats.items():
        print(f"{k:>18s}: {v:.3f}")

    print("\n=== What the blow-off risk is measuring ===")
    print("• Slope acceleration: big positive daily moves vs its own recent history (z-score).")
    print("• Distance from trend: how far price is above its MA (z-score).")
    print("• Persistence: unusual streakiness (high fraction of up-days).")
    print("• RSI: overbought pressure as a supporting feature.")
    print("\n=== Partial de-risk plan (simple tiers) ===")
    print(plan_text)
    print(f"\nSaved -> {SAVE_PNG}")


if __name__ == "__main__":
    main()