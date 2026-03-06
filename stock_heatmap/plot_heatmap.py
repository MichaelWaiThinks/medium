import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.colors as colors
from matplotlib.colors import LinearSegmentedColormap
import re
import math
from datetime import datetime,timedelta
import requests
from collections import Counter

def get_nasdaq_holdings(year):
    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36',
    }
    # Function to get QQQ holdings for a given year
    url = f"https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=100&offset=0&download=true&exchange=nasdaq&date={year}-01-01"
    response = requests.get(url,headers=headers)
    data = response.json()
    holdings = data['data']['rows']
    # return holdings
    return {stock['symbol']: stock['name'] for stock in holdings}


# Step 1: Read the file containing symbols and sectors
data = pd.read_csv('./data/stock_sector_list.csv')  # assuming 'stocks.csv' contains symbols and sectors
data=data.dropna()
print(data)


# Step 2: Get unique symbols
symbols = data['Symbol'].unique()
STOCK_DATA_FILE='./data/stock_data_nasdaq.csv'
STARTDATE='2023-01-01'
ENDDATE=(datetime.now()-timedelta(days=1)).strftime("%Y-%m-%d")
ENDDATE=(datetime.now()).strftime("%Y-%m-%d")
ENDDATE='2024-05-23'
# symbols_dict=get_nasdaq_holdings(2024)
# symbols=list(symbols_dict.keys())

symbols =['AAPL','NVDA','TSLA','^GSPC', '^DJI', '^IXIC', '^RUT', '^GSPTSE',
         '^BVSP', '^MXX',
          '^N225', '^HSI', '000001.SS', '399001.SZ', '^TWII', '^KS11',
         '^STI', '^JKSE', '^KLSE', '^AXJO', '^NZ50', '^BSESN',
         '^BSESN',# '^TA125.TA',
         '^FTSE', '^GDAXI', '^FCHI', '^STOXX50E', '^N100', '^BFX']

# historical_prices = pd.read_csv(STOCK_DATA_FILE)  # assuming 'stocks.csv' contains symbols and sectors
# print (set(symbols).issubset(historical_prices.columns))
historical_prices=pd.DataFrame([])
if  historical_prices.empty or set(symbols).issubset(historical_prices.columns):
    historical_prices = yf.download(symbols, period="max", group_by='column', auto_adjust=True)['Close']
    historical_prices.to_csv(STOCK_DATA_FILE)#,index=False)
    historical_prices=historical_prices.reset_index()
    print(historical_prices.columns)

# print (historical_prices['Date'].iloc[0],'-',historical_prices['Date'].iloc[-1])
historical_prices = historical_prices[historical_prices['Date']<ENDDATE]

# historical_prices = historical_prices[symbols.tolist()] #get a list of symbols and remove the rest
# print (historical_prices.columns)
# print (symbols)
# print( '\n\n\ndifference:\n',list((Counter(symbols) - Counter(historical_prices.columns)).elements()))

historical_prices = historical_prices[symbols] #get a list of symbols and remove the rest

# print(historical_prices.tail())

# Step 4: Convert the index to datetime and rename columns to match symbols
historical_prices.index = pd.to_datetime(historical_prices.index)
historical_prices.columns = symbols

# Step 5: Create a dictionary of historical prices for each symbol
prices_dict = {symbol: historical_prices[symbol] for symbol in symbols}

# Step 6: Create an empty DataFrame to store sector-wise historical prices
sector_prices = pd.DataFrame()

# Step 7: Group stocks by sector and concatenate historical prices
for sector, group in data.groupby('Sector'):
    sector_data = group.drop(columns=['Sector'])
    sector_data.set_index('Symbol', inplace=True)
    sector_prices = pd.concat([sector_prices, sector_data.apply(lambda x: prices_dict[x.name], axis=1)], axis=0)

# =============================================================================
# print(sector_prices)
# sector_prices.to_csv('sector_prices.csv')
# data.to_csv('data.csv')
# =============================================================================

