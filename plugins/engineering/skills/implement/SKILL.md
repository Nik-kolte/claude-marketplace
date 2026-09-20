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

Use an ephemeral working dir in the repo, e.g. `.engineering/<stage>/` (recommend it be gitignored). Three
files are the shared context that stops every agent from starting cold; pass everything **by path**, never
by pasting big content into your own context:

- **`profile.md`** — the **stable project brief, written once and read by every agent**: stack + manifest
  facts, build/lint/test/migrate/seed commands, health endpoint + key routes, where docs/tracker live, the
  discovered **scale/non-functional target**, the repo's **testing strategy** (framework, layers, what's
  worth covering — or "none yet"), and the path to the approved stage target. This is what kills the repeated
  "project-profile discovery." (`stage-prep` may have already seeded it — reuse it.)
- **`worklog.md`** — the **append-only board** (a lightweight Jira ticket). It holds: a **Status block at the
  top** (current phase, active work item, and the specific latest artifact paths — `plan.md`/`review-N.md`/
  `bugs-N.md` — you keep this current as part of your mechanical bookkeeping), an optional **work-items**
  table when the stage is decomposed, and a chronological **activity log** below it where **each agent
  appends its own thin entry** (outcome + a pointer to its detail artifact — never a transcript). You read
  the whole thing to route. **Agents you dispatch do not** — hand them `profile.md` + the Status block's
  pointers + the specific artifact relevant to their dispatch, not "read `worklog.md`" unscoped. The entry
  log is append-only and grows every round across a long stage; a blanket read-the-whole-file instruction
  means every later dispatch in the stage pays a bigger token cost than the one before it for no benefit —
  the Status block exists specifically so that doesn't happen. Full history is for you (routing) and for
  debugging a stalled loop, not a default per-agent read.
- **`retro.md`** — the **stage's retrospective board**, append-only, one short entry per agent dispatch (2-3
  bullets: what went well, what went wrong or was confusing, anything it had to guess at or work around) plus
  your own orchestrator-level findings (see Step 8/`test`'s Step 5). This is cheap — it's each agent's own
  postmortem on its own step, not a new review pass — and it's what turns "how did this stage go" from a
  question nobody can answer into one you read a file for. Create it empty at Step 0 alongside `worklog.md`.
  **When the human asks for a stage retrospective at any point**, read the whole of `retro.md` and summarize
  it grouped by theme (not a raw dump of every entry) — this file is small by construction (a few bullets per
  dispatch, not a growing transcript), so reading it in full for this purpose is fine; it's `worklog.md`'s
  entry log that needs scoping, not this one. **Hand its path to every agent you dispatch**, alongside
  `profile.md` and the Status block, so each one can append its own bullets on return — every agent
  definition in this plugin already expects it conditionally ("if the orchestrator gave you that path").
- **Detail artifacts** (each authored by the agent that produced it, linked from the worklog): `plan.md`
  (developer), `diff.patch` / diff range, `review-N.md` (reviewer), `item-<id>.md` (per parallel work item).

Durable records (Execution Log) still go in the repo's stage file — you build it from the worklog at the end.

## Conductor discipline (you route; you do not research)

You read **`worklog.md` + `profile.md` + each agent's short return** and *route* on that. You do **not** read
source files to understand the code, and you do **not** re-run project-profile discovery — if you need to
know something about the code, dispatch an agent to find out. You do **not** author plans, reviews, reports,
or Execution-Log prose — the agents write their own records. The only writing/running you do is thin
mechanical bookkeeping and infra: scaffold the `worklog.md` header and an empty `retro.md`, generate a diff
(`git diff`), set up/tear down worktrees for parallel work, and consolidate the final Execution Log from the
agents' worklog entries. If you catch yourself opening a source file to figure out what's going on, stop —
that's an agent's job.

## Step 0 — Orient & load the approved target

Ensure `profile.md` exists in the working dir: if `stage-prep` seeded it, reuse it; if not, dispatch a cheap
agent (developer, `haiku`/`sonnet`) to produce it — **you don't do discovery yourself**. Scaffold
`worklog.md` with the stage header and Status block, and an empty `retro.md`. Then read the **approved stage
target** from the tracker (the worklog links it). Everything you build is measured against this. If there's
no approved stage, stop and point the human to `engineering:stage-prep`.

## Branching discipline (applies to every step below)

**`master`/`main` is never edited directly — no exceptions.** This repo uses three branch kinds:

| Branch | Cut from | Merges into | Used for |
|---|---|---|---|
| `release/<stage>` | `master` | `master` (at deploy) | The whole stage's work. One per stage; `stage-prep` cuts it, or you cut it defensively here if it's missing. |
| `feature/<description>` | `release/<stage>` | `release/<stage>` | **Every** unit of implement work in an active stage — a single feature, *and* bug fixes found during that stage's own test loop (a bug in `release/<stage>` is still a `feature/` branch, not a `hotfix/` — it hasn't shipped yet). |
| `hotfix/<description>` | `master` | `master` | A bug in code that's **already on `master`/deployed**, found outside any active stage (e.g. a direct bug report against production, with no `release/<stage>` in play). |

