import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from datetime import datetime,timedelta
import requests
import os
import sys
import math
from progress.bar import Bar



STOCK_DATA_FILE = './data/stock_data.csv'
STOCK_SECTOR_FILE = './data/stock_sector.csv'
COMPARE_PERIOD=180
PREDICT_PERIOD=180
EXCLUDE_SELF=True

# =============================================================================
# NVDA 2023 Earnings Dates:
# Q1 2023 (fiscal year 2023): May 24, 2023 after market close
# Q2 2023: August 23, 2023 after market close
# Q3 2023: November 21, 2023 after market close
# 
# 2024 Earnings Dates:
# Q4 2023 (fiscal year 2023): February 21, 2024 after market close
# Q1 2024 (fiscal year 2024): May 22, 2024 after market close (confirmed)
# Q2 2024: Expected on August 21, 2024 after market close (inferred)
# Q3 2024: Expected on November 19, 2024 after market close (inferred)
# Q4 2024: Expected on February 19, 2025 after market close (inferred)
# 
# =============================================================================


COL = 'Close'
start_date = '1990-05-14'
end_date = '2025-12-30'
title_subtitle=''
current_date = datetime.now().strftime("%Y-%m-%d")
tomorrow=(datetime.now()+timedelta(days=1)).strftime("%Y-%m-%d")
currentime = datetime.now().strftime("%Y%m%d_%H%M")

print('Program starts on :',currentime)

target_symbol='XAUT-USD'
target_symbol='XAUT-USD'

# SI=F','DXY'
my_choice_of_symbols = ['XAUT-USD']#'ITB','AMD','NVDA','SOXX','TSM','INTC','TXN','SMCI','ASML']
    # ['AAPL', 'MSFT', 'GOOG', 'AMZN', 'META', 'T', 'VZ', 'DIS', 'NFLX', 'CMCSA', 
    #               'TSLA', 'GM', 'F', 'NIO', 'FORD', 'JNJ', 'PFE', 'UNH', 'MRK', 'AMGN', 
    #               'JPM', 'BAC', 'WFC', 'C', 'GS', 'PG', 'KO', 'PEP', 'COST', 'WMT', 
    #               'BA', 'HON', 'MMM', 'UNP', 'UPS', 'LIN', 'APD', 'ECL', 'NEM', 'DD', 
    #               'AMT', 'EQIX', 'PLD', 'SPG', 'CBRE', 'NEE', 'DUK', 'SO', 'EXC', 'D', 
    #               'XOM', 'CVX', 'COP', 'SLB', 'PSX']
indices = ['^GSPC', '^DJI', '^IXIC', '^RUT', '^GSPTSE',
         '^BVSP', '^MXX',
          '^N225', '^HSI', '000001.SS', '399001.SZ', '^TWII', '^KS11',
         '^STI', '^JKSE', '^KLSE', '^AXJO', '^NZ50', '^BSESN',
         '^BSESN',# '^TA125.TA',
         '^FTSE', '^GDAXI', '^FCHI', '^STOXX50E', '^N100', '^BFX']


def calculate_stock_volatility(df):
    """
    Calculate the stock volatility for a given symbol within a specified date range.
    
    Parameters:
    symbol (str): The stock ticker symbol.
    start_date (str): The start date for the data in 'YYYY-MM-DD' format.
    end_date (str): The end date for the data in 'YYYY-MM-DD' format.
    
    Returns:
    float: The annualized volatility of the stock.
    """
    # Download stock data from Yahoo Finance
    stock_data = yf.download(symbol, start=start_date, end=end_date)
    
    # Calculate daily returns
    stock_data['Daily Return'] = df.pct_change()
    
    # Calculate the standard deviation of daily returns
    daily_volatility = stock_data['Daily Return'].std()
    
    # Annualize the volatility
    annualized_volatility = daily_volatility * np.sqrt(252)  # Assuming 252 trading days in a year
    
    return annualized_volatility


def get_yearly_holdings_sectors(exchange='nasdaq',year=2024):
    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) target_stockWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36',
    }
    # Function to get holdings for a given year
    url = f"https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=100&offset=0&download=true&exchange={exchange}&date={year}-01-01"
    response = requests.get(url,headers=headers)
    data = response.json()
    holdings = data['data']['rows']
    # return holdings
    return {stock['symbol']: stock['sector'] for stock in holdings}

