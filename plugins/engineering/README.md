# engineering

A **token-aware, repo-agnostic software-development lifecycle** for a solo developer. Instead of
hand-conducting each stage — write it, test it, review it, judge it, all as separate manual prompts — you run
one **phase skill** at a time. Each skill spawns the specialist agents it needs, loops them until the work is
genuinely good (not gold-plated), and **stops at control gates to bring you in** wherever the plan could
drift.

## The one idea it's built on

In Claude Code, subagents are stateless workers spawned by a main agent — they can't autonomously loop or
message each other. So here: **skills orchestrate, agents specialize, and you (the human) sit in the main
thread as a first-class control gate.** You invoke each phase yourself, so you only pay for the phase you run.
(This is also why the "team lead" is the `implement` skill itself, not an agent — only the main thread can
dispatch and sequence developers.)

## Shared context — so agents don't start cold

Each stage keeps an ephemeral working dir (`.engineering/<stage>/`, recommend gitignored) with two files
that carry context between spawns:

- **`profile.md`** — the stable project brief (stack, build/lint/test/migrate commands, health endpoint, key
  routes, the discovered scale target). Written **once** (seeded by `stage-prep`) and **read by every
  agent**, so nobody re-runs project-profile discovery.
- **`worklog.md`** — an append-only, Jira-like board. **Each agent writes its own thin entry** (outcome + a
  pointer to its detail artifact) when it finishes; detail lives in linked files (`plan.md`, `review-N.md`,
  `bugs-N.md`). The orchestrator **reads the worklog to route and never researches the code itself** — the
  agents own all reading, writing, and authoring.

## The flow

```
  stage-prep ──▶ implement ──▶ test ──▶ deploy ──▶ (regression)
   (GATE 0)     (GATE A,C)    (GATE D)  (GATE E)      ↺ grows

  ── the loops ────────────────────────────────────────────────
  implement:   developer ⇄ reviewer   ── stalls? ─▶ architect ─▶ you (GATE C)
  test:        tester ─▶ bug report ─▶ you sign off ─▶ back into implement ─▶ re-test
```

## Agents (`agents/`)

| Agent | Does | Never |
|---|---|---|
| **architect** | Brainstorms stage scope with you; guards against over-engineering; resolves dev/reviewer stalls; checks plans for deviation | Writes product code |
| **developer** | Plans then builds in the repo's idiom; unit-tests the non-trivial logic; surfaces blockers instead of guessing | Silently expands scope |
| **reviewer** | One batched, severity-ranked review; correctness + test coverage + real simplifications | Gold-plates / demands perfection |
| **tester** | Runs the real app; authors the automated integration/e2e suite; finds all bugs in one pass; one bug report | Trickles findings one at a time |
| **devops** | Local build/migrate/health chain; cloud as a marked TBD | Fakes a deploy to infra that doesn't exist |

## Skills (`skills/`) — invoke in order across a stage

1. **`engineering:stage-prep`** — decide & lock the next stage *with you*. → GATE 0 (you approve scope).
2. **`engineering:implement`** — developer ⇄ reviewer loop; architect resolves stalls. → GATE A (plan
   deviation), GATE C (real design decision). Trivial changes skip the full cycle.
3. **`engineering:test`** — tester finds everything in one pass. → GATE D (you sign off the bug report /
   advance).
4. **`engineering:deploy`** — devops ships it. → GATE E (you sign off before deploy), then regression.
5. **`engineering:regression`** — the standing smoke checklist; grows one condition per stage.

## Branching (never touch `master`/`main` directly)

| Branch | Cut from | Merges into | Used for |
|---|---|---|---|
| `release/<stage>` | `master` | `master` (at deploy, GATE E) | One per stage — everything in it lands here first. Cut by `stage-prep`. |
| `feature/<description>` | `release/<stage>` | `release/<stage>` | Every unit of `implement` work — a feature, or a bug found in that stage's own test loop. |
| `hotfix/<description>` | `master` | `master` | A bug in already-shipped `master` code, found outside any active stage. |

Full detail lives in `engineering:implement`'s branching-discipline section; `engineering:deploy` does the
`release/<stage>` → `master` merge as the production-promotion step.

## Self-check (every skill ends with one)

Each of the five phase skills ends with a quick, cheap retro: what friction showed up in *this* run
(stalls, re-derived context, wrong triage, a bug that should've been caught earlier), and — only if
something real surfaced — a concrete proposed fix to a specific agent's or skill's instructions. Findings
go to the human; **skills never edit the plugin's own files** — that's a process change, same control-gate
philosophy as everything else here.

## Control gates (you are the gate)

| Gate | Where | Fires when |
|---|---|---|
| 0 | stage-prep | Approve the stage target & scope |
| A | implement | Plan **deviates** from the approved design / adds a new decision |
| C | implement | Architect can't resolve it, the resolution deviates, or the design is changing |
| D | test | Sign off the bug report (or approve advancing if clean) |
| E | deploy | Sign off **before** deploy; then review the regression result |

**Standing rule:** anything that changes the plan you approved → you decide.

## Token discipline (baked in)

Model tiering per spawn (judgment → `opus`; build/test/ops → `sonnet`; trivial → `haiku`) · file-mediated
handoffs through the shared `profile.md` + `worklog.md` (agents read/author their own records by path;
the orchestrator only routes) · one batched report per review/test pass · loop caps that escalate to the
architect, not an endless spin · a **three-tier triage** so effort matches size: *trivial* (one dev, no
ceremony) · *substantial* (serial dev⇄reviewer loop) · *large + splittable* (developers dispatched in
**parallel** across isolated git worktrees, then reconciled and reviewed once).

## Repo-agnostic

A cheap **project-profile discovery** captures the target repo's own `CLAUDE.md`/`AGENTS.md`/`README`, the
build/test/deploy commands from the manifest, and where the repo keeps docs and any stage tracker — **once**,
into `profile.md`, which every later agent reuses. Nothing is hardcoded to one project.
