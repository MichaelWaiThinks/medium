import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from scipy.signal import savgol_filter
import matplotlib.dates as mdates

# Fetch historical stock price data
ticker = 'COKE'
stock_data = yf.download(ticker, start='2020-01-01', end='2024-12-30')

# Calculate 200-DMA
stock_data['200-DMA'] = stock_data['Close'].rolling(window=200).mean()

# Fetch financial data and calculate price-to-sales ratio
data = yf.Ticker(ticker)
annual_revenue = data.financials.loc['Total Revenue']
shares_outstanding = data.info['sharesOutstanding']

# Calculate revenue per share and price-to-sales ratio
revenue_per_share = annual_revenue / shares_outstanding
annual_revenue_per_share = revenue_per_share.resample('YE').ffill().reindex(stock_data.index, method='ffill')

price_to_sales_ratio = stock_data['Close'] / annual_revenue_per_share 

# Prepare the data
valid_data = pd.DataFrame({
    'Close': stock_data['Close'],
    'Price_to_Sales': price_to_sales_ratio
}).dropna()

# Ensure there are enough data points
if valid_data.empty:
    raise ValueError("The dataset is empty after preprocessing. Please check the data source or preprocessing steps.")

# Apply Savitzky-Golay filter for smoothing
valid_data['Smoothed_Price_to_Sales'] = savgol_filter(valid_data['Price_to_Sales'], window_length=11, polyorder=2)

# Identify peaks and troughs
peaks, _ = find_peaks(valid_data['Smoothed_Price_to_Sales'], distance=90)
troughs, _ = find_peaks(-valid_data['Smoothed_Price_to_Sales'], distance=90)

# Plot the results
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

# Plot the actual stock price
ax1.set_xlabel('Date')
ax1.set_ylabel('Stock Price', color='tab:blue')
ax1.plot(stock_data.index, stock_data['Close'], color='tab:blue', label='Actual Stock Price')
ax1.plot(stock_data.index, stock_data['200-DMA'], color='tab:red', label='200-DMA')
ax1.tick_params(axis='y', labelcolor='tab:blue')

# Plot the smoothed price-to-sales ratio
ax2.set_ylabel('Price to Sales Ratio', color='tab:red')
ax2.plot(valid_data.index, valid_data['Smoothed_Price_to_Sales'], color='tab:red', label='Smoothed Price-to-Sales Ratio', alpha=0.8)

# Plot identified peaks and troughs
ax2.scatter(valid_data.index[peaks], valid_data['Smoothed_Price_to_Sales'][peaks], 
            color='darkred', label='Peaks', marker='v', s=120)

ax2.scatter(valid_data.index[troughs], valid_data['Smoothed_Price_to_Sales'][troughs], 
            color='darkblue', label='Troughs', marker='^', s=120)

# Annotate peaks and troughs
for idx in peaks:
    ax2.annotate(f'{valid_data.index[idx].strftime("%Y-%m-%d")}', xy=(valid_data.index[idx], valid_data['Smoothed_Price_to_Sales'][idx]),
                 xytext=(0,10), textcoords='offset points', arrowprops=dict(arrowstyle='->', lw=0.5))

for idx in troughs:
    ax2.annotate(f'{valid_data.index[idx].strftime("%Y-%m-%d")}', xy=(valid_data.index[idx], valid_data['Smoothed_Price_to_Sales'][idx]),
                 xytext=(0,-15), textcoords='offset points', arrowprops=dict(arrowstyle='->', lw=0.5))

ax2.tick_params(axis='y', labelcolor='tab:red')
ax2.tick_params(axis='x', rotation=90, labelcolor='tab:blue')

# Format the x-axis to show ticks and grid every 3 months
ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

# Add grid lines
ax1.grid(True, which='both', linestyle='--', linewidth=0.3, color='grey')
ax2.grid(True, which='both', linestyle='--', linewidth=0.3, color='grey')

plt.suptitle(f'{ticker} Price (upper) and Smoothed Price-to-Sales Ratio (lower)')
fig.tight_layout()

plt.show()