**Before Step 1:** confirm `release/<stage>` exists and is checked out (create it off up-to-date `master` if
`stage-prep` didn't). If you were dispatched to fix a bug in already-shipped code with no active stage — a
hotfix — skip the `release/<stage>` machinery entirely: branch `hotfix/<description>` off `master`, and treat
that as this run's working branch throughout.

**For every developer dispatch** (trivial tier, the serial loop, and each parallel work item alike): create
`feature/<description>` off the current working branch (`release/<stage>`, or `master` for a hotfix) *before*
dispatching the developer, and have the developer work on it. When the reviewer returns **APPROVE** or
**APPROVE-WITH-NITS**, merge the feature branch back (fast-forward if possible, otherwise a merge commit) and
delete it. Don't batch multiple unrelated units of work onto one feature branch. Note the branch name in the
worklog entry for that unit of work.

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

Dispatch **`engineering:developer`** (model: `sonnet`), handing it `profile.md` + the `worklog.md` Status
block (this is the stage's first dispatch, so the block is still small — same scoped-handoff convention as
every later round), to write a short self-contained plan to `plan.md`: files to change, what to reuse (with
paths), how to verify,
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

Repeat until the reviewer approves (typically 1–2 rounds). Every dispatch gets `profile.md` + the current
Status-block pointers from `worklog.md` + the one specific artifact this round needs — not an instruction to
read the whole worklog — so the agent reads exactly its shared context instead of re-deriving it or paying to
reread every prior round:
1. Dispatch **`engineering:developer`** (`sonnet`) to implement the current plan / address the latest review,
   pointing it at `plan.md` (first round) or `review-N.md` (fix round). It writes its own `worklog.md` entry
   and returns `DONE` / `DONE_WITH_CONCERNS` / `BLOCKED`.
2. Generate the diff (against the pre-change baseline) into the working dir — this is your bookkeeping.
3. Dispatch **`engineering:reviewer`** (model: `opus` — judgment) with the diff + `plan.md` path. It writes
   `review-N.md` and a worklog entry itself, and returns a verdict: **APPROVE** / **APPROVE-WITH-NITS** /
   **CHANGES-NEEDED**.
4. **APPROVE** or **APPROVE-WITH-NITS** → exit the loop (nits are the dev's discretion). **CHANGES-NEEDED** →
   point the developer at `review-N.md` (by path) and loop.
5. After each round, **update the Status block** in `worklog.md` to the new current artifact (`review-N.md`,
   then the next round's pointer) so the next dispatch — in this loop or a later one — reads the small block,
   not the growing log beneath it.

**Shared-checkout hygiene.** Require a **git worktree** for any dispatch that touches git state (branch,
commit, checkout, merge) while another agent may be active in the same checkout — not just the parallel
tier. Re-check `git status` immediately before committing so you never sweep in another agent's files.

**Keep status docs in sync as things happen, not at the docs batch.** When a run actually happens (tests,
migration, deploy step), update the worklog Status and any stage-file "not run"/"pending" claims right then.
When a fix round edits **test assertions**, re-verify against a live environment — an edited assertion
that was never run proves nothing.

Keep the reviewer's anti-over-engineering mandate in force: you want *correct and shippable for this
product*, not gold-plated.

## Step 4a — Parallel developers (large + splittable tier only)

When Step 1 selected the large tier and the developer's plan gave a work-item breakdown with **disjoint file
sets**:
1. **Isolate each item.** For each work item, create a worktree on its own `feature/<id>-<description>`
   branch cut from `release/<stage>`, so parallel developers don't collide in one working tree:
   `git worktree add ../.worktrees/<stage>-<id> -b feature/<id>-<description> release/<stage>`. (This is
   your infra bookkeeping — same `feature/` naming and `release/<stage>` base as the serial-tier rule above,
   just isolated into worktrees because they run concurrently.)
2. **Dispatch developers concurrently** — one message, multiple `engineering:developer` (`sonnet`) calls,
   each handed `profile.md`, the `worklog.md` Status block + its own work item's artifact pointer (not the
   full worklog), and **its own worktree path**. To avoid corrupting the shared board, each parallel developer
   writes its record to its **own `item-<id>.md`**, not `worklog.md`.
3. **Consolidate.** After they all return, append their per-item outcomes into `worklog.md` (mark each work
   item `done`), merge each `feature/<id>-<description>` branch back into `release/<stage>` to reconcile them
   into a single integrated change, then remove the worktrees (`git worktree remove …`) and delete the merged
   feature branches.
4. **One integration review.** Generate the combined diff and run a **single** `engineering:reviewer`
   (`opus`) pass over the integrated result (Step 4, from step 3). Any `CHANGES-NEEDED` findings route back to
   the relevant developer — serially, on the integrated tree, unless the fixes are again cleanly disjoint.

## Step 5 — Escalate to the architect (NOT the human) when the loop stalls

If the loop **hasn't converged after ~2 rounds**, or the developer returns `BLOCKED`:
- Dispatch **`engineering:architect`** (`opus`, Mode B) with `profile.md`, the `worklog.md` Status block, and
  a concise brief: the disagreement or blocker, the developer's lean, the reviewer's finding. Not the full
  worklog history — the brief you write *is* the relevant context; the architect doesn't need to rediscover
  it. The architect records its decision in the worklog and returns it; feed it back and resume the loop from
  Step 4.
- The human is **not** pulled in just because the loop is slow — the architect resolves ordinary
  disagreements and blockers.

**If the developer returns `NEEDS_ARCHITECT`** (stuck: 2 tries or ~5 min on one problem — developer §3a),
run the consult **immediately**; don't ask the human first and don't tell the developer to try again.
- Dispatch **`engineering:architect`** (`opus`, **Mode C**) with the developer's exact commands/errors and
  its **verified vs. assumed** split, verbatim. Do not summarize the errors — the raw output is the
  evidence, and your summary is where the useful detail dies.
- **The architect advises; it does not act.** Take its diagnosis back to the *developer* to implement. Do
  not let the architect write the fix, and do not implement it yourself — that silently makes you the
  developer and skips review.
- Then resume the loop from Step 4. A consult is cheap and expected; it is not a failure and does not count
  against the round budget.
- If the consult's guidance also fails, that's GATE C (Step 6) — a human decision, not a third try.

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
- Confirm `release/<stage>` is fully up to date (every `feature/`/`hotfix/` branch for this run merged in and
  deleted) before handing off — `test` and `deploy` build on this branch next.
- **Update the `worklog.md` Status block** to reflect the phase closing (e.g. "implement complete, handing
  off to test") so `engineering:test`'s first dispatch reads a current pointer, not a stale one from mid-loop.
- Tell the human the build is review-clean and the next phase is **`engineering:test`**. Do not test or
  deploy from this skill.

## Step 8 — Self-check: what would make this phase run smoother?

Before handing off, take a quick pass over how this run of implement actually went — how many review rounds
it took, whether the architect had to step in, whether a developer returned `BLOCKED` or guessed instead of
reading `profile.md`/`worklog.md`, whether the triage tier (Step 1) was judged right, any branching missteps.
This is a cheap check, not an audit — a few bullet points, or "ran clean, nothing to flag" if it did.
**Append these bullets to `retro.md`** (role: orchestrator) — don't just surface them in your handoff message
and let them evaporate; this is what makes a later "how did this stage go" answerable from a file instead of
re-derived from memory.

If something real surfaces, propose a **concrete fix** — usually a specific edit to this skill's or an
agent's instructions in this plugin (e.g. "the developer needed 3 rounds because `plan.md` didn't call out a
deviation the reviewer then caught — tighten Step 2's guidance" or "the trivial-tier bar let something too
big through — sharpen Step 1's examples"). Present the finding + proposed fix to the human; **don't edit the
plugin files yourself** — that's a change to the SDLC machinery itself, the human's call.

## Model tiering (token discipline)

Judgment → `opus` (architect, reviewer). Mechanical build → `sonnet` (developer). Trivial checks → `haiku`.
Batch reviews into one report per pass; hand artifacts by path; never let the loop run uncapped.
