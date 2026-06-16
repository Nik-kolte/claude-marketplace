# claude-marketplace

A personal [Claude Code plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces) —
a catalog of plugins you can install to add skills and agents to Claude Code.

## Structure

```
claude-marketplace/
├── .claude-plugin/
│   └── marketplace.json          # the catalog (lists plugins + where to find them)
└── plugins/
    └── demo-tools/               # a plugin
        ├── .claude-plugin/
        │   └── plugin.json       # plugin manifest
        ├── skills/hello/SKILL.md # → /demo-tools:hello
        └── agents/code-explainer.md
```

Only `plugin.json` goes inside a plugin's `.claude-plugin/`. All component directories
(`skills/`, `agents/`, `commands/`, `hooks/`) live at the **plugin root**.

## Use it

Validate the catalog and manifests:

```
claude plugin validate d:\projects\repos\claude-marketplace
```

From inside a Claude Code session, add this marketplace and install a plugin:

```
/plugin marketplace add d:\projects\repos\claude-marketplace
/plugin install demo-tools@nikko-marketplace
/reload-plugins
```

Then try it:

```
/demo-tools:hello Nikko      # run the skill
/agents                      # code-explainer appears here
```

## Add a plugin

1. Create `plugins/<your-plugin>/.claude-plugin/plugin.json`.
2. Add `skills/<name>/SKILL.md` and/or `agents/<name>.md` at the plugin root.
3. Add an entry to the `plugins` array in `.claude-plugin/marketplace.json`.
4. `/plugin marketplace update nikko-marketplace` to pick up the new plugin.

## Publish later

Push this repo to GitHub and others add it with `/plugin marketplace add <owner>/<repo>`.
Relative-path sources work because git-based marketplaces clone the whole repository.
