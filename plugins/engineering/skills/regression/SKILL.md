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

## Step 1 — Load the checklist (read, don't re-derive)

Read the durable regression checklist — a **committed** file in the repo's tracker/docs (default
`regression-checklist.md`, or a section of the stage tracker), **never** the ephemeral `.engineering/` dir
(that's per-stage and gitignored). `engineering:test` grows this file by one condition on each stage's clean
PASS, so the normal path here is simply **read it and run it** — you do not re-figure-out the cases. Only if
no checklist exists yet (a repo that predates this convention) do you bootstrap a minimal one from what's been
built so far (health endpoint, the key API(s) of each completed stage, tenancy isolation where applicable)
and note that you created it.

## Step 2 — Run it

Dispatch **`engineering:tester`** (model: `sonnet`), handing it `profile.md` if present, to execute each
checklist item against the target and return a single **PASS/FAIL** report: per item, the check performed and the actual result; for any FAIL, the
concrete repro and expected-vs-actual.

## Step 3 — Report (growth is owned by `test`)

- Report the outcome to the human: green, or exactly what regressed (a regression is a bug → route it into
  `engineering:test` / `engineering:implement` with the human's sign-off).
- The checklist **grows in `engineering:test`** on each stage's clean PASS, not here — so normally you add
  nothing. **Safety net only:** if you notice a completed stage's key condition is missing from the checklist,
  backfill that one line and say you did.

Keep it cheap: this should be a fast confidence check, not a full re-test of everything from scratch.
