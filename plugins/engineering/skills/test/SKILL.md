---
name: test
description: Verify a built stage by running the tester agent against the real app, producing one batched severity-ranked bug report and gating on the human's sign-off. Clean → advance to deploy; bugs → human signs off the report, then it loops back into implement for fixes and re-tests. Third phase of the engineering SDLC. Use after implement is review-clean, before deploying.
---

# Test — catch everything before shipping

You run the **verification phase**. One tester exercises the real software, finds **all** the issues in one
pass, and you gate on the human before anything advances to deploy. The whole point is to catch bugs on
localhost — cheaply and completely — so they never reach a deployed environment.

## Step 0 — Orient

Reuse the stage's **`profile.md`** and **`worklog.md`** from the `implement` working dir (e.g.
`.engineering/<stage>/`) — the app's run/exercise commands, health endpoint, and key routes are already
captured there, and the worklog records what was built. Don't re-run project-profile discovery yourself; the
tester reads that shared context. If no `profile.md` exists yet, have the tester produce one as its first
step. Read the approved stage target so the tester checks against **intended behavior**, not just crashes.

## Step 1 — Run the tester (one complete pass)

Dispatch **`engineering:tester`** (model: `sonnet`) with the `profile.md` + `worklog.md` paths and the stage
target, instructing it to **spot every issue in a single pass** and write ONE severity-ranked bug report
itself to a durable path in the working dir (e.g. `bugs-N.md`) plus a thin worklog entry, covering:
- build + lint clean,
- health endpoint returns a real dependency check,
- key APIs for this stage: status, shape, and **data correctness** (right rows/values, not just 200),
- **data integrity & tenancy isolation** (query the DB directly; confirm one tenant can't see another's
  data where applicable),
- **codify those black-box checks as committed automated tests** (per the repo's testing strategy) so they
  persist as the regression suite — plus a manual/exploratory pass for what isn't worth automating,
- UI flows **only if** there's real UI worth testing (recommend the Playwright upgrade in the report when
  the product reaches that point — don't stand it up prematurely).

The tester returns **PASS** or **FAIL** with the report path.

## Step 2 — GATE D: human sign-off

- **PASS (clean):** present the result; the human signs off to advance to **`engineering:deploy`**.
- **FAIL (bugs found):** present the batched bug report. **The human signs off the bug report before any fix
  work begins** — you approve each batch, then it goes to the developer. (This is deliberate: the human
  stays in control of what gets fixed and how.)

## Step 3 — Fix loop (bugs → back into implement)

For a signed-off bug batch, re-enter **`engineering:implement`** (Step 4 dev↔reviewer loop) with `bugs-N.md`
as the work item — the same `profile.md` + `worklog.md` carry over, so the developer resumes warm instead of
re-orienting. Same escalation ladder (architect for stalls, human at GATE C for real design decisions). When
the fixes are review-clean, **return here and re-run the tester** (Step 1) to confirm the batch is resolved
and nothing regressed.

Repeat test → sign-off → fix → re-test until the tester returns PASS and the human signs off to proceed.

## Step 4 — Hand off & grow the regression checklist

On a signed-off PASS:
- Update the stage's Execution Log with the test outcome.
- **Grow the durable regression coverage.** Preferably the stage's key conditions were already committed as
  **automated tests** (the tester's integration/e2e tests) — those *are* the regression suite. For anything
  not worth automating, append a terse runnable check to the committed `regression-checklist.md` (or a
  section of the stage tracker) — both live in the repo's committed docs/tests, **never** the ephemeral
  `.engineering/` dir. A clean PASS is exactly when you *know* the condition holds, so this is where coverage
  grows — roughly one condition per stage.
- Tell the human the next phase is **`engineering:deploy`**.

Growing coverage here (not at deploy) means `engineering:regression` later just **runs the suite** — it never
re-derives the cases, and a stage that isn't deployed still contributes its coverage.
