import pandas as pd
import matplotlib.pyplot as plt
from fredapi import Fred
import yfinance as yf
import datetime as dt

# Setup and fetching data
API_KEY = 'a4049a1e2039b9a7a8ceb6aa3afa3dc7'  # Make sure to use your actual API key
fred = Fred(api_key=API_KEY)
today = dt.datetime.now().strftime('%Y-%m-%d')

# Retrieve CPI data
cpi_series_id = 'CPIAUCSL'
cpi_data = fred.get_series(cpi_series_id, observation_start='1971-01-01', observation_end=today)
cpi_data = pd.DataFrame(cpi_data, columns=['CPI'])
cpi_data.index = pd.to_datetime(cpi_data.index)
cpi_data_monthly = cpi_data.resample('M').ffill()

# Calculate the inverse of the CPI to represent USD depreciation
cpi_data_monthly['Inverse CPI'] =  cpi_data_monthly['CPI']
base_inverse_cpi = cpi_data_monthly['Inverse CPI'].iloc[0]
cpi_data_monthly['Inverse CPI Change (%)'] = ((cpi_data_monthly['Inverse CPI'] / base_inverse_cpi) - 1) * 100

# Retrieve and process Gold price data
gold_data = pd.read_csv('goldprice.csv', parse_dates=['Date'], index_col='Date', dayfirst=True)
if gold_data.index.max() < pd.Timestamp(today):
    # Fetch recent data from yfinance if needed
    new_gold_data = yf.download('GC=F', start=gold_data.index.max() + pd.Timedelta(days=1), end=today)
    new_gold_data = new_gold_data['Close'].resample('D').ffill()
    gold_data = pd.concat([gold_data, new_gold_data])
gold_data = gold_data.resample('M').ffill()

# Calculate cumulative percentage change from the start point
base_gold_price = gold_data['Close'].iloc[0]
gold_data['Gold Change (%)'] = ((gold_data['Close'] / base_gold_price) - 1) * 100

# Combine CPI and Gold data for plotting
comparison_data = pd.DataFrame({
    'Inverse USD Change (%)': cpi_data_monthly['Inverse CPI Change (%)'],
    'Gold Change (%)': gold_data['Gold Change (%)']
}).dropna()

# Plotting
fig, ax = plt.subplots(figsize=(10, 6))
comparison_data.plot(ax=ax, color=['steelblue', 'goldenrod'])
ax.set_title('Cumulative Percentage Change in Inverse CPI and Gold Price Since 1971')
ax.set_ylabel('Cumulative Change (%)')
ax.grid(True)
plt.show()
