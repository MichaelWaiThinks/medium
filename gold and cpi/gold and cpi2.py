#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TITLE: Depreciation of US$ vs Gold (Monthly)

- Loads historical gold prices from CSV (Date, Close)
- Appends latest prices from Yahoo Finance (XAUUSD=X; fallback GC=F)
- Computes CPI-based "Inverse USD Value" from FRED
- Resamples gold to monthly averages and plots twin axes
- Saves updated goldprice.csv WITH a Date column preserved
"""

import os
import datetime as dt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from fredapi import Fred
import yfinance as yf
from matplotlib.ticker import FuncFormatter

# =========================
# Config
# =========================
API_KEY = 'a4049a1e2039b9a7a8ceb6aa3afa3dc7'  # your FRED API key
GOLD_CSV = 'goldprice.csv'                    # expects columns: Date, Close
SPOT_TICKER = 'XAUUSD=X'                      # Yahoo spot gold
FUT_TICKER  = 'GC=F'                          # Yahoo gold futures (fallback)
START_CPI   = '1971-01-01'                    # start for CPI series
CPI_SERIES  = 'CPIAUCSL'                      # CPI for All Urban Consumers
PLOT_CPI_ADJ_GOLD_PRICE = False
# =========================
# Today
# =========================
today = pd.Timestamp(dt.datetime.today().date())
print(f'** TODAY = {today.date()} **')

# =========================
# Recession shading
# =========================
def add_recession(ax):
    recession_periods = [
        ('1973-11-01', '1975-03-01'),
        ('1980-01-01', '1980-07-01'),
        ('1981-07-01', '1982-11-01'),
        ('1990-07-01', '1991-03-01'),
        ('2001-03-01', '2001-11-01'),
        ('2007-12-01', '2009-06-01'),
        ('2020-02-01', '2020-04-01')  # COVID-19 recession
    ]
    for start, end in recession_periods:
        ax.axvspan(pd.to_datetime(start), pd.to_datetime(end),
                   color='lightgrey', alpha=0.5)

# =========================
# Event annotations
# =========================
def add_incidents(ax):
    offset = 100
    text_color = 'gray'
    ax.annotate('End of Bretton Woods (1971)',
                xy=(pd.to_datetime('1971-08-15'), 50),
                xytext=(pd.to_datetime('1971-08-15'), 100 + offset),
                arrowprops=dict(facecolor=text_color, arrowstyle='->'),
                fontsize=8, ha='center')

    ax.annotate('Stagflation and Gold Surge ($665)',
                xy=(pd.to_datetime('1980-01-01'), 665),
                xytext=(pd.to_datetime('1980-01-01'), 750 + offset),
                arrowprops=dict(facecolor=text_color, arrowstyle='->'),
                fontsize=8, ha='center')

    ax.annotate('Gold Low ($253)',
                xy=(pd.to_datetime('1999-01-01'), 253),
                xytext=(pd.to_datetime('1999-01-01'), 300 + offset),
                arrowprops=dict(facecolor=text_color, arrowstyle='->'),
                fontsize=8, ha='center')

    ax.annotate('Great Recession (2008)',
                xy=(pd.to_datetime('2008-10-01'), 730),
                xytext=(pd.to_datetime('2008-10-01'), 800 + offset),
                arrowprops=dict(facecolor=text_color, arrowstyle='->'),
                fontsize=8, ha='center')

    ax.annotate('Euro Debt Crisis ($1,825)',
                xy=(pd.to_datetime('2011-08-01'), 1825),
                xytext=(pd.to_datetime('2011-08-01'), 1900 + offset),
                arrowprops=dict(facecolor=text_color, arrowstyle='->'),
                fontsize=8, ha='center')

    ax.annotate('Fed Tapering (2013–14)',
                xy=(pd.to_datetime('2013-01-01'), 1695),
                xytext=(pd.to_datetime('2013-01-01'), 1800 + offset),
                arrowprops=dict(facecolor=text_color, arrowstyle='->'),
                fontsize=8, ha='center')

    ax.annotate('COVID-19 Surge ($2,000)',
                xy=(pd.to_datetime('2020-07-01'), 2000),
                xytext=(pd.to_datetime('2020-07-01'), 2100 + offset),
                arrowprops=dict(facecolor=text_color, arrowstyle='->'),
                fontsize=8, ha='center')

    ax.annotate('Gold All-Time High 2024-09-23 ($2,648)',
                xy=(pd.to_datetime('2024-09-23'), 2500),
                xytext=(pd.to_datetime('2024-09-23'), 2500 + offset),
                arrowprops=dict(facecolor=text_color, arrowstyle='->'),
                fontsize=8, ha='center')

# =========================
# FRED CPI (Inverse USD Value)
# =========================
fred = Fred(api_key=API_KEY)
cpi = fred.get_series(CPI_SERIES, observation_start=START_CPI, observation_end=today)
df_cpi = pd.DataFrame({'CPI': cpi})
df_cpi.index = pd.to_datetime(df_cpi.index)
df_cpi_monthly = df_cpi.resample('ME').mean()

# Inverse USD purchasing power index: 1971 = 100
base = df_cpi_monthly['CPI'].iloc[0]
# Correct inverse (higher CPI => lower index). Do NOT invert again.
df_cpi_monthly['Inverse USD Value'] = 1/(df_cpi_monthly['CPI'] / base)

# =========================
# Load & extend gold prices
# =========================
if not os.path.exists(GOLD_CSV):
    raise FileNotFoundError(
        f"{GOLD_CSV} not found. Create it with columns ['Date','Close'] "
        f"(you can seed from Macrotrends or fetch from Yahoo)."
    )

gold_data = pd.read_csv(
    GOLD_CSV,
    parse_dates=['Date'],
    index_col='Date',
    dayfirst=True
)

last_csv_date = gold_data.index.max()
print(f"Last date in CSV: {last_csv_date.date()}")

if last_csv_date < today:
    print(f'Fetching remaining data from {last_csv_date.date()} to {today.date()}')

    def fetch_yahoo(ticker: str) -> pd.DataFrame:
        """Download and return a clean DF with a single 'Close' column."""
        df = yf.download(
            ticker,
            start=last_csv_date + pd.Timedelta(days=1),
            end=today + pd.Timedelta(days=1),   # include today (Yahoo end is exclusive)
            auto_adjust=True, progress=False, group_by='column'
        )
        if df is None or df.empty:
            return pd.DataFrame()

        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join([c for c in tup if c]).strip() for tup in df.columns.to_list()]

        # Pick the Close column regardless of ticker label
        close_cols = [c for c in df.columns if c.lower().startswith('close')]
        if not close_cols:
            return pd.DataFrame()
        out = df[close_cols].copy()
        out.columns = ['Close']  # normalize to a single 'Close'
        out = out.dropna()
        out.index = pd.to_datetime(out.index)
        return out

    new_px = fetch_yahoo(SPOT_TICKER)
    if new_px.empty:
        print("Spot fetch empty, retrying with futures (GC=F)...")
        new_px = fetch_yahoo(FUT_TICKER)

    if not new_px.empty:
        # Concatenate and clean duplicates
        gold_data = pd.concat([gold_data[['Close']], new_px], axis=0)
        gold_data = gold_data[~gold_data.index.duplicated(keep='last')].sort_index()

        # Save with 'Date' as a real column
        gold_data.reset_index().to_csv(GOLD_CSV, index=False, date_format='%Y-%m-%d')
        print(f"CSV updated and saved -> {GOLD_CSV}")
    else:
        print("No new Yahoo data appended. (Network/ticker issue?)")

# Keep DatetimeIndex for resampling
gold_data = gold_data.sort_index()

# =========================
# Monthly resample & combine
# =========================
gold_monthly = gold_data['Close'].resample('ME').mean()

# Left-join CPI and forward-fill (CPI lags; keep latest gold months)
df_combined = (
    pd.DataFrame({'Close': gold_monthly})
      .join(df_cpi_monthly[['Inverse USD Value']], how='left')
      .ffill()
)

print(df_combined.tail())

df_combined['adj_Close'] = df_combined['Close']/df_cpi_monthly['Inverse USD Value'] 
# =========================
# Plot
# =========================
fig, ax1 = plt.subplots(figsize=(11, 6))

# Left axis: Gold price (log scale, no sci; grid every $500)
ax1.set_xlabel('Year', fontsize=8)
ax1.set_ylabel('Monthly Avg Gold Price (USD/oz)', color='red', fontsize=12)
# ax1.set_yscale("log")

ax1.plot(df_combined.index, df_combined['Close'], color='red',
         label='Gold Price (USD/oz)', alpha=0.85)
ax1.tick_params(axis='y', labelcolor='red', labelsize=7)

if PLOT_CPI_ADJ_GOLD_PRICE:
    ax1.plot(df_combined.index, df_combined['adj_Close'], color='orange',
         label='CPI Adj Gold Price (USD/oz)', alpha=0.85)


# Format gold ticks as plain numbers with commas
ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x):,}" if x >= 1 else f"{x:.2f}"))

# Custom horizontal grid every $500 on gold axis
ymin, ymax = ax1.get_ylim()
y_ticks_gold = np.arange(np.floor(ymin/1000)*1000, np.ceil(ymax/1000)*1000 + 1000, 1000)
y_ticks_gold = y_ticks_gold[y_ticks_gold > 0]
ax1.set_yticks(y_ticks_gold)
ax1.yaxis.grid(True, which='major', color='lightgray', linestyle='--', linewidth=0.6)

from matplotlib.ticker import LogLocator, FuncFormatter

# Right axis: Inverse USD (log scale)
ax2 = ax1.twinx()
ax2.set_yscale("linear")
ax2.set_ylabel('Inverse USD Value (1971=100)', color='steelblue', fontsize=12)
ax2.plot(df_combined.index, 1/df_combined['Inverse USD Value'], color='steelblue',
         linestyle='-', label='Inverse USD Value (1971=100)', alpha=0.85)
ax2.tick_params(axis='y', labelcolor='steelblue')


# Grid every 0.1 on inverse USD axis
usd_min, usd_max = ax2.get_ylim()
# y_ticks_usd = np.arange(np.floor(usd_min*10)/10, np.ceil(usd_max*10)/10 + 0.1, 0.1)
# ax2.set_yticks(y_ticks_usd)
ax2.yaxis.grid(True, which='major', color='lightgray', linestyle='--', linewidth=0.4, alpha=0.6)

# Place major ticks at decades, format as plain numbers (no 1eX)
ax2.yaxis.set_major_locator(LogLocator(base=10, subs=(1.0,)))
ax2.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: ('{:.2f}'.format(x)).rstrip('0').rstrip('.')))
# ax2.yaxis.get_offset_text().set_visible(False)  # hide any ×10^n offset


# X ticks yearly (rotate for readability)
years = pd.date_range(start=df_combined.index.min(), end=df_combined.index.max(), freq='YS')
ax1.set_xticks(years)
ax1.set_xticklabels([d.strftime('%Y') for d in years], rotation=90)

# Grid + overlays
add_recession(ax1)
add_incidents(ax1)

plt.title(f'Gold Price vs. Inverse USD Purchasing Power (Monthly, 1971–{today.year})',
          fontsize=14)

fig.tight_layout()
plt.show()