# Importing required libraries
import yfinance as yf
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# List of ticker symbols for the stocks
tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']

# Define the start and end dates for the data
start_date = '2022-01-01'
end_date = '2023-01-01'

# Fetching the historical data for each stock
data = yf.download(tickers, start=start_date, end=end_date)['Adj Close']

# Calculating the daily returns
returns = data.pct_change()

# Calculating the correlation matrix
correlation_matrix = returns.corr()

# Sorting the correlation matrix
sorted_corr = correlation_matrix.abs().unstack().sort_values(ascending=False).drop_duplicates()
sorted_tickers = sorted_corr.index.get_level_values(0).unique()
sorted_corr_matrix = correlation_matrix.loc[sorted_tickers, sorted_tickers]

# Plotting the correlation heatmap with a new color scheme
plt.figure(figsize=(10, 8))
sns.heatmap(sorted_corr_matrix, annot=True, cmap='coolwarm', linewidths=0.5, linecolor='black')
plt.title('Sorted Stock Price Correlation Heatmap')
plt.show()
