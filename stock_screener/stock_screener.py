#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep  9 12:06:23 2024

@author: michaelwai
"""

import pandas as pd
import requests
import bs4
import time
import random
import re
import requests


def get_yahoo_cookie():
    cookie = None

    user_agent_key = "User-Agent"
    user_agent_value = "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"

    headers = {user_agent_key: user_agent_value}
    response = requests.get(
        "https://fc.yahoo.com", headers=headers, allow_redirects=True
    )

    if not response.cookies:
        raise Exception("Failed to obtain Yahoo auth cookie.")

    cookie = list(response.cookies)[0]

    return cookie


def get_yahoo_crumb(cookie):
    crumb = None

    user_agent_key = "User-Agent"
    user_agent_value = "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"

    headers = {user_agent_key: user_agent_value}

    crumb_response = requests.get(
        "https://query1.finance.yahoo.com/v1/test/getcrumb",
        headers=headers,
        cookies={cookie.name: cookie.value},
        allow_redirects=True,
    )
    crumb = crumb_response.text

    if crumb is None:
        raise Exception("Failed to retrieve Yahoo crumb.")

    return crumb


# Usage
# cookie = get_yahoo_cookie()
# crumb = get_yahoo_crumb(cookie)

header = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
headers = {
        'User-Agent'      : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36',
        'Accept'          : 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language' : 'en-US,en;q=0.5',
        'DNT'             : '1', # Do Not Track Request Header
        'Connection'      : 'close'
        }
header = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36 '}

url= f'https://finance.yahoo.com/screener/1411f024-fdc9-4835-bcde-25da73ab40a1/'  

# def getCredentials(cookieUrl='https://fc.yahoo.com', crumbUrl=apiBase+'/v1/test/getcrumb'):
def getCredentials(cookieUrl='https://fc.yahoo.com', crumbUrl=url):
  cookie =  requests.get(cookieUrl).cookies
  crumb =  requests.get(url=crumbUrl, cookies=cookie, headers=header).text
  return {'cookie': cookie, 'crumb': crumb}

def quotes(symbols, credentials):
    url = apiBase + '/v7/finance/quote'
    params = {'symbols': symbols, 'crumb': credentials['crumb']}
    # if list of symbols like ['appl','tsla']
    # params = {'symbols': ','.join(symbols), 'crumb': credentials['crumb']}
    for i in range(3): # retry if not getting info
        try:
            # print ('>> getting quote from yfinance:',params)
            response = requests.get(url, params=params, cookies=credentials['cookie'], headers=header)
            # quotes = response.json()['quoteResponse']['result']
            quotes = response.json()['quoteResponse']['result'][0] #assume one symbol
            # print ('>> getting quote from yfinance COMPLETED:')

            break
        except Exception as e:
            print ('retrying:',i,'/3 - ', url, params, str(e))
            time.sleep(1)
    if quotes:
        return quotes

    return None




def get_screener_stock_list():
    
    count=100
    page=0
    url= f'https://finance.yahoo.com/screener/predefined/solid_large_growth_funds/?count={count}&offset={page}'    
    # url = f'https://finance.yahoo.com/screener/1411f024-fdc9-4835-bcde-25da73ab40a1/?count={count}&offset={page}'   
    # url = f'https://finance.yahoo.com/screener/1411f024-fdc9-4835-bcde-25da73ab40a1/?count={count}&offset={page}'  
    
  
    def get_crumb():
        response = requests.get("https://finance.yahoo.com")
        pat = re.compile(r'window\.YAHOO\.context = ({.*?});', re.DOTALL)
        match = re.search(pat, response.text)
        if match:
            js_dict = json.loads(match.group(1))
            return js_dict.get('crumb')
        return None

    get_crumb()

    screen = requests.get(url.format(count=count, page=page*count),  headers=headers)
    
    # screen = requests.get(url.format(count=count, page=page*count), cookies=credentials['cookie'], headers=headers)
    soup = bs4.BeautifulSoup(screen.text,features="lxml")
    # soup = bs4.BeautifulSoup(screen.text,'html.parser')
    # //*[@id="fin-scr-res-table"]/div[1]/div[1]/span[2]
    with open("/Users/michaelwai/Downloads/output1.html", "w", encoding='utf-8') as file:
        file.write(str(soup))    

    try:
        print(soup.find_all('span', {'class': 'Mstart(15px) Fw(500) Fz(s)'})[-1].text)
        total = int(soup.find_all('span', {'class': 'Mstart(15px) Fw(500) Fz(s)'})[-1].text.split()[-2])
        print(total)
        pages = int(total/count)+1
        print(f'total stocks = {total} and pages = {pages}')
        data = []
        
        
        for page in range(0, pages, 1):
            print(f'reading page {page}...')
            screen = requests.get(url.format(count=count, page=page*count), headers=headers).text
            tables = pd.read_html(screen)
            tables = tables[-1]
            tables.columns =  dict(tables.iloc[0]).keys()
            tables = tables[1:]
            data.append(tables)
            time.sleep(random.random())
        return pd.concat(data).reset_index(drop=True).rename_axis(columns=None)
    except Exception as e:
         print('Maybe you need to turn on VPN to U.S. as error : ', str(e))


# credentials = getCredentials()

df = get_screener_stock_list()
print(df)
print(df.columns)
print('stock list:\n',df['Symbol'])