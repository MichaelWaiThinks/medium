#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 28 15:09:13 2025

Tom DeMark (TD Sequential) analysis on gold price, I’ll need to clarify how deep you’d like to go. There are a few common approaches we can use:
	1.	TD Sequential count visualization — plotting the 1–9 setup and 1–13 countdown phases directly on gold’s price chart (candlestick chart).
	2.	Signal backtest — showing where buy/sell exhaustion signals historically triggered and comparing performance.
	3.	Current market signal — checking whether gold is now near a TD Buy/Sell setup or countdown exhaustion.

Buy Setup numbers
	1.	Bar 1: first bar where Close[t] < Close[t-4] (after any prior opposite condition or neutral bars).
	2.	Bar 2: again Close[t] < Close[t-4].
	3.	Bar 3: same condition.
	4.	Bar 4: same condition.
	5.	Bar 5: same condition.
	6.	Bar 6: same condition.
	7.	Bar 7: same condition.
	8.	Bar 8: same condition.
	9.	Bar 9 (completion): ninth consecutive bar with Close[t] < Close[t-4].

If any bar fails (Close[t] >= Close[t-4]), the count stops and you look for a new Bar 1.

Perfection (optional, but common)
	•	A Buy Setup is considered “perfected” only if the low of bar 8 or 9 is below the lows of bars 6 and 7.
(Sell perfection: high of bar 8 or 9 is above highs of bars 6 and 7.)
	•	If not perfected, traders often wait for that dip/spike before treating the signal as higher-quality.

TD Countdown (1 → 13)

Idea: after a completed Setup 9, look for exhaustion using the close vs. the intraday extreme two bars earlier. Counts do not need to be consecutive (you can skip bars that don’t qualify).

When it starts
	•	A Buy Countdown can begin after a Buy Setup 9 completes.
(Many practitioners require a minor “pause/price flip” first; others start immediately. Both conventions exist.)

Buy Countdown qualifying condition
	•	Count a bar if:
Close[t] ≤ Low[t-2].
	•	Each qualifying bar increases the countdown by 1; non-qualifying bars are ignored (the count persists).

Buy Countdown numbers
	1.	First bar after the completed Buy Setup 9 where Close[t] ≤ Low[t-2].
	2.	Next bar that meets the same Close[t] ≤ Low[t-2].
	3.	…
…
	4.	Bar 13 (exhaustion): the 13th bar (not necessarily consecutive) satisfying Close[t] ≤ Low[t-2].

Typical management rules (widely used variants)
	•	Cancellation / recycle: If, before reaching 13, an opposite Setup 9 completes (i.e., a Sell Setup 9), many traders cancel or “recycle” the active countdown and start over aligned with the new direction.
	•	Perfection for Countdown (optional): A Buy Countdown is often called “perfected” only if the low of bar 13 is ≤ the low of countdown bar 8 or 10 (minor variations exist). If not, some wait for that print before treating it as fully exhausted.
	•	No double-counting: Some strict implementations won’t count a bar for countdown if it’s also a Setup 9 bar of the opposite direction on the same day. (Platform-specific.)
	•	Risk levels (TDST) & qualifiers: Many traders add TDST support/resistance and additional qualifiers, but these vary by source and platform and aren’t required to assign the numbers.

⸻

Quick mirror for the Sell side
	•	Sell Setup (1→9): Close[t] > Close[t-4] for nine consecutive bars.
Perfection: high of bar 8 or 9 > highs of bars 6 and 7.
	•	Sell Countdown (1→13): after Sell Setup 9, count bars where Close[t] ≥ High[t-2] until you get 13 qualifying bars (non-consecutive).
Perfection (variant): high of bar 13 ≥ high of countdown bar 8 or 10.

@author: michaelwai
"""
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gold TD Sequential with mplfinance
- Candlesticks (green up / red down)
- TD Setup (1–9): green numbers ABOVE candle highs (alpha increases with count)
- TD Countdown (1–13): red numbers BELOW candle lows (alpha decreases as 13 approaches)
"""

