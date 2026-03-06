import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import datetime

# =========================
# SETTINGS (EDIT ONLY HERE)
# =========================
START_CAPITAL = 1_000_000
LOOKBACK_YEARS = 10
SMA_MONTHS = 10
EQUITY_W_ON = 0.70

# FORCE OUTPUT DIRECTORY (CHANGE IF YOU WANT)
EXPORT_DIR = os.path.abspath("./plots")

# =========================
# DATA LOADER (STOOQ)
# =========================
def load_stooq(symbol):
    url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
    df = pd.read_csv(url)
    df["Date"] = pd.to_datetime(df["Date"])
    return df.set_index("Date")["Close"]

# =========================
# HELPERS
# =========================
def to_month_end(df):
    return df.resample("ME").last()

def sma(s, n):
    return s.rolling(n).mean()

def metals_split(w_metals, gsr):
    if gsr < 75:
        return w_metals, 0.0
    elif gsr < 85:
        return w_metals * 0.7, w_metals * 0.3
    else:
        return w_metals * 0.4, w_metals * 0.6

def base_weights(spy_on, gsr):
    w_spy = EQUITY_W_ON if spy_on else 0.0
    w_metals = 1 - w_spy
    w_gld, w_slv = metals_split(w_metals, gsr)
    return w_spy, w_gld, w_slv

# =========================
# MAIN
# =========================
def main():
    print("Loading data from Stooq...")

    spy = load_stooq("spy.us")
    gld = load_stooq("gld.us")
    slv = load_stooq("slv.us")
    gold = load_stooq("xauusd")
    silver = load_stooq("xagusd")

    df = pd.concat(
        [spy, gld, slv, gold, silver],
        axis=1,
        keys=["SPY", "GLD", "SLV", "GOLD", "SILVER"]
    ).dropna()

    m = to_month_end(df)
    m["GSR"] = m["GOLD"] / m["SILVER"]
    m["SPY_SMA"] = sma(m["SPY"], SMA_MONTHS)
    m = m.dropna()

    # ---- limit to last 10 years ----
    end = m.index[-1]
    start = end - pd.DateOffset(years=LOOKBACK_YEARS)
    m = m.loc[m.index >= start]

    # ---- simulate portfolio ----
    equity = [START_CAPITAL]
    labels = []

    for i in range(1, len(m)):
        prev = m.iloc[i - 1]
        spy_on = prev["SPY"] >= prev["SPY_SMA"]
        gsr = prev["GSR"]

        w_spy, w_gld, w_slv = base_weights(spy_on, gsr)
        label = f"{round(w_spy*100):.0f}/{round(w_gld*100):.0f}/{round(w_slv*100):.0f}"
        labels.append(label)

        r_spy = m.iloc[i]["SPY"] / prev["SPY"] - 1
        r_gld = m.iloc[i]["GLD"] / prev["GLD"] - 1
        r_slv = m.iloc[i]["SLV"] / prev["SLV"] - 1

        equity.append(
            equity[-1] * (1 + w_spy*r_spy + w_gld*r_gld + w_slv*r_slv)
        )

    m = m.iloc[1:]
    m["Equity"] = equity[1:]
    m["Label"] = labels

    # =========================
    # PLOT
    # =========================
    fig, ax = plt.subplots(
        figsize=(20, 12),
        constrained_layout=True
    )

    ax.plot(m.index, m["Equity"], linewidth=3, label="Strategy")
    ax.plot(m.index, START_CAPITAL * m["SPY"] / m["SPY"].iloc[0], "--", alpha=0.6, label="SPY")
    ax.plot(m.index, START_CAPITAL * m["GLD"] / m["GLD"].iloc[0], "--", alpha=0.6, label="GLD")
    ax.plot(m.index, START_CAPITAL * m["SLV"] / m["SLV"].iloc[0], "--", alpha=0.6, label="SLV")

    # ---- allocation annotations (only when changed) ----
    prev = None
    for dt, row in m.iterrows():
        if row["Label"] != prev:
            ax.text(
                dt, row["Equity"],
                row["Label"],
                fontsize=8,
                rotation=90,
                alpha=0.7,
                ha="center",
                va="bottom"
            )
            prev = row["Label"]

    ax.set_title("Strategy vs Buy & Hold (Last 10 Years)")
    ax.set_ylabel("Portfolio Value")
    ax.grid(True)
    ax.legend()

    # =========================
    # SAVE (GUARANTEED)
    # =========================
    os.makedirs(EXPORT_DIR, exist_ok=True)
    filename = f"strategy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    path = os.path.join(EXPORT_DIR, filename)

    fig.savefig(path, dpi=300)
    plt.close(fig)

    print("\n==============================")
    print("IMAGE SAVED SUCCESSFULLY")
    print(path)
    print("==============================\n")

# =========================
if __name__ == "__main__":
    main()
