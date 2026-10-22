---
name: fabstra
description: "One build flow for every Claude session: Fable 5.1 orchestrates; Opus 5.5 orchestrates or leads by plan size; Sonnet 5.5 / Haiku 5.5 lead. Astra or Sol gates and reviews; a fresh Fable second-reviews xhigh rows. Use for hard tasks (multi-step builds, debugging, research or audits with claims, unseen data), a 2+ file feature or fix, a budget ask, /fabstra, or Astra/Sol named; not one-line edits or simple lookups."
---

# FabStra - Fable + Astra build flow

## Session switch

| Session model | Mode | Read |
|---|---|---|
| Fable 5.1 | Orchestrate: plans, specs, routes, arbitrates; never codes | phases.md, specs.md |
| Opus 5.5 | Orchestrate at the Orchestrate threshold (2+ tasks or an excluded category), else Lead | phases.md + specs.md, or lead-mode.md |
| Sonnet 5.5 / Haiku 5.5 | Lead: plans, builds or delegates by tier, arbitrates | lead-mode.md |
| routed proxy model (never `deepseek-v4.1-flash`) | Lane C or D: leads its lane | lane-c.md, lane-d.md |

- Logbook found: phases.md "The run logbook"; leave a live one.
- **Hard rule:** Claude subagents run on the Agent tool on this login, never the proxy.
- **Excluded categories**: money, auth, PII or de-identification, permissions, data migration, concurrency, a client-facing release. OpenRouter seats (Lane C glm/deepseek) never build, review, or gate them; their spec or command carries its own line `excluded: no - <reason>`, or a hook denies it. Never edit `~/.cli-proxy-api/*.json` in place; restart the proxy (a hook denies it).

## Rules

1. Orchestrate mode: you never write code; builders build, reviewers review, you write specs, verdicts, and the report. Lead mode: you build what the authoritative plan says, delegating sizeable independent tracks by tier.
2. Specs carry the decisions that must not drift: outcome, invariants, scope and non-goals, shared interfaces and file ownership, grounded pointers, acceptance, verification. Builders own everything inside those lines and report each decision.
3. Context budget, not read caps: read what a decision depends on, whole files included; verify landed work with targeted slices; batch searches into one call; nothing rides in context that a later turn will not use.
4. Independent tasks launch in parallel and builders run in the background; every delegation finishes before the session ends.
5. The logbook `.fabstra/RUN.md` is the source of truth; resume from it, never re-plan from memory.
6. One accountable lead. Astra and every reviewer advise. A finding is accepted by revising the plan or code, or rejected with one logged line; never silently dropped, never applied unread. Only the user overrules the lead.
7. Finding nothing wrong is a legitimate result. Never manufacture findings.

## Effort

| Effort | Astra / Sol gate or review of | Codex build |
|---|---|---|
| xhigh | excluded categories, multi-file architecture, re-review after a P1, "break it" | Opus tier (`sol`) |
| high (default) | standard features, integrations, refactors, most re-reviews | Sonnet tier (`terra`) |
| medium | docs, config, copy, renames, boilerplate | Haiku tier (`spark`/`luna`) |

Floor high for user- or client-run work; a user effort word pins every Astra/Sol call ("sonnet max" pins only the Sonnet seat), logged in RUN.md. Rubric: phases.md; fast pin: quota.md.

**Gate seat (both modes):** Astra for an excluded category, an architecture or data-model decision, or a plan whose check you cannot state; Sol for every other real build. Naming a seat pins it; Astra spent drops to Sol; unsure: Astra. Rubric: lead-mode.md.

After 2026-10-08, Opus-tier builds take `model-router:builder` (xhigh); readout owed (effort-trial.md).

## Routing rubric

- **Opus** - multi-file, architecture, tricky algorithms, integrations, debugging with no sure theory.
- **Sonnet** - contained changes with a written contract ("sonnet max" pin: `model-router:sonnet-max`).
- **Haiku** - lookups, commands, one-file mechanical edits (2+ files: `model-router:builder-low`).
- **Codex side** - owns self-contained, well-specified Opus/Sonnet-tier tasks once the folder passes the write probe (transport.md); the gate seat parents it (phases.md).
- **Design and UI** - a user-facing surface gets a Design block from `model-router:designer` (airlock first for client-E work).
- **Fan-out** - build waves of 3-4; size audit, review, QA, research seats first (fanout.md).

## Phases

- **1 Plan** - lane, done, tasks with tier and acceptance, real/contained/small, a go (phases.md).
- **1b Design gate** (real builds) - the gate seat reads plan, specs, repo before build (specs.md, transport.md).
- **2 Build** - one delegation per task by tier; smoke gate when all land. Smoke gate fails -> fix by tier, re-run; no review until it passes.
- **3 Review** (real; contained: one) - diff first, then the pairing-rule seat: Claude built -> gate seat; Codex built -> fresh Fable; xhigh row adds a parallel fresh Fable (phases.md; crew, fallbacks: transport.md).
- **4 Fix and ship** - fix by tier, smoke gate per code round; re-reviews carry prior findings, diff-only from round 3 (phases.md). Open findings not down after a round, or two rounds on one finding -> back to 1: re-diagnose, re-spec, escalate a tier. Report: the short report, plus a decision page when JC must choose (decision-page.md). Separate verified from assumed, out loud; mark the unconfirmed and where you looked.

## Lanes

A (default): the phases above. B: "astra solo" or "astra x3", Astra designs and builds. C: an explicit budget ask, or an OpenRouter-routed session. D: a proxy session model leads.

## References

- `${CLAUDE_PLUGIN_ROOT}/skills/fabstra/references/lead-mode.md`, `lead-mode-deltas.md` - Lead mode, before Gate 1
- `${CLAUDE_PLUGIN_ROOT}/skills/fabstra/references/phases.md` - Orchestrate mode, before planning
- `${CLAUDE_PLUGIN_ROOT}/skills/fabstra/references/specs.md` - before a spec (small change: Builder spec contract)
- `${CLAUDE_PLUGIN_ROOT}/skills/fabstra/references/transport.md` - before a proxy/Codex launch
- `${CLAUDE_PLUGIN_ROOT}/skills/fabstra/references/quota.md` - proxy error, or "fast"
- `${CLAUDE_PLUGIN_ROOT}/skills/fabstra/references/lane-b.md`, `lane-c.md`, `lane-d.md` - the lane named
- `${CLAUDE_PLUGIN_ROOT}/skills/fabstra/references/surfaces.md` - browser QA, Computer Use, renders
- `${CLAUDE_PLUGIN_ROOT}/skills/fabstra/references/fanout.md` - build planning, audits, reviews
- `${CLAUDE_PLUGIN_ROOT}/skills/fabstra/references/effort-trial.md` - trial history
- `${CLAUDE_PLUGIN_ROOT}/skills/fabstra/references/pro-consult.md` - research claims, xhigh plans, 2 failed fix rounds, "pro consult"
- `${CLAUDE_PLUGIN_ROOT}/skills/fabstra/references/decision-page.md` - before any report or ask to JC
