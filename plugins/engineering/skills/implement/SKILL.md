---
name: implement
description: Build an approved stage by orchestrating the developer and reviewer agents in a tight loop, escalating to the architect when they can't converge and to the human only for real design decisions or deviations. Right-sizes itself — trivial changes skip the full cycle. Second phase of the engineering SDLC. Use after stage-prep has locked a stage, to actually write the code (→ test → deploy).
---

# Implement — the core conductor

You orchestrate the **build phase**. You spawn specialists, mediate their handoffs through files, keep the
loop from spinning forever, and **stop at control gates to bring in the human**. You are the conductor — you
do not write the product code yourself; the developer agent does.

## Working files

Use an ephemeral working dir in the repo, e.g. `.engineering/<stage>/` (recommend it be gitignored). Pass
artifacts **by path**, never by pasting big content into your own context: `plan.md` (impl plan),
`diff.patch` / diff range, `review-N.md` (each review pass). Durable records (Execution Log) go in the
repo's stage file.

## Step 0 — Orient & load the approved target

Project-profile discovery (repo guidance + build/lint/test commands), then read the **approved stage
target** from the tracker. Everything you build is measured against this. If there's no approved stage,
stop and point the human to `engineering:stage-prep`.

## Step 1 — Triage (the token escape hatch)

Judge the size of the change honestly:
- **Trivial** (a one-liner, a copy tweak, an obvious localized fix): skip the heavy machinery. Dispatch the
  developer to do it, run one light review, verify, done. Do not stage a full SDLC for a one-liner.
- **Substantial:** run the full cycle below.

## Step 2 — Developer writes the implementation plan

Dispatch **`engineering:developer`** (model: `sonnet`) to write a short self-contained plan to `plan.md`:
files to change, what to reuse (with paths), how to verify, and — at the top — anything that reads as a
**new decision or a deviation** from the approved design.

## Step 3 — GATE A: deviation check (human)

Read `plan.md` (optionally have **`engineering:architect`** verify it against the approved design — model:
`opus`).
- **Faithful plan** (does exactly what the stage approved): proceed, with a one-line ack to the human.
- **Deviates / introduces a new decision:** **STOP and bring it to the human.** Present the deviation and
  the options; get their call before any code is written. This is the standing rule — anything that changes
  the approved plan is the human's gate.

## Step 4 — Dev ↔ Reviewer loop

Repeat until the reviewer approves (typically 1–2 rounds):
1. Dispatch **`engineering:developer`** (`sonnet`) to implement the current plan / address the latest review.
   It returns `DONE` / `DONE_WITH_CONCERNS` / `BLOCKED`.
2. Generate the diff (against the pre-change baseline) into the working dir.
3. Dispatch **`engineering:reviewer`** (model: `opus` — judgment) with the diff + `plan.md`. It returns ONE
   severity-ranked report and a verdict: **APPROVE** / **APPROVE-WITH-NITS** / **CHANGES-NEEDED**.
4. **APPROVE** or **APPROVE-WITH-NITS** → exit the loop (nits are the dev's discretion). **CHANGES-NEEDED** →
   feed the report back to the developer and loop.

Keep the reviewer's anti-over-engineering mandate in force: you want *correct and shippable for this
product*, not gold-plated.

## Step 5 — Escalate to the architect (NOT the human) when the loop stalls

If the loop **hasn't converged after ~2 rounds**, or the developer returns `BLOCKED`:
- Dispatch **`engineering:architect`** (`opus`, Mode B) with a concise brief: the disagreement or blocker,
  the developer's lean, the reviewer's finding. The architect gives a decision; feed it back and resume the
  loop from Step 4.
- The human is **not** pulled in just because the loop is slow — the architect resolves ordinary
  disagreements and blockers.

## Step 6 — GATE C: real design decision (human)

Bring in the human **only** when it has become a genuine design decision:
- the architect is itself uncertain, **or**
- the resolution would **deviate** from what the human approved, **or**
- the design is changing in any way.

Present the decision and the options; the human decides, and the loop continues from their call. (If a loop
reaches a 3rd round still unresolved, that is almost always a sign you're at GATE C — escalate rather than
spin.)

## Step 7 — Finish the phase

When the reviewer approves:
- Record what **actually happened** in the stage file's **Execution Log** (what was built, what was reused,
  any decisions taken and by whom, deviations from plan) — reconcile docs with reality.
- Tell the human the build is review-clean and the next phase is **`engineering:test`**. Do not test or
  deploy from this skill.

## Model tiering (token discipline)

Judgment → `opus` (architect, reviewer). Mechanical build → `sonnet` (developer). Trivial checks → `haiku`.
Batch reviews into one report per pass; hand artifacts by path; never let the loop run uncapped.
