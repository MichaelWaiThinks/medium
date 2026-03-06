# pip install transformers torch requests yfinance newsapi-python bokeh

import sys
import yfinance as yf
from newsapi import NewsApiClient
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from bokeh.plotting import figure, output_file, show
from bokeh.models import ColumnDataSource, HoverTool, DatetimeTickFormatter, Range1d, LinearAxis
from bokeh.io import output_notebook

# ---------------- Config ----------------
STOCK_SYMBOL = 'GC=F'
START_DATE   = '2021-01-01'
END_DATE     = datetime.now().strftime("%Y-%m-%d")
NEWSAPI_KEY  = 'bf79517bda9f4b01a3dd78b270d19a66'   # <-- replace with your key
NEWS_LOOKBACK_DAYS = 30                              # pull news for last N days
NEWS_PAGE_SIZE     = 100
HTML_OUT      = f'{STOCK_SYMBOL}_stock_chart.html'

# ---------------- Load FinBERT ----------------
model_name = "yiyanghkust/finbert-tone"
tokenizer  = AutoTokenizer.from_pretrained(model_name)
model      = AutoModelForSequenceClassification.from_pretrained(model_name)
sentiment_pipeline = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer)

# ---------------- Download price data ----------------
hist = yf.download(STOCK_SYMBOL, start=START_DATE, end=END_DATE)
if hist.empty:
    print('No data downloaded. Program abort...')
    sys.exit()

# Ensure proper datetime index and a Date column for Bokeh
hist.index = pd.to_datetime(hist.index)
all_days = pd.date_range(hist.index.min(), hist.index.max(), freq='D')
hist = hist.reindex(all_days).ffill()  # fill missing days (weekends) so searchsorted works
hist.index.name = "Date"
hist["Date"] = hist.index

# Optional: save for inspection
hist.to_csv('hist.csv')

