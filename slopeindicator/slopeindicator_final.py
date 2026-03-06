import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from progress.bar import Bar
import os

from warnings import simplefilter
simplefilter(action="ignore", category=pd.errors.PerformanceWarning)

# i dont like so many warnings as some are false positives
pd.options.mode.chained_assignment = None 

ALLOW_LONG = 1 # 1 to activate
ALLOW_SHORT = 0 # -1 to activate

# Download historical data for TICKER for the last 5 years
ticker = 'NKE'
data = yf.download(ticker, period='5y')
data['Buy and Hold Return'] = data['Close'] / data['Close'].iloc[0]

stock_info = yf.Ticker(ticker)
company_name = stock_info.info['shortName']

# Function to calculate the slope and convert to degrees
def calculate_slope_in_degrees(series):
    x = np.arange(len(series))
    y = series.values
    if len(y) > 1:
        slope = np.polyfit(x, y, 1)[0]
        angle_in_radians = np.arctan(slope)
        angle_in_degrees = np.degrees(angle_in_radians)
    else:
        angle_in_degrees = np.nan
    return angle_in_degrees

# Function to calculate returns with a confirmation period 
def calculate_return_on_slope(data, window_size, confirm_days):
    data['Slope'] = data['Close'].rolling(window=window_size).apply(calculate_slope_in_degrees, raw=False)
    data['Signal'] = np.where(data['Slope'] > 0, ALLOW_LONG, ALLOW_SHORT)
    data['Confirmed Signal'] = data['Signal'].shift(confirm_days)
    
    data['Return'] = data['Close'].pct_change() * data['Confirmed Signal'].shift(1)
    data['Cumulative Return'] = (1 + data['Return']).cumprod()
    return data['Cumulative Return'].iloc[-1]

# Initialize variables to track the overall best results
overall_best_return = -np.inf
overall_best_period = ''
overall_best_window_size = 0
overall_best_confirm_days = 0
overall_best_test_size = 0

# Function to perform backtesting on different periods
def backtest_period(data, period_name, offset):
    global overall_best_return, overall_best_period, overall_best_window_size, overall_best_confirm_days, overall_best_test_size

    period_data = data.iloc[-offset:].copy()
    window_sizes_range = range(5, int(offset/10), 5)  # Test window sizes from 10 to 100 days
    confirm_days_range = range(0, 1)  # Test confirmation days from 1 to 5 days
    test_size_range = range(1,8,1)
    results = []

    # Train model and backtest for different window sizes and confirmation days
    iteration = len(test_size_range)*len(window_sizes_range)*len(confirm_days_range)
    with Bar('working... '+period_name, max=iteration) as bar:
        for test_size in test_size_range:
            test_size = float(test_size/10)
            # Split data into training (50%) and testing (50%)
            train_data, test_data = train_test_split(period_data, test_size=test_size, shuffle=False)
            for window_size in window_sizes_range:
                for confirm_days in confirm_days_range:
                    train_return = calculate_return_on_slope(train_data.copy(), window_size, confirm_days)
                    test_return = calculate_return_on_slope(test_data.copy(), window_size, confirm_days)

                    results.append({
                        'Window Size': window_size,
                        'Confirm Days': confirm_days,
                        'Train Return': train_return,
                        'Test Return': test_return,
                        'TrainTest ratio': test_size,
                    })
                    bar.next()

                    # Update the overall best return if the current one is better
                    if test_return > overall_best_return:
                        overall_best_return = test_return
                        overall_best_period = period_name
                        overall_best_window_size = window_size
                        overall_best_confirm_days = confirm_days
                        overall_best_test_size = test_size
                        print(f'\n*** LATEST Parameters for \
                              {overall_best_return},\
                              {overall_best_period},\
                              {overall_best_window_size},\
                              {overall_best_window_size},\
                              {overall_best_test_size}\n')
                                    
                        

    results_df = pd.DataFrame(results)
    results_df.to_csv(f'{ticker}_{period_name}_slope_indicator_results.csv', index=False)

    best_result = results_df.loc[results_df['Test Return'].idxmax()]
    best_window_size = int(best_result['Window Size'])
    best_confirm_days = int(best_result['Confirm Days'])
    best_test_size = best_result['TrainTest ratio']
    best_return = best_result['Test Return']  # only shows test period return

    # Calculate slope and signals for the entire dataset using the best window size and confirmation days
    period_data['Slope'] = period_data['Close'].rolling(window=best_window_size).apply(calculate_slope_in_degrees, raw=False)
    period_data['Signal'] = np.where(period_data['Slope'] > 0, ALLOW_LONG, ALLOW_SHORT)
    period_data['Confirmed Signal'] = period_data['Signal'].shift(best_confirm_days)
    period_data['Return'] = period_data['Close'].pct_change() * period_data['Confirmed Signal'].shift(1)
    period_data['Cumulative Return'] = (1 + period_data['Return']).cumprod()

    # Calculate the buy and hold return
    period_data['Buy and Hold Return'] = period_data['Close'] / period_data['Close'].iloc[0]

    # Avoiding duplicate buy/sell signals
    in_trade = False
    buy_signals = []
    sell_signals = []

    for i in range(1, len(period_data)):
        if period_data['Confirmed Signal'].iloc[i] == ALLOW_LONG and not in_trade:
            buy_signals.append(period_data.index[i])
            in_trade = True
        elif period_data['Confirmed Signal'].iloc[i] == ALLOW_SHORT and in_trade:
            sell_signals.append(period_data.index[i])
            in_trade = False

    # Plotting the results
    plt.figure(figsize=(14, 12))

    # Subplot 1: Stock Closing Price
    ax1 = plt.subplot(3, 1, 1)
    plt.text(0.5, 0.5, ticker,
             transform=ax1.transAxes,
             fontsize=50, color='gray', alpha=0.4,
             ha='center', va='center', rotation=0)
    plt.plot(period_data['Close'], label=f'{company_name} ({ticker})', color='blue')
    plt.title(f'{company_name} ({ticker}) - {period_name}')
    plt.ylabel('Price')
    plt.legend()

    # Subplot 2: Slope Indicator
    ax2 = plt.subplot(3, 1, 2, sharex=ax1)
    plt.plot(period_data['Slope'], label=f'Slope Indicator in Degrees ({best_window_size}-day)', color='red')
    plt.axhline(y=0, color='black', linestyle='--', linewidth=1)
    plt.ylim([-90, 90])  # Limiting the y-axis to -90 to 90 degrees
    plt.title(f'Slope Indicator ({best_window_size}-day Rolling Window) in Degrees - {period_name}')
    plt.ylabel('Slope (Degrees)')
    plt.legend()

    # Subplot 3: Cumulative Return with Buy/Sell Signals
    ax3 = plt.subplot(3, 1, 3, sharex=ax1)

    plt.plot(period_data['Cumulative Return'], label='Cumulative Return', color='purple')
    plt.text(period_data.index[-1], period_data['Cumulative Return'].iloc[-1], str(round(period_data['Cumulative Return'].iloc[-1], 2)) + '%')

    plt.plot(period_data['Buy and Hold Return'], label='Buy and Hold Return', color='gray', linestyle='--')
    plt.text(period_data.index[-1], period_data['Buy and Hold Return'].iloc[-1], str(round(period_data['Buy and Hold Return'].iloc[-1], 2)) + '%')

    plt.scatter(buy_signals, period_data['Cumulative Return'].loc[buy_signals], marker='^', color='green', label='Buy Signal', alpha=0.5, s=50)
    plt.scatter(sell_signals, period_data['Cumulative Return'].loc[sell_signals], marker='v', color='red', label='Sell Signal', alpha=0.5, s=50)

    plt.title(f'Cumulative Return with Buy/Sell Signals ({period_name}) - Confirm Days: {best_confirm_days}')
    plt.ylabel('Cumulative Return')
    plt.xlabel('Date')
    plt.legend()

    ax1.get_xaxis().set_visible(False)
    ax2.get_xaxis().set_visible(False)

    plt.tight_layout()
    plt.show()

    print(f'Best Parameters for {period_name}: Train/Test ratio = {best_test_size}, Window Size = {best_window_size} days, Confirmation Days = {best_confirm_days} days with returns at %s %%' % round((period_data['Cumulative Return'].iloc[-1]-1)*100, 2))
    print(f'Compare to Buy and Hold return for the same period was %s %%' % round((period_data['Buy and Hold Return'].iloc[-1] - 1) * 100, 2))


