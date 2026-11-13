# eth-pnl-fixed — entry

**Entry:** `strategy.py` (the strategy) + `backtest.py` (the replay runner)
+ `bars.csv` (the frozen challenge dataset, copied verbatim from the
challenge repo, md5 `9f8a16c669100d333b3c11c2bd6d503e`).

The challenge README does not prescribe file or entrypoint names, so the
interface is the natural one: `strategy.compute_positions(closes)` returns
one target position per bar (-1 / 0 / +1), decided from closes up to that
bar only.

## Strategy

EMA(20/60) trend-following with a **cost-aware no-trade band**:

- Long when EMA20 > EMA60 × 1.002, short when EMA20 < EMA60 × 0.998,
  otherwise hold the previous position (hysteresis). 60-bar warmup, flat.
- Rationale: a plain crossover on 1-minute bars whipsaws — on this sample
  it executed 25 times and paid $67.04 of costs against $34.05 of gross
  trend profit (net −$32.99). Requiring the trend signal to exceed ~the
  round-trip cost of acting on it (a flip costs ~14 bps in fees/slippage)
  before trading is a standard, dataset-independent fix.
- The improvement is a plateau, not a spike: every band × pairing cell
  tested (bands 0.05–0.3%, EMA 20/60 and 30/90) finishes positive while
  all no-band variants lose. The entered band (0.2%, EMA 20/60) is the
  middle of the plateau, deliberately not the grid maximum
  (30/90 @ 0.3%, +$58.61), to avoid fitting the sample the README warns
  about. Full grid in `transcript.txt`.

## Replay rules (no phantom fills)

- Signal from closes ≤ bar *i* is executed at the **open of bar *i+1***.
- A position executed at open[j] earns open[j] → open[j+1]; the final
  position is liquidated at the last close.
- Costs charged on every rebalance: |Δposition| × price × (fee + slippage).

## Cost model — stated assumption

The challenge says the sandbox applies its own maker/taker fee and
slippage schedule but does not publish the numbers, so this runner uses
documented Binance-spot-like blended values: **fee 5 bps + slippage 2 bps
per unit traded**, position size 1 ETH. Under a harsher model (e.g. 10 bps
taker) all figures worsen roughly linearly in turnover — which is exactly
why the strategy minimises turnover (8 ETH total).

## Result on the published 1,440 bars

| | USD |
|---|---|
| Gross PnL | +51.61 |
| Costs | −11.13 |
| **Net PnL** | **+40.48** |
| Executions / turnover | 5 / 8 ETH |
| Max drawdown | 82.05 |
| Buy & hold reference (no costs) | −64.71 |

## Limitations

- One day of data. The result says the design behaves sanely on a choppy
  downtrend day; it is not evidence of an edge on the held-out tail.
- The sandbox's exact cost schedule and fill model will differ from the
  assumptions above; rankings under their model may differ.

## Files

- `strategy.py` — the entered strategy
- `backtest.py` — replay runner (`python3 backtest.py bars.csv`)
- `bars.csv` — frozen dataset (verbatim copy from the challenge repo)
- `transcript.txt` — build/test log, including the losing v1 design
