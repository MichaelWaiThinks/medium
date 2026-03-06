#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 11 09:45:11 2024

@author: michaelwai
"""

import requests
from datetime import datetime as dt
import time
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as md
import matplotlib.ticker as mtick
import random
from yahooquery import Ticker
import numpy as np
import yfinance as yf
import warnings
import re
import seaborn
import os

warnings.simplefilter(action="ignore", category=FutureWarning)

FROM_YEAR='2023'
WHOLE_PLOT= False
pagoda = ["blue", "green", "red", "orchid",'orange', 'darkgrey',
      "darkred", "lightcoral", "brown", "sandybrown", "tan",
      "darkkhaki", "olivedrab", "lightseagreen",
      "steelblue", "dodgerblue", "slategray",
      "blue", "darkorchid", "violet", "deeppink", "hotpink"]

# =============================================================================
# import distinctipy
# color_list =distinctipy.get_colors(100,pastel_factor=0.3)
# =============================================================================
# =============================================================================
# import matplotlib.colors as mc
# color_list=[*(mc.CSS4_COLORS.keys())]
# random.shuffle(color_list)
# =============================================================================
# print ('### Color list contains ',len(pagoda)),' colors ###'


def assign_color(df):

    cmap = plt.get_cmap('Spectral')
    colors={}
    totalcolors=len(pagoda)

    for i,symbol in enumerate(df.columns):
        # color=color_list[i]
        # color=cmap(i)
        color=pagoda[i%totalcolors]
        # color = colorsys.hsv_to_rgb(i/1000, 1.0, 1.0)
        colors.update({symbol:color}) # pick from 20 colors
    return colors
# =============================================================================
# 
# def get_tickers_price(symbols,_start_date='1998-01-01',_end_date='2024-04-01'):
#     
#     if os.path.isfile('./nasdaq_data.csv'):
#         print('reading nasdaq data...')
#         df=pd.read_csv('./nasdaq_data.csv',index_col=0,header=[0,1])#if want to skip multicolumn header-> index_col=1,  header=None,skiprows=1
# 
#         # drop index and retrieve all stock Close price
#         # df=(df.drop(['Date'], axis = 1,level=0)) #to drop for heatmap
#         df.reset_index(drop=True, inplace=True)
#         print(df.columns)
#         df=df[['Date','Close']]
#         # df.to_csv('df_readdata.csv')
#         
#     else:
#         df = (yf.download(symbols,start=_start_date,end=_end_date)).reset_index() #download all symbols at once
#         df.to_csv('nasdaq_data.csv')
#         df = df[['Date','Close']]
#         # df.to_csv('df_download.csv')
#     return df
#     
# =============================================================================
def get_tickers_price(symbols,_start_date='1998-01-01',_end_date='2024-04-01'):
    
    if os.path.isfile('./nasdaq_data.csv'):
        print('reading nasdaq data...')
        df=pd.read_csv('./nasdaq_data.csv',index_col=0,header=[0,1])#if want to skip multicolumn header-> index_col=1,  header=None,skiprows=1

        # drop index and retrieve all stock Close price
        # df=(df.drop(['Date'], axis = 1,level=0)) #to drop for heatmap
        df.reset_index(drop=True, inplace=True)
        df=df[['Date','Close']]
        df=df.droplevel(0, axis=1)  #remove first level
        df=df.rename(columns={ df.columns[0]: "Date" }).set_index('Date')  # df=df.reset_index()
        # df.to_csv('df_readdata.csv')
        
    else:
        ticker = Ticker(symbols)
        # df = ticker.history(start=_start_date,end=_end_date).reset_index() #tickers.history(start=start,end=end)
        # df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y/%m/%d')
        # print (df)
        
        df = (yf.download(symbols,start=_start_date,end=_end_date)).reset_index() #download all symbols at once
        df.to_csv('nasdaq_data.csv')
        df = df[['Date','Close']]
        # df.to_csv('df_download.csv')
    return df

def sortcolumn(df,topcount=5):
    # print (df)
    
    lastrow=df.index[-1]
    df=df.T.sort_values(lastrow,ascending=False) # transpose and sort rows
    topnames=df[:topcount].index
    # print(topnames)
    # input('continue...')
    return df.T,topnames # transpose back to column

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
    return [(stock['symbol'], stock['name']) for stock in holdings]

def plot_qtr_chart(df,year):
    year=str(year)
    
    if True:
        i=0
        plt.close()
        fig, axes = plt.subplots(1, 4, figsize=(12, 8), dpi=150, sharey=True)
        ShowHighRunners=False

        highrunners=5

        colors=assign_color(df)

        df,topyearlyrunners=sortcolumn(df,highrunners)

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


        # plot for each quarter
        for i in range (4):
            try:
                Qdf[i]=(df[(df.index>Qstart[i]) & (df.index<Qend[i])])
                # print ('plotting ',Qstart[i],'-',Qend[i])
            # Q2df=(df[(df['date']>Q2start) & (df['date']<Q2end)]).set_index('date')
            # Q3df=(df[(df['date']>Q3start) & (df['date']<Q3end)]).set_index('date')
            # Q4df=(df[(df['date']>Q4start) & (df['date']<Q4end)]).set_index('date')

                Qdf[i].to_csv(str(year)+'Q'+str(i+1)+'.csv')

                Qdf[i],topquarterlyrunners=sortcolumn(Qdf[i],highrunners)
                # print (topquarterlyrunners, topyearlyrunners, Qdf[i])

                for s in Qdf[i].columns:
                    
                    # assign label to top runners else nothing for simplification
                    label=''
                    if s not in topquarterlyrunners and s not in topyearlyrunners:
                        axes[i].plot(Qdf[i][s],alpha=0.2,color=colors[s],label='_Hidden label')
                    else:
                        label=s
                        if s in topquarterlyrunners:
                            linestyle='-'
                            label=label+'^'
                            alpha=0.5
                        if s in topquarterlyrunners and s in topyearlyrunners:
                            linestyle='-'
                            label=label+'*'
                            alpha=1
                        
                        # plot the line
                        
                        axes[i].plot(Qdf[i][s],alpha=alpha,linestyle=linestyle,color=colors[s],label=label)
                        axes[i].text(Qdf[i][s].index[-1],Qdf[i][s].iloc[-1],label,color=colors[s])
            except Exception as e:
                print ('skipping ',Qstart[i],'-',Qend[i], str(e))
                continue
            # axes[i].plot(Qdf[i],alpha=0.5,color=colors,label=Qdf[i].columns)


            # labels = [(col if col in topquarterlyrunners else '_Hidden label') for col in Qdf[i].columns]
            # axes[i].legend(labels=labels)
            axes[i].legend()

            Qdf[i]['Max'] = Qdf[i].idxmax(axis=1)
            Qdf[i].to_csv(year+'Q'+str(i+1)+'.csv')

            # set grid for easy reading
            axes[i].xaxis.grid(color='black', linestyle='--', linewidth=0.2)
            axes[i].yaxis.grid(color='black', linestyle='--', linewidth=0.2)

            #find max symbol per quarter
            axes[i].yaxis.set_major_formatter(mtick.PercentFormatter())
            axes[i].xaxis.set_tick_params(labelsize=6, rotation=90)
            axes[i].set_facecolor('whitesmoke')


            # axes[i].legend(labels=df.columns, loc='upper left',
            #       ncol=1, fontsize=6, framealpha=0.7, facecolor='white', frameon=True)
        # axes[3].yaxis.tick_right()
        # # axes[3].get_yaxis().set_visible(True)
        # # axes[1].get_yaxis().set_visible(False)
        # axes[1].tick_params(axis='y', which='both', labelleft=False, labelright=False)
        # axes[3].tick_params(axis='y', which='both', labelleft=False, labelright=True)

        plt.tick_params(axis='y', which='both', labelleft=False, labelright=True)
        plt.tight_layout()
        plt.show()
    # except Exception as e:
    #     print ('plotting error with data from:', year, ' Q',i+1, ' with error:',str(e))

    return fig

def plot_all_time_chart(df):
    # try:
    if True:
        i=0
        plt.close()
        fig, axes = plt.subplots(1, 1, figsize=(12, 8), dpi=300)
        ShowHighRunners=False
        highrunners=5

        colors=assign_color(df)

        df,topyearlyrunners=sortcolumn(df,highrunners)

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


        for s in df.columns:
            label=''
            if s not in topyearlyrunners:
                axes.plot(df[s],alpha=0.3,color=colors[s],label='_Hidden label')
            else:
                label=s
                alpha=0.6
                linestyle='-'
                if s in topyearlyrunners:
                    linestyle='--'
                    label=s+'*'
                    alpha=1

                axes.plot(df[s],alpha=alpha,linestyle=linestyle,color=colors[s],label=label)
                axes.text(df[s].index[-1],df[s].iloc[-1],label,color=colors[s])

        axes.legend()

        df['Max'] = df.idxmax(axis=1)

        # set grid for easy reading
        axes.xaxis.grid(color='black', linestyle='--', linewidth=0.2)
        axes.yaxis.grid(color='black', linestyle='--', linewidth=0.2)

        #find max symbol per quarter
        axes.yaxis.set_major_formatter(mtick.PercentFormatter())
        axes.xaxis.set_tick_params(labelsize=6, rotation=90)
        axes.set_facecolor('whitesmoke')

        plt.tick_params(axis='y', which='both', labelleft=False, labelright=True)
        plt.tight_layout()
        plt.show()
        return fig

def plot_holdings_by_year(df, from_year):
    
    current_year_holdings=pd.DataFrame()
    # df['ipoyear']=df['ipoyear'].astype('Int64')
    fig, axes = plt.subplots(1, 1, figsize=(12, 8), dpi=300, sharey=True)

    
    startdate=str(from_year)+'-01-01'
    enddate= dt.now().strftime("%Y-%m-%d")
    print(df.columns)
    all_holdings_df=get_tickers_price(df['Symbol'].to_list(),startdate,enddate)
    all_holdings_df=all_holdings_df[['Date','Close']]
    print (all_holdings_df.columns,'>>>')
    # Convert the Date column to datetime
    all_holdings_df.index = pd.to_datetime(all_holdings_df.index)
    # Extract year and month from the Date column
    
  
      
    #whole period plot
    if WHOLE_PLOT:
            # print(df['symbol'])
            
            normalized_df = all_holdings_df.apply(lambda x: (x/x.iloc[0]-1)*100)
            normalized_df.replace([np.inf, -np.inf], np.nan, inplace=True)
            fig=plot_all_time_chart(normalized_df)
            fig.savefig(str(from_year)+'-2024_plot.jpg', dpi=300, bbox_inches='tight')

    else:
            
        all_holdings_df['','Year'] = all_holdings_df.index.year
        all_holdings_df['','Month'] = all_holdings_df.index.month

        
        print ('after +YM:',all_holdings_df.columns)
        
        for y in range(from_year,2025):
            print (y,':\n\n')
            
            # get data year by year
            startdate=str(y)+'-01-01'
            all_holdings_current_year_df = all_holdings_df[all_holdings_df['Year']==y]
            print(all_holdings_df)
            input()
            # all_holdings_df=get_tickers_price(current_year_holdings['symbol'],start=startdate,end=enddate)
            # all_holdings_df.to_csv(str(y)+'_original_df.csv')
            # get stock data from all_holdings_df for this year's holdings
            current_year_stock_list=(df['symbol'].loc[df['ipoyear'].astype(str)<=str(from_year)])
            print ('all_holdings_current_year_df\n',all_holdings_current_year_df.columns)
            print('current_year_stock_list\n',current_year_stock_list)
            available_symbols = list(filter(lambda col: (col in all_holdings_current_year_df.columns), current_year_stock_list.to_list())) 
            print ('available_symbols\n',available_symbols)
            current_year_stock_list=available_symbols+['Month']

            # current_year_stock_list=(current_year_stock_list.to_list())+['Month']
            current_year_holdings=all_holdings_current_year_df[current_year_stock_list]
            # all_holdings_df=get_tickers_price(current_year_holdings['symbol'],start=startdate,end=enddate)
        
            print(current_year_holdings)
            input()
            # Get the first trading date of each month
            # normalized using first date of each year
            # normalized_df = all_holdings_current_year_df.copy()
            new_df = pd.DataFrame()
            for q in range(1,13,3): # lets work on Q1-Q4
                # try:
                #     first_trading_dates = current_year_holdings.index.get_loc(current_year_holdings[current_year_holdings['Month']==q].index[0])
                # except: # if no data , proceed with existing
                #     break
                # print(q,':',first_trading_dates)
                normalized_df = current_year_holdings[(current_year_holdings['Month']>=q) & (current_year_holdings['Month']<= q+2)].apply(lambda x: (x/x.iloc[0]-1)*100)
                # print('quarter Q'+str(q)+'\n',normalized_df)
                new_df=pd.concat([new_df,normalized_df])
                
            print(new_df.columns)
            # new_df=new_df.drop(columns=['Month'])
            
# =============================================================================
#             first_trading_dates = all_holdings_current_year_df.index.get_loc(all_holdings_current_year_df[all_holdings_current_year_df['Month']==4].index[0])
#             print(first_trading_dates)
#             # normalized_df = normalized_df[normalized_df['Month']>=4 & normalized_df['Month']<=6].apply(lambda x: (x/x.loc[x.inde]-1)*100)
#             # Q3
#             first_trading_dates = all_holdings_current_year_df.index.get_loc(all_holdings_current_year_df[all_holdings_current_year_df['Month']==7].index[0])
#             print(first_trading_dates)
#             # normalized_df = normalized_df[normalized_df['Month']>=7 & normalized_df['Month']<=9].apply(lambda x: (x/x.iloc[0]-1)*100)
#             # Q4
#             first_trading_dates = all_holdings_current_year_df.index.get_loc(all_holdings_current_year_df[all_holdings_current_year_df['Month']==10].index[0])
#             print(first_trading_dates)
#             # normalized_df = normalized_df[normalized_df['Month']>=10 & normalized_df['Month']<=12].apply(lambda x: (x/x.iloc[0]-1)*100)
# =============================================================================
                        
            
            new_df.replace([np.inf, -np.inf], np.nan, inplace=True)
            # msi.dropna(inplace=True)

            
            new_df.to_csv(str(y)+'_normalized_df.csv')
            fig=plot_qtr_chart(new_df,y)
            fig.savefig(str(y)+'_plot.jpg', dpi=300, bbox_inches='tight')



def stock_52week_heatmap(_symbols_list, _portfolio_data_file='', _sortheatmap=True, _tickerdata=pd.DataFrame(), _portfolio_data=pd.DataFrame(), _imagefilename='', _savetofile=True):
    # define for heatmap MA range
    # ['SYMBOL', 'NAME', 'LASTSALE', 'NETCHANGE', 'PCTCHANGE', 'VOLUME', 'MARKETCAP', 'COUNTRY', 'IPOYEAR', 'INDUSTRY', 'SECTOR', 'URL']
    MA50_LABEL = 'MA50'
    MA100_LABEL = 'MA100'
    MA250_LABEL = 'MA250'
    ABOVE_MA50 = 'aboveMA50'
    ABOVE_MA100 = 'aboveMA100'
    ABOVE_MA250 = 'aboveMA250'
    MA50 = 50
    MA100 = 100
    MA250 = 250
    
    # plot reference:
    # https://www.machinelearningplus.com/plots/python-scatter-plot/
    # symbols = []
    print('CALLING stock_52week_heatmap')
    print(_symbols_list)

    df=get_tickers_price(_symbols_list)#,_start_date,_end_date)
 
    for symbol in _symbols_list:
        df[symbol+MA50_LABEL] = df[symbol].ewm(span=50, adjust=False).mean()
        df[symbol+MA100_LABEL] = df[symbol].ewm(span=100, adjust=False).mean()
        df[symbol+MA250_LABEL] = df[symbol].ewm(span=250, adjust=False).mean()
    
    
    df[symbol+ABOVE_MA100]=df[symbol]/df[symbol+MA100_LABEL]
    df[symbol+ABOVE_MA250]=df[symbol]/df[symbol+MA250_LABEL]
    df['highrunner']=df[symbol+ABOVE_MA100]/df[symbol+ABOVE_MA250]
    df.fillna(0)
    df=df.reset_index()
    # print(_symbols_list)
    list_of_symbols = ', '.join(f"'{item}'" for item in _symbols_list)

    print(list_of_symbols)

    df1 = df['Date', 'highrunner', list_of_symbols.replace('"',''), symbol+ABOVE_MA100, symbol+ABOVE_MA250]

    plt.style.use('ggplot')

    # setup a 4 x 1 figure with ration 3,1,1,1 mainly for price
    # grid = {'height_ratios':[3,1,1]}
    # use 4 rows
    fig, axes = plt.subplots(nrows=1, ncols=1, figsize=(10, 6), sharex=True)
    ###############
    # Create a figure with 6 plot areas
    plt.rcParams.update({'figure.figsize': (10, 6), 'figure.dpi': 100})

    # df_last['scaled'] = ((max(df_last['Close'])-df_last['Close'])/ (df_last['Close']-min(df_last['Close'])))*0.01
    # scaler = MinMaxScaler()
    # df_last['scaled'] = scaler.fit_transform(df_last['Close'])
    # scatter=plt.scatter(df_last[ABOVE_MA100], df_last[ABOVE_MA250], label=df_last['Symbol'],
    #            s=df_last['Close'], c=df_last['highrunner'], cmap='Spectral')

    plt.scatter(df_last[ABOVE_MA100], df_last[ABOVE_MA250], label=df_last['Symbol'],
                s=200, c=df_last['highrunner'], cmap='Spectral')

    # plt.legend(loc='lower left', numpoints=1, ncol=10, fontsize=4)
    # plt.legend(handles=scatter.legend_elements()[0], labels=df_last['Symbol'])

    plt.colorbar()
    plt.xlim([chartminX, chartmaxX])
    plt.ylim([chartminY, chartmaxY])
    plt.title('Moving Average for '+exchange.upper() + ' ' +
              df_last['Date'].iloc[0])  # .strftime("%Y-%m-%d"))
    plt.xlabel('X - MA50')
    plt.ylabel('Y - MA250')

    Q1x = (chartminX+1)/2
    Q2x = (chartminX+1)/2
    Q3x = (chartmaxX+1)/2
    Q4x = (chartmaxX+1)/2
    Q1y = (chartminY+1)/2
    Q2y = (chartmaxY+1)/2
    Q3y = (chartminY+1)/2
    Q4y = (chartmaxY+1)/2
    if _DEBUG_:
        print('Qx:', Q1x, Q2x, Q3x, Q4x)
        print('Qy:', Q1y, Q2y, Q3y, Q4y)

    plt.text(x=Q4x, y=Q4y, s="Bullish", alpha=0.7, fontsize=14, color='green')
    plt.text(x=Q3x, y=Q3y, s="Slightly\nBull",
             alpha=0.7, fontsize=14, color='darkgreen')
    plt.text(x=Q2x, y=Q2y, s="Slightly\nBear",
             alpha=0.7, fontsize=14, color='brown')
    plt.text(x=Q1x, y=Q1y, s="Bearish", alpha=0.7, fontsize=14, color='red')
    # Benchmark Mean values
    plt.axhline(y=1, color='grey', linestyle='--', linewidth=1)
    plt.axvline(x=1, color='grey', linestyle='--', linewidth=1)

    # plt.legend()
    # if len(pd.unique(df['Symbol']))<100:

    # label each stock
    for i, txt in enumerate(df_last['Symbol']):
        # if (len(df_last) < 50 or
        if (len(pd.unique(df_last['Symbol'])) < 50 or
           df_last[ABOVE_MA100].iloc[i] > np.percentile(df_last[ABOVE_MA100], 95) or
            df_last[ABOVE_MA100].iloc[i] < np.percentile(df_last[ABOVE_MA100], 5) or
            df_last[ABOVE_MA250].iloc[i] > np.percentile(df_last[ABOVE_MA250], 95) or
                df_last[ABOVE_MA250].iloc[i] < np.percentile(df_last[ABOVE_MA250], 5)):   # mark those stand out top 10%
            axes.annotate(
                txt, (df_last[ABOVE_MA100].iloc[i], df_last[ABOVE_MA250].iloc[i]), fontsize=6)
    plt.tight_layout()
    plt.show()
    # use 3 rows in chart
    # fig, ax = plt.subplots(nrows=1, ncols=1,figsize=(10, 6),sharex=True)

    # plt.yticks(rotation=0)
    # plt.xticks(rotation=90)
    # ax.tick_params(labelsize= 40 / np.sqrt(len(corr_df)))
    # ax.scatter(df_last[ABOVE_MA100],df_last[ABOVE_MA250], c=df_last['highrunner'], label=df_last['Symbol'],s=50,marker="x",zorder=5)
    # plt.gray()

    fig.tight_layout()
    # plt.show()
    if _savetofile:
        if _imagefilename:
            fn = _imagefilename
        else:
            fn = imgfilename+'_'+todaystr+'_MA.jpg'
        print('Saving 52wk plot to:', fn)

        fig.savefig(fn, dpi=200, bbox_inches='tight')

    # else:  # save to memory and return
    buf = io.BytesIO()
    fig.savefig(buf)
    buf.seek(0)
    img = Image.open(buf)
    return img


def stock_corel_heatmap(_symbols_list, _start_date, _end_date, _sortheatmap=True): 
                        #_tickerdatafile='', _imagefilename='', _sortheatmap=True, _savetofile=True):

    print(_symbols_list)

    df=get_tickers_price(_symbols_list,_start_date,_end_date)
    # _symbols_list.drop_duplicates(keep='first', inplace=True)
    # imgfilename = imgdir+'/'+exchange
    # csvfilename = corrdir+'/'+exchange

    # symbols = []
    # print('requesting tickers from yahoo :', exchange)
    
    df_pivot=df
    
    if (_sortheatmap):
        sum_corr = df_pivot.corr().sum().sort_values(ascending=True).index.values
        corr_df = df_pivot[sum_corr].corr(method='pearson')
    else:
        corr_df = df_pivot.corr(method='pearson')

    
    # reset symbol as index (rather than 0-X)
    corr_df.head().reset_index()
    # corr_df = corr_df.rename_axis(None, axis=1)
    # corr_df=corr_df.reset_index(level=[0,1])
    # 
    # corr_df=corr_df.sort_values()

    # del corr_df.index.name
    # corr_df.head(10)
    # take the bottom triangle since it repeats itself
    mask = np.zeros_like(corr_df)
    mask[np.triu_indices_from(mask)] = True
    # generate plot

    ax = plt.axes()
    heatmaptitle = 'Correlation of stock under ' + \
       '['+_end_date  # .strftime("%Y-%m-%d")+']'
    ax.set_title(heatmaptitle, fontsize=80 / np.sqrt(len(corr_df)))
    # plt.figure(figsize = (16,16))
    seaborn.set(font_scale=0.5)
    
    # remove multi index and multi column header
    corr_df=corr_df.droplevel(0, axis=1) 
    corr_df=corr_df.droplevel(0, axis=0) 
    corr_df.to_csv('corr_df.csv')

    print (corr_df.index)
    print (corr_df, corr_df.columns)
    
    # corr_df.sort_values(by=['symbol'], ascending=_sortheatmap)
    # print (len(df['Symbol']))
    annot_if_reasonable = len(pd.unique(_symbols_list)) < 51

    sbfig = seaborn.heatmap(corr_df, cmap='RdYlGn',
                            vmax=1.0, vmin=-1.0, center=0, mask=mask,
                            linewidths=0.2, annot=annot_if_reasonable,
                            xticklabels=True, yticklabels=True, cbar=False,
                            annot_kws={"size": 40 / np.sqrt(len(corr_df))}
                            )

    # SAVE correlation to CSV file
    corr_df.to_csv('heatmap'+_end_date+'.csv', index=False, header=True)

    fig = sbfig.get_figure()
    figsize = fig.get_size_inches()
    fig.set_size_inches(figsize*2)

    plt.yticks(rotation=0)
    plt.xticks(rotation=90)
    ax.tick_params(labelsize=40 / np.sqrt(len(corr_df)))
    plt.tight_layout()
    plt.show()

    
    fig.savefig('heatmap_'+_end_date+'.jpg', dpi=300, bbox_inches='tight')
    return

    # for other purpose:    
    buf = io.BytesIO()
    fig.savefig(buf)
    buf.seek(0)
    img = Image.open(buf)
    return img


def main():
    # Get QQQ holdings for each year from 2000 to 2024
    startdate='2000-01-01'
    enddate= dt.now().strftime("%Y-%m-%d")
    
    holdings = pd.DataFrame(get_nasdaq_holdings(FROM_YEAR))
    print(holdings)

    # holdings=['aapl','goog','meta','amzn','nvda','ai','slb','inve','c','h','pltr','tsla','nflx','baba']
    # holdings=[elem.upper() for elem in holdings ]
    
    # stock_52week_heatmap(holdings)

    # stock_corel_heatmap(holdings,startdate,enddate)
    # stock_corel_heatmap(holdings['symbol'].to_list(),startdate,enddate)
    
    # print (holdings)
    # holdings.to_csv('all_holdings.csv')
    # holdings=pd.DataFrame()
    # holdings=pd.read_csv('./all_holdings.csv')
    plot_holdings_by_year(holdings, int(FROM_YEAR))
    # print(f"QQQ Holdings in {YEAR}:")
        # for holding in holdings:
        #     print(f"{holding[0]} - {holding[1]}")


if __name__ == "__main__":
    main()
