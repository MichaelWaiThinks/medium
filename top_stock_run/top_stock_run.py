#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar  7 16:22:11 2024

@author: michaelwai
"""

import pandas as pd
from yahooquery import Ticker
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as md
import matplotlib.ticker as mtick
import numpy as np
import seaborn as sns
import time
import traceback
import requests

sns.set_theme()

import matplotlib.colors as mc
# color_list=list(mc.CSS4_COLORS.keys())
color_list = plt.cm.tab10.colors[:len(plt.cm.tab10.colors)] #//2]

# print (color_list)
# print ('### Color list contains ',len(color_list)),' colors ###'

title='Mag7'
symbols=['AAPL','GOOG','AMZN','NVDA',
         'META','TSLA','MSFT']

pagoda = ["blue", "green", "red", "orchid",'orange', 'darkgrey',
      "darkred", "lightcoral", "brown", "sandybrown", "tan",
      "darkkhaki", "olivedrab", "lightseagreen",
      "steelblue", "dodgerblue", "slategray",
      "blue", "darkorchid", "violet", "deeppink", "hotpink"]

# import distinctipy
# color_list =distinctipy.get_colors(100,pastel_factor=0.3)


def get_tickers_price(symbols,_start_date='2023-01-01',_end_date='2025-12-31'):
    import os
    import yfinance as yf
    
    if os.path.isfile('./nasdaq_data.csv'):
        print('reading from nasdaq data file...')
        df=pd.read_csv('./nasdaq_data.csv',index_col=0,header=[0,1])#if want to skip multicolumn header-> index_col=1,  header=None,skiprows=1
        df.reset_index(drop=True, inplace=True)
        df=df[['Date','Close']]
        df=df.droplevel(0, axis=1)  #remove first level
        df=df.rename(columns={ df.columns[0]: "Date" }).set_index('Date')  # df=df.reset_index()
        df.index=pd.to_datetime(df.index).strftime('%Y-%m-%d')

        if set(symbols).issubset(df.columns) and\
               min(df.index) <= _start_date and \
                max(df.index) >= _end_date:
            
            return df.loc[(df.index>=_start_date) & (df.index<=_end_date)]
    
# =============================================================================
#     print (symbols, '==', df.columns)
#     print (set(symbols).issubset(df.columns))
#     print (min(df.index) ,'<=', _start_date)
#     print (min(df.index) <= _start_date)
#     print (max(df.index) ,'>=', _end_date)
#     print (max(df.index) >= _end_date)
# =============================================================================
    
    
    # df = ticker.history(start=_start_date,end=_end_date).reset_index() #tickers.history(start=start,end=end)
    # df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y/%m/%d')
    # print (df)
    else:
        print ('getting stock data from yahoo!')
        try:
            if _end_date:
                df = (yf.download(symbols,start=_start_date,end=_end_date)).reset_index() #download all symbols at once
            else:
                df = (yf.download(symbols,start=_start_date)).reset_index() #download all symbols at once
        except:
            pass
    
        df.to_csv('nasdaq_data.csv')

       
        df = df[['Date','Adj Close']]
        df=df.droplevel(0, axis=1)  #remove first level
        df=df.rename(columns={ df.columns[0]: "Date" }).set_index('Date')  # df=df.reset_index()
        df.index=pd.to_datetime(df.index).strftime('%Y-%m-%d')
    
    return df


def remove_outliner(df, columns, threshold=3): #sometimes we have data which is outliner from Yahoo we need to clean
    df_cleaned = df.copy()
    # Iterate over each column
    for col in columns:

        if col in df_cleaned.columns:
            print('cleaning ', col)
            # Calculate Z-score for each value in the column
            z_scores = np.abs(
                (df_cleaned[col] - df_cleaned[col].mean()) / df_cleaned[col].std())

            # Find indices of outliers based on Z-score exceeding threshold
            outlier_indices = z_scores > threshold

            # Replace outliers with NaNs
            df_cleaned.loc[outlier_indices , col] = np.nan

            # Drop rows containing NaNs
            df_cleaned = df_cleaned.dropna()

    return df_cleaned

def sortcolumn(df,topcount=5):
    
    lastrow=df.index[-1]
    df=df.T.sort_values(lastrow,ascending=False) # transpose and sort rows
    topnames=df[:topcount].index
    # print(topnames)
    # input('continue...')
    return df.T,topnames # transpose back to column

def assign_color(df):

    cmap = plt.get_cmap('Spectral')
    colors={}
    totalcolors=len(pagoda)

    for i,symbol in enumerate(df.columns):
        color=color_list[i%len(color_list)]
        # color=cmap(i)
        # color=pagoda[i%totalcolors]
        # color = colorsys.hsv_to_rgb(i/1000, 1.0, 1.0)
        colors.update({symbol:color}) # pick from 20 colors
    return colors

def plot_qtr_chart(df):
    i=0
    plt.close()
    fig, axes = plt.subplots(1, 4, figsize=(12, 8), dpi=150, sharey=True)
    plt.yscale('log')

    try:
        ShowHighRunners=False
        highrunners=5

        colors=assign_color(df)
        
        df_yearly = df.apply(lambda x: (x/x.iloc[0]-1)*100)
        df_yearly.replace([np.inf, -np.inf], np.nan, inplace=True)

        df_yearly,topyearlyrunners=sortcolumn(df_yearly,highrunners)
        print ('topyearlyrunners:\n',topyearlyrunners)
        #assign color per symbol

        # {'VRTX': 'black',
        #  'REGN': 'green',
        #  'EXC': 'grey',
        #  'BKR': 'orchid',
        #  'BIIB': 'red',
        #  'PAYX': 'lightcoral',
        #  'SBUX': 'brown'...
        # }

        df.index=pd.to_datetime(df.index)
        # df=df.dropna()
        Q=list(range(0,4))
        Qstart=['']*4
        Qend=['']*4
        Qdf=[pd.DataFrame()]*4

        Qstart[0]=year+'-01-01'
        Qend[0]=year+'-03-31'
        Qstart[1]=year+'-04-01'
        Qend[1]=year+'-06-30'
        Qstart[2]=year+'-07-01'
        Qend[2]=year+'-09-30'
        Qstart[3]=year+'-10-01'
        Qend[3]=year+'-12-31'

        for i in range (4):
            Qdf[i]=(df[(df.index>Qstart[i]) & (df.index<Qend[i])])
            print ('plotting ',Qstart[i],'-',Qend[i])

            Qdf[i] = Qdf[i].apply(lambda x: (x/x.iloc[0]-1)*100)
            Qdf[i].replace([np.inf, -np.inf], np.nan, inplace=True)

            Qdf[i],topquarterlyrunners=sortcolumn(Qdf[i],highrunners)
            print ('topQuarterlyrunners:\n',topquarterlyrunners)

            for s in Qdf[i].columns:
                label=s
                if s not in topquarterlyrunners and s not in topyearlyrunners:
                    # axes[i].plot(Qdf[i][s],alpha=0.1,color=colors[s],label='_Hidden label')
                    axes[i].plot(Qdf[i][s],alpha=0.1,color='silver',label='_Hidden label')
                else:
                    if s in topquarterlyrunners:
                        linestyle='-'
                        label+='*Q'
                        alpha=1
                    if s in topyearlyrunners:
                        linestyle='-'
                        label+='*Y'
                        alpha=1
                    label+='('+str(round(Qdf[i][s].iloc[-1],2))+')'
                    axes[i].plot(Qdf[i][s],alpha=alpha,linestyle=linestyle,color=colors[s],label=label)

            axes[i].legend()

            # Qdf[i]['Max'] = Qdf[i].idxmax(axis=1)
            # Qdf[i].to_csv(year+'Q'+str(i+1)+'.csv')

            # set grid for easy reading
            axes[i].xaxis.grid(color='black', linestyle='--', linewidth=0.2)
            axes[i].yaxis.grid(color='black', linestyle='--', linewidth=0.2)

            #find max symbol per quarter
            axes[i].yaxis.set_major_formatter(mtick.PercentFormatter())
            axes[i].xaxis.set_tick_params(labelsize=6, rotation=90)
            axes[3].yaxis.tick_right()
            axes[i].set_facecolor('whitesmoke')


            # axes[i].legend(labels=df.columns, loc='upper left',
            #       ncol=1, fontsize=6, framealpha=0.7, facecolor='white', frameon=True)

        plt.tight_layout()
        plt.show()
    except Exception as e:
        print ('plotting error with data from:', year, ' Q',i+1, ' with error:',traceback.format_exc())

    return fig,axes


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

def get_stock_sector(symbols):
# =============================================================================
#     from concurrent.futures import ThreadPoolExecutor
# 
#     def get_stats(ticker):
#         info = yf.Tickers(ticker).tickers[ticker].info
#         print(f"{ticker} {info['currentPrice']} {info['marketCap']}")
# 
# 
#     with ThreadPoolExecutor() as executor:
#         executor.map(get_stats, symbols)
# =============================================================================

    """
    all_symbols = " ".join(ticker_list)
    myInfo = Ticker(all_symbols)
    myDict = myInfo.price
    
    for ticker in ticker_list:
        ticker = str(ticker)
        longName = myDict[ticker]['longName']
        market_cap = myDict[ticker]['marketCap']
        price = myDict[ticker]['regularMarketPrice']
        print(ticker, longName, market_cap, price)
    """

    sector_data=[]
    
    print ('Getting Ticker profiles...')
    
    asset_profiles={}
    for symbol in symbols:
        profile = None
        for attempt in range(3):
            try:
                print(f"...getting profile for {symbol} (attempt {attempt+1})")
                profile = Ticker(symbol).asset_profile
                break  # exit retry loop on success
            except Exception as e:
                print(f"⚠️ Attempt {attempt+1} failed for {symbol}: {e}")
                time.sleep(1)
        
        if profile is not None:
            asset_profiles[symbol] = profile
        else:
            print(f"❌ Failed to get profile for {symbol} after 3 attempts")
            asset_profiles[symbol] = None  # or skip/continue based on your logic

    # # if file not exists or data not in range, lets redownload
    # for attempt in range(3):
    #     try:
    #         print(f'...getting profile {symbols}')
    #         asset_profiles = Ticker(symbols).asset_profile
    
    #     except Exception as e:
    #         print(f"⚠️ Attempt {attempt+1} failed for asset_profile {symbols}: {e}")
    #         time.sleep(1)# delay * (2 ** attempt))  # Exponential backoff

    # Loop through each ticker and retrieve its asset profile
    
    for symbol in symbols:
        try:
            print(symbol)
            # Use Ticker to retrieve asset profile information
            # asset_profile = Ticker(symbol).asset_profile
            # Extract the sector information
            sector = asset_profiles[symbol]['sector']
            print (sector)
            # Append sector information to the list
            sector_data.append({'Symbol': symbol, 'Sector': sector})
        except Exception as e:
            print ('skipping ',symbol,':',str(e))
            
    # Create a DataFrame from the sector information
    sector_df = pd.DataFrame(sector_data).dropna()
    sector_df.to_csv('stock_sector_list.csv')

if __name__ == '__main__':


    # read from a specific file for stock lists
    # df=read_data('./qqq_listing.csv')
    # df_pivot=get_tickers_price(df['Symbol'].to_list())
   

    
    # get it from url nasdaq complete 3000+ holdings
    df=get_nasdaq_holdings(2026)

    # print(df.keys())
    
    # get stock sectors....
    # get_stock_sector(list(df.keys()))

    # get_stock_sector(symbols)
    
    
    # get ticker prices
    df_pivot=get_tickers_price(list(df.keys()),_end_date=None)
    
    # df_pivot.index = df_pivot.index.tz_localize('GMT').tz_convert('US/Eastern')
    # df_pivot.index=pd.to_datetime([i.replace(tzinfo=None) for i in t])
    
    for y in range(2023,2026):
        year=str(y)
        print (year+'...')

        df_yearly=df_pivot[(df_pivot.index>(str(year)+'-01-01')) & (df_pivot.index<(str(year)+'-12-31'))]
        # df_yearly.to_csv(year+'_df_yearly.csv')
        # remove_outliner(df_pivot,df_pivot.columns)
        
        normalized_df = df_yearly.apply(lambda x: (x/x.iloc[0]-1)*100)
        normalized_df.replace([np.inf, -np.inf], np.nan, inplace=True)
        
        # msi.dropna(inplace=True)

        normalized_df.to_csv(year+'_normalized_df.csv')
        fig,axes=plot_qtr_chart(df_yearly)
        fig.suptitle('Year '+year, fontsize=16)
        fig.tight_layout()
        fig.savefig(year+'_plot.jpg', dpi=300, bbox_inches='tight')


    matplotlib.pyplot.close()



