# trade-reflect

The intelligent self-improvement brain for the cloud paper-trading worker
(`trade-research`, deployed on Railway).

The worker takes ICT *Asian sweep → CISD reversal* paper trades on FX majors 24/7
and logs every outcome to a Railway volume. This plugin's **`reflect`** skill is the
"researcher": it reads the recent trades and the current `strategy.yaml`, reasons
about *why* trades are failing (regime, session timing, the FVG filter, RR, sizing),
changes **exactly one** strategy variable, snapshots the prior version, logs its
hypothesis, and pushes the change back to the volume — where the live worker adopts
it on its next cycle.

## Skill

- **`reflect`** — run one reflection cycle. No-ops if fewer than `reflection_every`
  trades have closed since the last cycle. One variable per cycle; full version
  history preserved.

## Two ways to run it

- **On-demand (laptop on):** open Claude Code and invoke the `reflect` skill. You
  see and approve every change.
- **Cloud, unattended (laptop off):** the companion *cloud reflector* runs Claude
  Code headless on a Railway cron and calls this same skill on a schedule, powered
  by your Claude Pro membership via `CLAUDE_CODE_OAUTH_TOKEN`. See
  `trade-research/reflector/` in the repo.

## Why Claude Code and not a third-party agent

Claude Code is the *authorized* client for a Claude Pro membership. Running the
reflection through Claude Code (interactive or headless) uses your subscription
within terms — unlike pointing a separate agent framework at the subscription token,
which Anthropic blocks.

## Requirements

- The `trade-research` worker deployed on Railway with its state volume
  (default name `hermes-trading-volume`).
- Railway access: `railway login` (local) or `RAILWAY_TOKEN` + linked project (cloud).
