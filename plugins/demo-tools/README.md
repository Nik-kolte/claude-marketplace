# demo-tools

Starter plugin for the `claude-marketplace`. Ships:

- **Skill** `hello` → invoke with `/demo-tools:hello <name>`
- **Agent** `code-explainer` → appears in `/agents`, explains code in plain language

## Structure

```
demo-tools/
├── .claude-plugin/plugin.json   # manifest (ONLY this file goes in .claude-plugin/)
├── skills/hello/SKILL.md        # → /demo-tools:hello
└── agents/code-explainer.md     # → /agents
```

Add more skills under `skills/<name>/SKILL.md` and more agents under `agents/<name>.md`.
Everything except `plugin.json` lives at the plugin root, never inside `.claude-plugin/`.
