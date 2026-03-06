#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 24 2024

@article: https://medium.com/@michael.wai/python-stock-analysis-rs-line-is-more-interesting-than-rsi-91a03e0be072
@author: https://medium.com/@michael.wai
"""

import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

# -----------------------------
# Parameters
# -----------------------------
ma_list = [10, 20, 50, 100]
ticker = "TSLA"
start_date = "2023-01-01"
end_date = "2026-12-31"

# -----------------------------
# Fetch data
# -----------------------------

def fetch_data():
    stock = yf.download(ticker, start=start_date, end=end_date, auto_adjust=False)
    sp500 = yf.download("^GSPC", start=start_date, end=end_date, auto_adjust=False)

    stock_close = stock["Adj Close"].squeeze()
    sp500_close = sp500["Adj Close"].squeeze()
    volume = stock["Volume"].squeeze()

    df = pd.concat(
        [
            stock_close.rename("Stock"),
            sp500_close.rename("SP500"),
            volume.rename("Volume"),
        ],
        axis=1,
    ).dropna()

    return df


# -----------------------------
# Relative Strength Line
# -----------------------------
def calculate_rs_line(df):
    df["RS_Line"] = df["Stock"] / df["SP500"]
    df["RS_MA_10"] = df["RS_Line"].rolling(10).mean()
    return df

# -----------------------------
# RSI
# -----------------------------
def calculate_rsi(df, rsi_window=14, ma_window=10):
    delta = df["Stock"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(rsi_window).mean()
    avg_loss = loss.rolling(rsi_window).mean()

    rs = avg_gain / avg_loss
    df["RSI_14"] = 100 - (100 / (1 + rs))
    df["RSI_10_MA"] = df["RSI_14"].rolling(ma_window).mean()

    return df

# -----------------------------
# Plot
# -----------------------------
def plot_data(df):
    fig = plt.figure(figsize=(12, 10), dpi=300)
    gs = GridSpec(4, 1, height_ratios=[4, 1, 3, 2])

    # ---- Price + MA ----
    ax_price = fig.add_subplot(gs[0])
    ax_price.plot(df.index, df["Stock"], label="Close", color="black")

    for ma in ma_list:
        ax_price.plot(
            df.index,
            df["Stock"].rolling(ma).mean(),
            label=f"{ma}-Day MA",
            alpha=0.6,
        )

    ax_price.set_title(f"{ticker} Price with Moving Averages")
    ax_price.set_ylabel("Price (USD)")
    ax_price.legend(loc="upper left")
    ax_price.grid(True)
    ax_price.tick_params(axis="x", labelbottom=False)

    # ---- Volume ----
    ax_vol = fig.add_subplot(gs[1], sharex=ax_price)
    ax_vol.bar(df.index, df["Volume"], color="gray", alpha=0.5)
    ax_vol.set_ylabel("Volume")
    ax_vol.grid(True)
    ax_vol.tick_params(axis="x", labelbottom=False)

    # ---- RS Line ----
    ax_rs = fig.add_subplot(gs[2], sharex=ax_price)
    ax_rs.plot(df.index, df["RS_Line"], label="RS Line", color="orange")
    ax_rs.plot(df.index, df["RS_MA_10"], label="RS MA(10)", color="gray")

    above = df["RS_Line"] > df["RS_MA_10"]
    below = df["RS_Line"] < df["RS_MA_10"]

    ax_rs.fill_between(
        df.index,
        df["RS_Line"],
        df["RS_MA_10"],
        where=above,
        color="green",
        alpha=0.4,
        label="Above MA",
    )

    ax_rs.fill_between(
        df.index,
        df["RS_Line"],
        df["RS_MA_10"],
        where=below,
        color="red",
        alpha=0.4,
        label="Below MA",
    )

    ax_rs.set_title(f"Relative Strength ({ticker} vs S&P 500)")
    ax_rs.set_ylabel("RS Value")
    ax_rs.legend(loc="upper left")
    ax_rs.grid(True)

    # ---- RSI ----
    ax_rsi = fig.add_subplot(gs[3], sharex=ax_price)
    ax_rsi.plot(df.index, df["RSI_14"], label="RSI (14)", color="darkblue")
    ax_rsi.plot(df.index, df["RSI_10_MA"], label="RSI MA(10)", color="red", alpha=0.6)

    ax_rsi.axhline(30, color="red", linewidth=1)
    ax_rsi.axhline(70, color="green", linewidth=1)

    ax_rsi.set_title("Relative Strength Index")
    ax_rsi.set_ylabel("RSI")
    ax_rsi.set_xlabel("Date")
    ax_rsi.legend(loc="upper left")
    ax_rsi.grid(True)

    plt.tight_layout()
    plt.show()

# -----------------------------
# Main
# -----------------------------
def main():
    df = fetch_data()
    df = calculate_rs_line(df)
    df = calculate_rsi(df)
    plot_data(df)

if __name__ == "__main__":
    main()
