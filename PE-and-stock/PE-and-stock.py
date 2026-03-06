#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 19 03:02:31 2024

@author: michaelwai
"""

import pandas as pd

import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as patches
from matplotlib.dates import DateFormatter
from matplotlib.ticker import FuncFormatter
from matplotlib import dates

import numpy as np
import math

import datetime as dt


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

def plot_log_chart(df,ax,label):

    RAINBOWCOLOR1='hotpink'
    RAINBOWCOLOR2='orange'
    RAINBOWCOLOR3='gold'
    RAINBOWCOLOR4='yellowgreen'
    RAINBOWCOLOR5='lightgreen'

    # chart beautification
    ax.grid(True, color='silver',linewidth=0.5)
    ax.set_xlabel('Date')
    ax.set_ylabel('Reg Log')
    # plt.suptitle(f'Japan Nikken index 1998 - 2024',fontsize=10)
    ax.set_xticklabels(df['Date'],rotation=90,fontsize=6)
    date_form = DateFormatter("%m/%y")
    ax.xaxis.set_major_formatter(date_form)

    # plotting stock price on log regression
    ax.plot(df['Date'],df['price_y'],color='black',linewidth=0.5,label=label)

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

    return fig


symbols=['^SPX','AAPL','META']#,'AAPL','MSFT','KO', 'CSCO']
df_SP=pd.read_csv('SP500PE.csv')#.set_index('date')
df_SP.rename(columns={'date':'Date','value':'Close'},inplace=True)


# df_SP.index=pd.to_datetime(df_SP.index, format='%d/%m/%Y')
df_SP['Date']=pd.to_datetime(df_SP['Date'], format='%d/%m/%Y')
# df_SP.index = df_SP['Date'].strftime('%Y-%m-%d')

df_stock = yf.download(symbols,start='1920-01-01') #download all symbols at once
set(df_stock.columns.get_level_values(0))
df_stock=df_stock['Close']

df_stock.to_csv('stock.csv')
# print(df_stock['AAPL'])
fig, ax = plt.subplots(dpi=300, nrows=2, figsize=(12, 12) , sharex=True)

# df.index = (pd.to_datetime(df.index,utc=True)).date

df_SP.rename(columns={'date':'Date','value':'Close'},inplace=True)

# ax[0].plot(df_SP['Date'],df_SP['Close'])

Logarithmic_regression(df_SP)
plot_log_chart(df_SP,ax[1],'P/E S&P500')

for s in symbols:
    df_1stock=pd.DataFrame(df_stock[s])
    df_1stock.rename(columns={s:'Close'},inplace=True)
    # df_1stock.index=pd.to_datetime(df_1stock.index)
    # df_1stock.index=pd.to_datetime(df_1stock.index, utc=True)
    # df_1stock.index = df_1stock.index.strftime('%Y-%m-%d')

    ax[0].plot(df_1stock.index,df_1stock['Close'], label=s)

ax[0].set_yscale('log')
# ax[1].set_yscale('log')


ax[0].tick_params(labelbottom=False)

ax[1].xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
ax[1].xaxis.set_tick_params(labelsize=6, rotation=90)
ax[1].xaxis.set_major_locator(mdates.YearLocator(5))
ax[0].xaxis.grid(linestyle='-')
ax[1].xaxis.grid(linestyle='-')
plt.suptitle('S&P500 PE')
plt.legend()
plt.tight_layout()

