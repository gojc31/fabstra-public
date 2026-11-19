# Lead mode deltas - Lane B, transports, Gemini seats

Reached from: lead-mode.md - the seat rubric row for Lane B, the Gemini seats line under the seat rubric, the first Codex launch, and the model notes before Gate 1

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

## Lead mode delta - transports

transport.md and quota.md are the text; on a Lead-mode session only this
differs.

- Resolve the companion before the first Codex launch instead of trusting
  the pinned version segment:
  `C=$(ls -d ~/.claude/plugins/cache/openai-codex/codex/*/scripts/codex-companion.mjs | sort -V | tail -1)`.
- The launch's `--model` is the model holding the gate seat on this build:
  `gpt-6.2-sol` by default, `gpt-6.2-astra` on an Astra row; always pass
  `--effort`; never copy the Astra id into a Sol-seat run. Every hop (cooling,
  model-rejected, retry): hop rules: transport.md, Model pins. Spec files
  are `<scratch>/fabstra-codex-<name>.md` and `<scratch>/fabstra-fix-<name>.md`;
  the job id lands in `<scratch>/codex-job-<name>.txt`.
- A Codex-column fix is its own launch: `<scratch>/fabstra-fix-<name>.md`
  (the fix delegation from lead-mode.md "After the review", assembled per
  specs.md "Codex-side tasks" - the GPT-6.2 swaps and additions and the "What
  I will check:" line - plus stack rules, the parent clause of the model that
  actually runs as parent from specs.md "Codex parent clauses" (hop rules:
  transport.md, Model pins), status line) opening "Fix task. You are the parent
  thread, implement the fix it specifies, delegating by tier, and report the
  status line.", sent with `--write --prompt-file`.

## Lead mode delta - Gemini seats

pro-consult.md, "Gemini consult - the build-sheet seat", is the text; in
Lead mode the lead launches and verifies each one.

- Hydrogen quick check: small change -> on the diff after the build;
  contained change -> on its RUN.md plan before the build; advisory, never
  replaces the contained change's Sol review.
- Reviewer G (Neon, Carbon spare): every real build, in the same message as the review
  gate seat(s) of every review round (round 1 and each re-review); its rows
  are OPEN findings you confirm against the code; pro-consult.md, "Reviewer G". Round scope: phases.md "Phase 4" (rounds 1-2
  the full diff from build start, from round 3 the diff since the last reviewed
  state). The full diff: a git repo sends the diff against the
  pre-build commit plus the build's new untracked files
  (`git ls-files --others --exclude-standard`); a non-git project copies the
  plan's files to `<scratch>/fabstra-prebuild/` before the first build starts.
- Gemini report check: a research or audit run whose report makes claims
  gets one, after the draft and before the report file and the chat report;
  each item is checked against a primary source and logged in RUN.md's
  "Pro consult" section.
- Hydrogen fix check: only on a code-changing fix round that gets no
  re-review, after its smoke-gate re-run passes, on that round's diff
  (snapshot before the fixes launch); a re-reviewed real-build round gets
  Reviewer G instead; a contained change keeps the Hydrogen fix check.
- Reviewer G rows are OPEN findings (above). The other seats' items are
  `G<n>` leads you verify before they become findings; never Reviewer
  A/B/C, never a pass/fail, never a blocker.

## Model notes (for the model running this session)

- **Fable 5.2 (and any other Fable)** - not this file's audience: run Orchestrate mode (SKILL.md,
  phases.md); you orchestrate and never write code.
- **Opus 5.5** - at or above the Orchestrate threshold you run Orchestrate mode (SKILL.md session switch): phases.md is your text and you never write code in-session. Below it: one check per claim, no verifier
  subagents (the plan gate and review gate are the reviews). Status notes go with the next tool call; keep going until the
  acceptance criteria pass. Given a time budget, pace to it. Frontend
  without a design block falls back on generic defaults: run the design row
  first and name the patterns to avoid.
- **Sonnet 5.5** - keep going until the acceptance criteria pass; stop only
  when blocked on the user or before a risky step (at low effort an early
  check-in is the documented failure). Build only what the plan names;
  extras are follow-ups. At xhigh or max do not start your own review rounds
  or reviewer subagents - the plan gate and review gate are the reviews. The
  hardest long-horizon work suits an Opus model better.
- **Haiku 5.5** - you are the mechanical tier. Send a hard task to the plan
  gate at once; a short draft plan is fine, the gate seat's plan review does the design. Do the mechanical parts exactly as specified and hand
  judgment calls to the senior seat (the run's gate seat through the
  design-gate transport; on `advisor=<model>`, the advisor first) or the user. With this long a prompt at
  low effort you may stop early or call a change done unchecked: keep going
  until the acceptance criteria pass, run a real check that exercises each
  change before reporting it, and build only what the plan names. Search
  before stating anything that can have changed since your training
  (versions, prices, "latest"). At xhigh a turn can end with the whole answer
  in thinking: always end on visible text.
