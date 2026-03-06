#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 30 11:59:40 2024

Reference : https://fred.stlouisfed.org/series/SAHMREALTIME

@author: michaelwai
"""

import pandas_datareader as pdr
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import matplotlib.dates as mdates


# Define the date range
start_date = '1960-01-01'
end_date = datetime.now().strftime('%Y-%m-%d')

# Fetch unemployment rate data from FRED (Federal Reserve Economic Data)
unemployment_rate = pdr.get_data_fred('UNRATE', start=start_date, end=end_date)

# Calculate 3-month moving average of unemployment rate
unemployment_rate['Unemployment_MA'] = unemployment_rate['UNRATE'].rolling(window=3).mean()

# Calculate minimum unemployment rate over the last 12 months (rolling window)
unemployment_rate['Min_Unemployment_12m'] = unemployment_rate['UNRATE'].rolling(window=12).min()

# Calculate Sahm Rule Indicator
unemployment_rate['Sahm_Indicator'] = unemployment_rate['Unemployment_MA'] - unemployment_rate['Min_Unemployment_12m']

# Identify periods where the Sahm Indicator exceeds the 0.50% threshold
recession_periods = unemployment_rate[unemployment_rate['Sahm_Indicator'] > 0.50].index

# Fetch stock indices data (S&P 500, DJIA, Nasdaq) using yfinance
sp500 = yf.download('^GSPC', start=start_date, end=end_date)
djia = yf.download('^DJI', start=start_date, end=end_date)
nasdaq = yf.download('^IXIC', start=start_date, end=end_date)

# Plot the data
plt.figure(figsize=(14, 14))

# First subplot: Unemployment Rate and Sahm Rule Indicator
ax1 = plt.subplot(3, 1, 1)
plt.plot(unemployment_rate.index, unemployment_rate['UNRATE'], label='Unemployment Rate', color='blue')
plt.plot(unemployment_rate.index, unemployment_rate['Unemployment_MA'], label='3-Month MA', color='orange')
plt.title('Unemployment Rate and Sahm Rule Indicator')
# plt.xlabel('Date')
plt.ylabel('Unemployment Rate (%)')
plt.legend()
plt.grid(True)


# Shade the recession periods
for period in recession_periods:
    plt.axvspan(period, period + pd.DateOffset(months=1), color='lightgray', alpha=0.3)


# Second subplot: Sahm Rule Indicator
ax2 = plt.subplot(3, 1, 2, sharex=ax1)
plt.plot(unemployment_rate.index, unemployment_rate['Sahm_Indicator'], label='Sahm Rule Indicator', color='red')
plt.axhline(y=0.50, color='black', linestyle='--', label='Recession Signal Threshold (0.5%)')
plt.title('Sahm Rule Indicator')
# plt.xlabel('Date')
plt.ylabel('Indicator (%)')
plt.legend()
plt.grid(True)


# Shade the recession periods
for period in recession_periods:
    plt.axvspan(period, period + pd.DateOffset(months=1), color='lightgray', alpha=0.3)


# Third subplot: S&P 500, DJIA, Nasdaq
ax3 = plt.subplot(3, 1, 3, sharex=ax1)
# ax3.set_yscale('log')
print(sp500.columns)

plt.plot(sp500.index, sp500['Close'], label='S&P 500', color='green')
plt.plot(djia.index, djia['Close'], label='DJIA', color='purple')
plt.plot(nasdaq.index, nasdaq['Close'], label='Nasdaq', color='brown')
plt.title('S&P 500, DJIA, and Nasdaq')
plt.xlabel('Date')
plt.ylabel('Index Value')
plt.legend()
plt.grid(True)


# # Set x-axis major ticks to every 6 months
# ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=12))
# ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

# # Apply the same x-axis configuration to the other subplots
# ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=12))
# ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

ax1.tick_params('x', labelbottom=False)
ax2.tick_params('x', labelbottom=False)

ax3.xaxis.set_major_locator(mdates.MonthLocator(interval=12))
ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
plt.xticks(rotation=90)

# Shade the recession periods
for period in recession_periods:
    plt.axvspan(period, period + pd.DateOffset(months=1), color='lightgray', alpha=0.3)

plt.tight_layout()
plt.show()