# Transpose the sector_prices DataFrame
sector_prices_transposed = sector_prices.T

# Calculate correlation matrix for each sector
correlation_matrices = {}
for sector, group in data.groupby('Sector'):
    prices = sector_prices_transposed[group['Symbol']]
    correlation_matrices[sector] = prices.corr()

print (prices)
prices.to_csv('sector_prices.csv')

# Plot the heatmap for each sector
num_sectors = len(correlation_matrices)
num_cols = min(4, num_sectors)
num_rows = math.ceil(num_sectors / num_cols)


# =============================================================================
# Plot the stock to stock correlation
# =============================================================================
plt.figure(figsize=(num_cols * 6, num_rows * 4))

for i, (sector, corr_matrix) in enumerate(correlation_matrices.items(), 1):
    ### SORT SECTORS
    # # Sort sectors based on correlation with the first sector
    sorted_sectors = corr_matrix.iloc[:, 0].sort_values(ascending=True).index
    # # Reorder the correlation matrix based on sorted sectors
    corr_matrix_sorted = corr_matrix.reindex(index=sorted_sectors, columns=sorted_sectors)
    
    plt.subplot(num_rows, num_cols, i)
    ax=sns.heatmap(corr_matrix_sorted, cmap='Reds', annot=False, fmt=".2f")
    # sns.heatmap(corr_matrix, cmap='coolwarm', annot=True, fmt=".2f")
    
# =============================================================================
#     # ax.tick_params(left=False, bottom=False) ## other options are right and top
# =============================================================================

    plt.suptitle('Correlation Heatmap - '+STARTDATE+' to '+ENDDATE)
    plt.title(f'Correlation Heatmap - {sector}')
    plt.xlabel('Stock Symbols')
    plt.ylabel('Stock Symbols')
    plt.tight_layout()


# =============================================================================
# # Calculate average stock price for each sector
# =============================================================================
average_sector_prices = {}
print(sector_prices_transposed.columns)
for sector, group in data.groupby('Sector'):
    prices = sector_prices_transposed[group['Symbol']]
    average_prices = prices.mean(axis=1)
    # average_prices = prices/prices.iloc[0](axis=1)
    average_sector_prices[sector] = average_prices


# Calculate correlation matrix between average sector prices
correlation_matrix_sectors = pd.DataFrame()


for sector1 in average_sector_prices:
    for sector2 in average_sector_prices:
        corr = average_sector_prices[sector1].corr(average_sector_prices[sector2])
        correlation_matrix_sectors.loc[sector1, sector2] = corr
# sns.clustermap

### SORT SECTORS
# Sort sectors based on correlation with the first sector
sorted_sectors = correlation_matrix_sectors.iloc[:, 0].sort_values(ascending=True).index
# Reorder the correlation matrix based on sorted sectors
correlation_matrix_sectors_sorted = correlation_matrix_sectors.reindex(index=sorted_sectors, columns=sorted_sectors)

# =============================================================================
# # Plot the heatmap for sectors correlation
# =============================================================================
plt.figure(figsize=(10, 8))
ax1=sns.heatmap(correlation_matrix_sectors_sorted, cmap='coolwarm', annot=False, fmt=".2f")
# ax2=sns.clustermap(correlation_matrix_sectors_sorted, cmap='coolwarm', annot=False, fmt=".2f")
# sns.heatmap(correlation_matrix_sectors, cmap='coolwarm', annot=True, fmt=".2f")
sns.clustermap(correlation_matrix_sectors, cmap='coolwarm', annot=True, fmt=".2f")

ax1.tick_params(left=False, bottom=False) ## other options are right and top
# ax2.tick_params(left=False, bottom=False) ## other options are right and top

plt.title('Correlation Heatmap - Sectors')
plt.xlabel('Sectors')
plt.ylabel('Sectors')
plt.tight_layout()
plt.show()
