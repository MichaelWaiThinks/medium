# -*- coding: utf-8 -*-

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 26 21:25:08 2024

Japan Stock Index approaching all time high, is the stock market really recovering? Let’s Python.
https://medium.com/tech-talk-tank/japan-stock-index-approaching-all-time-high-is-the-stock-market-really-recovered-lets-python-59488c4b2cfb

@author: michaelwai
"""

from datetime import datetime
import pandas as pd
import yfinance as yf
from matplotlib.dates import DateFormatter
from matplotlib import pyplot as plt
import os
import requests
import zipfile
import datetime as dt
import numpy as np

fig, axes = plt.subplots(dpi=300, nrows=4, figsize=(12, 12) , sharex=False)

def Logarithmic_regression(df):

    df=df.dropna()
    df['price_y']=np.log(df['Close']) # using natural log of stock price

    df['x']=np.arange(len(df)) #fill index x column with 1,2,3...n
    b,a =np.polyfit(df['x'],df['price_y'],1)

    df['priceTL']=b*df['x'] + a

    df['y-TL']=df['price_y']-df['priceTL']
    df['SD']=np.std(df['y-TL'])
    df['TL-3SD']=df['priceTL']-3*df['SD']
    df['TL-2SD']=df['priceTL']-2*df['SD']
    df['TL-SD']=df['priceTL']-df['SD']
    df['TL+SD']=df['priceTL']+df['SD']
    df['TL+2SD']=df['priceTL']+2*df['SD']
    df['TL+3SD']=df['priceTL']+3*df['SD']


    return df

def plot_log_chart(df,ax, ytitle=''):

    RAINBOWCOLOR0='silver'
    RAINBOWCOLOR1='hotpink'
    RAINBOWCOLOR2='orange'
    RAINBOWCOLOR3='gold'
    RAINBOWCOLOR4='yellowgreen'
    RAINBOWCOLOR5='lightgreen'
    RAINBOWCOLOR6='skyblue'

    # chart beautification
    ax.grid(True, color='silver',linewidth=0.5)
    ax.set_ylabel(ytitle)

    # plotting stock price on log regression
    ax.plot(df['Date'],df['price_y'],color='black',linewidth=0.5)

    # plotting stock price on log regression
    ax.plot(df['Date'],df['TL+3SD'],color=RAINBOWCOLOR0, linewidth=0.5)
    ax.plot(df['Date'],df['TL+2SD'],color=RAINBOWCOLOR1, linewidth=0.5)
    ax.plot(df['Date'],df['TL+SD'],color=RAINBOWCOLOR2,  linewidth=0.5)
    ax.plot(df['Date'],df['priceTL'],color=RAINBOWCOLOR3,linewidth=0.5)
    ax.plot(df['Date'],df['TL-SD'], color=RAINBOWCOLOR4, linewidth=0.5)
    ax.plot(df['Date'],df['TL-2SD'],color=RAINBOWCOLOR5, linewidth=0.5)
    ax.plot(df['Date'],df['TL-2SD'],color=RAINBOWCOLOR6, linewidth=0.5)

    ax.fill_between(df['Date'],df['TL+3SD'], df['TL+2SD'],facecolor=RAINBOWCOLOR1,  alpha=0.6,edgecolor=None,linewidth=0.5)
    ax.fill_between(df['Date'],df['TL+2SD'], df['TL+SD'],facecolor=RAINBOWCOLOR2,  alpha=0.6,edgecolor=None,linewidth=0.5)
    ax.fill_between(df['Date'],df['TL+SD'], df['priceTL'],facecolor=RAINBOWCOLOR3, alpha=0.6,edgecolor=None,linewidth=0.5)
    ax.fill_between(df['Date'],df['priceTL'], df['TL-SD'],facecolor=RAINBOWCOLOR4, alpha=0.6,edgecolor=None,linewidth=0.5)
    ax.fill_between(df['Date'],df['TL-SD'], df['TL-2SD'],facecolor=RAINBOWCOLOR5,  alpha=0.6,edgecolor=None,linewidth=0.5)
    ax.fill_between(df['Date'],df['TL-2SD'], df['TL-3SD'],facecolor=RAINBOWCOLOR6,  alpha=0.6,edgecolor=None,linewidth=0.5)
    return 


def plot_chart(df,col,ax1,color='blue', ytitle=''):
    # chart beautification
    ax1.grid(True, color='silver',linewidth=0.5)
    ax1.set_ylabel(ytitle+' ',fontsize=8)

    # plt.suptitle(f'Japan Nikken index 1998 - 2024',fontsize=10)
    # ax2.set_xticklabels(df['Date'],rotation=90,fontsize=6)
    ax1.grid(color='grey', linestyle='--', linewidth=0.3)
    ax1.yaxis.tick_right()
    ax1.set_xticklabels(df['Date'],rotation=90,fontsize=6)
    date_form = DateFormatter("%m/%Y")
    ax1.xaxis.set_major_formatter(date_form)
    ax1.xaxis.set_major_locator(plt.MaxNLocator(20))
    ax1.yaxis.set_major_locator(plt.MaxNLocator(5))


    # plotting normal stock price
    ax1.plot(df['Date'], df[col], color=color,linewidth=1,alpha=0.8)
    return fig


if __name__ == '__main__':

    symbol='^HSI'
    CCY='HKD=X'
    GLD='GC=F'
    CountryCode='HKG'

    symbol='^N225'
    CCY='JPY=X'
    ytitle='Nikken'
    GLD='GC=F'
    CountryCode='JPY'
    
    symbol='GC=F'
    ytitle='Gold 金價'
    CCY='SI=F'



    # symbol='BTC-USD'
    # CCY='DX-Y.NYB'
    # CountryCode='USA'

    # symbol='BTC-USD'
    # CCY='DX-Y.NYB'
    # CountryCode='USA'

    # symbol='^FTSE'
    # CCY='GBP=X'
    # CountryCode='GBR'

    start_date='2021-01-01'
    end_date = datetime.today().strftime('%Y-%m-%d')

    # INDEX PRICE
    df = pd.DataFrame()
    df=yf.Ticker(symbol).history(start=start_date,end=end_date, interval='1d').reset_index()
    # df['Date']=df['Date'].dt.tz_localize(None)
    # df['Date'] = pd.to_datetime(df['Date'])
    plot_chart(df,'Close',axes[0],color='orange',ytitle=symbol)

    # INDEX PRICE neutralized by USD and USD/Cuurency price
    # for another study providing local exchange rate
    dfCCY=yf.Ticker(CCY).history(start=start_date,end=end_date, interval='1d').reset_index()
    dfCCY=dfCCY.rename(columns={'Close':CCY})
    df['Real Index']=df['Close']/dfCCY[CCY]#*dfCCY[CCY].iloc[-1]
    # dfCCY['Date']=dfCCY['Date'].dt.tz_localize(None)

    # plot_chart(df,'Gold/Silver Ratio',axes[0],color='green')
    plot_chart(dfCCY,CCY,axes[1],color='gray',ytitle=CCY)

    
    # INDEX PRICE neutralized by USD and USD/Cuurency price
    # for another study providing local exchange rate
    # dfGLD=yf.Ticker(GLD).history(start=start_date,end=end_date, interval='1d').reset_index()
    # dfGLD=dfGLD.rename(columns={'Close':GLD})
    # df['Gold Silver Ratio']=df['Close']/dfGLD[GLD]*dfGLD[GLD].iloc[-1]
    # dfCCY['Date']=dfCCY['Date'].dt.tz_localize(None)

    plot_chart(df,'Real Index',axes[2],color='skyblue',ytitle=symbol+' / '+CCY)
    
    df_goldsilver=df.copy()
    df_goldsilver['Close']=df['Real Index']
    print(df_goldsilver['Close'])
    dflog=Logarithmic_regression(df_goldsilver)
    plot_log_chart(dflog, axes[3], ytitle='Real Index LogReg')
    
    plt.suptitle(symbol+' '+end_date)
    plt.tight_layout()