# Function to load results from CSV and plot them
def plot_cumulative_returns(ticker, periods):
    plt.figure(figsize=(14, 8))

    for period in periods:
        filename = f'{ticker}_{period}_slope_indicator_results.csv'
        if os.path.exists(filename):
            # Read the CSV file
            results_df = pd.read_csv(filename)
            
            # Reconstruct cumulative returns
            period_data = data.iloc[-time_periods[period]:].copy()
            best_result = results_df.loc[results_df['Test Return'].idxmax()]
            best_window_size = int(best_result['Window Size'])
            best_confirm_days = int(best_result['Confirm Days'])

            period_data['Slope'] = period_data['Close'].rolling(window=best_window_size).apply(calculate_slope_in_degrees, raw=False)
            period_data['Signal'] = np.where(period_data['Slope'] > 0, ALLOW_LONG, ALLOW_SHORT)
            period_data['Confirmed Signal'] = period_data['Signal'].shift(best_confirm_days)
            period_data['Return'] = period_data['Close'].pct_change() * period_data['Confirmed Signal'].shift(1)
            period_data['Cumulative Return'] = (1 + period_data['Return']).cumprod()

            # Plot the cumulative return for this period
            plt.plot(period_data['Cumulative Return'], label=f'{period} - Best Return: {(period_data["Cumulative Return"].iloc[-1] - 1) * 100:.2f}%')
            plt.text(period_data.index[-1], period_data['Cumulative Return'].iloc[-1], f'{period}')

    plt.plot(data['Buy and Hold Return'], label=f"Buy and Hold Return: {(data['Buy and Hold Return'].iloc[-1]-1)*100:.2f}%", color='black', linestyle='-')
    plt.text(data.index[-1], data['Buy and Hold Return'].iloc[-1],'Buy and Hold' )

    plt.title(f'Cumulative Returns Across Different Periods for {ticker}')
    plt.xlabel('Date')
    plt.ylabel('Cumulative Return')
    plt.legend()
    plt.grid(True)
    plt.show()
    
    

# Define time periods and corresponding offsets in data rows
time_periods = {
    '3 Months': 63,     # Approx. 21 trading days per month
    '6 Months': 126,
    '9 Months': 189,
    '1 Year': 252,
    '2 Years': 504,
    '3 Years': 756,
    '4 Years': 1008,
    '5 Years': len(data)
}

# Run backtests for each time period
for period_name, offset in time_periods.items():
    backtest_period(data, period_name, offset)

# Display overall best parameters across all periods
print("\n=== Overall Best Performance ===")
print(f'Period: {overall_best_period}')
print(f'Train/Test Ratio: {overall_best_test_size}')
print(f'Window Size: {overall_best_window_size} days')
print(f'Confirmation Days: {overall_best_confirm_days} days')
print(f'Return: {(overall_best_return - 1) * 100:.2f}%')

# Call the function to plot cumulative returns for all periods
plot_cumulative_returns(ticker, time_periods.keys())

