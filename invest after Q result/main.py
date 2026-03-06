#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime
from pandas.tseries.offsets import DateOffset

# =========================
# Config
# =========================
TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
    "META", "TSLA", "AVGO", "COST", "PEP"
]

YEARS_BACK = 5
CSV_OUTPUT = "nasdaq_top10_earnings_event_study.csv"
PNG_OUTPUT = "nasdaq_top10_earnings_subplot.png"

# =========================
# Helpers
# =========================

def get_price_history(tickers, start, end):
    """
    Download daily adjusted close prices for all tickers.
    """
    data = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    if isinstance(data.columns, pd.MultiIndex):
        px = data["Close"].copy()
    else:
        px = data["Close"].to_frame()
    return px


def _raw_earnings_df(ticker, max_quarters=40):
    """
    Try multiple yfinance APIs to get earnings dates:
    - newer versions: .get_earnings_dates(limit=...)
    - some versions: .earnings_dates (property / df)
    Returns a DataFrame or None.
    """
    tk = yf.Ticker(ticker)

    # Try attribute 'earnings_dates' first (some versions expose it directly)
    for attr_name in ["earnings_dates", "get_earnings_dates"]:
        try:
            attr = getattr(tk, attr_name)
        except AttributeError:
            continue

        df = None
        # If it's a method, call it
        if callable(attr):
            try:
                df = attr(limit=max_quarters)
            except TypeError:
                # some older versions may use different signature
                try:
                    df = attr()
                except Exception:
                    df = None
        else:
            # already a DataFrame / Series
            df = attr

        if df is not None and isinstance(df, (pd.DataFrame, pd.Series)) and not df.empty:
            return df

    # Fallback: nothing found
    return None


def get_earnings_dates_for_ticker(ticker, start, end, max_quarters=40):
    """
    Get quarterly earnings dates for a ticker, filtered to [start, end].
    Compatible with multiple yfinance versions.
    """
    ed = _raw_earnings_df(ticker, max_quarters=max_quarters)
    if ed is None is None or (hasattr(ed, "empty") and ed.empty):
        return pd.DatetimeIndex([])

    # Detect column containing earnings dates
    if isinstance(ed, pd.Series):
        date_values = pd.to_datetime(ed.index)
    else:
        col = None
        for c in ed.columns:
            cl = str(c).lower()
            if "earnings" in cl and "date" in cl:
                col = c
                break
        if col is None:
            # some versions give DatetimeIndex already
            if isinstance(ed.index, pd.DatetimeIndex):
                date_values = ed.index
            else:
                return pd.DatetimeIndex([])
        else:
            date_values = pd.to_datetime(ed[col])

    dates = pd.to_datetime(date_values).tz_localize(None)
    mask = (dates >= start) & (dates <= end)
    return pd.DatetimeIndex(dates[mask].sort_values())


def get_next_trading_day(date, price_index):
    """
    Next trading day strictly after 'date'.
    """
    pos = price_index.searchsorted(date, side="right")
    if pos < len(price_index):
        return price_index[pos]
    return None


def get_nearest_trading_day_on_or_after(date, price_index):
    """
    Get the first trading day on or after 'date'.
    """
    pos = price_index.searchsorted(date, side="left")
    if pos < len(price_index):
        return price_index[pos]
    return None


# =========================
# Main event study builder
# =========================

