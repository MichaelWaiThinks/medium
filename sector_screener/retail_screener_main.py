#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 7 17:18:59 2024

@author: michaelwai
"""

import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from yahooquery import Screener
import os
import sys
from progress.bar import Bar
from lxml import html
from selenium import webdriver # pip install selenium
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
import requests
import re
import math
import time
import matplotlib.pyplot as plt

def get_etf_holdings(symbol_list):
    header = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36 '}

    if type(symbol_list) != list:
        symbol_list = [symbol_list]

    etf_url = 'https://www.schwab.wallst.com/schwab/Prospect/research/etfs/schwabETF/index.asp?type=holdings&symbol={}'

    # which url to use?
    url = etf_url

    df_stocklist = pd.DataFrame()

    option = webdriver.ChromeOptions()
    option.add_argument("headless")  # ("start-maximized")
    driver = webdriver.Chrome(service=Service(
        ChromeDriverManager().install()), options=option)

    with requests.Session() as req:
        req.headers.update(header)
        for s in symbol_list:
            driver.get(etf_url.format(s))
            row_data = driver.find_element(
                By.XPATH, '//*[@id="activeContent"]')
            tree = html.fromstring(driver.page_source)

            # //*[@id="PaginationContainer"]/ul[2]/li[2]

            try:
                # nextp=driver.find_elements('xpath',"//*[@id=\"PaginationContainer\"]/ul[2]/li[")
                # next_page = driver.find_element(By.XPATH,'//*[@id="PaginationContainer"]/ul[2]/li[7]/a').click()

                all_list_elements = driver.find_elements(
                    By.XPATH, '//*[@id="PaginationContainer"]')
                # numofstocks = driver.find_elements(By.XPATH,'//*[@id="PaginationContainer"]/p/text()[2]')
                # print('numofstocks=',numofstocks[-1].text)

                # print('all_list_elements=',all_list_elements[0].text)
                totalstocks = re.split(
                    '\s', (re.search(r'[0-9]+ matches', all_list_elements[-1].text)).group(0), 1)[0]
                # as each page default 20 stocks
                numpages = math.ceil(int(totalstocks)/20)
                print('we need to scrap %s pages of total %s stocks' %
                      (numpages, totalstocks))
            except Exception as e:
                driver.close()
                print('get_etf_holdings error:', str(e))

            page_output = []
            page_elements = driver.find_elements(
                By.XPATH, '//*[@id="PaginationContainer"]/ul/li')
            # Iterate through the list of elements
            for each_element in page_elements:
                # Extract the text content of each element
                each_element_value = each_element.get_attribute('innerHTML')
                # Add the extracted text content to the page_output list
                page_output.append(each_element_value)

            # Iterate through the pages
            for page_num in range(numpages):
                tree = html.fromstring(driver.page_source)
                symbol_table = driver.find_elements(
                    By.XPATH, '//*[@id="tthHoldingsTbody"]/tr/td')
                numrow = int(len(symbol_table)/5)
                record = []

                symbol = []
                name = []
                weight = []
                held = []
                value = []

                for i in range(numrow):
                    symbol.append(symbol_table[i*5+0].text)
                    name.append(symbol_table[i*5+1].text)
                    weight.append(symbol_table[i*5+2].text)
                    held.append(symbol_table[i*5+3].text)
                    value.append(symbol_table[i*5+4].text)
                    # record=[symbol,name,weight,held,value]
                print('scrapping p.', page_num, ':', symbol)

                df = pd.DataFrame(
                    {
                        'Symbol': symbol,
                        'Name': name,
                        'Weight': weight,
                        'Held': held,
                        'Value': value
                    })
                df_stocklist = pd.concat([df_stocklist, df])

                try:
                    # Extract the data from the current page
                    # page_output = extract_page_data(driver)
                    # Add the data to the final_out list as a dictionary with the page number as the key
                    # final_out.append({
                    #     page_num: page_output
                    # })
                    # Locate the "Next" button on the webpage and click it to navigate to the next page
                    xpath_value = '//*[@id="PaginationContainer"]/ul[2]/li[%s]' % (
                        int(page_num % 5)+3)
                    next_page = driver.find_element(
                        By.XPATH, xpath_value).click()
                    element_present = EC.presence_of_element_located(
                        (By.ID, 'PaginationContainer'))
                    WebDriverWait(driver, 5).until(element_present)
                    page_elements = driver.find_elements(
                        By.XPATH, '//*[@id="PaginationContainer"]/ul/li')

                except Exception as e:
                    pass
                # //*[@id="tthHoldingsTbody"]/tr[1]/td[1]
                time.sleep(2)

        driver.quit()

    df_stocklist = df_stocklist.dropna(subset=['Symbol'])
    df_stocklist = df_stocklist.drop_duplicates(subset=['Symbol'])
    df_stocklist = df_stocklist.sort_values(
        by=['Weight'],key=lambda x: pd.to_numeric(x.str.rstrip('%'), errors='coerce'),ascending=False).reset_index(drop=True)
    # print (df_stocklist)

    return df_stocklist


# Function to fetch stock symbols, their industries, and long names
def fetch_stock_symbols_industry_longname(industry_name):
    s = Screener()
    screener_results = s.get_screeners( industry_name,count=200)  # Adjust count as needed
    if screener_results.get(industry_name) == 'size is too large':
        sys.exit('size is too large')
        
    print(f'{industry_name}=',screener_results[industry_name]['total'])
    
    symbols_and_details = [
        (stock['symbol'], industry_name, stock.get('longName', 'N/A')) 
        for stock in screener_results[industry_name]['quotes']
        # if stock.get('marketCap', 0) > 1e9 #mid cap or above 1B$ # in case one wants to only filter certain size companies
    ]
    
    return symbols_and_details

# Function to retrieve financial data and calculate ratios for a given stock symbol
def get_financial_data(symbol, industry, long_name):
    try:
        company = yf.Ticker(symbol)
        
        # Get financials, balance sheet, and current price data
        income_statement = company.financials.T
        balance_sheet = company.balance_sheet.T
        current_price = company.history(period="1d")['Close'].iloc[-1]
        if 'Total Revenue' not in income_statement.columns or 'Cost Of Revenue' not in income_statement.columns or 'Inventory' not in balance_sheet.columns:
            print (f'{symbol} without income statement or cost of goods')
            return None
        
        LATEST_YEAR=0  # yahoo financial and balance_sheet returns latest year first so first record is lastest data; otherwise I will use -1 instead

        # Calculate EPS
        net_income = income_statement['Net Income'].iloc[LATEST_YEAR]
        shares_outstanding = company.info.get('sharesOutstanding', None)
        if shares_outstanding:
            eps = net_income / shares_outstanding
        else:
            return None
        
        # Calculate P/E Ratio
        pe_ratio = current_price / eps
        
        # Get the latest financial data
        latest_financials = {
            'Symbol': symbol,
            'Name': long_name,
            'Industry': industry,
            'Date': income_statement.index[LATEST_YEAR],
            'Revenue': income_statement['Total Revenue'].iloc[LATEST_YEAR],
            'COGS': income_statement['Cost Of Revenue'].iloc[LATEST_YEAR],
            'Inventory': balance_sheet['Inventory'].iloc[LATEST_YEAR],
            'P/E Ratio': pe_ratio,
            'Stock Price': current_price,
            'Sales/Price Ratio': income_statement['Total Revenue'].iloc[LATEST_YEAR] / current_price
        }
        
        # print (income_statement.index[LATEST_YEAR])
        
        # Calculate Average Inventory and Inventory Turnover Ratio
        latest_financials['Average Inventory'] = balance_sheet['Inventory'].iloc[:2].mean()
        latest_financials['Turnover Ratio'] = latest_financials['COGS'] / latest_financials['Average Inventory']
        
        return latest_financials

    except Exception as e:
        
        print(f"Error fetching data for {symbol}: {e}")
        return None


def retrieve_finance_data(filename):

    all_data=pd.DataFrame()
    if  os.path.isfile(filename): # **** skipping this first
        all_data=pd.read_csv(filename)
    else:
        stock_symbols_and_details = []
        
        """
        1. SCRAP ETF XRT for Retail Sector stocsk around 78 stocks
        """
        
        industry='XRT ETF'
        symbols=get_etf_holdings('XRT') #S&P Retail Select Industry Index


        stock_symbols_and_details = [
            (row['Symbol'], industry, row['Name'])
            for index, row in symbols.iterrows()  # Iterate through DataFrame rows
        ]    
        
              
        """
        2. SCRAP Yahoo Screener for various retail stocks
        Note that there is limitation of Screener that might not return all availabel symbols
        """
        
        industries = [
            'apparel_retail',
            'department_stores',
            'discount_stores',
            'grocery_stores',
            'specialty_retail',
            'internet_retail',
            'luxury_goods',
            'apparel_manufacturing',
            'footwear_accessories',
        ]     
        
        for industry in industries:
            print(f'Fetching symbols from {industry}')
            symbols_and_details = fetch_stock_symbols_industry_longname(industry)
            stock_symbols_and_details += symbols_and_details
        
        # remove duplicates from ETF and Screeners
        stock_symbols_and_details = list(dict.fromkeys(stock_symbols_and_details))

        if not stock_symbols_and_details:
            print("No stock symbols found.")
            return
        
        # Initialize an empty list to store data
        all_data = []
    
        # Fetch financial data for each stock symbol
        with Bar(f"Processing {industry}...", max=len(stock_symbols_and_details)) as bar:
            for symbol, industry, long_name in stock_symbols_and_details:
                financial_data = get_financial_data(symbol, industry, long_name)
                # print(f"Processing {symbol} ({long_name}) in industry {industry}...")
                if financial_data:
                    all_data.append(financial_data)
                bar.next()
        
        if all_data:
            # Convert list of dicts to DataFrame
            final_df = pd.DataFrame(all_data)
            # remove any trailing spaces in column names
            final_df.rename(str.strip, axis = 'columns')
            # Save DataFrame to CSV
            final_df.to_csv(filename, index=False)
        else:
            sys.exit("No financial data available.")
        
    return filename
        
            
def plot_turnaround_ratio(filename):
 
    # Load the data (make sure to replace 'your_file_path.csv' with the actual path)
    data = pd.read_csv(filename)
    
    # Extract relevant columns: Company and Turnover Ratio (Assuming it's labeled as 'Turnover Ratio')
    # Adjust column names according to your CSV file structure
    company_data = data[['Name', 'Turnover Ratio']]
    
    # Drop rows with missing values in 'Turnover Ratio' (optional)
    company_data = company_data.dropna(subset=['Turnover Ratio'])
    
    # Sort by turnover ratio (optional)
    company_data = company_data.sort_values(by='Turnover Ratio', ascending=False)
    
    # Plotting the bar chart
    plt.figure(figsize=(10, 6),dpi=300)  # Set the figure size
    plt.bar(company_data['Name'], company_data['Turnover Ratio'], color='steelblue')
    
    # Adding labels and title
    plt.ylabel('Inventory Turnover Ratio')
    plt.title('Company Inventory Turnover Ratio')
    plt.xticks(rotation=90, fontsize=4)  # Rotate x-axis labels for better readability
    
    # Set y-ticks at intervals of 10
    plt.yticks(range(0, int(company_data['Turnover Ratio'].max()) + 10, 10))
    
    # Add gridlines at intervals of 10 along the y-axis
    plt.grid(axis='y', which='both', linestyle='--', linewidth=0.7)
    
    # Show the plot
    plt.tight_layout()  # Adjust layout to ensure labels fit well
    plt.show()


if __name__ == '__main__':
    filename='./financial_data.csv'

    retrieve_finance_data(filename)
    plot_turnaround_ratio(filename)
    