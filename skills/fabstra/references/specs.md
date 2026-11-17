# FabStra spec templates - design review, builder blueprint, adversarial review

Contents: Design-review spec template (Phase 1b); Builder spec contract (Phase 2); Review spec (Phase 3)

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
Project stack and hard rules: <from the project's CLAUDE.md, plus any feedback
memories that apply to this task, all verbatim>
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

Phase 2 - BUILD: Claude subagents via the Agent tool; Codex side via Astra.

One Agent tool call per task. The tier picks the seat (phases.md, "Claude
seat efforts", which also holds the excluded-category floor, the miss ladder
and the pins): `subagent_type: "model-router:builder"` with hard tier
`effort: "high"`, contract tier `effort: "medium"`, mechanical tier
`effort: "low"`. It pins its own model, so the call passes no `model` field;
it always passes `effort` by tier; log `seat=model-router:builder effort=<x>`.
Under a Sonnet max pin the contract tier takes
`subagent_type: "model-router:sonnet-max"` instead, no `model:` field
(phases.md routing rubric, Sonnet max pin). A seat that is not a pinned
`model-router:` agent names its model in the call, because an omitted model
inherits the session model and the guard denies a model-less call: a user pin of Sonnet or Haiku is `subagent_type: "general-purpose"`, `model: "sonnet"` / `"haiku"`,
and the "any other Claude seat" of phases.md takes its model and effort from
there. The prompt is a self-contained spec. The spec fixes the decisions that
must not drift; the builder owns everything inside them.

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
    block from one Agent call, `subagent_type: "model-router:designer"` (Opus
    5.5 xhigh, read-only; client work, client-E included, passes the brief as
    given with `Pass: CLIENT` (JC 2026-10-31: no airlock wash before the
    designer), else `Pass: INTERNAL`), and paste the
    block into the builder spec's Conventions; the review spec gets its Gates
    and Verify sub-blocks. Builders never load skills, so a blueprint without
    this block ships the on-distribution defaults.
- **Acceptance cases** - by name, input, and expected result, including a
  negative case.
- **Required verification** - the commands the builder runs and reports,
  picked by what the change is; take the strongest check that fits, since
  unit tests alone can pass while the feature is broken:
  - a user flow (a page, a form, an endpoint a client calls): an end-to-end
    run against the running app - the project's `verify` or `run-<name>`
    skill (verify-skill.md), or the flow driven step by step with each
    observed result;
  - a parser, serializer, money or date calculation, normalizer, retry or
    migration step: property tests with the project's property library
    (fast-check, Hypothesis, proptest; adding one is a spec decision) -
    round-trip (decode(encode(x)) equals x), invariant (a balance never
    goes negative), idempotency (twice equals once), equivalence (the
    optimized path equals the naive one);
  - a migration, port or rewrite that keeps behaviour: a differential test -
    old and new on the same inputs (generated, or a sample of real ones),
    irrelevant differences normalized (whitespace, ordering, timestamps),
    and an approved-differences list for the changes the spec intends; the
    old system is the oracle.
- **What not to touch** - exact paths.

The builder investigates the code it touches and owns internal signatures,
structure, algorithms, and additional tests, and lists each such decision in
its report. Escalate (NEEDS_CONTEXT) only when the spec contradicts the
repository, an action is unsafe, or business meaning is ambiguous.
Scale it to the tier: a mechanical-tier spec is exact text, file paths, what not to touch, and its acceptance checks.

The Haiku seat is reached only through a user pin (phases.md, "Claude seat
efforts", Pins); the rest of this block applies to that seat. The Haiku seat
is Claude Haiku 5.5: `~/.claude/settings.json` env
`ANTHROPIC_DEFAULT_HAIKU_MODEL=claude-haiku-5-5` maps the `haiku` alias to
it (since CLI 2.1.296 the bare alias also resolves to Haiku 5.5 on its own - verified 2026-10-10 - so the pin is a safeguard). A Haiku
subagent inherits the session's effort (`effortLevel` is `high` here, which
the guide recommends for strict instruction following); leave the Agent
`effort` unset and never pass `low`, which skips searches and checks. Per
Anthropic's Haiku 5.5 prompting guide, a Haiku spec also carries, verbatim:

