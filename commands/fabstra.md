---
description: Run the FabStra flow - Fable 5.1 always orchestrates and never codes; Opus 5.5 orchestrates at 2+ tasks or an excluded category, else leads (Lead mode); Sonnet 5.5 / Haiku 4.5 lead and build or delegate by tier. GPT-6 Astra gates the plan and reviews; a fresh Fable reviews Codex-built work; lanes B, C, D as the skill says
argument-hint: "<brief> [xhigh|high|medium] [fast]"
---

The brief: $ARGUMENTS

Read this plugin's fabstra skill (`skills/fabstra/SKILL.md`) and follow it
end to end with the brief above. FabStra: the session model is the lead. In
Orchestrate mode (Fable 5.1 always; Opus 5.5 at 2+ tasks or an excluded
category) you plan, write the blueprints, route, and arbitrate, and never
write code; in Lead mode (Opus 5.5 below that threshold, Sonnet 5.5, Haiku
4.5) you plan, build or delegate by tier, and arbitrate. GPT-6
Astra critiques the plan and blueprints before any builder launches (Phase
1b), owns the Codex side as the parent thread that spawns Sol / Terra / Luna
for routed tasks, and adversarially reviews Claude-built work; a fresh Fable
context reviews Codex-built work; Sol at the same effort reviews when
Astra is spent on every login. The lead (the session model, in either mode) decides every disagreement and logs why.
Effort for Astra and Sol follows the skill's effort rubric unless the brief
names one (an `xhigh`, `high`, or `medium` word in the brief pins every
Astra and Sol call the orchestrator issues in this run; Codex children Astra
spawns keep their agent-file efforts). A "sonnet max" phrase is not an
effort word: it pins only the Claude Sonnet seat (`model-router:sonnet-max`,
the skill's routing rubric); Astra and Sol effort still follows the rubric
unless an effort word pins it. A `fast` word beside Astra is the
skill's fast pin: Codex Fast mode on the `.codex-pro` native launches only
(`codex-fast on` / `off`), 2.5x usage, no effect on reviews or Lane B.
Every Claude session model runs: Fable 5.1 takes Orchestrate mode; Opus 5.5 takes Orchestrate mode at 2+ tasks or an excluded category, else Lead mode; Sonnet 5.5 and Haiku 4.5 take Lead mode (references/lead-mode.md); a newer or other Claude model takes its family's row in the skill's session switch. Never stop a Claude session or ask it to switch model.
A routed proxy session is accepted as the skill's Session check allows
(references/phases.md): Lane C for a session already routed to an OpenRouter
lane alias via `scripts\session.ps1` (`glm-5.3-flash`, the `budget` shim's
default, or `deepseek-v4-pro` for a `pro` run), Lane D for any proxy model
the user wants to LEAD the run - never `deepseek-v4.1-flash`, a builder and
reviewer seat only (0/5 as a lead, see the skill's Lane D). A non-Claude
session model outside those Lane C and Lane D cases stops and asks the user
to switch with `/model claude-opus-5-5`. If the brief names Astra as the builder ("astra solo",
"let Astra design and build") or asks for a count of Astras ("spawn 3 astra
subagents" = Lane B fan-out, N solo Astras on disjoint slices), run the skill's Lane B: Fable writes a brief,
Astra designs and builds through the proxy, Sol at xhigh and a fresh Fable both review, and the lead rules on every finding.
An explicit ask for the cheap crew in the brief (`/fabstra budget`, "use the budget crew", "run this on OpenRouter"; a mere mention of a model or of budgets is not an ask), or a session already routed to `glm-5.3-flash` (the `budget` shim's default) or `deepseek-v4-pro` for a `pro` run, runs the skill's full Lane C: a cheap OpenRouter crew through the proxy - `deepseek-v4.1-flash` builds every coding task (mandatory empty-200 retry, `glm-5.3-flash` fallback), `glm-5.3-flash` is Reviewer A, `deepseek-v4-pro` is Reviewer B on multi-file work, and `deepseek-v4-flash` takes the design gate and mechanic - excluded for money, auth, PII, permissions, migration, concurrency, or a client-facing release. Astra AND Sol both cooling down on every login does NOT by itself pull in Lane C: the Claude builders keep building, and only the review seat and the Phase 1b design gate swap to Lane C (Reviewer A on `glm-5.3-flash`, the design gate on `deepseek-v4-flash`).
