#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gold Weekly: Historical impulses + Current structure + Fib cluster density
Adds:
- Fibonacci extension clustering across all ZZ levels
- Exhaustion Probability Score (0–100) combining:
  (1) Fib confluence at price
  (2) Blow-off risk (8-week return z-score)
  (3) Stretch vs EMA52 (z-score)
  (4) Volatility spike (8-week vol z-score)

Notes:
- Heuristic score, not truth.
- Weekly data locked.
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ---------------- CONFIG ----------------
TICKERS = ["TSLA", "GC=F"]  # futures works well for long history
START_DATE = "1990-01-01"
END_DATE   = None

INTERVAL = "1wk"  # LOCKED WEEKLY

ZZ_RANGE = range(4, 13)     # 4% to 12%
TOP_N_HIST = 3

SAVE_PNG = "gold_weekly_impulses_with_cluster_and_exhaustion.png"

# Fib extension multipliers used for clustering (extensions from IV_low using len(III))
FIB_EXTS = [1.000, 1.272, 1.618, 2.000]

# Histogram bins for fib density (price axis)
BIN_SIZE = 25.0   # $25 bins; adjust to smooth / sharpen
MIN_LEVELS_PER_ZZ = 3  # skip ZZ levels with too few fib levels (noise guard)

# Exhaustion score components (weights should sum ~1)
W_CONFLUENCE = 0.40
W_BLOWOFF    = 0.25
W_STRETCH    = 0.20
W_VOL_SPIKE  = 0.15
 
# Component lookbacks (weeks)
RET_W = 8
VOL_W = 8
EMA_W = 52

# Z-score rolling windows (for normalization)
ZWIN_RET = 260   # ~5y
ZWIN_ST  = 260
ZWIN_VOL = 260

# Score shaping
SIGMOID_K = 1.2  # bigger => more “binary” score

# Projection knobs (heuristics)
PROJ_W4_RETRACE  = (0.236, 0.382)
PROJ_W5_EXT      = (0.618, 1.000)
PROJ_ABC_RETRACE = (0.382, 0.618)
# ----------------------------------------


# ---------------- DATA ----------------
def download_gold():
    end = pd.Timestamp.today().normalize() if END_DATE is None else pd.Timestamp(END_DATE)
    for t in TICKERS:
        try:
            print("Trying", t)
            df = yf.download(
                t, start=START_DATE, end=end + pd.Timedelta(days=1),
                interval=INTERVAL, auto_adjust=True, progress=False
            )
            if df.empty or "Close" not in df.columns:
                continue
            s = df["Close"].dropna()
            if isinstance(s, pd.DataFrame):
                s = s.iloc[:, 0]
            s.index = pd.to_datetime(s.index)
            s = s.sort_index()
            print("Using", t)
            return s.rename("Gold")
        except Exception:
            continue
    raise RuntimeError("No gold data available")


# ---------------- ZIGZAG ----------------
def zigzag(series, pct):
    s = series.dropna()
    if s.empty:
        return []

    piv = []
    p_last = float(s.iloc[0])
    i_last = s.index[0]
    trend = 0
    piv.append((i_last, p_last))

    for i, p in s.iloc[1:].items():
        p = float(p)
        chg = (p - p_last) / p_last * 100.0 if p_last != 0 else 0.0

        if trend >= 0:
            if p >= p_last:
                p_last, i_last = p, i
                piv[-1] = (i_last, p_last)
            elif chg <= -pct:
                piv.append((i, p))
                p_last, i_last = p, i
                trend = -1

        if trend <= 0:
            if p <= p_last:
                p_last, i_last = p, i
                piv[-1] = (i_last, p_last)
            elif chg >= pct:
                piv.append((i, p))
                p_last, i_last = p, i
                trend = +1

    # classify polarity
    out = []
    for k in range(len(piv)):
        dt, px = piv[k]
        pl = piv[k-1][1] if k > 0 else px
        pr = piv[k+1][1] if k < len(piv)-1 else px
        if px <= pl and px <= pr:
            pol = "low"
        elif px >= pl and px >= pr:
            pol = "high"
        else:
            pol = None
        if pol:
            out.append((dt, px, pol))

    # dedup dates
    cleaned = []
    for dt, px, pol in out:
        if not cleaned or cleaned[-1][0] != dt:
            cleaned.append((dt, px, pol))
    return cleaned


