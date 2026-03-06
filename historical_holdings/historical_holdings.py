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
warnings.simplefilter(action="ignore", category=FutureWarning)

FROM_YEAR='2000'
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

def get_tickers_price(symbols,start='1998-01-01',end='2024-04-01'):

    # tickers = Ticker(symbols, asynchronous=True)
    # df_ticker = tickers.history(start=start,end=end)
    time.sleep(1)
    symbols=symbols.dropna()
    
    # print(symbols.to_list(), start, end)

    df_ticker = (yf.download(symbols.to_list(),start=start,end=end)).reset_index() #download all symbols at once
    # df_ticker.reset_index(inplace=True)
    df_ticker = df_ticker.set_index('Date')

    print('df_ticker=\n',df_ticker)
    
    set(df_ticker.columns.get_level_values(0))
    
    df_pivot = df_ticker['Close'].bfill()

    # df_pivot = df_ticker.reset_index().pivot(index='Date',
    #                     columns='Symbol', values='Close')
    df_pivot.index = pd.to_datetime(df_pivot.index, utc=True)
    df_pivot=df_pivot.groupby('Date').sum()
    df_pivot.to_csv('df_pivot.csv')
    df_pivot.reset_index(inplace=True)
    df_pivot['Date'] = pd.to_datetime(df_pivot['Date']).dt.strftime('%Y/%m/%d')
    df_pivot = df_pivot.set_index('Date')
    # df_pivot.index = df_pivot['Date'].strftime('%Y/%m/%d')
    df_pivot.to_csv('df_pivot.csv')
    
    return df_pivot


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
    return holdings
    # return [(stock['symbol'], stock['name']) for stock in holdings]

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
    
    all_holdings_df=get_tickers_price(df['symbol'],start=startdate,end=enddate)
     
    print (all_holdings_df.columns,all_holdings_df)
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
            
        all_holdings_df['Year'] = all_holdings_df.index.year
        all_holdings_df['Month'] = all_holdings_df.index.month
      
        for y in range(from_year,2025):
            print (y,':')
            
            # get data year by year
            startdate=str(y)+'-01-01'
            all_holdings_current_year_df = all_holdings_df[all_holdings_df['Year']==y]
            
            # all_holdings_df=get_tickers_price(current_year_holdings['symbol'],start=startdate,end=enddate)
            # all_holdings_df.to_csv(str(y)+'_original_df.csv')
            # get stock data from all_holdings_df for this year's holdings
            current_year_stock_list=(df['symbol'].loc[df['ipoyear'].astype(str)<=str(from_year)])
            current_year_stock_list=(current_year_stock_list.to_list())+['Month']
            current_year_holdings=all_holdings_current_year_df[current_year_stock_list]
            # all_holdings_df=get_tickers_price(current_year_holdings['symbol'],start=startdate,end=enddate)
        
            # Get the first trading date of each month
            # normalized using first date of each year
            # normalized_df = all_holdings_current_year_df.copy()
            new_df = pd.DataFrame()
            for q in range(1,13,3): # lets work on Q1-Q4
                try:
                    first_trading_dates = current_year_holdings.index.get_loc(current_year_holdings[current_year_holdings['Month']==q].index[0])
                except: # if no data , proceed with existing
                    break
                # print(q,':',first_trading_dates)
                normalized_df = current_year_holdings[(current_year_holdings['Month']>=q) & (current_year_holdings['Month']<= q+2)].apply(lambda x: (x/x.iloc[0]-1)*100)
                # print('quarter Q'+str(q)+'\n',normalized_df)
                new_df=pd.concat([new_df,normalized_df])
                
            new_df=new_df.drop(columns=['Month'])
            
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




def main():
    # Get QQQ holdings for each year from 2000 to 2024
    holdings = pd.DataFrame(get_nasdaq_holdings(FROM_YEAR))
    
    # print (holdings)
    holdings.to_csv('all_holdings.csv')
    # holdings=pd.DataFrame()
    # holdings=pd.read_csv('./all_holdings.csv')
    plot_holdings_by_year(holdings, int(FROM_YEAR))
    # print(f"QQQ Holdings in {YEAR}:")
        # for holding in holdings:
        #     print(f"{holding[0]} - {holding[1]}")


if __name__ == "__main__":
    main()
