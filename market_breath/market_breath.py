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

from lxml import html
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time
import yfinance as yf
# from pandas_datareader import data as pdr
# from yahooquery import Ticker
pd.options.mode.chained_assignment = None  # default='warn'

def plot_trading_inidicator(ax, df):
    df['ema1'] = df['Close'].ewm(span=30, adjust=False).mean()
    df['ema2'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['ema3'] = df['Close'].ewm(span=80, adjust=False).mean()
    df['ema4'] = df['Close'].ewm(span=100, adjust=False).mean()

    ax.plot(df['Date'],df['ema1'],color='orange',linewidth=0.5, alpha=0.5)
    ax.plot(df['Date'],df['ema2'],color='blue',linewidth=0.5, alpha=0.5)
    ax.plot(df['Date'],df['ema3'],color='violet',linewidth=0.5, alpha=0.5)
    ax.plot(df['Date'],df['ema4'],color='red',linewidth=0.5, alpha=0.5)

    return ax

def get_stock_breath(s,df):
    df['breath']=(df['price_y'] - df['TL-2SD']) / (df['TL+2SD']- df['TL-2SD'])  
    print (s,'\n',df['breath'].tail())
    # input('1.cont?')
    return df
    
def check_stock_log_position(s,df):
    # print (s,100*round(((df['price_y'].iloc[-1]-df['TL-2SD'].iloc[-1]) / (df['TL+2SD'].iloc[-1]-df['TL-2SD'].iloc[-1])),2),'%')
    return (df['price_y'].iloc[-1] - df['TL-2SD'].iloc[-1]) / (df['TL+2SD'].iloc[-1] - df['TL-2SD'].iloc[-1]) 


def Logarithmic_regression(df):
# =============================================================================
#     df = df[df['Close'].notna()]
#     df['price_y']=np.log(df['Close']) # using natural log of stock price
# 
#     df['x']=np.arange(len(df)) #fill index x column with 1,2,3...n
#     try:
#         b,a =np.polyfit(df['x'],df['price_y'],1)
#     except Exception as e:
#         print('****** ERROR: setting b,a to 0')
#         b,a=0,0
#         
# 
#     df['priceTL']=b*df['x'] + a
#     df['y-TL']=df['price_y']-df['priceTL']
#     df['SD']=np.std(df['y-TL'])
#     df['TL-2SD']=df['priceTL']-2*df['SD']
#     df['TL-SD']=df['priceTL']-df['SD']
#     df['TL+SD']=df['priceTL']+df['SD']
#     df['TL+2SD']=df['priceTL']+2*df['SD']
# 
#     return df
# =============================================================================

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

def plot_log_chart(ax,df):

    RAINBOWCOLOR1='hotpink'
    RAINBOWCOLOR2='orange'
    RAINBOWCOLOR3='gold'
    RAINBOWCOLOR4='yellowgreen'
    RAINBOWCOLOR5='lightgreen'


    # fig, (ax1, ax2) = plt.subplots(dpi=600,nrows=2, sharex=True)

    # plotting stock price on log regression
    ax.plot(df['Date'],df['price_y'],color='black',linewidth=0.5)

    # plotting stock price on log regression
    # ax.plot(df['Date'],df['TL+2SD'],color=RAINBOWCOLOR1, linewidth=0.5)
    # ax.plot(df['Date'],df['TL+SD'],color=RAINBOWCOLOR2,  linewidth=0.5)
    # ax.plot(df['Date'],df['priceTL'],color=RAINBOWCOLOR3,linewidth=0.5)
    # ax.plot(df['Date'],df['TL-SD'], color=RAINBOWCOLOR4, linewidth=0.5)
    # ax.plot(df['Date'],df['TL-2SD'],color=RAINBOWCOLOR5, linewidth=0.5)
    
    ax.plot(df['Date'],df['TL+2SD'],color='white', linewidth=0.5)
    ax.plot(df['Date'],df['TL+SD'],color='white',  linewidth=0.5)
    ax.plot(df['Date'],df['priceTL'],color='white',linewidth=0.5)
    ax.plot(df['Date'],df['TL-SD'], color='white', linewidth=0.5)
    ax.plot(df['Date'],df['TL-2SD'],color='white', linewidth=0.5)

    ax.fill_between(df['Date'],df['TL+2SD'], df['TL+SD'],facecolor=RAINBOWCOLOR2,  alpha=0.6,edgecolor=None,linewidth=0)
    ax.fill_between(df['Date'],df['TL+SD'], df['priceTL'],facecolor=RAINBOWCOLOR3, alpha=0.6,edgecolor=None,linewidth=0)
    ax.fill_between(df['Date'],df['priceTL'], df['TL-SD'],facecolor=RAINBOWCOLOR4, alpha=0.6,edgecolor=None,linewidth=0)
    ax.fill_between(df['Date'],df['TL-SD'], df['TL-2SD'],facecolor=RAINBOWCOLOR5,  alpha=0.6,edgecolor=None,linewidth=0)
    
    RAINBOWCOLOR1='hotpink'
    RAINBOWCOLOR2='orange'
    RAINBOWCOLOR3='gold'
    RAINBOWCOLOR4='yellowgreen'
    RAINBOWCOLOR5='lightgreen'
    
    facecolor='black'
    if df['price_y'].iloc[-1]>df['TL+2SD'].iloc[-1]: facecolor='darkturquoise'#'dimgray'
    elif df['price_y'].iloc[-1]>df['TL+SD'].iloc[-1]: facecolor='skyblue'#'gray'
    elif df['price_y'].iloc[-1]>df['priceTL'].iloc[-1]: facecolor='paleturquoise'#'darkgray'
    elif df['price_y'].iloc[-1]>df['TL-SD'].iloc[-1]: facecolor='powderblue'#'silver'
    elif df['price_y'].iloc[-1]>df['TL-2SD'].iloc[-1]: facecolor='silver'#'whitesmoke'
    else: facecolor='whitesmoke'
        
    ax.patch.set_facecolor(facecolor)

    return ax


def get_holdings(symbol_list): #scrape schwab
    if type(symbol_list) != list: #Trust no one , make sure
        symbol_list=[symbol_list]

    header = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36 '}
    etf_url='https://www.schwab.wallst.com/schwab/Prospect/research/etfs/schwabETF/index.asp?type=holdings&symbol={}'

    #which url to use?
    url=etf_url

    option = webdriver.ChromeOptions()
    # option.add_argument("headless") #"start-maximized") #by running the browser in headless mode. Another advantage of this is that tests are executed faster
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),options=option)

    with requests.Session() as req:
        req.headers.update(header)
        for s in symbol_list:

            driver.get(etf_url.format(s))
            element_present = EC.presence_of_element_located((By.XPATH,'//*[@id="content"]/div[1]/h2'))
            WebDriverWait(driver, 60).until(element_present)

            raw_text = driver.find_element(By.XPATH,'//*[@id="content"]/div[1]/h2')
            title = raw_text.text
            df_stocklist=pd.DataFrame()
            df_stocklist.name=title

            # row_data = driver.find_element(By.XPATH,'//*[@id="activeContent"]')
            tree = html.fromstring(driver.page_source)

            try:
                all_list_elements = driver.find_elements(By.XPATH,'//*[@id="PaginationContainer"]')
                totalstocks = re.split('\s',(re.search(r'[0-9]+ matches',all_list_elements[-1].text)).group(0),1)[0]
                numpages = math.ceil(int(totalstocks)/20) #as each page default 20 stocks
                print (title,'\nwe need to scrap %s pages of total %s stocks' % (numpages,totalstocks))
            except Exception as e:
                driver.close()
                print ('error:',str(e))

            page_output=[]
            page_elements = driver.find_elements(By.XPATH,'//*[@id="PaginationContainer"]/ul/li')
            # Iterate through the list of elements
            for each_element in page_elements:
                # Extract the text content of each element
                each_element_value = each_element.get_attribute('innerHTML')
                # Add the extracted text content to the page_output list
                page_output.append(each_element_value)

            # Iterate through the pages
            for page_num in range(numpages):
                tree = html.fromstring(driver.page_source)
                symbol_table = driver.find_elements(By.XPATH,'//*[@id="tthHoldingsTbody"]/tr/td')

                numrow=int(len(symbol_table)/5)
                symbol=[]
                name=[]
                weight=[]
                held=[]
                value=[]

                for i in range(numrow):
                    symbol.append(symbol_table[i*5+0].text)
                    name.append(symbol_table[i*5+1].text)
                    weight.append(symbol_table[i*5+2].text)
                    held.append(symbol_table[i*5+3].text)
                    value.append(symbol_table[i*5+4].text)

                # print('page %s/%s' %(page_num,numpages), '=\n',symbol)
                df=pd.DataFrame(
                        {
                            'Symbol':symbol,
                            'Name':name,
                            'Weight':weight,
                            'Held':held,
                            'Value':value
                        })
                df_stocklist = pd.concat([df_stocklist,df])


                # go to next page
                try:
                # Extract the data from the current page
                # page_output = extract_page_data(driver)
                # Add the data to the final_out list as a dictionary with the page number as the key
                # final_out.append({
                #     page_num: page_output
                # })
                # Locate the "Next" button on the webpage and click it to navigate to the next page
                    xpath_value='//*[@id="PaginationContainer"]/ul[2]/li[%s]'%(int(page_num%5)+3)
                    # print('xpath_value=',page_num,': ',xpath_value)
                    next_page = driver.find_element(By.XPATH, xpath_value).click()
                    element_present = EC.presence_of_element_located((By.ID, 'PaginationContainer'))
                    WebDriverWait(driver, 5).until(element_present)
                    page_elements = driver.find_elements(By.XPATH,'//*[@id="PaginationContainer"]/ul/li')

                except Exception as e:
                    print ('skippig xpath_value=',xpath_value,' with error:',str(e))
                    pass
                time.sleep(2)
                filename='./ETF_'+s+'.csv'
            df_stocklist.to_csv(filename,header=title,index=False)
            print (title,'\n',df_stocklist)

    driver.quit()

    df_stocklist.to_csv('./etflist1.csv',index=False)

    df_stocklist=df_stocklist.dropna(subset=['Symbol'])
    df_stocklist=df_stocklist.loc[df_stocklist['Symbol']!='--']
    df_stocklist=df_stocklist.drop_duplicates(subset=['Symbol'])
    df_stocklist=df_stocklist.sort_values(by=['Symbol']).reset_index(drop=True)
    df_stocklist.to_csv('./etflist.csv',index=False)
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

