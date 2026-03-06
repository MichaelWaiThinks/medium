#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Feb  1 10:19:08 2026

@author: michaelwai
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quarterly Dynamic Allocation Strategy (SPY / QQQ / GLD-style metals via futures for GSR)

This version implements the “3-asset mix” we discussed:
- STOCK leg: SPY  (core equity regime anchor)
- ACCEL leg: QQQ  (growth accelerator)
- DEF leg:  GLD  (defensive ballast)

But we keep your original 3-layer logic structure:
1) SPY trend filter (10-period SMA with 2-period hysteresis)      [period = quarter]
2) SPY/GLD valuation tilt using z-score bands                      [period = quarter]
3) Gold/Silver ratio (GSR) to optionally add SLV when silver cheap

Important clarification:
- GLD and SLV are still the metals instruments.
- QQQ is an additional equity sleeve when risk-on.
- We DO NOT treat QQQ as “gold” anymore (your draft did that accidentally).

Decision frequency: QUARTER-END (QE)

Signals and weights computed at quarter-end using ONLY info up to prior quarter-end.
Weights applied over the next quarter return (no lookahead).

Outputs:
- CSV of signals/weights/equity
- PNG plot: equity vs buy&hold + drawdown shading + SPY/GLD z-score axis + allocation strip
- Console summary: total return, CAGR, max drawdown, max drawdown duration (quarters),
  plus 100% SPY and 100% QQQ benchmarks.
