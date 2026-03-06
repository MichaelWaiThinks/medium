#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Dynamic allocation strategy using:
1) STOCK trend filter (10-month SMA with 2-month hysteresis)
2) STOCK/Gold (STOCK/GLD) valuation tilt using z-score bands
3) Gold/Silver ratio (GSR) to optionally add SLV only when silver is cheap vs gold

Outputs:
- CSV of monthly signals/weights/equity
- PNG plot (equity vs buy&hold + drawdown shading + STOCK/GLD & GSR axes + allocation strip)
- Console summary: total return, CAGR, max drawdown, max DD duration, and comparison vs 100% STOCK

Strategy explained:
    This strategy is a monthly, rules-based dynamic allocation system that rotates between STOCK (US equities), GLD (gold), and SLV (silver) using three independent decision layers: trend, relative valuation, and cross-metal valuation.
The strategy operates strictly at month-end to avoid noise and look-ahead bias. Portfolio decisions for a given month are based only on information available at the previous month-end, and returns are applied over the following month.


1. Equity risk regime (STOCK trend filter)

The first decision is whether equity risk should be taken at all.
STOCK is considered risk-on when its price is above its 10-month simple moving average. To reduce whipsaws, a 2-month hysteresis is applied: STOCK must remain above (or below) the moving average for two consecutive month-ends before the regime switches.
When STOCK is risk-on, the portfolio is allowed to hold STOCK.
When STOCK is risk-off, STOCK exposure is reduced to zero and the portfolio moves fully into metals.
This layer is responsible for avoiding prolonged equity bear markets.

2. Equity vs gold valuation tilt (STOCK / Gold ratio)

When STOCK is risk-on, the strategy adjusts how aggressive the equity allocation should be using the STOCK-to-Gold ratio (STOCK divided by GLD).

A rolling z-score of the STOCK/Gold ratio is computed over a long lookback window (e.g. 5 years):
	•	If STOCK/Gold is high relative to history (z-score above +1), equities are considered expensive versus gold and STOCK exposure is reduced.
	•	If STOCK/Gold is low (z-score below −1), equities are considered cheap versus gold and STOCK exposure is increased.
	•	Otherwise, a neutral STOCK weight is used.
This layer does not attempt to time short-term moves; it provides a slow, macro-level valuation tilt that improves risk-adjusted returns across cycles.

3. Gold vs silver valuation (Gold/Silver ratio)

The third decision determines whether silver should be held alongside gold.
The Gold/Silver ratio (GSR) is used as a relative valuation signal between the two metals:
	•	When the GSR is very high, silver is considered cheap relative to gold and a portion of the metals allocation is shifted into SLV.
	•	When the GSR falls back below a lower threshold, silver exposure is removed and metals revert to gold only.
This decision is implemented as a stateful band (add silver above a high threshold, remove it below a lower threshold) to avoid frequent flipping.
Silver is never held continuously; it is only used tactically when relative valuation is extreme.

4. Portfolio construction

At each month-end, the strategy determines target weights:
	•	If STOCK is risk-on:
	•	Allocate a base percentage to STOCK.
	•	Allocate the remainder to metals (GLD and optionally SLV).
	•	Adjust STOCK weight using the STOCK/Gold valuation tilt.
	•	If STOCK is risk-off:
	•	Allocate 100% to metals.
	•	Split metals between GLD and SLV only if the GSR allows silver exposure.
Weights are normalized to always sum to 100%.

5. Rebalancing discipline

To reduce turnover, the portfolio only rebalances when the difference between current weights and target weights exceeds a predefined threshold (e.g. 5%).
This allows the strategy to remain invested through minor signal fluctuations while still responding decisively to regime changes.

6. Simulation window

The portfolio starts with a fixed initial capital at the first month-end after the specified start date and compounds until the specified end date.
All performance metrics (return, CAGR, drawdown) are calculated strictly within this window, allowing realistic “what-if I started then” simulations.


7. Design philosophy

The strategy is not optimized for short-term trading. Its objective is to:
	•	Participate fully in long equity bull markets
	•	Reduce exposure during equity bear markets
	•	Use gold as a defensive and rebalancing asset
	•	Use silver opportunistically only when relative valuation is extreme

