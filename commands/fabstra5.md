---
description: Run the FabStra flow on Fable 5 (claude-fable-5; the Fable 5.1 flow is /fabstra) - Fable 5 plans and never codes, GPT-6 Astra design-reviews the plan before build and adversarially reviews Claude-built work, Opus 5 / Sonnet 5 / Haiku build via the Agent tool, Astra runs the Codex side spawning GPT-5.6 Sol / Terra / Luna; Sol at the same effort is the reviewer when Astra's quota is spent, a fresh Fable context reviews Codex-built work; Lane B "astra solo" = Astra designs and builds from a Fable brief, Sol and a fresh Fable both review, three must agree
argument-hint: "<brief> [xhigh|high|medium] [fast]"
---

The brief: $ARGUMENTS

Read this plugin's fabstra5 skill (`skills/fabstra5/SKILL.md`) and follow it
end to end with the brief above. FabStra: you (Fable 5, the session model)
plan, write the blueprints, route, and arbitrate, and never write code. GPT-6
Astra critiques the plan and blueprints before any builder launches (Phase
1b), owns the Codex side as the parent thread that spawns Sol / Terra / Luna
for routed tasks, and adversarially reviews Claude-built work; a fresh Fable
context reviews Codex-built work; Sol at the same effort reviews when
Astra is spent on all three logins. Fable decides every disagreement and logs why.
Effort for Astra and Sol follows the skill's effort rubric unless the brief
names one (an `xhigh`, `high`, or `medium` word in the brief pins every
Astra and Sol call the orchestrator issues in this run; Codex children Astra
spawns keep their agent-file efforts). A `fast` word beside Astra is the
skill's fast pin: Codex Fast mode on the `.codex-biz` native launches only
(`codex-fast on` / `off`), 2.5x usage, no effect on reviews or Lane B.
If this session is not Fable 5, stop and ask the user
to switch with `/model claude-fable-5[1m]`, or to use `fable5-mode`
in-session instead - EXCEPT a session already routed to
`glm-5.3-flash` (the `budget` shim's default), or `deepseek-v4-pro` for a
`pro` run, via `scripts\session.ps1`, which is accepted for Lane C only
(below); or a session on `gpt-6-astra` or `glm-5.3-flash` that the user
wants to LEAD the run, which is accepted for Lane D (below); everything
else still stops, INCLUDING a session on
`deepseek-v4.1-flash` - that alias is a builder and reviewer seat, never a
lead (0/5, see the skill's Lane D). If the brief names Astra as the builder ("astra solo",
"let Astra design and build") or asks for a count of Astras ("spawn 3 astra
subagents" = Lane B fan-out, N solo Astras on disjoint slices), run the skill's Lane B: Fable writes a brief,
Astra designs and builds through the proxy, Sol at xhigh and a fresh Fable both review, and the three must agree.
An explicit ask for the cheap crew in the brief (`/fabstra5 budget`, "use the budget crew", "run this on OpenRouter"; a mere mention of a model or of budgets is not an ask), or a session already routed to `glm-5.3-flash` (the `budget` shim's default) or `deepseek-v4-pro` for a `pro` run, runs the skill's full Lane C: a cheap OpenRouter crew through the proxy - `deepseek-v4.1-flash` builds every coding task (mandatory empty-200 retry, `glm-5.3-flash` fallback), `glm-5.3-flash` is Reviewer A, `deepseek-v4-pro` is Reviewer B on multi-file work, and `deepseek-v4-flash` takes the design gate and mechanic - excluded for money, auth, PII, permissions, migration, concurrency, or a client-facing release. Astra AND Sol both cooling down on every login does NOT by itself pull in Lane C: the Claude builders keep building, and only the review seat and the Phase 1b design gate swap to Lane C (Reviewer A on `glm-5.3-flash`, the design gate on `deepseek-v4-flash`).