"""

import os
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf


# =========================
# USER INPUTS
# =========================
TICKER_SPY = "SPY"
TICKER_QQQ = "QQQ"
TICKER_GLD = "GLD"
TICKER_SLV = "SLV"

START_DATE = "2012-05-01"
END_DATE   = "2018-02-01"
START_CAPITAL = 1_000_000

EXPORT_DIR = os.path.abspath("./outputs_spy_qqq_gld_slv_quarterly")


# =========================
# STRATEGY PARAMETERS
# =========================
DECISION_FREQ = "QE"         # quarter-end resample; normalized to 'Q' internally

# Trend filter (period = quarter)
SMA_PERIODS = 10
HYSTERESIS_N = 2

# Rebalance threshold
REB_THRESHOLD = 0.05         # rebalance if any weight changes by >= 5%

# Drawdown control (quarters)
MAX_DRAWDOWN = -0.10         # trigger defensive at -10%
REENTRY_CONFIRM = 2          # require N consecutive periods SPY_ON to exit defensive

# SPY/GLD z-score tilt (period = quarter)
Z_WIN_PERIODS = 24           # rolling window (quarters)
Z_HIGH = 1.0
Z_LOW  = -1.0

# Equity structure when risk-on:
# Base equity split between SPY (core) and QQQ (accelerator).
# Then SPY/GLD z-score tilts total equity vs metals.
BASE_SPY_SHARE_OF_EQUITY = 0.67   # e.g. 2/3 of equity sleeve SPY
BASE_QQQ_SHARE_OF_EQUITY = 0.33   # e.g. 1/3 of equity sleeve QQQ

# Total equity weight when risk-on, driven by valuation tilt
EQUITY_WEIGHT_BASE_ON = 0.85      # default total equity weight when SPY_ON
EQUITY_WEIGHT_TILT_HIGH = 0.50    # when z > Z_HIGH (equity expensive vs gold) -> lower total equity
EQUITY_WEIGHT_TILT_LOW  = 1.00    # when z < Z_LOW  (equity cheap vs gold) -> higher total equity

# Silver only when GSR high (silver cheap vs gold)
GSR_ADD_SLV = 85
GSR_REMOVE_SLV = 75
SLV_SHARE_IN_METALS_WHEN_ON = 0.40
SLV_SHARE_IN_METALS_WHEN_OFF = 0.60

# Plotting
LOOKBACK_YEARS_VIEW = 10
FIGSIZE = (22, 14)


# =========================
# UTILITIES
# =========================
def _normalize_resample_freq(freq: str) -> str:
    """
    Normalize more exotic aliases. 'QE' -> 'Q' is safer across pandas versions.
    """
    if freq.upper() == "QE":
        return "Q"
    return freq


def extract_close(obj, name: str) -> pd.Series:
    """
    Robustly extract Close as a Series from yfinance output.
    Handles:
      - Series
      - DataFrame with single-level columns including 'Close'
      - DataFrame with MultiIndex columns (field, ticker)
    """
    if isinstance(obj, pd.Series):
        s = obj.copy()
        s.name = name
        return s

    if not isinstance(obj, pd.DataFrame):
        raise TypeError(f"Unexpected yfinance type: {type(obj)}")

    if obj.empty:
        raise ValueError(f"Empty download for {name}")

    if isinstance(obj.columns, pd.MultiIndex):
        if "Close" in obj.columns.get_level_values(0):
            close_df = obj.loc[:, ("Close", slice(None))]
            s = close_df.iloc[:, 0].copy()
        else:
            raise KeyError("MultiIndex download has no 'Close' level.")
    else:
        if "Close" in obj.columns:
            s = obj["Close"].copy()
        elif "Adj Close" in obj.columns:
            s = obj["Adj Close"].copy()
        else:
            raise KeyError("Download has no 'Close' or 'Adj Close' column.")

    s.name = name
    return s


def download_prices(start: str, end: str) -> pd.DataFrame:
    """
    Download daily adjusted prices for SPY/QQQ/GLD/SLV and futures proxies for GSR (GC=F / SI=F).
    Uses auto_adjust=True.
    """
    pad_start = (pd.to_datetime(start) - pd.DateOffset(years=10)).strftime("%Y-%m-%d")

    tickers = [TICKER_SPY, TICKER_QQQ, TICKER_GLD, TICKER_SLV]
    raw = yf.download(
        tickers,
        start=pad_start,
        end=end,
        auto_adjust=True,
        progress=False,
        group_by="column",
        threads=True,
    )

    if isinstance(raw.columns, pd.MultiIndex):
        if "Close" not in raw.columns.get_level_values(0):
            raise KeyError("Main download missing Close.")
        close = raw["Close"].copy()
    else:
        # single ticker fallback
        close = raw[["Close"]].copy()
        close.columns = tickers

    # Futures proxies for GSR
    gold_raw = yf.download("GC=F", start=pad_start, end=end, auto_adjust=True, progress=False)
    silver_raw = yf.download("SI=F", start=pad_start, end=end, auto_adjust=True, progress=False)
    gold_f = extract_close(gold_raw, "GOLD_F")
    silver_f = extract_close(silver_raw, "SILVER_F")

    df = pd.concat([close, gold_f, silver_f], axis=1)

    # drop rows missing any required series
    req = [TICKER_SPY, TICKER_QQQ, TICKER_GLD, TICKER_SLV, "GOLD_F", "SILVER_F"]
    df = df.dropna(subset=req, how="any")

    # stable rename for convenience
    df = df.rename(columns={
        TICKER_SPY: "SPY",
        TICKER_QQQ: "QQQ",
        TICKER_GLD: "GLD",
        TICKER_SLV: "SLV",
    })

    return df


def to_period_end(df_daily: pd.DataFrame) -> pd.DataFrame:
    freq = _normalize_resample_freq(DECISION_FREQ)
    return df_daily.resample(freq).last()


def compute_hysteresis_regime(raw_on: pd.Series, n: int) -> pd.Series:
    """
    raw_on: boolean series (True=ON) for each period-end.
    Hysteresis: require n consecutive True to turn ON, n consecutive False to turn OFF.
    """
    regime = pd.Series(index=raw_on.index, dtype="boolean")
    current = False
    t_streak = 0
    f_streak = 0

    for dt, v in raw_on.items():
        if pd.isna(v):
            regime.loc[dt] = pd.NA
            continue

        if bool(v):
            t_streak += 1
            f_streak = 0
        else:
            f_streak += 1
            t_streak = 0

        if (not current) and (t_streak >= n):
            current = True
        if current and (f_streak >= n):
            current = False

        regime.loc[dt] = current

    return regime.astype("boolean")


def drawdown_series(equity: pd.Series) -> pd.Series:
    peak = equity.cummax()
    return equity / peak - 1.0


def max_drawdown_duration(dd: pd.Series) -> int:
    """
    Max consecutive periods underwater (dd < 0). (periods = quarters here)
    """
    underwater = (dd < 0).astype(int)
    max_run = 0
    run = 0
    for v in underwater.values:
        if v == 1:
            run += 1
            max_run = max(max_run, run)
        else:
            run = 0
    return int(max_run)


# =========================
# STRATEGY: target weights
# =========================
def pick_total_equity_when_on(z: float) -> float:
    """
    Decide total equity sleeve weight (SPY+QQQ combined) when SPY regime is ON.
    """
    if np.isnan(z):
        return EQUITY_WEIGHT_BASE_ON
    if z > Z_HIGH:
        return EQUITY_WEIGHT_TILT_HIGH
    if z < Z_LOW:
        return EQUITY_WEIGHT_TILT_LOW
    return EQUITY_WEIGHT_BASE_ON


def metals_split(gsr: float, allow_slv: bool, risk_on: bool) -> tuple[float, float]:
    """
    Return (share_gld_inside_metals, share_slv_inside_metals).
    """
    if not allow_slv:
        return 1.0, 0.0
    slv_share = SLV_SHARE_IN_METALS_WHEN_ON if risk_on else SLV_SHARE_IN_METALS_WHEN_OFF
    return 1.0 - slv_share, slv_share


def compute_targets(row_prev: pd.Series) -> tuple[float, float, float, float, str]:
    """
    Use previous period-end signals to set weights for next period.
    Returns (wSPY, wQQQ, wGLD, wSLV, reason)
    """
    spy_on = bool(row_prev["SPY_ON"])
    z = float(row_prev["SPY_GLD_Z"])
    gsr = float(row_prev["GSR"])
    allow_slv = bool(row_prev["ALLOW_SLV"])

    if spy_on:
        w_eq_total = pick_total_equity_when_on(z)        # total equity (SPY+QQQ)
        w_spy = w_eq_total * BASE_SPY_SHARE_OF_EQUITY
        w_qqq = w_eq_total * BASE_QQQ_SHARE_OF_EQUITY

        metals = 1.0 - w_eq_total
        g_share, s_share = metals_split(gsr, allow_slv, risk_on=True)
        w_gld = metals * g_share
        w_slv = metals * s_share

        reason = f"ON: z={z:.2f} eq={w_eq_total:.2f} gsr={gsr:.1f} allow_slv={allow_slv}"
    else:
        w_spy = 0.0
        w_qqq = 0.0

        metals = 1.0
        g_share, s_share = metals_split(gsr, allow_slv, risk_on=False)
        w_gld = metals * g_share
        w_slv = metals * s_share

        reason = f"OFF: gsr={gsr:.1f} allow_slv={allow_slv}"

    # normalize safety
    s = w_spy + w_qqq + w_gld + w_slv
    if s <= 0:
        return 0.0, 0.0, 1.0, 0.0, "fallback"
    return w_spy / s, w_qqq / s, w_gld / s, w_slv / s, reason


def apply_rebalance_threshold(curr_w: np.ndarray, tgt_w: np.ndarray, thr: float) -> tuple[np.ndarray, bool]:
    if np.max(np.abs(tgt_w - curr_w)) >= thr:
        return tgt_w, True
    return curr_w, False


# =========================
# SIGNALS
# =========================
def build_signals(p: pd.DataFrame) -> pd.DataFrame:
    """
    p: period-end prices with columns: SPY, QQQ, GLD, SLV, GOLD_F, SILVER_F
    Adds:
      SPY_SMA
      SPY_ON (hysteresis)
      SPY_GLD
      SPY_GLD_Z
      GSR
      ALLOW_SLV (stateful)
    """
    out = p.copy()

    out["SPY_SMA"] = out["SPY"].rolling(SMA_PERIODS).mean()
    raw_on = out["SPY"] > out["SPY_SMA"]
    out["SPY_ON"] = compute_hysteresis_regime(raw_on, HYSTERESIS_N)

    out["SPY_GLD"] = out["SPY"] / out["GLD"]
    roll_mean = out["SPY_GLD"].rolling(Z_WIN_PERIODS).mean()
    roll_std = out["SPY_GLD"].rolling(Z_WIN_PERIODS).std(ddof=0)
    out["SPY_GLD_Z"] = (out["SPY_GLD"] - roll_mean) / roll_std

    out["GSR"] = out["GOLD_F"] / out["SILVER_F"]

    allow = False
    allow_series = []
    for dt in out.index:
        gsr = out.loc[dt, "GSR"]
        if np.isnan(gsr):
            allow_series.append(np.nan)
            continue
        if (not allow) and (gsr >= GSR_ADD_SLV):
            allow = True
        if allow and (gsr <= GSR_REMOVE_SLV):
            allow = False
        allow_series.append(allow)
    out["ALLOW_SLV"] = allow_series

    return out


# =========================
# BACKTEST
# =========================
def run_backtest(p_sig: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    start_ts = pd.to_datetime(start)
    end_ts = pd.to_datetime(end)

    idx = p_sig.index

    eval_start_candidates = idx[idx >= start_ts]
    if len(eval_start_candidates) == 0:
        raise ValueError("START_DATE is after available data.")
    eval_start = eval_start_candidates[0]

    prev_idx = idx[idx < eval_start]
    if len(prev_idx) == 0:
        raise ValueError("Not enough history before START_DATE to compute signals.")
    first_signal_dt = prev_idx[-1]

    p = p_sig.loc[(p_sig.index >= first_signal_dt) & (p_sig.index <= end_ts)].copy()
    if len(p) < 3:
        raise ValueError("Not enough period points in the selected window.")

    # returns for next-period application
    rets = p[["SPY", "QQQ", "GLD", "SLV"]].pct_change().fillna(0.0)

    # initial weights from first signal row apply to next period
    w_spy, w_qqq, w_gld, w_slv, _ = compute_targets(p.iloc[0])
    curr_w = np.array([w_spy, w_qqq, w_gld, w_slv], dtype=float)

    equity = START_CAPITAL
    peak_equity = START_CAPITAL

    defensive = False
    reentry_counter = 0

    rows = []

    for i in range(1, len(p)):
        dt = p.index[i]

        # apply returns over this period using current weights
        r = rets.iloc[i]
        equity *= (
            1.0
            + curr_w[0] * r["SPY"]
            + curr_w[1] * r["QQQ"]
            + curr_w[2] * r["GLD"]
            + curr_w[3] * r["SLV"]
        )

        # drawdown
        peak_equity = max(peak_equity, equity)
        dd = equity / peak_equity - 1.0

        # defensive trigger
        if dd <= MAX_DRAWDOWN:
            defensive = True
            reentry_counter = 0

        # regime from previous period-end (no lookahead)
        spy_on = bool(p.iloc[i-1]["SPY_ON"])

        # exit defensive with confirmation
        if defensive:
            if spy_on:
                reentry_counter += 1
            else:
                reentry_counter = 0

            if reentry_counter >= REENTRY_CONFIRM:
                defensive = False

        # target weights for NEXT period from prev period signals
        if defensive:
            # force to GLD only (pure defense)
            tgt_w = np.array([0.0, 0.0, 1.0, 0.0], dtype=float)
            reason = "DEFENSIVE: drawdown control"
            curr_w = tgt_w.copy()
            rebalanced = True
        else:
            tgt_spy, tgt_qqq, tgt_gld, tgt_slv, reason = compute_targets(p.iloc[i-1])
            tgt_w = np.array([tgt_spy, tgt_qqq, tgt_gld, tgt_slv], dtype=float)
            curr_w, rebalanced = apply_rebalance_threshold(curr_w, tgt_w, REB_THRESHOLD)

        rows.append({
            "Date": dt,
            "Equity": equity,
            "Drawdown": dd,
            "Defensive": defensive,
            "wSPY": curr_w[0],
            "wQQQ": curr_w[1],
            "wGLD": curr_w[2],
            "wSLV": curr_w[3],
            "Rebalanced": rebalanced,
            "Reason": reason,
            "SPY_ON": spy_on,
            "SPY_SMA": float(p.iloc[i-1]["SPY_SMA"]) if pd.notna(p.iloc[i-1]["SPY_SMA"]) else np.nan,
            "SPY_GLD_Z": float(p.iloc[i-1]["SPY_GLD_Z"]) if pd.notna(p.iloc[i-1]["SPY_GLD_Z"]) else np.nan,
            "GSR": float(p.iloc[i-1]["GSR"]) if pd.notna(p.iloc[i-1]["GSR"]) else np.nan,
            "ALLOW_SLV": bool(p.iloc[i-1]["ALLOW_SLV"]) if pd.notna(p.iloc[i-1]["ALLOW_SLV"]) else False,
        })

    bt = pd.DataFrame(rows).set_index("Date")
    return bt


# =========================
# PLOT + EXPORT
# =========================
def plot_and_export(bt: pd.DataFrame, p_sig: pd.DataFrame, start: str, end: str) -> None:
    os.makedirs(EXPORT_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    csv_path = os.path.join(EXPORT_DIR, f"bt_spyqqqgldslv_{start}_{end}_{stamp}.csv".replace(":", ""))
    bt.to_csv(csv_path)
    print(f"[OK] Saved CSV: {csv_path}")

    # Align buy&hold to bt index (same base, same dates)
    px = p_sig.loc[p_sig.index.isin(bt.index), ["SPY", "QQQ", "GLD", "SLV"]].copy().loc[bt.index]

    bh_spy = START_CAPITAL * (px["SPY"] / px["SPY"].iloc[0])
    bh_qqq = START_CAPITAL * (px["QQQ"] / px["QQQ"].iloc[0])
    bh_gld = START_CAPITAL * (px["GLD"] / px["GLD"].iloc[0])
    bh_slv = START_CAPITAL * (px["SLV"] / px["SLV"].iloc[0])

    # view window
    end_dt = bt.index[-1]
    start_view = max(bt.index[0], end_dt - pd.DateOffset(years=LOOKBACK_YEARS_VIEW))

    bt_v = bt.loc[bt.index >= start_view]
    bh_spy_v = bh_spy.loc[bh_spy.index >= start_view]
    bh_qqq_v = bh_qqq.loc[bh_qqq.index >= start_view]
    bh_gld_v = bh_gld.loc[bh_gld.index >= start_view]
    bh_slv_v = bh_slv.loc[bh_slv.index >= start_view]

    fig = plt.figure(figsize=FIGSIZE, constrained_layout=True)
    gs = fig.add_gridspec(3, 1, height_ratios=[3.6, 2.0, 1.2])

    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[1, 0], sharex=ax0)
    ax2 = fig.add_subplot(gs[2, 0], sharex=ax0)

    # --- Top: equity curves ---
    ax0.plot(bt_v.index, bt_v["Equity"], linewidth=3, label="Strategy")
    ax0.plot(bh_spy_v.index, bh_spy_v, "--", alpha=0.65, label="Buy&Hold SPY")
    ax0.plot(bh_qqq_v.index, bh_qqq_v, "--", alpha=0.65, label="Buy&Hold QQQ")
    ax0.plot(bh_gld_v.index, bh_gld_v, "--", alpha=0.65, label="Buy&Hold GLD")
    ax0.plot(bh_slv_v.index, bh_slv_v, "--", alpha=0.65, label="Buy&Hold SLV")
    ax0.set_title(f"Quarterly Strategy | SPY/QQQ/GLD/SLV | {start} → {end}")
    ax0.set_ylabel("Value ($)")
    ax0.grid(True)
    ax0.legend(loc="upper left")

    # drawdown shading (strategy)
    dd_v = bt_v["Drawdown"]
    in_dd = dd_v < 0
    start_dd = None
    for dt, flag in in_dd.items():
        if flag and start_dd is None:
            start_dd = dt
        elif (not flag) and start_dd is not None:
            ax0.axvspan(start_dd, dt, alpha=0.12)
            start_dd = None
    if start_dd is not None:
        ax0.axvspan(start_dd, in_dd.index[-1], alpha=0.12)

    # allocation labels (only when changed)
    prev_label = None
    for dt in bt_v.index:
        row = bt_v.loc[dt]
        label = f"{round(row['wSPY']*100):.0f}/{round(row['wQQQ']*100):.0f}/{round(row['wGLD']*100):.0f}/{round(row['wSLV']*100):.0f}"
        if label != prev_label:
            ax0.text(dt, float(row["Equity"]), label, fontsize=8, rotation=90, alpha=0.7,
                     ha="center", va="bottom")
            prev_label = label

    # --- Middle: relative performance + z-score ---
    perf = pd.DataFrame(index=bt_v.index)
    perf["Strategy"] = bt_v["Equity"] / bt_v["Equity"].iloc[0] - 1.0
    perf["SPY"] = bh_spy_v / bh_spy_v.iloc[0] - 1.0
    perf["QQQ"] = bh_qqq_v / bh_qqq_v.iloc[0] - 1.0
    perf["GLD"] = bh_gld_v / bh_gld_v.iloc[0] - 1.0
    perf["SLV"] = bh_slv_v / bh_slv_v.iloc[0] - 1.0

    ax1.plot(perf.index, perf["Strategy"], linewidth=3, label="Strategy")
    ax1.plot(perf.index, perf["SPY"], label="SPY")
    ax1.plot(perf.index, perf["QQQ"], label="QQQ")
    ax1.plot(perf.index, perf["GLD"], label="GLD")
    ax1.plot(perf.index, perf["SLV"], label="SLV")
    ax1.set_title("Relative Performance (quarterly) + SPY/GLD z-score")
    ax1.set_ylabel("Return (fraction)")
    ax1.grid(True)
    ax1.legend(loc="upper left")

    ax1b = ax1.twinx()
    ax1b.plot(bt_v.index, bt_v["SPY_GLD_Z"], linestyle=":", linewidth=2, label="SPY/GLD z")
    ax1b.axhline(Z_HIGH, alpha=0.25, linewidth=1)
    ax1b.axhline(Z_LOW, alpha=0.25, linewidth=1)
    ax1b.set_ylabel("SPY/GLD z-score")
    ax1b.legend(loc="upper right")

    # --- Bottom: allocation strip ---
    w = bt_v[["wSPY", "wQQQ", "wGLD", "wSLV"]]
    ax2.stackplot(w.index, w["wSPY"], w["wQQQ"], w["wGLD"], w["wSLV"],
                 labels=["SPY", "QQQ", "GLD", "SLV"], alpha=0.85)
    ax2.set_title("Recommended Weights Over Time (quarterly)")
    ax2.set_ylabel("Weight")
    ax2.set_ylim(0, 1)
    ax2.grid(True)
    ax2.legend(loc="upper left")

    png_path = os.path.join(EXPORT_DIR, f"plot_spyqqqgldslv_{start}_{end}_{stamp}.png".replace(":", ""))
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Saved PNG: {png_path}")


# =========================
# SUMMARY METRICS
# =========================
def summarize(bt: pd.DataFrame, p_sig: pd.DataFrame) -> None:
    final_val = float(bt["Equity"].iloc[-1])
    total_ret = final_val / START_CAPITAL - 1.0
    years = (bt.index[-1] - bt.index[0]).days / 365.25
    cagr = (1.0 + total_ret) ** (1.0 / years) - 1.0 if years > 0 else np.nan

    max_dd = float(bt["Drawdown"].min())
    max_dd_dur = max_drawdown_duration(bt["Drawdown"])

    # Benchmarks aligned to bt dates
    px = p_sig.loc[p_sig.index.isin(bt.index), ["SPY", "QQQ", "GLD", "SLV"]].copy().loc[bt.index]

    def bench_stats(series: pd.Series) -> tuple[float, float, float, int]:
        eq = START_CAPITAL * (series / series.iloc[0])
        tr = float(eq.iloc[-1] / START_CAPITAL - 1.0)
        c = (1.0 + tr) ** (1.0 / years) - 1.0 if years > 0 else np.nan
        dd = drawdown_series(eq)
        return float(eq.iloc[-1]), tr, c, max_drawdown_duration(dd)

    spy_final, spy_tr, spy_cagr, spy_dd_dur = bench_stats(px["SPY"])
    qqq_final, qqq_tr, qqq_cagr, qqq_dd_dur = bench_stats(px["QQQ"])

    # max drawdowns for benchmarks
    spy_dd = float(drawdown_series(START_CAPITAL * (px["SPY"] / px["SPY"].iloc[0])).min())
    qqq_dd = float(drawdown_series(START_CAPITAL * (px["QQQ"] / px["QQQ"].iloc[0])).min())

    print("\n==============================")
    print(f"Window: {bt.index[0].date()} → {bt.index[-1].date()}  ({years:.2f} years)")
    print(f"Decision frequency: {DECISION_FREQ} (periods = quarters)")
    print(f"Strategy final: ${final_val:,.0f} | Total: {total_ret:.2%} | CAGR: {cagr:.2%}")
    print(f"Strategy Max drawdown: {max_dd:.2%} | Max DD duration (quarters): {max_dd_dur}")
    print("---")
    print(f"100% SPY final: ${spy_final:,.0f} | Total: {spy_tr:.2%} | CAGR: {spy_cagr:.2%}")
    print(f"SPY Max drawdown: {spy_dd:.2%} | Max DD duration (quarters): {spy_dd_dur}")
    print("---")
    print(f"100% QQQ final: ${qqq_final:,.0f} | Total: {qqq_tr:.2%} | CAGR: {qqq_cagr:.2%}")
    print(f"QQQ Max drawdown: {qqq_dd:.2%} | Max DD duration (quarters): {qqq_dd_dur}")
    print("==============================\n")

    last = bt.iloc[-1]
    last_label = (
        f"{round(last['wSPY']*100):.0f}/"
        f"{round(last['wQQQ']*100):.0f}/"
        f"{round(last['wGLD']*100):.0f}/"
        f"{round(last['wSLV']*100):.0f}"
    )
    print(f"LAST RECOMMENDATION (SPY/QQQ/GLD/SLV %): {last_label}")
    print(f"Last reason: {last['Reason']}")


# =========================
# MAIN
# =========================
def main():
    os.makedirs(EXPORT_DIR, exist_ok=True)

    print("Downloading data from yfinance...")
    daily = download_prices(START_DATE, END_DATE)

    # Quarter-end prices
    p = to_period_end(daily)

    # Keep required cols and drop NA after resample
    p = p[["SPY", "QQQ", "GLD", "SLV", "GOLD_F", "SILVER_F"]].dropna()

    # Signals (built on padded history)
    p_sig = build_signals(p)

    # Need enough history for SMA + z-score
    p_sig = p_sig.dropna(subset=["SPY_SMA", "SPY_GLD_Z", "GSR", "SPY_ON", "ALLOW_SLV"])

    bt = run_backtest(p_sig, START_DATE, END_DATE)

    plot_and_export(bt, p_sig, START_DATE, END_DATE)
    summarize(bt, p_sig)


if __name__ == "__main__":
    main()