def get_stock_sector(year=2024):
    if os.path.isfile(STOCK_SECTOR_FILE):
        print('reading stock sector from file...')
        sector_df=pd.read_csv(STOCK_SECTOR_FILE,index_col=0)#,header=[0,1])#if want to skip multicolumn header-> index_col=1,  header=None,skiprows=1
        sector_df['Sector'] = sector_df['Sector'].replace(['',np.nan],'Undefined')
        sector_df = sector_df.dropna()
        sector_dict = sector_df.to_dict('dict')['Sector']
        # sector_df=sector_df.set_index('Symbol')
        
    else:
        nasdaq_symbols_sectors=get_yearly_holdings_sectors('nasdaq',year)
        nyse_symbols_sectors=get_yearly_holdings_sectors('NYSE',year)
        print ('%s stocks retrieved for nasdaq ' % len(nasdaq_symbols_sectors))
        print ('%s stocks retrieved for NYSE ' % len(nyse_symbols_sectors))
        
        #not best practise to merge 2 dicts and wont work if key is not string, but i am lazy anyway
        sector_dict = dict(nasdaq_symbols_sectors, **nyse_symbols_sectors)         
        sector_df = pd.DataFrame(sector_dict.items(),columns=['Symbol','Sector'])
        
        sector_df['Sector'] = sector_df['Sector'].replace(['',np.nan],'Undefined')
        sector_df = sector_df.set_index('Symbol')
        sector_df.to_csv(STOCK_SECTOR_FILE)
        
    return sector_dict

# Download and preprocess data
def download_stock_data(symbols, start_date, end_date):
    data = yf.download(symbols, start=start_date, end=end_date)
    return data

def get_tickers_price(symbols,_start_date='2020-01-01',_end_date='2024-05-14'):
    import os
    import yfinance as yf


    # tomorrow=(datetime.now()+timedelta(days=1)).strftime("%Y-%m-%d")
    if os.path.isfile(STOCK_DATA_FILE):
        print('Reading from stock data file...')
        df=pd.read_csv(STOCK_DATA_FILE)#,index_col=0,header=[0,1])#if want to skip multicolumn header-> index_col=1,  header=None,skiprows=1
        df=df.set_index('Date')
        LASTDATE=pd.to_datetime(df.index[-1]).strftime("%Y-%m-%d")
        STARTDATE_minus_1=(pd.to_datetime(min(df.index))-timedelta(days=1)).strftime("%Y-%m-%d")

        df.index=pd.to_datetime(df.index).strftime('%Y-%m-%d')
        
        print ('Last date in file ',df.index[-1],' target date is ',ENDDATE)
        
        if set(symbols).issubset(df.columns) and\
               STARTDATE_minus_1 <= _start_date and \
                LASTDATE >= _end_date:            
            return df.loc[(df.index<=_end_date)]

        else: #download missing dates till today (end=tomorrow to guarantee today will be downloaded)
            print ('download missing days ',df.index[-1],tomorrow)
            missingdata_df = yf.download(symbols,start=LASTDATE, end=tomorrow, threads=False).reset_index() #download all symbols at once
            missingdata_df = missingdata_df[['Date',COL]]
            missingdata_df = missingdata_df.droplevel(0, axis=1)  #remove first level
            missingdata_df = missingdata_df.rename(columns={missingdata_df.columns[0]: "Date" }).set_index('Date') 
            missingdata_df.index=pd.to_datetime(missingdata_df.index).strftime('%Y-%m-%d')
            df = pd.concat([df,missingdata_df])
            df = df[~df.index.duplicated(keep='last')]
            df.to_csv(STOCK_DATA_FILE)
            return df.loc[(df.index<=_end_date)]

    if len(symbols)>4096:
        df = yf.download(symbols,period=_start_date, threads=False).reset_index() #download all symbols at once without Thread
    else:
        df = yf.download(symbols,period=_start_date, threads=True).reset_index() #download all symbols at once with Thread

    df = df[['Date',COL]]
    df=df.droplevel(0, axis=1)  #remove first level
    df=df.rename(columns={ df.columns[0]: "Date" }).set_index('Date')  # df=df.reset_index()
    df.index=pd.to_datetime(df.index).strftime('%Y-%m-%d')
    df.to_csv(STOCK_DATA_FILE)

    return df

