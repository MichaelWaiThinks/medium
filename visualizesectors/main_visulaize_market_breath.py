#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# MIT license Copyright 2024 Michael Wai
"""
Created on Tue May 14 17:38:08 2024
https://medium.com/tech-talk-tank/i-scanned-6000-stocks-and-their-sectors-with-python-animated-subplot-to-monitor-the-market-breadth-b391baba0f7a
@author: michaelwai
"""

from datetime import datetime,timedelta
import os
import pandas as pd
import numpy as np
from numpy import inf

import math
import requests

import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib
import matplotlib.ticker as mtick
from matplotlib.animation import FuncAnimation, PillowWriter 

from progress.bar import Bar


title='By Sector MA Plot'
STOCK_DATA_FILE='./data/stock_data.csv'
STOCK_SECTOR_FILE='./data/stock_sector_list.csv'

STARTDATE='2000-12-05' # to be used to download extra past data in order to calculate MA esepcially for longer term
today=(datetime.now()).strftime("%Y-%m-%d") # if one always want to study today only
PLOTDAYS = 5
ENDDATE=targetdate = '2024-05-14'
SHORTMA = 50
LONGMA = 200
# # or you can simply provide a list
targetsymbols=['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'FB', 'T', 'VZ', 'DIS', 'NFLX', 'CMCSA', 
              'TSLA', 'GM', 'F', 'NIO', 'FORD', 'JNJ', 'PFE', 'UNH', 'MRK', 'AMGN', 
              'JPM', 'BAC', 'WFC', 'C', 'GS', 'PG', 'KO', 'PEP', 'COST', 'WMT', 
              'BA', 'HON', 'MMM', 'UNP', 'UPS', 'LIN', 'APD', 'ECL', 'NEM', 'DD', 
              'AMT', 'EQIX', 'PLD', 'SPG', 'CBRE', 'NEE', 'DUK', 'SO', 'EXC', 'D', 
              'XOM', 'CVX', 'COP', 'SLB', 'PSX']

# init global variables
num_sectors = 0 
num_cols = 0
num_rows = 0

# check if value is true value and not nan
def notnan(x):
    return not pd.isna(x)

#threshold is the % how close they are to be considered crossing going to happen
def isCrossing(x,y,threshold=0.01): #default threshold 1%  
    if notnan(x) and notnan(y):
        return abs(x-y) <= threshold * max(x,y)
    else:
        return False


def get_tickers_price(symbols,_start_date,_end_date):
    import os
    import yfinance as yf


    tomorrow=(datetime.now()+timedelta(days=1)).strftime("%Y-%m-%d")
    if os.path.isfile(STOCK_DATA_FILE):
        print('reading from stock data file...')
        df=pd.read_csv(STOCK_DATA_FILE)#,index_col=0,header=[0,1])#if want to skip multicolumn header-> index_col=1,  header=None,skiprows=1
        df=df.set_index('Date')
        LASTDATE=pd.to_datetime(df.index[-1]).strftime("%Y-%m-%d")
        STARTDATE_minus_1=(pd.to_datetime(min(df.index))-timedelta(days=1)).strftime("%Y-%m-%d")

        df.index=pd.to_datetime(df.index).strftime('%Y-%m-%d')
        
        print ('last date in file ',df.index[-1],' target date is ',ENDDATE)
        
        if set(symbols).issubset(df.columns) and\
               STARTDATE_minus_1 <= _start_date and \
                LASTDATE >= _end_date:            
            return df.loc[(df.index<=_end_date)]

        else: #download missing dates till today (end=tomorrow to guarantee today will be downloaded)
            print ('download missing days ',df.index[-1],tomorrow)
            missingdata_df = yf.download(symbols,start=LASTDATE, end=tomorrow, threads=False).reset_index() #download all symbols at once
            missingdata_df = missingdata_df[['Date','Close']]
            missingdata_df = missingdata_df.droplevel(0, axis=1)  #remove first level
            missingdata_df = missingdata_df.rename(columns={missingdata_df.columns[0]: "Date" }).set_index('Date') 
            missingdata_df.index=pd.to_datetime(missingdata_df.index).strftime('%Y-%m-%d')
            df = pd.concat([df,missingdata_df])
            df = df[~df.index.duplicated(keep='last')]
            df.to_csv(STOCK_DATA_FILE)
            return df.loc[(df.index<=_end_date)]

    if len(symbols)>4096:
        df = yf.download(symbols,period='max', threads=False).reset_index() #download all symbols at once without Thread
    else:
        df = yf.download(symbols,period='max', threads=True).reset_index() #download all symbols at once with Thread

    df = df[['Date','Close']]
    df=df.droplevel(0, axis=1)  #remove first level
    df=df.rename(columns={ df.columns[0]: "Date" }).set_index('Date')  # df=df.reset_index()
    df.index=pd.to_datetime(df.index).strftime('%Y-%m-%d')
    df.to_csv(STOCK_DATA_FILE)

    return df

