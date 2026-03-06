#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gold vs Silver: Divergence + Ratio Bands + Cycle-V Zones + Drawdown Backtests (Monthly)
PLUS: Gold/SP500 and Silver/SP500 ratio subplot (twin y-axis)

Outputs:
  - gold_silver_divergence_cycleV_backtest.png
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker

# ---------------- Config ----------------
YEARS_BACK = 100
SAVE_PNG = "gold_silver_divergence_cycleV_backtest.png"

# Download tickers (spot may fail; futures fallback)
GOLD_TICKERS   = ["XAUUSD=X", "GC=F", "XAU=X", "IAU"]
SILVER_TICKERS = ["XAGUSD=X", "SI=F", "SLV"]
SPX_TICKERS    = ["^GSPC", "SPY"]   # fallback to SPY if ^GSPC fails

# Date range
START_DATE = None# "2008-01-01"               # leave None to use YEARS_BACK from END_DATE
END_DATE   = None #"2011-09-01"       # set None for today, or e.g. "2012-12-31"

# Monthly processing
RESAMPLE = "D"          # month-end
SWING_WIN = 15
MATCH_TOL_MONTHS = 2*15

SILVER_CONFIRM_TOL = 0.00

# Cycle-V zones (auto I–V impulse via ZigZag pivots on monthly Gold)
ZZ_PCT = 10.0
STRICT_NO_OVERLAP = True
TOL_PX = 0.002
TOL_LEN = 0.10

V_MULTS = [1.00, 1.272, 1.618]
STRETCH_MAX_MULT = 2.00

# Backtest
DD_HORIZON_MONTHS = 12
NEXT_SWING_WAIT_MONTHS = 6
DD_THRESHOLD = 0.20  # 30%

# Plot formatting
FIGSIZE = (16, 14)
DPI = 180
LOG_SCALE = False

GOLD_TICK_STEP = 500
SILVER_TICK_STEP = 10