# ---------------- IMPULSE DETECTION ----------------
def detect_impulses(pivots):
    """Return impulse sequences: low,high,low,high,low,high"""
    impulses = []
    for i in range(len(pivots) - 5):
        seq = pivots[i:i+6]
        pols = [x[2] for x in seq]
        if pols == ["low","high","low","high","low","high"]:
            p1,p2,p3,p4,p5,p6 = [x[1] for x in seq]
            if (p2 < p4 < p6) and (p1 < p3 < p5) and (p5 > p2):
                impulses.append(seq)
    return impulses


# ---------------- SCORING (impulse quality) ----------------
def score_impulse(seq):
    dates = [x[0] for x in seq]
    prices = [x[1] for x in seq]
    duration = (dates[-1] - dates[0]).days / 365.25
    gain = (prices[-1] / prices[0]) - 1.0 if prices[0] > 0 else 0.0
    w1 = prices[1] - prices[0]
    w3 = prices[3] - prices[2]
    w5 = prices[5] - prices[4]
    if min(w1,w3,w5) <= 0:
        return 0.0
    symmetry = min(w1, w3, w5) / max(w1, w3, w5)
    return float(np.round(duration * (1.0 + gain) * symmetry, 2))


# ---------------- CURRENT STRUCTURE ----------------
def infer_current_run(pivots, lookback=36):
    if len(pivots) < 2:
        return None, "No pivots"

    anchor = None
    start_k = max(0, len(pivots) - lookback)
    for i in range(len(pivots)-1, start_k-1, -1):
        if pivots[i][2] == "low":
            anchor = i
            break
    if anchor is None:
        return None, "No recent low anchor"

    run = [pivots[anchor]]
    want = "high"
    for j in range(anchor+1, len(pivots)):
        if pivots[j][2] == want:
            run.append(pivots[j])
            want = "low" if want == "high" else "high"
        if len(run) >= 6:
            break

    L = len(run)
    if L <= 1:
        state = "Insufficient structure"
    elif L == 2:
        state = "I developing (up)"
    elif L == 3:
        state = "II likely done, III developing"
    elif L == 4:
        state = "III likely done, IV developing"
    elif L == 5:
        state = "IV likely done, V developing"
    else:
        state = "I–V completed (impulse done)"
    return run, state


