#!/usr/bin/env python3
"""Forecast Polymarket Yes prices 4 hours ahead, as five quantiles a minute.

Entry for make.fun polymarket-faa-attribution-01. Reads one case per run
from $MAKEFUN_INPUT_DIR (else /input) and writes one forecast per case to
$MAKEFUN_OUTPUT_DIR (else /output).

Method: persistence median with a level-dependent, jump-aware spread.
For a market whose last price is x, minute h after the checkpoint:

    q_tau(h) = clamp(x + z_tau * S(x) * h**0.45 * mult_tau(x), 0, 1)

    S(x)    = 0.0009 * (1 + 4x), doubled when a move larger than 0.03
              happened in the last 120 minutes (jump regime)
    mult    = 1 + 6x for the two lower quantiles, 1.0 otherwise
              (downside spread wider: high prices fall harder than they rise)
    median  = x (no drift)

The four markets of one attribution family are mutually exclusive, so
their Yes prices should sum to about 1: the medians are renormalised to
sum to 1 whenever the checkpoint sum lies in [0.5, 1.5].

Standard library only, no network, deterministic: the same input always
produces the same bytes.
"""

import json
import os

# Standard-normal quantiles for the levels this competition scores.
Z = {
    0.05: -1.6448536269514722,
    0.25: -0.6744897501960817,
    0.5: 0.0,
    0.75: 0.6744897501960817,
    0.95: 1.6448536269514722,
}

# Calibrated constants (local practice p00-p04, mean pinball loss, points).
# Base model, from the sibling NVIDIA entry's staged search:
#   S0=0.0009, ALPHA=0.45, KX=4, KD=6, median=x  ->  0.329740
#   (house baseline 0.392518; base beats it on every case)
# Two additions, each tested alone and together, kept only because each
# beats the base on practice AND on five fresh rolling origins in p05:
#   jump-aware spread (JUMP_* below)               ->  0.321612 alone
#   sum-to-1 median renormalisation                ->  0.323348 alone
#   both together (this entry)                     ->  0.306120
# Rejected on practice: median drift toward a trailing median, per-market
# activity scaling, raw empirical quantiles (all worse than the base).
S0 = 0.0009
ALPHA = 0.45
KX = 4.0
KD = 6.0
JUMP_WINDOW = 120
JUMP_THRESHOLD = 0.03
JUMP_MULT = 2.0


def clamp01(v):
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


def has_recent_jump(prices):
    """True when any 1-minute move larger than JUMP_THRESHOLD occurred
    in the last JUMP_WINDOW minutes."""
    seg = prices[-JUMP_WINDOW - 1:] if len(prices) > JUMP_WINDOW else prices
    for i in range(1, len(seg)):
        d = seg[i] - seg[i - 1]
        if d > JUMP_THRESHOLD or d < -JUMP_THRESHOLD:
            return True
    return False


def z_for(tau):
    """Standard-normal quantile for a level; 0.0 for any level the
    competition does not score (defensive: the graded levels are fixed)."""
    return Z.get(tau, 0.0)


def last_price(market):
    prices = market["prices"]
    return prices[-1] if prices else 0.5


def forecast_market(prices, horizon, quantiles):
    """240 (horizon) rows of one forecast per quantile level, non-decreasing."""
    if not prices:
        x = 0.5
        jump = False
    else:
        x = prices[-1]
        jump = has_recent_jump(prices)
    spread = S0 * (1.0 + KX * x)
    if jump:
        spread *= JUMP_MULT
    down_mult = 1.0 + KD * x
    rows = []
    for h in range(1, horizon + 1):
        w = spread * (h ** ALPHA)
        row = []
        prev = 0.0
        for i, tau in enumerate(quantiles):
            mult = down_mult if tau < 0.5 else 1.0
            q = round(clamp01(x + z_for(tau) * w * mult), 6)
            if q < prev:
                q = prev
            row.append(q)
            prev = q
        rows.append(row)
    return rows


def forecast_case(case):
    horizon = int(case.get("horizon_minutes", 240))
    quantiles = case.get("quantiles", [0.05, 0.25, 0.5, 0.75, 0.95])
    markets = case["markets"]
    forecasts = []
    for market in markets:
        forecasts.append({
            "id": market["id"],
            "q": forecast_market(market["prices"], horizon, quantiles),
        })
    # Cross-market sum-to-1 renormalisation of the medians. The median
    # index is the middle quantile level (0.5).
    if 0.5 in quantiles:
        med_i = quantiles.index(0.5)
        total = 0.0
        for market in markets:
            total += last_price(market)
        if 0.5 <= total <= 1.5 and total > 0.0:
            factor = 1.0 / total
            for fc in forecasts:
                for row in fc["q"]:
                    med = clamp01(round(row[med_i] * factor, 6))
                    row[med_i] = med
                    for i in range(med_i):
                        if row[i] > med:
                            row[i] = med
                    for i in range(med_i + 1, len(row)):
                        if row[i] < med:
                            row[i] = med
    return {"forecasts": forecasts}


def main():
    in_dir = os.environ.get("MAKEFUN_INPUT_DIR") or "/input"
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(out_dir, exist_ok=True)
    for name in sorted(os.listdir(in_dir)):
        if not name.endswith(".in"):
            continue
        case_id = name[:-3]
        with open(os.path.join(in_dir, name), "r", encoding="utf-8") as f:
            case = json.load(f)
        result = forecast_case(case)
        out_path = os.path.join(out_dir, case_id + ".out")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, separators=(",", ":"))


if __name__ == "__main__":
    main()
