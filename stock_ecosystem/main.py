import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd

# Define stock tickers and their categories (including more NVIDIA customers)
tickers = ['NVDA', 'AMD', 'INTC', 'AMZN', 'MSFT', 'GOOGL', 'ORCL', 'IBM', 'EQIX', 'DLR', 'DELL', 'META', 'TSLA', 'BABA']
categories = {
    'NVDA': 'NVIDIA',
    'AMD': 'Competitor',
    'INTC': 'Competitor',
    'AMZN': 'Customer',
    'MSFT': 'Customer',
    'GOOGL': 'Customer',
    'ORCL': 'Partner',
    'IBM': 'Partner',
    'EQIX': 'Supplier',
    'DLR': 'Supplier',
    'DELL': 'Customer/Partner',
    'META': 'Customer',
    'TSLA': 'Customer',
    'BABA': 'Customer'
}

# Download stock price data
data = yf.download(tickers, start="2022-01-01", end="2024-01-01")['Adj Close']

# Normalize stock prices to start at 100
normalized_data = data / data.iloc[0] * 100

# Calculate 30-day rolling correlation with NVIDIA
correlation_matrix = normalized_data.corr()

# Create a figure with a 5x5 grid layout
fig, axarr = plt.subplots(5, 5, figsize=(22, 22))  # Adjusted figure size

# Remove the center subplot (3,3) for the heatmap
for ax in axarr.flat:
    ax.set_xticks([])
    ax.set_yticks([])

ax_center = axarr[2, 2]  # Center subplot for heatmap
sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0, ax=ax_center)
ax_center.set_title('Correlation Heatmap\nStock Price vs NVDA', fontsize=16)

# Define color map for categories
category_colors = {
    'NVIDIA': 'green',
    'Competitor': 'red',
    'Customer': 'blue',
    'Partner': 'purple',
    'Supplier': 'orange',
    'Customer/Partner': 'cyan'
}

# Fill in subplots around the center heatmap
positions = [(i, j) for i in range(5) for j in range(5) if not (i == 2 and j == 2)]
for i, (ticker, pos) in enumerate(zip(tickers, positions)):
    if ticker == 'NVDA':
        continue  # Skip NVIDIA for individual plots since it's in the heatmap
    
    # Determine subplot position
    ax = axarr[pos[0], pos[1]]

    # Plot normalized stock price
    ax.plot(normalized_data.index, normalized_data[ticker], color=category_colors[categories[ticker]], label=ticker)
    ax.set_title(f'{ticker} ({categories[ticker]})', fontsize=10)
    
    # Plot correlation value with NVIDIA inside the subplot
    corr_value = correlation_matrix['NVDA'][ticker]
    ax.text(0.5, 0.5, f"Corr: {corr_value:.2f}",
            horizontalalignment='center', verticalalignment='center',
            transform=ax.transAxes, fontsize=12, color='black', bbox=dict(facecolor='white', alpha=0.7))

# Show the final figure
plt.suptitle('NVIDIA Ecosystem: Stock Price Trends & Correlations', fontsize=18, y=0.92)
plt.tight_layout()
plt.show()
