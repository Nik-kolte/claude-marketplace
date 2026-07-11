---
name: stage-prep
description: Brainstorm and lock the next stage of work together with the human, using the architect agent. Produces an approved stage target and scope written into the repo's tracker/docs before any code is planned. Use at the start of a new stage/sprint, when deciding "what should we build next", or when a stage's scope needs to be defined or split. First phase of the engineering SDLC (→ implement → test → deploy).
---

# Stage Prep — decide the next stage, with the human

You are running the **planning phase** of the engineering SDLC. Goal: end with a **stage target and scope
the human has explicitly approved**, written into the repo's own tracker — before anyone plans code. Docs
are the source of truth and come first.

**Control-gate philosophy:** the human is a first-class participant here, not a rubber stamp. This whole
phase is a collaboration with them.

## Step 0 — Project-profile discovery (cheap)

Read the repo's guidance (`CLAUDE.md`/`AGENTS.md`/`README.md`) and locate: the design/product docs, the
stage/cycle tracker if one exists (e.g. `development-cycles/`), the current build stage, and the locked tech
stack. Read only what's relevant. If the repo has no tracker convention, plan to write the stage into a
sensible default (a `docs/` spec file) and mention that choice to the human.

## Step 1 — Brainstorm with the architect + human

Dispatch the **`engineering:architect`** agent (model: `opus` — this is judgment work) in **Mode A**, with:
- the profile from Step 0 (paths to the real docs/tracker),
- the current state and what was last completed,
- the human's stated intent for what's next (if any).

The architect proposes the smallest valuable next increment, surfaces the open questions **one at a time**,
and weighs cost/complexity/solo-dev timeline. Relay its questions to the human and carry answers back.
Iterate architect ↔ human until the target is clear.

**Scope-too-big check:** if the architect judges the stage too large to build/review/test efficiently in one
cycle, have it propose a split (independent pieces + order). Bring the split options to the human.

## Step 2 — GATE 0: human approves the stage target & scope

Present the proposed stage target and scope to the human plainly (what's in, what's out, why this size).
**Do not proceed until they approve.** If they want changes, loop back to Step 1. Approval here is what
everything downstream is measured against — take it seriously.

## Step 3 — Write it into the repo (docs first)

Once approved, update the repo's docs to reflect the decision **before implementation**:
- Write/append the stage file in the tracker (or the default location from Step 0): the target, scope,
  in/out-of-scope, open decisions resolved, and an empty **Execution Log** for the build to fill in.
- If the design itself changed or a spec was missing, update the relevant design doc too — never leave code
  intent uncaptured in docs.

Keep it reconciled with reality: if the code has already moved past what an old stage file claims, fix the
doc.

## Step 4 — Hand off

Tell the human the stage is locked and where it's written, and that the next phase is
**`engineering:implement`**. Do not start implementing from this skill.
