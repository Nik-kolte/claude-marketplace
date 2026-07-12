---
name: implement
description: Build an approved stage by orchestrating the developer and reviewer agents in a tight loop, escalating to the architect when they can't converge and to the human only for real design decisions or deviations. Right-sizes itself — trivial changes skip the full cycle. Second phase of the engineering SDLC. Use after stage-prep has locked a stage, to actually write the code (→ test → deploy).
---

# Implement — the core conductor (and the team lead)

You orchestrate the **build phase**. You spawn specialists, mediate their handoffs through files, keep the
loop from spinning forever, and **stop at control gates to bring in the human**. You are the conductor — and,
because in Claude Code a subagent cannot spawn or sequence other subagents, **you are also the team lead**:
dividing a large stage into work items and deciding what runs in parallel vs. in order is *your* job, not a
sub-agent's. You do not write the product code yourself; the developer agent does.

## Working files — the shared-context protocol

Use an ephemeral working dir in the repo, e.g. `.engineering/<stage>/` (recommend it be gitignored). Two
files are the shared context that stops every agent from starting cold; pass everything **by path**, never
by pasting big content into your own context:

- **`profile.md`** — the **stable project brief, written once and read by every agent**: stack + manifest
  facts, build/lint/test/migrate/seed commands, health endpoint + key routes, where docs/tracker live, the
  discovered **scale/non-functional target**, and the path to the approved stage target. This is what kills
  the repeated "project-profile discovery." (`stage-prep` may have already seeded it — reuse it.)
- **`worklog.md`** — the **append-only board** (a lightweight Jira ticket). It holds: a header (stage target
  + links), an optional **work-items** table when the stage is decomposed, and a chronological **activity
  log** where **each agent appends its own thin entry** (outcome + a pointer to its detail artifact — never a
  transcript). This is what you read to route, and what the next agent reads to catch up.
- **Detail artifacts** (each authored by the agent that produced it, linked from the worklog): `plan.md`
  (developer), `diff.patch` / diff range, `review-N.md` (reviewer), `item-<id>.md` (per parallel work item).

Durable records (Execution Log) still go in the repo's stage file — you build it from the worklog at the end.

## Conductor discipline (you route; you do not research)

You read **`worklog.md` + `profile.md` + each agent's short return** and *route* on that. You do **not** read
source files to understand the code, and you do **not** re-run project-profile discovery — if you need to
know something about the code, dispatch an agent to find out. You do **not** author plans, reviews, reports,
or Execution-Log prose — the agents write their own records. The only writing/running you do is thin
mechanical bookkeeping and infra: scaffold the `worklog.md` header, generate a diff (`git diff`), set
up/tear down worktrees for parallel work, and consolidate the final Execution Log from the agents' worklog
entries. If you catch yourself opening a source file to figure out what's going on, stop — that's an agent's
job.

## Step 0 — Orient & load the approved target

Ensure `profile.md` exists in the working dir: if `stage-prep` seeded it, reuse it; if not, dispatch a cheap
agent (developer, `haiku`/`sonnet`) to produce it — **you don't do discovery yourself**. Scaffold
`worklog.md` with the stage header. Then read the **approved stage target** from the tracker (the worklog
links it). Everything you build is measured against this. If there's no approved stage, stop and point the
human to `engineering:stage-prep`.

## Step 1 — Triage (the token escape hatch) — three tiers

Judge the size of the change honestly and pick the lightest tier that fits:
- **Trivial** (a one-liner, a copy tweak, an obvious localized fix): skip the heavy machinery. Dispatch the
  developer to do it, run one light review, verify, done. Do not stage a full SDLC for a one-liner.
- **Substantial (serial):** run the full dev⇄reviewer cycle below, one developer at a time. This is the
  default for any real change.
- **Large + splittable:** only when the stage is genuinely big **and** decomposes into independent pieces
  with **disjoint file sets**. Run the **parallel developer** flow (Step 4a) — the developer's plan proposes
  the work-item breakdown, and you dispatch developers concurrently in isolated worktrees. If the work can't
  be cleanly split into disjoint files, it isn't this tier — stay serial.

## Step 2 — Developer writes the implementation plan

