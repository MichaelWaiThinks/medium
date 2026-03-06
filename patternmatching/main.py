#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May 21 17:53:23 2024

@author: michaelwai
"""

import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from datetime import datetime,timedelta
import requests
import os
import sys
import math
from progress.bar import Bar

COMPARE_PERIOD=90
PREDICT_PERIOD=360

# =============================================================================
#  THIS IS THE VARIABLES YOU WANT TO PLAY WITH
# =============================================================================

target_symbol='GC=F'
COL = 'Open' # you can use Open, Close, High, Low, Adj Close data if need
start_date = '2000-05-14'
end_date = '2026-02-24' 
title_subtitle='You can provide more info for your use'
my_choice_of_symbols =   ['GC=F']#['AAPL', 'MSFT', 'GOOG', 'AMZN', 'META', 'DIS', 'NFLX', 'EDIT', 'PLTR', 'LLY','TSLA']

# =============================================================================
#  BELOW ARE THE MAIN CODES NOT FOR MODIFICATION UNDER YOU KNOW WHAT YOU ARE DOING
# =============================================================================

current_date = datetime.now().strftime("%Y-%m-%d")
currentime = datetime.now().strftime("%Y%m%d_%H%M")

### Add more subtitle if need

print('Program starts on :', current_date, currentime)



# Download and preprocess data
def download_stock_data(symbols, start_date, end_date):
    data = yf.download(symbols, start=start_date, end=end_date)
    return data

# Function to calculate rolling 3-month periods
def rolling_periods(data, window=COMPARE_PERIOD):
    periods = []
    for i in range(len(data) - window + 1):
        periods.append(data.iloc[i:i+window])
    return periods

# Calcuate similarity and return if found
def calculate_similarity(target_period, other_period):
    # Handle NaN values by filling them with the mean of the corresponding column
    target_period_filled = np.nan_to_num(target_period, nan=np.nanmean(target_period))
    other_period_filled = np.nan_to_num(other_period, nan=np.nanmean(other_period))
    
    similarity = cosine_similarity(target_period_filled.reshape(1, -1), other_period_filled.reshape(1, -1))
    return similarity[0][0]

if __name__=='__main__':
    all_stocks_symbols=[]
    target_symbol_sector=''
    
   
    # prepare the symbol llist for comparison including itself
    all_stocks_symbols = my_choice_of_symbols + [target_symbol]
    
    '''
    DOWNLOAD ALL STOCK DATA
    '''  

    all_stock_data = download_stock_data(all_stocks_symbols, start_date, current_date)
    all_stock_data = all_stock_data.ffill()
    print(all_stock_data.columns, target_symbol,all_stock_data[COL])
    full_target_stock_data=all_stock_data[COL][target_symbol]
    target_stock_data=full_target_stock_data[:end_date] #only extract up to the target period
    print(target_stock_data)
    # use all stocks to compare, if one wants to remove target_symbol pls uncomment below instead
    # other_stocks_symbols =  my_choice_of_symbols
    other_stocks_symbols = all_stocks_symbols
      
    # Select the last 3 months of Apple's stock prices
    target_stock_recent_data = all_stock_data[COL][target_symbol][:end_date].tail(COMPARE_PERIOD)
    
    # Calculate rolling 3-month periods for each stock data
    other_rolling_periods = {}
    for symbol in other_stocks_symbols:  # Excluding Apple, as we already have its data
        if symbol==target_symbol: #if symbol is itself, exclude same period to avoid comparison to same period - otherwise same period always WIN! :_)
            self_compare_period=(pd.to_datetime(end_date)-timedelta(days=COMPARE_PERIOD)).strftime("%Y-%m-%d")
            other_rolling_periods[symbol] = rolling_periods(all_stock_data[COL][symbol][:self_compare_period])
        else:
            other_rolling_periods[symbol] = rolling_periods(all_stock_data[COL][symbol][:end_date])
    
    # Find the most similar period
    most_similar_stock = None
    most_similar_index = None
    highest_similarity = -1
    
    for symbol, periods in other_rolling_periods.items():
        with Bar('comparing '+symbol, max=len(periods)) as bar:
            for i, period in enumerate(periods):
                # print ('checking similarity...',symbol,'\n',period.values)
                if (period.isnull().all()): #i.e. if Nan
                    continue
                else:
                    similarity = calculate_similarity(target_stock_recent_data.values, period.values)
                    # print(symbol,' = ',similarity)
                    if similarity > highest_similarity:
                        # print('new similarity found:',symbol,' at ',similarity)
                        highest_similarity = similarity
                        most_similar_stock = symbol
                        most_similar_index = i
                bar.next()
    
    # Extract the most similar period's data
    if len(other_rolling_periods[most_similar_stock][most_similar_index:])<COMPARE_PERIOD:
        print('no similarity found, program abort')
        sys.exit(-1)
        
    most_similar_period = other_rolling_periods[most_similar_stock][most_similar_index]
    most_similar_period_index = other_rolling_periods[most_similar_stock][most_similar_index]#+COMPARE_PERIOD:most_similar_index+COMPARE_PERIOD+PREDICT_PERIOD]
    
    future_price_starting_index=all_stock_data.index.get_loc(most_similar_period_index.index[-1])
    future_price_ending_index = future_price_starting_index + PREDICT_PERIOD
    most_similar_future_price=all_stock_data[COL][most_similar_stock][future_price_starting_index:future_price_ending_index]
    if (len(most_similar_future_price)<PREDICT_PERIOD): # not enough future data for mimicking 
        print('not enough future data in similar stock for mimick, continue?')
        future_data_too_short=True
    else:
        future_data_too_short=False
        
    # Plot recent stock prices and future prediction
    target_stock_recent_dates = target_stock_data.index[-COMPARE_PERIOD:]
    future_dates = pd.date_range(start=target_stock_recent_dates[-1], periods=PREDICT_PERIOD, freq='D')

    
    '''
    # adjust future stock price based on ratio between similar stock
    '''
    percentage_changes = most_similar_future_price.pct_change().fillna(0)
    # Adjust Apple's future prediction based on these percentage changes
    last_price = target_stock_data.iloc[-1]
    target_stock_future_pattern = last_price * (1 + percentage_changes).cumprod().values
 
    # Append the recent data with the future prediction to ensure continuity
    target_stock_recent_and_future = np.concatenate((target_stock_recent_data.values, target_stock_future_pattern))
    
    
    # =============================================================================
    #
    #     Let's plot the result !
    #
    # =============================================================================

    fig, ax = plt.subplots( 4, 1, figsize=(14, 18), dpi=200)
    plt.suptitle(f'{target_symbol} pattern matching on {COL} price \nin the {COMPARE_PERIOD} days ends {end_date} with {PREDICT_PERIOD} days prediction.\n{title_subtitle}',fontsize=16,y=1)
    plt.title(f'chart generated on {currentime}',fontsize=10)

    # =============================================================================
    #     subplot [0]
    # =============================================================================
    
    # Plot the original stock price from COMPARE PERIOD starts till Latest downloaded data (today)
    ax[0].plot(full_target_stock_data.loc[target_stock_recent_dates[0]:].index,
               full_target_stock_data[target_stock_recent_dates[0]:].values, 
               label=f'{target_symbol} Stock Price ', color='green',linewidth=2,linestyle='-',alpha=0.8)
    
    # Highlight the stock we used for comparison
    ax[0].plot(target_stock_data.index[-COMPARE_PERIOD:], target_stock_data.iloc[-COMPARE_PERIOD:], label=f'{target_symbol} Stock Price (Search pattern used: Last {COMPARE_PERIOD} Days)', linestyle='-',color='red', linewidth=1,alpha=1)

    # Plot the future of PREDICT PERIOD from last date of COMPARE PERIOD
    # use len of future stock as to avoid data shortage in future dates and ensure dimension in line x & y
    # as data is short, so we use [:len()] to plot the first part of available data. 
    ax[0].plot(future_dates[:len(target_stock_future_pattern)], target_stock_future_pattern, label=f'Predicted {target_symbol} Stock Price ({PREDICT_PERIOD} Days)', color='red', linewidth=1,linestyle='--', alpha=1)
    ax[0].axvline(future_dates[0],color='red')
    ax[0].text(future_dates[0],0.1,'Prediction: '+future_dates[0].strftime("%Y-%m-%d"),transform=ax[0].get_xaxis_transform(), fontsize=8,rotation=90)
    
    # add symbol as watermark
    ax[0].text(0.5, 0.5, target_symbol, 
        transform=ax[0].transAxes,
        fontsize=50, color='gray', alpha=0.4,
        ha='center', va='center', rotation=0)
    ax[0].set_title(f'{target_symbol} Stock Price (sector: {target_symbol_sector})')
    ax[0].set_ylabel('Price')
    ax[0].legend(loc='upper left')
    ax[0].grid(True)
    ax[0].tick_params(axis='x', rotation=0)
  
    # =============================================================================
    #     subplot [1] - Similar Stock chart with period of similarity and its future
    # =============================================================================

    ax1=ax[1].twiny()
    
    # Highlight the Similar Period found on historical price chart
    ax[1].axvspan(most_similar_period.index[0], most_similar_period.index[-1], color='yellow', alpha=0.5, label='Most Similar Period')
    # Highlight the part we will be using for PREDICT PERIOD
    ax[1].axvspan(most_similar_future_price.index[0], most_similar_future_price.index[-1], color='gray', alpha=0.5, label='Use for Prediction')

    # Plot the selected stock's prices and highlight the most similar period
    ax[1].plot(all_stock_data[COL][most_similar_stock].index, all_stock_data[COL][most_similar_stock], label=f'{most_similar_stock} Stock Price', color='blue')
    ax1.plot(full_target_stock_data.index,
              full_target_stock_data.values, 
              label=f'{target_symbol} Stock Price ', color='red',linewidth=2,linestyle='-',alpha=1)
   
   
    # add symbol as watermark
    ax[1].text(0.5, 0.5, most_similar_stock , 
        transform=ax[1].transAxes,
        fontsize=50, color='gray', alpha=0.4,
        ha='center', va='center', rotation=0)

    ax[1].set_title(f'{most_similar_stock} Stock Price with Highlighted Most Similar Period')
    ax[1].set_ylabel('Price') 
    ax[1].legend()
    ax1.legend(loc='lower left')
    ax[1].grid(True)
    ax[1].tick_params(axis='x', rotation=0)
 
    # =============================================================================
    #     subplot [2] - zoom into the similar period and compare with target stock
    # =============================================================================

    # Plot the zoomed-in comparison of the similar period and Apple's recent data
    zoomed_end_date = most_similar_period.index[0] + pd.Timedelta(days=COMPARE_PERIOD-1)  # Adjusted to match the length of future_dates
    zoomed_dates = pd.date_range(start=most_similar_period.index[0], end=zoomed_end_date, freq='D')
 
    # Highlight the part we used to compare the targetstock
    ax[1].axvspan(target_stock_data.index[-COMPARE_PERIOD],target_stock_data.index[-1], color='red', alpha=0.5, label='Comparions period')
   
    ax2 = ax[2].twinx().twiny() # overlay target stock

    # Plot out both similar stock and target stock for visulization
    ax[2].plot(zoomed_dates[-COMPARE_PERIOD:], most_similar_period.tail(COMPARE_PERIOD), label=f'{most_similar_stock} Similar Period', color='gold')
    ax2.plot(target_stock_data.index[-COMPARE_PERIOD:], target_stock_data.tail(COMPARE_PERIOD), label=f'{target_symbol} Stock Price (Last 3 Months)', color='red')

    ax[2].set_xlabel('',color='blue')
    ax[2].set_ylabel(f'{most_similar_stock} Price', color='blue')
    ax[2].tick_params(axis='both', labelcolor='blue')
    ax[2].set_title(f'Zoomed-in Comparison of {target_symbol} and similar {most_similar_stock} stock ')
    ax[2].legend(loc='lower left')
    ax[2].grid(True)

    # color the border and x,y ticker for easy reading 
    ax2.set_xlabel('',color='red')
    ax2.set_ylabel(f'{target_symbol} Price', color='red')
    ax2.tick_params(axis='both', colors='red')
    ax2.legend(loc='upper left')
    ax2.spines['left'].set_color('blue')  
    ax2.spines['bottom'].set_color('blue')  
    ax2.spines['right'].set_color('red')  
    ax2.spines['top'].set_color('red')  
    ax2.grid(True,linestyle = "--")
    
    # =============================================================================
    #     subplot [3] - Future stock performance based on Similar stock's future projection
    # =============================================================================

    ax3 = ax[3].twinx().twiny()

    # Plot out both similar stock and target stock 's future days for visulization of PREDICT PERIOD
    ax[3].plot(most_similar_future_price.index[-len(most_similar_future_price):], most_similar_future_price, label=f'{most_similar_stock} Following price in same span', linestyle='-', color='blue',alpha=0.5)
    ax3.plot(future_dates[-len(target_stock_future_pattern):], target_stock_future_pattern, label=f'{target_symbol} Predicted price from {most_similar_stock} ', linestyle='--', color='red', alpha=1)

    ax[3].set_xlabel('',color='blue')
    ax[3].set_ylabel(f'{most_similar_stock} Price', color='blue')
    ax[3].tick_params(axis='both', labelcolor='blue')
    ax[3].set_title(f'Predicted Future {PREDICT_PERIOD} days pattern based on {most_similar_stock} stock')
    ax[3].legend(loc='lower left')
    ax[3].grid(True)
    
    # color the border and x,y ticker for easy reading 
    ax3.set_xlabel('',color='red')
    ax3.set_ylabel(f'{target_symbol} Price', color='red')
    ax3.tick_params(axis='both', colors='red')
    ax3.spines['left'].set_color('blue')  
    ax3.spines['bottom'].set_color('blue')  
    ax3.spines['right'].set_color('red')  
    ax3.spines['top'].set_color('red')      

    ax3.legend(loc='upper left')
    ax3.grid(True,linestyle = "--")

    # =============================================================================
    #     save the plot for record. Change filename path as in your system
    # =============================================================================
    
    fig.tight_layout(pad=5.0)
    plt.show()
    path='/Users/michaelwai/Downloads/'
    filename=path+f'{target_symbol}_{end_date}_{COMPARE_PERIOD}-{PREDICT_PERIOD} on {COL} price_{currentime}.jpg'
    fig.savefig(filename,bbox_inches='tight')
 
    # Here is the result in text
    
    print(f"Most similar period of {most_similar_stock} stock to {target_symbol} stock:")
    print ('most_similar_stock\n',most_similar_stock, 
           '\nwith Highest Similarity value: {0:10.2f}'.format(highest_similarity*100),'%\n' 
           )
    print("Similar Period Start Date:", most_similar_period.index[0])
    print("Similar Period End Date:", most_similar_period.index[-1])
    
    # Predicted values at a few horizons (actual price)
    horizons = [7, 30, 90, 180, 360]
    print("\nPredicted ACTUAL prices (from last known target price):")
    for h in horizons:
        if len(target_stock_future_pattern) >= h:
            pred_price = target_stock_future_pattern[h - 1]
            pred_date = future_dates[min(h - 1, len(future_dates) - 1)]
            print(f"  +{h:>3} days  ({pred_date.strftime('%Y-%m-%d')}): {pred_price:,.2f}")
        else:
            print(f"  +{h:>3} days: not enough future data (only {len(target_stock_future_pattern)} points)")