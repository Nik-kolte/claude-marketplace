# Risk, Prop Rules, Trade Management, Discipline

`scripts/risk_calc.py` applies these rules and its answer is final. This file explains them so you can tell the trader why.

## Prop challenge limits (default 5% daily / 10% max, static)

- **Daily floor** = start-of-day balance − 5% × the basis (`daily_basis` in account.json). Equity, including open trades, must never touch it.
- **Max floor** = initial balance × 90% (static), or high-water equity × 90% (trailing).
- If less than **1.5% of equity** is left before the daily floor → no new trades today.
- One trade may use at most **40% of the remaining daily room** and **25% of the remaining max room**.
- Profit target reached → stop. The challenge is passed. Don't give it back.

## Risk per trade (scales only on evidence, never on feelings)

| Situation | Risk |
|---|---|
| Grade B or worse | **no trade** |
| Grade A | 1.0% |
| Grade A+ after 1 win in a row | 1.25% |
| Grade A+ after 2+ wins in a row | 1.5% (hard cap) |
| 2+ losses in a row (carries across days until a win) | 0.5% |

"Confidence" means the grade from the checklist plus a winning streak. A strong feeling is not confidence. Lot size always rounds **down**, and the spread is added to the stop distance.

## Discipline (hard rules)

- At most **2 trades a day**. **Stop after 2 losses.**
- **One position at a time.** No stacking EURUSD and GBPUSD in the same direction.
- **Red-folder news:** no new entries from 30 minutes before to 30 minutes after. An open trade going into news must already be at break-even or past TP1. Otherwise close it, or tighten to the last M5 swing, before the release.
- Never widen a stop. Never add to a loser. Never re-enter the same setup after it stopped out. A new setup needs a new sweep and a new MSS.
- After a stopped-out trade: no new entry until the next killzone, or at least 30 minutes later.
- If the trader says they want to "make it back", answer with the rule, not with a trade.

## Trade management plan (include it with every trade call)

1. **Entry:** a limit at the FVG edge or CE. If it isn't filled by the end of the killzone, or price closes through the far side of the FVG first → cancel.
2. **At TP1** (first internal liquidity, or 1R): close **50%** (`tp1_close_lots`) and move the stop to **break-even + spread**. If the position is too small to split, just move the stop to break-even at TP1.
3. **Runner:** hold to **TP2** (external liquidity / draw). After a new M5 MSS in your favour, the stop may be trailed behind the latest swing. Never loosen it.
4. **Time stop:** if price hasn't reached +0.5R by the end of the killzone, close it or cut it to half. A good ICT entry should move away from the entry quickly.
5. **Invalidation while in the trade:** if an M5 candle closes back through the swept extreme's MSS level with displacement against you → close manually before the stop is hit.
6. **News:** see the discipline rules above.
7. **End of day / Friday:** flatten runners before the 17:00 NY rollover on Friday, and close anything still open at the NY PM killzone end unless it's past TP1 at break-even.
