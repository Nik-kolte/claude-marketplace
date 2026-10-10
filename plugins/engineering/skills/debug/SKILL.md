---
name: debug
description: Answer debugging and verification questions from the app's Axiom logs using the read-only debug agent - failures in a time window, what a given user ran into, what happened to one request or support reference, service health per environment (staging vs. production), whether a route is failing or slow, and whether a deploy changed error rates. Use when the user asks about errors, failures, outages, slowness, a user's problem, a request id, or "is prod healthy". Not part of the stage flow; usable any time.
---

# Debug: ask the logs

You hand the question to the **`debug` agent** and relay its answer. The agent is read-only: it queries Axiom
with a query-only token and reads code and docs. It never changes anything.

## Step 1: Shape the question (no queries yet)

Make sure the question has these four things. Fill gaps from the conversation; ask the user only if a gap would
change the answer (usually it won't, because the defaults are sensible):

| Slot | Default | Examples |
|---|---|---|
| **Environment** | production | "prod", "staging", "both" |
| **Window** | last 24 h | "today", "yesterday", "day before yesterday", "between 2 pm and 4 pm on the 8th" |
| **Subject** | everyone | a username, a request id / Reference, a route or feature, a commit |
| **Kind** | failures | failures · one user · one request · health · one feature · deploy check |

Keep the user's own words for dates ("day before yesterday"); the agent converts them in the users' time zone.

## Step 2: Dispatch

Spawn `engineering:debug` (foreground; you need its answer) with:
- the question in one line, plus the four slots;
- the workspace root, so it can find the repo's `axiom-debug.md` profile and the backlog;
- anything relevant you already know (a request id from an error toast, the commit just deployed).

One agent per question. If the user asks two unrelated questions, send both in one brief rather than spawning two.

## Step 3: Relay

Give the user the agent's report as is: answer first, one table, details, scope. Don't re-run its queries. If it
says a token is missing, pass on the runbook step it named. If it found a **new** failure, offer to add it to the
backlog. Don't add it without the user's yes.

## The six question types (what users can ask)

| Ask | Playbook | You get |
|---|---|---|
| "What failed in the last day / this morning?" | P1 Failures | Failure groups by route and error, users affected, latest request id, each marked test / known / expected / **new** |
| "What did `<username>` run into today?" | P2 One user | Their routes with error and rejection counts, then a timeline of what went wrong |
| "What happened to request / Reference `<id>`?" | P3 One request | Every line of that request and its child calls, plus the code at the failing spot |
| "How healthy was prod yesterday?" / "staging vs. prod" | P4 Health | Requests, 5xx %, p50/p95, slowest routes, trend; one column per environment |
| "Is `<feature>` failing / slow?" | P5 One feature | P4 and P1 narrowed to that feature's routes, with "since when" |
| "Did the last deploy break anything?" | P6 Deploy check | Old vs. new commit: error rate, p95, and error groups that only exist on the new one |

## Self-check

- The answer names its dataset(s), window (local time) and what was excluded.
- Nothing in the reply is a token or a field the profile forbids.
- No files, data or settings were changed.
