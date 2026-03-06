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
data_folder='./wbdata/'
zip_file='wbdata.zip'
data_file='WDIData.csv'
os.makedirs(os.path.dirname(data_folder+zip_file), exist_ok=True)

url = 'https://databank.worldbank.org/data/download/WDI_CSV.zip'
GDP = 'NY.GDP.MKTP.KD'       # GDP in constant 2015 $US
HCI = 'HD.HCI.OVRL'          # Human Capital Index
GDPPC = 'NY.GDP.PCAP.KD'     # GDP per capita in constant 2015 $US
CPI = 'FP.CPI.TOTL.ZG'       # Inflation rate
FDI = 'BX.KLT.DINV.WD.GD.ZS' # Foreign Direct Investment as a share of GDP


def init_world_data():
    if os.path.exists(data_folder+data_file):
        print('reading data file:',data_folder+data_file)
        df= pd.read_csv(data_folder+data_file)
    else:
        if not os.path.exists(data_folder+zip_file):
            r = requests.get(url,timeout=300)
            print('downloading data file:',url)

            with open(data_folder+zip_file, 'wb') as f:
                f.write(r.content)

        zf = zipfile.ZipFile(data_folder+zip_file)
        df = pd.read_csv(zf.open(data_file))
        print('saving data file:',data_folder+data_file)
        df.to_csv(data_folder+data_file,index=False)

    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    return df

def Logarithmic_regression(df):

    print (df)
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

def get_world_data(df,indicator='',country_code=''):
    print (indicator , '/',country_code)
    if indicator and country_code:
        # df.to_csv(country_code+'.csv') #For debug purpose
        df=df[(df['Indicator Code']==indicator) & (df['Country Code']==country_code)]
        df=df.T
        df=df.iloc[5:]
        df=df.reset_index()
        df.rename(columns={
            df.columns[0]:'Date',
            df.columns[1]:'GDP'},
            inplace=True)
        df['Date']=df['Date'].astype(str)+'-01-01'
        df['Date']=pd.to_datetime(df['Date'],format="%Y-%m-%d")
        df.to_csv(data_folder+country_code+'_GDP.csv',index=False)
        return df
    else:
        print ('%s or %s not found from GDP data, pls check'%(indicator , country_code))
        return None
        # df['Date']=df['Date'].tz_convert(None)
# =============================================================================
#
# def get_gdp(countryname):
#     data_url = "https://github.com/QuantEcon/lecture-python-intro/raw/main/lectures/datasets/mpd2020.xlsx"
#     data = pd.read_excel(data_url,
#                 sheet_name='Full data')
#     data.head()
#
#     countries = data.country.unique()
#     # print ('/Countries data available=',countries)
#     # print (data.columns)
#     # Index(['countrycode', 'country', 'year', 'gdppc', 'pop']
#     # print ('/Years of data available=',data.year.min(),'-',data.year.max())
#
#
#     country_years = []
#     for country in countries:
#         cy_data = data[data.country == country]['year']
#         ymin, ymax = cy_data.min(), cy_data.max()
#         country_years.append((country, ymin, ymax))
#     country_years = pd.DataFrame(country_years,
#                         columns=['country', 'min_year', 'max_year']).set_index('country')
#     country_years.head()
#
#     code_to_name = data[
#         ['countrycode', 'country']].drop_duplicates().reset_index(drop=True).set_index(['countrycode'])
#
#     gdp_pc = data.set_index(['country', 'year'])['gdppc']
#     gdp_pc = gdp_pc.unstack('country')
#
#     gdp_pc.tail()
#     gdp_pc.to_csv('gdp.csv')
#
#     # print (gdp_pc[countryname])
#
#
#     return gdp_pc[countryname]
#
# =============================================================================

def plot_log_chart(df,ax):

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

    return fig

def plot_chart(df,col,ax1,title='',color='blue'):
    # chart beautification
    ax1.grid(True, color='silver',linewidth=0.5)
    ax1.set_ylabel(col+' '+title,fontsize=8)

    # plt.suptitle(f'Japan Nikken index 1998 - 2024',fontsize=10)
    # ax2.set_xticklabels(df['Date'],rotation=90,fontsize=6)
    ax1.grid(color='grey', linestyle='--', linewidth=0.2)
    ax1.yaxis.tick_right()
    ax1.set_xticklabels(df['Date'],rotation=90,fontsize=6)
    date_form = DateFormatter("%m/%y")
    ax1.xaxis.set_major_formatter(date_form)
    ax1.xaxis.set_major_locator(plt.MaxNLocator(20))
    ax1.yaxis.set_major_locator(plt.MaxNLocator(5))


    # plotting normal stock price
    ax1.plot(df['Date'], df[col], color=color,linewidth=0.5,alpha=0.8)
    return fig

