#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 27 15:54:45 2024
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
from datetime import datetime, date

today = str(date.today())

# Define the stock ticker and the moving average period
ticker = 'DELL'
company = yf.Ticker(ticker).info['longName']

# ticker='XAUT-USD'
# ticker ='^GSPC'
ma_period = 200


# Fetch historical data for the last 2 years
stock_data = yf.download(ticker, period="5Y")
if len(stock_data) < ma_period:
    sys.exit(f'Data size too small for {ticker}, program aborted.')

# Calculate the xx-day Moving Average (x_day_MA)
stock_data['x_day_MA'] = stock_data['Close'].rolling(window=ma_period).mean()

# Adjust the percentage over/under x-MA calculation
stock_data['Pct_Over_MA'] = (stock_data['Close'] - stock_data['x_day_MA']) / stock_data['x_day_MA'] * 100

# Handle NaN values
stock_data['Pct_Over_MA'].fillna(0, inplace=True)

# Prepare data for neural network
def prepare_data(stock_data, ma_period):
    X = []
    for i in range(ma_period, len(stock_data)):
        X.append(stock_data['Pct_Over_MA'].iloc[i-ma_period:i].values)
    X = np.array(X)
    
    # Normalize the data
    scaler = MinMaxScaler(feature_range=(0, 1))
    X = scaler.fit_transform(X)
    
    return X

# Create the neural network model
def build_model(input_dim):
    model = Sequential()
    model.add(Dense(200, input_dim=input_dim, activation='relu', kernel_regularizer='l2'))
    model.add(Dropout(0.3))
    model.add(Dense(10, activation='relu', kernel_regularizer='l2'))
    model.add(Dropout(0.3))
    model.add(Dense(2, activation='linear'))  # Two outputs: window_peak and window_trough
    model.compile(optimizer='adam', loss='mse')
    plot_model(model, to_file='model_plot.png', show_shapes=True, show_layer_names=True)
    return model

# Prepare the data
X = prepare_data(stock_data, ma_period)

# Split the data into training and testing sets
split_index = int(0.5 * len(X))  # 50/50 training vs testing data
X_train, X_test = X[:split_index], X[split_index:]

# Target values (y) are not predefined; the model will attempt to learn the best window_peak and window_trough
y_train = np.random.rand(len(X_train), 2) * 30  # Random values between 0 and 30
y_test = np.random.rand(len(X_test), 2) * 30

# Build and train the model
model = build_model(X_train.shape[1])
history = model.fit(X_train, y_train, epochs=50, batch_size=32, verbose=1, validation_split=0.2)

# Make predictions
predictions = model.predict(X_test)

# Safeguard against NaNs in predictions
def safe_convert_to_int(value):
    if np.isnan(value) or value <= 0:
        return 1  # Default to a safe value
    else:
        return int(value)

best_window_peak = safe_convert_to_int(predictions[-1][0])
best_window_trough = safe_convert_to_int(predictions[-1][1])

# Find local maxima and minima using the predicted optimal windows
local_maxima = argrelextrema(stock_data['Pct_Over_MA'].values, comparator=np.greater, order=best_window_peak)[0]
local_minima = argrelextrema(stock_data['Pct_Over_MA'].values, comparator=np.less, order=best_window_trough)[0]

# Extract peak and trough values
peak_values = stock_data['Pct_Over_MA'].iloc[local_maxima]
trough_values = stock_data['Pct_Over_MA'].iloc[local_minima]

# Initialize positions array
positions = np.zeros(len(stock_data))

# Define buy and sell signals based on local minima and maxima
for i in range(1, len(stock_data)):
    if i in local_minima:
        positions[i] = 1  # Buy
    elif i in local_maxima:
        positions[i] = -1  # Sell

# Calculate log returns for buy and hold
stock_data['Log_Return_BnH'] = np.log(stock_data['Close'] / stock_data['Close'].shift(1))

# Initialize strategy returns with zeros (log returns start at 0)
strategy_log_returns = np.zeros_like(stock_data['Close'].values)

in_position = False
buy_price = 0

for i in range(1, len(stock_data)):
    if positions[i] == 1 and not in_position:
        # Buy at the closing price
        buy_price = stock_data['Close'].iloc[i]
        in_position = True
        strategy_log_returns[i] = strategy_log_returns[i-1]  # Carry forward previous return
    elif positions[i] == -1 and in_position:
        # Sell at the closing price
        sell_price = stock_data['Close'].iloc[i]
        # Calculate the log return for the sell action
        strategy_log_returns[i] = strategy_log_returns[i-1] + np.log(sell_price / buy_price)
        in_position = False
    elif in_position:
        # Update log returns while holding the position
        current_price = stock_data['Close'].iloc[i]
        daily_log_return = np.log(current_price / stock_data['Close'].iloc[i-1])
        strategy_log_returns[i] = strategy_log_returns[i-1] + daily_log_return
    else:
        # Carry forward the previous return if not in position
        strategy_log_returns[i] = strategy_log_returns[i-1]

