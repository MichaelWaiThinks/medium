import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns

STOCK_SECTOR_FILE='./data/stock_sector_list_all.csv'

# Step 1: Read the file containing symbols and sectors
data = pd.read_csv(STOCK_SECTOR_FILE).dropna()  # assuming 'stocks.csv' contains symbols and sectors

# Step 2: Get unique symbols
symbols = data['Symbol'].unique().tolist()
print(symbols)

# Step 3: Retrieve historical prices for all symbols
historical_prices = yf.download(symbols, period="1y", group_by='column', auto_adjust=True)['Close']

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

# Step 8: Calculate correlation matrix for each sector
correlation_matrices = {}
for sector, group in sector_prices.groupby(data['Sector']):
    prices = group.T
    correlation_matrices[sector] = prices.corr()

# Step 9: Plot the heatmap for each sector
plt.figure(figsize=(12, 8))  # Set figure size here
num_sectors = len(correlation_matrices)
num_cols = min(2, num_sectors)
num_rows = (num_sectors + num_cols - 1) // num_cols

for i, (sector, corr_matrix) in enumerate(correlation_matrices.items(), 1):
    plt.subplot(num_rows, num_cols, i)
    sns.heatmap(corr_matrix, cmap='coolwarm', annot=True, fmt=".2f")
    plt.title(f'Correlation Heatmap - {sector}')
    plt.xlabel('Stock Symbols')
    plt.ylabel('Stock Symbols')

plt.tight_layout()
plt.show()

# Step 10: Calculate average stock price for each sector
average_sector_prices = {}

for sector, group in data.groupby('Sector'):
    prices = sector_prices.T[group['Symbol']]
    average_prices = prices.mean(axis=1)
    average_sector_prices[sector] = average_prices

# Step 11: Calculate correlation matrix between average sector prices
correlation_matrix_sectors = pd.DataFrame()

for sector1 in average_sector_prices:
    for sector2 in average_sector_prices:
        corr = average_sector_prices[sector1].corr(average_sector_prices[sector2])
        correlation_matrix_sectors.loc[sector1, sector2] = corr

# Step 12: Sort sectors based on correlation with the first sector
sorted_sectors = correlation_matrix_sectors.iloc[:, 0].sort_values(ascending=False).index

# Step 13: Reorder the correlation matrix based on sorted sectors
correlation_matrix_sectors_sorted = correlation_matrix_sectors.reindex(index=sorted_sectors, columns=sorted_sectors)

# Step 14: Plot the heatmap for sorted sectors correlation
plt.figure(figsize=(10, 8))
sns.heatmap(correlation_matrix_sectors_sorted, cmap='coolwarm', annot=True, fmt=".2f")
plt.title('Correlation Heatmap - Sectors (Sorted)')
plt.xlabel('Sectors')
plt.ylabel('Sectors')
plt.tight_layout()
plt.show()
