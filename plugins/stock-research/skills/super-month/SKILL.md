---
name: super-month
description: Run the monthly Super Strategy playbook (Core+Shield unified NSE portfolio) - refresh prices, compute the 5-signal market-health shield and the 10-stock momentum+ATH-tilt portfolio from the frozen champion, and report the exact rebalance actions. Use on/near the last trading day of each month, or any time the user asks what the super strategy currently says.
---

# super-month — Super Strategy monthly playbook orchestrator

You run one monthly playbook for the unified Core+Shield super strategy
(repo: `D:\projects\repos\india-invest`, package `superstrategy/`). Everything is
deterministic Python from the frozen champion (`superstrategy/state/champion.json`);
you add only a light news sanity-check and the summary.

## Procedure

All commands run from `D:\projects\repos\india-invest`.

1. **Refresh + run (deterministic):**
   - `uv run python superstrategy/run_month.py --refresh`
     (add no other flags; `--refresh` pulls latest prices first)
   - It prints the signal readout, exposure, target portfolio, action list, and
     saves `superstrategy/output/run_<date>/playbook.json` **and**
     `superstrategy/output/run_<date>/rebalance_report.html` — the printed
     lines plus that HTML file are all the context you need — do NOT read
     parquet/price files.
   - The HTML report is the per-month "why": for each added/removed/held
     stock it shows the 12-1 momentum, % of 52-week high, and blended
     tilt score, diffed against the previous run, plus the shield signal
     changes and the ranks-11-15 near-misses. It's generated automatically
     every run — nothing else to do here.
   - It also carries a "Paper portfolio" section: a notional ₹1,00,000
     account (auto-opened on the first ever run) tracked stock-by-stock —
     realized P&L when a name is sold (dropped from the top 10, or a
     full book rebuild if the shield's exposure regime changed), unrealized
     P&L while a name is still held, cash, and total value. Nothing to do
     here either — it updates itself every run from `live_portfolio.py`.

2. **News sanity-check (optional, keep cheap):** for names NEW to the portfolio
   vs the previous `superstrategy/output/run_*/playbook.json` (if one exists),
   do a quick WebSearch for obvious adverse news (fraud, default, resignation,
   regulatory action) from the last month. This may only FLAG a name for the
   user's attention — it never adds, removes, or reweights positions. If nothing
   material, say so in one line. Skip silently if no previous run exists.

3. **Summarize to the user in chat** (<=15 lines):
   - Shield line: which of the 5 health signals are on, and the resulting
     equity exposure (100/50/0%).
   - The target portfolio (10 names + weights, gold, liquid).
   - The 3-4 concrete rebalance actions.
   - Any news flags from step 2.
   - Paper portfolio one-liner: total value, all-time return %, and
     realized vs. unrealized P&L (printed by run_month.py / in the report's
     "Paper portfolio" section).
   - One closing line: where the playbook.json and rebalance_report.html
     were saved — point the user at the HTML report for the full add/drop
     reasoning behind this month's changes.

## Guardrails

- **Frozen champion:** never edit `superstrategy/state/champion.json` or any
  strategy parameter from this skill. Rule changes require re-running the full
  IS/OOS research protocol (`sweep.py` + `validate_champion.py`) — out of scope.
- `superstrategy/results/` is APPEND-ONLY; this skill should not write there at all.
- Never touch the rotation board (`research/state/*`, `journal/*`, `scan/*`,
  `research/results/*`) or `prospects/` outputs.
- If the user asks whether to trust the strategy, point them at
  `superstrategy/reports/superstrategy_report_2026-07-19.html` (validated
  OOS 32.9%/yr, max DD -22.5%, 2x-cost pass) — do not oversell; the report's
  "when this will disappoint you" section is part of the answer.
- Advisory only. Never place orders, never call broker APIs.
