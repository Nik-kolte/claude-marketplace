---
name: reflect
description: Run one intelligent reflection cycle on the cloud paper-trading worker. Pulls the worker's recent trades + current strategy from its Railway volume, reasons about why trades are failing, changes EXACTLY ONE strategy variable, snapshots history, logs the hypothesis, and pushes the change back so the live worker adopts it. Use on-demand to evolve the strategy, or let the cloud reflector call it on a schedule. No-ops if too few new trades have closed since the last reflection.
---

# Strategy Reflection — the "researcher" brain

You are the reasoning brain of a self-improving paper-trading agent. A dumb worker
runs 24/7 on Railway taking ICT "Asian sweep → CISD reversal" paper trades on FX
majors and logging every outcome. Your job, each cycle: look at what actually
happened, figure out the single most likely improvement, change **exactly one**
variable, and hand it back. This is the scientific method — one variable per
experiment, every prior version preserved.

## Absolute rules

- **Change EXACTLY ONE variable per cycle.** If tempted to change more, pick the
  highest-confidence one and note the rest as `pending` in the hypothesis.
- **Append, never overwrite** `trades.jsonl` and `hypotheses.jsonl`. You only ever
  read trades; the worker owns that file.
- **Always snapshot** the prior `strategy.yaml` to `history/vNNNN.yaml` before
  changing it, and **bump `version`**.
- **No-op gracefully.** If fewer than `reflection_every` new trades have closed
  since the last reflection, do nothing and say so. Don't force a change.
- **Paper mode only.** Never touch live-trading flags.

## Configuration (provided by the environment)

- `REFLECT_VOLUME` — the Railway volume name (default `hermes-trading-volume`).
- `REFLECT_WORKDIR` — local working dir to sync into (default: a fresh temp dir).
- Railway auth: either you're already `railway login`-ed (local use) or a
  `RAILWAY_TOKEN` + linked project is present (cloud use).
- On **Windows Git Bash**, prefix every `railway volume files` path with
  `MSYS_NO_PATHCONV=1` so `/strategy.yaml` is not mangled into a Windows path.
  In a Linux container, drop that prefix.

## Step 1 — Sync state down from the volume

Create/clean the working dir (with a `history/` subdir) and download the live state:

```
V=${REFLECT_VOLUME:-hermes-trading-volume}
W=${REFLECT_WORKDIR:-/tmp/reflect-work}; mkdir -p "$W/history"
for f in goal.yaml strategy.yaml trades.jsonl hypotheses.jsonl; do
  railway volume files --volume "$V" download --overwrite /$f "$W/$f"
done
```

(Prepend `MSYS_NO_PATHCONV=1` to each download on Windows.)

## Step 2 — Decide whether to act

- `reflection_every` = the value in `goal.yaml` (e.g. 10).
- `last_total` = the `trades_total` field on the **last** line of `hypotheses.jsonl`
  (0 if the file is empty).
- `current_total` = number of closed trades in `trades.jsonl`
  (lines whose `outcome` is not `"open"`).
- If `current_total - last_total < reflection_every` → **stop**: print
  `"No reflection: only N new trades since last cycle (need M)."` and exit.

## Step 3 — Analyse the outcomes (reason, don't pattern-match)

Read `goal.yaml` (success = `target_return_30d`, failure = `max_drawdown`, quality =
`min_sharpe`) and the **last 25** closed trades. Compute, over those trades:

- realised return — compound each trade's `r_multiple` at `risk.position_size_pct`
  of running equity (start 10,000); return = final/initial − 1.
- max drawdown — peak-to-trough on that equity curve (a positive fraction).
- a simple Sharpe — mean(`r_multiple`) / stdev(`r_multiple`).
- win rate, and the spread of `asian_range_pips` on winners vs losers.

Then **think about the mechanism**, not just the numbers. Tag the recent regime
(trending vs ranging — e.g. 20-day rolling return of the pair, or the `macro.dxy`
context if present). Ask: are losers clustered in a regime? Are stops too tight
(many −1R that later would've hit target)? Is the `asian_min_range_pips` filter
letting in junk or starving the system of trades? Is buy-only the right side given
the regime? Is RR too greedy for the win rate?

## Step 4 — Form hypotheses, pick ONE

Generate 1–3 concrete hypotheses. Each must name **exactly one** variable in
`strategy.yaml`, predict the score direction, and say why. Tunable variables:

| Variable | Effect |
|---|---|
| `entry.asian_min_range_pips` | ↑ = fewer, higher-quality setups; ↓ = more trades |
| `entry.require_fvg_body` | true = stricter displacement filter |
| `entry.trade_side` | `buy` / `sell` / `both` (regime fit) |
| `stop.max_sl_pips` | stop-distance cap (drawdown vs survivability) |
| `stop.breakeven_at_r` | when to de-risk to BE |
| `target.rr` | reward:risk per trade (win-rate tradeoff) |
| `risk.position_size_pct` | sizing — the main drawdown lever |

Priority guidance (a starting point, not a straitjacket — reason past it when the
trades warrant): if `drawdown > max_drawdown`, the drawdown lever
(`risk.position_size_pct` or `stop.max_sl_pips`) wins; else if `realised_return <
target`, loosen the setup filter or adjust `target.rr` toward the observed win rate.
Pick the **single highest-confidence** change.

## Step 5 — Apply the one change

1. Snapshot: copy the current `strategy.yaml` → `$W/history/vNNNN.yaml` where NNNN
   is the current zero-padded `version` (e.g. `v0001.yaml`).
2. Edit `$W/strategy.yaml`: change the one variable, and bump `version` (`"01"`→`"02"`).
3. Append one line to `$W/hypotheses.jsonl`:
   ```json
   {"ts":"<iso8601 utc>","mode":"claude","to_version":"02",
    "change":{"variable":"<dotted.path>","old":<old>,"new":<new>},
    "rationale":"<one or two sentences of real reasoning>",
    "metrics":{"n":<n>,"realized_return":<r>,"drawdown":<dd>,"sharpe":<s>},
    "regime":"<trending|ranging|mixed>","trades_total":<current_total>,
    "pending":["<other ideas, optional>"],"one_variable_only":true}
   ```

## Step 6 — Push back to the volume

Upload only the files you changed (never `trades.jsonl`):

```
railway volume files --volume "$V" upload --overwrite "$W/strategy.yaml"        /strategy.yaml
railway volume files --volume "$V" upload --overwrite "$W/hypotheses.jsonl"     /hypotheses.jsonl
railway volume files --volume "$V" upload            "$W/history/vNNNN.yaml"    /history/vNNNN.yaml
```

(Prepend `MSYS_NO_PATHCONV=1` on Windows. The history upload omits `--overwrite`
because each version is written once.)

## Step 7 — Report

State plainly: the metrics you saw, the regime you judged, the **one** variable you
changed (old → new), your reasoning in a sentence, and the new version number. If
you no-op'd, say why. The live worker re-reads `strategy.yaml` every cycle, so the
change is already in effect — confirm by reading back `heartbeat.json` from the
volume and checking `strategy_version`.