import pandas as pd
import numpy as np
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# --------------------------- SETTINGS ---------------------------
TICKER = "GC=F"              # Use "XAUUSD=X" for spot if available
LOOKBACK_DAYS = 350
CSV_FALLBACK = "gold.csv"    # CSV with columns: Date,Open,High,Low,Close
# ---------------------------------------------------------------


# --------------------------- DATA LOAD --------------------------
def load_data():
    """Try yfinance; fallback to a local CSV."""
    end = datetime.today()
    start = end - timedelta(days=LOOKBACK_DAYS * 2)
    try:
        df = yf.download(TICKER, start=start, end=end, progress=False)
        if df is None or df.empty:
            raise RuntimeError("Empty download")
        df = df[['Open', 'High', 'Low', 'Close']]
        return df.tail(LOOKBACK_DAYS)
    except Exception:
        df = pd.read_csv(CSV_FALLBACK)
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.set_index('Date')
        return df[['Open', 'High', 'Low', 'Close']].tail(LOOKBACK_DAYS)

def sanitize_for_mpf(df: pd.DataFrame) -> pd.DataFrame:
    """Make sure df is compatible with mplfinance: float OHLC, DatetimeIndex."""
    df = pd.DataFrame(df).copy()

    # Flatten MultiIndex if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ['_'.join([str(x) for x in tup if str(x) != '']).strip() for tup in df.columns]

    # Normalize column names
    rename_map = {}
    for c in df.columns:
        lc = str(c).lower()
        if lc.startswith('open'):  rename_map[c] = 'Open'
        if lc.startswith('high'):  rename_map[c] = 'High'
        if lc.startswith('low'):   rename_map[c] = 'Low'
        if lc.startswith('close'): rename_map[c] = 'Close'
    df = df.rename(columns=rename_map)

    needed = ['Open', 'High', 'Low', 'Close']
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}. Found: {list(df.columns)}")

    # Remove commas/spaces, coerce to float
    for c in needed:
        df[c] = (df[c].astype(str)
                       .str.replace(',', '', regex=False)
                       .str.replace(' ', '', regex=False))
        df[c] = pd.to_numeric(df[c], errors='coerce')

    df = df.dropna(subset=needed)

    # Datetime index (no timezone)
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, errors='coerce')
    df = df[~df.index.isna()].sort_index()
    if getattr(df.index, 'tz', None) is not None:
        df.index = df.index.tz_convert(None)

    # Final assert: all numeric
    assert all(np.issubdtype(df[c].dtype, np.number) for c in needed), df.dtypes
    return df
# ---------------------------------------------------------------


# --------------------------- TD LOGIC ---------------------------
def td_setup(df: pd.DataFrame):
    """TD Setup 1–9: Buy (close < close[t-4]) and Sell (mirror). Returns Series."""
    close = df['Close'].values
    n = len(df)
    buy = np.zeros(n, dtype=int)
    sell = np.zeros(n, dtype=int)
    for i in range(4, n):
        if close[i] < close[i - 4]:
            buy[i] = buy[i - 1] + 1 if buy[i - 1] > 0 else 1
            buy[i] = min(buy[i], 9)
            sell[i] = 0
        elif close[i] > close[i - 4]:
            sell[i] = sell[i - 1] + 1 if sell[i - 1] > 0 else 1
            sell[i] = min(sell[i], 9)
            buy[i] = 0
        else:
            buy[i] = sell[i] = 0
    return pd.Series(buy, index=df.index, name='TD_Buy_Setup'), \
           pd.Series(sell, index=df.index, name='TD_Sell_Setup')

