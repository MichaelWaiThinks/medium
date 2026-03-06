#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov 17 11:50:02 2023

@author: michaelwai
"""

import pandas as pd
import yfinance as yf
from matplotlib import pyplot as plt
from matplotlib.dates import DateFormatter
from datetime import datetime
import numpy as np
import os

import pandas_datareader as web
import calendar

symbol='GC=F'
baseccy='SI=F'

start_date='1900-11-01'
end_date = datetime.today().strftime('%Y-%m-%d')
fig, (ax1, ax2) = plt.subplots(dpi=600,nrows=2, sharex=True)


def fetch_recession_periods(start_date, end_date):
    """
    Fetches the start and end dates of US recessions within a given date range from the FRED database.

    This function retrieves recession indicators (USREC) from FRED and processes the data to find 
    the precise start and end dates of each recession period. The start of a recession is marked 
    by the last day of the month before the recession indicator turns to 1, and the end is marked 
    by the last day of the month when the recession indicator is 1 before turning back to 0.

    Parameters:
    - start_date (str): The start date for fetching the recession data, formatted as 'YYYY-MM-DD'.
    - end_date (str): The end date for fetching the recession data, formatted as 'YYYY-MM-DD'.

    Returns:
    - dict: A nested dictionary where each key is a recession number and its value is another 
            dictionary with 'start' and 'end' keys indicating the respective start and end dates 
            of the recession, formatted as 'YYYY-MM-DD'.
    """
    
    # Fetch US recession data from FRED using the provided date range
    usrec = web.DataReader("USREC", "fred", start_date, end_date)
    
    # Initialize variables for tracking recessions and their dates
    recessions = {}
    recession_num = 0
    start = None

    # Iterate through the recession data to identify start and end dates
    for i in range(len(usrec)):
        if usrec.iloc[i, 0] == 1:  # Current month is marked as a recession month
            if start is None:  # This marks the beginning of a new recession
                start = usrec.index[i]  # Record the start date
                # Adjust to the last day of the start month
                start = datetime(start.year, start.month, calendar.monthrange(start.year, start.month)[1])
            # Keep updating the end date as long as the recession continues
            end = usrec.index[i]
            end = datetime(end.year, end.month, calendar.monthrange(end.year, end.month)[1])
        elif start is not None:  # Recession ends when a month is not marked as a recession month
            recession_num += 1
            # Store the start and end dates of the recession
            recessions[recession_num] = {'start': start.strftime('%Y-%m-%d'), 'end': end.strftime('%Y-%m-%d')}
            start = None  # Reset start for the next recession

    # Handle case where the data ends but a recession is ongoing
    if start is not None:
        recession_num += 1
        recessions[recession_num] = {'start': start.strftime('%Y-%m-%d'), 'end': end.strftime('%Y-%m-%d')}

    # Special case handling for when the data starts during a recession
    if usrec.iloc[0, 0] == 1:
        # Adjust the start date to the last day of the month before the data start date
        first_start = usrec.index[0] - pd.offsets.MonthBegin(1)
        first_start = datetime(first_start.year, first_start.month, calendar.monthrange(first_start.year, first_start.month)[1])
        recessions[1]['start'] = first_start.strftime('%Y-%m-%d')

    return recessions

def add_recession_bands(ax, recessions, start_date, end_date):
    """
    Adds shaded areas to the plot for each recession period that overlaps with the given date range.

    Parameters:
    - ax: The Matplotlib Axes object on which to add the recession bands.
    - recessions (dict): A dictionary containing the start and end dates of recessions.
    - start_date (str): The start date for the plot's data range in 'YYYY-MM-DD' format.
    - end_date (str): The end date for the plot's data range in 'YYYY-MM-DD' format.
    """
    plot_start_date = pd.to_datetime(start_date)
    plot_end_date = pd.to_datetime(end_date)

    # Add vertical shaded areas (vspan) for each recession period
    for rec_num, rec_dates in recessions.items():
        rec_start_date = pd.to_datetime(rec_dates['start'])
        rec_end_date = pd.to_datetime(rec_dates['end'])

        # Check if the recession period overlaps with the plot's data range
        if (rec_start_date <= plot_end_date) and (rec_end_date >= plot_start_date):
            ax.axvspan(rec_start_date, rec_end_date, color="grey", alpha=0.2)
            
# Retrieve the recession periods
# start_date = '1960-01-01'
# end_date = '2023-12-31'
# recessions_dict = fetch_recession_periods(start_date, end_date)
# print(recessions_dict)


def quote_from_url(symbol):
    import requests
    apiBase = 'https://query2.finance.yahoo.com'

    headers = {
      "User-Agent":
      "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"
    }

    def getCredentials(cookieUrl='https://fc.yahoo.com', crumbUrl=apiBase+'/v1/test/getcrumb'):
      cookie = requests.get(cookieUrl).cookies
      crumb = requests.get(url=crumbUrl, cookies=cookie, headers=headers).text
      return {'cookie': cookie, 'crumb': crumb}

    def quote(symbols, credentials):
        url = apiBase + '/v7/finance/quote'
        symbols=['aapl','tsla']
        params = {'symbols': ','.join(symbols), 'crumb': credentials['crumb']}
        response = requests.get(url, params=params, cookies=credentials['cookie'], headers=headers)
        # quotes = response.json()['quoteResponse']['result']
        quotes = response.json()['quoteResponse']['result'][0] #assume one symbol

        return quotes

    credentials = getCredentials()


    # quote_info={'info':quote(symbol,credentials),'history':history(symbol,credentials,day_begin,day_end,interval)}
    quote_info={'info':quote(symbol,credentials)}

    # print('>>>>',quote_info,'<<<<\n\n')
    return quote_info


def Logarithmic_regression(df):

    df['price_y']=np.log(df['Close']) # using natural log of stock price

    df['x']=np.arange(len(df)) #fill index x column with 1,2,3...n
    b,a =np.polyfit(df['x'],df['price_y'],1)

    df['priceTL']=b*df['x'] + a

    df['y-TL']=df['price_y']-df['priceTL']
    df['SD']=np.std(df['y-TL'])
    df['TL-2SD']=df['priceTL']-2*df['SD']
    df['TL-SD']=df['priceTL']-df['SD']
    df['TL+2SD']=df['priceTL']+2*df['SD']
    df['TL+SD']=df['priceTL']+df['SD']

    return df

def plot_chart(df):

    RAINBOWCOLOR1='hotpink'
    RAINBOWCOLOR2='orange'
    RAINBOWCOLOR3='gold'
    RAINBOWCOLOR4='yellowgreen'
    RAINBOWCOLOR5='lightgreen'

    fig, (ax1, ax2) = plt.subplots(dpi=600,nrows=2, sharex=False)

    # chart beautification
    ax1.grid(True, color='silver',linewidth=0.5)
    ax2.grid(True, color='silver',linewidth=0.5)
    ax1.set_ylabel('Price')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Indicator')
    plt.title(f'{symbol} Stock Price Trend with Logarithmic Regression',fontsize=10)
    # plt.suptitle(f'Japan Nikken index 1998 - 2024',fontsize=10)
    ax1.set_xticklabels([])
    ax2.set_xticklabels(df['Date'],rotation=90,fontsize=6)
    date_form = DateFormatter("%m/%Y")
    ax2.xaxis.set_major_formatter(date_form)

    # plotting normal stock price
    ax1.plot(df['Date'],df['Close'], color='darkblue',linewidth=0.5)

    # plotting stock price on log regression
    ax2.plot(df['Date'],df['price_y'],color='black',linewidth=0.5)

    # plotting stock price on log regression
    ax2.plot(df['Date'],df['TL+2SD'],color=RAINBOWCOLOR1, linewidth=0.5)
    ax2.plot(df['Date'],df['TL+SD'],color=RAINBOWCOLOR2,  linewidth=0.5)
    ax2.plot(df['Date'],df['priceTL'],color=RAINBOWCOLOR3,linewidth=0.5)
    ax2.plot(df['Date'],df['TL-SD'], color=RAINBOWCOLOR4, linewidth=0.5)
    ax2.plot(df['Date'],df['TL-2SD'],color=RAINBOWCOLOR5, linewidth=0.5)


    ax2.fill_between(df['Date'],df['TL+2SD'], df['TL+SD'],facecolor=RAINBOWCOLOR2,  alpha=0.6,edgecolor=None,linewidth=0)
    ax2.fill_between(df['Date'],df['TL+SD'], df['priceTL'],facecolor=RAINBOWCOLOR3, alpha=0.6,edgecolor=None,linewidth=0)
    ax2.fill_between(df['Date'],df['priceTL'], df['TL-SD'],facecolor=RAINBOWCOLOR4, alpha=0.6,edgecolor=None,linewidth=0)
    ax2.fill_between(df['Date'],df['TL-SD'], df['TL-2SD'],facecolor=RAINBOWCOLOR5,  alpha=0.6,edgecolor=None,linewidth=0)

    ax1.axhline(df['Close'].iloc[-1],color='red',linestyle='--',linewidth=0.5)
    ax1.text(df['Date'].iloc[-5],df['Close'].iloc[-1],str('{0:.2f}'.format(df['Close'].iloc[-1])),color='red',size=6)
    return fig,ax1,ax2

def predict_price(df):


    df['price_y']=np.log(df['Close']) # using natural log of stock price

    df['x']=np.arange(len(df)) #fill index x column with 1,2,3...n
    b,a =np.polyfit(df['x'],df['price_y'],1)

    df['priceTL']=b*df['x'] + a #apply log regression

    p=np.poly1d(b)
    y0=returns[np.argmax()]
    x0=p(y0)
    # priceTL = p(df['x'].iloc[-1])
    print (x0,y0)


    df['y-TL']=df['price_y']-df['priceTL']
    df['SD']=np.std(df['y-TL'])
    df['TL-2SD']=df['priceTL']-2*df['SD']
    df['TL-SD']=df['priceTL']-df['SD']
    df['TL+2SD']=df['priceTL']+2*df['SD']
    df['TL+SD']=df['priceTL']+df['SD']

    ax2.text(df['Date'].iloc[-1],df['TL+2SD'].iloc[-1],'123',fontsize=6)
    ax2.text(df['Date'].iloc[-1],df['TL+SD'].iloc[-1],'123',fontsize=6)
    ax2.text(df['Date'].iloc[-1],df['priceTL'].iloc[-1],str('%.2f'%priceTL),fontsize=6)
    ax2.text(df['Date'].iloc[-1],df['TL-SD'].iloc[-1], '123',fontsize=6)
    ax2.text(df['Date'].iloc[-1],df['TL-2SD'].iloc[-1],'123',fontsize=6)

def tmp_plot(df,df2):


    fig, (ax1, ax2) = plt.subplots(dpi=600,nrows=2, sharex=False)

    # chart beautification
    ax1.grid(True, color='silver',linewidth=0.5)
    ax2.grid(True, color='silver',linewidth=0.5)
    ax1.set_ylabel('Index')
    ax2.set_xlabel('Date')
    ax2.set_ylabel(baseccy)
    # plt.title(f'{symbol} Stock Price Trend with Logarithmic Regression',fontsize=10)
    plt.suptitle(f'Japan Nikken index 1998 - 2024',fontsize=10)
    ax2.set_xticklabels(df['Date'],rotation=90,fontsize=6)
    date_form = DateFormatter("%m/%y")
    ax2.xaxis.set_major_formatter(date_form)

    # plotting normal stock price
    ax1.plot(df['Date'],df['Close'], color='darkblue',linewidth=0.5)
    ax2.plot(df2['Date'],df2['Close'], color='red',linewidth=0.5)

    ax1.axhline(df['Close'].iloc[-1],color='red',linestyle='--',linewidth=0.5)
    ax1.text(df['Date'].iloc[-5],df['Close'].iloc[-1],str('{0:.2f}'.format(df['Close'].iloc[-1]+100)),color='red',size=6)
    return fig

if __name__ == '__main__':

    df = pd.DataFrame()
    df=yf.Ticker(symbol).history(start=start_date,end=end_date, interval='1d').reset_index()

    # df=pd.read_csv('./SP500PE.csv').reset_index()
    df.rename(columns={'value':'Close', 'date':'Date'},inplace=True)


    df=Logarithmic_regression(df)
    fig,ax1,ax2=plot_chart(df)
    # lets plot recession bands from starting date i.e. common_mindate
    startdate=df['Date'].iloc[0].strftime('%Y-%m-%d')
    print(startdate)
    
    recessions_dict = fetch_recession_periods(startdate, end_date)
    add_recession_bands(ax1, recessions_dict, startdate, end_date)
    add_recession_bands(ax2, recessions_dict, startdate, end_date)

    
    fig.savefig(os.path.expanduser('~/Downloads/rainbow_'+symbol+'_'+start_date+'.jpg'),dpi=600,bbox_inches='tight')
    # predict_price(df)