# ---------------- PROJECTIONS ----------------
def project_forward_from_run(run):
    zones, proj_points = [], []
    if run is None or len(run) < 2:
        return proj_points, "No projection (not enough pivots).", zones

    dates = [x[0] for x in run]
    prices = [x[1] for x in run]
    last_dt, last_px = dates[-1], prices[-1]
    step = pd.DateOffset(weeks=26)

    I_low = prices[0]
    I_high = prices[1] if len(prices) >= 2 else None
    II_low = prices[2] if len(prices) >= 3 else None
    III_high = prices[3] if len(prices) >= 4 else None
    IV_low = prices[4] if len(prices) >= 5 else None
    V_high = prices[5] if len(prices) >= 6 else None

    if len(prices) == 4 and II_low is not None and III_high is not None:
        w3_len = III_high - II_low
        lo = III_high - PROJ_W4_RETRACE[1]*w3_len
        hi = III_high - PROJ_W4_RETRACE[0]*w3_len
        zones.append(("Proj Wave IV zone", min(lo,hi), max(lo,hi)))

        iv_proxy = (lo+hi)/2
        w1_len = (I_high - I_low) if (I_high is not None) else w3_len*0.5
        v_lo = iv_proxy + PROJ_W5_EXT[0]*w1_len
        v_hi = iv_proxy + PROJ_W5_EXT[1]*w1_len
        zones.append(("Proj Wave V zone", min(v_lo,v_hi), max(v_lo,v_hi)))

        proj_points = [(last_dt, last_px), (last_dt + step, (lo+hi)/2), (last_dt + step*2, (v_lo+v_hi)/2)]
        txt = "Guide: If Wave III is topping, expect IV pullback zone, then V zone."
        return proj_points, txt, zones

    if len(prices) == 5 and IV_low is not None and I_high is not None:
        w1_len = I_high - I_low
        v_lo = IV_low + PROJ_W5_EXT[0]*w1_len
        v_hi = IV_low + PROJ_W5_EXT[1]*w1_len
        zones.append(("Proj Wave V zone", min(v_lo,v_hi), max(v_lo,v_hi)))
        proj_points = [(last_dt, last_px), (last_dt + step, (v_lo+v_hi)/2)]
        txt = "Guide: If Wave IV is in, Wave V often targets the shaded zone."
        return proj_points, txt, zones

    if len(prices) >= 6 and V_high is not None:
        impulse_len = V_high - I_low
        lo = V_high - PROJ_ABC_RETRACE[1]*impulse_len
        hi = V_high - PROJ_ABC_RETRACE[0]*impulse_len
        zones.append(("Proj ABC retrace zone", min(lo,hi), max(lo,hi)))
        proj_points = [(last_dt, last_px), (last_dt + step, (lo+hi)/2)]
        txt = "Guide: After 5-wave impulse, ABC retrace often pulls into the shaded zone."
        return proj_points, txt, zones

    return proj_points, "Guide: structure incomplete; wait for next pivot confirmation.", zones


# ---------------- FIB EXTENSION LEVELS (for clustering) ----------------
def fib_levels_from_impulse(seq, fibs=FIB_EXTS):
    """
    seq = [I_low, I_high, II_low, III_high, IV_low, V_high]
    Use IV_low + fib * len(III) as projected extension targets.
    """
    p2 = seq[1][1]   # I_high
    p3 = seq[2][1]   # II_low
    p4 = seq[3][1]   # III_high
    p5 = seq[4][1]   # IV_low

    len_III = (p4 - p3)
    if len_III <= 0:
        return []

    return [p5 + f*len_III for f in fibs]


