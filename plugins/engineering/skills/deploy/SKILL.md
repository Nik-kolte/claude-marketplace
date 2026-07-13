---
name: deploy
description: Ship a tested stage using the devops agent, gated on the human's sign-off before anything deploys, then run post-deploy regression and report back. Handles the local build/migrate/health chain now; cloud deploy (e.g. Vercel/Neon) is a marked TBD until resources are provisioned. Fourth phase of the engineering SDLC. Use after test has passed and the human has signed off.
---

# Deploy — ship it, with a sign-off gate

You run the **release phase**. Nothing deploys without the human's explicit go, and nothing is called
"deployed" without a health check that proves it. You conduct; the devops agent does the work.

## Step 0 — Orient

Reuse the stage's **`profile.md`** and **`worklog.md`** from the working dir (the run/build/migrate/deploy
chain, container/db setup, env files, and deploy config are already captured there); the devops agent reads
that shared context rather than re-discovering it. Confirm the stage passed testing and the human signed off
(per `engineering:test`). If not, stop.

## Step 1 — GATE E: human signs off before deploy

Present exactly what will happen and where (target environment, migrations to run, the deploy command).
**Do not proceed until the human approves.** For a cloud target, first confirm the resources actually
exist — see Step 3.

**Production is a hard rule, no exceptions:** every deploy to production needs its own explicit human
approval at the time it happens — a prior approval (of the stage, of a preview deploy of the same code, of
testing in general) never carries over. **Preview/staging deploys are different** — testing and QA against
a preview environment is standing-approved as part of the normal test/regression flow and doesn't need a
fresh ask each time. Only the production gate is absolute.

**Branching:** the stage's work lives on `release/<stage>` (see `engineering:implement`'s branching
discipline — `master`/`main` is never edited directly). Preview/staging deploys can run directly off
`release/<stage>`, no merge needed. **Production deploys are what promote the branch**: only once the human
approves at this gate, merge `release/<stage>` into `master` (fast-forward if possible, otherwise a merge
commit) — then deploy `master`, not the release branch. That merge *is* the release.

## Step 2 — Local release chain (available today)

Dispatch **`engineering:devops`** (model: `sonnet`), handing it the `profile.md` + `worklog.md` paths, to:
- bring up local dependencies (e.g. the DB container) on the repo's configured port,
- run migrations + seed with the repo's own commands,
- build, start, and **verify health** (hit the health endpoint; expect a real dependency check, not just a
  served page).
Report the exact commands and the actual health response.

## Step 3 — Cloud deploy (TBD until provisioned — do not fake it)

Cloud deploy is real **only once the resources are provisioned and credentials exist**. If they are not:
- Have devops record the *intended* procedure as a clearly-marked **TBD** in the docs, and stop there for
  the cloud target. Do not run deploy commands against infra that doesn't exist, and never invent
  credentials/URLs/project IDs.
- When the human confirms cloud resources exist, proceed: set platform env vars, run the production
  migration, deploy, and verify the **deployed** health endpoint.
- **devops already knows the Vercel/Neon-class platform mechanics** (marketplace terms-acceptance gates,
  the Hobby-plan private-org-repo git-connect ceiling, CLI-deploy-without-git-linkage as a fallback,
  deployment-protection vs. application-routing when a health check doesn't return 200) — see its own
  "Cloud deployment" section. Let it drive; don't re-derive these from scratch, and route any
  plan-tier/cost tradeoff it surfaces (e.g. "needs Pro to connect this repo") to the human via Step 1's
  gate rather than deciding it yourself.

## Step 4 — Post-deploy regression

Once something is actually deployed (local or cloud), invoke **`engineering:regression`** against that
environment to confirm the verified-conditions checklist still holds. **Report the result to the human** —
green, or exactly what regressed.

## Step 5 — Record

Update the stage's Execution Log with what was deployed, where, the health/regression results, whether
`release/<stage>` was merged to `master` (and if so, that `master` is what's now live), and any remaining
TBDs (e.g. "cloud deploy pending Neon provisioning"). Then the stage is operational — hand back to the human
to decide the next stage (`engineering:stage-prep`).

## Step 6 — Self-check: what would make this phase run smoother?

Before handing off, take a quick pass over how this run of deploy actually went — did the human have to
push back on what was presented at GATE E, did devops hit a platform gotcha that should be baked into its
instructions, did the release→master merge or the health check surface anything unexpected. This is a cheap
check, not an audit — a few bullet points, or "ran clean, nothing to flag" if it did.

If something real surfaces, propose a **concrete fix** — usually a specific edit to this skill's or the
devops agent's instructions in this plugin (e.g. "devops re-discovered the Hobby-plan git-connect ceiling
again — it's already documented, so the profile.md reuse rule wasn't followed" or "GATE E's presentation
missed the migration step, so the human had to ask"). Present the finding + proposed fix to the human;
**don't edit the plugin files yourself** — that's a change to the SDLC machinery itself, the human's call.