# ---------------- News + sentiment ----------------
def fetch_latest_news(symbol: str, count=100):
    newsapi = NewsApiClient(api_key=NEWSAPI_KEY)
    news_startdate = (datetime.now() - timedelta(days=NEWS_LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    res = newsapi.get_everything(
        q=symbol,
        language='en',
        sort_by='publishedAt',
        from_param=news_startdate,
        to=END_DATE,
        page_size=count,
    )
    articles = res.get('articles', []) or []
    return [(a.get('publishedAt','')[:10], a.get('title',''), a.get('description','')) for a in articles]

def analyze_sentiment(headlines):
    if not headlines:
        return []
    res = sentiment_pipeline(headlines)
    # convert to (headline, LABEL, score)
    return [(h, r['label'].upper(), float(r['score'])) for h, r in zip(headlines, res)]

news = fetch_latest_news(STOCK_SYMBOL, NEWS_PAGE_SIZE)

if news:
    headlines = [h for d, h, desc in news]
    sentiments = analyze_sentiment(headlines)
    rows = []
    for (date_str, headline, desc), (_, label, score) in zip(news, sentiments):
        rows.append({
            "Date": pd.to_datetime(date_str),
            "Headline": headline,
            "Description": desc,
            "Sentiment": label,
            "Score": float(score),
        })
    news_sentiment = pd.DataFrame(rows).sort_values("Date").reset_index(drop=True)
else:
    news_sentiment = pd.DataFrame(columns=["Date","Headline","Description","Sentiment","Score"])

# ---------------- Map sentiment to a plot price (CloseP) ----------------
# We want the **first bar on/after** the news timestamp. Use searchsorted on hist.index.
def first_bar_on_or_after(ts: pd.Timestamp):
    pos = hist.index.searchsorted(ts)  # first index >= ts
    if pos >= len(hist):
        return None  # past the end
    return hist.iloc[pos]

closep_vals = []
for _, r in news_sentiment.iterrows():
    bar = first_bar_on_or_after(r["Date"])
    if bar is None:
        closep_vals.append(np.nan)
        continue
    if r["Sentiment"] == "POSITIVE":
        closep_vals.append(float(bar["High"]) + r["Score"])
    elif r["Sentiment"] == "NEGATIVE":
        closep_vals.append(float(bar["Low"]) - r["Score"])
    else:
        closep_vals.append(float(bar["Close"]) + r["Score"])

news_sentiment["CloseP"] = closep_vals

# Keep only points within chart range
news_sentiment = news_sentiment[(news_sentiment["Date"] >= hist["Date"].min()) &
                                (news_sentiment["Date"] <= hist["Date"].max())]

# Color map for scatter
sentiment_colors = {'POSITIVE': 'green', 'NEGATIVE': 'red', 'NEUTRAL': 'gold'}
news_sentiment["Color"] = news_sentiment["Sentiment"].map(sentiment_colors).fillna("gray")

# ---------------- Bokeh data sources ----------------
price_source    = ColumnDataSource(hist)
volume_source   = ColumnDataSource(data=dict(Date=hist["Date"], Volume=hist["Volume"]))
sentiment_source= ColumnDataSource(news_sentiment)

# ---------------- Candlestick helpers ----------------
inc = hist["Close"] > hist["Open"]
dec = hist["Open"] > hist["Close"]
hist["Color"] = np.where(inc, "green", "red")

# width ~ one day in ms
DAY_MS = 24 * 60 * 60 * 1000

# ---------------- Figure ----------------
p = figure(title=f'{STOCK_SYMBOL} Price & Volume',
           x_axis_type='datetime', height=450, width=950)

# Wick (high-low)
p.segment(x0='Date', y0='Low', x1='Date', y1='High',
          color='Color', source=price_source)

# Body (open-close)
p.vbar(x='Date', width=DAY_MS*0.7, top='Open', bottom='Close',
       fill_color='Color', line_color='Color',
       source=ColumnDataSource(hist[inc]))

p.vbar(x='Date', width=DAY_MS*0.7, top='Close', bottom='Open',
       fill_color='Color', line_color='Color',
       source=ColumnDataSource(hist[dec]))

# Right axis for volume
p.extra_y_ranges = {"Volume": Range1d(start=0, end=float(hist['Volume'].max()) * 1.5)}
p.add_layout(LinearAxis(y_range_name="Volume", axis_label="Volume"), 'right')

# Volume bars
p.vbar(x='Date', top='Volume', width=DAY_MS*0.7,
       source=volume_source, color='gray', alpha=0.45, y_range_name="Volume")

# Sentiment scatter
sentiment_scatter = p.scatter(x='Date', y='CloseP', color='Color',
                              source=sentiment_source, legend_field='Sentiment',
                              size=9, alpha=0.75)

# ---------------- Hovers ----------------
hover_candles = HoverTool(
    tooltips=[
        ('Date', '@Date{%F}'),
        ('Open', '@Open{0,0.00}'),
        ('High', '@High{0,0.00}'),
        ('Low', '@Low{0,0.00}'),
        ('Close', '@Close{0,0.00}'),
        ('Volume', '@Volume{0,0}'),
    ],
    formatters={'@Date': 'datetime'},
    mode='vline'
)
p.add_tools(hover_candles)

hover_news = HoverTool(
    renderers=[sentiment_scatter],
    tooltips=[
        ('Date', '@Date{%F}'),
        ('Sentiment', '@Sentiment'),
        ('Score', '@Score{0.000}'),
        ('Headline', '@Headline'),
        ('Description', '@Description')
    ],
    formatters={'@Date': 'datetime'},
)
p.add_tools(hover_news)

# ---------------- Axes/legend formatting ----------------
p.xaxis.axis_label = 'Date'
p.yaxis.axis_label = 'Price'
p.xaxis.formatter = DatetimeTickFormatter(days="%Y-%m-%d", months="%Y-%m", years="%Y")
p.legend.location = "top_left"
p.legend.click_policy = "hide"
p.grid.grid_line_alpha = 0.25
p.y_range = Range1d(start=float(hist['Low'].min()) * 0.98,
                    end=float(hist['High'].max()) * 1.02)

# ---------------- Output ----------------
output_file(HTML_OUT)
output_notebook()  # comment out if you're not in a notebook
show(p)
print(f"Saved chart → {HTML_OUT}")