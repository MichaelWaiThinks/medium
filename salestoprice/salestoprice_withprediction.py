#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 24 00:08:12 2024

@author: michaelwai
"""

import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import numpy as np
import talib
from scipy.signal import find_peaks

# Fetch historical stock price data for NVDA
ticker = 'MSFT'
stock_data = yf.download(ticker, start='2020-01-01', end='2024-08-01')

# Fetch annual revenue data for NVDA
nvda = yf.Ticker(ticker)

# Check if annual financial data is available
if 'Total Revenue' in nvda.financials.index:
    annual_revenue = nvda.financials.loc['Total Revenue']
    
    # Resample revenue to match the frequency of the stock data (i.e., daily)
    revenue_df = pd.DataFrame(annual_revenue).reset_index()
    revenue_df.columns = ['Date', 'Revenue']
    revenue_df.set_index('Date', inplace=True)
    
    # Calculate the price-to-sales ratio
    daily_revenue = revenue_df.resample('D').ffill().reindex(stock_data.index).ffill()
    price_to_sales_ratio = stock_data['Close'] / (daily_revenue['Revenue'] / stock_data['Close'].count())
    
    # Drop rows with NaN values
    valid_data = pd.DataFrame({'Close': stock_data['Close'], 'Price_to_Sales': price_to_sales_ratio}).dropna()
    
    # Prepare data for linear regression
    X = np.array(valid_data['Price_to_Sales']).reshape(-1, 1)
    y = valid_data['Close'].values
    
    # Train the linear regression model
    model = LinearRegression()
    model.fit(X, y)
    
    # Make predictions
    predicted_prices = model.predict(X)
    
    # Create a DataFrame to store actual and predicted prices
    stock_data = stock_data.loc[valid_data.index]
    stock_data['Predicted_Close'] = predicted_prices
    
    # Calculate the SAR indicator for the price-to-sales ratio
    high = valid_data['Price_to_Sales'].values
    low = valid_data['Price_to_Sales'].values
    sar = talib.SAR(high, low, acceleration=0.02, maximum=0.2)
    
    # Align SAR with price_to_sales_ratio using the index
    aligned_sar = pd.Series(sar, index=valid_data.index)
    
    # Calculate rolling max and find peaks using scipy find_peaks
    rolling_max = price_to_sales_ratio.rolling(window=30, min_periods=1).max()
    peaks, _ = find_peaks(rolling_max, distance=30)  # Ensure peaks are separated by at least 30 days
    peak_values = rolling_max.iloc[peaks]
    
    # Calculate rolling min and find troughs using scipy find_peaks
    rolling_min = price_to_sales_ratio.rolling(window=30, min_periods=1).min()
    troughs, _ = find_peaks(-rolling_min, distance=30)  # Ensure troughs are separated by at least 30 days
    trough_values = rolling_min.iloc[troughs]
    
    # Calculate weights for peaks and troughs based on their date proximity to the current date
    current_date = stock_data.index[-1]
    peak_weights = np.exp(-((current_date - peak_values.index).days / 365))
    trough_weights = np.exp(-((current_date - trough_values.index).days / 365))
    
    # Calculate weighted average for peaks and troughs
    avg_peak_value = np.average(peak_values, weights=peak_weights) if not peak_values.empty else None
    avg_trough_value = np.average(trough_values, weights=trough_weights) if not trough_values.empty else None
    
    # Plot the actual and predicted stock prices
    fig, ax1 = plt.subplots(figsize=(14, 7))
    
    # Plot the actual stock price
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Stock Price', color='tab:blue')
    ax1.plot(stock_data.index, stock_data['Close'], color='tab:blue', label='Actual Stock Price')
    ax1.tick_params(axis='y', labelcolor='tab:blue')
    
    # Plot the predicted stock price
    ax1.plot(stock_data.index, stock_data['Predicted_Close'], color='tab:green', linestyle='dashed', label='Predicted Stock Price')
    
    # Create a second y-axis to plot the price-to-sales ratio and SAR indicator
    ax2 = ax1.twinx()
    ax2.set_ylabel('Price-to-Sales Ratio', color='tab:orange')
    ax2.plot(price_to_sales_ratio.index, price_to_sales_ratio, color='tab:orange', label='Price-to-Sales Ratio')
    
    # Plot the SAR indicator
    ax2.plot(aligned_sar.index, aligned_sar, color='tab:red', linestyle='dotted', label='SAR Indicator')
    
    # Plot scatter points for peaks and troughs
    ax2.scatter(peak_values.index, peak_values, color='red', label='Peaks', marker='^', s=100)
    ax2.scatter(trough_values.index, trough_values, color='blue', label='Bottoms', marker='v', s=100)
    
    # Plot horizontal line at the weighted average peak price-to-sales ratio
    if avg_peak_value is not None:
        ax2.axhline(y=avg_peak_value, color='gray', linestyle='-', label=f'Weighted Avg Peak Price-to-Sales Ratio ({avg_peak_value:.2f})')
    
    # Plot horizontal line at the weighted average trough price-to-sales ratio
    if avg_trough_value is not None:
        ax2.axhline(y=avg_trough_value, color='black', linestyle='-', label=f'Weighted Avg Bottom Price-to-Sales Ratio ({avg_trough_value:.2f})')
    
    ax2.tick_params(axis='y', labelcolor='tab:orange')
    
    fig.tight_layout()
    fig.legend(loc='lower right')#, bbox_to_anchor=(0.1,0.9))
    plt.show()
else:
    print("Total Revenue data is not available in the financial statements.")
