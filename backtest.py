#!/usr/bin/env python3
"""Backtest runner for the frozen AIProve ETH 1-minute dataset (bars.csv).

Replay rules (no phantom fills):
  * The signal for a bar is computed from closes up to and including that
    bar, then executed at the NEXT bar's open.
  * A position executed at open[j] earns open[j] -> open[j+1]; the final
    position is liquidated at the last bar's close.
  * Every rebalance pays costs on the traded amount: |delta position| *
    execution price * (FEE + SLIPPAGE), trading 1 ETH units.

Cost model (documented assumption — the sandbox applies its own maker/
taker + slippage schedule; these are Binance-spot-like blended values):
  FEE      = 5 bps per unit traded
  SLIPPAGE = 2 bps per unit traded

Usage: python3 backtest.py [bars.csv]
Prints gross PnL, costs, net PnL, trade count, turnover, max drawdown,
plus a buy-and-hold reference and a small robustness check over other
standard EMA pairings (the entered strategy stays FAST=20 / SLOW=60).
"""
import csv
import sys
from typing import List, Sequence, Tuple

from strategy import compute_positions

FEE = 0.0005        # 5 bps
SLIPPAGE = 0.0002   # 2 bps
COST_RATE = FEE + SLIPPAGE
QTY = 1.0           # trade 1 ETH units


def load_bars(path: str):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    opens = [float(r["open"]) for r in rows]
    closes = [float(r["close"]) for r in rows]
    return opens, closes


def run_backtest(opens: Sequence[float], closes: Sequence[float],
                 fast: int, slow: int, band: float = 0.002) -> dict:
    n = len(closes)
    signals = compute_positions(closes, fast, slow, band)
    equity = 0.0
    curve = [0.0]
    costs = 0.0
    gross = 0.0
    trades = 0
    turnover = 0.0
    held = 0  # position currently on, in ETH units

    # Rebalance at open[j] to signals[j-1]; earn open[j] -> open[j+1].
    for j in range(1, n - 1):
        target = signals[j - 1] * QTY
        delta = target - held
        if delta != 0:
            c = abs(delta) * opens[j] * COST_RATE
            costs += c
            equity -= c
            turnover += abs(delta)
            trades += 1
            held = target
        pnl = held * (opens[j + 1] - opens[j])
        gross += pnl
        equity += pnl
        curve.append(equity)
    # Final bar: rebalance at open[n-1], earn to close[n-1], then liquidate.
    j = n - 1
    target = signals[j - 1] * QTY
    delta = target - held
    if delta != 0:
        c = abs(delta) * opens[j] * COST_RATE
        costs += c
        equity -= c
        turnover += abs(delta)
        trades += 1
        held = target
    pnl = held * (closes[j] - opens[j])
    gross += pnl
    equity += pnl
    if held != 0:  # liquidation cost at last close
        c = abs(held) * closes[j] * COST_RATE
        costs += c
        equity -= c
        turnover += abs(held)
        trades += 1
        held = 0
    curve.append(equity)

    peak = 0.0
    max_dd = 0.0
    for v in curve:
        peak = max(peak, v)
        max_dd = max(max_dd, peak - v)

    return {
        "gross": gross, "costs": costs, "net": equity, "trades": trades,
        "turnover": turnover, "max_dd": max_dd,
    }


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "bars.csv"
    opens, closes = load_bars(path)
    n = len(closes)
    print(f"dataset: {path}  bars={n}  first close={closes[0]}  last close={closes[-1]}")

    bh = closes[-1] - opens[0]
    print(f"buy & hold reference (open[0] -> close[-1], no costs): {bh:+.2f} USD")

    r = run_backtest(opens, closes, 20, 60, 0.002)
    print("\nENTERED STRATEGY  EMA(20/60) crossover + 0.2% cost-aware band, long/short, 1 ETH")
    print(f"  gross PnL : {r['gross']:+.2f} USD")
    print(f"  costs     : {r['costs']:.2f} USD  (fee {FEE*1e4:.0f} bps + slippage {SLIPPAGE*1e4:.0f} bps per unit traded)")
    print(f"  NET PnL   : {r['net']:+.2f} USD")
    print(f"  executions: {r['trades']}   turnover: {r['turnover']:.0f} ETH   max drawdown: {r['max_dd']:.2f} USD")

    print("\nrobustness grid (same replay rules — reported for honesty, NOT the entry):")
    print("  no-band plain crossover:")
    for fast, slow in [(10, 30), (20, 60), (30, 90)]:
        rr = run_backtest(opens, closes, fast, slow, 0.0)
        print(f"  EMA({fast}/{slow}) band=0     : net {rr['net']:+8.2f} USD  costs {rr['costs']:6.2f}  trades {rr['trades']:3d}  maxDD {rr['max_dd']:7.2f}")
    print("  with band:")
    for fast, slow in [(20, 60), (30, 90)]:
        for band in (0.001, 0.002, 0.003):
            rr = run_backtest(opens, closes, fast, slow, band)
            print(f"  EMA({fast}/{slow}) band={band:.3f}: net {rr['net']:+8.2f} USD  costs {rr['costs']:6.2f}  trades {rr['trades']:3d}  maxDD {rr['max_dd']:7.2f}")


if __name__ == "__main__":
    main()
