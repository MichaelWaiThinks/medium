#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 11 13:41:07 2024

@author: michaelwai
"""

# -*- coding: utf-8 -*-
"""
Created on Tue Aug 26
@article: https://medium.com/@michael.wai/the-rubber-band-effect-understanding-stock-price-movements-and-moving-averages-d3a64584dde9
@author: michaelwai
"""

import yfinance as yf
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import argrelextrema
from keras.models import Sequential
from keras.layers import Dense, Dropout
from sklearn.preprocessing import MinMaxScaler
from keras.utils import plot_model
import sys
from datetime import date
import matplotlib.dates as mdates

# Define the stock ticker and the moving average period
ticker = 'AAPL'
ma_period = 200

# Fetch historical data for the last 5 years
stock_data = yf.download(ticker, period="5y")
if len(stock_data) < ma_period:
    sys.exit(f'Data size too small for {ticker}, program aborted.')

# Calculate the xx-day Moving Average (x_day_MA)
stock_data['x_day_MA'] = stock_data['Close'].rolling(window=ma_period).mean()
stock_data['Pct_Over_MA'] = (stock_data['Close'] - stock_data['x_day_MA']) / stock_data['x_day_MA'] * 100
stock_data['Pct_Over_MA'].fillna(0, inplace=True)

def prepare_data(stock_data, ma_period):
    X = []
    for i in range(ma_period, len(stock_data)):
        X.append(stock_data['Pct_Over_MA'].iloc[i-ma_period:i].values)
    X = np.array(X)
    scaler = MinMaxScaler(feature_range=(0, 1))
    X = scaler.fit_transform(X)
    return X

def build_model(input_dim):
    model = Sequential()
    model.add(Dense(200, input_dim=input_dim, activation='relu', kernel_regularizer='l2'))
    model.add(Dropout(0.3))
    model.add(Dense(10, activation='relu', kernel_regularizer='l2'))
    model.add(Dropout(0.3))
    model.add(Dense(2, activation='linear'))
    model.compile(optimizer='adam', loss='mse')
    plot_model(model, to_file='model_plot.png', show_shapes=True, show_layer_names=True)
    return model

X = prepare_data(stock_data, ma_period)
split_index = int(0.5 * len(X))
X_train, X_test = X[:split_index], X[split_index:]
y_train = np.random.rand(len(X_train), 2) * 30
y_test = np.random.rand(len(X_test), 2) * 30

model = build_model(X_train.shape[1])
history = model.fit(X_train, y_train, epochs=50, batch_size=32, verbose=1, validation_split=0.2)
predictions = model.predict(X_test)

def safe_convert_to_int(value):
    if np.isnan(value) or value <= 0:
        return 1
    else:
        return int(value)

best_window_peak = safe_convert_to_int(predictions[-1][0])
best_window_trough = safe_convert_to_int(predictions[-1][1])

local_maxima = argrelextrema(stock_data['Pct_Over_MA'].values, comparator=np.greater, order=best_window_peak)[0]
local_minima = argrelextrema(stock_data['Pct_Over_MA'].values, comparator=np.less, order=best_window_trough)[0]

peak_values = stock_data['Pct_Over_MA'].iloc[local_maxima]
trough_values = stock_data['Pct_Over_MA'].iloc[local_minima]

positions = np.zeros(len(stock_data))

for i in range(1, len(stock_data)):
    if i in local_minima:
        positions[i] = 1
    elif i in local_maxima:
        positions[i] = -1

stock_data['Log_Return_BnH'] = np.log(stock_data['Close'] / stock_data['Close'].shift(1))
strategy_log_returns = np.zeros_like(stock_data['Close'].values)

in_position = False
buy_price = 0

for i in range(1, len(stock_data)):
    if positions[i] == 1 and not in_position:
        buy_price = stock_data['Close'].iloc[i]
        in_position = True
        strategy_log_returns[i] = strategy_log_returns[i-1]
    elif positions[i] == -1 and in_position:
        sell_price = stock_data['Close'].iloc[i]
        strategy_log_returns[i] = strategy_log_returns[i-1] + np.log(sell_price / buy_price)
        in_position = False
    elif in_position:
        current_price = stock_data['Close'].iloc[i]
        daily_log_return = np.log(current_price / stock_data['Close'].iloc[i-1])
        strategy_log_returns[i] = strategy_log_returns[i-1] + daily_log_return
    else:
        strategy_log_returns[i] = strategy_log_returns[i-1]

stock_data['Cumulative_Log_Return_BnH'] = stock_data['Log_Return_BnH'].cumsum()
cumulative_strategy_log_returns = strategy_log_returns

fig = plt.figure(figsize=(14, 14))

ax1 = plt.subplot(3, 1, 1)
plt.plot(stock_data.index, stock_data['Close'], label=f'{ticker} Price', color='black', alpha=0.6)
plt.plot(stock_data.index, stock_data['x_day_MA'], label=f'{ma_period}-Day MA', color='orange', alpha=0.8)
plt.title(f'{ticker} Price and {ma_period}-Day Moving Average (Log Scale)')
plt.xlabel('Date')
plt.ylabel('Price (USD)')
plt.legend()
plt.grid(True, which="both", ls="--")

ax2 = plt.subplot(3, 1, 2, sharex=ax1)
plt.plot(stock_data.index, stock_data['Pct_Over_MA'], label=f'Percentage Over/Under {ma_period}-Day MA', color='blue', alpha=0.6)
plt.axhline(y=0, color='black', linestyle='-', alpha=0.5)
plt.fill_between(stock_data.index, stock_data['Pct_Over_MA'], where=(stock_data['Pct_Over_MA'] >= 0), color='green', alpha=0.3)
plt.fill_between(stock_data.index, stock_data['Pct_Over_MA'], where=(stock_data['Pct_Over_MA'] < 0), color='red', alpha=0.3)
plt.scatter(stock_data.index[local_maxima], peak_values, color='red', label='Peaks', marker='o')
plt.scatter(stock_data.index[local_minima], trough_values, color='green', label='Troughs', marker='o')
plt.title(f'Percentage of {ticker} Price Over/Under {ma_period}-Day MA with Optimal Peaks and Troughs')
plt.xlabel('Date')
plt.ylabel('Percentage (%)')
plt.legend()
plt.grid(True)

ax3 = plt.subplot(3, 1, 3, sharex=ax1)
plt.plot(stock_data.index, cumulative_strategy_log_returns * 100, label='Strategy Cumulative Log Returns (%)', color='green', alpha=0.7)
plt.plot(stock_data.index, stock_data['Cumulative_Log_Return_BnH'] * 100, label='Buy and Hold Cumulative Log Returns (%)', color='black', alpha=0.7)
plt.title('Cumulative Log Returns Comparison: Strategy vs. Buy and Hold')
plt.xlabel('Date')
plt.ylabel('Cumulative Log Returns (%)')
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.show()

# Additional plot comparing predicted vs actual peaks and troughs
actual_window_peak = 20
actual_window_trough = 20
actual_peaks = argrelextrema(stock_data['Pct_Over_MA'].values, comparator=np.greater, order=actual_window_peak)[0]
actual_troughs = argrelextrema(stock_data['Pct_Over_MA'].values, comparator=np.less, order=actual_window_trough)[0]

predicted_peak_values = stock_data['Pct_Over_MA'].iloc[local_maxima]
predicted_trough_values = stock_data['Pct_Over_MA'].iloc[local_minima]
actual_peak_values = stock_data['Pct_Over_MA'].iloc[actual_peaks]
actual_trough_values = stock_data['Pct_Over_MA'].iloc[actual_troughs]

fig, ax = plt.subplots(figsize=(14, 7))
# =============================================================================
# plt.plot(stock_data.index, stock_data['Pct_Over_MA'], label='Percentage Over/Under MA', color='blue', alpha=0.6)
# plt.axhline(y=0, color='black', linestyle='-', alpha=0.5, label='Zero Line')
# plt.scatter(stock_data.index[local_maxima], predicted_peak_values, color='orange', label='Predicted Peaks', marker='o')
# plt.scatter(stock_data.index[local_minima], predicted_trough_values, color='purple', label='Predicted Troughs', marker='o')
# plt.scatter(stock_data.index[actual_peaks], actual_peak_values, color='red', label='Actual Peaks', marker='x')
# plt.scatter(stock_data.index[actual_troughs], actual_trough_values, color='green', label='Actual Troughs', marker='x')
# 
# plt.title('Comparison of Predicted vs. Actual Peaks and Troughs')
# plt.xlabel('Date')
# plt.ylabel('Percentage Over/Under Moving Average (%)')
# plt.legend()
# plt.grid(True)
# plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
# plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=3))
# plt.xticks(rotation=45)
# 
# =============================================================================

# Plot the results
fig=plt.figure(figsize=(14, 14))

# First subplot: Stock Price and x-Day MA
ax1 = plt.subplot(3, 1, 1)
plt.plot(stock_data.index, stock_data['Close'], label=f'{ticker} Price', color='black',alpha=0.6)
plt.plot(stock_data.index, stock_data['x_day_MA'], label=f'{ma_period}-Day MA', color='orange', alpha=0.8)
plt.title(f'{ticker} Price and {ma_period}-Day Moving Average (Log Scale)')
plt.xlabel('Date')
plt.ylabel('Price (USD)')
plt.legend()
plt.grid(True, which="both", ls="--")

# Second subplot: Percentage Over/Under x-Day MA with Peaks and Troughs
ax2 = plt.subplot(3, 1, 2, sharex=ax1)
plt.plot(stock_data.index, stock_data['Pct_Over_MA'], label='Percentage Over/Under {ma_period}-Day MA', color='blue', alpha=0.6)
plt.axhline(y=0, color='black', linestyle='-', alpha=0.5, label=f'Zero Line')

# Fill green above 0 and red below 0
plt.fill_between(stock_data.index, stock_data['Pct_Over_MA'], where=(stock_data['Pct_Over_MA'] >= 0), color='green', alpha=0.3)
plt.fill_between(stock_data.index, stock_data['Pct_Over_MA'], where=(stock_data['Pct_Over_MA'] < 0), color='red', alpha=0.3)

plt.plot(stock_data.index, stock_data['Pct_Over_MA'], label='Percentage Over/Under MA', color='blue', alpha=0.6)
plt.axhline(y=0, color='black', linestyle='-', alpha=0.5, label='Zero Line')
plt.scatter(stock_data.index[local_maxima], predicted_peak_values, color='pink', label='Predicted Peaks', marker='o')
plt.scatter(stock_data.index[local_minima], predicted_trough_values, color='lime', label='Predicted Troughs', marker='o')
plt.scatter(stock_data.index[actual_peaks], actual_peak_values, color='red', label='Actual Peaks', marker='x',s=30)
plt.scatter(stock_data.index[actual_troughs], actual_trough_values, color='green', label='Actual Troughs', marker='x',s=30)
# =============================================================================
# 
# plt.scatter(stock_data.index[local_maxima], peak_values, color='red', label='Peaks', marker='o')
# plt.scatter(stock_data.index[local_minima], trough_values, color='green', label='Troughs', marker='o')
# =============================================================================
plt.title(f'Percentage of {ticker} Price Over/Under {ma_period}-Day MA with Optimal Peaks and Troughs')
plt.xlabel('Date')
plt.ylabel('Percentage (%)')
plt.legend()
plt.grid(True)

# Plot cumulative log returns
ax3 = plt.subplot(3, 1, 3, sharex=ax1)

plt.plot(stock_data.index, cumulative_strategy_log_returns * 100, label='Strategy Cumulative Log Returns (%)', color='green', alpha=0.7)
plt.plot(stock_data.index, stock_data['Cumulative_Log_Return_BnH'] * 100, label='Buy and Hold Cumulative Log Returns (%)', color='black', alpha=0.7)

plt.title('Cumulative Log Returns Comparison: Strategy vs. Buy and Hold')
plt.xlabel('Date')
plt.ylabel('Cumulative Log Returns (%)')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()