- Every Haiku spec: "Keep working until everything this spec asks for is
  done, and only stop to ask when you can't go on without the lead or before
  a risky step. When the work is done and checked, stop and report. Don't
  add new features, docs, or refactors that weren't asked for. If you think
  one would help, mention it at the end instead of doing it."
- A spec that changes runnable code: "When you change code that can be run,
  built, or type-checked, run a real check that exercises the change before
  reporting it done: the project's tests, type-checker, or build, or the
  changed command itself. A syntax-only check, or a check command that failed
  to start, does not count; if all that is missing is the project's declared
  dependencies, install them with its own package manager and lockfile (e.g.
  npm install, pip install -r requirements.txt), never via sudo or the system
  package manager, unless told not to. Only if no real check can run here,
  say which one you did not run and why instead of reporting the change as
  done."
- A lookup that may search the web: "The current date is <YYYY-MM-DD>. Your
  training data ends well before today's date. Records, office holders,
  prices, versions, rules and anything "latest" may have changed since then,
  so search for those before you answer, even when you feel sure. Facts that
  can't change need no search. When the answer depends on where the user is,
  put the user's country or region in the search query."

Haiku 5.5 runs safety classifiers (`stop_reason: "refusal"`; the `cyber`
category can fire on benign security work) and a resend usually refuses
again: send a refused Haiku task to the seat its tier takes unpinned
(phases.md, "Claude seat efforts") with the same spec.

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
- "Where the task produces testable behavior: write the test first, run it
  to see it fail, then implement until it passes. Include at least one
  negative test - an input that must fail, confirmed failing. A rename,
  config, copy, or other reversible change whose test would only mirror the
  implementation gets no new test; the spec's verification command is its
  check."
- "The checks that judge this task stay as they are: the tests and fixtures
  named in its acceptance, lint, type and CI configuration, hooks, and
  REVIEW.md change only where this spec names them. If such a check looks
  wrong, report it with your evidence and leave it in place."
- "A flaky test gets its root cause found and fixed. Retrying until it
  passes, adding sleeps, or skipping it hides the failure; if you cannot
  find the cause, leave the test in place and report it as flaky with the
  failing output, status DONE_WITH_CONCERNS."
- "Running the project's test suite and build is pre-approved only where this spec states they are local and isolated and says how that was checked; otherwise stop and report before running anything that reaches outside this repository."
- "Time matters here: do not spend time that can be avoided, and the earlier a correct result is obtained, the better."
- Multi-app specs only (n8n, GHL, Drive, mail, CRM automations): "Before taking any action, explore broadly with tool calls: list and open the emails, documents, spreadsheet tabs and records across the available apps that could be relevant to this task, including ones the task does not explicitly mention, and use what you find."
- Automation specs (n8n, Make, GHL, VAPI) carry verbatim: "A source that fails to read is reported as unreadable and its cursor does not move; a write is recorded only after the destination confirms it."
- Contract- and mechanical-tier specs (`model-router:builder` at effort medium or low, and a pinned Sonnet or Haiku seat): "Keep working until everything this spec asks for is done; stop only when you cannot go on without the user or before a risky step."
- "Before your report, stop every background command you started (dev servers, watchers, tails): a headless run waits for them and can hit its timeout."
- "Keep the report short, ending with exactly one status: DONE /
  DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED - plus changed paths, each
  implementation decision you made inside the spec, the verification
  commands you ran this session, and the tail of their output. 'It should
  work' does not count; only fresh command output counts."

