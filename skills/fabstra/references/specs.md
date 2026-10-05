# FabStra spec templates - design review, builder blueprint, adversarial review

Contents: Design-review spec template (Phase 1b); Builder spec contract (Phase 2); Phase 2 - BUILD; Review spec (Phase 3)

Reached from: fabstra SKILL.md - before writing any blueprint or review spec

Related:
> The commands that carry these specs are in transport.md.
> Arbitrating what comes back is in phases.md.
## Design-review spec template (Phase 1b)

**Design-review spec template:**

```xml
<task>
Design review, read-only. You are the second architect - find what in this
plan WILL NOT WORK before it is built. You may read anything in the
repository and run read-only commands; you change nothing.
Brief: <the user's brief>
Plan: <numbered tasks with tiers and acceptance criteria, verbatim>
Project stack and hard rules: <from the project's CLAUDE.md, verbatim>
</task>
<blueprints>
<every builder spec, verbatim, in task order - outcome, invariants, scope,
interfaces and file ownership, pointers, acceptance, what not to touch>
</blueprints>
<review_scope>
Check, in this order: (1) each spec's pointers, interfaces, and invariants against the code it cites; (2) the seams between parallel tasks -
interface names, data shapes, and file ownership must agree, and no two
tasks may edit the same file; (3) the logic - edge cases, error paths,
empty states, retries, idempotency the specs get wrong or leave
undecided; (4) the tests - do the named cases prove the acceptance
criteria, and is the negative case real; (5) out-of-stack or non-existent
platform components (n8n node types, Make.com modules, API endpoints,
libraries not installed) - each is a P1. Do not redesign for taste; report
only what would fail, mislead the builder, or violate a hard rule.
(6) a `## Design (from design-pass)` block is Opus 5.5's call: check
feasibility and contradictions with the code only, never redesign it.
</review_scope>
<turn_budget>
You have 30 tool calls. Read whole files rather than line windows; find
callers with one grep pass; chain shell commands into one call. At your
26th call, stop exploring and write the report.
</turn_budget>
<grounding_rules>
Ground every finding in file:line evidence or command output you ran.
Label hypotheses as hypotheses. If you cannot verify a component exists,
mark it UNVERIFIED for the orchestrator - do not pass it silently.
</grounding_rules>
<action_safety>
Never modify any file. Write probe files only under <scratch dir>.
</action_safety>
<structured_output_contract>
Return exactly: (1) per task: SOUND, or REVISE with the specific objection;
(2) findings ranked - P1 the build will fail or violate a hard rule, P2 the
builder will likely get it wrong as written, P3 minor - each with the task
number, the blueprint line it concerns, file:line evidence from the repo,
what breaks, and your confidence 0-100. Report only findings you are 80+
confident in and would act on yourself. (3) nothing else. A plan with no
findings is a legitimate result - do not manufacture objections. Before
finishing, overwrite <scratch dir>/fabstra-design-findings.md via Bash
with this report.
</structured_output_contract>
```

## Builder spec contract (Phase 2)

## Phase 2 - BUILD (Claude subagents via the Agent tool; Codex side via Astra)

One Agent tool call per task. Opus tier: the arm the effort trial picks
(SKILL.md, Effort) - `subagent_type: "model-router:builder"` (Opus 5.5 xhigh)
or `"model-router:builder-medium"` (Opus 5.5 medium); a mechanical task
spanning 2+ files: `"model-router:builder-low"` (Opus 5.5 low, outside the
trial). All three pin their own model and effort. Sonnet and Haiku tiers:
`subagent_type: "general-purpose"`, `model: "sonnet"` / `"haiku"` per the rubric (REQUIRED - an
omitted model inherits the Fable session; the guard denies it), prompt = a
self-contained spec. Under a Sonnet max pin the Sonnet tier takes
`subagent_type: "model-router:sonnet-max"` instead, no `model:` field
(phases.md routing rubric, Sonnet max pin). The spec fixes the decisions that must not drift; the
builder owns everything inside them.

The spec fixes, in this order:

- **Outcome** - what exists, and what is true of it, when the task is done.
- **Invariants** - the business and safety rules that must hold in the
  result.
- **Scope and non-goals** - what the task covers and what it deliberately
  leaves alone.
- **Shared interfaces and file ownership** - between parallel tasks, and only
  where coordination needs them: the names, data shapes, and files each task
  owns.
- **Grounded pointers and conventions** - the nearest existing module of the
  same shape, cited file:line, as the pattern to match; the libraries to use
  and the ones not to reach for.
  - UI surface in the task (page, screen, component, dashboard, landing
    section, form, empty/error state): get its "## Design (from design-pass)"
    block from ONE Agent call, `subagent_type: "model-router:designer"` (Opus
    5.5 xhigh, read-only; for client-E client work run `airlock` first and pass
    the washed brief with `Pass: CLIENT`, other client work the brief as
    given with `Pass: CLIENT`, else `Pass: INTERNAL`), and paste the
    block into the builder spec's Conventions; the review spec gets its Gates
    and Verify sub-blocks. Builders never load skills, so a blueprint without
    this block ships the on-distribution defaults.
- **Acceptance cases** - by name, input, and expected result, including a
  negative case.
- **Required verification** - the commands the builder runs and reports.
- **What not to touch** - exact paths.

The builder investigates the code it touches and owns internal signatures,
structure, algorithms, and additional tests, and lists each such decision in
its report. Escalate (NEEDS_CONTEXT) only when the spec contradicts the
repository, an action is unsafe, or business meaning is ambiguous.
Scale it to the tier: a Haiku mechanical spec is exact text, file paths, what not to touch, and its acceptance checks.

Every spec also carries these lines, verbatim:

- "Hold the outcome, invariants, scope, shared interfaces, and file
  ownership this spec fixes. Inside them, investigate the code you touch and
  decide internal signatures, structure, algorithms, and additional tests
  yourself; list each decision in your report. Return NEEDS_CONTEXT only when
  the spec contradicts the repository, an action is unsafe, or business
  meaning is ambiguous."
- "Build every behavior the spec asks for, completely, and nothing beside
  it: a pre-existing bug, a performance concern, or an unrequested extension
  goes in your report as a follow-up, not in the change."
- "Respect the project's CLAUDE.md in your context. If the task seems to
  need a tool outside its stack, return NEEDS_CONTEXT - do not improvise a
  substitute."
- "Where the task produces testable behavior: write the test FIRST, run it
  to see it fail, then implement until it passes. Include at least one
  negative test - an input that must fail, confirmed failing. A rename,
  config, copy, or other reversible change whose test would only mirror the
  implementation gets no new test; the spec's verification command is its
  check."
- "Running the project's test suite and build is pre-approved only where this spec states they are local and isolated and says how that was checked; otherwise stop and report before running anything that reaches outside this repository."
- "Time matters here: do not spend time that can be avoided, and the earlier a correct result is obtained, the better."
- Multi-app specs only (n8n, GHL, Drive, mail, CRM automations): "Before taking any action, explore broadly with tool calls: list and open the emails, documents, spreadsheet tabs and records across the available apps that could be relevant to this task, including ones the task does not explicitly mention, and use what you find."
- Sonnet-tier specs only: "Keep working until everything this spec asks for is done; stop only when you cannot go on without the user or before a risky step."
- "Keep the report short, ending with exactly one status: DONE /
  DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED - plus changed paths, each
  implementation decision you made inside the spec, the verification
  commands you ran this session, and the tail of their output. 'It should
  work' does not count; only fresh command output counts."

**Codex-side tasks** take the same spec, delivered headless through Astra.
Write the spec to `<scratch>/fabstra-task-N.md`, then run the Codex
transport (launch with `--write --model gpt-6-astra --prompt-file
<scratch>/fabstra-task-N.md`, background wait, fetch). Any directory works (the companion falls back to the working
directory when there is no git repo). A NEEDS_CONTEXT re-send is a new
`--fresh` job with the revised spec; the answer lives in the spec, not in a
resumed thread (see the transport note on `--resume-last`). The companion
needs `codex` on PATH: `~/bin/codex` (bash) and
`codex.cmd` (cmd, PowerShell) shim to the desktop app's bundled binary.

Codex reads the project's `AGENTS.md` natively: root to cwd, one file per
directory, where `AGENTS.override.md` wins over `AGENTS.md`, which wins over
any `project_doc_fallback_filenames` entry (such as `CLAUDE.md`) an operator
has configured for that Codex home; plain markdown with no `@` imports, so a
pointer-only file delivers nothing; and a combined `project_doc_max_bytes`
budget (32 KiB by default) that truncates the stack. Launch Codex seats with
cwd at the project root: a non-git directory is searched at cwd only. A file
existing is not a seat receiving it: paste every business or safety
invariant the task needs into the Codex-side spec verbatim unless you have
established that the selected, untruncated instruction stack of that seat's
`CODEX_HOME` carries it. Never paste Claude-only routing (fabstra
lanes, Agent tool models, skill names) - delegated seats follow their spec,
not the session's orchestration rules. Agent tool builders inherit CLAUDE.md;
a Codex seat inherits only what its own `CODEX_HOME` and effective config
load. The layering that serves both tools: tool-agnostic facts in
`AGENTS.md`, and a thin `CLAUDE.md` whose first line is `@AGENTS.md`
followed by Claude-only rules.

**Astra delegates by tier.** Codex's `multi_agent` feature gives the parent
thread `spawn_agent`; three custom agents exist for it in `~/.codex/agents`:
`sol` (GPT-6.1 Sol at xhigh, workspace-write, the Opus-tier role), `terra`
(GPT-5.6 Terra at high, the Sonnet-tier role), and `luna` (GPT-6 Luna at
medium, the Haiku-tier role), plus `spark` (GPT-5.3-Codex-Spark at medium,
the same Haiku-tier role at 1000+ tok/s; defined only in `~/.codex-pro/agents`
because it is Pro-only and the proxy cannot serve it; it meters on its own
5-hour and 7-day Spark windows, separate from the general window Astra, Sol,
Terra, and Luna share, so prefer it over `luna` whenever the parent runs
natively on the Pro home). Children must not spawn further agents (the Pro
and `.codex-biz` homes set `max_depth = 1`; the main home sets no limit of
its own, and the codex-chatgpt-web bridge patches in `max_depth = 2` while
it is on, so the rule below is the enforcement there), at most 6 run at
once, and a job is capped at 1800 s.
Add this clause to every
Codex-side build spec:
"You are the parent thread. Spawn `sol` for a multi-file or design-level
sub-task, `terra` for a self-contained sub-task with a written contract,
and `spark` for mechanical steps (`luna` if `spark` is not defined in your
home). Sub-tasks whose files do not overlap launch together, in one turn;
do the typing yourself only when the task fits one thread. You own the plan as written, the integration, and the
single final report; pass each sub-agent its slice of the blueprint and the
stack rules verbatim and the same DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT
/ BLOCKED protocol; never delegate your own verification. Sub-agents you
spawn never spawn agents of their own. The blueprint
fixes the interface, the file set, and the acceptance criteria: keep those.
Inside them, resolve implementation details yourself rather than stopping,
and list each decision in your report. Return NEEDS_CONTEXT only when the
blueprint contradicts the repository or would require changing an interface
or a file the spec did not name.
You are done when every acceptance criterion passes and the integration
works - not at a first implementation." Reviewer roles never delegate: one
fresh context is the review.

## Review spec (Phase 3)

**Before writing the spec, produce the diff.** Run `git diff <base>` (the
commit the build started from, plus the working tree) AND
`git ls-files --others --exclude-standard` for the files the build created,
which `git diff` does not show; inline each new file's full contents after
the diff (do not stage them - the index is the user's). List the changed
files with a one-line note each and whatever callers or entry points you
already know. That is what goes in the `<context>` block: the reviewer then
spends its turns verifying instead of discovering, and keeps full freedom to
follow the change outward.

**When to include the `<context>`, `<review_scope>` and `<turn_budget>`
blocks:** when the build spans more than about two files, or the reviewer
would otherwise have to hunt for the callers itself. For a single-file
review with no callers, drop all three and send the plain spec - measured
2026-09-04 on the bench fixture (one 35-line module), the three blocks cost
1-6 extra tool calls and 114-205 s with nothing to discover, because
`review_scope` sends the reviewer looking for callers that do not exist.
The blocks pay for themselves only when there is discovery to skip.

**Review spec template** (GPT models hold contracts best as XML blocks):

```xml
<task>
Adversarially review this build. You are the red team - find what is WRONG.
Brief: <the user's brief>
Acceptance criteria: <from the plan, verbatim>
Project stack and hard rules: <from the project's CLAUDE.md, verbatim>
</task>
<context>
Files changed: <paths, one per line, each with a one-line note of what the
change does>
Entry points and callers you already know: <what calls, renders, or imports
the changed code - pages, routes, workflows, templates - or "unknown">
Test command: <how to run the project's tests, or "none">
Diff:
<the build's unified diff, inline: `git diff <base>` over the working tree,
followed by the full contents of every untracked file the build created,
or for a non-git project the full text of each changed file. Over ~1500
lines: inline the hunks for the files under review and say which files to
read whole>
</context>
<review_scope>
Start from the diff: verify it first, then follow every edge it touches -
callers, templates, configs, sibling pages, the other side of any contract
it changes. The diff is where you start, not where you stop; a change that
is correct in isolation and breaks a caller is still a P1.
</review_scope>
<turn_budget>
You have 30 tool calls in total. Spend them on verification, not discovery:
read whole files rather than line windows; find callers with one grep pass
over the tree, not one per symbol; chain shell commands into one call.
Do not save findings one at a time - every save is a tool call. If you
reach your 20th tool call without having written the report, save what
you have confirmed so far to <scratch dir>/fabstra-review-findings.md in
one Bash call; at your 26th, stop exploring and write the final report.
(Codex transport: the orchestrator replaces this save with "note what you
have confirmed so far in your final message".)
</turn_budget>
<grounding_rules>
Ground every finding in file:line evidence or command output you ran.
Never present an inference as fact; label hypotheses as hypotheses.
Out-of-stack output, or references to platform components that do not
exist (n8n node types, Make.com modules, API endpoints), are P1 findings.
Verify existence with what Bash gives you (installed packages, local
configs, the platform's API if credentials are local); if you cannot
verify either way, mark the component UNVERIFIED for the orchestrator
to check - do not silently pass it.
A `## Design (from design-pass)` block in the spec is settled direction:
report only what does not work as built, never taste.
</grounding_rules>
<dig_deeper_nudge>
After the first plausible issue, keep going: empty states, error paths,
edge inputs, stale state, concurrency, and whether the acceptance criteria
are actually met rather than approximately met.
</dig_deeper_nudge>
<action_safety>
Never modify the reviewed files. Run builds and tests only where the specs
above state they are local and isolated; otherwise stay read-only. Write
probe files only under <scratch dir>.
</action_safety>
<structured_output_contract>
Return exactly: (1) per acceptance criterion: PASS or FAIL with evidence;
(2) findings ranked by severity - P1 breaks the brief, P2 should fix, P3
minor - each with file:line, what breaks, how you proved it, and your
confidence 0-100. Report only findings you are 80+ confident in and would
personally act on: precision over recall - a noisy review gets ignored.
(3) nothing else. Finding nothing wrong is a legitimate result - do not
manufacture findings to look thorough. Before finishing, overwrite
<scratch dir>/fabstra-review-findings.md via Bash with this final report.
</structured_output_contract>
```

Codex's read-only sandbox cannot write the findings file, so before sending
a review spec through the Codex transport replace every save instruction
(the `<turn_budget>` checkpoint save and the `<structured_output_contract>`
overwrite) with "return the report as your final message"; a literal
reviewer given an unsatisfiable write contract wastes calls or reports
BLOCKED. The report then arrives only through `result <job-id>`. If a wait ends before the reviewer has
finished, wait again on the same job id - never re-launch blind.
