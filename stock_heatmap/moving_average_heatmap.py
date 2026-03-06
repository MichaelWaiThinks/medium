#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 23 23:17:34 2024

@author: michaelwai
"""
import requests
import yfinance as yf
from yahooquery import Ticker
import pandas as pd
import os
import numpy as np
from datetime import datetime, timedelta

from matplotlib import colors
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.animation as animation
import matplotlib.colors as mc

from warnings import simplefilter
simplefilter(action="ignore", category=pd.errors.PerformanceWarning)

STOCK_DATA_FILE='./stock_data_file.csv'
NO_LEGEND_JUST_PLOT=True
SHORTMA=50
LONGMA=200
stock_data=[]
startdate='2020-03-01'
today='2020-04-05'
PLOTNUMDAYS = 10
# today= (datetime.now()+timedelta(days=1)).strftime("%Y-%m-%d")
# today= (datetime.now()-timedelta(days=1)).strftime("%Y-%m-%d")
fig, axes = plt.subplots(dpi=100, nrows=3, figsize=(8, 12) , sharex=False)

# color_list=list(mc.CSS4_COLORS.keys())
color_list = plt.cm.tab10.colors[:len(plt.cm.tab10.colors)] #//2]

global scats

tickers = ['SMXT',
            'DJT',
            'ALAB',
            'CGON',
            'MAMO',
            'MNDR']

title='Mag7'
tickers=['AAPL','GOOG','AMZN','NVDA',
         'META','TSLA','MSFT']
# '^BSESN',

# title='WorldIndex'
# tickers = ['^GSPC', '^DJI', '^IXIC', '^N225', '^HSI', '000001.SS', '^TWII', '^FTSE']


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

    
def get_tickers_price(symbols,_start_date='2000-01-01',_end_date='2024-12-29'):

    if os.path.isfile(STOCK_DATA_FILE):
        try:
            print('reading from data file...')
            df=pd.read_csv(STOCK_DATA_FILE,header=[0,1])#if want to skip multicolumn header-> index_col=1,  header=None,skiprows=1
            df.reset_index(drop=True, inplace=True)
            print (df.index, df.columns)
            df=df[['Date','Close']]
            df=df.droplevel(0, axis=1)  #remove first level
            df=df.rename(columns={ df.columns[0]: "Date" }).set_index('Date')  # df=df.reset_index()
            df.index=pd.to_datetime(df.index).strftime('%Y-%m-%d')
    
    
            # for debug use
            # print (symbols, '==', df.columns)
            print (set(symbols).issubset(df.columns))
            print (min(df.index) ,'<=', _start_date)
            print (min(df.index) <= _start_date)
            print (max(df.index) ,'>=', _end_date)
            print (max(df.index) >= _end_date)
            
# =============================================================================
#             if set(symbols).issubset(df.columns) and\
#                    min(df.index) <= _start_date and \
#                     max(df.index) >= _end_date:                
# =============================================================================
            
            # return df.loc[(df.index>=_start_date) & (df.index<=_end_date)]
            return df.loc[ (df.index<=_end_date)]
            
           

        except Exception as e:
            print ('Error reading data file, will download from Yahoo instead...', str(e))
    
    else:
        print ('getting symbols:\n',symbols)
    
    # if file not exists or data not in range, lets redownload
    ticker = Ticker(symbols)
    # df = ticker.history(start=_start_date,end=_end_date).reset_index() #tickers.history(start=start,end=end)
    # df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y/%m/%d')
    # print (df)
    print ('getting stock data from yahoo!')
    df = (yf.download(symbols,start=_start_date,end=_end_date)).reset_index() #download all symbols at once
    df.to_csv(STOCK_DATA_FILE,index=False)

    df = df[['Date','Close']]
    df=df.droplevel(0, axis=1)  #remove first level
    df=df.rename(columns={ df.columns[0]: "Date" }).set_index('Date')  # df=df.reset_index()
    df.index=pd.to_datetime(df.index).strftime('%Y-%m-%d')
    
    return df



def work_out_stock_MA_ratio(tickers,df):
                
    df=df.ffill()
    
    # df=remove_outliner(df, tickers)
    
    for ticker in tickers:
        if ticker in df.columns:
            df_t = df[ticker]
    
            df[ticker+'shortMA'] = df_t.rolling(window=SHORTMA).mean()
            df[ticker+'longMA'] = df_t.rolling(window=LONGMA).mean()
            
            df[ticker+'shortMAratio'] = ( (df_t-df[ticker+'shortMA'])/df[ticker+'shortMA'] )*100
            df[ticker+'longMAratio'] = ( (df_t-df[ticker+'longMA'])/df[ticker+'longMA'] ) *100
            
            # Applying the normalization function to column Ticker
            df[ticker+'NORM'] = df_t.apply(lambda x: ((x/df_t.iloc[0])-1)*100)
    
        
    return df

  
def update_plot(i):   
    global stock_data
    
    i=(PLOTNUMDAYS-i+1)*-1
    print (datetime.now(),' plotting day ',i,' of ',PLOTNUMDAYS)

    axes[0].clear()
    axes[1].clear()
    axes[2].clear()
    
    axes[0].set_title('Moving Average quartrand')
    axes[0].set_xlabel('Price over '+str(SHORTMA)+'-day MA %')
    axes[0].set_ylabel('Price over '+str(LONGMA)+'-day MA %')
    axes[0].axhline(0,color='black',linewidth=1)
    axes[0].axvline(0,color='black',linewidth=1)
    
    axes[1].set_title('')
    axes[1].set_xlabel('')
    axes[1].set_ylabel('Price')

    axes[2].set_title('Stock chart (above) and P/L (below)')
    axes[2].set_xlabel('Date')
    axes[2].set_ylabel('%')


    minX=0
    minY=0
    maxX=0
    maxY=0
    
    # df=stock_data.fillna(0)
    df=stock_data.fillna(0)
    print ('plotting:',i)
    fig.suptitle(title+' [ ' + startdate + '-' + today + ' ] over Moving Averages ratio on ' + str(stock_data.index[i]))

    for ticker in tickers:
        if ticker in df.columns:
            if (min(df[ticker+'shortMAratio'])<minX):
                minX=min(df[ticker+'shortMAratio'])
                         
            if (max(df[ticker+'shortMAratio'])>maxX):
                maxX=max(df[ticker+'shortMAratio'])
                         
            if (min(df[ticker+'longMAratio'])<minY):
                minY=min(df[ticker+'longMAratio'])
                         
            if (max(df[ticker+'longMAratio'])>maxY):
                maxY=max(df[ticker+'longMAratio'])
                

    # print (minX,maxX,minY,maxY)
    axes[0].set_xlim(minX,maxX)
    axes[0].set_ylim(minY,maxY)
    # axes[0].set_xlim(-100,200)
    # axes[0].set_ylim(-100,200)
    
    # stock_data.to_csv('stock_data.csv')

    for t,ticker in enumerate(tickers):
        if ticker in stock_data.columns:
            print ('plotting ', ticker)
            color = color_list[t%len(color_list)]
            
            axes[1].plot(stock_data.index, stock_data[ticker],color=color, label=ticker)
            axes[1].axvline(stock_data.index[i],color='red',linewidth=1,alpha=0.5)
      
            axes[2].plot(stock_data.index,df[ticker+'NORM'], color=color,label=ticker)
            axes[2].axvline(stock_data.index[i],color='red',linewidth=1,alpha=0.5)
    
    
            # plot last 5 trailing and not Nan
            scats=axes[0].scatter(stock_data[ticker+'shortMAratio'].iloc[i],stock_data[ticker+'longMAratio'].iloc[i], alpha=0.9, color=color, label=ticker)
    
            if stock_data[ticker+'shortMAratio'].iloc[i]*stock_data[ticker+'longMAratio'].iloc[i-1] == stock_data[ticker+'shortMAratio'].iloc[i]*stock_data[ticker+'longMAratio'].iloc[i-1]:
    # =============================================================================
    #             if i>9:
    #                 scats=axes[0].scatter(stock_data[ticker+'shortMAratio'].iloc[i],stock_data[ticker+'longMAratio'].iloc[i-8], alpha=0.1, color=color, label='_HIDDEN')
    #                 scats=axes[0].scatter(stock_data[ticker+'shortMAratio'].iloc[i],stock_data[ticker+'longMAratio'].iloc[i-7], alpha=0.2, color=color, label='_HIDDEN')
    #                 scats=axes[0].scatter(stock_data[ticker+'shortMAratio'].iloc[i],stock_data[ticker+'longMAratio'].iloc[i-6], alpha=0.3, color=color, label='_HIDDEN')
    #                 scats=axes[0].scatter(stock_data[ticker+'shortMAratio'].iloc[i],stock_data[ticker+'longMAratio'].iloc[i-5], alpha=0.35, color=color, label='_HIDDEN')
    #                 scats=axes[0].scatter(stock_data[ticker+'shortMAratio'].iloc[i],stock_data[ticker+'longMAratio'].iloc[i-4], alpha=0.4, color=color, label='_HIDDEN')
    #                 scats=axes[0].scatter(stock_data[ticker+'shortMAratio'].iloc[i],stock_data[ticker+'longMAratio'].iloc[i-3], alpha=0.45, color=color, label='_HIDDEN')
    #                 scats=axes[0].scatter(stock_data[ticker+'shortMAratio'].iloc[i],stock_data[ticker+'longMAratio'].iloc[i-2], alpha=0.5, color=color, label='_HIDDEN')
    #                 scats=axes[0].scatter(stock_data[ticker+'shortMAratio'].iloc[i],stock_data[ticker+'longMAratio'].iloc[i-1], alpha=0.55, color=color, label='_HIDDEN')
    #             
    # =============================================================================
                if not NO_LEGEND_JUST_PLOT:
                    axes[0].text(stock_data[ticker+'shortMAratio'].iloc[i],stock_data[ticker+'longMAratio'].iloc[i],ticker,color=color)
                # axes[0].autoscale(True)

    # axes[1].xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    # axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%m-%Y"))
    axes[1].set_xticks([])
    axes[2].xaxis.set_major_locator(plt.MaxNLocator(10))
    # axes[2].xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    # axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    axes[2].xaxis.set_tick_params(labelsize=10, rotation=90)

    axes[0].grid(True)
    axes[1].grid(True)
    # axes[2].grid(False)
    axes[2].grid(axis='y', which='both')

    if not NO_LEGEND_JUST_PLOT:
        # axes[0].legend(loc='center left', bbox_to_anchor=(1, 0.5))
        axes[1].legend(loc='center left', bbox_to_anchor=(1, 0.5))
        # axes[2].legend(loc='center left', bbox_to_anchor=(1, 0.5))

    
    # vmax = np.abs(np.concatenate([x1,x2,y1,y2])).max() + 5
    # axes[1].set_yscale("log")#, nonposy ='clip') 
    vmax = max(maxX-minX,maxY-minY)
    extent = [vmax*-1,vmax, vmax*-1,vmax]
    # extent = [-100,100,-100,100]
    # print (extent)
    arr = np.array([[0,100],[100,0]])
    # axes[0].autoscale(True)
    axes[0].imshow(arr, extent=extent, cmap=plt.cm.Greys, interpolation='none', alpha=.1)
    # axes[0].imshow(arr,  cmap=plt.cm.Greys, interpolation='none', alpha=.1)

    plt.tight_layout()
        
    return scats,


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

# =============================================================================
# 
# from moviepy.editor import *
# import os
# os.environ["IMAGEIO_FFMPEG_EXE"] = "/opt/homebrew/bin/ffmpeg"
# 
# def gif_to_mp4(gif_path, mp4_path):
#     gif_clip = VideoFileClip(gif_path)
#     gif_clip.write_videofile(mp4_path)
# 
# gif_path = './'+title+'_(MA='+str(SHORTMA)+'_'+str(LONGMA)+')_'+startdate+'_'+today+'.gif'
# mp4_path = './'+title+'_(MA='+str(SHORTMA)+'_'+str(LONGMA)+')_'+startdate+'_'+today+'.mp4'
# 
# gif_to_mp4(gif_path, mp4_path)
# xxx
# =============================================================================

tickers_and_name=get_nasdaq_holdings(2024)
tickers=list(tickers_and_name.keys())

stock_data=get_tickers_price(tickers,startdate,today)
# numpoints = len(tickers) # number of symbols
# numframes = len(stock_data) # number of dates

# plot_stock_mov_avg(tickers,df)
stock_data=work_out_stock_MA_ratio(tickers,stock_data)
# stock_data.to_csv('stock_data.csv')
# update_plot(-1)

fig.savefig('/Users/michaelwai/Downloads/python-image'+today+'_('+str(len(tickers))+'stocks).jpg')


ani = animation.FuncAnimation(fig, update_plot ,frames=range(PLOTNUMDAYS))
#fargs=(color_data, scats))
# =============================================================================
# 
# try:
#     # brew install ffmpeg
#     FFwriter = animation.FFMpegWriter(fps=10)
#     ani.save('./'+title+'_(MA='+str(SHORTMA)+'_'+str(LONGMA)+')_'+startdate+'_'+today+'.mp4', writer=FFwriter)
# except Exception as e:
#     print (str(e))
# =============================================================================

ani.save('./'+title+'_(MA='+str(SHORTMA)+'_'+str(LONGMA)+')_'+startdate+'_'+today+'.gif', writer='imagemagick', fps=3)
