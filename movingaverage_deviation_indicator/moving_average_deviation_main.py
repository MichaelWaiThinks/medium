#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Moving Average Deviation Indicator (Rubber Band Effect)
- Auto-select peak/trough windows by brute-force scoring on recent lookback
- Trade: BUY at trough, SELL at peak
- Risk controls:
    A) Stop-loss (% from entry)
    B) Time stop (max holding days)
    C) MA-break stop (N consecutive closes below MA)
- Plot middle subplot BUY/SELL annotations + SELL reason labels
- End-of-run comment: BUY / SELL / WAIT / HOLD (based on latest executed signals)
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import argrelextrema
from datetime import date
import os
import sys

# =====================
# Parameters
# =====================
ticker = "BTC-USD"
ma_period = 200
lookback_len = 252
today = str(date.today())

# Risk controls (tweak these)
stop_loss_pct = 0.12      # 12% stop from entry
max_hold_days = 60        # time stop (trading days)
ma_break_days = 3         # exit if Close < MA for N consecutive days

# Signal recency thresholds
buy_recent_days = 10
sell_recent_days = 5

# =====================
# Download data
# =====================
stock_data = yf.download(ticker, period="5y", group_by="column")

# Handle MultiIndex columns (common in yfinance)
if isinstance(stock_data.columns, pd.MultiIndex):
    stock_data = stock_data.xs(ticker, axis=1, level=1)

stock_data = stock_data.copy()

if len(stock_data) < ma_period + lookback_len:
    sys.exit("Not enough data.")

# =====================
# Indicators
# =====================
stock_data["Close"] = stock_data["Close"].astype(float)
stock_data["x_day_MA"] = stock_data["Close"].rolling(ma_period).mean()

stock_data["Pct_Over_MA"] = (
    (stock_data["Close"] - stock_data["x_day_MA"]) / stock_data["x_day_MA"] * 100
).fillna(0.0)

pct = stock_data["Pct_Over_MA"].values
close = stock_data["Close"].values

# MA-break helper: count consecutive closes below MA
below_ma = (stock_data["Close"] < stock_data["x_day_MA"]).astype(int)
stock_data["BelowMA_Streak"] = below_ma.groupby((below_ma != below_ma.shift()).cumsum()).cumsum()
below_streak = stock_data["BelowMA_Streak"].fillna(0).astype(int).values

# =====================
# Strategy scoring (buy at trough, sell at peak)
# =====================
def score_window(pct_slice, close_slice, wp, wt):
    peaks = argrelextrema(pct_slice, np.greater, order=wp)[0]
    troughs = argrelextrema(pct_slice, np.less, order=wt)[0]
    if len(peaks) == 0 or len(troughs) == 0:
        return 1.0

    events = [(i, "B") for i in troughs] + [(i, "S") for i in peaks]
    events.sort(key=lambda x: x[0])

    mult = 1.0
    in_pos = False
    buy_price = None

    for idx, typ in events:
        if typ == "B" and not in_pos:
            buy_price = close_slice[idx]
            in_pos = True
        elif typ == "S" and in_pos:
            sell_price = close_slice[idx]
            if buy_price and buy_price > 0:
                mult *= (sell_price / buy_price)
            in_pos = False
            buy_price = None

    return mult

# =====================
# Find optimal windows (brute force on latest lookback slice)
# =====================
w_candidates = range(3, 61)
pct_slice = pct[-lookback_len:]
close_slice = close[-lookback_len:]

best_score = -np.inf
best_wp, best_wt = 10, 10

for wp in w_candidates:
    for wt in w_candidates:
        s = score_window(pct_slice, close_slice, wp, wt)
        if s > best_score:
            best_score = s
            best_wp, best_wt = wp, wt

print(f"Optimal windows → peak={best_wp}, trough={best_wt} (score={best_score:.3f}x)")