def stock_screener(link='',symbol_list=[],startdate='2020-01-01',charttitle='', compare_stock=None):


    if link!='':
        symbol_list =read_html_table(link)

    print ('stock list retreived: ',symbol_list)

    if symbol_list.empty:
        raise RuntimeError('stock list is empty?!')

    symbol_list.to_csv('./'+compare_stock+'_stocklist.csv')


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
    

    total_stock_log_pos = 0
    empty_stock = 0
    stock_indicator_df=pd.DataFrame()
    stock_indicator_df['Date']=all_stock_data['Date']
    stock_indicator_df['breath']=0

    
    for i,s in enumerate(symbol_list.Symbol): # iterate for every stock indices

        tickerDf=pd.DataFrame()
        ax = axes[int(i%figrow),int(i/figrow)]

        tickerDf['Date']=all_stock_data['Date']
        tickerDf['Close']=all_stock_data['Close'][s]
        tickerDf = tickerDf[tickerDf['Close'].notna()]
        tickerDf = tickerDf.replace(np.nan,0)

        tickerDf.to_csv('./tmp/'+s+'.csv',index=False)
        

        """                                           """
        """ +------- SUBPLOT CHART TITLE HERE ------+ """
        """                                           """
        company_name_len=16

        if 'Company Name' in symbol_list.columns:
            title_name=(symbol_list[symbol_list['Symbol']==s].iloc[0])['Company Name']
        else:
            title_name=(symbol_list[symbol_list['Symbol']==s].iloc[0])['Name']
        title_name=title_name[:company_name_len]

        titlecolor='black'
        facecolor='white'


        """ Your trading analysis and Plot here """
        
        # =============================================================================
        """         LOG REGRESSION PLOT and STOCK BREATH     """
        # =============================================================================
        if len(tickerDf)==0 or tickerDf.empty:
            print (s, ' is empty, skipping...')
            empty_stock += 1
            continue
        else:
            
            tickerDf=Logarithmic_regression(tickerDf)
           
            ax=plot_log_chart(ax, tickerDf)
            total_stock_log_pos+=check_stock_log_position(s,tickerDf)
            stock_breath_df = get_stock_breath(s,tickerDf)
            

            stock_indicator_df['breath'] += stock_breath_df['breath']
            stock_indicator_df.to_csv('./breath/'+s+'_breath.csv')
        
        """ Moving average plot """
        # ax=plot_trading_inidicator(ax, tickerDf)
        # ax.plot(tickerDf['Date'],tickerDf['Close'],color='black',linewidth=0.6, alpha=1)
        """ """
        
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
            # facecolor='mistyrose'


        # use facecolor to indicate Up/Down for easy visualization
        # ax.patch.set_facecolor(facecolor)
        # let's beautify the chart a bit
        ax.grid(True, color='gray',linewidth=0.5)
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

    print ('total_stock:',total_stock_log_pos, 'i=', i+1, 'empty=',empty_stock)
    market_breath = (total_stock_log_pos/(i+1-empty_stock))
    stock_indicator_df['Close']=(stock_indicator_df['breath']/(i+1-empty_stock))*100
    fig2, stock_ax = plt.subplots(2,1, dpi=600, sharey=False,sharex=True)
    if (compare_stock):
        compare_stock_df=yf.download(compare_stock,start=startdate,interval='1d').reset_index()
        print(stock_indicator_df,stock_indicator_df.columns)
        
        stock_indicator_df['Date'] = (pd.to_datetime(stock_indicator_df['Date'],utc=True)).dt.date

        
        """ plot the two charts """
        stock_ax[0].plot(compare_stock_df['Date'],compare_stock_df['Close'],linewidth=0.8,alpha=0.8)
        plot_trading_inidicator(stock_ax[0],compare_stock_df)

        stock_ax[1].plot(stock_indicator_df['Date'],stock_indicator_df['Close'],linewidth=0.8,alpha=0.8)
        plot_trading_inidicator(stock_ax[1],stock_indicator_df)
        """ """
        
        stock_ax[1].axhline(80,color='red',linewidth=0.5,alpha=1,zorder=120)
        stock_ax[1].axhline(50,color='black',linewidth=0.5,alpha=1,zorder=120)
        stock_ax[1].axhline(20,color='green',linewidth=0.5,alpha=1,zorder=120)

        stock_ax[0].grid(True, color='silver',linewidth=0.5)
        stock_ax[1].grid(True, color='silver',linewidth=0.5)
        stock_ax[1].set_xticklabels(stock_indicator_df['Date'],rotation=90,fontsize=6)

    plt.subplots_adjust(wspace=0.12, hspace=0.1)

    today=datetime.now().strftime("%Y-%m-%d")
    fig.suptitle(charttitle+'\n'+startdate+'~'+today, fontweight ="bold",y=1, fontsize=dynamic_fontsize)
    fig.tight_layout()
    fig.savefig('./'+compare_stock+'_grid_plot.jpg',dpi=400,bbox_inches='tight')
    fig2.savefig('./'+compare_stock+'_breath.jpg',dpi=400,bbox_inches='tight')

    
    return tickerDf, market_breath



