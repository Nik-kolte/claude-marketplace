# ICT Playbook

All times are New York local time. Every level you quote must come from the feed (`mt5_feed.py`) or the chart. Never invent a price.

## 1. Vocabulary (exact definitions, used the same way every time)

| Term | Definition used here |
|---|---|
| **BSL / SSL** | Buy-side liquidity: resting stops above old highs. Sell-side liquidity: below old lows. The strongest pools are equal highs/lows (`equal_highs_BSL` / `equal_lows_SSL` in the feed), PDH/PDL, PWH/PWL, and the Asia and London highs/lows. |
| **Liquidity sweep / raid** | Price trades through a pool, then **closes back inside** on the timeframe you are watching. A close beyond the pool that holds is a breakout, not a sweep. |
| **Displacement** | An energetic, one-directional move: candle bodies of at least 1.2× ATR (`displacement: true` in the feed) that leave an FVG behind. A slow drift is not displacement. |
| **MSS** (market structure shift) | After a sweep, a candle **close** through the last opposing swing point, with displacement. It flips short-term order flow. Break direction in the feed = `structure.last_break` with `type: MSS`. |
| **BOS** | A close through a swing point in the same direction as the current order flow (continuation). |
| **FVG** | A three-candle imbalance: candle 3's low is above candle 1's high (bullish), or the mirror image. **CE** = the 50% level of the gap. A fresh FVG (not yet revisited) is stronger than a mitigated one. |
| **Order block (OB)** | The last opposing candle before the displacement that caused the MSS. Bullish OB = the last down-close candle before an up-displacement. |
| **Breaker** | An OB that failed (price closed through it) and was then retested from the other side. |
| **Dealing range / premium-discount** | The range from the most recent significant swing low to swing high on the bias timeframe. Above 50% (equilibrium) = premium, below = discount. **Buy in discount, sell in premium.** |
| **OTE** | The 62–79% retracement of the displacement leg (70.5% sweet spot). Used only as confluence. |
| **Draw on liquidity (DOL)** | The pool price is most likely heading to next. It is your final target (TP2). |
| **SMT divergence** | Correlated markets disagree at a sweep: e.g. EURUSD makes a lower low while GBPUSD doesn't, or gold sweeps a low while DXY fails to make a higher high. Run the feed for the correlated symbol to check. |
| **NY midnight open** | The 00:00 NY price. In the day's distribution, longs are best taken **below** it and shorts **above** it. |

## 2. Top-down sequence (do it in this order, every time)

1. **Daily:** where is the draw on liquidity? Which old high or low, PDH/PDL, PWH/PWL or unfilled daily FVG is price heading toward? Is price in the premium or discount of the daily dealing range?
2. **H4:** does the order flow agree (most recent MSS/BOS direction, respect of H4 FVGs)?
3. **Bias = Daily DOL + H4 order flow agreeing.** If they disagree, or price is sitting at equilibrium with no clear draw → **no bias → NO TRADE.**
4. **H1/M15:** map today's levels: Asia range, midnight open, London range, PDH/PDL, nearest fresh FVGs and the BSL/SSL pools on both sides.
5. **M5 (M1 visually through TradingView, if connected):** execute only inside a killzone, with one of the two models below.

## 3. Killzones (the only times entries are allowed)

| Killzone | NY time | Typical role |
|---|---|---|
| Asia | 20:00–23:00 | Builds the range that London and NY later raid. Gold spreads widen here and the moves are thin. **Asia entries must be graded A+ and the spread must be normal**, otherwise just map the range. |
| London | 02:00–05:00 | Often sets the high or low of the day with a Judas swing. |
| NY AM | 07:00–10:00 | Most liquid. 08:30 and 10:00 news releases drive it. Check the news first. |
| NY PM | 13:30–16:00 | Continuation toward the day's draw, or a reversal after the AM session ran it. |

Outside a killzone the answer is always **NO TRADE — wait for <next killzone>**. You can still prepare the plan.

## 4. Model A — ICT 2022 Model

