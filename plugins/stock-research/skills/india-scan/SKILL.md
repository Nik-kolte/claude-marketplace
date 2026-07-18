---
name: india-scan
description: Run the India 3-tier stock rotation scan end-to-end - refresh EOD data, apply the frozen quant champions, dispatch model-tiered research agents (news sweep, deep verdicts, macro brief), apply verdicts mechanically, and render the local dashboard. Use for the monthly rebalance or an ad-hoc check-in on the india-invest board.
---

# india-scan — 3-tier rotation scan orchestrator

You orchestrate one scan of the india-invest board (repo: `D:\projects\repos\india-invest`).
Deterministic code computes everything computable; agents add ONLY live news judgment.
You run fine on Sonnet — do not do deep research yourself; that is the opus agent's job.

## Token rules (non-negotiable)

- Pass **paths + short task briefs** to agents. NEVER paste scan.json/parquet/notes content
  into a prompt or your own context. Read at most: the scan summary lines that scan.py PRINTS,
  and verdicts.json (small).
- Agents write their outputs as files in the run dir; downstream consumers read files.
- HTML is rendered by `scan/dashboard.py` (jinja2). No model ever writes HTML.
- If an agent fails, retry it once with the same brief; then continue without it and say so
  in your summary (a scan with no news layer is still a valid quant scan).

## Procedure

All commands run from `D:\projects\repos\india-invest`.

1. **Refresh data + scan (deterministic):**
   - `uv run python data/download.py --refresh`
   - `uv run python scan/scan.py`
   - Note the run dir it prints: `scan/output/run_<date>/` (call it RUN). The printed
     per-tier lines tell you the buys/sells counts and regime states — that's all the
     context you need.

2. **Dispatch in PARALLEL (one message, two Agent calls):**
   - `stock-research:news-sweeper` (sonnet): brief = "Run dir: <RUN absolute path>.
     Read scan.json's tier portfolios (holdings only), do a quick adverse-news sweep per
     holding since the previous scan, write sweep.json per your agent spec."
   - `stock-research:macro-analyst` (sonnet): brief = "Run dir: <RUN absolute path>.
     Read scan.json's sector_heat blocks only, research current India macro (RBI, inflation,
     FII/DII flows, global cues) and the hot/cold sectors, write macro.md per your agent spec."

3. **Dispatch `stock-research:stock-researcher` (opus)** after both return:
   brief = "Run dir: <RUN absolute path>. Deep-research every ticker in scan.json's buys and
   sells lists for all three tiers, plus every ticker flagged in sweep.json. Read macro.md
   for context. Write verdicts.json + notes.md per your agent spec. Hard cap: 15 deep notes —
   triage by materiality if more qualify and say which you skipped."

4. **Apply + render (deterministic):**
   - `uv run python scan/apply_verdicts.py <RUN>`
   - If it prints any `[REJECTED]` line: report that in your summary verbatim — an agent
     tried to add a non-qualified stock and the protocol blocked it.
   - `uv run python scan/dashboard.py <RUN>`

5. **Summarize to the user in chat** (this is the only prose you write):
   per tier: regime state, buys/sells with the researcher's verdict one-liners, any vetoes/
   flags, and the dashboard path `dashboard/index.html`. Keep it under ~25 lines.

## Guardrails

- Never edit `research/state/best_*.json` (frozen champions), `research/results/*`, or
  `journal/*` by hand — `apply_verdicts.py` is the only journal writer.
- If scan.py fails because a champion file is missing, STOP and tell the user the research
  phase hasn't produced/validated that tier yet.
- This board is advisory. Never place orders, never call broker APIs.
