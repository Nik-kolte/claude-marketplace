---
name: test
description: Verify a built stage by running the tester agent against the real app, producing one batched severity-ranked bug report and gating on the human's sign-off. Clean → advance to deploy; bugs → human signs off the report, then it loops back into implement for fixes and re-tests. Third phase of the engineering SDLC. Use after implement is review-clean, before deploying.
---

# Test — catch everything before shipping

You run the **verification phase**. One tester exercises the real software, finds **all** the issues in one
pass, and you gate on the human before anything advances to deploy. The whole point is to catch bugs on
localhost — cheaply and completely — so they never reach a deployed environment.

## Step 0 — Orient

Project-profile discovery (how to run and exercise this app; build/lint/test commands; health endpoint; key
routes). Read the approved stage target so the tester checks against **intended behavior**, not just
crashes.

## Step 1 — Run the tester (one complete pass)

Dispatch **`engineering:tester`** (model: `sonnet`) with the stage target and the profile, instructing it
to **spot every issue in a single pass** and write ONE severity-ranked bug report to a durable path in the
repo's tracker (e.g. the stage folder), covering:
- build + lint clean,
- health endpoint returns a real dependency check,
- key APIs for this stage: status, shape, and **data correctness** (right rows/values, not just 200),
- **data integrity & tenancy isolation** (query the DB directly; confirm one tenant can't see another's
  data where applicable),
- UI flows **only if** there's real UI worth testing (recommend the Playwright upgrade in the report when
  the product reaches that point — don't stand it up prematurely).

The tester returns **PASS** or **FAIL** with the report path.

## Step 2 — GATE D: human sign-off

- **PASS (clean):** present the result; the human signs off to advance to **`engineering:deploy`**.
- **FAIL (bugs found):** present the batched bug report. **The human signs off the bug report before any fix
  work begins** — you approve each batch, then it goes to the developer. (This is deliberate: the human
  stays in control of what gets fixed and how.)

## Step 3 — Fix loop (bugs → back into implement)

For a signed-off bug batch, re-enter **`engineering:implement`** (Step 4 dev↔reviewer loop) with the bug
report as the work item — same escalation ladder (architect for stalls, human at GATE C for real design
decisions). When the fixes are review-clean, **return here and re-run the tester** (Step 1) to confirm the
batch is resolved and nothing regressed.

Repeat test → sign-off → fix → re-test until the tester returns PASS and the human signs off to proceed.

## Step 4 — Hand off

On a signed-off PASS, update the stage's Execution Log with the test outcome and tell the human the next
phase is **`engineering:deploy`**.