# Calculate cumulative log returns for buy and hold strategy
stock_data['Cumulative_Log_Return_BnH'] = stock_data['Log_Return_BnH'].cumsum()

# The log returns for the strategy are already cumulative (as we sum them up)
cumulative_strategy_log_returns = strategy_log_returns

# Plot the results
fig = plt.figure(figsize=(14, 7))

# Plot cumulative log returns
plt.plot(stock_data.index, cumulative_strategy_log_returns * 100, label='Strategy Cumulative Log Returns (%)', color='green', alpha=0.7)
plt.plot(stock_data.index, stock_data['Cumulative_Log_Return_BnH'] * 100, label='Buy and Hold Cumulative Log Returns (%)', color='black', alpha=0.7)

plt.title('Cumulative Log Returns Comparison: Strategy vs. Buy and Hold')
plt.xlabel('Date')
plt.ylabel('Cumulative Log Returns (%)')
plt.legend()
plt.grid(True)

# Show the plot
plt.tight_layout()
plt.show()


# Plot the results
fig=plt.figure(figsize=(14, 14))

# First subplot: Stock Price and x-Day MA
ax1 = plt.subplot(3, 1, 1)
plt.plot(stock_data.index, stock_data['Close'], label=f'{ticker} Price', color='black',alpha=0.6)
plt.plot(stock_data.index, stock_data['x_day_MA'], label=f'{ma_period}-Day MA', color='orange', alpha=0.8)
plt.title(f'{company} ({ticker}) Price and {ma_period}-Day Moving Average (Log Scale)')
# add symbol as watermark
ax1.text(0.5, 0.5, ticker, 
    transform=ax1.transAxes,
    fontsize=50, color='gray', alpha=0.4,
    ha='center', va='center', rotation=0)

plt.xlabel('Date')
plt.ylabel('Price (USD)')
plt.legend()
plt.grid(True, which="both", ls="--")

# Second subplot: Percentage Over/Under x-Day MA with Peaks and Troughs
ax2 = plt.subplot(3, 1, 2, sharex=ax1)
plt.plot(stock_data.index, stock_data['Pct_Over_MA'], label=f'Percentage Over/Under {ma_period}-Day MA', color='blue', alpha=0.6)
plt.axhline(y=0, color='black', linestyle='-', alpha=0.5)

# Fill green above 0 and red below 0
plt.fill_between(stock_data.index, stock_data['Pct_Over_MA'], where=(stock_data['Pct_Over_MA'] >= 0), color='green', alpha=0.3)
plt.fill_between(stock_data.index, stock_data['Pct_Over_MA'], where=(stock_data['Pct_Over_MA'] < 0), color='red', alpha=0.3)

plt.scatter(stock_data.index[local_maxima], peak_values, color='red', label='Peaks', marker='o')
plt.scatter(stock_data.index[local_minima], trough_values, color='green', label='Troughs', marker='o')
plt.title(f'Percentage of Price Over/Under {ma_period}-Day MA with Optimal Peaks and Troughs')
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

now = datetime.strptime(today, "%Y-%m-%d").date()
lastpeak = (now-datetime.strptime(str(peak_values.index[-1]),'%Y-%m-%d %H:%M:%S').date()).days
lasttrough = (now-datetime.strptime(str(trough_values.index[-1]),'%Y-%m-%d %H:%M:%S').date()).days

print(f'last peak={lastpeak}, last trough={lasttrough}')


# BUY signal
if lasttrough < lastpeak and lasttrough < 10: #if last trough is within 5 dyas then buy!
    if trough_values.index[-1] > trough_values.index[-2]: # higher low confirmed
        print(f'STRONG BUY singal observed as Last Trough in {lasttrough} days...')
        signal='STRONGBUY_'
    else:
        print(f'BUY singal observed as Last Trough in {lasttrough} days...')
        signal='BUY_'
# SELL signal
elif lastpeak < lasttrough and lastpeak < 5 :# lower low 
        print(f'SELL singal observed as Last Peak in {lastpeak} days...')
        signal='SELL_'
else:
    print('No trading Singal found')
    signal=''
    
fig.savefig(f'./{today}_{signal}{ticker}_MAdeviation.png')