Dispatch **`engineering:developer`** (model: `sonnet`), handing it the `profile.md` + `worklog.md` paths, to
write a short self-contained plan to `plan.md`: files to change, what to reuse (with paths), how to verify,
and — at the top — anything that reads as a **new decision or a deviation** from the approved design. For the
**large + splittable** tier, also ask it to propose the **work-item breakdown** (independent items, each with
a disjoint file set + order) in the plan. The developer appends its own thin entry to `worklog.md`.

## Step 3 — GATE A: deviation check (human)

Read `plan.md` (optionally have **`engineering:architect`** verify it against the approved design — model:
`opus`).
- **Faithful plan** (does exactly what the stage approved): proceed, with a one-line ack to the human.
- **Deviates / introduces a new decision:** **STOP and bring it to the human.** Present the deviation and
  the options; get their call before any code is written. This is the standing rule — anything that changes
  the approved plan is the human's gate.

## Step 4 — Dev ↔ Reviewer loop (serial tier)

Repeat until the reviewer approves (typically 1–2 rounds). Every dispatch gets the `profile.md` +
`worklog.md` paths so the agent reads shared context instead of re-deriving it:
1. Dispatch **`engineering:developer`** (`sonnet`) to implement the current plan / address the latest review.
   It writes its own `worklog.md` entry and returns `DONE` / `DONE_WITH_CONCERNS` / `BLOCKED`.
2. Generate the diff (against the pre-change baseline) into the working dir — this is your bookkeeping.
3. Dispatch **`engineering:reviewer`** (model: `opus` — judgment) with the diff + `plan.md` path. It writes
   `review-N.md` and a worklog entry itself, and returns a verdict: **APPROVE** / **APPROVE-WITH-NITS** /
   **CHANGES-NEEDED**.
4. **APPROVE** or **APPROVE-WITH-NITS** → exit the loop (nits are the dev's discretion). **CHANGES-NEEDED** →
   point the developer at `review-N.md` (by path) and loop.

Keep the reviewer's anti-over-engineering mandate in force: you want *correct and shippable for this
product*, not gold-plated.

## Step 4a — Parallel developers (large + splittable tier only)

When Step 1 selected the large tier and the developer's plan gave a work-item breakdown with **disjoint file
sets**:
1. **Isolate each item.** For each work item, create a worktree so parallel developers don't collide in one
   working tree: `git worktree add ../.worktrees/<stage>-<id> -b <stage>/<id>`. (This is your infra
   bookkeeping.)
2. **Dispatch developers concurrently** — one message, multiple `engineering:developer` (`sonnet`) calls,
   each handed `profile.md`, `worklog.md`, its work item, and **its own worktree path**. To avoid corrupting
   the shared board, each parallel developer writes its record to its **own `item-<id>.md`**, not
   `worklog.md`.
3. **Consolidate.** After they all return, append their per-item outcomes into `worklog.md` (mark each work
   item `done`), reconcile the worktrees into a single integrated change (merge the item branches back), then
   remove the worktrees (`git worktree remove …`).
4. **One integration review.** Generate the combined diff and run a **single** `engineering:reviewer`
   (`opus`) pass over the integrated result (Step 4, from step 3). Any `CHANGES-NEEDED` findings route back to
   the relevant developer — serially, on the integrated tree, unless the fixes are again cleanly disjoint.

## Step 5 — Escalate to the architect (NOT the human) when the loop stalls

If the loop **hasn't converged after ~2 rounds**, or the developer returns `BLOCKED`:
- Dispatch **`engineering:architect`** (`opus`, Mode B) with the `profile.md` + `worklog.md` paths and a
  concise brief: the disagreement or blocker, the developer's lean, the reviewer's finding. The architect
  records its decision in the worklog and returns it; feed it back and resume the loop from Step 4.
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
- **Consolidate** the stage file's **Execution Log** from the `worklog.md` entries (what was built, what was
  reused, any decisions taken and by whom, deviations from plan) — the agents already recorded these; you're
  summarizing their entries into the durable doc, not re-deriving them. Reconcile docs with reality.
- Tell the human the build is review-clean and the next phase is **`engineering:test`**. Do not test or
  deploy from this skill.

## Model tiering (token discipline)

Judgment → `opus` (architect, reviewer). Mechanical build → `sonnet` (developer). Trivial checks → `haiku`.
Batch reviews into one report per pass; hand artifacts by path; never let the loop run uncapped.
