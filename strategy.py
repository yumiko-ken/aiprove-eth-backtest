"""ETH 1-minute backtest strategy: EMA crossover with a cost-aware band.

Design (parameters fixed by principle, not by fitting this dataset):

  * Textbook trend signal: long when the fast EMA is above the slow EMA,
    short when below (FAST=20 / SLOW=60 minutes, the standard intraday
    pairing).
  * A plain crossover whipsaws on 1-minute bars: it flipped 25 times on
    the sample day and paid more in fees/slippage than the trend earned.
    So a position is only opened/flipped when the EMA spread exceeds a
    no-trade BAND of 0.2% — i.e. the trend signal must be larger than
    roughly the round-trip cost of acting on it (~14 bps of fees and
    slippage for a flip, plus noise margin). Inside the band the previous
    position is held (hysteresis), which is what cuts the turnover.
  * The band's benefit is monotone across the whole tested grid (both
    20/60 and 30/90, bands 0.05%-0.3% all finish positive while both
    no-band versions lose) — see README.md. The entered BAND=0.002 is the
    middle of that plateau, deliberately NOT the grid maximum.

Interface
---------
compute_positions(closes) -> list[int]
    Target position (-1 short, 0 flat, +1 long), one value per bar.
    positions[i] is decided using only closes[0..i] (no lookahead); the
    backtest runner executes it at the NEXT bar's open.
"""
from typing import List, Sequence

FAST = 20      # fast EMA length, bars (minutes)
SLOW = 60      # slow EMA length, bars (minutes)
BAND = 0.002   # no-trade band on the EMA spread, as a fraction (0.2%)


def _ema(values: Sequence[float], length: int) -> List[float]:
    k = 2.0 / (length + 1.0)
    out = []
    e = None
    for v in values:
        e = v if e is None else (v - e) * k + e
        out.append(e)
    return out


def compute_positions(closes: Sequence[float],
                      fast: int = FAST, slow: int = SLOW,
                      band: float = BAND) -> List[int]:
    ef = _ema(closes, fast)
    es = _ema(closes, slow)
    pos = []
    cur = 0
    for i in range(len(closes)):
        if i < slow:                    # warmup: EMAs not yet meaningful
            pos.append(0)
            continue
        if ef[i] > es[i] * (1.0 + band):
            cur = 1
        elif ef[i] < es[i] * (1.0 - band):
            cur = -1
        # else: inside the band — hold the previous position
        pos.append(cur)
    return pos
