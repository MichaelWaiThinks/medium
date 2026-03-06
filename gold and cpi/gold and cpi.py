#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 23 00:58:24 2024

TITLE: Depreciation of US$ vs Gold

***** API_KEY = 'a4049a1e2039b9a7a8ceb6aa3afa3dc7'    ******

@author: michaelwai
"""
import pandas as pd
import matplotlib.pyplot as plt
from fredapi import Fred
import yfinance as yf
import datetime as dt

# today=dt.datetime.now().strftime('%Y-%m-%d')

# Get today's date
today = pd.Timestamp(dt.datetime.today())
print(f'** TODAY = {today} **')

# Add recession periods as a list of tuples (start_date, end_date)
def add_recession(ax):
    recession_periods = [
        ('1973-11-01', '1975-03-01'),
        ('1980-01-01', '1980-07-01'),
        ('1981-07-01', '1982-11-01'),
        ('1990-07-01', '1991-03-01'),
        ('2001-03-01', '2001-11-01'),
        ('2007-12-01', '2009-06-01'),
        ('2020-02-01', '2020-04-01')  # COVID-19 recession
    ]
    
    # Plot grey spans for each recession period
    for start, end in recession_periods:
        ax.axvspan(pd.to_datetime(start), pd.to_datetime(end), color='lightgrey', alpha=0.5)

# Add text annotations for major historical events related to gold prices
def add_incidents(ax):
    
    # Add text annotations for major historical events related to gold prices
    offset=100
    text_color='gray'
    # End of Bretton Woods system (1971)
    ax.annotate('End of Bretton Woods (1971)', 
                 xy=(pd.to_datetime('1971-08-15'), 50), 
                 xytext=(pd.to_datetime('1971-08-15'), 100+offset),  # Place above the price
                 arrowprops=dict(facecolor=text_color, arrowstyle='->'), fontsize=8, ha='center')
    
    # Stagflation crisis and gold surge (1980)
    ax.annotate('Stagflation and Gold Surge ($665)', 
                 xy=(pd.to_datetime('1980-01-01'), 665), 
                 xytext=(pd.to_datetime('1980-01-01'), 750+offset),  # Place above the price
                 arrowprops=dict(facecolor=text_color, arrowstyle='->'), fontsize=8, ha='center')
    
    # Gold price local low (1999)
    ax.annotate('Gold Low ($253)', 
                 xy=(pd.to_datetime('1999-01-01'), 253), 
                 xytext=(pd.to_datetime('1999-01-01'), 300+offset),  # Place above the price
                 arrowprops=dict(facecolor=text_color, arrowstyle='->'), fontsize=8, ha='center')
    
    # Great Recession and gold rise (2008)
    ax.annotate('Great Recession (2008)', 
                 xy=(pd.to_datetime('2008-10-01'), 730), 
                 xytext=(pd.to_datetime('2008-10-01'), 800+offset),  # Place above the price
                 arrowprops=dict(facecolor=text_color, arrowstyle='->'), fontsize=8, ha='center')
    
    # European debt crisis and gold high (2011)
    ax.annotate('Euro Debt Crisis ($1,825)', 
                 xy=(pd.to_datetime('2011-08-01'), 1825), 
                 xytext=(pd.to_datetime('2011-08-01'), 1900+offset),  # Place above the price
                 arrowprops=dict(facecolor=text_color, arrowstyle='->'), fontsize=8, ha='center')
    
    # Gold price decline during Fed tapering (2013-2014)
    ax.annotate('Fed Tapering (2013-14)', 
                 xy=(pd.to_datetime('2013-01-01'), 1695), 
                 xytext=(pd.to_datetime('2013-01-01'), 1800+offset),  # Place above the price
                 arrowprops=dict(facecolor=text_color, arrowstyle='->'), fontsize=8, ha='center')
    
    # COVID-19 pandemic and gold price surge (2020)
    ax.annotate('COVID-19 Surge ($2,000)', 
                 xy=(pd.to_datetime('2020-07-01'), 2000), 
                 xytext=(pd.to_datetime('2020-07-01'), 2100+offset),  # Place above the price
                 arrowprops=dict(facecolor=text_color, arrowstyle='->'), fontsize=8, ha='center')
    
    # Post-pandemic gold high in 2024
    ax.annotate('Gold All-Time High 2024-09-23($2,648)', 
                 xy=(pd.to_datetime('2024-09-23'), 2500), 
                 xytext=(pd.to_datetime('2024-09-23'), 2500+offset),  # Place above the price
                 arrowprops=dict(facecolor=text_color, arrowstyle='->'), fontsize=8, ha='center')
    

# Step 1: Set up FRED API key
API_KEY = 'a4049a1e2039b9a7a8ceb6aa3afa3dc7'  # Replace with your actual FRED API key
fred = Fred(api_key=API_KEY)

# Step 2: Retrieve CPI data from FRED (1971 to 2023)
cpi_series_id = 'CPIAUCSL'  # CPI for All Urban Consumers
# cpi_series_id = 'CPILFESL'  # CPI for All Urban Consumers: All Items Less Food & Energy"- less voliatile 
cpi_data = fred.get_series(cpi_series_id, observation_start='1971-01-01', observation_end=today)

# Step 3: Prepare the CPI data
df_cpi = pd.DataFrame({'CPI': cpi_data})
df_cpi.index = pd.to_datetime(df_cpi.index)
df_cpi_monthly = df_cpi.resample('ME').mean()
df_cpi_monthly['Inverse USD Value'] = 100 / (df_cpi_monthly['CPI'] / df_cpi_monthly['CPI'].iloc[0])

print (df_cpi_monthly)
# Step 4: Load historical gold price data from Macrotrends (download CSV)
# URL: https://www.macrotrends.net/1333/historical-gold-prices-100-year-chart
# Let's assume the CSV file is downloaded and named 'gold_prices_macrotrends.csv'
# =============================================================================
# try:
#     gold_data = pd.read_csv('./goldprice.csv')  # Adjust skiprows if needed based on your CSV structure
#     print("Columns in the file:", gold_data.columns)  # Display column names
# except Exception as e:
#     print("An error occurred:", e)
# 
# # Assuming we identify the correct date column, we can then load the file with date parsing
# date_col = input("Please enter the correct name for the date column, based on the output above: ")
# # gold_data = pd.read_csv('./goldprice.csv', skiprows=1, parse_dates=[date_col], index_col=date_col)
# 
# # Display the first few rows to confirm correct loading and parsing
# print(gold_data.head())
# =============================================================================

# You would download and manually save the CSV from the website to avoid scraping issues
# gold_data = pd.read_csv('goldprice.csv', skiprows=1)
gold_data = pd.read_csv('goldprice.csv', parse_dates=['Date'], index_col='Date',dayfirst=True)

# Check the last date in the CSV data
last_csv_date = gold_data.index.max()


# Check if the last date in CSV is less than this month's start
if last_csv_date < today:
    print(f'Fetching remaining data from {last_csv_date} to {today}')
    # Fetch data from yfinance from the day after the last date in CSV to today
    new_gold_data = yf.download('XAUT-USD', start=last_csv_date + pd.Timedelta(days=1), end=today)
    
    # Process the new data: resample and clean as necessary
    new_gold_data = new_gold_data['Close'].resample('D').ffill()  # Resample daily and forward-fill any missing data
    
    # Combine the old data with new data
    gold_data = pd.concat([gold_data, new_gold_data])
    
    print(gold_data)
    
# Save the combined data if needed or proceed with further processing
gold_data.to_csv('goldprice.csv')

gold_data=gold_data.reset_index()


# Step 5: Clean and prepare the gold price data
print(gold_data.columns)
gold_data=gold_data[['Date','Close']]
gold_data.columns = ['Date', 'Close']  # Rename columns
gold_data['Date'] = pd.to_datetime(gold_data['Date'],dayfirst=True)
# gold_data.set_index('Date', inplace=True)

# Resample to monthly data and align it with the CPI data
gold_data_monthly = gold_data.resample('ME').mean()

# Step 6: Combine the CPI and Gold Price data
df_combined = pd.DataFrame({
    'Close': gold_data_monthly['Close'],
    'Inverse USD Value': 1/df_cpi_monthly['Inverse USD Value']
})

# Step 7: Plot the data using a twin-y axis
fig, ax1 = plt.subplots(figsize=(10, 6))

# Plot gold price on the left y-axis
ax1.set_xlabel('Year', fontsize=12)
ax1.set_ylabel('Monthly (average) Gold Price (USD per ounce)', color='red', fontsize=12)
ax1.plot(df_combined.index, df_combined['Close'], color='red', label='Gold Price (USD per ounce)', alpha=0.7)
ax1.tick_params(axis='y', labelcolor='red')

# Create the second y-axis and plot the inverse USD value
ax2 = ax1.twinx()
ax2.set_ylabel('Inverse USD Value (1971=100)', color='steelblue', fontsize=12)
ax2.plot(df_combined.index, df_combined['Inverse USD Value'], color='steelblue', linestyle='-', label='Inverse USD Value (1971=100)', alpha=0.7)
ax2.tick_params(axis='y', labelcolor='steelblue')

# Set x-ticks for every 5 year and rotate labels for better readability
ax1.set_xticks(pd.date_range(start=df_combined.index.min(), end=df_combined.index.max(), freq='1YS'))  # 'YS' is Year Start frequency for every year
ax1.set_xticklabels([label.strftime('%Y') for label in pd.date_range(start=df_combined.index.min(), end=df_combined.index.max(), freq='1YS')], rotation=90)

# Enable grid only on x-axis, drawing lines at major ticks (every 10 years)
ax1.grid(which='major', linestyle='-', linewidth='0.5', color='lightgray')
ax1.grid(which='minor', linestyle='-', color='red')  # Disable minor grid lines

add_recession(ax1)
add_incidents(ax1)

print(df_combined.tail())

# Title and legend
plt.title(f'Gold Price vs. Inverse USD Purchasing Power (Monthly Data, 1971-{today.year})', fontsize=14)
fig.tight_layout()
plt.grid(True)
plt.show()


