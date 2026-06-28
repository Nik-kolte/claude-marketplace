# trading

TradingView analysis & strategy-development tooling for Claude Code.

## Contents

- `agents/tv-analyst.md` — expert TradingView analyst + Pine Script engineer. Drives the
  TradingView MCP to analyze charts on any timeframe, scroll/zoom to specific dates, read
  custom Pine indicator output, run and validate backtests, perform bar-replay walkthroughs,
  and build + validate new Pine strategies and indicators. Includes a self-diagnosis &
  repair playbook for when the MCP itself misbehaves.
- `skills/night-watch/` — **observe-only** live-session journaling. During the London
  killzone (~2–5am New York time) it snapshots EURUSD + GBPUSD and logs what the three
  London-session ICT strategies *would* signal vs. what the market actually does,
  appending to `improve/journal/` in the tradingview-mcp repo. Invoke as
  `/trading:night-watch`. Never trades, never edits strategy files.
- `skills/strategy-study/` — **propose-only** weekly review. Mines the night-watch
  journals for patterns/near-misses, optionally re-runs the offline Python backtesters,
  and writes honest improvement proposals to `improve/findings/`. Invoke as
  `/trading:strategy-study`. Never edits the locked strategy specs or protected results.

## Scheduling the night-watch loop (local only)

The TradingView MCP drives a **local** TradingView Desktop over CDP `localhost:9222`,
so the scheduler must run on the same machine — Anthropic cloud routines cannot reach
it. Use a **Claude Desktop → Routines → New → Local** task (or Windows Task Scheduler
running `claude -p "/trading:night-watch"`). Set the project folder to your
tradingview-mcp repo so `./improve/` resolves there.

> **Timezone:** the killzone is New York time. On an IST machine that lands ~10:50–15:05
> IST (it shifts an hour across US DST). Schedule the OS trigger broadly across that
> IST window every ~25 min; the skill gates on the live NY clock and skips firings
> outside 01:25–05:00 NY, so over-scheduling is harmless. Run `strategy-study` weekly
> (e.g. Sundays). Full setup steps live in the tradingview-mcp repo at `improve/README.md`.

## Requirement

The `tv-analyst` agent depends on the **TradingView MCP** server being installed and running,
connected to a live TradingView Desktop via CDP on port `9222`. Register it (user scope) in
`~/.claude/.mcp.json`:

```json
{
  "mcpServers": {
    "tradingview": { "command": "node", "args": ["<path>/tradingview-mcp/src/server.js"] }
  }
}
```

TradingView Desktop must be launched with `--remote-debugging-port=9222`. The agent runs
`tv_health_check` first and will guide you if the connection isn't ready.

## Use

Invoke the agent by name (e.g. "use tv-analyst to analyze my chart" or via the Task tool).
After adding or updating this plugin, run `/plugin marketplace update nikko-marketplace`.
