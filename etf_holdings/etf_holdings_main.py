#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb  6 23:43:04 2024
https://medium.com/tech-talk-tank/this-python-codes-can-retreive-all-stock-holdings-under-the-etf-and-why-this-is-interesting-81b9a5975342
@author: michaelwai
"""

import requests
import re
import pandas as pd
import numpy as np
import math
import time

from lxml import html
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC



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

    df_stocklist.to_csv('./etflist1.csv')

    df_stocklist=df_stocklist.dropna(subset=['Symbol'])
    df_stocklist=df_stocklist.drop_duplicates(subset=['Symbol'])
    df_stocklist=df_stocklist.sort_values(by=['Symbol']).reset_index(drop=True)
    df_stocklist.to_csv('./etflist.csv')
    return df_stocklist

def main2(symbol_list): #scrap zacks
    header = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36 '}

    if type(symbol_list) != list:
        symbol_list=[symbol_list]

    etf_url='https://www.zacks.com/funds/etf/{}/holding'
    mutual_fund_url="https://www.zacks.com/funds/mutual-fund/quote/{}/holding"

    #which url to use?
    url=etf_url

    df_stocklist=pd.DataFrame()
    with requests.Session() as req:
        req.headers.update(header)
        for s in symbol_list:
            r = req.get(url.format(s))
            print (url.format(s))
            etfholdings = re.findall(r'etf\\\/(.*?)\\', r.text)
            print ('***** ETF: ',s,'holds:\n',etfholdings)
            etfholdingsname = re.findall(r'<\\\/span><\\\/span><\\\/a>",(.*?), "<a class=\\\"report_document newwin\\', r.text)
            # etfdata = re.findall(r'\[ \"(.*?)\", \"<button class=\\\"modal_external appear-on-focus\\\" ',r.text)
            etfdata = re.findall(r'[ \"(.*?)\"',r.text)
            print(etfdata)
            # print(etfholdingsname)
            print (len(etfholdings))
            print (len(etfholdingsname))

            df=pd.DataFrame(
                {
                    'Symbol':etfholdings,
                    'Name':etfholdingsname
                })

            print (df)
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

def main(url):
    with requests.Session() as req:
        req.headers.update(headers)
        for s in symbol_list:
            r = req.get(url.format(s))
            print(f"Extracting: {r.url}")
            etfholdings = re.findall(r'etf\\\/(.*?)\\', r.text)
            print(etfholdings)
            etf_stock_details_list = re.findall(r'<\\\/span><\\\/span><\\\/a>",(.*?), "<a class=\\\"report_document newwin\\', r.text)
            print(etf_stock_details_list)

get_holdings(['TLT'])

# main(ETF)
# main(mutual_fund)

