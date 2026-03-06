import yfinance as yf
import numpy as np

# Define the ticker symbol
ticker_symbol = "DELL"

# Retrieve the stock data
stock = yf.Ticker(ticker_symbol)

# Get the short name, current price, and last close price of the stock
short_name = stock.info.get('shortName', 'N/A')
current_price = stock.info.get('regularMarketPrice', 'N/A')
last_close_price = stock.info.get('previousClose', 'N/A')

# Get the enterprise value, net debt, total cash value, and outstanding shares
enterprise_value = stock.info.get('enterpriseValue', 0)
total_debt = stock.info.get('totalDebt', 0)
total_cash = stock.info.get('totalCash', 0)
outstanding_shares = stock.info.get('sharesOutstanding', 1)  # Avoid division by zero

# Calculate net debt (total debt minus total cash)
net_debt = total_debt - total_cash

# Calculate equity value
equity_value = enterprise_value - net_debt + total_cash

# Calculate intrinsic price
intrinsic_price = equity_value / outstanding_shares

# Retrieve historical market data for volume analysis
hist_data = stock.history(period="1y")

# Check for signs of institutional accumulation
average_volume = np.mean(hist_data['Volume'])
high_volume_days = hist_data[hist_data['Volume'] > 1.5 * average_volume]
price_increase_days = high_volume_days[high_volume_days['Close'] > high_volume_days['Open']]

# Print the results
print(f"Short Name: {short_name}")
print(f"Enterprise Value: {enterprise_value}")
print(f"Net Debt: {net_debt}")
print(f"Total Cash: {total_cash}")
print(f"Outstanding Shares: {outstanding_shares}")
print(f"Equity Value: {equity_value}")
print('\n')
print(f"Current Price: {current_price}")
print(f"Last Close Price: ${last_close_price}")
print(f"Intrinsic Price: ${intrinsic_price}")
print(f"Average Daily Volume: {average_volume}")
print(f"High Volume Days: {len(high_volume_days)}")
print(f"Price Increase Days with High Volume: {len(price_increase_days)}")

# Analyzing the pattern for institutional accumulation
if len(price_increase_days) > 0.2 * len(high_volume_days) and\
    len(price_increase_days) < 0.5 * len(high_volume_days):  # Example threshold
    print("Possible signs of institutional accumulation detected.")
else:
    print("No strong signs of institutional accumulation detected.")
