---
name: regression
description: Run the accumulated smoke/regression checklist against a running environment (local or deployed) using the tester agent, and report exactly what passed or regressed. Thin and reusable — grows one verified condition per stage. Use standalone to sanity-check an environment, or as the final step of deploy after a release.
---

# Regression — does everything we've built still work?

You run the standing **regression checklist** against a target environment and report honestly. This is
deliberately thin: it's the set of conditions we've verified over past stages, re-checked so a new change
hasn't broken an old guarantee. It grows by **one condition per stage**, not by a big upfront suite.

## Step 0 — Orient & pick the target

Reuse the stage's **`profile.md`** if one exists (health endpoint, key routes, run commands) rather than
re-discovering; the tester reads it. Determine the target environment from the caller or ask: **local**
(running dev server / local DB) or a **deployed** URL. Get the base URL/health endpoint for that target.

## Step 1 — Load the suite (read, don't re-derive)

The durable regression coverage is, preferably, the **committed automated test suite** the tester built up
across stages — plus a `regression-checklist.md` (or a section of the stage tracker) for any conditions not
worth automating. Both are **committed** files, **never** the ephemeral `.engineering/` dir (that's per-stage
and gitignored). `engineering:test` grows them on each stage's clean PASS, so the normal path here is simply
**run the suite and read/run the checklist** — you do not re-figure-out the cases. Only if neither exists yet
(a repo that predates this convention) do you bootstrap a minimal checklist from what's been built so far
(health endpoint, the key API(s) of each completed stage, tenancy isolation where applicable) and note that
you created it.

## Step 2 — Run it

Dispatch **`engineering:tester`** (model: `sonnet`), handing it `profile.md` if present, to **run the
automated test suite** and execute each remaining checklist item against the target, returning a single
**PASS/FAIL** report: per suite/item, the check performed and the actual result; for any FAIL, the concrete
repro and expected-vs-actual.

## Step 3 — Report (growth is owned by `test`)

- Report the outcome to the human: green, or exactly what regressed (a regression is a bug → route it into
  `engineering:test` / `engineering:implement` with the human's sign-off).
- The checklist **grows in `engineering:test`** on each stage's clean PASS, not here — so normally you add
  nothing. **Safety net only:** if you notice a completed stage's key condition is missing from the checklist,
  backfill that one line and say you did.

Keep it cheap: this should be a fast confidence check, not a full re-test of everything from scratch.

## Step 4 — Self-check: what would make this phase run smoother?

Before handing off, take a quick pass over how this run went — was the target environment ambiguous, was the
checklist stale or missing a condition it should already have, did the tester have to re-derive anything it
should have just read. This is a cheap check, not an audit — a couple of bullet points, or "ran clean,
nothing to flag" if it did.

If something real surfaces, propose a **concrete fix** — usually a specific edit to this skill's instructions
or the committed `regression-checklist.md` itself. Present the finding + proposed fix to the human; **don't
edit the plugin files yourself** — that's a change to the SDLC machinery itself, the human's call. (Editing
the repo's own `regression-checklist.md` to fix a stale/wrong line is fine — that's normal maintenance of a
committed doc, not a change to the plugin.)
