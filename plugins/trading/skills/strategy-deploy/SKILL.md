---
name: strategy-deploy
description: Convert an approved trade-research strategy into a TradingView Pine Script strategy plus companion indicator, load it on a live chart, and run a fidelity comparison between the Python backtest and TradingView's Strategy Tester, producing an honest HTML fidelity report. Requires a handoff summary from strategy-optimize (or equivalent approval context). Delegates Pine authoring to the tv-analyst agent and reuses the strategy-report skill's data-pull sequence. Use once a strategy has been approved and is ready to become a real TradingView script.
---

# Strategy Deploy — Pine Conversion & Fidelity Report

You are taking an approved Python strategy from `trade-research` and turning it into
a real TradingView Pine Script strategy + indicator, then honestly checking whether
TradingView's execution reproduces what the Python backtest found.

## Absolute rules (do not violate)

- **Never touch** `research/state/LOCKED/`, any milestone `.md`, or the champion JSON —
  those belong to `strategy-optimize`.
- **Pine saves are additive.** Use `pine_new` + `pine_save` for genuinely new scripts. Never
  call `pine_set_source` onto an existing named script the user cares about without their
  explicit confirmation first — see the `tv-analyst` agent's Section 6 overwrite-bug history
  for why this matters.
- **HTML for the final fidelity report, Markdown for working notes.**
- Respect all protected paths from both `trade-research/CLAUDE.md` and
  `tradingview-mcp/CLAUDE.md`.
- **`strategy/utils/{goal_schema,prop_firms,generic_optimizer,orchestrate_core}.py` are shared
  framework code** (used by `strategy-optimize`) — this skill doesn't need them, but if you ever
  touch them for any reason, that's out of scope for a normal deploy run; only edit them when the
  user is explicitly asking to update the shared optimizer infrastructure itself.

## Working directories

`D:\projects\repos\trade-research` (read the champion/spec) and
`D:\projects\repos\tradingview-mcp` (Pine authoring + live chart).

## Step 0 — Receive and validate the handoff

Parse the handoff block from `strategy-optimize` (or ask the user for it / the missing pieces):
`strategy_folder`, `champion_json`, `final_report`, `symbol`, `is_window`/`oos_window`, champion
IS/OOS CAGR + maxDD, `prop_firm`/`account_type`. Confirm `champion_json` and `final_report` exist
and are non-empty before continuing.

## Step 1 — Naming discussion

Before writing any Pine code, read the strategy's spec (`strategy/<name>/<name>.md` if present)
for context, then propose 2-3 name options for the pair:
- one technical (signal type + timeframe, e.g. "GBPUSD London-Open Breakout M15"),
- one market-facing/memorable,
- one literal to the ICT setup if applicable.

Ask which the user prefers (or for their own name), and whether the strategy and indicator
should share a name prefix (e.g. `[<name>] Strategy` / `[<name>] Signals`).

## Step 2 — Pine strategy development (delegate to tv-analyst)

Hand this off to the `tv-analyst` agent, following its Section 6 dev loop exactly:
`pine_analyze` → `pine_check` → `pine_new {type:"strategy"}` → `pine_set_source` →
`pine_smart_compile` → fix via `pine_get_errors`/`pine_get_console` → validate on chart →
`pine_save` with the agreed name.

Brief tv-analyst with:
- the champion parameters (from `champion.json`) as `input.*()` defaults,
- the mechanical entry/exit rules from the strategy's spec,
- commission/slippage settings in the `strategy()` declaration that match the Python backtest's
  cost assumptions (spread_pips / fixed pip cost) as closely as TradingView's model allows —
  this matters directly for Step 7's fidelity comparison,
- the agreed name from Step 1.

Save a local copy to `strategy/<name>/<name>_strategy.pine` in `trade-research` (a new,
unprotected file).

## Step 3 — Pine indicator development (delegate to tv-analyst)

Same delegation for a companion **indicator** — visual-only signals (shapes/labels/lines)
mirroring the strategy's entries, `overlay=true`, named `[<name>] Signals` or the user's
preferred suffix. Save to `strategy/<name>/<name>_indicator.pine`.

## Step 4 — Load on chart

1. `tv_health_check` (launch via `tv_launch` if needed).
2. `chart_set_symbol` to the strategy's symbol, `chart_set_timeframe` to its primary timeframe.
3. `pine_open {name: "<agreed strategy name>"}`, then `pine_smart_compile` to confirm it loads
   clean.
4. `ui_open_panel {panel: "strategy-tester", action: "open"}`.

## Step 5 — TradingView-side data pull

Reuse the `strategy-report` skill's canonical sequence rather than re-deriving it:
1. `data_get_strategy_results` — full metrics payload.
2. `data_get_trades {max_trades: 20}` — spot-check individual trades.
3. `data_get_equity {max_points: 1000}` — equity curve.
4. `capture_screenshot {region: "strategy_tester"}` and `capture_screenshot {region: "chart"}`.

## Step 6 — Python-side comparison data

Read the OOS metrics from `champion.json` and the relevant milestone: OOS total return%, CAGR,
max drawdown, trade count, win rate, profit factor, per-year OOS returns, and the risk% used.

## Step 7 — Fidelity comparison and HTML report

Write `strategy/<name>/research/fidelity_<YYYY-MM-DD>.html`:

- **Summary verdict** (2-3 sentences): good fidelity (OOS CAGR direction consistent, magnitude
  within ~30%), acceptable (30-60% divergence, still profitable both sides), or poor (opposite
  sign OOS between Python and TradingView).
- **Side-by-side metrics table** (OOS window): total return%, CAGR%/yr, max drawdown%, trade
  count, win rate%, profit factor — Python column vs TradingView column vs delta.
- **Divergence attribution table** — explain, don't just flag, each source: spread/commission
  model (Python's fixed pip cost vs TradingView's `strategy()` commission setting), slippage
  (Python's assumption vs TradingView's simulated bar-close fills), execution-model timing
  (Python's specific bar entry vs TradingView's next-bar-open `strategy.entry()` default — often
  the largest source for intraday strategies), and data/history-depth (TradingView Essentials'
  capped intraday history — should be sufficient for a 2024+ OOS window on most strategies).
- **Per-year comparison** where TradingView's history allows.
- **Visual evidence** — embed the Step 5 screenshots.
- **Recommendation**: is fidelity acceptable to proceed to paper trading, or what to investigate
  first (e.g. switch fill timing, recalibrate commission to match spread_pips).

## Step 8 — Summary

Report back: both Pine file paths (local + confirmed TradingView cloud save), the fidelity report
path, a one-paragraph verdict, and recommended next steps.
