# stock-research

India NSE 3-tier long-horizon rotation board (SAFE = Nifty 100, BALANCED = Midcap 150,
HIGH-RISK = Smallcap 250). The deterministic quant core (frozen, backtested champions) lives in
`D:\projects\repos\india-invest`; this plugin adds the orchestrator skill and the model-tiered
research agents that layer live news judgment on top.

## Components

| Component | Model | Role |
|---|---|---|
| `india-scan` (skill) | session (sonnet ok) | Orchestrates: refresh → scan → agents → verdicts → dashboard |
| `news-sweeper` (agent) | sonnet | Breadth triage of all holdings for adverse news |
| `stock-researcher` (agent) | **opus** | Deep notes + CONFIRM/VETO/FLAG verdicts (≤15 names) |
| `macro-analyst` (agent) | sonnet | Macro dashboard + sector commentary |
| `report-builder` (agent) | sonnet | Runs apply_verdicts + dashboard render, verifies outputs |

## Token economics

Opus is spent ONLY on the ~10–15 names where judgment matters (new buys, sells, flagged
holdings). Breadth work runs on sonnet. Everything computable is Python in india-invest —
agents exchange context by run-dir file paths, never pasted data, and no model writes HTML.

## Protocol (enforced in code, not prompts)

News may VETO or FLAG a quant pick; it can never add a stock the ranking didn't qualify
(`scan/apply_verdicts.py` rejects such verdicts). Quant-only and news-adjusted portfolios are
both journaled append-only so the news layer's added value is measured prospectively.

## Usage

Run `/india-scan` from a session whose cwd can reach `D:\projects\repos\india-invest`.
Monthly for the rebalance; ad-hoc for check-ins. Requires the three frozen champions in
`india-invest/research/state/` (produced by the one-time research phase).