def get_stock_data(symbols):
    if len(symbols)>4096:
        df = yf.download(symbols,period='2020-01-01', threads=False).reset_index() #download all symbols at once
    else:
        df = yf.download(symbols,period='2020-01-01', threads=False).reset_index() #download all symbols at once

    df = df[['Date',COL]]
    df=df.droplevel(0, axis=1)  #remove first level
    df=df.rename(columns={ df.columns[0]: "Date" }).set_index('Date')  # df=df.reset_index()
    df.index=pd.to_datetime(df.index).strftime('%Y-%m-%d')
    df.to_csv(STOCK_DATA_FILE)

    return df

# Function to calculate rolling 3-month periods
def rolling_periods(data, window=COMPARE_PERIOD):
    periods = []
    for i in range(len(data) - window + 1):
        periods.append(data.iloc[i:i+window])
    return periods


def calculate_similarity(target_period, other_period):
    # Handle NaN values by filling them with the mean of the corresponding column
    
    target_period_filled = np.nan_to_num(target_period, nan=np.nanmean(target_period))
    other_period_filled = np.nan_to_num(other_period, nan=np.nanmean(other_period))
    # print(target_period_filled)
    x=np.nan_to_num(target_period_filled.reshape(1, -1))
    y=np.nan_to_num(other_period_filled.reshape(1, -1))

    # similarity = cosine_similarity(target_period_filled.reshape(1, -1), other_period_filled.reshape(1, -1))
    similarity = cosine_similarity(x,y)
    return similarity[0][0]

if __name__=='__main__':
    all_stocks_symbols=[]
    target_symbol_sector=''
    

    try:
        # try to find sector of stock and use it for similar stock in the same sector
        stock_and_sector=get_stock_sector(2024)
        #remove nan
        # stock_and_sector = [ x for x in stock_and_sector if type(x)==str ]

        try:
            target_symbol_sector=stock_and_sector[target_symbol]
            

            # collect all stocks symbols !) same as target_symbol_sector and remove any nan symbol (using symbol==symbol test)
            all_stocks_symbols= [symbol for symbol, sector in stock_and_sector.items() if sector == target_symbol_sector and symbol==symbol]
        except:
            pass
    except Exception as e:
        # if any problem, we will use self comparison  
        print ('seems there is problem finding stock sector or similar stocks...%tb',str(e))
        sys.exit(-1)
        
    if not all_stocks_symbols:
        
        all_stocks_symbols=[target_symbol]
        print('ERROR>>>>>>>all_stocks_symbols>>>>> Using predefined symbols')
        all_stocks_symbols.extend(my_choice_of_symbols)
        
    # =============================================================================
    #     Use my own symbol starts
    # =============================================================================
    
    all_stocks_symbols=my_choice_of_symbols + [target_symbol]
    print('all_stocks_sybmols=',all_stocks_symbols)
    # all_stocks_symbols=indices + [target_symbol]

    # =============================================================================
    #     Use my own symbol ends
    # =============================================================================
    
    '''
    DOWNLOAD ALL STOCK DATA
    '''  

    all_stock_data = download_stock_data(all_stocks_symbols, start_date, tomorrow)#current_date)
    all_stock_data = all_stock_data.ffill()
    if target_symbol not in all_stock_data.columns or \
        target_symbol not in all_stock_data[COL].columns:
        full_target_stock_data=all_stock_data[COL][:end_date] 

        if isinstance(full_target_stock_data,pd. DataFrame) :
            target_stock_data = full_target_stock_data[target_symbol] #only extract up to the target period

        else:
            target_stock_data = full_target_stock_data
            cc

    else:
        full_target_stock_data=all_stock_data[COL][target_symbol]
        target_stock_data = full_target_stock_data[target_symbol][:end_date] #only extract up to the target period
    
    # if all_stock_data.index[-1]+timedelta(days=COMPARE_PERIOD)).strftime("%Y-%m-%d")  

    if EXCLUDE_SELF:
        other_stocks_symbols = list(set(all_stocks_symbols)-set([target_symbol]))
        if len(other_stocks_symbols)==0:
            other_stocks_symbols = [target_symbol]
    else:
        other_stocks_symbols = all_stocks_symbols
        