if __name__ == '__main__':

    # symbol='^HSI'
    # CCY='HKD=X'
    # CountryCode='HKG'

    # symbol='^N225'
    # CCY='JPY=X'
    # CountryCode='JPN'


    # symbol='BTC-USD'
    # CCY='DX-Y.NYB'
    # CountryCode='USA'

    symbol='BTC-USD'
    CCY='DX-Y.NYB'
    CountryCode='USA'

    # symbol='^FTSE'
    # CCY='GBP=X'
    # CountryCode='GBR'

    start_date='2012-01-01'
    end_date = datetime.today().strftime('%Y-%m-%d')

    # INDEX PRICE
    df = pd.DataFrame()
    df=yf.Ticker(symbol).history(start=start_date,end=end_date, interval='1d').reset_index()
    df['Date']=df['Date'].dt.tz_localize(None)

    df['Date'] = pd.to_datetime(df['Date'])
    # print(df[(df['Date'].dt.year>=2012) & (df['Date'].dt.year<=2013)])
    df1=df
    plot_chart(df1,'Close',axes[0],color='blue')
    # df2=df[(df['Date']>=2016) & (df['Date'].dt.year<=2017)]
    df2=df[(df['Date']<="2016-08-01")] #before 2nd halving
    plot_chart(df2,'Close',axes[1],color='blue')
    # df3=df[(df['Date'].dt.year>=2020) & (df['Date'].dt.year<=2021)]
    df3=df[(df['Date']>="2016-07-01") & (df['Date']<="2020-05-01")] #between 2nd and 3rd halving
    plot_chart(df3,'Close',axes[2],color='blue')
    # df4=df[(df['Date'].dt.year>=2024) & (df['Date'].dt.year<=2024)]
    df4=df[(df['Date']>="2020-05-01")] #between 2nd and 3rd halving
    plot_chart(df4,'Close',axes[3],color='blue')
    df1=Logarithmic_regression(df)
    aaa
    plot_log_chart(df1,axes[0])
    df2=Logarithmic_regression(df[(df['Date'].dt.year>=2016) & (df['Date'].dt.year<=2017)])
    plot_log_chart(df2,axes[1])
    df3=Logarithmic_regression(df[(df['Date'].dt.year>=2020) & (df['Date'].dt.year<=2021)])
    plot_log_chart(df3,axes[2])
    df4=Logarithmic_regression(df[(df['Date'].dt.year>=2024) & (df['Date'].dt.year<=2024)])
    plot_log_chart(df4,axes[3])
    fig.tight_layout()

    fig.show()
    aaa

    # CURRENCY PRICE neutralized
    # for another study providing local exchange rate
    dfCCY=yf.Ticker(CCY).history(start=start_date,end=end_date, interval='1d').reset_index()
    dfCCY=dfCCY.rename(columns={'Close':CCY})
    df['Price US$ adjusted']=df['Close']/dfCCY[CCY]*dfCCY[CCY].mean()
    dfCCY['Date']=dfCCY['Date'].dt.tz_localize(None)

    plot_chart(df,'Price US$ adjusted',axes[0],color='gray')
    plot_chart(dfCCY,CCY,axes[1],color='red')


    # GDP PRICE
    dfGDP=init_world_data()
    dfGDP=get_world_data(dfGDP,GDP,CountryCode)
    dfGDP['Date']=dfGDP['Date'].dt.tz_localize(None)

    minmin_year=min(min(df['Date']),min(dfCCY['Date']))
    dfGDP_for_plot=dfGDP[dfGDP['Date']>=minmin_year]

    plot_chart(dfGDP_for_plot,'GDP',axes[2],color='green')

    chart_title = symbol + ', ' + CCY + ' and GDP of '+CountryCode
    fig.suptitle(chart_title,fontsize=12)
    fig.savefig(os.path.expanduser('~/Downloads/'+symbol+'_'+start_date+'.jpg'),dpi=600)
    print('~/Downloads/'+symbol+'_'+start_date+'.jpg')

