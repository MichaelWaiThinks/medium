#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf

ASSET_TICKER = 'GC=F'
# === Load your Excel ===
file_path = "查詢1971-07-31至2025-10-31中原城市領先指數.xlsx"
df = pd.read_excel(file_path, sheet_name="中原城市領先指數")

def get_end_date(period):
    if isinstance(period, str) and "-" in period:
        return pd.to_datetime(period.split("-")[-1].strip(), errors="coerce")
    return pd.NaT

# Find the period and index columns
col_period = [c for c in df.columns if "-" in str(df[c].dropna().iloc[0]) or "至" in str(df[c].dropna().iloc[0])][0]
col_value  = [c for c in df.columns if ("指數" in c) or ("CCL" in c)][0]


# Weekly -> Date (week end)
df["Date"] = df[col_period].apply(get_end_date)
df = df[["Date", col_value]].dropna().rename(columns={col_value: "CCL"})
df = df.sort_values("Date").set_index("Date")

# Expand weekly to daily + ffill
daily_index = pd.date_range(df.index.min(), df.index.max(), freq="D")
ccl_daily = df.reindex(daily_index).ffill()

# === Gold (HKD) via spot gold × FX ===
start_date, end_date = ccl_daily.index.min(), ccl_daily.index.max()


def get_gold_hkd(start, end):
    """Download gold price in HKD/oz (auto-handles MultiIndex)."""
    import pandas as pd
    import yfinance as yf

    def flatten(df):
        """If MultiIndex columns exist, keep only first level."""
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df

    # 1️⃣ Try spot gold first
    gold = flatten(yf.download(ASSET_TICKER, start=start, end=end, progress=False, group_by="column"))
    if "Close" in gold.columns:
        s_gold_usd = gold["Close"].copy()
        s_gold_usd.name = "Gold_USD"
    else:
        # 2️⃣ Fallback to COMEX futures
        gold = flatten(yf.download(ASSET_TICKER, start=start, end=end, progress=False, group_by="column"))
        if "Close" in gold.columns:
            s_gold_usd = gold["Close"].copy()
            s_gold_usd.name = "Gold_USD"
        else:
            raise RuntimeError("No gold price data found for ASSET_TICKER or ASSET_TICKER")

    # 3️⃣ Download USD/HKD FX
    fx = flatten(yf.download("HKD=X", start=start, end=end, progress=False, group_by="column"))
    if "Close" not in fx.columns:
        raise RuntimeError("Could not retrieve USDHKD=X from Yahoo Finance")
    s_usdhkd = fx["Close"].copy()
    s_usdhkd.name = "USDHKD"
    print(s_usdhkd)

    # 4️⃣ Merge & compute HKD gold
    gold_hkd_df = pd.concat([s_gold_usd, s_usdhkd], axis=1).dropna()
    gold_hkd_df["Gold_HKD"] = gold_hkd_df["Gold_USD"] * gold_hkd_df["USDHKD"]
    return gold_hkd_df["Gold_HKD"]


gold_hkd = get_gold_hkd(start_date, end_date)
gold_hkd = gold_hkd.reindex(daily_index).ffill()

# === Ratio = CCI / Gold(HKD) ===
ratio = (ccl_daily["CCL"] / gold_hkd).rename("CCI_to_Gold")
ratio = ratio.replace([float("inf"), -float("inf")], pd.NA).dropna()
# === Plot 3 subplots: Ratio, CCI, Gold ===
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12,10), sharex=True)

# --- (1) Ratio: CCI ÷ Gold(HKD) ---
ax3.plot(ratio.index, ratio.values, color="tab:blue", linewidth=1.2, label="CCI ÷ Gold (HKD/oz)")
ax3.set_title("Hong Kong CCI vs Gold (HKD/oz) — Ratio, Index, and Gold Price (1997–2025)")
ax3.set_ylabel("CCI ÷ Gold (oz equivalent)")
ax3.grid(True, linestyle="--", alpha=0.6)
ax3.legend(loc="upper left")

# --- (2) CCI Index ---
ax1.plot(ccl_daily.index, ccl_daily["CCL"], color="tab:green", linewidth=1.2, label="CCI Index")
ax1.set_ylabel("CCI Index")
ax1.grid(True, linestyle="--", alpha=0.6)
ax1.legend(loc="upper left")

# --- (3) Gold Price (HKD/oz) ---
ax2.plot(gold_hkd.index, gold_hkd.values, color="tab:orange", linewidth=1.2, label="Gold Price (HKD/oz)")
ax2.set_xlabel("Year")
ax2.set_ylabel("Gold Price (HKD/oz)")
ax2.grid(True, linestyle="--", alpha=0.6)
ax2.legend(loc="upper left")

plt.tight_layout()
plt.savefig("CCI_Gold_3subplot.png", dpi=300)
plt.show()