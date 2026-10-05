---
name: fabstra
description: One build flow for every Claude session. Fable 5.1 always orchestrates; Opus 5.5 orchestrates at the Orchestrate threshold, else leads; Sonnet 5.5 / Haiku 4.5 lead. Astra or Sol gates and reviews; a fresh Fable second-reviews xhigh rows. Use for every hard task: multi-step builds, debugging, research or audits with claims, unseen data; a feature or bug fix touching 2+ files; a budget-crew ask; /fabstra; Astra or Sol named; not one-line edits or simple lookups.
---

# FabStra - Fable + Astra build flow

One lead decides; builders build; Astra or Sol tries to break the plan, then the build.

## Session switch

| Session model | Mode | What the lead does | Read |
|---|---|---|---|
| Fable 5.1 | Orchestrate | plans, specs, routes, arbitrates; never codes | phases.md, specs.md |
| Opus 5.5 | Orchestrate at the Orchestrate threshold (2+ tasks or an excluded category), else Lead | as Fable; or as Lead | phases.md + specs.md, or lead-mode.md |
| Sonnet 5.5 / Haiku 4.5 | Lead | plans, builds or delegates by tier, arbitrates | lead-mode.md |
| routed proxy model (never `deepseek-v4.1-flash`) | Lane C or D | leads its lane | lane-c.md, lane-d.md |

- Unfinished `.fabstra/RUN.md`: summarize it, ask resume or fresh (rename rule: phases.md).
- **Hard rule:** Claude subagents run on the Agent tool on this login, never via the proxy. From Fable every Agent call names `model:` opus/sonnet/haiku or a self-pinning `model-router:*`/`codex:*` type.

## Crew

Crew table and fallbacks: transport.md.
Claude built -> gate seat reviews; Codex built -> fresh Fable; xhigh row adds a parallel fresh Fable (phases.md, pairing rule).

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

Floor high for anything a user or client runs; a user effort word pins every Astra/Sol call ("sonnet max" pins only the Sonnet seat); log it in RUN.md. Rubric: phases.md; fast pin: quota.md. Sol row: the table too, so high unless a row says xhigh.

**Gate seat (both modes):** Astra for an excluded category, an architecture or data-model decision, or a plan whose check you cannot state; Sol for every other real build. Naming a seat pins it; Astra spent drops to Sol (say so); unsure: Astra. Detail: lead-mode.md seat rubric.

Opus-tier builder arm: effort-trial.md (time-boxed trial).

## Routing rubric

- **Opus** - multi-file, architecture, tricky algorithms, integrations, debugging with no sure theory.
- **Sonnet** - contained changes with a written contract ("sonnet max" pin: `model-router:sonnet-max`).
- **Haiku** - lookups, commands, one-file mechanical edits (across 2+ files: `model-router:builder-low`, Opus 5.5 low).
- **Codex side** - default owner of a self-contained, well-specified Opus/Sonnet-tier task once the folder passes the Codex write probe (transport.md); the gate seat parents it by tier (phases.md).
- **Design and UI** - a user-facing surface gets its Design block from Opus 5.5 (`model-router:designer`; airlock first for client-E work).
- **Browser** - browser QA, Computer Use, renders: surfaces.md.
- **Fan-out** - builds in waves of 3-4; audit, review, QA, research seats sized first (fanout.md).

## Phases

1. **Plan** - lane, done, tasks with tier and acceptance, real/contained/small, a go (phases.md).
2. **Design gate** (real builds) - the gate seat reads plan, specs, repo before any build (specs.md, transport.md).
3. **Build** - one delegation per task by tier; smoke gate when all land.
4. **Review** (real; contained: one) - diff first, then the pairing rule's seat (transport.md).
5. **Fix and ship** - fix by tier, smoke gate per code round, two rounds per finding. Report: needs-the-user first (open decisions, approvals, user-only commands), then what shipped and how verified. Separate verified from assumed, out loud; mark the unconfirmed and where you looked; cite paths, lines, commands, numbers seen; report what you observed, not intended; never soften a real problem.

## Lanes

- **A** (default) - the phases above.
- **B** - "astra solo" or "astra x3": Astra designs and builds.
- **C** - an explicit budget ask, or an OpenRouter-routed session.
- **D** - a proxy session model leads.

## References

- `${CLAUDE_PLUGIN_ROOT}/skills/fabstra/references/lead-mode.md`, `lead-mode-deltas.md` - Lead mode, before Gate 1
- `${CLAUDE_PLUGIN_ROOT}/skills/fabstra/references/phases.md` - Orchestrate mode, before planning
- `${CLAUDE_PLUGIN_ROOT}/skills/fabstra/references/specs.md` - before any spec (small change: its Builder spec contract)
- `${CLAUDE_PLUGIN_ROOT}/skills/fabstra/references/transport.md` - before the first proxy/Codex launch
- `${CLAUDE_PLUGIN_ROOT}/skills/fabstra/references/quota.md` - on a proxy error, or "fast"
- `${CLAUDE_PLUGIN_ROOT}/skills/fabstra/references/lane-b.md`, `lane-c.md`, `lane-d.md` - the lane named
- `${CLAUDE_PLUGIN_ROOT}/skills/fabstra/references/surfaces.md` - browser, Computer Use, renders
- `${CLAUDE_PLUGIN_ROOT}/skills/fabstra/references/fanout.md` - planning a build; any audit or review seat
- `${CLAUDE_PLUGIN_ROOT}/skills/fabstra/references/effort-trial.md` - before any Opus-tier delegation
