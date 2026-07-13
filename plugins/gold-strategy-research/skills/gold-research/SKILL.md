---
name: gold-research
description: Resume / review / drive the autonomous XAUUSD gold strategy-research loop in trade-research/strategy/gold. Use when the user wants to check progress on the gold strategy hunt, continue the Optuna search, review the latest milestone, or course-correct the strategies toward the 4%/mo @ 8%-maxDD goal. Reads only compact state so a fresh session stays cheap.
---

# Gold strategy research — resume & drive

You are picking up a long-running, mostly-deterministic gold (XAUUSD) strategy search. The heavy
lifting is Python; you are the periodic reviewer who interprets milestones and decides the next
experiment. **Keep context small** — read the compact state files below, NOT raw trial logs or
engine source, unless you are changing an engine.

Project root: `D:\projects\repos\trade-research` (run everything with `py -3.12` from there).
Code lives in `strategy/gold/`. The goal, sizing, validation and resource caps are in
`strategy/gold/goal.yaml`.

## 1. Orient (cheap reads only)
- `strategy/gold/research/state/champion.json` — current global best (params + opt/holdout/full metrics).
- `strategy/gold/research/state/orchestrator.json` — round count, plateau counter, recent history.
- The newest file in `strategy/gold/research/milestones/` — the latest honest write-up.
- `strategy/gold/research/state/best_<engine>.json` — per-engine champions (intraday_momentum, orb,
  mean_reversion, tsmom_overlay).
Summarize for the user: best avg/mo at the 8% DD budget, Calmar, **holdout vs opt** (overfit check),
cost sensitivity, and honest gap to the 4%/mo target.

## 2. Continue the search
- One round, foreground sanity: `py -3.12 strategy/gold/orchestrate.py --rounds 1`
- A batch then stop: `py -3.12 strategy/gold/orchestrate.py --rounds 10`
- Until plateau/goal (long; prefer background): `py -3.12 strategy/gold/orchestrate.py`
It is **resumable** — it re-reads state and re-seeds Optuna each round, so just run it again to keep
going. State is append-only; never delete `research/state/*` or `research/milestones/*` unless the
user explicitly asks to reset.

## 3. Course-correct (the part only you can do)
When milestones plateau, propose a NEW deterministic experiment rather than more of the same:
- add a TSMOM trend-filter gate to a breakout/mean-reversion engine (`engines/tsmom_overlay.py:TrendFilter`),
- new session windows / regime conditioning / a volatility filter,
- a new engine under `strategy/gold/engines/` following the shared interface
  (`NAME`, `Params`, `suggest(trial)`, `Engine(tf, years, cost).evaluate()->[bt_core.Trade]`, `default_tf()`),
  then add it to `STUDY_PLAN` in `orchestrate.py`.
Keep every rule mechanical (no discretion) so it can be optimized and regressed.

## 4. Non-negotiables
- Honesty first: always report **locked-holdout** and **cost-sensitivity** numbers, never just the
  in-sample best. The 4%/mo @ 8% maxDD target is a best-effort north star; report the true result.
- Verify before claiming: run the selftests (`py -3.12 strategy/gold/gold_metrics.py`, each engine
  file) after editing shared code.
- Respect the resource caps in `goal.yaml` (old machine; no GPU).
