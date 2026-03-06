import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from scipy.signal import savgol_filter
import matplotlib.dates as mdates

# Fetch historical stock price data
ticker = 'MSFT'
stock_data = yf.download(ticker, start='2020-01-01', end='2024-12-30')

# Calculate 200-DMA
stock_data['200-DMA'] = stock_data['Close'].rolling(window=200).mean()

# Fetch financial data for quarterly and annual revenue
data = yf.Ticker(ticker)
quarterly_revenue = data.quarterly_financials.loc['Total Revenue']  # Fetch quarterly revenue data
annual_revenue = data.financials.loc['Total Revenue']  # Fetch annual revenue data
shares_outstanding = data.info['sharesOutstanding']

# Calculate annual revenue per share and price-to-sales ratio based on annual data
annual_revenue_per_share = (annual_revenue / shares_outstanding).reindex(stock_data.index, method='ffill')
price_to_sales_ratio_annual = stock_data['Close'] / annual_revenue_per_share  # Annual price-to-sales ratio

# Prepare the data
valid_data = pd.DataFrame({
    'Close': stock_data['Close'],
    'Price_to_Sales_Annual': price_to_sales_ratio_annual
}).dropna()

# Apply Savitzky-Golay filter for smoothing the annual price-to-sales ratio
valid_data['Smoothed_Price_to_Sales_Annual'] = savgol_filter(valid_data['Price_to_Sales_Annual'], window_length=11, polyorder=2)

# Identify peaks and troughs
peaks, _ = find_peaks(valid_data['Smoothed_Price_to_Sales_Annual'], distance=90)
troughs, _ = find_peaks(-valid_data['Smoothed_Price_to_Sales_Annual'], distance=90)

# Plot the results
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

# Plot the actual stock price with 200-DMA on ax1
ax1.set_title(f'{ticker} Stock Price and 200-Day Moving Average')
ax1.set_ylabel('Stock Price', color='tab:blue')
ax1.plot(stock_data.index, stock_data['Close'], color='tab:blue', label='Actual Stock Price')
ax1.plot(stock_data.index, stock_data['200-DMA'], color='tab:red', label='200-DMA')
ax1.tick_params(axis='y', labelcolor='tab:blue')
ax1.legend(loc='upper left')
ax1.grid(True, which='both', linestyle='--', linewidth=0.3, color='grey')

# Plot the smoothed annual price-to-sales ratio on ax2
ax2.set_title(f'{ticker} Smoothed Annual Price-to-Sales Ratio with Quarterly Revenue')
ax2.set_ylabel('Annual Price to Sales Ratio', color='tab:red')
ax2.plot(valid_data.index, valid_data['Smoothed_Price_to_Sales_Annual'], color='tab:red', label='Smoothed Price-to-Sales Ratio (Annual)', alpha=0.8)

# Plot identified peaks and troughs on ax2
ax2.scatter(valid_data.index[peaks], valid_data['Smoothed_Price_to_Sales_Annual'][peaks], 
            color='darkred', label='Peaks', marker='v', s=120)
ax2.scatter(valid_data.index[troughs], valid_data['Smoothed_Price_to_Sales_Annual'][troughs], 
            color='darkblue', label='Troughs', marker='^', s=120)

# Add a secondary y-axis on ax2 to plot quarterly revenue as bars
ax3 = ax2.twinx()
ax3.set_ylabel("Quarterly Revenue", color="purple")
ax3.bar(quarterly_revenue.index, quarterly_revenue.values, color="grey", width=30, alpha=0.3, label="Quarterly Revenue")
ax3.bar(annual_revenue.index, annual_revenue.values, color="gray", width=30, alpha=0.5, label="Annual Revenue")
ax3.tick_params(axis='y', labelcolor="purple")

# Annotate peaks and troughs on ax2
for idx in peaks:
    ax2.annotate(f'{valid_data.index[idx].strftime("%Y-%m-%d")}', xy=(valid_data.index[idx], valid_data['Smoothed_Price_to_Sales_Annual'][idx]),
                 xytext=(0,10), textcoords='offset points', arrowprops=dict(arrowstyle='->', lw=0.5))
for idx in troughs:
    ax2.annotate(f'{valid_data.index[idx].strftime("%Y-%m-%d")}', xy=(valid_data.index[idx], valid_data['Smoothed_Price_to_Sales_Annual'][idx]),
                 xytext=(0,-15), textcoords='offset points', arrowprops=dict(arrowstyle='->', lw=0.5))

# Format x-axis and add grid lines
ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
ax2.grid(True, which='both', linestyle='--', linewidth=0.3, color='grey')

# Add legends for clarity
ax2.legend(loc='upper left')
ax1.legend(loc='upper left')

plt.suptitle(f'{ticker} Stock Analysis')
fig.tight_layout(rect=[0, 0.03, 1, 0.95])  # Adjust layout to fit titles

plt.show()
