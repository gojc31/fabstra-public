---
name: fabstra
description: "One build flow for every Claude session: Fable 5.2 orchestrates; Opus 5.5 orchestrates or leads by task count; Sonnet 5.5 / Haiku 5.5 lead. Sol (or Astra) gates and reviews; a fresh Fable second-reviews xhigh rows. Use for hard tasks (multi-step builds, debugging, research or audits with claims, unseen data), a 2+ file feature or fix, /fabstra, or Astra/Sol named; not one-line edits or simple lookups."
---

# FabStra - Fable + Astra build flow

## Session switch

| Session model | Mode | Read |
|---|---|---|
| Fable 5.2 | Orchestrate: plans, specs, routes, arbitrates; never codes | phases.md, specs.md |
| Opus 5.5 | Orchestrate at 2+ independent tasks or an excluded category, else Lead | phases.md + specs.md, or lead-mode.md |
| Sonnet 5.5 / Haiku 5.5 | Lead: plans, builds or delegates by tier, arbitrates | lead-mode.md |
| proxy model (`gpt-6.2-sol` or a named alias) | Lane D: leads the run | lane-d.md |

- Logbook found: phases.md "The run logbook"; leave a live one.
- **Hard rule:** Claude seats run on this login, another of JC's own Claude logins (T3 overflow, t3-code.md), or on credits, never the proxy.
- **Excluded categories**: money, auth, PII or de-identification, permissions, data migration, concurrency, a client-facing release. Never edit `~/.cli-proxy-api/*.json` in place; restart the proxy (hook-enforced).

## Rules

1. Orchestrate mode: you never write code; builders build, reviewers review, you write specs, verdicts, and the report. Lead mode: you build what the authoritative plan says, delegating sizeable independent tracks by tier.
2. Specs carry the decisions that must not drift: outcome, invariants, scope and non-goals, shared interfaces and file ownership, grounded pointers, acceptance, verification. Builders own everything inside those lines and report each decision.
3. Context budget, not read caps: read what a decision depends on, whole files included; verify landed work with targeted slices; batch searches into one call; nothing rides in context that a later turn will not use.
4. Independent tasks launch in parallel and builders run in the background; every delegation finishes before the session ends.
5. The logbook `.fabstra/RUN.md` is the source of truth; resume from it, never re-plan from memory.
6. One accountable lead. Astra and every reviewer advise. A finding is accepted by revising the plan or code, or rejected with one logged line; never silently dropped, never applied unread. Only the user overrules the lead.
7. Finding nothing wrong is a legitimate result. Never manufacture findings.

## Effort

| Effort | Sol / Astra gate or review of | Codex build |
|---|---|---|
| xhigh | excluded categories, multi-file architecture, P1 re-review, "break it" | hard tier (Sol; Astra-row parent: `sol`) |
| high (default) | standard features, integrations, refactors, most re-reviews | contract tier (`terra`) |
| medium | docs, config, copy, renames, boilerplate | mechanical tier (`spark`/`luna`) |

Floor high for user- or client-run work; a user effort word pins every Astra/Sol call, never below the excluded xhigh floor ("sonnet max" pins only its seat), logged in RUN.md. Rubric: phases.md; fast pin: quota.md.

**Gate seat (both modes):** Sol (GPT-6.2) for every real build, excluded categories included (xhigh), and when unsure; Astra for an architecture or data-model decision, a plan whose check you cannot state, "break it", or a re-review after a Sol miss on a P1 - an Astra trigger wins. Naming a seat pins it; one cooling: the other. Rubric: lead-mode.md.

**Claude seats** (credits first: transport.md): Opus 5.5 builds on `model-router:builder`, effort by tier per call - mechanical low, contract medium, hard high, excluded hard or second miss at high xhigh; Reviewer C fresh Fable 5.2 (high, excluded xhigh): fable-review.py, else `model-router:reviewer`. Rules: phases.md "Claude seat efforts"; evidence: effort-trial.md.

## Routing rubric

- **Hard** - multi-file, architecture, tricky algorithms, integrations, debugging with no sure theory.
- **Contract** - a contained, written-contract change ("sonnet max" pin: `model-router:sonnet-max`).
- **Mechanical** - exact-text or known-pattern edits, any file count.
- **Codex side** - owns well-specified hard and contract tasks once the folder passes the write probe (transport.md); the gate seat parents it: Sol, Astra on Astra rows (phases.md).
- **Design and UI** - a user-facing surface gets a Design block from `model-router:designer` (client briefs as given, client-E too; Pro consult keeps airlock).
- **Fan-out** - build waves of 3-4; size audit, review, QA, research seats first (fanout.md).

## Phases

- **1 Plan** - lane, done, tasks with tier and acceptance, real/contained/small, a go (phases.md).
- **1b Design gate** (real builds) - the gate seat reads plan, specs, repo before build (specs.md, transport.md).
- **2 Build** - one delegation per task by tier; smoke gate when all land; failed: fix by tier, re-run; review once it passes.
- **3 Review** (real; contained: one) - diff first, then the pairing-rule seat: Claude built -> gate seat; Codex built -> fresh Fable; xhigh row adds a parallel one (phases.md; crew, fallbacks: transport.md). Real builds: Neon G attacks round 1, excluded too; T3: AG first (t3-code.md).
- **4 Fix and ship** - fix proven breaks by tier, smoke gate per code round, Hydrogen fix check if no re-review; 3 review rounds max (excluded: no cap), re-reviews carry prior findings, diff-only from round 3 (phases.md). Open findings not down (pre-cap), or two rounds on one finding -> back to 1: re-diagnose, re-spec, one seat up; a third failed round -> JC. Report: short; ask JC via AskUserQuestion, no Artifact page (decision-page.md). Separate verified from assumed; say where you looked.

## Lanes

A (default): the phases above. B: "astra solo" or "astra x3", Astra designs and builds. D: a proxy model leads (default `gpt-6.2-sol`). Lane C retired 2026-11-15.

## References

Under `${CLAUDE_PLUGIN_ROOT}/skills/fabstra/references/`:

- `lead-mode.md`, `lead-mode-deltas.md` - Lead mode, before Gate 1
- `phases.md` - Orchestrate mode, before planning; `specs.md` - before a spec (small change: Builder spec contract); `fanout.md` - build planning, audits, reviews
- `t3-code.md` - at run start in T3 Code (`CLAUDE_CODE_ENTRYPOINT=t3-code`): seats, login overflow, Antigravity
- `transport.md` - before a proxy/Codex launch; `quota.md` - proxy error, or "fast"
- `lane-b.md`, `lane-d.md` - the lane named
- `surfaces.md` - browser QA, Computer Use, renders; `decision-page.md` - before any report or ask to JC
- `pro-consult.md` - research claims, xhigh plans, 2 failed fix rounds, "pro/gemini consult", Reviewer G; `advisor.md` - every run, before each Claude seat