# =============================================================================
#     print(all_stocks_symbols,'\n other stock symbols:',other_stocks_symbols)
#     
#     print(f'total stock in {target_symbol_sector} sector:',len(other_stocks_symbols))
#     
# =============================================================================
    # other_stocks_symbols=['AAPL'] #just find similar pattern from itself
    
    
    # Select the last 3 months of  stock prices
    if target_symbol not in all_stock_data.columns: 
        target_stock_recent_data = all_stock_data[COL][target_symbol][:end_date].tail(COMPARE_PERIOD)
        print(target_stock_recent_data)
    else:
        target_stock_recent_data = all_stock_data[COL][target_symbol][:end_date].tail(COMPARE_PERIOD)
        print(target_stock_recent_data)

    
    
    # Calculate rolling 3-month periods for each stock data
    other_rolling_periods = {}
    
    for symbol in other_stocks_symbols:  # Excluding target_stock, as we already have its data
        if symbol==target_symbol and not EXCLUDE_SELF:
            self_compare_period=(pd.to_datetime(end_date)-timedelta(days=COMPARE_PERIOD)).strftime("%Y-%m-%d")
            other_rolling_periods[symbol] = rolling_periods(all_stock_data[COL][symbol][:self_compare_period])
        else:
            if symbol in all_stock_data.columns:
                other_rolling_periods[symbol] = rolling_periods(all_stock_data[COL][symbol][:end_date])
                
            else:
                other_rolling_periods[symbol] = rolling_periods(all_stock_data[COL][symbol][:end_date])
                
    # Find the most similar period
    most_similar_stock = None
    most_similar_index = None
    highest_similarity = -1
    

    df_similarity_list=pd.DataFrame(columns=['Symbol','Similarity','Row','Start','End'])
    for symbol, periods in other_rolling_periods.items():
        with Bar('comparing '+symbol, max=len(periods)) as bar:
            for i, period in enumerate(periods):
                # print ('checking similarity...',symbol,'\n',period.values)
                if (period.empty):#isnull().all()): #i.e. if Nan
                    continue
                else:
                    similarity = calculate_similarity(target_stock_recent_data.values, period.values)
                    # print(symbol,' = ',similarity)
                    if similarity > highest_similarity:
                        # print('new similarity found:',symbol,' at ',similarity)
                        highest_similarity = similarity
                        most_similar_stock = symbol
                        most_similar_index = i
                        
                        most_similar_period = other_rolling_periods[most_similar_stock][most_similar_index]
                        df=pd.DataFrame(
                                {
                                    'Symbol':most_similar_stock,
                                    'Similarity':highest_similarity,
                                    'Row':most_similar_index,
                                    'Start': most_similar_period.index[0],
                                    'End':  most_similar_period.index[-1]
                                },index=[0])
                        df_similarity_list = pd.concat([df_similarity_list,df])
                bar.next()
    
    df_similarity_list=df_similarity_list.reset_index()
    df_similarity_list.to_csv('./data/df_similarity_list.csv')
    
    for similar_plot_number in range(0,len(df_similarity_list)):
        
        highest_similarity = df_similarity_list['Similarity'].iloc[similar_plot_number]
        most_similar_stock = df_similarity_list['Symbol'].iloc[similar_plot_number]
        most_similar_index = df_similarity_list['Row'].iloc[similar_plot_number]
        most_similar_period = other_rolling_periods[most_similar_stock][most_similar_index]
 
        # Extract the most similar period's data
        if len(other_rolling_periods[most_similar_stock][most_similar_index:])<COMPARE_PERIOD:
            print(f"Most similar period of {most_similar_stock} stock to {target_symbol} stock:")
            print ('most_similar_stock\n',most_similar_stock, 
                   '\nwith Highest Similarity value: {0:10.2f}'.format(highest_similarity*100),'%\n' )
            most_similar_period = other_rolling_periods[most_similar_stock][most_similar_index]
            print("Similar Period Start Date:", most_similar_period.index[0])
            print("Similar Period End Date:", most_similar_period.index[-1])
            print('Using next similar... ')
            
            if  len(df_similarity_list)>2:
                
                # use next similar instead
                highest_similarity = df_similarity_list['Similarity'].iloc[-2]
                most_similar_stock = df_similarity_list['Symbol'].iloc[-2]
                most_similar_index = df_similarity_list['Row'].iloc[-2]
                most_similar_period = other_rolling_periods[most_similar_stock][most_similar_index]
                print(f"Most similar period of {most_similar_stock} stock to {target_symbol} stock:")
                print ('most_similar_stock\n',most_similar_stock, 
                       '\nwith Highest Similarity value: {0:10.2f}'.format(highest_similarity*100),'%\n' )
                print("Similar Period Start Date:", most_similar_period.index[0])
                print("Similar Period End Date:", most_similar_period.index[-1])
            else:
                print('no similarity found, program abort')
                sys.exit(-1)
        
        
        most_similar_period = other_rolling_periods[most_similar_stock][most_similar_index]
        most_similar_period_index = other_rolling_periods[most_similar_stock][most_similar_index]#+COMPARE_PERIOD:most_similar_index+COMPARE_PERIOD+PREDICT_PERIOD]
        print(f"Most similar period of {most_similar_stock} stock to {target_symbol} stock:")
        print ('most_similar_stock is :',most_similar_stock, 
               '\nwith Highest Similarity value: {0:10.2f}'.format(highest_similarity*100),'%\n' )
        print("Similar Period Start Date:", most_similar_period.index[0])
        print("Similar Period End Date:", most_similar_period.index[-1])
        
        future_price_starting_index=all_stock_data.index.get_loc(most_similar_period_index.index[-1])
        future_price_ending_index = future_price_starting_index + PREDICT_PERIOD
        

        print(most_similar_stock , all_stock_data[COL].columns)
        
        if most_similar_stock in all_stock_data[COL].columns:
            
            most_similar_future_price=all_stock_data[COL][most_similar_stock][future_price_starting_index:future_price_ending_index]
        else:
            most_similar_future_price=all_stock_data[COL][future_price_starting_index:future_price_ending_index]

        
        if (len(most_similar_future_price)<PREDICT_PERIOD): # not enough future data for mimicking 
            print('not enough future data in similar stock for mimick, continue?')
            future_data_too_short=True
        else:
            future_data_too_short=False
            
        # Plot recent stock prices and future prediction
        target_stock_recent_dates = target_stock_data.index[-COMPARE_PERIOD:]
        future_dates = pd.date_range(start=target_stock_recent_dates[-1], periods=PREDICT_PERIOD, freq='D')
    
        # most_similar_future_price = all_stock_data[COL][most_similar_stock][most_similar_period_index.index[-1]:(most_similar_period_index.index[-1]+pd.Timedelta(days=PREDICT_PERIOD)).strftime("%Y-%m-%d")]
    
        '''
        # adjust future stock price based on ratio between similar stock
        '''
        
        # === method 1 = Using price difference ratio to adjust target stock price ===============================================================
        # ratio_of_similar_stock = target_stock_data.iloc[-1] / most_similar_future_price.iloc[0]
        # target_stock_future_pattern = np.array(most_similar_future_price) * ratio_of_similar_stock
        # =============================================================================
    
        # === method 2 = Using Percentage change to apply to future stock =========================
        # Calculate the percentage change in the most similar period
        percentage_changes = most_similar_future_price.pct_change().fillna(0)
        # Adjust target_stock's future prediction based on these percentage changes
        last_price = target_stock_data.iloc[-1]
        
        target_stock_future_pattern = last_price * (1 + percentage_changes).cumprod().values
        # =============================================================================
        
        # === method 3 = Using Volaatitlity =========================================================================
        # target_stock_volatility = calculate_stock_volatility(all_stock_data[COL][target_symbol])
        # similar_stock_volatility = calculate_stock_volatility(all_stock_data[COL][most_similar_stock])
        # volatility_ratio_of_similar_stock=(target_stock_volatility/similar_stock_volatility)
        # target_stock_future_pattern = target_stock_future_pattern / volatility_ratio_of_similar_stock
        # =============================================================================
    
        print(target_stock_recent_data,target_stock_future_pattern)
        # Append the recent data with the future prediction to ensure continuity
        target_stock_recent_and_future = np.concatenate((target_stock_recent_data.values, target_stock_future_pattern))
        
        
        # =============================================================================
        #
        #     Let's plot the result !
        #
        # =============================================================================
    
        fig, ax = plt.subplots( 4, 1, figsize=(14, 18), dpi=200)
        plt.suptitle(f'{target_symbol} pattern matching on {COL} price \nin the {COMPARE_PERIOD} days ends {end_date} with {PREDICT_PERIOD} days prediction.\n{title_subtitle}',fontsize=16,y=1)
        plt.title(f'chart generated on {currentime}',fontsize=10)
    
        # =============================================================================
        #     subplot [0]
        # =============================================================================
        
        # Plot the original stock price from COMPARE PERIOD starts till Latest downloaded data (today)
        # ax[0].plot(full_target_stock_data.loc[target_stock_recent_dates[0]:].index,
        #             full_target_stock_data[target_stock_recent_dates[0]:].values, 
        print(full_target_stock_data[target_symbol])
        
        ax[0].plot(full_target_stock_data[target_symbol].index,#..loc[target_stock_recent_dates[0]:].index,
                    full_target_stock_data[target_symbol].values,#.loc[target_stock_recent_dates[0]:].values, 
                    label=f'{target_symbol} Stock Price ', color='green',linewidth=2,linestyle='-',alpha=0.8)
        
        # Highlight the stock we used for comparison
        ax[0].plot(target_stock_data.index[-COMPARE_PERIOD:], target_stock_data.iloc[-COMPARE_PERIOD:], label=f'{target_symbol} Stock Price (Search pattern used: Last {COMPARE_PERIOD} Days)', linestyle='-',color='red', linewidth=1,alpha=1)
    
        # Plot the future of PREDICT PERIOD from last date of COMPARE PERIOD
        # use len of future stock as to avoid data shortage in future dates and ensure dimension in line x & y
        # as data is short, so we use [:len()] to plot the first part of available data. 

        ax[0].plot(future_dates[:len(target_stock_future_pattern)], target_stock_future_pattern, label=f'Predicted {target_symbol} Stock Price ({PREDICT_PERIOD} Days)', color='red', linewidth=1,linestyle='--', alpha=1)
        ax[0].axvline(future_dates[0],color='red')
        ax[0].text(future_dates[0],0.1,'Prediction: '+future_dates[0].strftime("%Y-%m-%d"),transform=ax[0].get_xaxis_transform(), fontsize=8,rotation=90)
        
        # add symbol as watermark
        ax[0].text(0.5, 0.5, target_symbol, 
            transform=ax[0].transAxes,
            fontsize=50, color='gray', alpha=0.4,
            ha='center', va='center', rotation=0)
        ax[0].set_title(f'{target_symbol} Stock Price (sector: {target_symbol_sector})')
        ax[0].set_ylabel('Price')
        ax[0].legend(loc='best')
        ax[0].grid(True)
        ax[0].tick_params(axis='x', rotation=0)
      
        # =============================================================================
        #     subplot [1] - Similar Stock chart with period of similarity and its future
        # =============================================================================
    
        ax1=ax[1].twinx().twiny()
    
        # Highlight the Similar Period found on historical price chart
        ax[1].axvspan(most_similar_period.index[0], most_similar_period.index[-1], color='yellow', alpha=0.5, label='Most Similar Period')
        # Highlight the part we will be using for PREDICT PERIOD
        ax[1].axvspan(most_similar_future_price.index[0], most_similar_future_price.index[-1], color='gray', alpha=0.5, label='Use for Prediction')
    
        # Plot the selected stock's prices and highlight the most similar period
        if most_similar_stock in all_stock_data.columns:
            ax[1].plot(all_stock_data[COL][most_similar_stock].index, all_stock_data[COL][most_similar_stock], label=f'{most_similar_stock} Stock Price', color='blue')
        else:
            ax[1].plot(all_stock_data[COL].index, all_stock_data[COL], label=f'{most_similar_stock} Stock Price', color='blue')

        ax1.plot(full_target_stock_data.index,
                  full_target_stock_data.values, 
                  label=f'{target_symbol} Stock Price ', color='red',linewidth=2,linestyle='-',alpha=1)
       
       
        # add symbol as watermark
        ax[1].text(0.5, 0.5, most_similar_stock , 
            transform=ax[1].transAxes,
            fontsize=50, color='gray', alpha=0.4,
            ha='center', va='center', rotation=0)
    
        ax[1].set_title(f'{most_similar_stock} Stock Price with Highlighted Most Similar Period')
        ax[1].set_ylabel('Price') 
        ax[1].legend()
        ax1.legend(loc='lower left')
        ax[1].legend(loc='upper left')
        ax[1].grid(True)
        ax[1].tick_params(axis='x', rotation=0)
        ax[1].axvspan(target_stock_data.index[-COMPARE_PERIOD],target_stock_data.index[-1], color='red', alpha=0.5, label='Comparions period')

        # =============================================================================
        #     subplot [2] - zoom into the similar period and compare with target stock
        # =============================================================================
    
        # Plot the zoomed-in comparison of the similar period and target_stock's recent data
        zoomed_end_date = most_similar_period.index[0] + pd.Timedelta(days=COMPARE_PERIOD-1)  # Adjusted to match the length of future_dates
        zoomed_dates = pd.date_range(start=most_similar_period.index[0], end=zoomed_end_date, freq='D')
        print("Similar Period Start Date:", zoomed_dates[0])
        print("Similar Period End Date:", zoomed_dates[-1])
        
        # Highlight the part we used to compare the targetstock
       
        ax2 = ax[2].twinx().twiny() # overlay target stock
    
        # Plot out both similar stock and target stock for visulization
        # ax[2].plot(zoomed_dates[-COMPARE_PERIOD:], most_similar_period.tail(COMPARE_PERIOD), label=f'{most_similar_stock} Similar Period', color='gold')
        ax[2].plot(zoomed_dates, most_similar_period.tail(COMPARE_PERIOD), label=f'{most_similar_stock} Similar Period', color='blue')
        ax2.plot(target_stock_data.index[-COMPARE_PERIOD:], target_stock_data.tail(COMPARE_PERIOD), label=f'{target_symbol} Stock Price (Last 3 Months)', color='red')
    
        ax[2].set_xlabel('',color='blue')
        ax[2].set_ylabel(f'{most_similar_stock} Price', color='blue')
        ax[2].tick_params(axis='both', labelcolor='blue')
        ax[2].grid(True)
        ax[2].legend(loc='lower left')

        # color the border and x,y ticker for easy reading 
        ax2.set_xlabel('',color='red')
        ax2.set_ylabel(f'{target_symbol} Price', color='red')
        ax2.tick_params(axis='both', colors='red')
        ax2.grid(True)
        ax2.legend(loc='upper left')
        
        ax[2].set_title(f'Zoomed-in Comparison of {target_symbol} and similar {most_similar_stock} stock (similiarity='+str(round(highest_similarity*100,2))+'%)')

        ax2.spines['left'].set_color('blue')  
        ax2.spines['bottom'].set_color('blue')  
        ax2.spines['right'].set_color('red')  
        ax2.spines['top'].set_color('red')  
        ax2.grid(True,linestyle = "--")
        
        # =============================================================================
        #     subplot [3] - Future stock performance based on Similar stock's future projection
        # =============================================================================
    
        ax3 = ax[3].twinx().twiny()
    
        # Plot out both similar stock and target stock 's future days for visulization of PREDICT PERIOD
        ax[3].plot(most_similar_future_price.index[-len(most_similar_future_price):], most_similar_future_price, label=f'{most_similar_stock} Following price in same span', linestyle='-', color='blue',alpha=0.5)
        ax3.plot(future_dates[-len(target_stock_future_pattern):], target_stock_future_pattern, label=f'{target_symbol} Predicted price from {most_similar_stock} ', linestyle='--', color='red', alpha=1)
    
        ax[3].set_xlabel('',color='blue')
        ax[3].set_ylabel(f'{most_similar_stock} Price', color='blue')
        ax[3].tick_params(axis='both', labelcolor='blue')
        ax[3].set_title(f'Predicted Future {PREDICT_PERIOD} days pattern based on {most_similar_stock} stock')
        ax[3].legend(loc='lower left')
        ax[3].grid(True)
        
        # color the border and x,y ticker for easy reading 
        ax3.set_xlabel('',color='red')
        ax3.set_ylabel(f'{target_symbol} Price', color='red')
        ax3.tick_params(axis='both', colors='red')
        ax3.spines['left'].set_color('blue')  
        ax3.spines['bottom'].set_color('blue')  
        ax3.spines['right'].set_color('red')  
        ax3.spines['top'].set_color('red')      
    
        ax3.legend(loc='upper left')
        ax3.grid(True,linestyle = "--")

        fig.tight_layout(pad=5.0)
        plt.show()    
        
        similaritypct=str(round(highest_similarity*100,2))
        path='/Users/michaelwai/SynologyDrive/pypy/medium/trading/patternmatching/img/'
        filename=path+f'{target_symbol}_{most_similar_stock}_{end_date}_{COMPARE_PERIOD}-{PREDICT_PERIOD} on {COL} price_{currentime}_{similaritypct}pct.jpg'
        fig.savefig(filename,bbox_inches='tight')
     
        # =============================================================================
        #     save the plot for record. Change filename path as in your system
        # =============================================================================
        
    # save the highest one to Downloads
    path='/Users/michaelwai/Downloads/'
    filename=path+f'{target_symbol}_{most_similar_stock}_{end_date}_{COMPARE_PERIOD}-{PREDICT_PERIOD} on {COL} price_{currentime}_{similaritypct}pct.jpg'
    fig.savefig(filename,bbox_inches='tight')

    
    # Here is the result in text
    
    print(df_similarity_list)
    
    print(f"Most similar period of {most_similar_stock} stock to {target_symbol} stock:")
    print ('most_similar_stock\n',most_similar_stock, 
           '\nwith Highest Similarity value: {0:10.2f}'.format(highest_similarity*100),'%\n' 
           )
    print("Similar Period Start Date:", most_similar_period.index[0])
    print("Similar Period End Date:", most_similar_period.index[-1])
    
    # Download data for other stocks for comparison
