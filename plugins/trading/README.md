# trading plugin

TradingView analysis and strategy-development tooling for the consolidated trading repo at
`D:\projects\repos\trading`. Read that repo's `instructions/` before using any of this — in
particular `instructions/01-point-in-time-backtesting.md`, which gates what may be optimized or
deployed at all.

## Contents

- `agents/tv-analyst.md` — expert TradingView analyst and Pine engineer. Drives the TradingView MCP
  (~78 tools over CDP to a live TradingView Desktop chart): chart analysis on any timeframe, reading
  custom Pine output, running and validating backtests, bar-replay walkthroughs, and developing new
  Pine strategies end to end.
- `agents/researcher.md` — **opus**. Open-minded strategy hunter. Reads the research journal so it
  never re-runs a dead idea, generates hypotheses from the literature and from first principles,
  screens them against the 3x cost clause **and Benjamini-Hochberg FDR at q=0.10**, builds engines
  for survivors, and hands up to 5 promising-but-imperfect candidates to the optimizer with a pitch
  deck each. Records every result — especially failures — back into the journal. Accepts an optional
  bias ("use RSI", "session-based only") to steer the search without lowering the bar.
- `agents/optimizer.md` — **opus**. Takes a strategy that already passed the research gate and
  finds the fastest *admissible* path to a funded prop account. Computes expected calendar days to
  funded (`research/core/funding_speed.py`), proves by arithmetic whether the speed target is
  reachable at all before searching, and either tunes within hard risk constraints or proposes new
  higher-frequency hypotheses that must clear the null screen first. Optimises time, never
  survival: a lower pass rate is tradeable, a higher breach rate is not. Reports "not reachable"
  rather than manufacturing a fast-looking breach.

## Requirements

**tv-analyst** needs TradingView Desktop running with CDP on port 9222. Launch via the repo's
`tools/tradingview-mcp/scripts/launch_tv_debug.*` or the MCP's `tv_launch` tool; `tv_health_check`
verifies the connection.

**optimizer** needs no TradingView. It runs against the research toolchain
(`cd research && uv sync`) and the parquet in `research/marketData/`.

## Protected paths

Never delete, overwrite, or truncate anything under `research/strategies/*/results/`. Those files
represent hours or days of compute — open logs in append mode, and ask before touching a result file.

## Removed

**2026-09-04** — `strategy-optimize` and `strategy-deploy` were deleted. Both still pointed at
`D:\projects
epos	rade-research` and `strategy/utils/`, paths that stopped existing at the
September consolidation into `trading/` with `research/core/`, so both would have failed on
invocation. The optimization role is now the `optimizer` agent, built against the real paths.

**2026-09-03** — `night-watch` (observe-only London-session journaling) and `strategy-study`
(weekly propose-only review) were removed along with the London ICT strategies they served and the
`improve/` journal tree they wrote to.

All are recoverable from git history if any of those workflows is ever wanted again.