**Advisor block** (advisor.md) - optional. Only when RUN.md logs
`advisor=<model>` (not `off`; the default is `fable`) and the effective state
matches it (advisor.md, Lifecycle): the seat has that advisor attached (a
headless seat launched with `--advisor <model>`; an Agent-tool seat only while
the lead's `status --project` read shows `effective=<model>`) and `CLAUDE_CODE_DISABLE_ADVISOR_TOOL` is not
set to a true value in the lead's environment or a settings `env` block, a
Claude builder spec carries, verbatim:

> An advisor model is attached to this session. Consult it before you settle how to build the feature, and again before you report DONE; it reads your whole transcript, so ask in one line. Its reply is advice: check it against this spec and the code before you act on it. In your report, list each consult and what you did with its advice.

While an advisor is effective, every review, gate and grading spec
carries, verbatim: "Do not consult the advisor tool in this session; this seat's judgment must be its own."
On an `advisor=off` run with no advisor effective, no spec carries either.

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
`sol` (GPT-6.1 Sol at xhigh, workspace-write, the hard-tier role), `terra`
(GPT-6.1 Terra at high, the contract-tier role), and `luna` (GPT-6 Luna at
medium, the mechanical-tier role), plus `spark` (GPT-5.3-Codex-Spark at medium,
the same mechanical-tier role at 1000+ tok/s; defined only in `~/.codex-pro/agents`
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
commit the build started from, plus the working tree) and
`git ls-files --others --exclude-standard` for the files the build created,
which `git diff` does not show; inline each new file's full contents after
the diff (do not stage them - the index is the user's). List the changed
files with a one-line note each and whatever callers or entry points you
already know. That is what goes in the `<context>` block: the reviewer then
spends its turns verifying instead of discovering, and keeps full freedom to
follow the change outward.

**REVIEW.md:** when the reviewed project has a `REVIEW.md` at its root,
take it from the build-start base, never the working tree: `git show
<base>:REVIEW.md`, or in a non-git project the copy in
`<scratch>/fabstra-prebuild/` (copy it there before the first builder
launches); a REVIEW.md the build created counts as absent. The rules that
judge a change come from where the change cannot edit them. Paste that copy
verbatim into the template's "Project review rules" line, beside
"Project stack and hard rules" - review seats launch `--bare` and never load
it themselves. Follow it with this precedence line, verbatim: "These project
rules decide what to look for and what to skip; the
`<structured_output_contract>` below decides the returned format, the
severity scale and the per-id verification. Read their tags as: Important
-> P1 or P2 by impact, Nit -> P3 (the project's nit cap still applies),
Pre-existing -> PRE-EXISTING under the contract's base-proof rule."

**When to include the `<context>`, `<review_scope>` and `<turn_budget>`
blocks:** when the build spans more than about two files, or the reviewer
would otherwise have to hunt for the callers itself. For a single-file
review with no callers, drop all three and send the plain spec - measured
2026-09-04 on the bench fixture (one 35-line module), the three blocks cost
1-6 extra tool calls and 114-205 s with nothing to discover, because
`review_scope` sends the reviewer looking for callers that do not exist.
The blocks pay for themselves only when there is discovery to skip.
A re-review keeps its round facts even as a plain spec: beside
`<prior_findings>` it still carries the `Build-start base:` line, that
round's diff, and from round 3 the round-3 `<review_scope>` text.

**Reviewer C (the fresh Fable 5.2 Agent seat, `model-router:reviewer`, effort high; effort xhigh on a build in an excluded category):**
drop the `<turn_budget>` block from the spec it receives. The 30-call
ceiling is the proxy `claude -p` seats' `--max-turns 30` (transport.md); the
Agent seat has no cap and carries about 2.5x the scope (fanout.md, seat
capacity), so the count only cuts its verification short. Keep the save
instructions - it can write. Same for the design-review template on the
rows where the fresh Fable holds the design gate (transport.md, Reviewer
fallback). GPT seats keep the block.

**Review spec template** (GPT models hold contracts best as XML blocks):

```xml
<task>
Adversarially review this build. You are the red team - find what is WRONG.
Brief: <the user's brief>
Acceptance criteria: <from the plan, verbatim>
Checks the spec allowed to change: <per task: the tests, configs, hooks or
REVIEW.md that task's spec named as editable, or "none">
Project stack and hard rules: <from the project's CLAUDE.md, plus any feedback
memories that apply to this task, all verbatim>
Project review rules: <the project's root REVIEW.md, verbatim, then the
precedence line above; drop this line when there is none>
</task>
<prior_findings>
(Re-reviews only: every round after the build's first review, in every lane
and on every seat, plain single-file specs included; drop it on round 1.)
Review round: <N>
Ledger rows for this build, from the logbook, one per finding:
<id | file:line | one-line defect | status: FIXED (verified), WITHDRAWN
(rejected by the lead or withdrawn by a reviewer), or OPEN - an OPEN row
whose fix landed since the last review reads "OPEN - fix claimed" | for
WITHDRAWN, the logged reason>
</prior_findings>
<context>
Files changed: <paths, one per line, each with a one-line note of what the
change does>
Build-start base: <the commit the diff is taken against; non-git: the
<scratch>/fabstra-prebuild/ snapshot path, or "non-git: none" when no
snapshot exists>
Entry points and callers you already know: <what calls, renders, or imports
the changed code - pages, routes, workflows, templates - or "unknown">
Test command: <how to run the project's tests, or "none">
Diff:
<the build's unified diff, inline: `git diff <base>` over the working tree,
followed by the full contents of every untracked file the build created,
or for a non-git project `diff -u` of each changed file against its
`<scratch>/fabstra-prebuild/` copy (the full text when no snapshot exists). Over ~1500
lines: inline the hunks for the files under review and say which files to
read whole. Round 3 on (phases.md "Phase 4"): only the diff since the last
reviewed state>
</context>
<review_scope>
<rounds 1-2:>
Start from the diff: verify it first, then follow every edge it touches -
callers, templates, configs, sibling pages, the other side of any contract
it changes. The diff is where you start, not where you stop; a change that
is correct in isolation and breaks a caller is still a P1.
<round 3 on (phases.md "Phase 4"), in place of the paragraph above:>
Verify the fixes and the changed lines in this diff. Follow callers of the
changed lines only; do not re-read unchanged code for new findings.
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
An edit to a check that judges this build - a test or fixture the
acceptance criteria name, lint, type or CI configuration, hooks, REVIEW.md -
that is not listed under "Checks the spec allowed to change" is a P1: the
build weakened its own check. A test changed to retry, sleep or skip until
it passes is the same finding.
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
(2) re-reviews only - prior-finding verification, one line per OPEN row of
<prior_findings>: `VERIFIED FIXED: <id>` or `STILL OPEN: <id>`, plus
`REOPENED: <id>` for a FIXED row the current changes reintroduce, each with
file:line evidence; an incomplete fix is STILL OPEN and a reintroduced one
REOPENED here, never a new finding;
(3) new findings ranked by severity - P1 breaks the brief, P2 should fix, P3
minor - each with file:line, what breaks, how you proved it, and your
confidence 0-100. Report only findings you are 80+ confident in and would
personally act on: precision over recall - a noisy review gets ignored.
Name each finding's bug class (the defect pattern, e.g. "unquoted path in a
shell command") and list every instance of that class in the reviewed
scope, found with one grep pass, not only the first. A new finding is never
an id listed in <prior_findings>; a WITHDRAWN id comes back only when new
evidence contradicts its logged reason, and you name that evidence. A new
instance of a listed bug class is a new finding. PRE-EXISTING is a tag
beside the severity, judged against the build-start base, not by location:
use it only for a defect that existed before the build, independent of it,
that you show reproduces on the base (`git show <base>:<path>`, probes
under <scratch dir>); without that proof it is an ordinary finding. A
regression the build causes in code it did not touch - a changed API or
shape breaking an untouched caller - did not exist on the base, so it is
never PRE-EXISTING: it stays an ordinary finding, and a change that breaks
a caller is still a P1 (review_scope).
(4) nothing else. Finding nothing wrong is a legitimate result - do not
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