# ---------------- EXHAUSTION SCORE ----------------
def rolling_z(x, win):
    mu = x.rolling(win, min_periods=max(20, win//5)).mean()
    sd = x.rolling(win, min_periods=max(20, win//5)).std(ddof=0)
    return (x - mu) / (sd.replace(0, np.nan))


def sigmoid(x, k=1.0):
    return 1.0 / (1.0 + np.exp(-k*x))


def build_fib_density(levels, price_min, price_max, bin_size=25.0):
    bins = np.arange(price_min, price_max + bin_size, bin_size)
    hist, edges = np.histogram(levels, bins=bins)
    centers = (edges[:-1] + edges[1:]) / 2.0
    return centers, hist.astype(float)


def density_at_price(centers, hist, price_series):
    """
    Map each price to density via linear interpolation on histogram centers.
    """
    if len(centers) < 2:
        return pd.Series(np.nan, index=price_series.index)
    dens = np.interp(price_series.values, centers, hist, left=0.0, right=0.0)
    return pd.Series(dens, index=price_series.index, name="FibDensity")


def exhaustion_probability_score(price: pd.Series, fib_dens: pd.Series):
    """
    Build 0–100 score from components.
    """

    # 1) Confluence: density normalized 0–1
    dens_norm = fib_dens / (fib_dens.max() if fib_dens.max() > 0 else np.nan)
    dens_norm = dens_norm.clip(0, 1).fillna(0)

    # 2) Blow-off: 8-week return z-score
    ret8 = price.pct_change(RET_W)
    ret8_z = rolling_z(ret8, ZWIN_RET).clip(-5, 5)

    # 3) Stretch vs EMA52: (price/ema - 1) z-score
    ema = price.ewm(span=EMA_W, adjust=False).mean()
    stretch = (price / ema) - 1.0
    stretch_z = rolling_z(stretch, ZWIN_ST).clip(-5, 5)

    # 4) Vol spike: 8-week realized vol z-score
    r1 = price.pct_change().fillna(0)
    vol8 = r1.rolling(VOL_W, min_periods=VOL_W).std(ddof=0)
    vol8_z = rolling_z(vol8, ZWIN_VOL).clip(-5, 5)

    # Convert z-scores to 0–1 risk via sigmoid (only positive side should matter)
    blowoff_risk = sigmoid(ret8_z.fillna(0), k=SIGMOID_K)
    stretch_risk = sigmoid(stretch_z.fillna(0), k=SIGMOID_K)
    vol_risk     = sigmoid(vol8_z.fillna(0), k=SIGMOID_K)

    # Weighted sum -> 0–1 -> 0–100
    score01 = (
        W_CONFLUENCE * dens_norm +
        W_BLOWOFF    * blowoff_risk +
        W_STRETCH    * stretch_risk +
        W_VOL_SPIKE  * vol_risk
    ).clip(0, 1)

    out = pd.DataFrame({
        "Price": price,
        "FibDensity": fib_dens,
        "Confluence01": dens_norm,
        "Blowoff01": blowoff_risk,
        "Stretch01": stretch_risk,
        "VolSpike01": vol_risk,
        "Score01": score01,
        "Score": score01 * 100.0
    }, index=price.index)

    return out


# ---------------- PLOTTING HELPERS ----------------
def _fmt(x): return f"{x:,.0f}"

def add_zone(ax, name, y0, y1, x1):
    ax.axhspan(y0, y1, alpha=0.10)
    ax.text(x1, (y0+y1)/2, name, ha="right", va="center", fontsize=8,
            bbox=dict(fc="white", ec="none", alpha=0.6))

def annotate_seq(ax, seq, color_line=None):
    labels = ["I","I","II","III","IV","V"]
    xs = [x[0] for x in seq]
    ys = [x[1] for x in seq]
    ax.plot(xs, ys, lw=2, color=color_line)
    for (d,p,_), lab in zip(seq, labels):
        ax.scatter(d, p, s=28, zorder=5)
        ax.annotate(f"{lab}\n{_fmt(p)}", (d,p), xytext=(6,6),
                    textcoords="offset points", fontsize=8,
                    bbox=dict(fc="white", ec="none", alpha=0.65))

def annotate_box(ax, text, loc="tl"):
    if loc == "tl":
        x,y,ha,va = 0.01, 0.99, "left", "top"
    else:
        x,y,ha,va = 0.01, 0.02, "left", "bottom"
    ax.text(x, y, text, transform=ax.transAxes,
            ha=ha, va=va, fontsize=9,
            bbox=dict(fc="white", ec="black", alpha=0.65))

def annotate_projection(ax, proj_points):
    if len(proj_points) >= 2:
        xs = [p[0] for p in proj_points]
        ys = [p[1] for p in proj_points]
        ax.plot(xs, ys, lw=1.8, ls="--", alpha=0.8)
        ax.scatter(xs[1:], ys[1:], s=18, zorder=5)
        ax.annotate("Possible path (guide)", (xs[1], ys[1]),
                    xytext=(8, -10), textcoords="offset points",
                    fontsize=8, bbox=dict(fc="white", ec="none", alpha=0.6))


# ---------------- MAIN ----------------
def main():
    gold = download_gold()

    historical = []
    current_candidates = []

    # Collect fib extension levels for density
    fib_levels_all = []
    fib_levels_by_zz = {zz: [] for zz in ZZ_RANGE}

    for zz in ZZ_RANGE:
        piv = zigzag(gold, zz)
        imps = detect_impulses(piv)

        for seq in imps:
            sc = score_impulse(seq)
            historical.append((zz, seq, sc))

            lvls = fib_levels_from_impulse(seq, fibs=FIB_EXTS)
            if lvls:
                fib_levels_by_zz[zz].extend(lvls)

        run, state = infer_current_run(piv)
        if run is not None:
            conf = min(0.95, 0.40 + 0.12*len(run))
            current_candidates.append((zz, run, state, conf))

    # Flatten levels with a simple noise guard
    for zz in ZZ_RANGE:
        lv = fib_levels_by_zz[zz]
        if len(lv) >= MIN_LEVELS_PER_ZZ:
            fib_levels_all.extend(lv)

    historical = sorted(historical, key=lambda x: x[2], reverse=True)
    top_hist = historical[:TOP_N_HIST]

    current_candidates = sorted(current_candidates, key=lambda x: (len(x[1]), x[0]), reverse=True)
    current_best = current_candidates[0] if current_candidates else None

    # Build density (price-binned)
    price_min = float(np.nanmin(gold.values))
    price_max = float(np.nanmax(gold.values)) * 1.05
    centers, hist = build_fib_density(fib_levels_all, price_min, price_max, bin_size=BIN_SIZE)

    # Map density to time series
    fib_dens_ts = density_at_price(centers, hist, gold)

    # Exhaustion score time series
    score_df = exhaustion_probability_score(gold, fib_dens_ts)
    last = score_df.iloc[-1]

    # Build heatmap matrix: ZZ% vs price bins
    # each row = histogram for that ZZ’s levels
    heat_rows = []
    zz_list = list(ZZ_RANGE)
    for zz in zz_list:
        lv = fib_levels_by_zz[zz]
        if len(lv) < MIN_LEVELS_PER_ZZ:
            heat_rows.append(np.zeros_like(hist))
        else:
            _, h = build_fib_density(lv, price_min, price_max, bin_size=BIN_SIZE)
            heat_rows.append(h)
    heat = np.vstack(heat_rows)

    # ---------------- PLOT ----------------
    nrows = len(top_hist) + 4  # hist templates + current + heatmap + density + score
    fig, axes = plt.subplots(nrows, 1, figsize=(15, 4.5*nrows), sharex=False)

    # 1) Historical templates
    for ax, (zz, seq, sc) in zip(axes[:len(top_hist)], top_hist):
        ax.plot(gold.index, gold.values, lw=1.2, color="black")
        annotate_seq(ax, seq)

        d1,p1,_ = seq[0]
        d6,p6,_ = seq[-1]
        years = (d6 - d1).days / 365.25
        gain = (p6/p1 - 1.0)*100 if p1>0 else 0.0
        w1 = seq[1][1] - seq[0][1]
        w3 = seq[3][1] - seq[2][1]
        w5 = seq[5][1] - seq[4][1]
        strongest = "III" if w3 >= max(w1,w5) else ("I" if w1 >= w5 else "V")

        comm = (
            f"ZZ={zz}% | Score={sc}\n"
            f"Span: {d1.date()} → {d6.date()} (~{years:.1f}y)\n"
            f"Impulse gain: {gain:.0f}%\n"
            f"Strongest leg: Wave {strongest}\n"
            f"Read: use as a template for a 5-wave advance → correction."
        )
        annotate_box(ax, comm, "tl")

        proj_pts, proj_text, zones = project_forward_from_run(seq)
        x1 = gold.index.max()
        for name, y0, y1 in zones:
            add_zone(ax, name, y0, y1, x1)
        annotate_projection(ax, proj_pts)
        annotate_box(ax, proj_text, "bl")

        ax.set_title("Historical impulse template (weekly)")
        ax.grid(alpha=0.25)
        ax.set_ylabel("Price")

    # 2) Current structure
    axC = axes[len(top_hist)]
    axC.plot(gold.index, gold.values, lw=1.2, color="black")
    axC.set_title("CURRENT structure (weekly) + forward guide")
    axC.grid(alpha=0.25)
    axC.set_ylabel("Price")

    if current_best:
        zz, run, state, conf = current_best
        xs = [x[0] for x in run]
        ys = [x[1] for x in run]
        axC.plot(xs, ys, lw=2.2, color="red")
        wave_labels = ["I", "I", "II", "III", "IV", "V"]
        for i, (d,p,pol) in enumerate(run):
            lab = wave_labels[i] if i < len(wave_labels) else "?"
            axC.scatter(d, p, color="red", s=30, zorder=6)
            axC.annotate(f"{lab}\n{_fmt(p)}", (d,p), xytext=(6,6),
                         textcoords="offset points", fontsize=8,
                         bbox=dict(fc="white", ec="none", alpha=0.65))

        comm = (
            f"ZZ={zz}% | Confidence≈{conf:.2f}\n"
            f"State: {state}\n"
            f"Interpretation:\n"
            f"- This is the most recent alternating pivot run.\n"
            f"- Next pivot confirmation is what upgrades confidence."
        )
        annotate_box(axC, comm, "tl")

        proj_pts, proj_text, zones = project_forward_from_run(run)
        x1 = gold.index.max()
        for name, y0, y1 in zones:
            add_zone(axC, name, y0, y1, x1)
        annotate_projection(axC, proj_pts)
        annotate_box(axC, proj_text, "bl")

    # 3) Heatmap
    axH = axes[len(top_hist)+1]
    extent = [centers[0], centers[-1], zz_list[0], zz_list[-1]]
    im = axH.imshow(
        heat,
        aspect="auto",
        origin="lower",
        extent=extent
    )
    axH.set_title("Fibonacci extension cluster density across ALL ZZ levels (weekly Gold)")
    axH.set_ylabel("Zigzag %")
    axH.set_xlabel("Price level")
    cbar = plt.colorbar(im, ax=axH, pad=0.01)
    cbar.set_label("Count of fib targets in bin")

    # mark current price on heatmap
    axH.axvline(float(gold.iloc[-1]), ls="--", lw=1.2)

    # 4) Collapsed density
    axD = axes[len(top_hist)+2]
    axD.plot(centers, hist, lw=1.4)
    axD.axvline(float(gold.iloc[-1]), ls="--", lw=1.2)
    axD.set_title("Collapsed fib density (all ZZ combined)")
    axD.set_ylabel("Density")
    axD.set_xlabel("Price level")
    axD.grid(alpha=0.25)

    # 5) Exhaustion score over time
    axS = axes[len(top_hist)+3]
    axS.plot(score_df.index, score_df["Score"], lw=1.6)
    axS.axhline(70, ls="--", lw=1.0)
    axS.axhline(85, ls="--", lw=1.0)
    axS.set_title("Exhaustion Probability Score (0–100)")
    axS.set_ylabel("Score")
    axS.grid(alpha=0.25)

    score_txt = (
        f"Current score: {last['Score']:.1f}\n"
        f"Confluence: {last['Confluence01']:.2f}\n"
        f"Blow-off:   {last['Blowoff01']:.2f}\n"
        f"Stretch:    {last['Stretch01']:.2f}\n"
        f"Vol spike:  {last['VolSpike01']:.2f}\n"
        f"Rule of thumb:\n"
        f"70–85 = elevated risk\n"
        f">85  = high risk / late-stage"
    )
    annotate_box(axS, score_txt, "tl")

    # x formatting for time axes
    for ax in axes[:len(top_hist)+1]:
        locator = mdates.AutoDateLocator()
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))

    # score subplot x formatting
    locator = mdates.AutoDateLocator()
    axS.xaxis.set_major_locator(locator)
    axS.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))

    plt.tight_layout()
    plt.savefig(SAVE_PNG, dpi=180)
    plt.show()

    print("Saved ->", SAVE_PNG)
    print(f"Current Exhaustion Score: {last['Score']:.2f}")
    print(f"  Confluence01: {last['Confluence01']:.3f}")
    print(f"  Blowoff01:    {last['Blowoff01']:.3f}")
    print(f"  Stretch01:    {last['Stretch01']:.3f}")
    print(f"  VolSpike01:   {last['VolSpike01']:.3f}")


if __name__ == "__main__":
    main()