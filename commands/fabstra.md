---
description: Run the FabStra flow - Fable 5.2 always orchestrates and never codes; Opus 5.5 orchestrates at 2+ independent tasks or an excluded category, else leads (Lead mode); Sonnet 5.5 / Haiku 5.5 lead and build or delegate by tier. The gate seat (GPT-6 Astra or GPT-6.1 Sol, per the skill's gate seat rubric) gates the plan and reviews; a fresh Fable reviews Codex-built work; lanes B, D as the skill says
argument-hint: "<brief> [xhigh|high|medium] [fast]"
---

The brief: $ARGUMENTS

Read this plugin's fabstra skill (`skills/fabstra/SKILL.md`) and follow it
end to end with the brief above. FabStra: the session model is the lead. In
Orchestrate mode (Fable 5.2 always; Opus 5.5 at 2+ independent tasks or an
excluded category) you plan, write the blueprints, route, and arbitrate, and never
write code; in Lead mode (Opus 5.5 below that threshold, Sonnet 5.5, Haiku
5.5) you plan, build or delegate by tier, and arbitrate.
What that threshold counts: Independent tasks edit disjoint files and neither needs the other's result before its spec can be written. Tasks that edit the same files, or a chain where a step cannot be specced until the previous step lands, count as one task toward the threshold. A run-time dependency alone does not merge tasks - a contract task and the tasks that build against its stated interface, or an API and the client that calls it, stay separate and run in later waves (fanout.md). In doubt, count them as separate.
The gate seat - GPT-6 Astra for an excluded category, an architecture or
data-model decision, or a plan whose check you cannot state; GPT-6.1 Sol for
every other real build (the skill's gate seat rubric; naming a seat pins it) -
critiques the plan and blueprints before any builder launches (Phase 1b),
owns the Codex side as the parent thread that spawns Sol / Terra / Luna /
Spark for routed tasks, and adversarially reviews Claude-built work; a fresh
Fable context reviews Codex-built work; Sol at the same effort reviews when
Astra is spent on every login. The lead (the session model, in either mode) decides every disagreement and logs why.
Claude build seats are Opus 5.5 and pin their effort by tier; Reviewer C is a fresh Fable 5.2 (the skill's Claude seat efforts).
Effort for Astra and Sol follows the skill's effort rubric unless the brief
names one (an `xhigh`, `high`, or `medium` word in the brief pins every
Astra and Sol call the orchestrator issues in this run; Codex children Astra
spawns keep their agent-file efforts). A "sonnet max" phrase is not an
effort word: it pins only the Claude Sonnet seat (`model-router:sonnet-max`,
the skill's routing rubric); Astra and Sol effort still follows the rubric
unless an effort word pins it. A `fast` word beside Astra is the
skill's fast pin: Codex Fast mode on the `.codex-pro` native launches only
(`codex-fast on` / `off`), 2.5x usage, no effect on reviews or Lane B.
Every Claude session model runs: Fable 5.2 takes Orchestrate mode; Opus 5.5 takes Orchestrate mode at 2+ independent tasks (defined above) or an excluded category, else Lead mode; Sonnet 5.5 and Haiku 5.5 take Lead mode (references/lead-mode.md); a newer or other Claude model takes its family's row in the skill's session switch. Never stop a Claude session or ask it to switch model.
A routed proxy session is accepted as the skill's Session check allows
(references/phases.md): Lane D for a proxy model the user wants to LEAD the
run (`gpt-6-astra`, or another proxy alias the user names). A non-Claude
session model outside that Lane D case stops and asks the user
to switch with `/model claude-opus-5-5`. If the brief names Astra as the builder ("astra solo",
"let Astra design and build") or asks for a count of Astras ("spawn 3 astra
subagents" = Lane B fan-out, N solo Astras on disjoint slices), run the skill's Lane B: Fable writes a brief,
Astra designs and builds through the proxy, Sol at xhigh and a fresh Fable both review, and the lead rules on every finding.
Lane C (OpenRouter budget crew: DeepSeek builds, GLM reviews/leads) retired 2026-11-15; archive/2026-11-15-lane-c/. A budget ask (`/fabstra budget`, "use the budget crew", "run this on OpenRouter") runs Lane A, and the report says the budget crew is retired. Astra AND Sol both cooling down on every login: the Claude builders keep building, and the review seat and the Phase 1b design gate take a fresh Fable (the skill's Reviewer fallback).