def build_event_study(tickers, years_back=5):
    end = datetime.today()
    start = end - DateOffset(years=years_back)

    # Fetch price history once for all
    prices = get_price_history(tickers, start, end + DateOffset(months=7))
    if isinstance(prices, pd.Series):
        prices = prices.to_frame()
    prices = prices.sort_index()

    all_events = []

    for ticker in tickers:
        print(f"Processing {ticker}...")
        px = prices[ticker].dropna()
        if px.empty:
            print(f"  No price data for {ticker} in period.")
            continue

        earnings_dates = get_earnings_dates_for_ticker(ticker, start, end)
        if len(earnings_dates) == 0:
            print(f"  No earnings dates found for {ticker} in period.")
            continue

        for ed in earnings_dates:
            # Pre-earnings close: last trading day on or before earnings date
            pre_idx_pos = px.index.searchsorted(ed, side="right") - 1
            if pre_idx_pos < 0:
                continue
            pre_date = px.index[pre_idx_pos]
            pre_close = px.loc[pre_date]

            # Next trading day close
            next_date = get_next_trading_day(pre_date, px.index)
            if next_date is None:
                continue
            next_close = px.loc[next_date]

            # Direction (Up/Down) based on next day vs pre-earnings close
            next_day_ret = (next_close / pre_close) - 1.0
            if next_day_ret > 0:
                direction = "Up"
            elif next_day_ret < 0:
                direction = "Down"
            else:
                direction = "Flat"

            # 6-month forward: from next-day close
            fwd_target_date = next_date + DateOffset(months=6)
            fwd_date = get_nearest_trading_day_on_or_after(fwd_target_date, px.index)
            if fwd_date is None:
                sixm_ret = np.nan
                fwd_close = np.nan
            else:
                fwd_close = px.loc[fwd_date]
                sixm_ret = (fwd_close / next_close) - 1.0

            all_events.append({
                "Ticker": ticker,
                "EarningsDate": ed.date(),
                "PreEarningsDate": pre_date.date(),
                "PreClose": float(pre_close),
                "NextDayDate": next_date.date(),
                "NextDayClose": float(next_close),
                "NextDayReturn": float(next_day_ret),
                "NextDayDirection": direction,
                "Fwd6MDate": fwd_date.date() if not pd.isna(fwd_close) else np.nan,
                "Fwd6MClose": float(fwd_close) if not pd.isna(fwd_close) else np.nan,
                "Fwd6MReturn": float(sixm_ret) if not pd.isna(sixm_ret) else np.nan,
            })

    if not all_events:
        # Return an empty DF with expected columns (no crash)
        cols = [
            "Ticker", "EarningsDate", "PreEarningsDate", "PreClose",
            "NextDayDate", "NextDayClose", "NextDayReturn", "NextDayDirection",
            "Fwd6MDate", "Fwd6MClose", "Fwd6MReturn"
        ]
        return pd.DataFrame(columns=cols)

    df = pd.DataFrame(all_events)
    df.sort_values(["Ticker", "EarningsDate"], inplace=True)
    return df


# =========================
# Run + Save CSV + Plot
# =========================

if __name__ == "__main__":
    print("yfinance version:", yf.__version__)
    df_events = build_event_study(TICKERS, YEARS_BACK)

    if df_events.empty:
        print("\n*** No earnings events collected. ***")
        print("Possible reasons:")
        print(" - yfinance version too old (upgrade with: pip install --upgrade yfinance)")
        print(" - temporary network / Yahoo API issue")
        print(" - symbols changed / delisted (unlikely for these 10)")
    else:
        # Save CSV for your own analysis
        df_events.to_csv(CSV_OUTPUT, index=False)
        print(f"\nSaved event study to: {CSV_OUTPUT}")
        print(df_events.head())

        # Quick overview plot:
        # 2x5 subplot matrix, each shows 6M forward return by earnings event
        fig, axes = plt.subplots(2, 5, figsize=(22, 8), sharex=False, sharey=True)
        axes = axes.flatten()

        unique_tickers = TICKERS  # fixed order for layout

        for ax, ticker in zip(axes, unique_tickers):
            sub = df_events[df_events["Ticker"] == ticker].dropna(subset=["Fwd6MReturn"])
            if sub.empty:
                ax.set_title(ticker)
                ax.set_xlabel("Earnings #")
                ax.set_ylabel("6M Return")
                continue

            sub = sub.reset_index(drop=True)
            # use row index as event number
            up = sub[sub["NextDayDirection"] == "Up"]
            down = sub[sub["NextDayDirection"] == "Down"]
            flat = sub[sub["NextDayDirection"] == "Flat"]

            if not up.empty:
                ax.scatter(up.index, up["Fwd6MReturn"], marker="^", label="Up")
            if not down.empty:
                ax.scatter(down.index, down["Fwd6MReturn"], marker="v", label="Down")
            if not flat.empty:
                ax.scatter(flat.index, flat["Fwd6MReturn"], marker="o", label="Flat")

            ax.axhline(0, linestyle="--", linewidth=0.8)
            ax.set_title(ticker)
            ax.set_xlabel("Earnings events")
            ax.set_ylabel("6M ROI")

            if ticker == unique_tickers[0]:
                ax.legend()

        # Hide any extra axes if fewer than 10
        for j in range(len(unique_tickers), len(axes)):
            fig.delaxes(axes[j])

        plt.tight_layout()
        plt.savefig(PNG_OUTPUT, dpi=200)
        plt.show()
        print(f"Saved overview plot to: {PNG_OUTPUT}")