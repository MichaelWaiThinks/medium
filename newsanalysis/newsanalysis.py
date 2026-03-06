#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 12 2024

@author: michaelwai
"""

from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
from datetime import datetime,timedelta
from newsapi import NewsApiClient 
from progress.bar import Bar
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from progress.bar import Bar



# Load tokenizer and model
model_name = "yiyanghkust/finbert-tone"
tokenizer_name = "yiyanghkust/finbert-tone"
tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
model_id = AutoModelForSequenceClassification.from_pretrained(tokenizer_name)

stock_symbol = 'INVE'
stock_keyword = stock_symbol 
model_id_filename=model_name.replace('/','-')

#maximum start date is one month from now for FREE plan
startdate=(datetime.now()-timedelta(days=100)).strftime("%Y-%m-%d")
enddate=datetime.now().strftime("%Y-%m-%d")

# Function to fetch the latest news about a stock symbol using NewsAPI
def fetch_latest_news(stock_symbol, count=100):
    
    APIKEY = 'bf79517bda9f4b01a3dd78b270d19a66'  # Replace with your NewsAPI key
    news_startdate=(datetime.now()-timedelta(days=30)).strftime("%Y-%m-%d")

    newsapi = NewsApiClient(api_key=APIKEY)
    all_articles = newsapi.get_everything(q=stock_keyword,
                                          language='en',
                                          sort_by='publishedAt',
                                          from_param=news_startdate,
                                          to=enddate,
                                          page_size=count,
                                          #page=
                                          )
    total_results=all_articles['totalResults']
    latest_news = []
    with Bar('fetching '+stock_symbol+' news', max=len(all_articles['articles'])) as bar:
        for article in all_articles['articles']:
            date=article['publishedAt'][:10] # extract "YYYY-MM-DD"
            title = article['title']
            description=article['description']
            # date = datetime.datetime.strptime(article['publishedAt'], "%Y-%m-%dT%H:%M:%SZ").date()
            latest_news.append((date, title, description))
            bar.next()
    
    return latest_news
    

# Function to analyze sentiment of news headlines
def analyze_sentiment(headlines):
    sentiment_pipeline = pipeline("sentiment-analysis", model=model_id, tokenizer=tokenizer)
    sentiments = sentiment_pipeline(headlines)
    
    return [(headline, sentiment['label'].upper(), sentiment['score']) for headline, sentiment in zip(headlines, sentiments)]


def apply_news_sentiment_color(sentiment):
    if sentiment=='POSITIVE':
        return 'Green','^'
    elif sentiment=='NEGATIVE':
        return 'Red','v'
    else: # NEUTRAL
        return 'skyblue','o'  
       
        
# Fetch the latest news
news = fetch_latest_news(stock_symbol)

headlines = [headline for date, headline, description in news]


# Analyze sentiment of the headlines
sentiment_results = analyze_sentiment(headlines)

news_sentiment=pd.DataFrame(columns=[
    'Date',
    'Headline',
    'Description',
    'Sentiment', 
    'Score'])

# add each headline news to DataFrame
for (date, headline, description), (headline_text, sentiment, score) in zip(news, sentiment_results):
    news_sentiment = pd.concat([news_sentiment,
        pd.DataFrame({
            'Date':pd.to_datetime(date),#.strftime('%Y-%m-%d'),
            'Sentiment':sentiment,
            'Score':round(score,3),
            'Headline':headline,
            'Description':description,

            }, index=[0])])

news_sentiment = news_sentiment.sort_values(by='Date')
news_sentiment.index=news_sentiment['Date']

# Save the news !!
news_sentiment.to_csv(f'./news/{stock_symbol}_news_sentiment_{startdate}_{enddate}.csv',index=False)

# Fetch stock price data
hist = yf.download(stock_symbol, start=startdate, end=enddate)
all_days = pd.date_range(hist.index.min(), hist.index.max(), freq='D')
hist=hist.reindex(all_days)
hist=hist.ffill()
hist['Date']=hist.index

ohlc = hist[['Date', 'Open', 'High', 'Low', 'Close']].copy()

hist.index = pd.DatetimeIndex(hist['Date'])#.strftime("%Y-%m-%d")
hist['Date'] = pd.to_datetime(hist.index).strftime("%Y-%m-%d")

    
fig, axes = plt.subplots( 2, 1, figsize=(12, 7), dpi=100, gridspec_kw={'height_ratios': [2, 1]})
ax = axes[0].twinx()

axes[1].bar(hist.index, hist['Volume'], width=0.6, color='grey',zorder=10, label='volume')
axes[0].plot(hist.index, hist['Close'],  color='blue',zorder=20,label='Close Price')


# Filter sentiment data based on the date range of the stock price data
# Overlay filtered sentiment data as scatter plot
for idx, row in news_sentiment.iterrows():
    color,marker=apply_news_sentiment_color(row['Sentiment'])
    ax.scatter(row['Date'], row['Score'], marker=marker, color=color, alpha=0.5,zorder=30)

# Customize the plot
plt.title(f'{stock_symbol} Stock Price & News')
# axes[0].tick_params(axis='x', rotation=90)

plt.legend(loc='upper left')
plt.grid(True,linewidth=1,color='gray')
plt.tight_layout()
plt.show()

# Save the image
fig.savefig(f'./news/{stock_symbol}_news_sentiment_{startdate}_{enddate}.jpg')

