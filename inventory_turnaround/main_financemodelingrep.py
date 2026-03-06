api_key = '26017e40c3959430972038daf440335e'

import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import requests

# Fetch Walmart's financial data from FMP

ticker_symbol = 'WMT'

# Fetch income statement (for COGS)
income_statement_url = f'https://financialmodelingprep.com/api/v3/income-statement/{ticker_symbol}?limit=10&apikey={api_key}'
income_statement_data = requests.get(income_statement_url).json()

# Fetch balance sheet (for Inventory)
balance_sheet_url = f'https://financialmodelingprep.com/api/v3/balance-sheet-statement/{ticker_symbol}?limit=10&apikey={api_key}'
balance_sheet_data = requests.get(balance_sheet_url).json()

# Convert data to DataFrame
income_df = pd.DataFrame(income_statement_data)
balance_df = pd.DataFrame(balance_sheet_data)

# Extract necessary fields: Date, COGS, and Inventory
income_df = income_df[['date', 'costOfRevenue']]
balance_df = balance_df[['date', 'inventory']]

# Merge the dataframes on the date
df = pd.merge(income_df, balance_df, on='date')

# Sort the dataframe by date (ascending order)
df = df.sort_values(by='date')

# Rename columns for clarity
df.rename(columns={'costOfRevenue': 'COGS', 'inventory': 'Inventory'}, inplace=True)

# Convert to numeric values (in case they are not already)
df['COGS'] = pd.to_numeric(df['COGS'], errors='coerce')
df['Inventory'] = pd.to_numeric(df['Inventory'], errors='coerce')

# Calculate the Inventory Turnover Ratio
df['Average Inventory'] = df['Inventory'].rolling(window=2).mean()
df['Turnover Ratio'] = df['COGS'] / df['Average Inventory']

# Fetch share prices for the date range from Yahoo Finance
share_price_data = yf.download(ticker_symbol, start=df['date'].min(), end=df['date'].max(), progress=False)

# Reset the index to make 'Date' a column
share_price_data.reset_index(inplace=True)

# Select the 'Close' price and merge with existing data based on the date
df['date'] = pd.to_datetime(df['date'])
share_price_data['Date'] = pd.to_datetime(share_price_data['Date'])
df = pd.merge(df, share_price_data[['Date', 'Close']], left_on='date', right_on='Date', how='left')

# Rename the 'Close' column to 'Share Price' for clarity
df.rename(columns={'Close': 'Share Price'}, inplace=True)

# Plotting the data in three subplots with shared x-axis
fig, ax = plt.subplots(3, 1, figsize=(12, 18), sharex=True)

# Plot Inventory Turnover Ratio
ax[0].plot(df['date'], df['Turnover Ratio'], marker='o', color='b', label='Inventory Turnover Ratio')
ax[0].set_title('Walmart Inventory Turnover Ratio per Year')
ax[0].set_ylabel('Turnover Ratio')
ax[0].legend()

# Plot Share Price
ax[1].plot(share_price_data['Date'], share_price_data['Close'], color='g', label='Share Price')
ax[1].set_title('Walmart Share Price per Year')
ax[1].set_ylabel('Share Price (USD)')
ax[1].legend()

# Plot COGS and Inventory Turnover Ratio in the same subplot with dual y-axes
ax2 = ax[2].twinx()  # Create a second y-axis
ax[2].plot(df['date'], df['COGS'], marker='o', color='r', label='Cost of Goods Sold (COGS)')
ax2.plot(df['date'], df['Inventory'], marker='o', color='b', linestyle='--', label='Inventory')

ax[2].set_title('Walmart Annual COGS and Inventory')
ax[2].set_ylabel('Inventory')
ax[2].set_xlabel('Date')

# Custom formatting for y-axis to show B, M, K
def format_func(value, tick_position):
    if value >= 1_000_000_000:
        return f'{value/1_000_000_000:.1f}B'
    elif value >= 1_000_000:
        return f'{value/1_000_000:.1f}M'
    elif value >= 1_000:
        return f'{value/1_000:.1f}K'
    else:
        return f'{value:.0f}'

# Apply custom formatting to the primary y-axis (COGS)
ax[2].yaxis.set_major_formatter(ticker.FuncFormatter(format_func))

# Apply custom formatting to the secondary y-axis (Turnover Ratio)
ax2.yaxis.set_major_formatter(ticker.FuncFormatter(format_func))#lambda x, _: f'{x:.1f}'))

# Legends for both y-axes
ax[2].legend(loc='upper left')
ax2.legend(loc='upper right')

# Improve layout to ensure no overlap
plt.tight_layout()

# Display the plots
plt.show()