# =====================
# Detect extrema on full series using optimal windows
# =====================
local_maxima = argrelextrema(pct, np.greater, order=best_wp)[0]
local_minima = argrelextrema(pct, np.less, order=best_wt)[0]

peak_values = stock_data["Pct_Over_MA"].iloc[local_maxima]
trough_values = stock_data["Pct_Over_MA"].iloc[local_minima]

# =====================
# Build raw BUY/SELL events from extrema
# =====================
raw_positions = np.zeros_like(close)
raw_positions[local_minima] = 1      # BUY events
raw_positions[local_maxima] = -1     # SELL events

# =====================
# Trading simulation with risk controls + exit reasons
# =====================
trade_positions = np.zeros_like(close)  # executed events (for plotting)
strategy_nav = np.ones_like(close, dtype=float)
sell_reason = {}  # index -> reason string

in_pos = False
buy_price = 0.0
hold_days = 0

for i in range(1, len(close)):
    # carry forward NAV by default
    strategy_nav[i] = strategy_nav[i-1]

    if in_pos:
        hold_days += 1

        # A) Stop-loss exit
        if close[i] <= buy_price * (1 - stop_loss_pct):
            trade_positions[i] = -1
            sell_reason[i] = "SELL(stop)"
            strategy_nav[i] = strategy_nav[i-1] * (close[i] / buy_price)
            in_pos = False
            buy_price = 0.0
            hold_days = 0
            continue

        # B) Time stop exit
        if hold_days >= max_hold_days:
            trade_positions[i] = -1
            sell_reason[i] = "SELL(time)"
            strategy_nav[i] = strategy_nav[i-1] * (close[i] / buy_price)
            in_pos = False
            buy_price = 0.0
            hold_days = 0
            continue

        # C) MA-break stop exit
        if below_streak[i] >= ma_break_days:
            trade_positions[i] = -1
            sell_reason[i] = "SELL(MA)"
            strategy_nav[i] = strategy_nav[i-1] * (close[i] / buy_price)
            in_pos = False
            buy_price = 0.0
            hold_days = 0
            continue

        # Normal SELL signal at peak
        if raw_positions[i] == -1:
            trade_positions[i] = -1
            sell_reason[i] = "SELL(peak)"
            strategy_nav[i] = strategy_nav[i-1] * (close[i] / buy_price)
            in_pos = False
            buy_price = 0.0
            hold_days = 0
            continue

    else:
        # Not in position: look for BUY
        if raw_positions[i] == 1:
            trade_positions[i] = 1
            buy_price = close[i]
            in_pos = True
            hold_days = 0
            continue

cumulative_strategy = strategy_nav - 1
cumulative_bnh = np.cumprod(1 + stock_data["Close"].pct_change().fillna(0).values) - 1

# Indices for annotations (executed trades)
buy_idx = np.where(trade_positions == 1)[0]
sell_idx = np.where(trade_positions == -1)[0]

# =====================
# Plot
# =====================
fig = plt.figure(figsize=(14, 14))

# 1) Price + MA
ax1 = plt.subplot(3, 1, 1)
plt.plot(stock_data.index, stock_data["Close"], label=f"{ticker} Price", color="black", alpha=0.65)
plt.plot(stock_data.index, stock_data["x_day_MA"], label=f"{ma_period}-Day MA", color="orange", alpha=0.85)
plt.title(f"{ticker} Price and {ma_period}-Day Moving Average")
plt.ylabel("Price")
plt.legend()
plt.grid(True, ls="--", alpha=0.35)

# 2) MA deviation + Peaks/Troughs + BUY/SELL + SELL reason labels
ax2 = plt.subplot(3, 1, 2, sharex=ax1)
plt.plot(stock_data.index, stock_data["Pct_Over_MA"], label=f"Pct Over/Under {ma_period}-MA", color="blue", alpha=0.6)
plt.axhline(0, color="black", alpha=0.5)

