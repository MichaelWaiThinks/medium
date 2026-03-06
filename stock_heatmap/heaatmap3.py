#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May  8 16:16:47 2024

@author: michaelwai
"""

from yahooquery import Ticker
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.colors as colors
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.animation as animation

import re
import math
from datetime import datetime,timedelta
import requests
from collections import Counter
import numpy as np
from progress.bar import Bar
import matplotlib.ticker as mtick

title='By Sector MA Plot '
STOCK_DATA_FILE='./data/nasdaq_data.csv'
STOCK_SECTOR_FILE='./data/stock_sector_list.csv'
STARTDATE='2024-04-26'
ENDDATEplus1=(datetime.now()+timedelta(days=1)).strftime("%Y-%m-%d")
ENDDATE=(datetime.now()).strftime("%Y-%m-%d")
target_symbols=['TSLA','AAPL','GOOG','MSFT','MSTR','NVDA','AMD','GM','GS','C','SNAP','AI']
SHORTMA = 50
LONGMA = 100
PLOTDAYS = 1

num_sectors = 0 #11
num_cols = 0
num_rows = 0



def get_stock_sector(symbols):


    sector_data=[]
    
    print ('Getting Ticker profiles...')
    # if file not exists or data not in range, lets redownload
    asset_profiles = Ticker(symbols).asset_profile
    print ('Getting Ticker profiles... completed')

    # Loop through each ticker and retrieve its asset profile
    
    for symbol in symbols:
        try:
            # print(symbol)
            # Use Ticker to retrieve asset profile information
            # asset_profile = Ticker(symbol).asset_profile
            # Extract the sector information
            sector = asset_profiles[symbol]['sector']
            # print (sector)
            # Append sector information to the list
            sector_data.append({'Symbol': symbol, 'Sector': sector})
        except Exception as e:
            print ('skipping ',symbol,':',str(e))
            
    # Create a DataFrame from the sector information
    sector_df = pd.DataFrame(sector_data).dropna()
    sector_df.to_csv(STOCK_SECTOR_FILE, index=False)
    return sector_df

def get_tickers_price(symbols,_start_date='2024-03-05',_end_date='2024-05-08'):
    import os
    import yfinance as yf
    
    if os.path.isfile(STOCK_DATA_FILE):
        print('reading from stock data file...')
        df=pd.read_csv(STOCK_DATA_FILE)#,index_col=0,header=[0,1])#if want to skip multicolumn header-> index_col=1,  header=None,skiprows=1
        df=df.set_index('Date')
        # df.reset_index(drop=True, inplace=True)
        # df=df[['Date','Close']]
        # df=df.droplevel(0, axis=1)  #remove first level
        # df=df.rename(columns={ df.columns[0]: "Date" }).set_index('Date')  # df=df.reset_index()
        df.index=pd.to_datetime(df.index).strftime('%Y-%m-%d')

        print('df=\n',df)
        
        print ('set(symbols).issubset(df.columns)=',symbols,df.columns,set(symbols).issubset(df.columns))
        print ('min(df.index) <= _start_date ',min(df.index) <= _start_date )
        print ('max(df.index) >= _end_date',max(df.index) >= _end_date, max(df.index), _end_date)
        
        if set(symbols).issubset(df.columns) and\
               min(df.index) <= _start_date and \
                max(df.index) >= _end_date:
            return df.loc[(df.index>=_start_date) & (df.index<=_end_date)]
    
    
    input('really want to download again?')
    print ('getting stock data from yahoo!')
    ENDDATE_plus_1=(datetime.now()+timedelta(days=1)).strftime("%Y-%m-%d")

    df = (yf.download(symbols,start=_start_date,end=ENDDATE_plus_1)).reset_index() #download all symbols at once

    df = df[['Date','Close']]
    df=df.droplevel(0, axis=1)  #remove first level
    df=df.rename(columns={ df.columns[0]: "Date" }).set_index('Date')  # df=df.reset_index()
    df.index=pd.to_datetime(df.index).strftime('%Y-%m-%d')
    df.to_csv(STOCK_DATA_FILE)

    return df

# Step 1: Read the file containing symbols and sectors
data=get_stock_sector(target_symbols)
# data = pd.read_csv(STOCK_SECTOR_FILE)  # assuming 'stocks.csv' contains symbols and sectors
# data = data.dropna()
# =============================================================================
#   Symbol                  Sector
#     TSLA       Consumer Cyclical
#     AAPL              Technology
#     GOOG  Communication Services
#     MSFT              Technology
#     MSTR              Technology
#     NVDA              Technology
#      AMD              Technology
#       GM       Consumer Cyclical
#       GS      Financial Services
#        C      Financial Services
#    SNAP  Communication Services
# =============================================================================
# Step 2: Get unique symbols
symbols = data['Symbol'].unique().tolist()

# symbols=target_symbols
# data=get_stock_sector(symbols)
# print(data,symbols)


# historical_prices=get_tickers_price(symbols)
historical_prices=get_tickers_price(target_symbols)

# print (historical_prices, historical_prices.describe())
# Step 3: Retrieve historical prices for all symbols
# historical_prices = yf.download(symbols, period="max", group_by='column', auto_adjust=True)['Close']

# Step 4: Convert the index to datetime and rename columns to match symbols
historical_prices.index = pd.to_datetime(historical_prices.index)
# historical_prices.columns = symbols
# print (historical_prices)


# Step 5: Create a dictionary of historical prices for each symbol
prices_dict = {symbol: historical_prices[symbol] for symbol in symbols}

# print (prices_dict)
# =============================================================================
# 
# # Step 6: Create an empty DataFrame to store sector-wise historical prices
# sector_prices = pd.DataFrame()
# 
# # Step 7: Group stocks by sector and concatenate historical prices
# for sector, group in data.groupby('Sector'):
#     sector_data = group.drop(columns=['Sector'])
#     sector_data.set_index('Symbol', inplace=True)
#     sector_prices = pd.concat([sector_prices, sector_data.apply(lambda x: prices_dict[x.name], axis=1)], axis=0)
#     print ('sector_prices=', sector, group,sector_prices)
#     input(sector+'?')
#     
#     
# =============================================================================


# Step 6: Create an empty DataFrame to store sector-wise historical prices
sector_prices = pd.DataFrame()

# Step 7: Group stocks by sector and concatenate historical prices
for sector, group in data.groupby('Sector'):
    sector_data = group.drop(columns=['Sector'])
    sector_data = sector_data.set_index('Symbol')#, inplace=True)
        
    print('sector_data',sector_data,'\nsector_data')
    
    for s in sector_data.index:
        print(s)
        # print ('*',sector_data.apply(lambda x:prices_dict[x.name],'*\n'))
        
    sector_prices = pd.concat([sector_prices, sector_data.apply(lambda x:prices_dict[x.name], axis=1)], axis=0)
    
    print (sector_prices)
    input('now?')
# Transpose the sector_prices DataFrame
sector_prices_transposed = sector_prices.T

# Step 9: Plot the heatmap for each sector
num_sectors = data.groupby('Sector').ngroups #11

num_rows=math.ceil(math.sqrt(num_sectors))
num_cols=math.ceil(math.sqrt(num_sectors))
if num_rows*num_cols-num_sectors >= num_rows: # find the best fit square array of charts
    num_rows-=1
    
# num_cols = min(4, num_sectors)
# num_rows = math.ceil(num_sectors / num_cols)
print ('Subplot size:',num_cols,num_rows)

# print (range(30,0,-1) )
for target_date in range(PLOTDAYS,0,-1) :
    fig, axes = plt.subplots(dpi=300, nrows=num_rows, ncols=num_cols, figsize=(num_cols * 6, num_rows * 4), sharex=False,sharey=False)

    target_date = target_date*-1
    
    plt.cla()
    
    print(sector_prices_transposed)
    input('ok?')
    
# =============================================================================
#     for i in range(len(axes)):
#         ax = axes[int(i%num_rows),int(i/num_rows)]
#         ax.clear()
#         
# =============================================================================
    with Bar('Processing ' + str(historical_prices.index[target_date]) + '('+str(target_date)+ '/'+str(PLOTDAYS)+'):', max=11) as bar:
        
        for i, (sector, group) in enumerate(data.groupby('Sector')):
            
            prices = sector_prices_transposed[group['Symbol']]
            
            print ('##',i,'\n\n',sector,group,'\n*****\n',prices,'\n*****')
            symbollist=group['Symbol'].tolist()
            shortMA = prices.copy()
            shortMA = shortMA.rolling(window=SHORTMA).mean()
            shortMA = round((prices-shortMA)/shortMA*100,2)
            # shortMA = shortMA.apply(lambda x: remove_outliner(x))
            longMA = prices.copy()
            longMA = longMA.rolling(window=LONGMA).mean()
            longMA = round((prices-longMA)/longMA*100,2)
            # longMA = longMA.apply(lambda x: remove_outliner(x))
        
            ax = axes[int(i%num_rows),int(i/num_rows)]

            print ('plotting ax[',int(i%num_rows),',',int(i/num_rows),']', sector)
            
            ax.axhline(0,color='red',linewidth=1,alpha=0.5)
            ax.axvline(0,color='red',linewidth=1,alpha=0.5)
    
    # =============================================================================
    #             print('before:',len(shortMA))
    #             shortMA=shortMA.dropna()
    #             longMA=longMA.dropna()
    #             print('after:',len(shortMA))
    # =============================================================================
            print ('\n*****',target_date,':',shortMA,longMA,'\n*****')            
            ax.scatter(shortMA.iloc[target_date],longMA.iloc[target_date], alpha=0.5, color='gray') #cmap=plt.cm.Spectral)
            
            
            for s in symbollist:
                if s in target_symbols: # plot our target stocks location
                    if shortMA[s].iloc[target_date] != np.nan and longMA[s].iloc[target_date] != np.nan:
                        ax.scatter(shortMA[s].iloc[target_date],longMA[s].iloc[target_date], color='red', alpha=1, zorder=100)
                        ax.text(shortMA[s].iloc[target_date],longMA[s].iloc[target_date],s,fontsize=6,color='brown', zorder=120)
                        continue
                    
                # if price is close to both short and long MA by 1% which means they are going to cross and need to monitor
                if abs(shortMA[s].iloc[target_date]-longMA[s].iloc[target_date]) <= 0.001 * max(shortMA[s].iloc[target_date],longMA[s].iloc[target_date]):
                       ax.scatter(shortMA[s].iloc[target_date],longMA[s].iloc[target_date], color='green', alpha=1, zorder=100)
                       ax.text(shortMA[s].iloc[target_date],longMA[s].iloc[target_date],s,fontsize=6,color='black', zorder=120)
                       continue
                
                if shortMA[s].iloc[target_date] != np.nan and longMA[s].iloc[target_date] != np.nan:
                        ax.text(shortMA[s].iloc[target_date],longMA[s].iloc[target_date],s,color='gray',fontsize=5)
            
            ax.set_title(sector)
            ax.xaxis.set_major_formatter(mtick.PercentFormatter())
            ax.yaxis.set_major_formatter(mtick.PercentFormatter())
            ax.set_xlabel(str(SHORTMA)+' days MA')
            ax.set_ylabel(str(LONGMA)+' days MA')
            
            bar.next()
    # print (data.columns)
    
    fig.suptitle('Moving Average distribution by sector '+ str(historical_prices.index[target_date]))
    # fig.legend()
    plt.tight_layout()
    plt.show()
    fig.savefig('/Users/michaelwai/Downloads/stockMAheatmap'+'_('+str(historical_prices.index[target_date])+'.jpg')
