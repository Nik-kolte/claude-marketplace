# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Personal [Claude Code plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces)
named `nikko-marketplace` — a catalog of plugins (skills + agents) the operator installs into
Claude Code. No build step; the "code" is JSON manifests and Markdown skill/agent definitions.

## Commands

```bash
claude plugin validate d:\projects\repos\claude-marketplace    # validate catalog + every plugin.json
```

From inside a Claude Code session:
```
/plugin marketplace add d:\projects\repos\claude-marketplace
/plugin install <plugin>@nikko-marketplace
/plugin marketplace update nikko-marketplace      # after adding/editing a plugin
```

## Structure & the rule that bites

```
.claude-plugin/marketplace.json     # the catalog: lists plugins + their ./plugins/<name> source
plugins/<name>/
  .claude-plugin/plugin.json        # plugin manifest — ONLY this file goes in .claude-plugin/
  skills/<name>/SKILL.md            # component dirs live at the PLUGIN ROOT, not under .claude-plugin/
  agents/<name>.md
```

**The structural rule:** only `plugin.json` belongs in a plugin's `.claude-plugin/`. All component
directories (`skills/`, `agents/`, `commands/`, `hooks/`) sit at the plugin **root**. Getting this
wrong is the most common validation failure.

Adding a plugin = create `plugins/<name>/.claude-plugin/plugin.json` + components, then add an entry
to the `plugins` array in `.claude-plugin/marketplace.json`.

## Current plugins

- **demo-tools** — starter: a `hello` skill + `code-explainer` agent.
- **trading** — `tv-analyst` agent + `night-watch` / `strategy-study` skills, driven by the
  TradingView MCP (see the `tradingview-mcp` and `trade-research` projects in this workspace).
- **trade-reflect** — `reflect` skill: the self-improvement brain for the cloud paper-trading worker
  (`trade-selflearning`), evolving `strategy.yaml` one variable per cycle.
- **personal** — `cc-statement` skill: credit-card statement parsing / expense categorisation.
