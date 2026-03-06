#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 30 00:01:01 2021
https://medium.com/tech-talk-tank/finding-intrinsic-value-on-yahoo-finance-screener-stocks-with-python-693d8b649c6c
reference:Building an Intrinsic Value Calculator With Python, Julian Marx

https://medium.com/analytics-vidhya/building-an-intrinsic-value-calculator-with-python-7986833962cd
http://kaushik316-blog.logdown.com/posts/1651749-stock-valuation-with-python

@author: michael.wai
"""
import random # just to use it to pick a request header
import yfinance as yf # yahoo finance
import requests # web requests handling
import pandas as pd # DataFrame  and read_html
from bs4 import BeautifulSoup as bs # for web scrapping
import datetime
import time
from io import StringIO
import sys
from numerize_denumerize import numerize, denumerize
# pip install py3-tts

'''---------- // Hard-coded variables below // ----------'''


timespan = 300 #timespan for the equity beta calculation
market_risk_float = 0.08 # assume risky asset at 8% return
long_term_growth = 0.0 #assume asset at x% growth, will try to get from yahoo analysis
debt_return = 0.05 # long term debt return at 1% rate
tax_rate = 0.21 #year 2023


header = {
'User-Agent'      : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36',
'Accept'          : 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
'Accept-Language' : 'en-US,en;q=0.5',
'DNT'             : '1', # Do Not Track Request Header
'Connection'      : 'close'
}

def _yfTicker(symbol):
    import requests
    apiBase = 'https://query2.finance.yahoo.com'

# =============================================================================
#     header = {
#       "User-Agent":
#       "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"
#     }
#
# =============================================================================
    def getCredentials(cookieUrl='https://fc.yahoo.com', crumbUrl=apiBase+'/v1/test/getcrumb'):
      cookie = requests.get(cookieUrl).cookies
      crumb = requests.get(url=crumbUrl, cookies=cookie, headers=header).text
      return {'cookie': cookie, 'crumb': crumb}

    def quote(symbols, credentials):
        url = apiBase + '/v7/finance/quote'
        params = {'symbols': symbols, 'crumb': credentials['crumb']}
        # if list of symbols like ['appl','tsla']
        # params = {'symbols': ','.join(symbols), 'crumb': credentials['crumb']}

        response = requests.get(url, params=params, cookies=credentials['cookie'], headers=header)
        # quotes = response.json()['quoteResponse']['result']
        quotes = response.json()['quoteResponse']['result'][0] #assume one symbol

        return quotes

    credentials = getCredentials()
    ticker_info={'info':quote(symbol,credentials)}

    return ticker_info['info']

def calc_intrinsic_value(symbol):

    # Step 2: Retrieve the stock data
    stock = yf.Ticker(symbol)
    
    # Step 3: Get the enterprise value, net debt, total cash value, and outstanding shares
   
    short_name = stock.info.get('shortName', 'N/A')
    price = stock.info.get('regularMarketPrice', 'N/A')
    if price == 'N/A':
        price = stock.info.get('previousClose', 'N/A')
    enterprise_value = stock.info.get('enterpriseValue', 0)
    total_debt = stock.info.get('totalDebt', 0)
    total_cash = stock.info.get('totalCash', 0)
    outstanding_shares = stock.info.get('sharesOutstanding', 1)  # Avoid division by zero
    
    # Calculate net debt (total debt minus total cash)
    net_debt = total_debt - total_cash
    
    # Step 4: Calculate equity value
    equity_value = enterprise_value - net_debt + total_cash
    
    # Step 5: Calculate intrinsic price
    intrinsic_price = equity_value / outstanding_shares
    
    intrinsic_value_text = \
        short_name+f' ({symbol})\n' +\
        '(A) enterprise_value='+str(numerize.numerize(enterprise_value))+'\n'\
        '(B) total_debt='+str(numerize.numerize(total_debt))+'\n'\
        '(C) total_cash='+str(numerize.numerize(total_cash))+'\n'\
        '(D) outstanding_shares='+str(numerize.numerize(outstanding_shares))+'\n'\
        '(E) net debt (B-C)='+str(numerize.numerize(net_debt))+'\n'\
        '(F) equity_value (D-E+C)='+str(numerize.numerize(equity_value))+'\n\n'\
        '(G) intrinsic_price (F/D)='+str(round(intrinsic_price,2))+'\n'\
        'Price='+str(round(price,2))

    print(intrinsic_value_text)
    return symbol, short_name, round(intrinsic_price,3), price, intrinsic_value_text

    

def calc_intrinsic_value_old_version(symbol):

    '''----- // I. Financial Information from Yahoo Finance // -----'''

    income_statement_url=f'https://finance.yahoo.com/quote/{symbol}/financials?p={symbol}'
    balance_sheet_url=f'https://finance.yahoo.com/quote/{symbol}/balance-sheet?p={symbol}'
    market_cap_url = f'https://finance.yahoo.com/quote/{symbol}?p={symbol}'
    analyse_url = f'https://finance.yahoo.com/quote/{symbol}/analysis?p={symbol}'
    statistics_url = f'https://finance.yahoo.com/quote/{symbol}/key-statistics?p={symbol}'
       # https://finance.yahoo.com/quote/AAPL/analysis?p=AAPL

    # import tdfbacktester as bt
    tickerinfo=_yfTicker(symbol)#,day_begin='1-1-2022', day_end='31-12-2022',interval='1d')
    # tickerinfo=ticker['info']

    # y_Outstandingshare=tickerinfo.get('sharesOutstanding')
    y_Beta=tickerinfo.get('beta')
    y_previousClose=yf.Ticker(symbol).history(period="1d", interval='1d')['Close'].iloc[0]

    print('Beta=',y_Beta)

    Next5YearPAGrowthRate=0

    try:
        ''' ----------------------- '''
        '''    ANALYSIS   SECTION   '''
        ''' ----------------------- '''
        header = {
          "User-Agent":
          "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"
        }

        r = requests.get(analyse_url,headers=header)

        # save the html to file
        # with open("output1.html", "w") as file:
        #     file.write(str(r.text))


        # page = pd.read_html(str(r.text))
        page = pd.read_html(StringIO(str(r.text)))

        print(page)

        for i,p in enumerate(page):
            try:
                df= p[p['Growth Estimates'].str.contains('Next 5 Years \(per annum\)')]
                Next5YearPAGrowthRate  = float(p.loc[4,symbol.upper()].replace('%',''))
                break
            except Exception as e:
                continue
    except Exception as e:
        print ('Cannot get Analysis view of growth rate. Assume 0 (error:%s) on %s'%(str(e),analyse_url))
        return  0, y_previousClose

    long_term_growth=((float(Next5YearPAGrowthRate+100)/100)**(1/5)-1) # Next 5 Years (per annum) prediction by analyst
    print('long_term_growth:',long_term_growth)


    '''---------- // I. INCOME STATEMENT // ----------'''
    retry=3
    income_statement_header=None
    for i in range(retry): # retry if not getting info
        try:
            income_statement_html = requests.get(income_statement_url,headers=header)
            print(f'{symbol} income_statement_html')
            # with open(f'{symbol} income_statement_html.html', 'w') as file:
            #     file.write(income_statement_html.text)
            income_statement_soup = bs(income_statement_html.text, 'html.parser')
            print(f'{symbol} income_statement_soup')
            # with open(f'{symbol} income_statement_soup.html', 'w') as file:
            #     file.write(income_statement_soup)
            income_statement_table = income_statement_soup.find('div', class_='M(0) Whs(n) BdEnd Bdc($seperatorColor) D(itb)')
            print(f'{symbol} income_statement_table')
            # with open(f'{symbol} income_statement_table.html', 'w') as file:
            #     file.write(income_statement_table)
            income_statement_header = income_statement_table.find('div', class_='D(tbr) C($primaryColor)')
            print(f'{symbol} income_statement_header')
            break # if no error then skip retry
        except AttributeError as e:
            print(i,f'{symbol}:retry getting income statement from ',income_statement_url,str(e))
            time.sleep(1)
            sys.exit()
        except Exception as e:
            print ('Error getting income statement:',str(e))


    header_lst = []
    try:
        if income_statement_header is None:
            return  -1, y_previousClose

        for i in income_statement_header.find_all('div'):
            if len(i) != 0:
               header_lst.append(i.text)
        header_lst = header_lst[::-1]
        del header_lst[len(header_lst)-1]
        header_lst.insert(0,'Breakdown')
        income_statement_df = pd.DataFrame(columns = header_lst)
    except Exception as e:
        print ('Error getting income_statement_header:', e)
        return  0, y_previousClose

    revenue_row = income_statement_table.find('div', class_='D(tbr) fi-row Bgc($hoverBgColor):h')
    revenue_lst = []
    for i in revenue_row.find_all('div', attrs={'data-test':'fin-col'}):
        i = i.text
        i = i.replace(",","")
        revenue_lst.append(int(float(i))*1000)
    revenue_lst = revenue_lst[::-1]
    revenue_lst.insert(0,'Total Revenue')

    income_statement_df.loc[0] = revenue_lst

    retry=5
    EBIT_row=None

    for i in range(retry): # retry if not getting info
        try:
            EBIT_row = income_statement_table.find('div', attrs={'title':'EBIT'}).parent.parent
            break
        except AttributeError as e:
            print ('Attribute Error getting EBIT from income statement:',str(e))
            time.sleep(1)
        except Exception as e:
            print ('Error getting income statement:',str(e))

    if EBIT_row is None:
        return  0, y_previousClose

    EBIT_lst = []
    for i in EBIT_row.find_all('div', attrs={'data-test':'fin-col'}):
        i = i.text
        i = i.replace(",","")
        if i=='-':
            i=0
        EBIT_lst.append(int(float(i))*1000)
    EBIT_lst = EBIT_lst[::-1]
    EBIT_lst.insert(0,'EBIT')
    income_statement_df.loc[1] = EBIT_lst

    income_statement_df = income_statement_df.drop('ttm', axis=1)


    '''---------- // II. Forecasting Revenues and EBIT // ----------'''

    latest_rev = income_statement_df.iloc[0,len(income_statement_df.columns)-1]
    earliest_rev = income_statement_df.iloc[0,1]
    rev_CAGR = (latest_rev/earliest_rev)**(float(1/(len(income_statement_df.columns)-1)))-1
    print('rev_CAGR',rev_CAGR)
    EBIT_margin_lst = []
    for year in range(1,len(income_statement_df.columns)):
        EBIT_margin = income_statement_df.iloc[1,year]/income_statement_df.iloc[0,year]
        EBIT_margin_lst.append(EBIT_margin)
    avg_EBIT_margin = sum(EBIT_margin_lst)/len(EBIT_margin_lst)

    len_EBIT_available=len(EBIT_lst)
    forecast_df = pd.DataFrame(columns=['Year ' + str(i) for i in range(1,len_EBIT_available+1)]) # 7)])

    rev_forecast_lst = []
    for i in range(1,len_EBIT_available+1): #7):
        if i != len_EBIT_available-1: #6:
            rev_forecast = latest_rev*(1+rev_CAGR)**i
        else:
            rev_forecast = latest_rev*(1+rev_CAGR)**(i-1)*(1+long_term_growth)
        if pd.isna(rev_forecast):
            rev_forecast_lst.append(0)
        else:
            rev_forecast_lst.append(int(float(rev_forecast)))
    forecast_df.loc[0] = rev_forecast_lst

    def applyposneg(num):
        if float(num)<0:
            return -1
        return 1

    EBIT_forecast_lst = []
    EBIT_lst.append(0) # TEST: add 0 to last year just to make +ve/-ve sign for forecasted EBIT

    for i in range(0,len_EBIT_available):
        EBIT_forecast = rev_forecast_lst[i]*abs(avg_EBIT_margin)*applyposneg(EBIT_lst[i+1])
        EBIT_forecast_lst.append(int(float(EBIT_forecast)))
    forecast_df.loc[1] = EBIT_forecast_lst

    '''---------- // III. Calculating the WACC // ----------'''

    ''' ---- WACC  ---- '''
    current_date = datetime.date.today()
    past_date = current_date-datetime.timedelta(days=timespan)

    #CBOE Interest Rate 10 Year T No
    risk_free_rate_float=(yf.Ticker('^TNX').history(period='5d',
                                 interval='1d')['Close'].iloc[-1])/100

    price_information_df = pd.DataFrame(columns=['Stock Prices', 'Market Prices'])

    price_information_df['Stock Prices']=yf.Ticker(symbol).history(start=past_date,
                                                        end=current_date,
                                                        interval='1d')['Close']#.reset_index()

    # S&P 500 as Market growth reference
    price_information_df['Market Prices']=yf.Ticker('^GSPC').history(start=past_date,
                                                        end=current_date,
                                                        interval='1d')['Close']#.reset_index()

    returns_information_df = pd.DataFrame(columns =['Stock Returns', 'Market Returns'])


    stock_return_lst = []
    for i in range(1,len(price_information_df)):
        open_price = price_information_df.iloc[i-1,0]
        close_price = price_information_df.iloc[i,0]
        stock_return = (close_price-open_price)/open_price
        stock_return_lst.append(stock_return)
    returns_information_df['Stock Returns'] = stock_return_lst

    market_return_lst = []
    for i in range(1,len(price_information_df)):
        open_price = price_information_df.iloc[i-1,1]
        close_price = price_information_df.iloc[i,1]
        market_return = (close_price-open_price)/open_price
        market_return_lst.append(market_return)
    returns_information_df['Market Returns'] = market_return_lst

    covariance_df = returns_information_df.cov()
    covariance_float = covariance_df.iloc[1,0]
    variance_df = returns_information_df.var()
    market_variance_float = variance_df.iloc[1]

    equity_beta = covariance_float/market_variance_float

    market_risk_premium = market_risk_float - risk_free_rate_float

    if y_Beta is None or True:
        beta = equity_beta #use calculated Beta
    else:
        beta = y_Beta #use Yahoo Beta if exists

    equity_return = risk_free_rate_float+ beta *(market_risk_premium)

    retry=3
    with requests.Session() as s:
        for i in range(retry): # retry if not getting info
            try:
                balance_sheet_html = s.get(balance_sheet_url,headers=header, timeout=20)
            except Exception as e:
                print ('Error getting balance sheet,retrying:',balance_sheet_html.status_code)
    balance_sheet_soup = bs(balance_sheet_html.text, 'html.parser')

    balance_sheet_table = balance_sheet_soup.find('div', class_='D(tbrg)')

    net_debt_lst = []

    net_debt_row = balance_sheet_table.find('div', attrs={'title':'Total Debt'}).parent.parent
    for value in net_debt_row.find_all('div'):
        value = value.text
        value = value.replace(',','')
        net_debt_lst.append(value)

    net_debt_int = int(float(net_debt_lst[3]))*1000 #skip the first two columns which is text and start with 3 which is current period value

    market_cap_html = requests.get(market_cap_url,headers=header)

    market_cap_soup = bs(market_cap_html.text, 'html.parser')
    market_cap_int = 0

    market_cap_row = market_cap_soup.find('td', attrs={'data-test':'MARKET_CAP-value'})
    market_cap_str = market_cap_row.text
    market_cap_lst = market_cap_str.split('.')

    if market_cap_str[len(market_cap_str)-1] == 'T':
        market_cap_length = len(market_cap_lst[1])-1
        market_cap_lst[1] = market_cap_lst[1].replace('T',(12-market_cap_length)*'0')
        market_cap_int = int(''.join(market_cap_lst))

    if market_cap_str[len(market_cap_str)-1] == 'B':
        market_cap_length = len(market_cap_lst[1])-1
        market_cap_lst[1] = market_cap_lst[1].replace('B',(9-market_cap_length)*'0')
        market_cap_int = int(''.join(market_cap_lst))

    company_value = market_cap_int + net_debt_int
    WACC = market_cap_int/company_value * equity_return + net_debt_int/company_value * debt_return * (1-tax_rate)

    '''-------- // IV. Discounting the Forecasted EBIT // --------'''

    discounted_EBIT_lst = []


    for year in range(0,5):
        discounted_EBIT = forecast_df.iloc[1,year]/(1+WACC)**(year+1)
        discounted_EBIT_lst.append(int(float(discounted_EBIT)))

    terminal_value = forecast_df.iloc[1,len_EBIT_available-1]/(WACC-long_term_growth) # len_EBIT_available = 5 used to be
    PV_terminal_value = int(terminal_value/((1+WACC)**len_EBIT_available)) #5))

    ''' ----------------------- '''
    '''    STATISTICS SECTION   '''
    ''' ----------------------- '''
    try:

        r = requests.get(statistics_url,headers ={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})

        # page = pd.read_html(r.text)
        page = pd.read_html(StringIO(str(r.text)))

        y_enterprise_value = 0
        y_total_cash_value = 0
        for i,p in enumerate(page):
            try:
                df= p[p[0].str.contains('Enterprise Value')]
                # print('df==',df,'\n',p[0][1],'\n',p[0].str.contains('Enterprise Value '),'\n',p[p[0].str.contains('Enterprise Value ')])
                if not df.empty:
                    #p.index(0).filter(regex='^Enterprise Value ')
                    y_enterprise_value_str=df[1].iloc[0]
                    y_stat_Enterprise_Value = y_enterprise_value_str.split('.') #split 123.4B into 1234 and 4B
                    # print (df, 'y_enterprise_value=',y_enterprise_value, ' vs ticker.info = ',numerize.numerize(y_enterpriseValue))

                    if y_enterprise_value_str[-1] == 'T':
                        if len(y_stat_Enterprise_Value)==1: # no decimal
                            y_stat_Enterprise_Value[0]=y_stat_Enterprise_Value[0].replace('T',12*'0')
                        else:
                            y_stat_Enterprise_Value_len = len(y_stat_Enterprise_Value[1])-1
                            y_stat_Enterprise_Value[1] = y_stat_Enterprise_Value[1].replace('T',(12-y_stat_Enterprise_Value_len)*'0')
                        y_enterprise_value = float(''.join(y_stat_Enterprise_Value))

                    if y_enterprise_value_str[-1] == 'B':
                        if len(y_stat_Enterprise_Value)==1: # no decimal
                            y_stat_Enterprise_Value[0]=y_stat_Enterprise_Value[0].replace('B',9*'0')
                        else:
                            y_stat_Enterprise_Value_len = len(y_stat_Enterprise_Value[1])-1
                            y_stat_Enterprise_Value[1] = y_stat_Enterprise_Value[1].replace('B',(9-y_stat_Enterprise_Value_len)*'0')
                        y_enterprise_value = float(''.join(y_stat_Enterprise_Value))
                    break
                else:
                    print (p)
            except Exception as e:
                print ('Waring: error occurs during y_enterprise_value extraction:',str(e),'page#',i,'\n',p)
                continue

        for i,p in enumerate(page):
            try:

                df= p[p[0].str.contains('Total Cash')]
                if not df.empty:

                    y_total_cash_value_str=df[1].iloc[0]
                    y_stat_Total_Cash = y_total_cash_value_str.split('.') #split 123.4B into 1234 and 4B

                    if y_total_cash_value_str[-1] == 'T':
                        if len(y_stat_Total_Cash)==1: # no decimal
                            y_stat_Total_Cash[0]=y_stat_Total_Cash[0].replace('T',12*'0')
                        else:
                            y_stat_Total_Cash_len = len(y_stat_Total_Cash[1])-1
                            y_stat_Total_Cash[1] = y_stat_Total_Cash[1].replace('T',(12-y_stat_Total_Cash_len)*'0')
                        y_total_cash_value = float(''.join(y_stat_Total_Cash))

                    if y_total_cash_value_str[-1] == 'B':
                        if len(y_stat_Total_Cash)==1: # no decimal
                            y_stat_Total_Cash[0]=y_stat_Total_Cash[0].replace('B',9*'0')
                        else:
                            y_stat_Total_Cash_len = len(y_stat_Total_Cash[1])-1
                            y_stat_Total_Cash[1] = y_stat_Total_Cash[1].replace('B',(9-y_stat_Total_Cash_len)*'0')
                        y_total_cash_value = float(''.join(y_stat_Total_Cash))

                    break
            except Exception as e:
                print ('Waring: error during y_stat_Total_Cash extraction:',str(e))
                continue
    except Exception as e:
        print ('Cannot get EV / TC from yahoo statistisc: %s)'%(str(e)))

    ''' --- my interpretation of ENTERPRISE VALUE --- '''

    if y_enterprise_value: # if Yahoo enterprise_value exists, use it
        enterprise_value = y_enterprise_value
    else:
        enterprise_value = sum(discounted_EBIT_lst)+PV_terminal_value-y_total_cash_value


    equity_value = enterprise_value-net_debt_int+y_total_cash_value

    share_outstanding = balance_sheet_table.find('div', attrs={'title':'Share Issued'}).parent.parent
    share_outstanding_lst = []
    for value in share_outstanding.find_all('div'):
        value = value.text
        value = value.replace(',','')
        share_outstanding_lst.append(value)

    # working backward to get the expected share price
    share_outstanding_int = int(float(share_outstanding_lst[3]))*1000
    equity_intrinsic_value = equity_value/share_outstanding_int

    overundervalue_pct=round(((y_previousClose-equity_intrinsic_value)/y_previousClose)*100,2)

    return round(equity_intrinsic_value,3), y_previousClose


def read_html_table(source):
    user_agents = [
	'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
	'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
	'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
	'Mozilla/5.0 (iPhone; CPU iPhone OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148',
	'Mozilla/5.0 (Linux; Android 11; SM-G960U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.72 Mobile Safari/537.36'
    ]
    user_agent = random.choice(user_agents)

    header = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36 '}
    header = {
      "User-Agent":
      "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"
    }

    res = requests.get(source,headers=header, timeout=20)

    if res.status_code != 200:
        res = requests.get(source,headers=header, timeout=20) #try 1 more time
        return None, res.status_code, res.text

    soup = bs(res.content, "html.parser")

    if 'Select All' in res.text:
        for tag in soup.find_all("span", {'class':'Fz(0)'}): #remove those select checkboxes if any
            tag.replaceWith('')

    table = soup.find_all('table') # it should give us a table of tickers

    if len(table)==0:
        print ('something very wrong gtting ',symbol)
        return None, res.status_code, res.text
    # df = pd.read_html(str(table))[0]
    df = pd.read_html(StringIO(str(table)))[0]

    print('source returned symbol list:',source)
    print('\n\n\n*******************\n',df)
    return df['Symbol']

    
def calc_intrinsic_value(symbol):

    # Step 2: Retrieve the stock data
    stock = yf.Ticker(symbol)
    
    # Step 3: Get the enterprise value, net debt, total cash value, and outstanding shares
   
    short_name = stock.info.get('shortName', 'N/A')
    price = stock.info.get('regularMarketPrice', 'N/A')
    if price == 'N/A':
        price = stock.info.get('previousClose', 'N/A')
    enterprise_value = stock.info.get('enterpriseValue', 0)
    total_debt = stock.info.get('totalDebt', 0)
    total_cash = stock.info.get('totalCash', 0)
    outstanding_shares = stock.info.get('sharesOutstanding', 1)  # Avoid division by zero
    
    # Calculate net debt (total debt minus total cash)
    net_debt = total_debt - total_cash
    
    # Step 4: Calculate equity value
    equity_value = enterprise_value - net_debt + total_cash
    
    # Step 5: Calculate intrinsic price
    intrinsic_price = equity_value / outstanding_shares
    

    return round(intrinsic_price,3), price



if __name__ == '__main__':
    import pyttsx3
    # speak = pyttsx3.init()  # object creation

    #
    # Example 1 of ggetting intrinsic value of ONE stock
    #
    symbol='MSTR'
    in_value,stock_price=calc_intrinsic_value(symbol)
    print (symbol,' intrinsic value:', in_value,' and stock price is now', round(stock_price,2))
# =============================================================================
#     speak.setProperty('voice', 'com.apple.speech.synthesis.voice.samantha')
#     speak.say(symbol+' intrinsic='+str(in_value)+' stock price= ' +str(stock_price))
#     speak.runAndWait()
#     if speak._inLoop: # must add at the end to stop the loop
#         speak.endLoop()
#
# =============================================================================
    xx
    stockscreeners={
    'US Most Actives': 'https://finance.yahoo.com/trending-tickers',
    'UK Most Actives': 'https://uk.finance.yahoo.com/most-active',
    # 'UK Most Actives':'https://uk.finance.yahoo.com/most-active/',
    # 'HK Most Actives':'https://hk.finance.yahoo.com/most-active',
    'Growth Technology Stocks': 'https://finance.yahoo.com/screener/predefined/growth_technology_stocks',
    # 'UK High Value':'https://uk.finance.yahoo.com/screener/d6297804-c260-40b4-b47f-818b97aa2159',
    # 'UK Most Actives': 'https://uk.finance.yahoo.com/most-active',
    # 'HK Most Actives':'https://hk.finance.yahoo.com/most-active', #Region: Hong Kong
    'Growth Technology Stocks': 'https://finance.yahoo.com/screener/predefined/growth_technology_stocks', #Quarterly Revenue Growth YoY %:greater than 25, 1 yr. % Change in EPS (Basic):greater than 25, Sector: Technology, Exchange: NasdaqGS and NYSE
    'Undervalued Growth Stocks': 'https://finance.yahoo.com/screener/predefined/undervalued_growth_stocks',#Trailing P/E: 0 - 20, Price / Earnings to Growth (P/E/G): < 1, 1 yr. % Change in EPS (Basic): 25% to 50% and 50% to 100% and > 100%, Exchange: NasdaqGS and NYSE
    # 'Day Gainers':'https://finance.yahoo.com/screener/predefined/day_gainers', #% Change in Price (Intraday):greater than 3, Region: United States, Market Cap (Intraday): Mid Cap and Large Cap and Mega Cap, Volume (Intraday):greater than 15000
    # 'Day Losers': 'https://finance.yahoo.com/screener/predefined/day_losers', #% Change in Price (Intraday):less than -2.5, Region: United States, Market Cap (Intraday): Mid Cap and Large Cap and Mega Cap, Volume (Intraday):greater than 20000
    'Most Actives': 'https://finance.yahoo.com/screener/predefined/most_actives', #Region: United States, Market Cap (Intraday): Mid Cap and Large Cap and Mega Cap, Volume (Intraday):greater than 5000000
    'Undervalued Large Caps':'https://finance.yahoo.com/screener/predefined/undervalued_large_caps', #Trailing P/E: 0 - 20, Price / Earnings to Growth (P/E/G): < 1, Market Cap (Intraday): Large Cap, Exchange: NasdaqGS and NYSE
    'Aggressive Small Caps': 'https://finance.yahoo.com/screener/predefined/aggressive_small_caps', #1 yr. % Change in EPS (Basic):greater than 25, Market Cap (Intraday): Small Cap, Exchange: NasdaqGS and NYSE
    'Small cap Gainers': 'https://finance.yahoo.com/screener/predefined/small_cap_gainers', #% Change in Price (Intraday):greater than 5, Market Cap (Intraday): Small Cap, Exchange: NasdaqGS and NYSE
    # 'Top Mutual Funds': 'https://finance.yahoo.com/screener/predefined/top_mutual_funds', #Price (Intraday):greater than 15, Morningstar Performance Rating Overall: ★★★★ and ★★★★★, Initial Minimum Investment:greater than 1000, Exchange: Nasdaq
    # 'Top ETF':'https://finance.yahoo.com/etfs', #
    # 'Portfolio Anchors': 'https://finance.yahoo.com/screener/predefined/portfolio_anchors', #unds by Category: Large Blend, Morningstar Performance Rating Overall: ★★★★ and ★★★★★, Initial Minimum Investment:less than 100001, Annual Return NAV Year 1 Category Rank:less than 50, Exchange: Nasdaq
    # 'Solid Large Growth Funds':'https://finance.yahoo.com/screener/predefined/solid_large_growth_funds', #Funds by Category: Large Growth, Morningstar Performance Rating Overall: ★★★★ and ★★★★★, Initial Minimum Investment:less than 100001, Annual Return NAV Year 1 Category Rank:less than 50, Exchange: Nasdaq
    # 'Solid Mid-Cap Growth Funds':'https://finance.yahoo.com/screener/predefined/solid_midcap_growth_funds', #Funds by Category: Mid-Cap Growth, Morningstar Performance Rating Overall: ★★★★ and ★★★★★, Initial Minimum Investment:less than 100001, Annual Return NAV Year 1 Category Rank:less than 50, Exchange: Nasdaq
    # 'Conservative Foreign Funds':'https://finance.yahoo.com/screener/predefined/conservative_foreign_funds', #Funds by Category: Foreign Large Value and Foreign Large Blend and Foreign Large Growth and Foreign Small/Mid Growth and Foreign Large Blend and Foreign Small/Mid Blend and Foreign Small/Mid Value and Foreign Small/Mid Blend and Foreign Small/Mid Value and Foreign Small/Mid Blend and Foreign Small/Mid Value and Foreign Small/Mid Blend and Foreign Small/Mid Value, Morningstar Performance Rating Overall: ★★★★ and ★★★★★, Initial Minimum Investment:less than 100001, Annual Return NAV Year 1 Category Rank:less than 50, Morningstar Risk Rating Overall: ★ and ★★★ and ★★, Exchange: Nasdaq
    # 'High Yield Bond':'https://finance.yahoo.com/screener/predefined/high_yield_bond',
    # 'World Indices':'https://finance.yahoo.com/world-indices',
    # 'my screener':'https://uk.finance.yahoo.com/screener/12aafa3f-9f07-4b56-ba2c-62e78d97ad4a', # UK REITS
    # 'UK Top Picks':'https://uk.finance.yahoo.com/most-active',
    }



    #
    # Example 2 of ggetting intrinsic value of ONE stock
    #
    for screener in stockscreeners:
        symbols=read_html_table(stockscreeners.get(screener))
        print ('SCREENER:',screener)
        print (symbols)
        if symbols is None:
             raise RuntimeError('stock_screener erorr: likely Yahoo not responding!', status_code, pagetext)

        print ('Working on screener:',screener)
        df = pd.DataFrame(columns=['symbol','intrinsic value','price','delta'])
        for symbol in symbols:
            try:
                print ('working on symbol: ', symbol)
                in_value, curr_price= calc_intrinsic_value(symbol)
                # add data to end of df
                df.loc[len(df.index)]=[symbol,in_value,curr_price,str(round((curr_price-in_value)/in_value,2)*100)+'%']
                print (symbol, in_value, curr_price)
            except:
                df.loc[len(df.index)]=[symbol,0,0,-1]
                continue

            # write to file as soon as result obtained
            df.to_csv(screener+'-'+str(datetime.date.today())+'.csv')