if __name__ == '__main__':
    url='https://finance.yahoo.com/trending-tickers'
    hkurl = 'https://finance.yahoo.com/quote/%5EHSI/components/'
    ARK=['ARKK','ARKW','ARKG','ARKQ','ARKF','ARKX']
    HK=['^HSI']
    US=['QQQ', '']
    startdate='2022-01-01'

    listofEFT=HK
    # stock_screener('https://finance.yahoo.com/trending-tickers',startdate='2022-01-01')
    # stock_screener(url,startdate='2023-01-01')

    # df, breath=stock_screener('', get_holdings(listofEFT) ,startdate=startdate, charttitle=''.join(listofEFT) ,compare_stock=''.join(listofEFT))
    df, breath=stock_screener(hkurl ,startdate=startdate, charttitle=''.join(listofEFT) ,compare_stock=''.join(listofEFT))
    print ('market breath of these stocks are : ',breath*100)
    

# https://www.schwab.wallst.com/schwab/Prospect/research/etfs/schwabETF/index.asp?YYY101_z5K6INmijHlJfnlzwDHOvi/hjoBQ5b+E0TeOoGxn1A7DsA/X/2E43Z8cvZPk2Bq1kYqlVaWSSvG7LA7ia8UkC+dIWy0JMFtSM57akQFVHX7483xVCc/Aopv7kniRT3o2&type=holdings&symbol=EWH


