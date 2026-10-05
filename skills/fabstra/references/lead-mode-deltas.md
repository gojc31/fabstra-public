# Lead mode deltas - Lanes B and C, transports

Reached from: lead-mode.md - the seat rubric rows for Lane B and Lane C, and the first Codex launch, and the model notes before Gate 1

## Lead mode delta - Lane B (Astra solo)

lane-b.md is the text; on a Lead-mode session only this differs.

- You do not build in this lane: Astra designs and codes from your brief; you
  keep the gates, the user, and the report. Write the brief after Gates 1 and
  2; its nearest-pattern pointer comes from your Gate 2 reads.
- The Design block comes as in lead-mode.md, Build (in-session on Opus 5.5, else
  `model-router:designer` with a `Pass:` marker).
- Astra's REBUTTED answer in part 5(b) is its one rebuttal; you do not rebut
  on its behalf.
- Part 5(d): you take a fix yourself only when it needs something the solo
  session cannot reach (a plugin skill with `disable-model-invocation`, a
  Claude-only MCP tool); log it, and the active set re-reviews it.

## Lead mode delta - Lane C (budget crew)

lane-c.md is the text; on a Lead-mode session only this differs.

- The session model orchestrates the crew. On an Opus or Sonnet session where
  the Claude limit is not the problem you may still build the Sonnet / Haiku
  tiers through the Agent tool as usual, sending only the pieces that need it
  to the OpenRouter crew; on a routed session every seat runs on the proxy.
- The reviewer-alias overlap does not arise when an Opus or Sonnet session
  orchestrates the crew itself.
- `deepseek-v4-flash` (design gate, mechanic) drifts from the requested
  headings unless the spec restates them.

## Lead mode delta - transports

transport.md and quota.md are the text; on a Lead-mode session only this
differs.

- Resolve the companion before the first Codex launch instead of trusting
  the pinned version segment:
  `C=$(ls -d ~/.claude/plugins/cache/openai-codex/codex/*/scripts/codex-companion.mjs | sort -V | tail -1)`.
- The launch's `--model` is the model holding the gate seat on THIS build:
  `gpt-6-astra` when Astra holds it, `gpt-6.1-sol` when Sol does or Astra's
  quota is spent - never copy the Astra id into a Sol-seat run. Spec files
  are `<scratch>/fabstra-codex-<name>.md` and `<scratch>/fabstra-fix-<name>.md`;
  the job id lands in `<scratch>/codex-job-<name>.txt`.
- A Codex-column fix is its own launch: `<scratch>/fabstra-fix-<name>.md`
  (the fix delegation from lead-mode.md "After the review" plus stack
  rules, the parent-thread clause, status line) opening "Fix task. You are the parent
  thread, implement the fix it specifies, delegating by tier, and report the
  status line.", sent with `--write --prompt-file`.

## Model notes (for the model running this session)

- **Fable 5.1** - not this file's audience: run Orchestrate mode (SKILL.md,
  phases.md); you orchestrate and never write code.
- **Opus 5.5** - at or above the Orchestrate threshold you run Orchestrate mode (SKILL.md session switch): phases.md is your text and you never write code in-session. Below it: you verify unprompted: one check per claim, no verifier
  subagents. You may end a turn on a text report with work still owed: status notes go with the next tool call; keep going until the
  acceptance criteria pass. Given a time budget, pace to it. Frontend
  without a design block falls back on generic defaults: run the design row
  first and name the patterns to avoid.
- **Sonnet 5.5** - at low or medium effort you may stop to check in before
  multi-part work is done: keep going until the acceptance criteria pass;
  stop only when blocked on the user or before a risky step. You tend to add
  tests, docs or files nobody asked for: build only what the plan names,
  extras are follow-ups. At xhigh or max do not start your own review rounds
  or reviewer subagents - the plan gate and review gate are the reviews. The
  hardest long-horizon work suits an Opus model better.
- **Haiku 4.5** - you are the mechanical tier. Send a hard task to the plan
  gate at once; a short draft plan is fine, Astra's plan does the design. Do the mechanical parts exactly as specified and hand
  judgment calls to the senior seat or the user.