# =============================================================================
#     other_stocks_symbols = \
#         ['AAPL', 'MSFT', 'GOOG', 'AMZN', 'META', 'T', 'VZ', 'DIS', 'NFLX', 'CMCSA', 
#                       'TSLA', 'GM', 'F', 'NIO', 'FORD', 'JNJ', 'PFE', 'UNH', 'MRK', 'AMGN', 
#                       'JPM', 'BAC', 'WFC', 'C', 'GS', 'PG', 'KO', 'PEP', 'COST', 'WMT', 
#                       'BA', 'HON', 'MMM', 'UNP', 'UPS', 'LIN', 'APD', 'ECL', 'NEM', 'DD', 
#                       'AMT', 'EQIX', 'PLD', 'SPG', 'CBRE', 'NEE', 'DUK', 'SO', 'EXC', 'D', 
#                       'XOM', 'CVX', 'COP', 'SLB', 'PSX']
#         
# =============================================================================
    # other_stocks_symbols=    ['MSFT', 'CSCO','INTC','NVDA','TSLA','SLB', 'GOOG','WMT']#'GOOGL']  # Example symbols for Microsoft and Google


# =============================================================================
#    indcis = ['^GSPC', '^DJI', '^IXIC', '^RUT', '^GSPTSE',
#             '^BVSP', '^MXX',
#              '^N225', '^HSI', '000001.SS', '399001.SZ', '^TWII', '^KS11',
#             '^STI', '^JKSE', '^KLSE', '^AXJO', '^NZ50', '^BSESN', '^TA125.TA',
#             '^BSESN', '^TA125.TA',
#          '^FTSE', '^GDAXI', '^FCHI', '^STOXX50E', '^N100', '^BFX']
# 
# =============================================================================
