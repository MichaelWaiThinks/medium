import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# -----------------------------------
# ETF universe
# -----------------------------------

tickers = [
"SCHD","VYM","HDV","DGRO","JEPI","JEPQ","VOO", "VTI","QQQ","SPY",
"DIVO","VIG","SPYD","VNQ","QYLD","XYLD","NOBL"
]

start = "2015-01-01"
investment = 100000
risk_free_rate = 0.02

# -----------------------------------
# Download prices
# -----------------------------------

prices = yf.download(tickers,start=start,auto_adjust=True)["Close"]

returns = prices.pct_change().dropna()

results = []

for t in tickers:

    price = prices[t].dropna()
    ret = returns[t].dropna()

    years = len(price)/252
    total_return = ((price.iloc[-1]/price.iloc[0])**(1/years)-1)*100

    volatility = ret.std()*np.sqrt(252)

    sharpe = (total_return-risk_free_rate)/volatility

    drawdown = (price/price.cummax()-1).min()

    info = yf.Ticker(t).info

    yield_est = info.get("dividendYield",0)
    if yield_est is None:
        yield_est = 0

    annual_income = investment * yield_est
    monthly_income = annual_income/12

    results.append({
        "ETF":t,
        "DividendYield":yield_est,
        "TotalReturn":total_return,
        "Volatility":volatility,
        "Sharpe":sharpe,
        "MaxDrawdown":drawdown,
        "AnnualIncome_100k":annual_income,
        "MonthlyIncome_100k":monthly_income
    })

df = pd.DataFrame(results)

# -----------------------------------
# Normalize scores
# -----------------------------------

def normalize(series):
    return (series-series.min())/(series.max()-series.min())

df["Return_score"] = normalize(df["TotalReturn"])
df["Yield_score"] = normalize(df["DividendYield"])
df["Risk_score"] = 1-normalize(df["Volatility"])
df["Drawdown_score"] = 1-normalize(df["MaxDrawdown"])

# composite score
df["Score"] = (
0.35*df["Return_score"]+
0.30*df["Yield_score"]+
0.20*df["Risk_score"]+
0.15*df["Drawdown_score"]
)

df = df.sort_values("Score",ascending=False)

# -----------------------------------
# Save ranking
# -----------------------------------

df.to_csv("dividend_etf_ranking.csv",index=False)

print("\nETF Ranking\n")
print(df[["ETF","Score","DividendYield","TotalReturn"]])

# -----------------------------------
# Income projection
# -----------------------------------

income_table = df[["ETF","DividendYield","AnnualIncome_100k","MonthlyIncome_100k"]]
income_table.to_csv("dividend_income_projection.csv",index=False)

# -----------------------------------
# Yield vs Drawdown bar chart
# -----------------------------------

plt.figure(figsize=(12,7))

x = np.arange(len(df))

yield_vals = df["DividendYield"] * 100
drawdown_vals = df["MaxDrawdown"] * 100

# draw bars
plt.bar(x, yield_vals, label="Dividend Yield (%)")
plt.bar(x, drawdown_vals, label="Max Drawdown (%)")

plt.axhline(0, color="black", linewidth=1)

plt.xticks(x, df["ETF"], rotation=45)

plt.title("Dividend Yield vs Max Drawdown")
plt.ylabel("Percent")

plt.legend()
plt.grid(axis="y", alpha=0.3)

plt.tight_layout()
plt.show()

# -----------------------------------
# Best ETF
# -----------------------------------

best = df.iloc[0]

print("\nBest ETF based on model:\n")
print(best["ETF"])
print("Score:",best["Score"])
print("Yield:",best["DividendYield"])
print("Expected monthly income per $100k:",best["MonthlyIncome_100k"])