Outperformance versus STOCK, when it occurs, comes primarily from drawdown avoidance and valuation-aware exposure, not from market timing.
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
STOCK_TICKER = "AAPL"

START_DATE = "2020-05-01"
END_DATE   = "2026-02-01"
START_CAPITAL = 1_000_000
EXPORT_DIR = os.path.abspath("./outputs_stock_gold_gsr")

# =========================
# STRATEGY PARAMETERS
# =========================
DECISION_FREQ = "ME"          # month-end
SMA_MONTHS = 10               # trend filter for STOCK
HYSTERESIS_N = 2              # require 2 consecutive months to switch ON/OFF
REB_THRESHOLD = 0.05          # rebalance only if any weight changes by >= 5%

# ===== Drawdown control =====
MAX_DRAWDOWN = -0.10        # -10%
MAX_DD_MONTHS = 3           # 3 consecutive months underwater
REENTRY_CONFIRM = 2         # 2 months STOCK_ON to exit defensive

# STOCK/GLD z-score tilt (computed on trailing window)
Z_WIN_MONTHS = 24             # 5 years rolling stats
Z_HIGH = 1.0                  # expensive equities vs gold -> tilt to GLD
Z_LOW  = -1.0                 # cheap equities vs gold -> tilt to STOCK

# Tilt target weights when STOCK trend ON:
W_STOCK_TILT_HIGH = 0.50        # when STOCK/GLD zscore > Z_HIGH (equity expensive vs gold)
# otherwise use STOCK_WEIGHT_BASE_ON
# W_STOCK_TILT_LOW  = 0.85        # when STOCK/GLD zscore < Z_LOW  (equity cheap vs gold)
# STOCK_WEIGHT_BASE_ON = 0.70     # base STOCK weight when trend is ON (before tilt)
W_STOCK_TILT_LOW = 1.00
STOCK_WEIGHT_BASE_ON =0.85  # optional

# Silver only when GSR high (silver cheap vs gold)
GSR_ADD_SLV = 85              # if GSR > 85, allow SLV in metals sleeve
GSR_REMOVE_SLV = 75           # if GSR < 75, force SLV to 0 in metals sleeve
SLV_SHARE_IN_METALS_WHEN_ON = 0.40  # if allowed, % of metals sleeve allocated to SLV
SLV_SHARE_IN_METALS_WHEN_OFF = 0.60 # if risk-off and allowed, SLV share in metals sleeve


# =========================
# UTILITIES
# =========================
def download_prices(start: str, end: str) -> pd.DataFrame:
    """
    Download daily adjusted close prices for STOCK/GLD/SLV and futures proxies for gold/silver.
    Uses auto_adjust=True to work in total-return-ish space (splits/dividends adjusted).
    """
    # Pull more history than needed for indicators (SMA + rolling zscore)
    pad_start = (pd.to_datetime(start) - pd.DateOffset(years=10)).strftime("%Y-%m-%d")

    tickers_etf = [STOCK_TICKER, "GLD", "SLV"]
    etf = yf.download(
        tickers_etf,
        start=pad_start,
        end=end,
        auto_adjust=True,
        progress=False,
        group_by="column",
        threads=True
    )["Close"]

    # gold = yf.download("GC=F", start=pad_start, end=end, auto_adjust=True, progress=False)["Close"].rename("GOLD_F")
    # silver = yf.download("SI=F", start=pad_start, end=end, auto_adjust=True, progress=False)["Close"].rename("SILVER_F")
    gold = yf.download("GC=F", start=pad_start, end=end, auto_adjust=True, progress=False)
    silver = yf.download("SI=F", start=pad_start, end=end, auto_adjust=True, progress=False)
    
    def extract_close(obj, name):
        """
        Robustly extract a Close Series from yfinance output
        """
        # Case 1: already a Series
        if isinstance(obj, pd.Series):
            s = obj
    
        # Case 2: DataFrame
        elif isinstance(obj, pd.DataFrame):
            # MultiIndex columns
            if isinstance(obj.columns, pd.MultiIndex):
                s = obj.loc[:, ("Close", slice(None))]
                s = s.iloc[:, 0]
            else:
                s = obj["Close"]
    
        else:
            raise TypeError(f"Unexpected type: {type(obj)}")
    
        s = s.copy()
        s.name = name
        return s
    
    
    # ---- download ----
    gold_raw = yf.download("GC=F", start=pad_start, end=end,
                            auto_adjust=True, progress=False)
    
    silver_raw = yf.download("SI=F", start=pad_start, end=end,
                              auto_adjust=True, progress=False)
    
    # ---- normalize ----
    gold = extract_close(gold_raw, "GOLD_F")
    silver = extract_close(silver_raw, "SILVER_F")
   
    df = pd.concat([etf, gold, silver], axis=1).dropna()
    df = df.rename(columns={STOCK_TICKER: STOCK_TICKER, "GLD": "GLD", "SLV": "SLV"})
    return df