def td_countdown(df: pd.DataFrame, buy_setup: pd.Series, sell_setup: pd.Series):
    """
    Basic TD Countdown (no recycle):
    - Buy Countdown: after Buy Setup 9, count bars where Close <= Low[t-2] until 13 (non-consecutive).
    - Sell Countdown: after Sell Setup 9, count bars where Close >= High[t-2] until 13.
    """
    n = len(df)
    high, low, close = df['High'].values, df['Low'].values, df['Close'].values
    cd_buy = np.zeros(n, dtype=int)
    cd_sell = np.zeros(n, dtype=int)

    in_buy = in_sell = False
    bcount = scount = 0

    for i in range(n):
        if buy_setup.iloc[i] == 9:
            in_buy, bcount = True, 0
            in_sell, scount = False, 0
        elif sell_setup.iloc[i] == 9:
            in_sell, scount = True, 0
            in_buy, bcount = False, 0

        if in_buy and i >= 2:
            if close[i] <= low[i - 2]:
                bcount = min(bcount + 1, 13)
            cd_buy[i] = bcount
            if bcount == 13:
                in_buy = False

        if in_sell and i >= 2:
            if close[i] >= high[i - 2]:
                scount = min(scount + 1, 13)
            cd_sell[i] = scount
            if scount == 13:
                in_sell = False

    return pd.Series(cd_buy, index=df.index, name='TD_Buy_CD'), \
           pd.Series(cd_sell, index=df.index, name='TD_Sell_CD')
# ---------------------------------------------------------------


# --------------------------- PLOT -------------------------------
def plot_td(df: pd.DataFrame, buy_setup: pd.Series, buy_cd: pd.Series):
    """
    Draw:
    - Candlesticks via mplfinance.
    - Green setup numbers (1–9) above highs (alpha increases with count).
    - Red countdown numbers (1–13) below lows (alpha decreases as it approaches 13).
    """
    # Create “anchor” addplots so we can easily annotate later at proper y levels
    setup_y = pd.Series(np.nan, index=df.index)
    cd_y    = pd.Series(np.nan, index=df.index)
    for i, ts in enumerate(df.index):
        s = int(buy_setup.iat[i])
        if 1 <= s <= 9:
            setup_y.iat[i] = df['High'].iat[i] * 1.01  # a bit above high
        cdb = int(buy_cd.iat[i])
        if 1 <= cdb <= 13:
            cd_y.iat[i] = df['Low'].iat[i] * 0.99      # a bit below low

    add_plots = [
        mpf.make_addplot(setup_y, scatter=True, marker='x', markersize=0.1, color='gray', panel=0),
        mpf.make_addplot(cd_y,    scatter=True, marker='x', markersize=0.1, color='grey',   panel=0),
    ]

    style = mpf.make_mpf_style(base_mpf_style='charles')  # nice green/red candles

    fig, axlist = mpf.plot(
        df,
        type='candle',
        style=style,
        title='Gold — TD Sequential (Setup ↑ green / Countdown ↓ red)',
        ylabel='USD/oz',
        addplot=add_plots,
        returnfig=True,
        volume=False,
        xrotation=10,
        figratio=(32, 16)
    )
    ax = axlist[0]
    fig.set_dpi(300)   # 👈 set desired DPI here (e.g. 150, 200, 300)

    # mpf uses integer x positions [0..N-1]
    xvals = np.arange(len(df.index))

    # Place setup numbers (alpha increases with s)
    for i, ts in enumerate(df.index):
        s = int(buy_setup.iat[i])
        if 1 <= s <= 9 and not np.isnan(setup_y.iat[i]):
            alpha = 0.25 + 0.75 * (s / 9.0)     # 1 faint → 9 strong
            ax.text(xvals[i], setup_y.iat[i], str(s),
                    color='green', fontsize=2, ha='center', va='bottom', alpha=1, clip_on=True)

    # Place countdown numbers (alpha decreases with cdb)
    for i, ts in enumerate(df.index):
        cdb = int(buy_cd.iat[i])
        if 1 <= cdb <= 13 and not np.isnan(cd_y.iat[i]):
            alpha = 0.25 + 0.75 * ((14 - cdb) / 13.0)  # 1 strong → 13 faint
            ax.text(xvals[i], cd_y.iat[i], str(cdb),
                    color='darkred', fontsize=2, ha='center', va='top', alpha=1, clip_on=True)

    fig.tight_layout()
    plt.show()
# ---------------------------------------------------------------


# --------------------------- MAIN ------------------------------
def main():
    df = load_data()
    df = sanitize_for_mpf(df)
    buy_setup, sell_setup = td_setup(df)
    buy_cd, sell_cd = td_countdown(df, buy_setup, sell_setup)
    plot_td(df, buy_setup, buy_cd)

if __name__ == "__main__":
    main()
# ---------------------------------------------------------------