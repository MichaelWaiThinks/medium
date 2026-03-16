#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Explosive Innovation Screener
- NASDAQ universe
- Behaviour similarity detection
- UMAP cluster visualization
"""

import os
import json
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import umap
from datetime import datetime, timedelta
from tqdm import tqdm
import matplotlib.pyplot as plt
from scipy.spatial import ConvexHull

# ---------------- SETTINGS ----------------

CACHE_FILE = "price_cache.csv"
META_FILE = "cache_meta.json"
NASDAQ_FILE = "nasdaq.csv"

TARGETS = [
    "CRSP", "NTLA", "BEAM", "RXRX", "MRNA", "PACB", "DNA",
    "UPST", "ROOT", "SOFI", "AFRM", "TDOC", "TWST", "ALNY", "ARCT", "AXSM"
]

# Example:
TARGETS = ["TSLA", "META", "MSFT", "AAPL", "NFLX", "NVDA", "AMZN", "SNDK"]

DOWNLOAD_LIMIT = None
CACHE_DAYS = 30
NASDAQ_CACHE_DAYS = 90
RANDOM_SEED = 42

# Lower this if your target basket is broad and you want more results
MIN_CORRELATION = 0.03

# ---------------- UTIL ----------------

def safe_round(v, n=3):
    try:
        return round(float(v), n)
    except Exception:
        return np.nan


# ---------------- CLUSTER PLOT ----------------

def plot_screener_cluster(data, screener_df, targets, top_n=40):
    candidates = screener_df.head(top_n)["ticker"].tolist()
    stocks = list(set(candidates + targets))
    stocks = [s for s in stocks if s in data.columns]

    if len(stocks) < 3:
        print("Not enough stocks to plot cluster.")
        return

    sub = data[stocks]
    # returns = sub.pct_change(fill_method=None).dropna()
    returns = data.pct_change(fill_method=None).dropna(how="all")
    if returns.empty or returns.shape[1] < 3:
        print("Not enough return data to plot cluster.")
        return

    corr = returns.corr()
    corr = corr.replace([np.inf, -np.inf], np.nan).dropna(axis=0, how="any").dropna(axis=1, how="any")

    if corr.shape[0] < 3:
        print("Not enough correlation data to plot cluster.")
        return

    dist_matrix = 1 - corr.clip(-1, 1)

    reducer = umap.UMAP(
        n_neighbors=min(20, max(2, corr.shape[0] - 1)),
        min_dist=0.25,
        metric="precomputed",
        random_state=42
    )

    coords = reducer.fit_transform(dist_matrix)

    df_plot = pd.DataFrame(coords, columns=["x", "y"])
    df_plot["ticker"] = corr.columns

    fig = plt.figure(figsize=(12, 9))
    ax = plt.gca()

    for target in targets:
        if target not in df_plot["ticker"].values:
            continue

        trow = df_plot[df_plot["ticker"] == target].iloc[0]
        tx, ty = trow["x"], trow["y"]

        euclid_dist = np.sqrt((df_plot["x"] - tx) ** 2 + (df_plot["y"] - ty) ** 2)
        neighbors = df_plot.loc[euclid_dist.nsmallest(min(10, len(df_plot))).index]

        points = neighbors[["x", "y"]].values

        if len(points) >= 3:
            try:
                hull = ConvexHull(points)
                hull_points = points[hull.vertices]
                ax.fill(
                    hull_points[:, 0],
                    hull_points[:, 1],
                    color="orange",
                    alpha=0.12
                )
            except Exception:
                pass

    for _, row in df_plot.iterrows():
        x = row["x"]
        y = row["y"]
        ticker = row["ticker"]

        if ticker in targets:
            plt.scatter(x, y, color="red", s=130)
            plt.text(x, y, ticker, fontsize=10, weight="bold")
        else:
            plt.scatter(x, y, color="steelblue", s=40)

    plt.title("Innovation Behaviour Map")
    plt.xlabel("UMAP-1")
    plt.ylabel("UMAP-2")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    fig.savefig("innovation_cluster_map.png", dpi=200, bbox_inches="tight")
    plt.show()


# ---------------- CACHE ----------------

def cache_valid():
    if not os.path.exists(CACHE_FILE):
        return False

    if not os.path.exists(META_FILE):
        return False

    with open(META_FILE, "r") as f:
        meta = json.load(f)

    last_update = datetime.strptime(meta["date"], "%Y-%m-%d")

    if datetime.now() - last_update > timedelta(days=CACHE_DAYS):
        return False

    return True


# ---------------- NASDAQ LIST ----------------

def get_nasdaq_tickers():
    if os.path.exists(NASDAQ_FILE):
        file_time = datetime.fromtimestamp(os.path.getmtime(NASDAQ_FILE))

        if datetime.now() - file_time < timedelta(days=NASDAQ_CACHE_DAYS):
            print("Loading NASDAQ tickers from cache...")
            df = pd.read_csv(NASDAQ_FILE)
            return df["symbol"].dropna().astype(str).str.strip().tolist()

    print("Downloading NASDAQ tickers...")

    url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&download=true"
    headers = {"User-Agent": "Mozilla/5.0"}

    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    payload = r.json()

    rows = payload["data"]["rows"]
    df = pd.DataFrame(rows)
    df.columns = df.columns.str.lower()

    df["marketcap"] = pd.to_numeric(df["marketcap"], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
    df["lastsale"] = pd.to_numeric(
        df["lastsale"].astype(str).str.replace("$", "", regex=False).str.replace(",", "", regex=False),
        errors="coerce"
    )

    name = df["name"].astype(str).str.lower()

    df = df[
        (~name.str.contains("etf", na=False)) &
        (~name.str.contains("fund", na=False)) &
        (~name.str.contains("trust", na=False)) &
        (~name.str.contains("adr", na=False)) &
        (~name.str.contains("warrant", na=False)) &
        (~name.str.contains("unit", na=False)) &
        (~name.str.contains("preferred", na=False))
    ]

    df = df[
        (df["lastsale"] > 100) &
        # (df["marketcap"] > 50_000_000) &
        (df["marketcap"] > 100_000_000_000) &
        (df["volume"] > 200_000_000)
    ]

    tickers = df["symbol"].dropna().astype(str).str.strip().tolist()
    tickers = [t for t in tickers if "." not in t and "/" not in t and "^" not in t]
    tickers = sorted(set(tickers))

    pd.DataFrame({"symbol": tickers}).to_csv(NASDAQ_FILE, index=False)

    print("Filtered NASDAQ universe:", len(tickers))
    return tickers


# ---------------- DOWNLOAD ----------------

def download_data(tickers, save_cache=True):
    if not tickers:
        return pd.DataFrame()

    batch = 200
    frames = []

    for i in range(0, len(tickers), batch):
        group = tickers[i:i + batch]
        print("Downloading", i, "to", i + len(group))

        raw = yf.download(
            group,
            period="2y",
            interval="1d",
            auto_adjust=True,
            progress=True,
            threads=False
        )

        if raw.empty:
            continue

        if isinstance(raw.columns, pd.MultiIndex):
            if "Close" not in raw.columns.get_level_values(0):
                continue
            df = raw["Close"].copy()
        else:
            if "Close" in raw.columns:
                df = raw[["Close"]].copy()
                if len(group) == 1:
                    df.columns = [group[0]]
            else:
                continue

        frames.append(df)

    if not frames:
        return pd.DataFrame()

    data = pd.concat(frames, axis=1)
    data = data.loc[:, ~data.columns.duplicated()]
    data = data.dropna(axis=1, how="all")

    print("Downloaded", len(data.columns), "stocks")

    if save_cache:
        data.to_csv(CACHE_FILE)
        meta = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "tickers": list(data.columns)
        }
        with open(META_FILE, "w") as f:
            json.dump(meta, f)

    return data


def load_cached():
    print("Loading cached price data...")
    return pd.read_csv(CACHE_FILE, index_col=0, parse_dates=True)


# ---------------- SCREENER ----------------
def run_screener(data, targets, universe):
    returns = data.pct_change(fill_method=None).dropna(how="all")

    valid_targets = [t for t in targets if t in returns.columns]

    print("Targets in dataset:", valid_targets)
    print("data shape:", data.shape)
    print("returns shape:", returns.shape)

    if len(valid_targets) == 0:
        print("No valid targets in dataset")
        return pd.DataFrame()

    results = []

    for stock in tqdm(universe, desc="Scanning"):
        if stock in targets:
            continue
        if stock not in returns.columns:
            continue

        series = returns[stock].dropna()

        if len(series) < 200:
            continue

        best_distance = np.inf
        best_corr = None
        best_target = None

        for target in valid_targets:
            if stock == target:
                continue

            tseries = returns[target].dropna()
            common = series.index.intersection(tseries.index)

            if len(common) < 100:
                continue

            corr = series.loc[common].corr(tseries.loc[common])

            if pd.isna(corr):
                continue

            distance = 1 - corr

            if distance < best_distance:
                best_distance = distance
                best_corr = corr
                best_target = target

        if best_corr is None:
            continue

        momentum = series.mean() * 100
        vol = series.std()
        vol_ratio = series.tail(30).std() / vol if vol > 0 else 0
        score = (best_corr * 0.6) + (vol_ratio * 0.25) + (momentum * 0.15)

        results.append({
            "ticker": stock,
            "closest_target": best_target,
            "correlation": safe_round(best_corr),
            "distance": safe_round(best_distance),
            "momentum_daily_%": safe_round(momentum),
            "vol_ratio": safe_round(vol_ratio),
            "score": safe_round(score)
        })

    df = pd.DataFrame(results)

    if df.empty:
        return df

    df = df.sort_values(["correlation", "score"], ascending=[False, False]).reset_index(drop=True)
    return df
# ---------------- MAIN ----------------

def main():
    tickers = get_nasdaq_tickers()

    if DOWNLOAD_LIMIT:
        rng = np.random.default_rng(RANDOM_SEED)
        universe = rng.choice(tickers, size=DOWNLOAD_LIMIT, replace=False).tolist()
    else:
        universe = tickers

    all_tickers = sorted(set(TARGETS + universe))
    print("Universe to request:", len(all_tickers), "tickers")

    if cache_valid():
        data = load_cached()

        missing = [t for t in all_tickers if t not in data.columns]
        if missing:
            print("Downloading missing targets:", missing)
            new = download_data(missing, save_cache=False)

            if not new.empty:
                data = pd.concat([data, new], axis=1)
                data = data.loc[:, ~data.columns.duplicated()]

                data.to_csv(CACHE_FILE)
                meta = {
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "tickers": list(data.columns)
                }
                with open(META_FILE, "w") as f:
                    json.dump(meta, f)
    else:
        data = download_data(all_tickers, save_cache=True)
    data = data.dropna(axis=1, thresh=len(data)*0.7)
    if data.empty:
        print("No data available.")
        return

    data = data.loc[:, ~data.columns.duplicated()]
# =============================================================================
#     # data = data.dropna(axis=1, thresh=200)
# =============================================================================

    df = run_screener(data, TARGETS, universe)

    if df.empty:
        print("No screener results found.")
        return

    plot_screener_cluster(data, df, TARGETS, top_n=100)

    print("\nTop similar stocks:\n")
    print(df.head(20))

    df["rank"] = range(1, len(df) + 1)
    df.head(50).to_csv("explosive_candidates.csv", index=False)
    df.to_csv("innovation_cluster_candidates.csv", index=False)

    # create comma-separated ticker string
    ticker_string = " ".join(df["ticker"].head(20).str.lower())
    
    print("\nTicker list:")
    print(ticker_string)
    
    # optional: save to file
    with open("ticker_list.txt", "w") as f:
        f.write(ticker_string)

if __name__ == "__main__":
    main()