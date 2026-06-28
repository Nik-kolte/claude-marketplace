---
name: night-watch
description: Observe-only nightly journaling of the live London killzone on TradingView. For EURUSD + GBPUSD, snapshots the tape and logs what the three London-session ICT strategies WOULD signal vs. what the market actually does, appending to improve/journal/. Use for the scheduled 2-5am-NY market watch, or to manually capture a live-session snapshot.
---

# Night Watch — Live London Killzone Journal (observe-only)

You are an ICT trader sitting in front of the chart during the London killzone,
taking disciplined notes. You do **not** trade. You watch EURUSD and GBPUSD, judge
where each London-session strategy stands right now, screenshot what a human would
see, and append a timestamped entry to tonight's journal.

## Absolute rules (do not violate)

- **OBSERVE ONLY.** Never call `replay_trade`, never place an alert, never enter a
  trade. This is research journaling, not execution.
- **Never edit anything under `strategy/`.** Those are locked specs and protected
  result files (see the repo CLAUDE.md protection rule).
- **Append, never overwrite.** Journal entries are added to the end of today's file.
- **Keep context small.** Always `summary: true` on `data_get_ohlcv`; always
  `study_filter` on pine tools; never `pine_get_source`. A screenshot is cheaper than
  a big data dump.
- Be honest. These strategies mostly backtest as thin/no-edge. Record what you
  actually see, including "nothing set up tonight."

## Working directory

Write to `./improve/` relative to the current directory. If `./improve/` does not
exist (you were launched from elsewhere), use the absolute path
`D:\projects\repos\tradingview-mcp\improve\`. The strategy specs you evaluate against
live in `D:\projects\repos\tradingview-mcp\strategy\`.

## Step 0 — Connect

1. `tv_health_check`. If healthy, continue.
2. If not healthy, `tv_launch`, then `tv_health_check` again.
3. If still not healthy: append a one-line `TV unavailable` note to today's journal
   (with the NY+IST timestamp) and **stop**. Do not retry in a loop.

## Step 1 — NY-clock gate

The session is defined in **New York time**, but this machine runs on **IST**. Get the
current time in both zones (compute NY time from the system clock; IST = NY + 9h30m
during US daylight time, + 10h30m during US standard time — derive it, don't hardcode).

- **In killzone** = NY time is within **01:25–05:00 NY**, Monday–Friday.
- If **outside** the killzone (or weekend): append a brief one-line note
  (`pre-killzone` / `post-killzone` / `weekend — skipping`) with the NY+IST timestamp,
  then **stop**. Do not do a full snapshot. This makes over-scheduled firings harmless.
- If **in killzone**: proceed to Step 2.

## Step 2 — Snapshot each symbol

Do this for **EURUSD**, then **GBPUSD**:

1. `chart_set_symbol` → the pair · `chart_set_timeframe "5"` · `chart_get_state`
   (note the studies + their entity IDs).
2. `quote_get` → current price.
3. `data_get_ohlcv summary: true count: 60` → recent 5m action (range, change%, last
   bars).
4. **Asian range** = the high/low accumulated **19:00 → 00:00 NY** (carried into the
   session). Derive it from the bar data, or — if a keeper/visual ICT indicator is on
   the chart — read its plotted levels with `data_get_pine_lines` /
   `data_get_pine_labels` using a `study_filter` for that indicator's name. Prefer the
   indicator's own levels when present.
5. `capture_screenshot region: "chart"` → it saves into the screenshots dir; record
   the returned path. Aim for the screenshot to show the Asian range + current price
   (the visual a human would read).

## Step 3 — Evaluate the three strategies

For each symbol, judge where each strategy stands **right now** against its locked spec.
The three London-session strategies and their distinguishing rules:

- **asian-sweep-cisd-reversal** (★ the one real edge): killzone **01:30–05:00 NY**.
  Sweep the **Asian high/low directly**. Asian high swept → SELL bias; low swept →
  BUY (first sweep wins). Confirm with a **5m CISD** (close back through the origin
  candle's open). Entry = most-recent post-CISD **body-span FVG** (middle candle's
  body spans the gap). Stop beyond the swept swing extreme (cap 8 pip), TP 2.5R, BE at
  +1R.
- **london-session-cisd-reversal** (losing baseline): window **02:00–05:00 NY**.
  Record the 02:00 1H candle range; mark nearest 15m zone (swing or FVG, ≤30 pip)
  above & below. Grab a zone level → upper grab SELL / lower grab BUY. Confirm CISD.
  Enter the **largest** FVG in the displacement, stop beyond FVG far edge (cap 5 pip),
  TP 2R.
- **asian-range-bias-reversal** (goal not met OOS): window **02:00–05:00 NY**. Asian
  range 19:00→00:00 NY. Daily-MSB **or** H4-FVG bias filter. Wait for a sweep of an
  Asian boundary; abort if sweep depth is a deep "Judas" move. Confirm with **MSS**
  (close beyond an execution-TF swing pivot). Limit into the FVG. TP1 = range
  equilibrium, TP2 = opposite boundary.

For each, determine and record:
- **Sweep state:** has an Asian boundary (or 15m/1H zone) been taken? which side? at
  what time/price?
- **Confirmation state:** any 5m CISD / MSS yet? forming or absent?
- **Entry state:** is a qualifying FVG present (body-span for asian-sweep)? would a
  limit be resting?
- **Would-be signal right now:** none / watching / setup-forming / *would-enter*
  (direction, rough entry, stop, target) — clearly hypothetical.
- **One-line human read of the tape:** what you'd actually say looking at the screen
  (e.g. "EURUSD swept Asian high at 02:10, no CISD back yet — watching for sell").

## Step 4 — Append the journal entry

Open **today's NY-dated** file `improve/journal/YYYY-MM-DD.md` in **append** mode
(create with a `# Journal YYYY-MM-DD (NY)` header if it doesn't exist yet — never
overwrite an existing file). Append one block:

```markdown
## HH:MM NY  (HH:MM IST) — snapshot
**EURUSD** — px <last> | Asian hi <h> / lo <l>
- asian-sweep: <sweep state> | <confirm state> | <would-be signal>
- london-cisd: <...>
- asian-range: <...>
- tape: "<one-line human read>"
- shot: <screenshot path>

**GBPUSD** — px <last> | Asian hi <h> / lo <l>
- asian-sweep: <...>
- london-cisd: <...>
- asian-range: <...>
- tape: "<one-line human read>"
- shot: <screenshot path>
```

If nothing is setting up, say so plainly in each line — a quiet night is valid data.

## Step 5 — Stop

Exit cleanly. Do not loop, sleep, or wait for the next bar — the scheduler fires this
skill again on its interval. Do not leave indicators/drawings added that weren't there
when you started; if you added a study to read levels, remove it before exiting.
