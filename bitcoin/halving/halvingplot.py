import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
# Fetch historical Bitcoin price data from Yahoo Finance
bitcoin_data = yf.download('BTC-USD', start='2010-01-01')
bitcoin_data['Date']=bitcoin_data.index
# bitcoin_data=bitcoin_data.reset_index()
# print(bitcoin_data)

# Define the halving dates
halving_dates = [
    '2012-11-28',  # First halving
    '2016-07-09',  # Second halving
    '2020-05-11',  # Third halving
    '2024-04-29'   # Fourth halving
]

# Create subplots for each halving event
fig, axs = plt.subplots(len(halving_dates), 1, figsize=(10, 6*len(halving_dates)))




def plot_logreg_chart(ax,df):
    
    def Logarithmic_regression(df):
        df = df[df['Close'].notna()]
        df['price_y']=np.log(df['Close']) # using natural log of stock price

        df['x']=np.arange(len(df)) #fill index x column with 1,2,3...n
        try:
            b,a =np.polyfit(df['x'],df['price_y'],1)
        except Exception as e:
            b,a=0,0

        df['priceTL']=b*df['x'] + a

        df['y-TL']=df['price_y']-df['priceTL']
        df['SD']=np.std(df['y-TL'])
        df['TL-2SD']=df['priceTL']-2*df['SD']
        df['TL-SD']=df['priceTL']-df['SD']
        df['TL+2SD']=df['priceTL']+2*df['SD']
        df['TL+SD']=df['priceTL']+df['SD']

        return df

    df = Logarithmic_regression(df)
    RAINBOWCOLOR1='hotpink'
    RAINBOWCOLOR2='orange'
    RAINBOWCOLOR3='gold'
    RAINBOWCOLOR4='yellowgreen'
    RAINBOWCOLOR5='lightgreen'


    # fig, (ax1, ax2) = plt.subplots(dpi=600,nrows=2, sharex=True)

    # plotting stock price on log regression
    ax.plot(df['Date'],df['price_y'],color='black',linewidth=0.5)

    # plotting stock price on log regression
    ax.plot(df['Date'],df['TL+2SD'],color=RAINBOWCOLOR1, linewidth=0.5)
    ax.plot(df['Date'],df['TL+SD'],color=RAINBOWCOLOR2,  linewidth=0.5)
    ax.plot(df['Date'],df['priceTL'],color=RAINBOWCOLOR3,linewidth=0.5)
    ax.plot(df['Date'],df['TL-SD'], color=RAINBOWCOLOR4, linewidth=0.5)
    ax.plot(df['Date'],df['TL-2SD'],color=RAINBOWCOLOR5, linewidth=0.5)


    ax.fill_between(df['Date'],df['TL+2SD'], df['TL+SD'],facecolor=RAINBOWCOLOR2,  alpha=0.6,edgecolor=None,linewidth=0)
    ax.fill_between(df['Date'],df['TL+SD'], df['priceTL'],facecolor=RAINBOWCOLOR3, alpha=0.6,edgecolor=None,linewidth=0)
    ax.fill_between(df['Date'],df['priceTL'], df['TL-SD'],facecolor=RAINBOWCOLOR4, alpha=0.6,edgecolor=None,linewidth=0)
    ax.fill_between(df['Date'],df['TL-SD'], df['TL-2SD'],facecolor=RAINBOWCOLOR5,  alpha=0.6,edgecolor=None,linewidth=0)

    return ax


# Plot Bitcoin price trend around each halving
for i, halving_date in enumerate(halving_dates):
    halving_date = pd.to_datetime(halving_date)
    if i < len(halving_dates) - 1:
        next_halving_date = pd.to_datetime(halving_dates[i + 1])
        bitcoin_period = bitcoin_data[(bitcoin_data.index >= halving_date) & (bitcoin_data.index < next_halving_date)]
    else:
        # For the last subplot, plot until the end of the data
        bitcoin_period = bitcoin_data[bitcoin_data.index >= halving_date]

    # axs[i].plot(bitcoin_period.index, bitcoin_period['Close'], label=f'Halving {i+1}')
    plot_logreg_chart(axs[i],bitcoin_period)
    axs[i].set_title(f'Bitcoin Price Trend around Halving {i+1}')
    axs[i].set_ylabel('Price (USD)')
    axs[i].grid(True)
    axs[i].legend()

    # Set x-axis limits for each subplot
    axs[i].set_xlim(bitcoin_period.index.min(), bitcoin_period.index.max())

plt.xlabel('Date')
plt.tight_layout()
plt.show()