def to_month_end(df_daily: pd.DataFrame) -> pd.DataFrame:
    return df_daily.resample(DECISION_FREQ).last()


def compute_hysteresis_regime(raw_on: pd.Series, n: int) -> pd.Series:
    """
    raw_on: boolean series (True=ON) for each month-end.
    Returns regime with hysteresis: require n consecutive True to turn ON, n consecutive False to turn OFF.
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
    Max consecutive months underwater (dd < 0).
    Returns duration in months.
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
    """
    Returns (w_gld_in_metals, w_slv_in_metals)
    """
    if not allow_slv:
        return 1.0, 0.0

    slv_share = SLV_SHARE_IN_METALS_WHEN_ON if risk_on else SLV_SHARE_IN_METALS_WHEN_OFF
    return 1.0 - slv_share, slv_share


def compute_targets(row_prev: pd.Series) -> tuple[float, float, float, str]:
    """
    Use previous month-end signals to set weights for next month.
    """
    stock_on = bool(row_prev["STOCK_ON"])
    z = float(row_prev["STOCK_GLD_Z"])
    gsr = float(row_prev["GSR"])

    # SLV permission with hysteresis band (add above 85, remove below 75)
    # We carry "ALLOW_SLV" state in dataframe, so use that.
    allow_slv = bool(row_prev["ALLOW_SLV"])

    if stock_on:
        w_spy = pick_stock_weight_when_on(z)
        metals = 1.0 - w_spy
        w_g_m, w_s_m = metals_split(gsr, allow_slv, risk_on=True)
        w_gld = metals * w_g_m
        w_slv = metals * w_s_m
        reason = f"ON: z={z:.2f} gsr={gsr:.1f} allow_slv={allow_slv}"
    else:
        w_spy = 0.0
        metals = 1.0
        w_g_m, w_s_m = metals_split(gsr, allow_slv, risk_on=False)
        w_gld = metals * w_g_m
        w_slv = metals * w_s_m
        reason = f"OFF: gsr={gsr:.1f} allow_slv={allow_slv}"

    # normalize (safety)
    s = w_spy + w_gld + w_slv
    if s <= 0:
        return 0.0, 1.0, 0.0, "fallback"
    return w_spy / s, w_gld / s, w_slv / s, reason


def apply_rebalance_threshold(curr_w: np.ndarray, tgt_w: np.ndarray, thr: float) -> tuple[np.ndarray, bool]:
    if np.max(np.abs(tgt_w - curr_w)) >= thr:
        return tgt_w, True
    return curr_w, False


# =========================
# BACKTEST
# =========================
def build_signals(m: pd.DataFrame) -> pd.DataFrame:
    """
    m: month-end prices with columns STOCK, GLD, SLV, GOLD_F, SILVER_F
    Adds:
      STOCK_SMA
      STOCK_ON (with hysteresis)
      STOCK_GLD (ratio)
      STOCK_GLD_Z (rolling z-score)
      GSR (gold/silver)
      ALLOW_SLV (stateful band)
    """
    out = m.copy()

    out["STOCK_SMA"] = out[STOCK_TICKER].rolling(SMA_MONTHS).mean()
    raw_on = out[STOCK_TICKER] > out["STOCK_SMA"]
    out["STOCK_ON"] = compute_hysteresis_regime(raw_on, HYSTERESIS_N)

    out["STOCK_GLD"] = out[STOCK_TICKER] / out["GLD"]
    roll_mean = out["STOCK_GLD"].rolling(Z_WIN_MONTHS).mean()
    roll_std = out["STOCK_GLD"].rolling(Z_WIN_MONTHS).std(ddof=0)
    out["STOCK_GLD_Z"] = (out["STOCK_GLD"] - roll_mean) / roll_std

    out["GSR"] = out["GOLD_F"] / out["SILVER_F"]

    # Build ALLOW_SLV as a state machine
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

def run_backtest(m_sig: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    start_ts = pd.to_datetime(start)
    end_ts = pd.to_datetime(end)

    idx = m_sig.index
    eval_start = idx[idx >= start_ts]
    if len(eval_start) == 0:
        raise ValueError("START_DATE is after available data.")
    eval_start = eval_start[0]

    prev_idx = idx[idx < eval_start]
    if len(prev_idx) == 0:
        raise ValueError("Not enough history before START_DATE to compute signals.")
    first_signal_dt = prev_idx[-1]

    m = m_sig.loc[(m_sig.index >= first_signal_dt) & (m_sig.index <= end_ts)].copy()
    if len(m) < 3:
        raise ValueError("Not enough monthly points in the selected window.")

    rets = m[[STOCK_TICKER, "GLD", "SLV"]].pct_change().fillna(0.0)

    # initial weights
    w_spy, w_gld, w_slv, reason = compute_targets(m.iloc[0])
    curr_w = np.array([w_spy, w_gld, w_slv], dtype=float)

    equity = START_CAPITAL
    peak_equity = START_CAPITAL

    drawdown_months = 0
    defensive = False
    reentry_counter = 0

    rows = []

    for i in range(1, len(m)):
        dt = m.index[i]

        # ---------- APPLY RETURNS ----------
        r = rets.iloc[i]
        equity *= (
            1.0
            + curr_w[0] * r[STOCK_TICKER]
            + curr_w[1] * r["GLD"]
            + curr_w[2] * r["SLV"]
        )

        # ---------- DRAWDOWN ----------
        peak_equity = max(peak_equity, equity)
        drawdown = equity / peak_equity - 1.0

        if drawdown < 0:
            drawdown_months += 1
        else:
            drawdown_months = 0

        # ---------- ENTER DEFENSIVE ----------
        if (drawdown <= MAX_DRAWDOWN) : #or (drawdown_months >= MAX_DD_MONTHS):
            defensive = True
            reentry_counter = 0

        # ---------- EXIT DEFENSIVE ----------
        stock_on = bool(m.iloc[i-1]["STOCK_ON"])
        if defensive:
            if stock_on:
                reentry_counter += 1
            else:
                reentry_counter = 0

            if reentry_counter >= REENTRY_CONFIRM:
                defensive = False
                drawdown_months = 0

        # ---------- TARGET WEIGHTS ----------
        if defensive:
            tgt_w = np.array([0.0, 1.0, 0.0])
            reason = "DEFENSIVE: drawdown control"
            curr_w = tgt_w.copy()   # BYPASS rebalance threshold
            rebalanced = True
        else:
            tgt_spy, tgt_gld, tgt_slv, reason = compute_targets(m.iloc[i-1])
            tgt_w = np.array([tgt_spy, tgt_gld, tgt_slv])
            curr_w, rebalanced = apply_rebalance_threshold(curr_w, tgt_w, REB_THRESHOLD)

        rows.append({
            "Date": dt,
            "Equity": equity,
            "Drawdown": drawdown,
            "DD_Months": drawdown_months,
            "Defensive": defensive,
            "wSTOCK": curr_w[0],
            "wGLD": curr_w[1],
            "wSLV": curr_w[2],
            "Rebalanced": rebalanced,
            "Reason": reason,
            "STOCK_ON": stock_on,
            "STOCK_GLD_Z": float(m.iloc[i-1]["STOCK_GLD_Z"]),
            "GSR": float(m.iloc[i-1]["GSR"]),
            "ALLOW_SLV": bool(m.iloc[i-1]["ALLOW_SLV"]),
        })

    bt = pd.DataFrame(rows).set_index("Date")
    return bt
# =========================
# PLOT + EXPORT
# =========================
def plot_and_export(bt: pd.DataFrame, m_prices: pd.DataFrame, start: str, end: str) -> None:
    os.makedirs(EXPORT_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    csv_path = os.path.join(EXPORT_DIR, f"bt_{start}_{end}_{stamp}.csv".replace(":", ""))
    bt.to_csv(csv_path)
    print(f"[OK] Saved CSV: {csv_path}")

    # Buy & hold series (aligned)
    px = m_prices.loc[m_prices.index.isin(bt.index), [STOCK_TICKER, "GLD", "SLV"]].copy()
    px = px.loc[bt.index]
    bh_spy = START_CAPITAL * (px[STOCK_TICKER] / px[STOCK_TICKER].iloc[0])
    bh_gld = START_CAPITAL * (px["GLD"] / px["GLD"].iloc[0])
    bh_slv = START_CAPITAL * (px["SLV"] / px["SLV"].iloc[0])

    # Plot last N years view (but results computed strictly start->end)
    end_dt = bt.index[-1]
    start_view = max(bt.index[0], end_dt - pd.DateOffset(years=LOOKBACK_YEARS_VIEW))
    bt_v = bt.loc[bt.index >= start_view]
    bh_stock_v = bh_spy.loc[bh_spy.index >= start_view]
    bh_gld_v = bh_gld.loc[bh_gld.index >= start_view]
    bh_slv_v = bh_slv.loc[bh_slv.index >= start_view]

    dd_v = bt_v["Drawdown"]

    fig = plt.figure(figsize=(20, 14), constrained_layout=True)
    gs = fig.add_gridspec(3, 1, height_ratios=[3.6, 2.0, 1.2])

    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[1, 0], sharex=ax0)
    ax2 = fig.add_subplot(gs[2, 0], sharex=ax0)

    # Top: equity + drawdown shading + allocation labels (only when changed)
    ax0.plot(bt_v.index, bt_v["Equity"], linewidth=3, label="Strategy")
    ax0.plot(bh_stock_v.index, bh_stock_v, "--", alpha=0.6, label="Buy&Hold STOCK")
    ax0.plot(bh_gld_v.index, bh_gld_v, "--", alpha=0.6, label="Buy&Hold GLD")
    ax0.plot(bh_slv_v.index, bh_slv_v, "--", alpha=0.6, label="Buy&Hold SLV")
    ax0.set_title(f"Strategy (STOCK trend + STOCK/Gold tilt + GSR silver) | {start} → {end}")
    ax0.set_ylabel("Value ($)")
    ax0.grid(True)
    ax0.legend(loc="upper left")

    # drawdown shading
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

    # allocation labels (0 decimals), only when changed
    prev_label = None
    for dt in bt_v.index:
        row = bt_v.loc[dt]
        label = f"{round(row['wSTOCK']*100):.0f}/{round(row['wGLD']*100):.0f}/{round(row['wSLV']*100):.0f}"
        if label != prev_label:
            ax0.text(dt, float(row["Equity"]), label, fontsize=8, rotation=90, alpha=0.7,
                     ha="center", va="bottom")
            prev_label = label

    # Middle: relative performance + STOCK/GLD z on secondary axis + GSR on another secondary axis (scaled)
    perf = pd.DataFrame(index=bt_v.index)
    perf["Strategy"] = bt_v["Equity"] / bt_v["Equity"].iloc[0] - 1.0
    perf[STOCK_TICKER] = bh_stock_v / bh_stock_v.iloc[0] - 1.0
    perf["GLD"] = bh_gld_v / bh_gld_v.iloc[0] - 1.0
    perf["SLV"] = bh_slv_v / bh_slv_v.iloc[0] - 1.0

    ax1.plot(perf.index, perf["Strategy"], linewidth=3, label="Strategy")
    ax1.plot(perf.index, perf[STOCK_TICKER], label=STOCK_TICKER)
    ax1.plot(perf.index, perf["GLD"], label="GLD")
    ax1.plot(perf.index, perf["SLV"], label="SLV")
    ax1.set_title("Relative Performance | Secondary axes: STOCK/GLD z-score and GSR")
    ax1.set_ylabel("Return (fraction)")
    ax1.grid(True)
    ax1.legend(loc="upper left")

    # Secondary axis: z-score
    ax1b = ax1.twinx()
    ax1b.plot(bt_v.index, bt_v["STOCK_GLD_Z"], linestyle=":", linewidth=2, label="STOCK/GLD z")
    ax1b.axhline(Z_HIGH, alpha=0.25, linewidth=1)
    ax1b.axhline(Z_LOW, alpha=0.25, linewidth=1)
    ax1b.set_ylabel("STOCK/GLD z-score")
    ax1b.legend(loc="upper right")

    # Bottom: allocation strip
    w = bt_v[["wSTOCK", "wGLD", "wSLV"]]
    ax2.stackplot(w.index, w["wSTOCK"], w["wGLD"], w["wSLV"],
                 labels=[STOCK_TICKER, "GLD", "SLV"], alpha=0.85)
    ax2.set_title("Recommended Weights Over Time")
    ax2.set_ylabel("Weight")
    ax2.set_ylim(0, 1)
    ax2.grid(True)
    ax2.legend(loc="upper left")

    png_path = os.path.join(EXPORT_DIR, f"{STOCK_TICKER}_{start}_{end}_{stamp}.png".replace(":", ""))
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Saved PNG: {png_path}")


# =========================
# SUMMARY METRICS
# =========================
def summarize(bt: pd.DataFrame, m_prices: pd.DataFrame) -> None:
    final_val = float(bt["Equity"].iloc[-1])
    total_ret = final_val / START_CAPITAL - 1.0
    years = (bt.index[-1] - bt.index[0]).days / 365.25
    cagr = (1.0 + total_ret) ** (1.0 / years) - 1.0 if years > 0 else np.nan

    max_dd = float(bt["Drawdown"].min())
    max_dd_dur = max_drawdown_duration(bt["Drawdown"])

    # STOCK-only benchmark in-window
    px = m_prices.loc[m_prices.index.isin(bt.index), STOCK_TICKER].copy().loc[bt.index]
    stock_final = START_CAPITAL * (px.iloc[-1] / px.iloc[0])
    stock_total = stock_final / START_CAPITAL - 1.0
    stock_cagr = (1.0 + stock_total) ** (1.0 / years) - 1.0 if years > 0 else np.nan
    # ---- STOCK drawdown stats ----
    stock_equity = START_CAPITAL * (px / px.iloc[0])
    stock_dd = drawdown_series(stock_equity)
    stock_max_dd = float(stock_dd.min())
    stock_max_dd_dur = max_drawdown_duration(stock_dd)
    print("\n==============================")
    print(f"Window: {bt.index[0].date()} → {bt.index[-1].date()}  ({years:.2f} years)")
    print(f"Strategy final: ${final_val:,.0f} | Total: {total_ret:.2%} | CAGR: {cagr:.2%}")
    print(f"Max drawdown: {max_dd:.2%} | Max DD duration (months): {max_dd_dur}")
    print("---")
    print(
        f"100% {STOCK_TICKER} final: ${stock_final:,.0f} | "
        f"Total: {stock_total:.2%} | CAGR: {stock_cagr:.2%}\n"
        f"STOCK Max drawdown: {stock_max_dd:.2%} | "
        f"Max DD duration (months): {stock_max_dd_dur}"
    )    
    print("==============================\n")

    last = bt.iloc[-1]
    last_label = f"{round(last['wSTOCK']*100):.0f}/{round(last['wGLD']*100):.0f}/{round(last['wSLV']*100):.0f}"
    print(f"LAST RECOMMENDATION ({STOCK_TICKER}/GLD/SLV %):", last_label)
    print(f"Last reason:", last["Reason"])


# =========================
# MAIN
# =========================
LOOKBACK_YEARS_VIEW = 10

def main():
    os.makedirs(EXPORT_DIR, exist_ok=True)

    print("Downloading data from yfinance...")
    daily = download_prices(START_DATE, END_DATE)

    # Month-end prices
    m = to_month_end(daily).dropna()

    # Build signals on full padded history, then backtest strictly start->end
    m_sig = build_signals(m).dropna()

    bt = run_backtest(m_sig, START_DATE, END_DATE)

    # For plotting/benchmarks, use the same month-end price frame
    plot_and_export(bt, m_sig, START_DATE, END_DATE)
    summarize(bt, m_sig)


if __name__ == "__main__":
    main()