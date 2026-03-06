#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Feb  1 09:25:18 2026

@author: michaelwai
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Quarterly Dynamic Allocation Strategy (STOCK / GLD / SLV)

Decision frequency: QUARTER-END (QE)

Signals and weights are computed at quarter-end using ONLY information available
up to the prior quarter-end. The resulting weights are applied over the next
quarter return (no lookahead).

Layers:
1) STOCK trend filter (10-period SMA with 2-period hysteresis)  [period = quarter]
2) STOCK/Gold (STOCK/GLD) valuation tilt using z-score bands     [period = quarter]
3) Gold/Silver ratio (GSR) to optionally add SLV when silver is cheap vs gold

Outputs:
- CSV of signals/weights/equity
- PNG plot: equity vs buy&hold + drawdown shading + STOCK/GLD z-score axis + allocation strip
- Console summary: total return, CAGR, max drawdown, max drawdown duration (periods), plus 100% STOCK benchmark
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
STOCK_TICKER = "SPY"
TICKER1="QQQ"
TICKER2="SPY"

STOCK_TICKER = "SPY"
TICKER1="QQQ"
TICKER2="BRK-B"

START_DATE = "2012-05-01"
END_DATE   = "2025-02-01"
START_CAPITAL = 1_000_000

EXPORT_DIR = os.path.abspath("./outputs_stock_gold_gsr_quarterly")


# =========================
# STRATEGY PARAMETERS
# =========================
DECISION_FREQ = "QE"         # quarter-end resample

# Trend filter (period=quarter)
SMA_PERIODS = 10
HYSTERESIS_N = 2

# Rebalance threshold
REB_THRESHOLD = 0.05         # rebalance if any weight changes by >= 5%

# Drawdown control (periods=quarters)
MAX_DRAWDOWN = -0.10         # trigger defensive at -10%
REENTRY_CONFIRM = 2          # require N consecutive periods STOCK_ON to exit defensive

# STOCK/GLD z-score tilt (period=quarter)
Z_WIN_PERIODS = 24           # rolling window (quarters)
Z_HIGH = 1.0
Z_LOW  = -1.0

