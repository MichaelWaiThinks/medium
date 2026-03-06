import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from sec_edgar_downloader import Downloader
import re

# Initialize the EDGAR Downloader
dl = Downloader('abc','abc@abc.com')

# Download Walmart's 10-K filings (annual reports) for the last 10 years
ticker = 'WMT'
dl.get("10-K", ticker, limit=3)

# Extract the latest 10-K file path from the downloaded files
import os

def get_latest_10k_path(ticker):
    base_dir = os.path.join('sec-edgar-data', '10-K', ticker)
    files = os.listdir(base_dir)
    files = [f for f in files if f.endswith('.txt')]
    files.sort(reverse=True)  # Sort files by date, newest first
    return os.path.join(base_dir, files[0]) if files else None

latest_10k_path = get_latest_10k_path(ticker)
if not latest_10k_path:
    raise FileNotFoundError("No 10-K filings found.")

# Read the 10-K filing
with open(latest_10k_path, 'r', encoding='utf-8') as file:
    filing_text = file.read()

# Example function to extract financial data (COGS and Inventory)
def extract_financial_data(text):
    cogs_match = re.search(r'Cost of Goods Sold.*?(\$[\d,]+\.?\d*)', text, re.IGNORECASE)
    inventory_match = re.search(r'Inventory.*?(\$[\d,]+\.?\d*)', text, re.IGNORECASE)
    
    cogs = float(cogs_match.group(1).replace('$', '').replace(',', '').replace('(', '-').replace(')', '') if cogs_match else 0)
    inventory = float(inventory_match.group(1).replace('$', '').replace(',', '').replace('(', '-').replace(')', '') if inventory_match else 0)
    
    return cogs, inventory

# Extract data from the latest 10-K filing
cogs, inventory = extract_financial_data(filing_text)

# Example historical data (for demonstration, you should fetch actual data)
dates = pd.date_range(start="2014-01-01", end="2024-01-01", freq='A')
data = {
    'Date': dates,
    'COGS': [cogs] * len(dates),
    'Inventory': [inventory] * len(dates),
    'Share Price': [150] * len(dates)  # Example share price, replace with actual data
}

df = pd.DataFrame(data).set_index('Date')

# Calculate Inventory Turnover Ratio
df['Average Inventory'] = df['Inventory'].rolling(window=2).mean()
df['Turnover Ratio'] = df['COGS'] / df['Average Inventory']

# Plotting the data in three subplots with shared x-axis
fig, ax = plt.subplots(3, 1, figsize=(12, 18), sharex=True)

# Plot Inventory Turnover Ratio
ax[0].plot(df.index, df['Turnover Ratio'], marker='o', color='b', label='Inventory Turnover Ratio')
ax[0].set_title('Walmart Inventory Turnover Ratio per Year')
ax[0].set_ylabel('Turnover Ratio')
ax[0].legend()

# Plot Share Price
ax[1].plot(df.index, df['Share Price'], marker='o', color='g', label='Share Price')
ax[1].set_title('Walmart Share Price per Year')
ax[1].set_ylabel('Share Price (USD)')
ax[1].legend()

# Plot COGS and Inventory Turnover Ratio in the same subplot with dual y-axes
ax2 = ax[2].twinx()  # Create a second y-axis
ax[2].plot(df.index, df['COGS'], marker='o', color='r', label='Cost of Goods Sold (COGS)')
ax2.plot(df.index, df['Turnover Ratio'], marker='o', color='b', linestyle='--', label='Inventory Turnover Ratio')

ax[2].set_title('Walmart Annual COGS and Inventory Turnover Ratio')
ax[2].set_ylabel('Cost of Goods Sold (USD)')
ax2.set_ylabel('Turnover Ratio')
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
ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f'{x:.1f}'))

# Legends for both y-axes
ax[2].legend(loc='upper left')
ax2.legend(loc='upper right')

# Improve layout to ensure no overlap
plt.tight_layout()

# Display the plots
plt.show()