def get_stock_sector():
    if os.path.isfile(STOCK_SECTOR_FILE):
        print('reading stock sector from file...')
        sector_df=pd.read_csv(STOCK_SECTOR_FILE)#,index_col=0,header=[0,1])#if want to skip multicolumn header-> index_col=1,  header=None,skiprows=1
        sector_df['Sector'] = sector_df['Sector'].replace(['',np.nan],'Undefined')
        sector_df = sector_df.dropna()        
    else:
        nasdaq_symbols_sectors=get_yearly_holdings_sectors('nasdaq',2024)
        nyse_symbols_sectors=get_yearly_holdings_sectors('NYSE',2024)
        print ('%s stocks retrieved for nasdaq ' % len(nasdaq_symbols_sectors))
        print ('%s stocks retrieved for NYSE ' % len(nyse_symbols_sectors))
        
        sector_df = dict(nasdaq_symbols_sectors, **nyse_symbols_sectors)         
        sector_df = pd.DataFrame(sector_df.items(),columns=['Symbol','Sector'])
        sector_df['Sector'] = sector_df['Sector'].replace(['',np.nan],'Undefined')
        sector_df.to_csv(STOCK_SECTOR_FILE,index=False)
        
    return sector_df

def get_yearly_holdings_sectors(exchange='nasdaq',year=2024):
    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36',
    }
    # Function to get holdings for a given year
    url = f"https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=100&offset=0&download=true&exchange={exchange}&date={year}-01-01"
    response = requests.get(url,headers=headers)
    data = response.json()
    holdings = data['data']['rows']
    # return holdings
    return {stock['symbol']: stock['sector'] for stock in holdings}


