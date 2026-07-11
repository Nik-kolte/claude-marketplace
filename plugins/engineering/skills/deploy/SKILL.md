---
name: deploy
description: Ship a tested stage using the devops agent, gated on the human's sign-off before anything deploys, then run post-deploy regression and report back. Handles the local build/migrate/health chain now; cloud deploy (e.g. Vercel/Neon) is a marked TBD until resources are provisioned. Fourth phase of the engineering SDLC. Use after test has passed and the human has signed off.
---

# Deploy — ship it, with a sign-off gate

You run the **release phase**. Nothing deploys without the human's explicit go, and nothing is called
"deployed" without a health check that proves it. You conduct; the devops agent does the work.

## Step 0 — Orient

Project-profile discovery focused on infra: the run/build/migrate/deploy chain, container/db setup, env
files, and any deploy config (`vercel.json`, CI workflows, Dockerfiles). Confirm the stage passed testing
and the human signed off (per `engineering:test`). If not, stop.

## Step 1 — GATE E: human signs off before deploy

Present exactly what will happen and where (target environment, migrations to run, the deploy command).
**Do not proceed until the human approves.** For a cloud target, first confirm the resources actually
exist — see Step 3.

## Step 2 — Local release chain (available today)

Dispatch **`engineering:devops`** (model: `sonnet`) to:
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

## Step 4 — Post-deploy regression

Once something is actually deployed (local or cloud), invoke **`engineering:regression`** against that
environment to confirm the verified-conditions checklist still holds. **Report the result to the human** —
green, or exactly what regressed.

## Step 5 — Record

Update the stage's Execution Log with what was deployed, where, the health/regression results, and any
remaining TBDs (e.g. "cloud deploy pending Neon provisioning"). Then the stage is operational — hand back to
the human to decide the next stage (`engineering:stage-prep`).