STOCK_WEIGHT_BASE_ON = 0.85
W_STOCK_TILT_HIGH = 0.50     # when z > Z_HIGH
W_STOCK_TILT_LOW  = 1.00     # when z < Z_LOW

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
    Pandas commonly supports 'Q' / 'Q-DEC'. Newer versions also accept 'QE'.
    We normalize 'QE' -> 'Q' as a safer default.
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

    # MultiIndex columns: ('Close', 'AAPL') etc
    if isinstance(obj.columns, pd.MultiIndex):
        if ("Close" in obj.columns.get_level_values(0)):
            close_df = obj.loc[:, ("Close", slice(None))]
            # take first column (for single ticker downloads)
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
    Download daily adjusted prices for STOCK/GLD/SLV and futures proxies for gold/silver.
    Uses auto_adjust=True (split/dividend adjusted).
    """
    pad_start = (pd.to_datetime(start) - pd.DateOffset(years=10)).strftime("%Y-%m-%d")

    # ETFs + stock together
    tickers_main = [STOCK_TICKER, TICKER1, TICKER2]

    main_raw = yf.download(
        tickers_main,
        start=pad_start,
        end=end,
        auto_adjust=True,
        progress=False,
        group_by="column",
        threads=True,
    )

    # main_raw can be MultiIndex with fields at level 0
    if isinstance(main_raw.columns, pd.MultiIndex):
        if "Close" not in main_raw.columns.get_level_values(0):
            raise KeyError("Main download missing Close.")
        main_close = main_raw["Close"].copy()
    else:
        # single ticker fallback (unlikely here)
        main_close = main_raw[["Close"]].copy()
        main_close.columns = tickers_main

    # Futures proxies for GSR
    gold_raw = yf.download("GC=F", start=pad_start, end=end, auto_adjust=True, progress=False)
    silver_raw = yf.download("SI=F", start=pad_start, end=end, auto_adjust=True, progress=False)

    gold = extract_close(gold_raw, "GOLD_F")
    silver = extract_close(silver_raw, "SILVER_F")

    df = pd.concat([main_close, gold, silver], axis=1)

    # Rename columns to stable names
    rename_map = {}
    if STOCK_TICKER in df.columns:
        rename_map[STOCK_TICKER] = "STOCK"
    df = df.rename(columns=rename_map)

    # Some rows may have missing futures while ETFs exist or vice versa
    df = df.dropna(subset=["STOCK", TICKER1, TICKER2, "GOLD_F", "SILVER_F"], how="any")
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
def pick_stock_weight_when_on(z: float) -> float:
    if np.isnan(z):
        return STOCK_WEIGHT_BASE_ON
    if z > Z_HIGH:
        return W_STOCK_TILT_HIGH
    if z < Z_LOW:
        return W_STOCK_TILT_LOW
    return STOCK_WEIGHT_BASE_ON


def metals_split(gsr: float, allow_slv: bool, risk_on: bool) -> tuple[float, float]:
    if not allow_slv:
        return 1.0, 0.0
    slv_share = SLV_SHARE_IN_METALS_WHEN_ON if risk_on else SLV_SHARE_IN_METALS_WHEN_OFF
    return 1.0 - slv_share, slv_share


def compute_targets(row_prev: pd.Series) -> tuple[float, float, float, str]:
    stock_on = bool(row_prev["STOCK_ON"])
    z = float(row_prev["STOCK_GLD_Z"])
    gsr = float(row_prev["GSR"])
    allow_slv = bool(row_prev["ALLOW_SLV"])

    if stock_on:
        w_stock = pick_stock_weight_when_on(z)
        metals = 1.0 - w_stock
        w_g_m, w_s_m = metals_split(gsr, allow_slv, risk_on=True)
        w_gld = metals * w_g_m
        w_slv = metals * w_s_m
        reason = f"ON: z={z:.2f} gsr={gsr:.1f} allow_slv={allow_slv}"
    else:
        w_stock = 0.0
        metals = 1.0
        w_g_m, w_s_m = metals_split(gsr, allow_slv, risk_on=False)
        w_gld = metals * w_g_m
        w_slv = metals * w_s_m
        reason = f"OFF: gsr={gsr:.1f} allow_slv={allow_slv}"

    s = w_stock + w_gld + w_slv
    if s <= 0:
        return 0.0, 1.0, 0.0, "fallback"
    return w_stock / s, w_gld / s, w_slv / s, reason


def apply_rebalance_threshold(curr_w: np.ndarray, tgt_w: np.ndarray, thr: float) -> tuple[np.ndarray, bool]:
    if np.max(np.abs(tgt_w - curr_w)) >= thr:
        return tgt_w, True
    return curr_w, False


# =========================
# SIGNALS
# =========================
def build_signals(p: pd.DataFrame) -> pd.DataFrame:
    """
    p: period-end prices with columns: STOCK, GLD, SLV, GOLD_F, SILVER_F
    Adds:
      STOCK_SMA
      STOCK_ON (hysteresis)
      STOCK_GLD
      STOCK_GLD_Z
      GSR
      ALLOW_SLV (stateful)
    """
    out = p.copy()

    out["STOCK_SMA"] = out["STOCK"].rolling(SMA_PERIODS).mean()
    raw_on = out["STOCK"] > out["STOCK_SMA"]
    out["STOCK_ON"] = compute_hysteresis_regime(raw_on, HYSTERESIS_N)

    out["STOCK_GLD"] = out["STOCK"] / out[TICKER1]
    roll_mean = out["STOCK_GLD"].rolling(Z_WIN_PERIODS).mean()
    roll_std = out["STOCK_GLD"].rolling(Z_WIN_PERIODS).std(ddof=0)
    out["STOCK_GLD_Z"] = (out["STOCK_GLD"] - roll_mean) / roll_std

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

    rets = p[["STOCK", TICKER1, TICKER2]].pct_change().fillna(0.0)

    # initial weights from first signal row apply to next period
    w_stock, w_gld, w_slv, reason0 = compute_targets(p.iloc[0])
    curr_w = np.array([w_stock, w_gld, w_slv], dtype=float)

    equity = START_CAPITAL
    peak_equity = START_CAPITAL

    defensive = False
    reentry_counter = 0

    rows = []

    for i in range(1, len(p)):
        dt = p.index[i]

        # apply returns over this period using current weights
        r = rets.iloc[i]
        equity *= (1.0 + curr_w[0]*r["STOCK"] + curr_w[1]*r[TICKER1] + curr_w[2]*r[TICKER2])

        # drawdown
        peak_equity = max(peak_equity, equity)
        dd = equity / peak_equity - 1.0

        # defensive trigger
        if dd <= MAX_DRAWDOWN:
            defensive = True
            reentry_counter = 0

        # regime from previous period-end (no lookahead)
        stock_on = bool(p.iloc[i-1]["STOCK_ON"])

        # exit defensive with confirmation
        if defensive:
            if stock_on:
                reentry_counter += 1
            else:
                reentry_counter = 0

            if reentry_counter >= REENTRY_CONFIRM:
                defensive = False

        # target weights for NEXT period from prev period signals
        if defensive:
            tgt_w = np.array([0.0, 1.0, 0.0], dtype=float)
            reason = "DEFENSIVE: drawdown control"
            curr_w = tgt_w.copy()  # force immediate
            rebalanced = True
        else:
            tgt_stock, tgt_gld, tgt_slv, reason = compute_targets(p.iloc[i-1])
            tgt_w = np.array([tgt_stock, tgt_gld, tgt_slv], dtype=float)
            curr_w, rebalanced = apply_rebalance_threshold(curr_w, tgt_w, REB_THRESHOLD)

        rows.append({
            "Date": dt,
            "Equity": equity,
            "Drawdown": dd,
            "Defensive": defensive,
            "wSTOCK": curr_w[0],
            "wGLD": curr_w[1],
            "wSLV": curr_w[2],
            "Rebalanced": rebalanced,
            "Reason": reason,
            "STOCK_ON": stock_on,
            "STOCK_SMA": float(p.iloc[i-1]["STOCK_SMA"]) if pd.notna(p.iloc[i-1]["STOCK_SMA"]) else np.nan,
            "STOCK_GLD_Z": float(p.iloc[i-1]["STOCK_GLD_Z"]) if pd.notna(p.iloc[i-1]["STOCK_GLD_Z"]) else np.nan,
            "GSR": float(p.iloc[i-1]["GSR"]) if pd.notna(p.iloc[i-1]["GSR"]) else np.nan,
            "ALLOW_SLV": bool(p.iloc[i-1]["ALLOW_SLV"]) if pd.notna(p.iloc[i-1]["ALLOW_SLV"]) else False,
        })

    bt = pd.DataFrame(rows).set_index("Date")
    bt["DD_Duration_Periods"] = (bt["Drawdown"] < 0).astype(int).groupby((bt["Drawdown"] >= 0).cumsum()).cumsum()
    return bt


# =========================
# PLOT + EXPORT
# =========================
def plot_and_export(bt: pd.DataFrame, p_sig: pd.DataFrame, start: str, end: str) -> None:
    os.makedirs(EXPORT_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    csv_path = os.path.join(EXPORT_DIR, f"bt_{STOCK_TICKER}_{start}_{end}_{stamp}.csv".replace(":", ""))
    bt.to_csv(csv_path)
    print(f"[OK] Saved CSV: {csv_path}")

    # Align buy&hold to bt index
    px = p_sig.loc[p_sig.index.isin(bt.index), ["STOCK", TICKER1, TICKER2]].copy().loc[bt.index]

    bh_stock = START_CAPITAL * (px["STOCK"] / px["STOCK"].iloc[0])
    bh_gld   = START_CAPITAL * (px[TICKER1]   / px[TICKER1].iloc[0])
    bh_slv   = START_CAPITAL * (px[TICKER2]   / px[TICKER2].iloc[0])

    # view window
    end_dt = bt.index[-1]
    start_view = max(bt.index[0], end_dt - pd.DateOffset(years=LOOKBACK_YEARS_VIEW))

    bt_v = bt.loc[bt.index >= start_view]
    bh_stock_v = bh_stock.loc[bh_stock.index >= start_view]
    bh_gld_v   = bh_gld.loc[bh_gld.index >= start_view]
    bh_slv_v   = bh_slv.loc[bh_slv.index >= start_view]

    fig = plt.figure(figsize=FIGSIZE, constrained_layout=True)
    gs = fig.add_gridspec(3, 1, height_ratios=[3.6, 2.0, 1.2])

    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[1, 0], sharex=ax0)
    ax2 = fig.add_subplot(gs[2, 0], sharex=ax0)
    
    # --- Top: equity curves ---
    ax0.plot(bt_v.index, bt_v["Equity"], linewidth=3, label="Strategy")
    ax0.plot(bh_stock_v.index, bh_stock_v, "--", alpha=0.65, label=f"Buy&Hold {STOCK_TICKER}")
    ax0.plot(bh_gld_v.index, bh_gld_v, "--", alpha=0.65, label=f"Buy&Hold {TICKER1}")
    ax0.plot(bh_slv_v.index, bh_slv_v, "--", alpha=0.65, label=f"Buy&Hold {TICKER2}")
    ax0.set_title(f"Quarterly Strategy | {STOCK_TICKER}/{TICKER1}/{TICKER2} | {start} → {end}")
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

    # allocation labels (only when changed) 0 decimals
    prev_label = None
    for dt in bt_v.index:
        row = bt_v.loc[dt]
        label = f"{round(row['wSTOCK']*100):.0f}/{round(row['wGLD']*100):.0f}/{round(row['wSLV']*100):.0f}"
        if label != prev_label:
            ax0.text(dt, float(row["Equity"]), label, fontsize=8, rotation=90, alpha=0.7,
                     ha="center", va="bottom")
            prev_label = label

    # --- Middle: relative performance + z-score ---
    perf = pd.DataFrame(index=bt_v.index)
    perf["Strategy"] = bt_v["Equity"] / bt_v["Equity"].iloc[0] - 1.0
    perf[STOCK_TICKER] = bh_stock_v / bh_stock_v.iloc[0] - 1.0
    perf[TICKER1] = bh_gld_v / bh_gld_v.iloc[0] - 1.0
    perf[TICKER2] = bh_slv_v / bh_slv_v.iloc[0] - 1.0

    ax1.plot(perf.index, perf["Strategy"], linewidth=3, label="Strategy")
    ax1.plot(perf.index, perf[STOCK_TICKER], label=STOCK_TICKER)
    ax1.plot(perf.index, perf[TICKER1], label=TICKER1)
    ax1.plot(perf.index, perf[TICKER2], label=TICKER2)
    ax1.set_title(f"Relative Performance (quarterly) + STOCK/{TICKER1} z-score")
    ax1.set_ylabel("Return (fraction)")
    ax1.grid(True)
    ax1.legend(loc="upper left")

    ax1b = ax1.twinx()
    ax1b.plot(bt_v.index, bt_v["STOCK_GLD_Z"], linestyle=":", linewidth=2, label=f"{STOCK_TICKER}/{TICKER1} z")
    ax1b.axhline(Z_HIGH, alpha=0.25, linewidth=1)
    ax1b.axhline(Z_LOW, alpha=0.25, linewidth=1)
    ax1b.set_ylabel(f"STOCK/{TICKER1} z-score")
    ax1b.legend(loc="upper right")

    # --- Bottom: allocation strip ---
    w = bt_v[["wSTOCK", "wGLD", "wSLV"]]
    ax2.stackplot(w.index, w["wSTOCK"], w["wGLD"], w["wSLV"],
                 labels=[STOCK_TICKER, TICKER1, TICKER2], alpha=0.85)
    ax2.set_title("Recommended Weights Over Time (quarterly)")
    ax2.set_ylabel("Weight")
    ax2.set_ylim(0, 1)
    ax2.grid(True)
    ax2.legend(loc="upper left")

    png_path = os.path.join(EXPORT_DIR, f"plot_{STOCK_TICKER}_{start}_{end}_{stamp}.png".replace(":", ""))
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

    # STOCK benchmark aligned to bt dates
    px = p_sig.loc[p_sig.index.isin(bt.index), "STOCK"].copy().loc[bt.index]
    stock_final = START_CAPITAL * (px.iloc[-1] / px.iloc[0])
    stock_total = stock_final / START_CAPITAL - 1.0
    stock_cagr = (1.0 + stock_total) ** (1.0 / years) - 1.0 if years > 0 else np.nan

    stock_equity = START_CAPITAL * (px / px.iloc[0])
    stock_dd = drawdown_series(stock_equity)
    stock_max_dd = float(stock_dd.min())
    stock_max_dd_dur = max_drawdown_duration(stock_dd)

    print("\n==============================")
    print(f"Window: {bt.index[0].date()} → {bt.index[-1].date()}  ({years:.2f} years)")
    print(f"Decision frequency: {DECISION_FREQ} (periods = quarters)")
    print(f"Strategy final: ${final_val:,.0f} | Total: {total_ret:.2%} | CAGR: {cagr:.2%}")
    print(f"Strategy Max drawdown: {max_dd:.2%} | Max DD duration (periods): {max_dd_dur}")
    print("---")
    print(
        f"100% {STOCK_TICKER} final: ${stock_final:,.0f} | "
        f"Total: {stock_total:.2%} | CAGR: {stock_cagr:.2%}\n"
        f"{STOCK_TICKER} Max drawdown: {stock_max_dd:.2%} | "
        f"Max DD duration (periods): {stock_max_dd_dur}"
    )
    print("==============================\n")

    last = bt.iloc[-1]
    last_label = f"{round(last['wSTOCK']*100):.0f}/{round(last['wGLD']*100):.0f}/{round(last['wSLV']*100):.0f}"
    print(f"LAST RECOMMENDATION ({STOCK_TICKER}/{TICKER1}/{TICKER2} %): {last_label}")
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
    # Keep required cols only and drop NA after resample
    p = p[["STOCK", TICKER1, TICKER2, "GOLD_F", "SILVER_F"]].dropna()

    # Signals (built on padded history)
    p_sig = build_signals(p)
    # We need enough history for SMA + z-score; drop rows where indicators are NA
    p_sig = p_sig.dropna(subset=["STOCK_SMA", "STOCK_GLD_Z", "GSR", "STOCK_ON", "ALLOW_SLV"])

    bt = run_backtest(p_sig, START_DATE, END_DATE)

    plot_and_export(bt, p_sig, START_DATE, END_DATE)
    summarize(bt, p_sig)


if __name__ == "__main__":
    main()