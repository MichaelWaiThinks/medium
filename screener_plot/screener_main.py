#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb  1 17:41:25 2024
Everyone can visualize stock trend with these Python codes!
https://medium.com/tech-talk-tank/everyone-can-visualize-stock-data-with-these-python-codes-46be14fca954
@author: michaelwai
"""

import pandas as pd
from datetime import datetime
import math
import requests
import numpy as np
import re

from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.dates import DateFormatter

import yfinance as yf
# from pandas_datareader import data as pdr
# from yahooquery import Ticker
# pd.options.mode.chained_assignment = None  # default='warn'

def trading_inidicator(ax, df):
    df['ema1'] = df['Close'].ewm(span=30, adjust=False).mean()
    df['ema2'] = df['Close'].ewm(span=80, adjust=False).mean()
    df['ema3'] = df['Close'].ewm(span=100, adjust=False).mean()
    df['ema4'] = df['Close'].ewm(span=200, adjust=False).mean()

    ax.plot(df['Date'],df['ema1'],color='orange',linewidth=0.6, alpha=1)
    ax.plot(df['Date'],df['ema2'],color='blue',linewidth=0.6, alpha=1)
    ax.plot(df['Date'],df['ema3'],color='violet',linewidth=0.6, alpha=1)
    ax.plot(df['Date'],df['ema4'],color='red',linewidth=0.6, alpha=1)

    return ax


def Logarithmic_regression(df):
    df = df[df['Close'].notna()]
    df['price_y']=np.log(df['Close']) # using natural log of stock price

    df['x']=np.arange(len(df)) #fill index x column with 1,2,3...n
    try:
        b,a =np.polyfit(df['x'],df['price_y'],1)
    except Exception as e:
        b,a=0,0

    df['priceTL']=b*df['x'] + a

    df['y-TL']=df['price_y']-df['priceTL']
    df['SD']=np.std(df['y-TL'])
    df['TL-2SD']=df['priceTL']-2*df['SD']
    df['TL-SD']=df['priceTL']-df['SD']
    df['TL+2SD']=df['priceTL']+2*df['SD']
    df['TL+SD']=df['priceTL']+df['SD']

    return df

def plot_chart(ax,df):

    RAINBOWCOLOR1='hotpink'
    RAINBOWCOLOR2='orange'
    RAINBOWCOLOR3='gold'
    RAINBOWCOLOR4='yellowgreen'
    RAINBOWCOLOR5='lightgreen'


    # fig, (ax1, ax2) = plt.subplots(dpi=600,nrows=2, sharex=True)

    # plotting stock price on log regression
    ax.plot(df['Date'],df['price_y'],color='black',linewidth=0.5)

    # plotting stock price on log regression
    ax.plot(df['Date'],df['TL+2SD'],color=RAINBOWCOLOR1, linewidth=0.5)
    ax.plot(df['Date'],df['TL+SD'],color=RAINBOWCOLOR2,  linewidth=0.5)
    ax.plot(df['Date'],df['priceTL'],color=RAINBOWCOLOR3,linewidth=0.5)
    ax.plot(df['Date'],df['TL-SD'], color=RAINBOWCOLOR4, linewidth=0.5)
    ax.plot(df['Date'],df['TL-2SD'],color=RAINBOWCOLOR5, linewidth=0.5)


    ax.fill_between(df['Date'],df['TL+2SD'], df['TL+SD'],facecolor=RAINBOWCOLOR2,  alpha=0.6,edgecolor=None,linewidth=0)
    ax.fill_between(df['Date'],df['TL+SD'], df['priceTL'],facecolor=RAINBOWCOLOR3, alpha=0.6,edgecolor=None,linewidth=0)
    ax.fill_between(df['Date'],df['priceTL'], df['TL-SD'],facecolor=RAINBOWCOLOR4, alpha=0.6,edgecolor=None,linewidth=0)
    ax.fill_between(df['Date'],df['TL-SD'], df['TL-2SD'],facecolor=RAINBOWCOLOR5,  alpha=0.6,edgecolor=None,linewidth=0)

    return ax

def get_etf_holdings(symbol_list):
    header = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36 '}

    if type(symbol_list) != list:
        symbol_list=[symbol_list]

    etf_url='https://www.schwab.wallst.com/schwab/Prospect/research/etfs/schwabETF/index.asp?type=holdings&symbol={}'
    mutual_fund_url="https://www.zacks.com/funds/mutual-fund/quote/{}/holding"

    #which url to use?
    url=etf_url

    df_stocklist=pd.DataFrame()
    with requests.Session() as req:
        req.headers.update(header)
        for s in symbol_list:
            r = req.get(url.format(s))

            etfholdings = re.findall(r'<td class=\"symbol firstColumn\" tsraw=\"(.*?)\">', r.text)
            print ('***** ETF: ',s,'holds:\n',etfholdings)
            etfholdingsname = re.findall(r'<td class=\"description\" tsraw=\"(.*?)\">', r.text)
            df=pd.DataFrame(
                {
                    'Symbol':etfholdings,
                    'Name':etfholdingsname
                })

            df['Name']=df['Name'].str.replace(' Class A','')
            df['Name']=df['Name'].str.replace(' Ordinary Shares','')
            df['Name']=df['Name'].str.replace(' -','')
            df['Symbol']=df['Symbol'].replace('', np.nan)
            df_stocklist=pd.concat([df_stocklist,df])

    print (df_stocklist)

    df_stocklist=df_stocklist.dropna(subset=['Symbol'])
    df_stocklist=df_stocklist.drop_duplicates(subset=['Symbol'])
    df_stocklist=df_stocklist.sort_values(by=['Symbol']).reset_index(drop=True)

    return df_stocklist

def read_html_table(source):
    header = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36 '}

    res = requests.get(source,headers=header, timeout=20)

    if res.status_code != 200:
        res = requests.get(source,headers=header, timeout=20) #try 1 more time
        return None, res.status_code, res.text

    # soup = BeautifulSoup(res.content, "lxml")
    soup = BeautifulSoup(res.content, "html.parser")

    if 'Select All' in res.text:
        for tag in soup.find_all("span", {'class':'Fz(0)'}): #remove those select checkboxes if any
            tag.replaceWith('')

    table = soup.find_all('table')
    if len(table)==0:
        print ('something very wrong!')
        return None

    # return symbol list
    df = pd.read_html(str(table))[0]
    return df

def stock_screener(link='',symbol_list=[],startdate='2020-01-01',charttitle=''):


    if link!='':
        symbol_list =read_html_table(link)

    print ('stock list retreived: ',symbol_list)

    if symbol_list.empty:
        raise RuntimeError('stock list is empty?!')


    # symbol_list = pd.DataFrame(
    #     {
    #         'Symbol':['META','TSLA','MSFT','AAPL','AMZN','NVDA','COIN', 'WMT'],
    #         'Name':['Meta','Tesla','Microsoft','Apple','Amazon','Nvidia','Coinbase','Walmart']
    #     }
    # )

    figrow=math.ceil(math.sqrt(len(symbol_list)))
    figcol=math.ceil(math.sqrt(len(symbol_list)))
    if figrow*figcol-len(symbol_list) >= figrow: # find the best fit square array of charts
        figrow-=1

    dynamic_dpi = min(figrow * figcol * 10, 1200)
    dynamic_fontsize = max(8-figcol,4) #max(100/(figcol*figrow),5)

    # prepare the chart
    fig, axes = plt.subplots(figrow,figcol, figsize=(figcol, figrow), dpi=600, squeeze=False, sharey=False,sharex='col')


    # Read finance data from Yahoo

    all_stock_data=yf.download(symbol_list.Symbol.to_list(),start=startdate,interval='1d')

    set(all_stock_data.columns.get_level_values(0))
    all_stock_data=all_stock_data.reset_index()
    # all_stock_data.to_csv('all_stock_data.csv')


    for i,s in enumerate(symbol_list.Symbol): # iterate for every stock indices

        tickerDf=pd.DataFrame()
        ax = axes[int(i%figrow),int(i/figrow)]

        tickerDf['Date']=all_stock_data['Date']
        tickerDf['Close']=all_stock_data['Close'][s]

        """                                           """
        """ +------- SUBPLOT CHART TITLE HERE ------+ """
        """                                           """
        company_name_len=16

        title_name=(symbol_list[symbol_list['Symbol']==s].iloc[0])['Name']
        title_name=title_name[:company_name_len]

        titlecolor='black'
        facecolor='white'

        # Plot stock chart
        ax.plot(tickerDf['Date'],tickerDf['Close'],color='black',linewidth=0.6, alpha=1)

        """ Your trading analysis and Plot here """
        # tickerDf=Logarithmic_regression(tickerDf)
        # ax=plot_chart(ax, tickerDf)
        ax=trading_inidicator(ax, tickerDf)

        # Here we try to use background color to indicate stock changes
        if len(tickerDf)>3 : # try to avoid new stock with less than 3 days of data
            if math.isnan(tickerDf['Close'].iloc[-1]): #sometimes yahoo returns current date data as NaN as the market hasn't open
                current_price=tickerDf['Close'].iloc[-2] #tickerinfoData.get('ask')
                previous_price=tickerDf['Close'].iloc[-3]
            else:
                current_price=tickerDf['Close'].iloc[-1] #tickerinfoData.get('ask')
                previous_price=tickerDf['Close'].iloc[-2]

            pct_change=((current_price-previous_price)/previous_price)*100

        if (pct_change>=0):
            todaytrendsymbol='⇧'
            titlecolor='darkgreen'
            facecolor='palegreen'
        else:
            todaytrendsymbol='⇩'
            titlecolor='red'
            facecolor='mistyrose'


        # use facecolor to indicate Up/Down for easy visualization
        ax.patch.set_facecolor(facecolor)
        # let's beautify the chart a bit
        ax.grid(True, color='silver',linewidth=0.5)
        ax.tick_params(axis='x',labelrotation=90)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y/%m'))
        ax.xaxis.set_tick_params(labelsize=dynamic_fontsize)
        ax.yaxis.set_tick_params(labelsize=dynamic_fontsize)

        # Finally, add a title to the figure
        title=title_name+'\n('+s+')'+\
            str('%.2f'%current_price)+\
            todaytrendsymbol+str('%.2f'%pct_change)+'%'
        ax.set_title(title, fontweight='bold',color=titlecolor,fontsize=dynamic_fontsize)

        if (i==0): # at each bottom row set the xaxis as date tick
            for j in range(len(symbol_list),int(figrow*figcol)):
                ax = axes[ int(j%figrow),int(j/figrow)]
                ax.tick_params(axis='x',labelrotation=90)
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y/%m'))
                ax.xaxis.set_tick_params(labelsize=dynamic_fontsize)
                ax.yaxis.set_tick_params(labelsize=dynamic_fontsize)

    plt.subplots_adjust(wspace=0.12, hspace=0.1)

    today=datetime.now().strftime("%Y-%m-%d")
    fig.suptitle(charttitle+'\n'+startdate+'~'+today, fontweight ="bold",y=1, fontsize=dynamic_fontsize)
    fig.tight_layout()
    fig.savefig('/Users/michaelwai/Downloads/fig.jpg',dpi=400,bbox_inches='tight')

    return True



if __name__ == '__main__':
    url='https://finance.yahoo.com/trending-tickers'
    ARK=['ARKK','ARKW','ARKG','ARKQ','ARKF','ARKX']
    HK='EWH'
    US=['QQQ']

    listofEFT=US
    # stock_screener('https://finance.yahoo.com/trending-tickers',startdate='2022-01-01')
    # stock_screener(url,startdate='2023-01-01')

    stock_screener('', get_etf_holdings(listofEFT) ,startdate='2023-01-01', charttitle='US ETF')


# https://www.schwab.wallst.com/schwab/Prospect/research/etfs/schwabETF/index.asp?YYY101_z5K6INmijHlJfnlzwDHOvi/hjoBQ5b+E0TeOoGxn1A7DsA/X/2E43Z8cvZPk2Bq1kYqlVaWSSvG7LA7ia8UkC+dIWy0JMFtSM57akQFVHX7483xVCc/Aopv7kniRT3o2&type=holdings&symbol=EWH


