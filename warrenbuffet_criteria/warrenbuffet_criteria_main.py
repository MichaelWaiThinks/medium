#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 30 2024
@article: https://medium.com/@michael.wai/i-follow-the-7-warren-buffets-criteria-to-evaluate-finanical-statements-and-screen-all-s-p500-4a5d6a89fdc7
@author: https://medium.com/@michael.wai
"""

import yfinance as yf
import pandas as pd

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

import progressbar

from selenium.webdriver.chrome.options import Options

options = Options()
options.binary_location = "/usr/bin/chromium-browser"

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


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

                for i in range(numrow):
                    symbol.append(symbol_table[i*5+0].text)
                
                # to fit Yahoo finance symboll format e.g. BRK/B should be BRK-B
                symbol=[ticker.replace('/', '-') for ticker in symbol]
                df=pd.DataFrame(
                        {
                            'Symbol':symbol,
                        })
                
                df_stocklist = pd.concat([df_stocklist,df])


                # go to next page
                try:
                    # Locate the "Next" button on the webpage and click it to navigate to the next page
                    xpath_value='//*[@id="PaginationContainer"]/ul[2]/li[%s]'%(int(page_num%5)+3)
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

    driver.quit()


    df_stocklist.to_csv('./etflist1.csv')
    
    df_stocklist=df_stocklist.dropna(subset=['Symbol'])
    df_stocklist=df_stocklist.drop_duplicates(subset=['Symbol'])
    df_stocklist=df_stocklist.sort_values(by=['Symbol']).reset_index(drop=True)
    df_stocklist.to_csv('./etflist.csv')
    stock_list = df_stocklist['Symbol'].values.tolist()
    stock_list.remove('--')
    return stock_list


def warren_buffet_critera(stocks) :
    # Define the criteria thresholds for scoring
    criteria = {
        "Gross Margin": 0.4,
        "SG&A Margin": 0.3,
        "R&D Margin": 0.3,
        "Interest Expense Margin": 0.15,
        "Income Tax Margin": 0.2,  # around 20%
        "Profit Margin": 0.2,
        "EPS Growth": "growth"  # Calculated based on EPS growth average
    }

    # Initialize an empty list to store results
    results = []

    print("Processing stock data:")
    bar = progressbar.ProgressBar(maxval=len(stocks), widgets=[progressbar.Bar('$', '[', ']'), ' ', progressbar.Percentage()])
    bar.start()
    
    # Fetch data for each stock ticker
    for i,ticker in enumerate(stocks):
        
        bar.update(i + 1)  # Update progress bar
    
        stock = yf.Ticker(ticker)
        financials = stock.financials
        income_stmt = financials.T  # Transpose for easier access to years as rows
    
        # Calculate each metric using alternate formulas if direct values are missing
        try:
            # Now work out the 7 criteria
            
            # Prepare the basic components for the criteria calculation
            revenue = income_stmt["Total Revenue"].iloc[0] if "Total Revenue" in income_stmt.columns else None
            cost_of_revenue = income_stmt["Cost Of Revenue"].iloc[0] if "Cost Of Revenue" in income_stmt.columns else None
            gross_profit = income_stmt["Gross Profit"].iloc[0] if "Gross Profit" in income_stmt.columns else (revenue - cost_of_revenue if revenue and cost_of_revenue else None)
            operating_expense = income_stmt["Operating Expense"].iloc[0] if "Operating Expense" in income_stmt.columns else None
            operating_income = income_stmt["Operating Income"].iloc[0] if "Operating Income" in income_stmt.columns else (gross_profit - operating_expense if gross_profit and operating_expense else None)
            interest_expense = income_stmt["Interest Expense"].iloc[0] if "Interest Expense" in income_stmt.columns else None
            other_income_expense = income_stmt["Other Income Expense"].iloc[0] if "Other Income Expense" in income_stmt.columns else None
            pre_tax_income = income_stmt["Pretax Income"].iloc[0] if "Pretax Income" in income_stmt.columns else (operating_income + other_income_expense if operating_income and other_income_expense else None)
            income_tax = income_stmt["Tax Provision"].iloc[0] if "Tax Provision" in income_stmt.columns else None
            net_income = income_stmt["Net Income"].iloc[0] if "Net Income" in income_stmt.columns else (pre_tax_income - income_tax if pre_tax_income and income_tax else None)
    
            # Calculate each metric using the values derived or directly available
            gross_margin = gross_profit / revenue if gross_profit and revenue else None
            
            # 2. SG&A Margin
            sga_margin = income_stmt["Selling General And Administration"].iloc[0] / gross_profit if "Selling General And Administration" in income_stmt.columns and gross_profit else None
            
            # 3. R&D Margin
            rd_margin = income_stmt["Research And Development"].iloc[0] / gross_profit if "Research And Development" in income_stmt.columns and gross_profit else None
            
            # 4. Interest Expense Margin
            interest_expense_margin = interest_expense / operating_income if interest_expense and operating_income else None
            
            # 5, Income Tax Margin
            income_tax_margin = income_tax / pre_tax_income if income_tax and pre_tax_income else None
            
            # 6. Profit Margin
            profit_margin = net_income / revenue if net_income and revenue else None
    
            #  7. EPS calculation: Take past 2-3 years or maximum available years
            net_income_values = income_stmt["Net Income"].values[:3] if "Net Income" in income_stmt.columns else []
            shares_outstanding = stock.info.get("sharesOutstanding", 1)  # Default to 1 if unavailable
            eps_values = [ni / shares_outstanding for ni in net_income_values if shares_outstanding > 0]
    
            # Calculate the scores based on criteria
            scores = []
            
            # Gross Margin Score
            gross_margin_score = ((gross_margin - criteria["Gross Margin"]) / criteria["Gross Margin"] +1) if gross_margin else 0
            scores.append(gross_margin_score)
            
            # SG&A Margin Score (negative if above threshold)
            sga_margin_score = ((criteria["SG&A Margin"] - sga_margin) / criteria["SG&A Margin"] +1) if sga_margin else 0
            scores.append(sga_margin_score)
    
            # R&D Margin Score
            rd_margin_score = ((criteria["R&D Margin"] - rd_margin) / criteria["R&D Margin"] +1) if rd_margin else 0
            scores.append(rd_margin_score)
    
            # Interest Expense Margin Score
            interest_expense_margin_score = ((criteria["Interest Expense Margin"] - interest_expense_margin) / criteria["Interest Expense Margin"] +1) if interest_expense_margin else 0
            scores.append(interest_expense_margin_score)
    
            # Income Tax Margin Score (close to 20%)
            income_tax_margin_score = (1 - abs(income_tax_margin - criteria["Income Tax Margin"]) / criteria["Income Tax Margin"]) +1 if income_tax_margin else 0
            scores.append(income_tax_margin_score)
    
            # Profit Margin Score
            profit_margin_score = ((profit_margin - criteria["Profit Margin"]) / criteria["Profit Margin"] +1) if profit_margin else 0
            scores.append(profit_margin_score)
    
            # EPS Growth Score - Average growth percentage
            eps_growth_score = (
                (sum((eps_values[i] - eps_values[i - 1]) / eps_values[i - 1] for i in range(1, len(eps_values))) / (len(eps_values) - 1) +1) 
                if len(eps_values) > 1 else 0
            )
            
            scores.append(eps_growth_score)
    
            # Aggregate score: Average of all scores
            total_score = sum(scores) / len(scores)
            
            # Check if each metric meets the criteria
            num_score_met=0
            criteria_met = [
                gross_margin >= criteria["Gross Margin"] if gross_margin is not None else False,
                sga_margin <= criteria["SG&A Margin"] if sga_margin is not None else False,
                rd_margin <= criteria["R&D Margin"] if rd_margin is not None else False,
                interest_expense_margin <= criteria["Interest Expense Margin"] if interest_expense_margin is not None else False,
                0.18 <= income_tax_margin <= 0.22 if income_tax_margin is not None else False,  # Income tax around 20%
                profit_margin >= criteria["Profit Margin"] if profit_margin is not None else False,
                eps_growth_score > 0  # EPS growth is positive
            ]
            num_criteria_met = sum(criteria_met)
            
            # Append the results
            results.append({
                "Ticker": ticker,
                "Gross Margin": gross_margin,
                "SG&A Margin": sga_margin,
                "R&D Margin": rd_margin,
                "Interest Expense Margin": interest_expense_margin,
                "Income Tax Margin": income_tax_margin,
                "Profit Margin": profit_margin,
                "EPS Growth": eps_values,
                "Score": total_score,
                "Buffet Criteria Matches (0-7)":num_criteria_met,
                "Meets All Criteria": all(criteria_met)
            })
    
        except Exception as e:
            print(f"Error processing {ticker}: {e}")
    
    bar.finish()
    
    # Convert results to a DataFrame
    results_df = pd.DataFrame(results)
    
    # save the results
    results_df.to_csv("stock_analysis_results.csv", index=False)

    return results_df

def main():
    # Define your list of stock tickers
    stocks = ['MSTR', 'MARA', 'DJT','PLTR','PYPL','NVDA','META','INVE','AVY','COST','WMT','NKE','KO','MCD']  # Add your desired stock tickers here
    stocks = get_holdings('QQQ')
    
    results_df=warren_buffet_critera(stocks)
    
    # Calculate summary statistics
    total_stocks = len(results_df)
    stocks_over_100 = len(results_df[results_df['Score'] > 1.0])  # Assuming score over 100% means a Score > 1.0
    stocks_below_100 = len(results_df[results_df['Score'] <= 1.0])
    stocks_meet_criteria = len(results_df[results_df['Meets All Criteria'] == True])
    stocks_didnt_meet_criteria = total_stocks - stocks_meet_criteria
    
    # Print summary
    print("Summary of Stock Analysis:")
    print(f"Total stocks processed: {total_stocks}")
    print(f"Stocks with a score over 100%: {stocks_over_100}")
    print(f"Stocks with a score below or equal to 100%: {stocks_below_100}")
    print(f"Stocks that meet all criteria: {stocks_meet_criteria}")
    print(f"Stocks that don't meet all criteria: {stocks_didnt_meet_criteria}")


if __name__ == "__main__":
    main()