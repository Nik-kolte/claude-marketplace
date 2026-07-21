---
name: prospect-scan
description: Run the Harsh-method NSE swing-prospect scan end-to-end - refresh the IPO watchlist via the sweeper agent, run the deterministic screeners (monthly-ROC market-cycle gate, near-ATH sector leaders, recent-IPO VCP/base breakouts), dispatch the opus researcher for STRONG/WATCH/PASS ratings, and render the prospects dashboard. Use to find new swing/momentum investment candidates on the NSE, or for an ad-hoc market-cycle check.
---

# prospect-scan — Harsh-method swing screener orchestrator

You orchestrate one prospect scan (repo: `D:\projects\repos\india-invest`, package
`prospects/`). Deterministic Python computes everything computable (cycle gate, both
engines, fundamentals soft flags); agents add ONLY the live web layer (fresh IPO
listings, deep research). This is a separate, shorter-horizon strategy from the
3-tier rotation board — it shares data but never touches the board's files.

## Token rules (non-negotiable, same as india-scan)

- Pass **paths + short task briefs** to agents. NEVER paste candidates.json or price
  data into a prompt or your own context. Read at most: the summary lines the Python
  scripts PRINT, and the agents' one-line returns.
- Agents write files into the run dir; downstream consumers read files.
- HTML is rendered by `prospects/dashboard.py` (jinja2). No model ever writes HTML.
- If an agent fails, retry once with the same brief; then continue without it and say
  so (a scan with no ratings column is still a valid quant scan).

## Procedure

All commands run from `D:\projects\repos\india-invest`.

1. **Freshen the IPO watchlist (sonnet agent, before the scan):** dispatch
   `stock-research:prospect-sweeper`, brief = "Update the IPO watchlist per your agent
   spec." Wait for its one-line report. If it failed, continue — the scan still works
   on its data-derived IPO universe.

2. **Refresh data + scan (deterministic):**
   - `uv run python data/download.py --refresh`
   - `uv run python prospects/scan_prospects.py`
   - Note the run dir it prints: `prospects/output/run_<date>/` (call it RUN). The
     printed `[cycle] / [engine_ath] / [engine_ipo] / [fundamentals]` lines are all
     the context you need.

3. **Deep ratings (opus agent):** dispatch `stock-research:prospect-researcher`,
   brief = "Run dir: <RUN absolute path>. Read candidates.json, triage to <=12 names
   per your agent spec, research and write ratings.json + notes.md there."

4. **Render (deterministic):** `uv run python prospects/dashboard.py <RUN>`

5. **Summarize to the user in chat** (the only prose you write, <=20 lines):
   market-cycle stance line (ROC readings + gold tilt), the researcher's rating
   one-liners grouped STRONG / WATCH / PASS, anything actionable from Engine A
   (breakouts/tight bases), and the dashboard path `prospects/dashboard/index.html`.

## Guardrails

- Never touch the rotation board: `research/state/*`, `journal/*`, `scan/*`,
  `research/results/*` are off-limits to this skill.
- `prospects/data/ipo_watchlist.csv` is append-only (the sweeper's spec enforces it).
- The evidence basis for the encoded rules is the one-time validation in
  `prospects/reports/` (ROC checkpoints 6/6; Engine B backtest 2013-2026 +4.9%/6m
  excess after costs, edge decays post-2020). If a user asks whether to trust a
  signal, point them at that report — do not oversell.
- Advisory only. Never place orders, never call broker APIs.
