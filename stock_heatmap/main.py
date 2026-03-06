#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May 10 13:18:52 2024

@author: michaelwai
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May  3 16:56:25 2024

@author: michaelwai
"""

from yahooquery import Ticker
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib
import matplotlib.colors as colors
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.animation as animation
from matplotlib.animation import FuncAnimation, PillowWriter 

import re
import math
from datetime import datetime,timedelta
import requests
from collections import Counter
import numpy as np
from numpy import inf
from progress.bar import Bar
import matplotlib.ticker as mtick
import os
import traceback
import stats
# import mplcursors
# from mplcursors import cursor  # separate package must be installed
# matplotlib.use('TkAgg')

# %matplotlib qt

# PLOTDAYS = 1
title='By Sector MA Plot'
STOCK_DATA_FILE='./data/stock_data.csv'
STOCK_SECTOR_FILE='./data/stock_sector_list.csv'
STARTDATE='2000-12-05'
ENDDATE=(datetime.now()-timedelta(days=1)).strftime("%Y-%m-%d")
ENDDATE=(datetime.now()).strftime("%Y-%m-%d")
# ENDDATE='2020-04-20'

technology_stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'FB']
communication_services_stocks = ['T', 'VZ', 'DIS', 'NFLX', 'CMCSA']
consumer_cyclical_stocks = ['TSLA', 'GM', 'F', 'NIO', 'FORD']
healthcare_stocks = ['JNJ', 'PFE', 'UNH', 'MRK', 'AMGN']
financial_services_stocks = ['JPM', 'BAC', 'WFC', 'C', 'GS']
consumer_defensive_stocks = ['PG', 'KO', 'PEP', 'COST', 'WMT']
industrials_stocks = ['BA', 'HON', 'MMM', 'UNP', 'UPS']
basic_materials_stocks = ['LIN', 'APD', 'ECL', 'NEM', 'DD']
real_estate_stocks = ['AMT', 'EQIX', 'PLD', 'SPG', 'CBRE']
utilities_stocks = ['NEE', 'DUK', 'SO', 'EXC', 'D']
energy_stocks = ['XOM', 'CVX', 'COP', 'SLB', 'PSX']

targetsymbols=[technology_stocks,
               communication_services_stocks,
               consumer_cyclical_stocks,
               healthcare_stocks,
               financial_services_stocks,
               consumer_defensive_stocks,
               industrials_stocks,
               basic_materials_stocks,
               real_estate_stocks,
               utilities_stocks,
               energy_stocks,
               ]
targetsymbols=[item for row in targetsymbols for item in row]


# =============================================================================
# # or you can simply provide a list
# targetsymbols=['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'FB', 'T', 'VZ', 'DIS', 'NFLX', 'CMCSA', 
#               'TSLA', 'GM', 'F', 'NIO', 'FORD', 'JNJ', 'PFE', 'UNH', 'MRK', 'AMGN', 
#               'JPM', 'BAC', 'WFC', 'C', 'GS', 'PG', 'KO', 'PEP', 'COST', 'WMT', 
#               'BA', 'HON', 'MMM', 'UNP', 'UPS', 'LIN', 'APD', 'ECL', 'NEM', 'DD', 
#               'AMT', 'EQIX', 'PLD', 'SPG', 'CBRE', 'NEE', 'DUK', 'SO', 'EXC', 'D', 
#               'XOM', 'CVX', 'COP', 'SLB', 'PSX']
# =============================================================================


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
        # print(df.head())
        df=df.set_index('Date')
        ENDDATE_minus_1=(pd.to_datetime(df.index[-1])-timedelta(days=1)).strftime("%Y-%m-%d")
        STARTDATE_minus_1=(pd.to_datetime(min(df.index))-timedelta(days=1)).strftime("%Y-%m-%d")

        df.index=pd.to_datetime(df.index).strftime('%Y-%m-%d')
        
        
        print ('set(symbols).issubset(df.columns)=',set(symbols).issubset(df.columns))
        print ('min(df.index) <= _start_date',STARTDATE_minus_1 <= _start_date, min(df.index), STARTDATE_minus_1, _start_date)
        print ('max(df.index) >= _end_date',ENDDATE >= _end_date, max(df.index),ENDDATE, _end_date)
        if set(symbols).issubset(df.columns) and\
               STARTDATE_minus_1 <= _start_date and \
                ENDDATE >= _end_date:
            # print (df.loc[(df.index<=_end_date)])
            
            return df.loc[(df.index<=_end_date)]

        else: #download missing dates till today (end=tomorrow to guarantee today will be downloaded)
            print ('download missing days ',df.index[-1],tomorrow)
            missingdata_df = yf.download(symbols,start=ENDDATE_minus_1, end=tomorrow, threads=False).reset_index() #download all symbols at once
            missingdata_df = missingdata_df[['Date','Close']]
            missingdata_df=missingdata_df.droplevel(0, axis=1)  #remove first level
            missingdata_df=missingdata_df.rename(columns={missingdata_df.columns[0]: "Date" }).set_index('Date') 
            missingdata_df.index=pd.to_datetime(missingdata_df.index).strftime('%Y-%m-%d')
            df = pd.concat([df,missingdata_df]).drop_duplicates()
            df.to_csv(STOCK_DATA_FILE)
            return df.loc[(df.index<=_end_date)]


    input('Do you really redownload everything?')
    if len(symbols)>4096:
        df = yf.download(symbols,period='max', threads=False).reset_index() #download all symbols at once
    else:
        df = yf.download(symbols,period='max', threads=False).reset_index() #download all symbols at once

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
        # sector_df=sector_df.set_index('Symbol')
        
    else:
        nasdaq_symbols_sectors=get_yearly_holdings_sectors('nasdaq',2024)
        nyse_symbols_sectors=get_yearly_holdings_sectors('NYSE',2024)
        print ('%s stocks retrieved for nasdaq ' % len(nasdaq_symbols_sectors))
        print ('%s stocks retrieved for NYSE ' % len(nyse_symbols_sectors))
        
        #not best practise to merge 2 dicts and wont work if key is not string, but i am lazy anyway
        sector_df = dict(nasdaq_symbols_sectors, **nyse_symbols_sectors)         
        sector_df = pd.DataFrame(sector_df.items(),columns=['Symbol','Sector'])
        sector_df['Sector'] = sector_df['Sector'].replace(['',np.nan],'Undefined')
        # sector_df=sector_df.set_index('Symbol')
        sector_df.to_csv(STOCK_SECTOR_FILE,index=False)
        
    return sector_df

# get stock symbols of exchange
# EXAMPLE =====================================================================
# {"symbol":"SLB",
# "name":"Schlumberger N.V. Common Stock",
# "lastsale":"$48.48",
# "netchange":"0.62",
# "pctchange":"1.295%",
# "volume":"6366963",
# "marketCap":"69294292860.00",
# "country":"France",
# "ipoyear":"",
# "industry":"Oilfield Services/Equipment",
# "sector":"Energy",
# "url":"/market-activity/stocks/slb"}
# =============================================================================

def get_yearly_holdings_sectors(exchange='nasdaq',year=2024):
    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36',
    }
    # Function to get QQQ holdings for a given year
    url = f"https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=100&offset=0&download=true&exchange={exchange}&date={year}-01-01"
    response = requests.get(url,headers=headers)
    data = response.json()
    holdings = data['data']['rows']
    # return holdings
    return {stock['symbol']: stock['sector'] for stock in holdings}


def plot_chart(piror_to,date,axes):
    
    MA_crossing=pd.DataFrame(columns=['Symbol','Sector', 'Price','MA'+str(SHORTMA), 'MA'+str(LONGMA)])
    
    if date < historical_prices.index[0] or date > historical_prices.index[-1]:
        print ('*** ERROR!!! target date is not in data range! Program abort please download stock data. Last date in datafile is ',historical_prices.index[-1] )
        print (historical_prices.tail(),'\nyour target date is :',date)
        input ('program aborting. Get ready to be ejected ?')
        sys.exit(-1)
    
    # the row of the date as our target study date,
    print(historical_prices.index, date,len(historical_prices) )
    print(historical_prices.index[historical_prices.index >= date][0])
    target_index = historical_prices.index.get_loc(historical_prices.index[historical_prices.index >= date][0])-len(historical_prices)

    # animate from -1,-2,-3 up to -10  in index
    # target_index = target_index-piror_to
    
    # animate from -10, -9, -8,  up to -1 in index
    target_index = target_index+piror_to-PLOTDAYS+1
    date = historical_prices.index[target_index] #in case the date falls under no trade date, reassign next date

    # clean up chart for next plot to be animated
    for i in range(num_sectors):
        axes[int(i%num_rows),int(i/num_rows)].clear()

    print ('***** Plotting chart : ', date, '(%s/%s) *****\n' %(piror_to,PLOTDAYS))
    for i, (sector, group) in enumerate(stock_sector.groupby('Sector')):
        if sector == 'Undefined': #skipping undefined sector
            continue
        # work on prices in this sector - common_symbols denotes symbols in the stock_sector group and value exists in historical prices df
        common_symbols = list(set(historical_prices.columns)&set(group['Symbol'].tolist()))
        prices = historical_prices[common_symbols]

        shortMA = round(prices.rolling(window=SHORTMA).mean(),2)
        shortMAratio = round((prices-shortMA)/shortMA*100,2).replace([np.nan,-np.nan,inf,-inf],np.nan)
        
        # print(sector,'short=',shortMAratio[shortMAratio=='inf'])

        longMA = round(prices.rolling(window=LONGMA).mean(),2)
        longMAratio = round((prices-longMA)/longMA*100,2).replace([np.nan,-np.nan,inf,-inf],np.nan)
        
        if plotpercentile>0: # positive denote pencentile within 
            plotpercentile_upper = 50+plotpercentile/2
            plotpercentile_lower = 50-plotpercentile/2
            
            # print (sector,' range pct tile = %s-%s' %(plotpercentile_lower,plotpercentile_upper))
            shortMAratio=\
                shortMAratio[
                    (shortMAratio < np.nanpercentile(shortMAratio,plotpercentile_upper)) & \
                    (shortMAratio > np.nanpercentile(shortMAratio,plotpercentile_lower))]
            
            longMAratio = \
                longMAratio[
                    (longMAratio < np.nanpercentile(longMAratio,plotpercentile_upper)) & \
                    (longMAratio > np.nanpercentile(longMAratio,plotpercentile_lower))]
 
        else: #negative denote pencentile outside
            # print (sector,' range pct tile above %s and below %s' %(plotpercentile_upper,plotpercentile_lower))

            plotpercentile_upper = 100+plotpercentile/2
            plotpercentile_lower = 0-plotpercentile/2
            
            shortMAratio=\
                shortMAratio[
                    (shortMAratio > np.nanpercentile(shortMAratio,plotpercentile_upper)) | \
                    (shortMAratio < np.nanpercentile(shortMAratio,plotpercentile_lower))]
            # as x,y must be same size so we now focus only on those filtered x elements (shortMA remains)
            longMAratio = \
                longMAratio[
                    (longMAratio > np.nanpercentile(longMAratio,plotpercentile_upper)) | \
                    (longMAratio < np.nanpercentile(longMAratio,plotpercentile_lower))]


        ax = axes[int(i%num_rows),int(i/num_rows)]

        ax.axhline(0,color='red',linewidth=1,alpha=0.5, zorder=100)
        ax.axvline(0,color='red',linewidth=1,alpha=0.5, zorder=100)
        
        # ax.scatter(shortMA.iloc[target_index],longMA.iloc[target_index], alpha=0.5, color='gray', zorder=50) #cmap=plt.cm.Spectral)

        # let's highlght those we want to visulaize
        with Bar(sector, max=len(common_symbols)) as bar:
            # if sector == 'Health Care':
                # input ('Health Care gogogo')
            for s in common_symbols:
                # print (sector,s)
                # print(target_index, len(shortMAratio), len(longMAratio))
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
                            
                    else: # plot other symbol and give it a label
                        # if not is_outliers(shortMAratio[s].iloc[target_index],longMAratio[s].iloc[target_index],0) : #is it 1% outliers?
                        ax.scatter(shortMAratio[s].iloc[target_index],longMAratio[s].iloc[target_index], alpha=0.3, color='skyblue', zorder=50) #cmap=plt.cm.Spectral)
                        # ax.text(shortMAratio[s].iloc[target_index],longMAratio[s].iloc[target_index],s, fontsize=8, color='grey',zorder=50)

                bar.next()

        MA_crossing.to_csv('MA_crossing_'+targetdate+'.csv')
        ax.set_title(sector + '(' +str(len(shortMAratio.columns))+ ' stocks)' )
        ax.xaxis.set_major_formatter(mtick.PercentFormatter())
        ax.yaxis.set_major_formatter(mtick.PercentFormatter())
        ax.set_xlabel(str(SHORTMA)+' days MA')
        ax.set_ylabel(str(LONGMA)+' days MA')
        # ax.set_xlim(-30,30)
        # ax.set_ylim(-30,30)
                    
    # fig.subplots_adjust( left=None, bottom=None,  right=None, top=None, wspace=None, hspace=None)
    fig.suptitle('Moving Average distribution by sector \n'+ str(historical_prices.index[target_index]), fontsize=18)
    # fig.legend()
    plt.tight_layout()
    plt.show()
    fig.savefig('./img/MAplot_'+str(SHORTMA)+'_'+str(LONGMA)+'_('+str(historical_prices.index[target_index])+')-'+str(plotpercentile)+'pct.jpg')

    
def update_annotation(sel):
    """ update the annotation belonging to the current selected item (sel) """
    # get the label of the graphical element that is selected
    label = sel.artist.get_label()
    # change the text of the annotation
    sel.annotation.set_text(label)

    # create an mplcursor object that shows an annotation while hovering
    cursor = mplcursors.cursor(hover=True)
    # call the function "update_annotation" each time a new element gets hovered over
    cursor.connect("add", update_annotation)
    
    # def hover(event):
    #     if event.inaxes == ax:
    #         x, y = event.xdata, event.ydata
    #         index = np.argmin(np.abs(stock_prices.index - x))
    #         symbol = sumbols[index]
    #         fig.suptitle(f'Stock Symbol: {symbol}', fontsize=12)
    # fig.canvas.mpl_connect('motion_notify_event', hover)


if __name__=='__main__':
    
    ENDDATE = targetdate = '2024-05-09'
    PLOTDAYS = 1
    SHORTMA = 50
    LONGMA = 200
    plotpercentile = 100


    # test()

    stock_sector = get_stock_sector()
    stock_sector = stock_sector[stock_sector['Sector']!='Undefined']
    # print(stock_sector)
    
    symbols=stock_sector['Symbol'].tolist()
    # print(symbols)
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

     
    # ani = animation.FuncAnimation(fig, plot_chart , fargs=[targetdate, axes], init_func=lambda: None, frames=range(PLOTDAYS))
    # ani.save('./img/'+title+'_(MA='+str(SHORTMA)+'_'+str(LONGMA)+')_'+STARTDATE+'_'+ENDDATE+'_'+str(plotpercentile)+'pct.gif', writer='imagemagick', fps=3)

    # plot_chart(0,'1987-10-19',axes) #Dot-com Bubble Burst (March 10, 2000)
    # plot_chart(0,'2020-03-16',axes)
    # plot_chart(0,'2020-03-12',axes)
    plot_chart(0,'2024-05-09',axes)
     # piror_to,date,axes
     
# ==Misc sector definiton by Nasdaq =====================================================================
#      In the context of the Nasdaq sector classification, "Miscellaneous" refers to a category that includes various market participants or securities that do not fit neatly into other predefined categories. Specifically, the term "Miscellaneous" is used to describe:
# Market Participant Type: The MP Type "N" reflects a miscellaneous market participant type rather than a non-member. This classification is used for entities that do not fall into other specific categories such as Agency Quote, Electronic Communications Network (ECN), Exchange, Market Maker, or Order Entry Firm
# Sector Classification: Securities classified under the "Miscellaneous" sector are those that do not fit into any of the existing sector categories defined by industry classification benchmarks. This can include a wide range of companies and investment vehicles that are too diverse to be grouped under a single, more specific sector
# In summary, the "Miscellaneous" category on Nasdaq encompasses a broad array of market participants and securities that do not conform to other established classifications, providing a catch-all category for diverse and unique entities.
# =============================================================================