def plot_chart(piror_to,date,axes):
    
    # to store the MA crossing symboles and data
    MA_crossing=pd.DataFrame(columns=['Symbol','Sector', 'Price','MA'+str(SHORTMA), 'MA'+str(LONGMA)])
    
    if date < historical_prices.index[0] or date > historical_prices.index[-1]:
        print ('*** ERROR!!! target date is not in data range! Program abort please download stock data. Last date in datafile is ',historical_prices.index[-1] )
        print (historical_prices.tail(),'\nyour target date is :',date)
        input ('program aborting. Get ready to be ejected ?')
        sys.exit(-1)
    
    # the row of the date as our target study date,
    target_index = historical_prices.index.get_loc(historical_prices.index[historical_prices.index >= date][0])-len(historical_prices)

    target_index = target_index+piror_to-PLOTDAYS+1
    date = historical_prices.index[target_index] #in case the date falls under no trade date, reassign next date

    # FOR ANIMATE: clean up chart for next plot to be animated
    for i in range(num_sectors):
        axes[int(i%num_rows),int(i/num_rows)].clear()

    print ('***** Plotting chart : ', date, '(%s/%s) *****\n' %(piror_to,PLOTDAYS))
    for i, (sector, group) in enumerate(stock_sector.groupby('Sector')):
        if sector == 'Undefined': #skipping undefined sector
            continue
        
        # work on prices in this sector - common_symbols denotes symbols in the stock_sector group and value exists in historical prices df
        common_symbols = list(set(historical_prices.columns)&set(group['Symbol'].tolist()))
        prices = historical_prices[common_symbols]
        
        
        # calculate short and long term MA and price distance between them        
        shortMA = round(prices.rolling(window=SHORTMA).mean(),2)
        shortMAratio = round((prices-shortMA)/shortMA*100,2).replace([np.nan,-np.nan,inf,-inf],np.nan)
        
        longMA = round(prices.rolling(window=LONGMA).mean(),2)
        longMAratio = round((prices-longMA)/longMA*100,2).replace([np.nan,-np.nan,inf,-inf],np.nan)
 
        def color_majority_quadrant(short,long):
            # define color based on which quadrant majority of stock locates
            short_low = short<0
            short_high = short>0
            long_low = long<0
            long_high = long>0
            quad_Low_Low = (short_low & long_low).sum()
            quad_Low_High = (short_low & long_high).sum()
            quad_High_Low = ((short_high & long_low).sum())
            quad_High_High = (short_high & long_high).sum()

            if max(quad_High_High,quad_High_Low,quad_Low_High,quad_Low_Low) == quad_High_High:
                color = 'palegreen'
            elif max(quad_High_High,quad_High_Low,quad_Low_High,quad_Low_Low) == quad_High_Low:
                color = 'lightcyan'
            elif max(quad_High_High,quad_High_Low,quad_Low_High,quad_Low_Low) == quad_Low_High:
                color = 'seashell'
            elif max(quad_High_High,quad_High_Low,quad_Low_High,quad_Low_Low) == quad_Low_Low:
                color = 'mistyrose'
            else:
                color = 'white'
            
            
            return color
   
        facecolor=color_majority_quadrant(shortMAratio.iloc[target_index],longMAratio.iloc[target_index])

        ax = axes[int(i%num_rows),int(i/num_rows)]
        ax.set_facecolor(facecolor)
        ax.axhline(0,color='red',linewidth=1,alpha=0.5, zorder=100)
        ax.axvline(0,color='red',linewidth=1,alpha=0.5, zorder=100)
        
        # let's highlght those we want to visulaize
        with Bar(sector, max=len(common_symbols)) as bar:

            for s in common_symbols:
                
                if notnan(shortMAratio[s].iloc[target_index]) and \
                    notnan(longMAratio[s].iloc[target_index]): # if there is data otherwise don't waste time plotting
                    
                    # if price is close to both short and long MA by 1% which means they are going to cross and need to monitor
                    if isCrossing(shortMAratio[s].iloc[target_index],longMAratio[s].iloc[target_index], 0.001): #consider crossing if <= 0.1% difference
                        MA_crossing.loc[len(MA_crossing)]=[s,sector,round(historical_prices[s].iloc[target_index],2),shortMA[s].iloc[target_index],longMA[s].iloc[target_index]]
                        ax.scatter(shortMAratio[s].iloc[target_index],longMAratio[s].iloc[target_index], color='green', alpha=0.5, zorder=120)
                        ax.text(shortMAratio[s].iloc[target_index],longMAratio[s].iloc[target_index],s,fontsize=12,color='darkgreen', zorder=130)
                        
                    # if it is our target symbols give it a special color RED
                    elif s in targetsymbols: # plot our target stocks location    
                        if notnan(shortMAratio[s].iloc[target_index]) and notnan(longMAratio[s].iloc[target_index]):
                            ax.scatter(shortMAratio[s].iloc[target_index],longMAratio[s].iloc[target_index], color='red', alpha=0.5, zorder=100)
                            ax.text(shortMAratio[s].iloc[target_index],longMAratio[s].iloc[target_index],s,fontsize=10,color='brown', zorder=110)
                    
                    # plot other symbol and give it a label
                    else: 
                        ax.scatter(shortMAratio[s].iloc[target_index],longMAratio[s].iloc[target_index], alpha=0.3, color='gray', zorder=50) 

                bar.next()

        MA_crossing.to_csv('MA_crossing_'+targetdate+'.csv')
        ax.set_title(sector + '(' +str(len(shortMAratio.columns))+ ' stocks)' )
        ax.xaxis.set_major_formatter(mtick.PercentFormatter())
        ax.yaxis.set_major_formatter(mtick.PercentFormatter())
        ax.set_xlabel(str(SHORTMA)+' days MA')
        ax.set_ylabel(str(LONGMA)+' days MA')

                    
    fig.suptitle('Moving Average distribution by sector \n'+ str(historical_prices.index[target_index]), fontsize=18)
    plt.tight_layout()
    plt.show()
    fig.savefig('./img/MAplot_'+str(SHORTMA)+'_'+str(LONGMA)+'_('+str(historical_prices.index[target_index])+').jpg')


if __name__=='__main__':
    


    stock_sector = get_stock_sector()
    stock_sector = stock_sector[stock_sector['Sector']!='Undefined']
    
    symbols=stock_sector['Symbol'].tolist()
    num_sectors = stock_sector.groupby('Sector').ngroups #11

    print ('number of sector  %s , and stock  : %s' %(num_sectors,len(symbols)))
    
    historical_prices = get_tickers_price(symbols,STARTDATE,ENDDATE)
    
    if 'Date' in historical_prices.columns:
        historical_prices = historical_prices[historical_prices['Date']<=ENDDATE]
    else:
        historical_prices = historical_prices[historical_prices.index<=ENDDATE]
    if 'Date' in historical_prices.columns:
        historical_prices = historical_prices.set_index('Date')
     
    # Let's setup the subplot dimension NxN
    num_rows=math.ceil(math.sqrt(num_sectors))
    num_cols=math.ceil(math.sqrt(num_sectors))
    if num_rows*num_cols-num_sectors >= num_rows: # find the best fit square array of charts
        num_rows -= 1
    
  
    fig, axes = plt.subplots(dpi=300, nrows=num_rows, ncols=num_cols, figsize=(num_cols * 6, num_rows * 4), sharex=False,sharey=False)
     
    plot_chart(0,ENDDATE,axes)
    # ani = FuncAnimation(fig, plot_chart , fargs=[targetdate, axes], init_func=lambda: None, frames=range(PLOTDAYS))
    # ani.save('./img/'+title+'_(MA='+str(SHORTMA)+'_'+str(LONGMA)+')_'+PLOTDAYS+'days from_'+ENDDATE+'_'+'.gif', writer='imagemagick', fps=3)