All steps are required, in this order:
1. **Bias** from section 2.
2. **Sweep:** inside a killzone, price raids a short-term pool **against** the bias (for longs: takes out a swing low, Asia low, London low, or PDL) and closes back inside.
3. **MSS with displacement** on M5/M15 **in the bias direction**, closing through the swing that led into the sweep.
4. **FVG** created by that displacement leg. That is the entry array.
5. **Entry:** a limit order at the FVG's near edge or its CE. Stop **beyond the sweep extreme** plus a buffer of about 10% of the M15 ATR. A stop inside the FVG is not allowed.
6. **TP1** = the first internal liquidity (the nearest opposing swing or the high/low that formed the MSS), or 1R if that's closer. **TP2** = the draw on liquidity from section 2, and it must be at least 2R away.

Invalidation before fill: price closes through the far side of the FVG, or the killzone ends without a fill → cancel.

## 5. Model B — Power of 3 / Judas Swing (AMD)

1. **Accumulation:** the Asia range (20:00–00:00) and the midnight open are known.
2. **Bias** from section 2.
3. **Manipulation (Judas):** in London or NY AM, price runs **against** the bias beyond the Asia range or the midnight open, ideally into an HTF PD array (H1/H4 FVG or OB), and takes liquidity.
4. **Reversal confirmation:** MSS with displacement on M5/M15 back in the bias direction, leaving an FVG.
5. **Entry** in that FVG/OB, and **on the right side of the midnight open** (longs below it, shorts above it). If price is already on the wrong side, the trade is late → NO TRADE.
6. **Stop** beyond the Judas extreme plus the buffer. **TP1** = the opposite side of the Asia range, or 1R. **TP2** = the day's draw (PDH/PDL or the opposite pool), at least 2R away.

## 6. Grading (decides whether a trade is allowed at all, and how big it can be)

**Mandatory (any one missing → NO TRADE):**
- [ ] Daily and H4 agree on the bias, and the draw on liquidity is named
- [ ] Inside an allowed killzone
- [ ] A clear sweep of a named pool, closed back inside
- [ ] MSS with displacement in the bias direction
- [ ] Entry at an FVG/OB from that displacement, in discount for longs (premium for shorts)
- [ ] Stop at structural invalidation (beyond the sweep or Judas extreme)
- [ ] TP2 ≥ 2R to a named liquidity target
- [ ] No red-folder news within ±30 minutes, and the spread is normal
- [ ] `risk_calc.py` says `allowed: true`

**Confluences (each one counts):**
- The swept pool was a major one (PDH/PDL, PWH/PWL, Asia or London high/low, equal highs/lows)
- SMT divergence with the correlated market
- The entry overlaps OTE (62–79%)
- The reaction came from an HTF PD array (H1/H4 FVG or OB)
- The entry is on the correct side of the midnight open
- A fresh (unmitigated) FVG

**Grade:** mandatory only = **B → NO TRADE**. Mandatory + 1–2 confluences = **A**. Mandatory + 3 or more = **A+**.

## 7. Confusion = NO TRADE (any of these on its own is enough)

- Daily and H4 disagree, or price is at equilibrium with no obvious draw
- Liquidity was swept on **both** sides this session (a stop hunt both ways) and no clean MSS followed
- The MSS has no displacement (a small drift through a swing)
- The FVG is already filled, or the entry is mid-range or on the wrong side of the midnight open
- You need to "squint" to find the sweep, the MSS or the FVG
- You disagree with yourself between two reads of the same chart
- The feed says `market_open: false`, or there is a feed error, or the spread is more than 2× its normal level
- News status is unknown for a session that has scheduled releases

## 8. Instrument notes

**XAUUSD:**
- Moves fast. M15 ATR is often $3–8. Stops need the ATR buffer.
- Spread widens a lot in Asia, at the 17:00 NY rollover, and around US data.
- Reacts to US yields and DXY: CPI, NFP, FOMC, PCE, PPI and jobless claims. Treat any of those as red-folder.
- Use DXY or XAGUSD for SMT where available.

**EURUSD / GBPUSD:**
- Strongly correlated, so they are SMT partners for each other.
- **Never hold both in the same direction**; that doubles the same risk. The one-position-at-a-time rule handles this.
- GBP is more volatile than EUR. Pound news (UK CPI, BoE) is red-folder for GBPUSD; ECB and EU CPI are red-folder for EURUSD.

**Monday:** the first London session often builds the week's range. Be more selective.
**Friday:** after the NY AM session, don't open new trades. Protect what you have going into the weekend.