# ---------------- Utilities ----------------
def _download_close_any(tickers, start, end, name):
    last_err = None
    for t in tickers:
        try:
            print(f"[{name}] Trying {t} …")
            df = yf.download(
                t, start=start, end=end + pd.Timedelta(days=1),
                interval="1d", auto_adjust=True, progress=False, group_by="column", threads=False
            )
            if df is None or df.empty or "Close" not in df.columns:
                print(f"[{name}] {t} empty/failed, trying next…")
                continue
            close = df["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.squeeze("columns")
            s = close.dropna().astype(float)
            if s.empty:
                print(f"[{name}] {t} returned empty series, trying next…")
                continue
            s.index = pd.to_datetime(s.index)
            print(f"[{name}] Using {t} (rows={len(s)})")
            return s.rename(name)
        except Exception as e:
            last_err = e
            print(f"[{name}] Failed {t}: {e}")
    raise RuntimeError(f"No {name} data available. Last error: {last_err}")


def to_monthly_last(s: pd.Series) -> pd.Series:
    s = s.copy()
    s.index = pd.to_datetime(s.index)
    s = s.sort_index()
    return s.resample(RESAMPLE).last().dropna()


def swings(series: pd.Series, win: int):
    x = series.astype(float)
    roll_max = x.rolling(window=2*win+1, center=True).max()
    roll_min = x.rolling(window=2*win+1, center=True).min()
    is_high = (x == roll_max) & roll_max.notna()
    is_low  = (x == roll_min) & roll_min.notna()
    return is_high, is_low


def nearest_date_idx(index: pd.DatetimeIndex, target: pd.Timestamp, tol_months: int):
    if target is pd.NaT:
        return None
    lo = target - pd.DateOffset(months=tol_months)
    hi = target + pd.DateOffset(months=tol_months)
    candidates = index[(index >= lo) & (index <= hi)]
    if len(candidates) == 0:
        return None
    deltas = np.abs((candidates - target).to_numpy(dtype="timedelta64[D]").astype(int))
    return candidates[int(np.argmin(deltas))]


# ---------------- ZigZag pivots (monthly) for Cycle detection ----------------
def zigzag(series: pd.Series, pct: float = 10.0) -> pd.DataFrame:
    s = series.dropna().astype(float)
    if s.empty:
        return pd.DataFrame(columns=["Price", "Pol"])

    p_last = float(s.iloc[0])
    i_last = s.index[0]
    trend = 0
    pivots = [(i_last, p_last)]

    for i, p in s.iloc[1:].items():
        p = float(p)
        chg = (p - p_last) / p_last * 100.0 if p_last != 0 else 0.0

        if trend >= 0:
            if chg >= 0:
                p_last, i_last = p, i
                pivots[-1] = (i_last, p_last)
            elif chg <= -pct:
                pivots.append((i, p))
                p_last, i_last = p, i
                trend = -1

        if trend <= 0:
            if chg <= 0:
                p_last, i_last = p, i
                pivots[-1] = (i_last, p_last)
            elif chg >= pct:
                pivots.append((i, p))
                p_last, i_last = p, i
                trend = +1

    piv_df = pd.DataFrame(pivots, columns=["Date", "Price"]).drop_duplicates("Date").set_index("Date")
    piv_df = piv_df.sort_index()

    pol = []
    px = piv_df["Price"].to_numpy()
    for k in range(len(piv_df)):
        p = px[k]
        pl = px[k-1] if k-1 >= 0 else p
        pr = px[k+1] if k+1 < len(px) else p
        if p <= pl and p <= pr:
            pol.append("low")
        elif p >= pl and p >= pr:
            pol.append("high")
        else:
            pol.append("flat")
    piv_df["Pol"] = pol
    piv_df = piv_df[piv_df["Pol"].isin(["low","high"])].copy()
    return piv_df


def is_valid_impulse(p1, p2, p3, p4, p5, p6,
                     tol_px=0.002, tol_len=0.10, no_overlap=True):
    if not (p2*(1+tol_px) < p4 and p4*(1+tol_px) < p6):
        return False
    if not (p1*(1+tol_px) < p3 and p3*(1+tol_px) < p5):
        return False
    if no_overlap and not (p5 > p2*(1 - tol_px)):
        return False
    len1, len3, len5 = (p2 - p1), (p4 - p3), (p6 - p5)
    if min(len1, len3, len5) <= 0:
        return False
    if len3 < min(len1, len5) * (1 - tol_len):
        return False
    return True


def extract_best_cycle_from_pivots(piv: pd.DataFrame):
    if piv.empty:
        return None
    seq = [(dt, float(row.Price), row.Pol) for dt, row in piv.iterrows()]
    n = len(seq)
    candidates = []

    i = 0
    while i < n:
        while i < n and seq[i][2] != "low":
            i += 1
        if i >= n:
            break

        need = ["low","high","low","high","low","high"]
        picked = []
        j = i
        for want in need:
            found = None
            while j < n:
                dt, px, pol = seq[j]
                j += 1
                if pol == want:
                    found = (dt, px, pol, j-1)
                    break
            if found is None:
                picked = []
                break
            picked.append(found)

        if len(picked) == 6:
            (d1,p1,_,i1),(d2,p2,_,i2),(d3,p3,_,i3),(d4,p4,_,i4),(d5,p5,_,i5),(d6,p6,_,i6) = picked
            years = (d6 - d1).days / 365.25
            gain  = (p6 / p1) - 1.0 if p1 > 0 else 0.0
            if is_valid_impulse(p1,p2,p3,p4,p5,p6, tol_px=TOL_PX, tol_len=TOL_LEN, no_overlap=STRICT_NO_OVERLAP):
                score = years * (1.0 + gain)
                candidates.append(dict(
                    I_low=(d1,p1), I_high=(d2,p2), II_low=(d3,p3),
                    III_high=(d4,p4), IV_low=(d5,p5), V_high=(d6,p6),
                    years=years, gain=gain, score=score
                ))
            i = i6 + 1
        else:
            i += 1

    if not candidates:
        return None
    return max(candidates, key=lambda x: x["score"])


def cycle_v_bands(cycle):
    if cycle is None:
        return None

    iv_low = cycle["IV_low"][1]
    i_low  = cycle["I_low"][1]
    i_high = cycle["I_high"][1]
    ii_low = cycle["II_low"][1]
    iii_hi = cycle["III_high"][1]

    len_I   = max(0.0, i_high - i_low)
    len_III = max(0.0, iii_hi - ii_low)
    if len_III <= 0:
        return None

    t1 = iv_low + V_MULTS[0] * len_III
    t2 = iv_low + V_MULTS[1] * len_III
    t3 = iv_low + V_MULTS[2] * len_III
    t4 = iv_low + STRETCH_MAX_MULT * len_III

    return {
        "under_run": (min(t1,t2), max(t1,t2)),
        "base":      (min(t2,t3), max(t2,t3)),
        "stretch":   (min(t3,max(t4,t3)), max(t3,max(t4,t3))),
    }


# ---------------- Divergence detection ----------------
def draw_divergence_arrows(ax_gold, ax_silver,
                           g_prev_dt, g_prev, g_dt, g,
                           s_prev_dt, s_prev, s_dt, s,
                           kind="bear"):
    """
    Draw arrows + explicit FROM/TO markers on both axes:
      - Gold markers+arrow on ax_gold (left)
      - Silver markers+arrow on ax_silver (right)
    """

    if kind == "bear":
        c = "crimson"
        gold_txt = "Gold HH"
        silv_txt = "Silver LH"
        m_from, m_to = "o", "v"   # from=dot, to=down-triangle
    else:
        c = "green"
        gold_txt = "Gold LL"
        silv_txt = "Silver HL"
        m_from, m_to = "o", "^"   # from=dot, to=up-triangle

    # --- GOLD: markers (from/to) ---
    ax_gold.scatter([g_prev_dt], [g_prev], s=60, marker=m_from,
                    color=c, edgecolor="black", zorder=9)
    ax_gold.scatter([g_dt], [g], s=70, marker=m_to,
                    color=c, edgecolor="black", zorder=10)

    # GOLD arrow
    ax_gold.annotate(
        "", xy=(g_dt, g), xytext=(g_prev_dt, g_prev),
        arrowprops=dict(arrowstyle="->", lw=1.6, color=c, alpha=0.9),
        zorder=8
    )
    ax_gold.annotate(
        gold_txt,
        xy=(g_dt, g),
        xytext=(8, 8), textcoords="offset points",
        fontsize=8, color=c,
        bbox=dict(fc="white", ec="none", alpha=0.65),
        zorder=11
    )

    # --- SILVER: markers (from/to) ---
    ax_silver.scatter([s_prev_dt], [s_prev], s=60, marker=m_from,
                      color=c, edgecolor="black", zorder=9)
    ax_silver.scatter([s_dt], [s], s=70, marker=m_to,
                      color=c, edgecolor="black", zorder=10)

    # SILVER arrow
    ax_silver.annotate(
        "", xy=(s_dt, s), xytext=(s_prev_dt, s_prev),
        arrowprops=dict(arrowstyle="->", lw=1.6, color=c, alpha=0.9),
        zorder=8
    )
    ax_silver.annotate(
        silv_txt,
        xy=(s_dt, s),
        xytext=(8, -14), textcoords="offset points",
        fontsize=8, color=c,
        bbox=dict(fc="white", ec="none", alpha=0.65),
        zorder=11
    )
    
def detect_divergences(df: pd.DataFrame):
    gold = df["Gold"]
    silver = df["Silver"]

    g_hi, g_lo = swings(gold, SWING_WIN)
    s_hi, s_lo = swings(silver, SWING_WIN)

    gold_high_dates = gold.index[g_hi]
    gold_low_dates  = gold.index[g_lo]

    bear_dates, bull_dates = [], []
    bear_arrows, bull_arrows = [], []   # <-- NEW

    prev_g_high = prev_s_high = None
    prev_g_high_dt = prev_s_high_dt = None

    for d in gold_high_dates:
        sd = nearest_date_idx(silver.index[s_hi], d, MATCH_TOL_MONTHS)
        if sd is None:
            continue

        gpx = float(gold.loc[d])
        spx = float(silver.loc[sd])

        if prev_g_high is not None and prev_s_high is not None:
            if gpx > prev_g_high and spx < prev_s_high * (1.0 + SILVER_CONFIRM_TOL):
                bear_dates.append(d)
                bear_arrows.append(dict(
                    g_prev_dt=prev_g_high_dt, g_prev=prev_g_high,
                    g_dt=d, g=gpx,
                    s_prev_dt=prev_s_high_dt, s_prev=prev_s_high,
                    s_dt=sd, s=spx
                ))

        prev_g_high, prev_s_high = gpx, spx
        prev_g_high_dt, prev_s_high_dt = d, sd

    prev_g_low = prev_s_low = None
    prev_g_low_dt = prev_s_low_dt = None

    for d in gold_low_dates:
        sd = nearest_date_idx(silver.index[s_lo], d, MATCH_TOL_MONTHS)
        if sd is None:
            continue

        gpx = float(gold.loc[d])
        spx = float(silver.loc[sd])

        if prev_g_low is not None and prev_s_low is not None:
            if gpx < prev_g_low and spx > prev_s_low * (1.0 - SILVER_CONFIRM_TOL):
                bull_dates.append(d)
                bull_arrows.append(dict(
                    g_prev_dt=prev_g_low_dt, g_prev=prev_g_low,
                    g_dt=d, g=gpx,
                    s_prev_dt=prev_s_low_dt, s_prev=prev_s_low,
                    s_dt=sd, s=spx
                ))

        prev_g_low, prev_s_low = gpx, spx
        prev_g_low_dt, prev_s_low_dt = d, sd

    return (
        pd.DatetimeIndex(sorted(set(bear_dates))),
        pd.DatetimeIndex(sorted(set(bull_dates))),
        bear_arrows,
        bull_arrows
    )


# ---------------- Backtests ----------------
def forward_drawdown(prices: pd.Series, start_date: pd.Timestamp, horizon_months: int):
    if start_date not in prices.index:
        return None
    start_px = float(prices.loc[start_date])
    end_date = start_date + pd.DateOffset(months=horizon_months)
    window = prices.loc[start_date:end_date].dropna()
    if window.empty or start_px <= 0:
        return None
    min_px = float(window.min())
    dd = (start_px - min_px) / start_px
    return start_px, min_px, dd


def next_swing_high_date(series: pd.Series, after_date: pd.Timestamp, win: int, max_wait_months: int):
    is_hi, _ = swings(series, win)
    highs = series.index[is_hi]
    hi = highs[(highs > after_date) & (highs <= after_date + pd.DateOffset(months=max_wait_months))]
    if len(hi) == 0:
        return None
    return hi[0]


# ---------------- Main ----------------
def main():
    end = pd.Timestamp.today().normalize() if END_DATE is None else pd.Timestamp(END_DATE)
    start = pd.Timestamp(START_DATE) if START_DATE is not None else (end - pd.DateOffset(years=YEARS_BACK))

    gold_d   = _download_close_any(GOLD_TICKERS, start, end, "Gold")
    silver_d = _download_close_any(SILVER_TICKERS, start, end, "Silver")
    spx_d    = _download_close_any(SPX_TICKERS, start, end, "SPX")

    gold   = to_monthly_last(gold_d).rename("Gold")
    silver = to_monthly_last(silver_d).rename("Silver")
    spx    = to_monthly_last(spx_d).rename("SPX")

    df = pd.concat([gold, silver, spx], axis=1).dropna()

    # --- Gold/Silver ratio bands (lines) ---
    ratio = (df["Gold"] / df["Silver"]).rename("GSR")
    mu = ratio.rolling(60, min_periods=24).mean()
    sd = ratio.rolling(60, min_periods=24).std(ddof=0)
    band1_u = mu + 1*sd
    band1_l = mu - 1*sd
    band2_u = mu + 2*sd
    band2_l = mu - 2*sd

    # --- Gold/SPX & Silver/SPX ratios ---
    g_spx = (df["Gold"] / df["SPX"]).rename("Gold/SPX")
    s_spx = (df["Silver"] / df["SPX"]).rename("Silver/SPX")

    # --- Divergences (on raw Gold & Silver monthly prices) ---
    # bear_dates, bull_dates = detect_divergences(df[["Gold","Silver"]])
    bear_dates, bull_dates, bear_arrows, bull_arrows = detect_divergences(df[["Gold","Silver"]])
    # --- Cycle-V zones from gold zigzag pivots ---
    piv = zigzag(df["Gold"], pct=ZZ_PCT)
    cycle = extract_best_cycle_from_pivots(piv)
    bands = cycle_v_bands(cycle)

    # --- Backtests (bear divergences only) ---
    btA = []
    for d in bear_dates:
        out = forward_drawdown(df["Gold"], d, DD_HORIZON_MONTHS)
        if out:
            entry, mn, dd = out
            btA.append((d, dd))
    btA_df = pd.DataFrame(btA, columns=["Date","DD"]).set_index("Date")

    btB = []
    for d in bear_dates:
        nh = next_swing_high_date(df["Gold"], d, SWING_WIN, NEXT_SWING_WAIT_MONTHS)
        if nh is None:
            continue
        out = forward_drawdown(df["Gold"], nh, DD_HORIZON_MONTHS)
        if out:
            entry, mn, dd = out
            btB.append((d, dd))
    btB_df = pd.DataFrame(btB, columns=["DivDate","DD"]).set_index("DivDate")

    # ---------------- Plot layout (NOW 5 subplots) ----------------
    fig = plt.figure(figsize=FIGSIZE, dpi=DPI, constrained_layout=True)
    gs = fig.add_gridspec(nrows=5, ncols=1, height_ratios=[2.4, 1.2, 1.1, 1.2, 1.2])

    # === 1) Top: Gold + Silver prices (twin y) ===
    ax0 = fig.add_subplot(gs[0, 0])
    ax0b = ax0.twinx()

    if LOG_SCALE:
        ax0.set_yscale("log")
        ax0b.set_yscale("log")

    ax0.plot(df.index, df["Gold"], color="goldenrod", lw=2.0, label="Gold (USD/oz)")
    ax0b.plot(df.index, df["Silver"], color="gray", lw=1.4, label="Silver (USD/oz)")

    ax0.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax0b.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    if not LOG_SCALE:
        ax0.yaxis.set_major_locator(mticker.MultipleLocator(GOLD_TICK_STEP))
        ax0b.yaxis.set_major_locator(mticker.MultipleLocator(SILVER_TICK_STEP))

    # Cycle-V zones on gold axis
    if bands is not None:
        u0, u1 = bands["under_run"]
        b0, b1 = bands["base"]
        s0, s1 = bands["stretch"]
        ax0.axhspan(u0, u1, color="#D6ECFF", alpha=0.40, label="Cycle V Under-run zone")
        ax0.axhspan(b0, b1, color="#D9F7D9", alpha=0.35, label="Cycle V Base zone")
        ax0.axhspan(s0, s1, color="#FFE3E3", alpha=0.35, label="Cycle V Stretch zone")

    # Divergence markers & labels at SILVER price
    for d in bear_dates:
        if d not in df.index:
            continue
        sp = float(df.loc[d, "Silver"])
        ax0b.scatter([d], [sp], s=50, color="crimson", edgecolor="black", zorder=6)
        ax0.axvline(d, color="crimson", alpha=0.15, lw=1.0)
        ax0b.annotate(
            f"Silver ${sp:,.0f}\nBear div",
            xy=(d, sp), xytext=(0, 22), textcoords="offset points",
            ha="center", va="bottom", fontsize=8, color="crimson",
            bbox=dict(boxstyle="round,pad=0.22", fc="white", ec="crimson", alpha=0.85),
            arrowprops=dict(arrowstyle='-|>', color='crimson', lw=0.9)
        )

    for d in bull_dates:
        if d not in df.index:
            continue
        sp = float(df.loc[d, "Silver"])
        ax0b.scatter([d], [sp], s=50, color="green", edgecolor="black", zorder=6)
        ax0.axvline(d, color="green", alpha=0.12, lw=1.0)
        ax0b.annotate(
            f"Silver ${sp:,.0f}\nBull div",
            xy=(d, sp), xytext=(0, -26), textcoords="offset points",
            ha="center", va="top", fontsize=8, color="green",
            bbox=dict(boxstyle="round,pad=0.22", fc="white", ec="green", alpha=0.85),
            arrowprops=dict(arrowstyle='-|>', color='green', lw=0.9)
        )

    ax0.set_title("Gold & Silver (Monthly) — Divergence + Cycle V Zones")
    ax0.set_ylabel("Gold (USD/oz)")
    ax0b.set_ylabel("Silver (USD/oz)")
    ax0.grid(True, color="lightgray", linestyle="--", alpha=0.5)
    
    # --- NEW: draw divergence arrows (what is being compared) ---
    for a in bear_arrows:
        draw_divergence_arrows(
            ax0, ax0b,
            a["g_prev_dt"], a["g_prev"], a["g_dt"], a["g"],
            a["s_prev_dt"], a["s_prev"], a["s_dt"], a["s"],
            kind="bear"
        )

    for a in bull_arrows:
        draw_divergence_arrows(
            ax0, ax0b,
            a["g_prev_dt"], a["g_prev"], a["g_dt"], a["g"],
            a["s_prev_dt"], a["s_prev"], a["s_dt"], a["s"],
            kind="bull"
        )
        
    h1, l1 = ax0.get_legend_handles_labels()
    h2, l2 = ax0b.get_legend_handles_labels()
    ax0.legend(h1 + h2, l1 + l2, loc="upper left", frameon=True)
    

        
    # === 2) NEW: Gold/SPX (left) and Silver/SPX (right) ratios (twin y) ===
    axX = fig.add_subplot(gs[1, 0], sharex=ax0)
    axXb = axX.twinx()

    axX.plot(g_spx.index, g_spx, lw=1.8, label="Gold / S&P 500", color='gold')
    axXb.plot(s_spx.index, s_spx, lw=1.2, label="Silver / S&P 500",color='silver')

    axX.set_ylabel("Gold/SPX")
    axXb.set_ylabel("Silver/SPX")
    axX.grid(True, color="lightgray", linestyle="--", alpha=0.5)

    # annotate latest
    axX.annotate(f"Latest Gold/SPX: {g_spx.iloc[-1]:.4f}",
                 xy=(g_spx.index[-1], g_spx.iloc[-1]), xytext=(8, 8),
                 textcoords="offset points",
                 fontsize=8, bbox=dict(fc="white", ec="none", alpha=0.7))
    axXb.annotate(f"Latest Silver/SPX: {s_spx.iloc[-1]:.4f}",
                  xy=(s_spx.index[-1], s_spx.iloc[-1]), xytext=(8, -14),
                  textcoords="offset points",
                  fontsize=8, bbox=dict(fc="white", ec="none", alpha=0.7))

    hx1, lx1 = axX.get_legend_handles_labels()
    hx2, lx2 = axXb.get_legend_handles_labels()
    axX.legend(hx1 + hx2, lx1 + lx2, loc="upper left", frameon=True)

    # === 3) Ratio bands (lines) ===
    ax1 = fig.add_subplot(gs[2, 0], sharex=ax0)
    ax1.plot(ratio.index, ratio, lw=1.4, label="Gold/Silver Ratio (GSR)")
    ax1.plot(mu.index, mu, lw=0.5, linestyle="--", label="Mean")
    ax1.plot(band1_u.index, band1_u, lw=1.0, linestyle="", label="+1σ")
    ax1.plot(band1_l.index, band1_l, lw=1.0, linestyle="", label="-1σ")
    ax1.plot(band2_u.index, band2_u, lw=1.0, linestyle="", label="+2σ")
    ax1.plot(band2_l.index, band2_l, lw=1.0, linestyle="", label="-2σ")

    # ±1σ band
    ax1.fill_between(
        ratio.index,
        band1_l,
        band1_u,
        alpha=0.18,
        label="±1σ"
    )
    
    # ±2σ band
    ax1.fill_between(
        ratio.index,
        band2_l,
        band2_u,
        alpha=0.10,
        label="±2σ"
    )
    ax1.set_ylabel("GSR")
    ax1.grid(True, color="lightgray", linestyle="--", alpha=0.5)
    ax1.legend(loc="upper left", ncol=3, fontsize=8)

    ax1.annotate(
        f"Latest: {ratio.iloc[-1]:.2f}",
        xy=(ratio.index[-1], ratio.iloc[-1]),
        xytext=(8, 8), textcoords="offset points",
        fontsize=8, bbox=dict(fc="white", ec="none", alpha=0.7)
    )

    # === 4) Backtest A ===
    ax2 = fig.add_subplot(gs[3, 0], sharex=ax0)
    if not btA_df.empty:
        ax2.plot(btA_df.index, -btA_df["DD"] * 100.0, marker="o", lw=1.2, label="Max drawdown next 12m (%)")
        ax2.axhline(-DD_THRESHOLD * 100.0, color="crimson", linestyle="--", lw=1.2, label="-30% threshold")
        hit = (btA_df["DD"] >= DD_THRESHOLD).mean() * 100.0
        ax2.set_title(f"Backtest A: Bear div → next-12m drawdown | Hit ≥30%: {hit:.1f}%")
    else:
        ax2.text(0.5, 0.5, "No bearish divergences detected for Backtest A.",
                 transform=ax2.transAxes, ha="center", va="center", color="crimson")
    ax2.set_ylabel("Drawdown (%)")
    ax2.grid(True, color="lightgray", linestyle="--", alpha=0.5)
    ax2.legend(loc="upper left", frameon=True)

    # === 5) Backtest B ===
    ax3 = fig.add_subplot(gs[4, 0], sharex=ax0)
    if not btB_df.empty:
        ax3.plot(btB_df.index, -btB_df["DD"] * 100.0, marker="s", lw=1.2, label="Max drawdown next 12m (%)")
        ax3.axhline(-DD_THRESHOLD * 100.0, color="crimson", linestyle="--", lw=1.2, label="-30% threshold")
        hit = (btB_df["DD"] >= DD_THRESHOLD).mean() * 100.0
        ax3.set_title(f"Backtest B: Bear div → next-12m drawdown (from next swing high) | Hit ≥30%: {hit:.1f}%")
    else:
        ax3.text(0.5, 0.5, "No valid next-swing-high entries found for Backtest B.",
                 transform=ax3.transAxes, ha="center", va="center", color="crimson")
    ax3.set_ylabel("Drawdown (%)")
    ax3.set_xlabel("Year")
    ax3.grid(True, color="lightgray", linestyle="--", alpha=0.5)
    ax3.legend(loc="upper left", frameon=True)

    # X-axis formatting
    ax3.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax3.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax3.xaxis.get_major_locator()))

    plt.savefig("/Users/michaelwai/Downloads/"+SAVE_PNG, dpi=DPI)
    plt.show()

    print(f"Saved -> {SAVE_PNG}")
    print(f"Bear divergences: {len(bear_dates)} | Bull divergences: {len(bull_dates)}")


if __name__ == "__main__":
    main()