plt.fill_between(stock_data.index, stock_data["Pct_Over_MA"], where=(stock_data["Pct_Over_MA"] >= 0), alpha=0.15)
plt.fill_between(stock_data.index, stock_data["Pct_Over_MA"], where=(stock_data["Pct_Over_MA"] < 0), alpha=0.15)

plt.scatter(stock_data.index[local_maxima], peak_values, color="red", s=20, label="Peaks")
plt.scatter(stock_data.index[local_minima], trough_values, color="green", s=20, label="Troughs")

# Executed BUY/SELL markers
plt.scatter(
    stock_data.index[buy_idx],
    stock_data["Pct_Over_MA"].iloc[buy_idx],
    marker="^",
    color="green",
    s=90,
    label="BUY",
    zorder=5
)
plt.scatter(
    stock_data.index[sell_idx],
    stock_data["Pct_Over_MA"].iloc[sell_idx],
    marker="v",
    color="red",
    s=90,
    label="SELL",
    zorder=5
)

# Text annotations
for i in buy_idx:
    plt.annotate(
        "BUY",
        (stock_data.index[i], stock_data["Pct_Over_MA"].iloc[i]),
        textcoords="offset points",
        xytext=(0, 8),
        ha="center",
        fontsize=8,
        color="green"
    )

for i in sell_idx:
    reason = sell_reason.get(i, "SELL")
    plt.annotate(
        reason,
        (stock_data.index[i], stock_data["Pct_Over_MA"].iloc[i]),
        textcoords="offset points",
        xytext=(0, -14),
        ha="center",
        fontsize=8,
        color="red"
    )

plt.title(f"MA Deviation with Executed Signals (peak={best_wp}, trough={best_wt})")
plt.ylabel("Pct (%)")
plt.legend(ncol=3)
plt.grid(True, alpha=0.35)

# 3) Returns
ax3 = plt.subplot(3, 1, 3, sharex=ax1)
plt.plot(stock_data.index, cumulative_strategy, label="Strategy (risk controls)", color="green", alpha=0.75)
plt.plot(stock_data.index, cumulative_bnh, label="Buy & Hold", color="blue", alpha=0.75)
plt.title("Cumulative Returns")
plt.ylabel("Return")
plt.legend()
plt.grid(True, alpha=0.35)

plt.tight_layout()
plt.show()

# =====================
# End-of-run decision comment: BUY / SELL / WAIT / HOLD
# =====================
def days_since(idx_array):
    if len(idx_array) == 0:
        return 999999
    return (len(stock_data) - 1) - int(idx_array[-1])

last_buy_days = days_since(buy_idx)
last_sell_days = days_since(sell_idx)

# Decide current "state" based on last executed trade event
last_buy_i = int(buy_idx[-1]) if len(buy_idx) else -1
last_sell_i = int(sell_idx[-1]) if len(sell_idx) else -1
currently_in_position = (last_buy_i > last_sell_i)

decision = "WAIT"
comment = ""

if not currently_in_position:
    # Out of market
    if last_buy_days <= buy_recent_days:
        decision = "BUY"
        comment = f"BUY: last executed BUY was {last_buy_days} trading days ago."
    else:
        decision = "WAIT"
        comment = f"WAIT: no recent BUY signal (last BUY {last_buy_days} trading days ago)."
else:
    # In market
    if last_sell_days <= sell_recent_days:
        decision = "SELL"
        reason = sell_reason.get(last_sell_i, "SELL")
        comment = f"{reason}: last executed SELL was {last_sell_days} trading days ago."
    else:
        decision = "HOLD"
        comment = f"HOLD: in position (last BUY {last_buy_days} trading days ago), no recent SELL."

print("\n====================")
print(f"FINAL ACTION: {decision}")
print(comment)
print("====================\n")

# =====================
# Save figure
# =====================
outpath = os.path.expanduser(f"~/Downloads/{today}_{ticker}_MAdeviation.png")
fig.savefig(outpath, dpi=160)
print("Saved:", outpath)