#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TICKER — Elliott-like I–V cycles + ABC(+X) with auto-relax AND continued partial count
- Finds validated complete I–V cycles (with ABC(+X) corrections).
- If 0 cycles, auto-relaxes filters (and optionally ZigZag threshold) and retries.
- Always annotates detected I–V + A/B/C/X.
- Continues counting the **current partial wave** (I..V) with "(?)" labels and cyan styling.

This version ENFORCES "Wave IV must not overlap Wave I" (IV_low > I_high)
in ALL modes (base + relaxed), and also post-filters cycles as a safety net.
"""

import numpy as np, pandas as pd, yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ---------------- Base Config ----------------
TICKERS     = ["XAU=X", "GC=F", "XAU=X", "IAU"]
YEARS_BACK  = 80
INTERVAL    = "1d"
RESAMPLE    = "W-FRI"      # set to None for daily data
ZZ_PCT      = 12.0         # higher → fewer swings
LOG_SCALE   = False

# Cycle quality filters (for COMPLETE cycles)
MIN_YEARS   = 1.0          # I→V min span (years)
MIN_GAIN    = 0.50         # (V/I - 1)

# Elliott rule tolerances (complete impulse validation)
STRICT_NO_OVERLAP = True   # enforce IV low > I high
TOL_PX      = 0        # ~0.2% price tolerance
TOL_LEN     = 0.10         # 10% tolerance for "Wave 3 not the shortest"

SAVE_PNG    = f"{TICKERS[0]}_cycles_auto_relax_with_partial.png"

# ---------------- Data ----------------
def download_close():
    end = pd.Timestamp.today().normalize()
    start = end - pd.DateOffset(years=YEARS_BACK)
    last_err = None
    for t in TICKERS:
        try:
            df = yf.download(t, start=start, end=end + pd.Timedelta(days=1),
                             interval=INTERVAL, auto_adjust=True, progress=False,
                             group_by="column", threads=False)
            if df is None or df.empty or "Close" not in df.columns:
                continue
            close = df["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.squeeze("columns")
            s = close.dropna().astype(float)
            if not s.empty:
                print(f"Ticker using {t} (rows={len(s)})")
                return s.rename("Gold")
        except Exception as e:
            last_err = e
    raise RuntimeError(f"Could not download ticker. Last error: {last_err}")

def build_pivots(series, zz_pct):
    def zigzag(series, pct=10.0):
        s = series.dropna()
        if s.empty: return []
        p_last = s.iloc[0]; i_last = s.index[0]
        trend = 0
        pivots = [(i_last, float(p_last))]
        for i, p in s.iloc[1:].items():
            chg = (p - p_last) / p_last * 100.0
            if trend >= 0:
                if chg >= 0:
                    p_last, i_last = p, i
                    pivots[-1] = (i_last, float(p_last))
                elif chg <= -pct:
                    pivots.append((i, float(p)))
                    p_last, i_last = p, i
                    trend = -1
            if trend <= 0:
                if chg <= 0:
                    p_last, i_last = p, i
                    pivots[-1] = (i_last, float(p_last))
                elif chg >= pct:
                    pivots.append((i, float(p)))
                    p_last, i_last = p, i
                    trend = +1
        out = []
        for pt in pivots:
            if not out or out[-1][0] != pt[0]:
                out.append(pt)
        return out

    piv = zigzag(series, pct=zz_pct)
    piv_df = pd.DataFrame(piv, columns=["Date", "Price"]).set_index("Date")

    # polarity tags among pivots
    pol = []
    for i in range(len(piv_df)):
        p  = piv_df["Price"].iloc[i]
        pl = piv_df["Price"].iloc[i-1] if i-1 >= 0 else p
        pr = piv_df["Price"].iloc[i+1] if i+1 < len(piv_df) else p
        if p <= pl and p <= pr: pol.append("low")
        elif p >= pl and p >= pr: pol.append("high")
        else: pol.append("flat")
    piv_df["Pol"] = pol

    seq = [(idx, float(row.Price), row.Pol) for idx, row in piv_df.iterrows()]
    # seq item = (datetime, price, 'low'/'high'/'flat')
    return piv_df, seq

# ---------------- Elliott validation (complete cycles) ----------------
def is_valid_impulse(p1, p2, p3, p4, p5, p6,
                     tol_px=0.002, tol_len=0.05, no_overlap=True):
    # Rising highs/lows
    if not (p2*(1+tol_px) < p4 and p4*(1+tol_px) < p6): return False
    if not (p1*(1+tol_px) < p3 and p3*(1+tol_px) < p5): return False
    # Optional: IV above I high (no-overlap rule)
    if no_overlap and not (p5 > p2*(1 - tol_px)): return False
    # Wave 3 not shortest
    len1, len3, len5 = p2-p1, p4-p3, p6-p5
    if min(len1, len3, len5) <= 0: return False
    if len3 < min(len1, len5) * (1 - tol_len): return False
    return True

# ---------------- Extract validated COMPLETE cycles ----------------
def extract_cycles(seq_all, min_years, min_gain,
                   tol_px, tol_len, no_overlap):
    """Pattern: low→high→low→high→low→high with Elliott validation."""
    cycles = []
    i, n = 0, len(seq_all)
    while i < n:
        while i < n and seq_all[i][2] != "low":
            i += 1
        if i >= n: break
        need = ["low","high","low","high","low","high"]
        picked, j = [], i
        for want in need:
            found = None
            while j < n:
                dt, px, pol = seq_all[j]; j += 1
                if pol == want:
                    found = (dt, px, pol, j-1); break
            if found is None:
                i += 1; break
            picked.append(found)
        if len(picked) < 6:
            continue
        (d1,p1,_,i1),(d2,p2,_,i2),(d3,p3,_,i3),(d4,p4,_,i4),(d5,p5,_,i5),(d6,p6,_,i6) = picked
        years = (d6 - d1).days / 365.25
        gain  = (p6 / p1) - 1.0 if p1 > 0 else 0.0
        if not is_valid_impulse(p1,p2,p3,p4,p5,p6, tol_px, tol_len, no_overlap):
            i += 1; continue
        if years >= min_years and gain >= min_gain:
            cycles.append({
                "I_low":(d1,p1,i1), "I_high":(d2,p2,i2), "II_low":(d3,p3,i3),
                "III_high":(d4,p4,i4), "IV_low":(d5,p5,i5), "V_high":(d6,p6,i6),
                "years":years, "gain":gain
            })
            i = i6 + 1
        else:
            i += 1
    return cycles

# ---------- Extra safety: enforce IV not below I (post-filter) ----------
def enforce_no_overlap(cycles, tol_px):
    """Keep only cycles with IV_low > I_high (within tolerance)."""
    kept = []
    for c in cycles:
        iv_low  = c["IV_low"][1]
        i_high  = c["I_high"][1]
        if iv_low > i_high * (1 - tol_px):
            kept.append(c)
    return kept

# ---------------- Corrections after V (for complete cycles) ----------------
def find_abc_after(seq_all, v_index):
    n = len(seq_all); i = v_index + 1
    while i < n and seq_all[i][2] != "low":  i += 1
    if i >= n: return {}
    A = (seq_all[i][0], seq_all[i][1], i); i += 1
    while i < n and seq_all[i][2] != "high": i += 1
    if i >= n: return {}
    B = (seq_all[i][0], seq_all[i][1], i); i += 1
    while i < n and seq_all[i][2] != "low":  i += 1
    if i >= n: return {}
    C = (seq_all[i][0], seq_all[i][1], i)
    return {"A":A,"B":B,"C":C}

def find_abc_x_abc(seq_all, v_index):
    out = {}
    abc1 = find_abc_after(seq_all, v_index)
    if not abc1: return out
    out["ABC1"] = abc1
    c1_idx = abc1["C"][2]
    i = c1_idx + 1; n = len(seq_all)
    while i < n and seq_all[i][2] != "high": i += 1
    if i < n:
        out["X"] = (seq_all[i][0], seq_all[i][1], i)
        abc2 = find_abc_after(seq_all, i)
        if abc2: out["ABC2"] = abc2
    return out

# ---------------- PARTIAL (continued) cycle inference ----------------
def infer_current_partial(seq_all, tol_px=0.002, enforce_no_overlap=True):
    """
    Greedy inference of the latest impulse from recent pivots.
    Returns labels for I_low..V_high (subset), plus current_wave/direction/complete.
    Enforces IV_low > I_high (within tol_px) if enforce_no_overlap=True.
    """
    if len(seq_all) < 2:
        return {}

    # Try up to 3 anchors (walk back recent lows) until overlap is satisfied
    tries = 0
    k_end = max(-1, len(seq_all) - 12)  # lookback window for anchor lows
    for anchor in range(len(seq_all)-1, k_end, -1):
        if seq_all[anchor][2] != "low":
            continue
        tries += 1

        expected = [("I_low","low"), ("I_high","high"), ("II_low","low"),
                    ("III_high","high"), ("IV_low","low"), ("V_high","high")]
        labels = {"I_low": (seq_all[anchor][0], seq_all[anchor][1], anchor)}
        i = anchor; want_idx = 1
        while want_idx < len(expected) and i < len(seq_all)-1:
            want_name, want_pol = expected[want_idx]
            i += 1
            while i < len(seq_all) and seq_all[i][2] != want_pol:
                i += 1
            if i >= len(seq_all):
                break
            labels[want_name] = (seq_all[i][0], seq_all[i][1], i)
            want_idx += 1

        # If we don't even have I_high yet, try another anchor
        if "I_high" not in labels:
            continue

        # Enforce IV above I high for partials if requested (when IV is present)
        if enforce_no_overlap and "IV_low" in labels:
            iv_low  = labels["IV_low"][1]
            i_high  = labels["I_high"][1]
            if iv_low <= i_high * (1 - tol_px):
                # overlap violation → try an earlier/later anchor
                continue

        # Build result
        got = list(labels.keys())
        last_key = got[-1]
        mapping = {
            "I_low":"I (up)", "I_high":"II (down)",
            "II_low":"III (up)", "III_high":"IV (down)",
            "IV_low":"V (up)", "V_high":"V (done)"
        }
        label = mapping.get(last_key, "I (up)")
        return {
            "labels": labels,
            "current_wave": label.split()[0],
            "direction": "up" if "up" in label else ("down" if "down" in label else "unknown"),
            "complete": (last_key == "V_high")
        }

    # If all anchors failed
    return {}

def infer_partial_fallback(seq_all, tol_px=0.002, need=6, enforce_no_overlap=True):
    """
    Best-effort last-N pivots labelling with optional overlap enforcement.
    """
    if len(seq_all) < 2:
        return {}
    tail = seq_all[-need:]
    labels_order = ["I_low","I_high","II_low","III_high","IV_low","V_high"]
    if tail[0][2] == "high":
        labels_order = ["I_high","II_low","III_high","IV_low","V_high","_"]

    labels = {}
    for (dt, px, pol), name in zip(tail, labels_order):
        if name == "_":
            break
        labels[name] = (dt, px, None)

    if "I_high" not in labels:
        return {}

    if enforce_no_overlap and "IV_low" in labels:
        iv_low  = labels["IV_low"][1]
        i_high  = labels["I_high"][1]
        if iv_low <= i_high * (1 - tol_px):
            return {}  # reject fallback if it violates overlap

    got = list(labels.keys())
    last_key = got[-1]
    mapping = {
        "I_low":"I (up)", "I_high":"II (down)",
        "II_low":"III (up)", "III_high":"IV (down)",
        "IV_low":"V (up)", "V_high":"V (done)"
    }
    label = mapping.get(last_key, "I (up)")
    return {
        "labels": labels,
        "current_wave": label.split()[0],
        "direction": "up" if "up" in label else ("down" if "down" in label else "unknown"),
        "complete": (last_key == "V_high")
    }
# ---------------- Best-fit score ----------------
def cycle_score(c):  # duration × (1+gain)
    return c["years"] * (1.0 + c["gain"])

# ---------------- Run detection (with auto-relax) ----------------
g = download_close()
if RESAMPLE:
    g = g.resample(RESAMPLE).last().dropna()

piv_df, seq_all = build_pivots(g, ZZ_PCT)
print(f"Pivots detected: {len(piv_df)} (ZZ={ZZ_PCT}%, resample={RESAMPLE or 'Daily'})")

# Base extraction (no-overlap enforced)
cycles = extract_cycles(seq_all, MIN_YEARS, MIN_GAIN, TOL_PX, TOL_LEN, no_overlap=True)
cycles = enforce_no_overlap(cycles, TOL_PX)
print(f"Valid cycles found: {len(cycles)}")

relaxed_stage = "Base settings"
if len(cycles) == 0:
    # Stage 1: relax filters (still enforce no-overlap)
    relaxed_stage = "Stage 1: relaxed filters"
    print("→ No cycles; relaxing filters (no-overlap still ON)…")
    cycles = extract_cycles(seq_all,
                            min_years=max(1.25, MIN_YEARS*0.75),
                            min_gain=max(0.20, MIN_GAIN*0.7),
                            tol_px=TOL_PX*2,
                            tol_len=TOL_LEN*1.5,
                            no_overlap=True)  # <-- keep ON
    cycles = enforce_no_overlap(cycles, TOL_PX)
    print(f"Valid cycles after relaxation: {len(cycles)}")
    # Stage 2: lower ZigZag if still none (still enforce no-overlap)
    if len(cycles) == 0:
        relaxed_stage = "Stage 2: lower ZigZag"
        new_ZZ = max(8.0, ZZ_PCT - 3.0)
        print(f"→ Still none; lowering ZigZag threshold to {new_ZZ}% …")
        piv_df, seq_all = build_pivots(g, new_ZZ)
        print(f"Pivots now: {len(piv_df)}")
        cycles = extract_cycles(seq_all,
                                min_years=max(1.25, MIN_YEARS*0.75),
                                min_gain=max(0.20, MIN_GAIN*0.7),
                                tol_px=TOL_PX*2,
                                tol_len=TOL_LEN*1.5,
                                no_overlap=True)  # <-- keep ON
        cycles = enforce_no_overlap(cycles, TOL_PX)
        print(f"Valid cycles after lower ZigZag: {len(cycles)}")

# Attach corrections for complete cycles
for c in cycles:
    _, _, v_idx = c["V_high"]
    c["CORR"] = find_abc_x_abc(seq_all, v_idx)

best_cycle = max(cycles, key=cycle_score) if cycles else None

# --------- Continue counting from last wave (current partial) ---------
partial = infer_current_partial(seq_all, tol_px=TOL_PX, enforce_no_overlap=True)
if not partial:
    partial = infer_partial_fallback(seq_all, tol_px=TOL_PX, enforce_no_overlap=True)

# ---------------- Plot ----------------
fig, ax = plt.subplots(figsize=(14, 8))
if LOG_SCALE: ax.set_yscale("log")

ax.plot(g.index, g.values, lw=1.6, color="black", label=f"{TICKERS[0]} (close)")
ax.scatter(piv_df.index, piv_df["Price"], s=10, color="black", alpha=0.45,
           label=f"ZigZag pivots ({relaxed_stage})")

PASTEL    = ["#E6F2FF", "#EAF7EA", "#FFF0E6", "#F3E6FF", "#FFE6F0"]
IMPULSE   = ["#1F77B4", "#2CA02C", "#FF7F0E", "#9467BD", "#D62728"]
CORR_FILL = "#FFE9E9"
CORR_CLR  = "#C23B22"
PART_CLR  = "teal"
PART_FILL = "steelblue"

def annotate_point(dt, px, text, color, z=6):
    label_text = f"{text} ({px:,.0f})"
    ax.scatter([dt], [px], s=40, color=color, zorder=z)
    ax.annotate(label_text, xy=(dt, px), xytext=(6, 6), textcoords="offset points",
                fontsize=9, color="white" if text in ["I","II","III","IV","V","I(?)","II(?)","III(?)","IV(?)","V(?)"] else color,
                bbox=dict(boxstyle="round,pad=0.2",
                          fc=color if text in ["I","II","III","IV","V","I(?)","II(?)","III(?)","IV(?)","V(?)"] else "white",
                          ec="white" if text in ["I","II","III","IV","V","I(?)","II(?)","III(?)","IV(?)","V(?)"] else color,
                          alpha=0.7),
                zorder=z+1)

def get_corr_end(corr, fallback_dt):
    if not corr: return fallback_dt
    if "ABC2" in corr: return corr["ABC2"]["C"][0]
    if "ABC1" in corr: return corr["ABC1"]["C"][0]
    return fallback_dt

# Draw complete cycles
for k, cyc in enumerate(cycles, start=1):
    cfill = PASTEL[(k-1) % len(PASTEL)]
    cline = IMPULSE[(k-1) % len(IMPULSE)]
    d1, p1, _ = cyc["I_low"]; dv, pv, _ = cyc["V_high"]
    ax.axvspan(d1, dv, color=cfill, alpha=0.28, label=(f"Cycle #{k}" if k==1 else None))
    for lbl, key in [("I","I_low"), ("II","II_low"), ("III","III_high"), ("IV","IV_low"), ("V","V_high")]:
        d, p, _ = cyc[key]; annotate_point(d, p, lbl, cline)
    corr = cyc.get("CORR", {})
    if corr:
        ax.axvspan(dv, get_corr_end(corr, dv), color=CORR_FILL, alpha=0.20,
                   label=(f"Correction (Cycle {k})" if k==1 else None))
        if "ABC1" in corr:
            A,B,C = corr["ABC1"]["A"], corr["ABC1"]["B"], corr["ABC1"]["C"]
            annotate_point(A[0], A[1], "A", CORR_CLR)
            annotate_point(B[0], B[1], "B", CORR_CLR)
            annotate_point(C[0], C[1], "C", CORR_CLR)
        if "X" in corr:
            xd, xp, _ = corr["X"]; annotate_point(xd, xp, "X", CORR_CLR)
        if "ABC2" in corr:
            A2,B2,C2 = corr["ABC2"]["A"], corr["ABC2"]["B"], corr["ABC2"]["C"]
            annotate_point(A2[0], A2[1], "A", CORR_CLR)
            annotate_point(B2[0], B2[1], "B", CORR_CLR)
            annotate_point(C2[0], C2[1], "C", CORR_CLR)

# Highlight best-fit complete cycle
if best_cycle:
    d1, p1, _ = best_cycle["I_low"]; dv, pv, _ = best_cycle["V_high"]
    ax.axvspan(d1, dv, color="orange", alpha=0.12, label="Primary (best-fit) cycle")
    ax.plot([d1, dv], [p1, pv], color="orange", lw=2.2, ls="-", alpha=0.9)
    ax.annotate("Primary (best-fit) cycle", xy=(dv, pv), xytext=(10, 10),
                textcoords="offset points", color="orange", fontsize=10,
                bbox=dict(fc="white", ec="none", alpha=0.25))

# Draw CURRENT PARTIAL cycle (continued count from last wave)
if partial:
    lab = partial["labels"]
    keys_order = ["I_low","I_high","II_low","III_high","IV_low","V_high"]
    got_keys = [k for k in keys_order if k in lab]
    if len(got_keys) >= 2:
        first_key, last_key = got_keys[0], got_keys[-1]
        d_start, p_start, _ = lab[first_key]
        d_last,  p_last,  _ = lab[last_key]
        ax.axvspan(d_start, d_last, color=PART_FILL, alpha=0.20, label="Current partial (inferred)")
        name_map = {"I_low":"I(?)", "I_high":"I(?)", "II_low":"II(?)", "III_high":"III(?)",
                    "IV_low":"IV(?)", "V_high":"V(?)"}
        for kname in got_keys:
            d, p, _ = lab[kname]
            annotate_point(d, p, name_map[kname], PART_CLR)
        ax.plot([d_start, d_last], [p_start, p_last], color=PART_CLR, lw=2.0, ls="--", alpha=0.9)
        state = f"Current inferred wave: {partial['current_wave']}  (direction: {partial['direction']})"
        ax.annotate(state, xy=(d_last, p_last), xytext=(10, 10),
                    textcoords="offset points", fontsize=10, color=PART_CLR,
                    bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=PART_CLR, alpha=0.9))

# Cosmetics
title_note = " + partial in-progress" if partial else ""
ax.set_title(f"{TICKERS[0]} — Elliott-like I–V cycles with ABC(+X){title_note}\n"
             f"(ZigZag={ZZ_PCT:.0f}%, resample={RESAMPLE or 'Daily'})",
             fontsize=13)
ax.set_xlabel("Year"); ax.set_ylabel(f"USD/oz{' [log]' if LOG_SCALE else ''}")
ax.xaxis.set_major_locator(mdates.AutoDateLocator())
ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
ax.grid(True, alpha=0.3)

# Legend (dedupe)
handles, labels = ax.get_legend_handles_labels()
seen, H, L = set(), [], []
for h, l in zip(handles, labels):
    if l not in seen and l != "":
        H.append(h); L.append(l); seen.add(l)
if H: ax.legend(H, L, loc="upper left", frameon=True)

plt.tight_layout()
plt.savefig(SAVE_PNG, dpi=180)
plt.show()

# ---------------- Diagnostics ----------------
def _fmt(x):
    try: return f"${x:,.0f}"
    except: return "n/a"

print(f"\nPivots: {len(piv_df)} | Complete cycles found: {len(cycles)}")
for idx, c in enumerate(cycles, start=1):
    print(f"\nCycle #{idx}: years≈{c['years']:.1f}, gain≈{c['gain']*100:.0f}%")
    for key in ["I_low","I_high","II_low","III_high","IV_low","V_high"]:
        d,p,_ = c[key]; print(f"  {key:9s}: {d.date()}  {_fmt(p)}")

if partial:
    print("\nCURRENT PARTIAL (continued):")
    for k in ["I_low","I_high","II_low","III_high","IV_low","V_high"]:
        if k in partial["labels"]:
            d,p,_ = partial["labels"][k]
            print(f"  {k:9s}: {d.date()}  {_fmt(p)}")
    print(f"  → Current wave: {partial['current_wave']}, direction: {partial['direction']}")
else:
    print("\nCould not infer a partial structure (lower ZZ_PCT or turn RESAMPLE=None).")

print(f"\nSaved chart → {SAVE_PNG}")