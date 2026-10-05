# FabStra long form - pairing, rubrics, orchestrator rules, phase procedure

Contents: Hard rule, session check, pairing, arbitration; Routing rubric; Effort rubric; ORCHESTRATOR RULES; The run logbook; Phase 1 - ALIGN AND PLAN; Arbitrate the design review (Phase 1b); Phase 2 - status handling, task sizing, smoke gate; Phase 4 - FIX AND SHIP

Reached from: fabstra SKILL.md - before planning, and wherever the root condenses a rule

Related:
> The crew table, the routing policy and every launch command are in transport.md.
> The fast-pin bullet of the effort rubric and the quota windows are in quota.md.
> The three spec templates are in specs.md.
## Hard rule, session check, pairing, arbitration (long form of the root)

**Hard rule:** Claude subagents run through the Agent tool on this session's
normal login - NEVER through the proxy (Anthropic's terms ban subscription
OAuth in third-party tools). Astra and Sol reach this machine only through
every ChatGPT login in the local proxy (CLIProxyAPI, port 8317; 7.3.12 verified
2026-09-23 serves `gpt-6-astra`, `gpt-6-sol` and `gpt-6-luna` - 7.2.157 did not
know GPT-6 Sol/Luna). `gpt-6.1-sol` verified served 2026-09-30 (proxy 7.3.12; native Codex needs CLI 0.159.2+). The
`codex` shims in `~/bin` add `-c model_provider=router`, so the
Codex CLI's model calls also go through that proxy as a plain OpenAI
Responses provider; nothing is translated, and the Codex runtime, sandbox,
and `spawn_agent` stay native.

**Session check:** the orchestrator is Fable 5.1, or Opus 5.5 above the
Orchestrate threshold (a plan with 2+ tasks, or an excluded category) -
Orchestrate mode, this file; the orchestrator never writes code in-session.
On Opus 5.5 the mode is settled when the draft plan exists: at or above the
threshold -> continue here from Phase 1 with that draft as the plan; below
it -> Lead mode. Log `mode=` in RUN.md; never switch after a builder has
launched. On Opus 5.5 below the threshold, and on Sonnet 5.5 / Haiku 4.5,
run Lead mode instead - lead-mode.md:
the session model builds, the gate seat (Astra or Sol) gates the plan and reviews, and the fixes are
delegated by tier; do not ask for a switch. Any other Claude model (a newer
or older Fable, Opus, Sonnet or Haiku) runs the mode of its family's row in
the SKILL.md session switch; no Claude session is asked to switch. Only a
non-Claude session model outside the Lane C and Lane D exceptions below
stops before Phase 1 and asks the user to switch with `/model claude-opus-5-5`.
**Lane C exception:** a session already running
on a routed OpenRouter model (`scripts/session.ps1 glm-5.3-flash` - the
`budget` shim's default - or any other lane alias: `deepseek-v4-pro` for a
`pro` ask) is how JC starts work once the Claude
limit is hit - accept that session model instead of asking for the switch,
but only for Lane C, and say so in the logbook. **Lane D exception:** a session
running on `gpt-6-astra` or `glm-5.3-flash` (or another proxy alias except
`deepseek-v4.1-flash`, which hangs as a lead - 0/5 on 2026-09-11)
that the user wants to LEAD the run is Lane D - accept it, and run the Lane D
seats in lane-d.md instead of this crew.

**Pairing rule:** Claude (Opus/Sonnet/Haiku) built -> the gate seat reviews
(Reviewer A: Astra on the Astra row, Sol on the Sol row - gate seat
rubric, SKILL.md); an xhigh row (an excluded category, multi-file
architecture, re-review after a P1) adds a fresh Fable (Reviewer C) in
parallel with the full scope, and the lead rules on both ledgers. Codex
side (Astra or Sol + Terra/Luna) built -> fresh Fable
reviews (Reviewer C), because Astra reviewing a build it orchestrated is the
same eyes twice. Astra blocked after a Claude build -> Sol reviews at the
same effort (Reviewer B), logged as "Astra quota spent, Sol reviewed". Sol cooling on the Sol row with Astra available -> Astra at the Sol row's effort, logged "Sol quota spent, Astra gated/reviewed". Astra
AND Sol both cooling (proxy still up) after a Claude build -> Reviewer A
(Lane C, glm-5.3-flash), logged as "GPT quota spent, Lane C reviewed" -
EXCEPT excluded categories (money, auth, PII or de-identification,
permissions, data migration, concurrency, a client-facing release), which
never take a Lane C seat, not even for the review or the design gate: with
Astra and Sol both cooling, that review goes to the fresh Fable (Reviewer
C) instead, logged as "same-family review, GPT seats cooling, Lane C
excluded", so nothing sensitive leaves the Claude login. The proxy itself
down -> Reviewer C, logged as a same-family review. A **mixed
build** (some tasks Claude, some Codex side) gets both reviews in the same
message, partitioned by provenance: Reviewer A the BUILDER tasks only,
Reviewer C the CODEX tasks and every seam with the BUILDER tasks; each
acceptance criterion goes to exactly one reviewer (lead-mode.md, the review
gate, has the wording). A contained change (Phase 1) has no gate seat and
takes one review: Claude built -> Sol high; Codex side built -> fresh Fable.
Fix rounds are different: the Codex column may fix a Claude build (Phase 4
default), and the re-review rule there handles the family change. The
orchestrator never builds under any pairing; Fable 5.1 never builds at all.
Lane B (Astra solo) built -> Sol xhigh
(Reviewer B) AND a fresh Fable (Reviewer C) review in parallel,
independently, and the lead rules on every finding before the work ships
(Lane B parts 4-5); Astra never reviews its own solo build. Lane
C (budget crew) built -> Reviewer A (Lane C, `glm-5.3-flash`) alone on
single-file work, plus Reviewer B (Lane C, `deepseek-v4-pro`) on multi-file
work; the
orchestrator never reviews its own lane.

**Arbitration rule:** when Astra's design review and the plan disagree, the
lead decides (Fable; the session model in Lead mode) and writes the reason in
the logbook. Astra advises; it does
not own the plan. A design finding is accepted by revising the blueprint, or
rejected with one line - never silently dropped, never applied unread.
A design-review or review finding that objects to the Design block's taste
is rejected with one line; a feasibility finding against it is arbitrated
like any other.

## Routing rubric (tag every task in the plan)

- **Opus** - multi-file features, architecture or data-model decisions baked
  into code, tricky algorithms, integration surfaces, debugging where the
  first theory might be wrong.
- **Sonnet** - self-contained changes with a written contract: standard
  endpoints, UI components, tests against defined behavior, refactors with a
  clear before/after.
- **Sonnet max pin** (the one rule; other sites point here) - a user pin of
  Sonnet max ("sonnet max", "sonnet 5.5 max", "sonnet max thinking") sends
  that run's Sonnet-tier tasks, builds and fixes, to
  `subagent_type: "model-router:sonnet-max"` (Claude Sonnet 5.5 at max; it
  pins its own model and effort, so no `model:` field) instead of
  `general-purpose` + `model: "sonnet"`; nothing routes there unpinned. The
  pin reaches only the Claude Sonnet seat: it is not an Astra or Sol effort
  pin (the Codex transport rejects `max`), so their effort follows the
  effort rubric unless an effort word pins it separately. Log the pin in RUN.md.
- **Haiku** - lookups, running commands and reporting output, and
  single-file mechanical edits: a rename, config edit, format conversion, or
  doc touch-up in one file.
- **Opus 5.5 low** (`subagent_type: "model-router:builder-low"`) - mechanical
  edits that span 2+ files: renames across files, a known pattern applied
  across files, format conversions, boilerplate across files. Outside the
  effort trial (log `arm=builder-low eligible=no`).
- **Codex side (routed)** - the default owner for a self-contained,
  well-specified Opus- or Sonnet-tier task (a written contract, no
  Claude-only MCP tool or skill, no CLAUDE.md-context dependence) in a folder
  that has passed the Codex write probe (transport.md); Claude side for the
  rest, and for every task in a folder that has not passed. Same spec
  contract as a Claude builder; the gate seat is the parent thread - Astra
  spawns `sol` / `terra` / `spark` by the same three tiers, Sol does the
  Opus-tier work itself and spawns `terra` / `spark` (Sol-parent clause,
  transport.md); `luna` replaces `spark` only when the parent runs through
  the proxy.
- **Design and UI/UX** - any task with a user-facing surface (page, screen,
  component, dashboard, landing section, form, empty/error state) gets its
  `## Design (from design-pass)` block from ONE Agent call,
  `subagent_type: "model-router:designer"` (Claude Opus 5.5 at xhigh,
  read-only; it pins its own model and effort), before its Opus or Sonnet
  blueprint is written. For client-confidential work run your
  redaction gate (`airlock` if installed) first and hand the designer the washed brief
  with `Pass: CLIENT`; other client work skips airlock and passes the brief
  as given with `Pass: CLIENT`; otherwise state `Pass: INTERNAL`. The block goes into the builder spec's Conventions and
  its Gates / Verify sub-blocks into the review spec (specs.md). Opus 5.5
  owns visual direction; Astra and every other reviewer
  report only what will not work, never taste. Lane C and Lane D sessions
  cannot use the Agent tool for Claude seats: reach the designer by the
  stripped-env headless command in lane-d.md (no `--bare`) with `--model claude-opus-5-5
  --effort xhigh`, never through the proxy; a Lane C run with the Claude
  login spent skips the design lead and logs it.
- **Browser or desktop surface** - browser QA, dashboard testing, form
  filling, anything the user says "use computer use" about: Codex side on
  the Pro home, per surfaces.md. Not a Claude
  builder, not the `claude -p` transport.
- **Concept render (design, dashboard, UI/UX work ONLY)** - a GPT Image 2
  render of a screen when the visual direction is undecided or the user
  asks for a mockup: Codex side on the Pro home via the built-in
  `image_gen` tool, per "Concept renders" in surfaces.md. Never for
  backend, data, automation, or any task with
  no UI; never a substitute for building the UI in code.
- In doubt between two tiers, take the higher one - a failed cheap build
  costs more than the tier difference.
- **Tag every task yourself.** The per-prompt Jev tag line and the batched
  tagging call were retired 2026-09-28: the lead sets tier, effort and seat
  per task from this routing rubric alone and logs the pick, with its
  confidence, in RUN.md. The PreToolUse guard (`scripts/jev-agent-guard.py`)
  only denies an Agent call that names no model (pinned `model-router:` /
  `codex:` subagent types are exempt - they pin their own model); put
  `jev-override: <reason>` on its own line in the spec when a deliberate
  override still needs to pass.
- You orchestrate, never build. Reviewers review, never build. Astra as
  design reviewer or build reviewer never edits; Astra as Codex parent
  builds only what its spec names.

## Effort rubric (Astra and Sol) - pick per call, write it in the plan and logbook

`--effort` is chosen per call from what is being reviewed or built, not
fixed. On Sol each step up roughly doubled wall time (xhigh reviews 4-6 min
on 2026-09-04). Log the duration of every Astra and Sol call in RUN.md; the
rubric is tuned from those numbers.

| Effort | Astra design review of a plan for... / review of a build of... | Codex-side build of... |
|---|---|---|
| **xhigh** | anything touching money, auth, PII or de-identification, permissions, data migration, concurrency, or a client-facing release; multi-file architecture; a re-review after a P1 fix; the user asks to "break it" | Opus-tier tasks (Astra parent at xhigh; `sol` runs at xhigh) |
| **high** (default) | standard features with tests, integration surfaces, refactors with a clear before/after, most fix-round re-reviews | Sonnet-tier tasks (`terra` runs at high) |
| **medium** | docs, config, copy, renames, generated boilerplate, a single-file point fix you can verify yourself | Haiku-tier tasks (prefer `spark` when Astra runs natively on Pro - free against the general window - else `luna`, medium) |

Rules:
- **User override pins the run.** An effort word in the invocation or the
  brief - `/fabstra ... xhigh`, "astra xhigh", "review at high", "quick
  review" (= high) - sets every Astra and Sol call YOU issue in that run
  (design review, Codex-side build launch, review, Sol fallback) to that
  effort; the rubric only decides when no effort was named. The pin does not
  reach into Codex children: agents Astra spawns run at their agent-file
  efforts (`sol` xhigh, `terra` high, `luna` medium), which is by design -
  say so in the logbook rather than treating it as a violation. A "sonnet
  max" phrase is not an effort word: it pins only the Claude Sonnet seat
  (routing rubric, Sonnet max pin).
- Take the higher effort whenever the diff mixes tiers or you are unsure;
  a shallow review of a deep bug costs more than the minutes saved.
- Floor: never below **high** for anything a user or client will run. Medium
  is for changes whose worst failure is cosmetic.
- Log the chosen effort and the one-line reason (rubric row, or "user said
  xhigh") in `RUN.md` beside the task.
- Opus-tier builder arm: effort-trial.md (time-boxed trial) - read it before any Opus-tier delegation; its rule picks `model-router:builder` or `model-router:builder-medium` and what to log.
- The effort row comes from this rubric alone, picked per task and logged
  beside the pick. The floor still applies: never below high for anything a
  user or client runs.
- Do not lower effort mid-run to save time. Raise it after a review that
  came back empty on a build you doubt, or after a fix round that did not
  shrink the findings count.

## ORCHESTRATOR RULES (non-negotiable)

1. **You never write code** (Orchestrate mode; Lead mode: lead-mode.md).
   Builders build, reviewers review, you write specs, verdicts, and the final
   report. A missed build or a review finding
   goes back as a fix delegation with the evidence attached - even a
   one-line fix. You do not open an editor.
2. **Specs carry the decisions that must not drift:** outcome, invariants,
   scope and non-goals, shared interfaces and file ownership, grounded
   pointers, acceptance, verification (specs.md, "Builder spec contract").
   Builders own everything inside those lines and report each decision.
   Astra's design review sharpens the specs; it does not replace them.
   Lane B is the one exception: there the brief carries the contract and the
   acceptance criteria, Astra owns the design by the user's choice, and this
   rule governs Lane A specs only.
3. **Context budget, not read caps: read what a decision depends on, whole files included; verify landed work with targeted slices; batch searches into one call; nothing rides in context that a later turn will not use.**
4. **Independent tasks launch in parallel** - multiple Agent calls in a
   single message. Builders run in the background: while they work, write
   the next spec, draft the review spec, and slice-verify tasks that have
   landed. Every builder and reviewer must finish before the session ends;
   never leave delegations in flight.
5. **The logbook, not your memory, is the source of truth.** Keep
   `.fabstra/RUN.md` current (next section); after a crash, compaction, or a
   new session, resume from it instead of re-planning.
6. **One accountable orchestrator.** Astra never talks to the user, never
   changes the plan on its own, and never picks its own scope. Everything it
   does arrives as a spec from you and returns as a report to you.

## The run logbook - `.fabstra/RUN.md` in the project directory

The logbook lives at `.fabstra/RUN.md` in the project directory the session
was launched from - one per client or project folder. Create it the moment
the plan is approved; update it whenever a task changes
status, after the design review, after the smoke gate, and after each
arbitration. Contents: the brief, the approved plan (tasks, tiers,
acceptance criteria), the design-review ledger (each Astra finding ->
spec revised / rejected + one-line reason), one status line per task,
smoke-gate result, review findings ledger (each finding -> fixed/rejected +
one-line reason), and what is still open. You are the only writer -
builders and reviewers never touch it. (In a git repo, add `.fabstra/` to
`.gitignore` unless the user wants the record committed.)

Each task line carries `tier`, `arm` (`builder` or `builder-medium` for an
Opus-tier delegation, `builder-low` for a multi-file mechanical one, logged
`eligible=no`, else `n/a`), `eligible` (yes/no, Opus-tier tasks, per
the effort trial), `effort`, `elapsed` (minutes from launch to accepted), and
`first_pass` (yes/no - accepted with no fix round). Each review finding
carries its task number and `repro: yes|no|na` (a failing reproduction
existed before the fix).

Invoked while an unfinished RUN.md exists? Summarize it and ask the user:
resume where it left off, or start fresh. Starting fresh over an existing
RUN.md (finished or abandoned) first renames it to
`.fabstra/RUN-<YYYY-MM-DD-HHMMSS>.md`, stamped from that file's own mtime; if
that name already exists, append `-2`, `-3`, ... - never overwrite. A folder
keeps every run's record; the orchestrator never deletes a logbook.

## Phase 1 - ALIGN AND PLAN (you)

- **Pick the lane first.** Lane A (default, the phases below): you
  blueprint, Claude builds, Astra design-reviews and reviews. Lane B (Astra
  solo): the user names Astra as the builder - "astra solo", "let Astra
  design and build", "astra build it", or the brief says Astra owns the
  design. A count - "spawn 3 astra subagents", "a few astras on this",
  "astra x3" - is Lane B fan-out (lane-b.md, "Fan-out"): N solo Astras on N
  disjoint slices, never N children of one Astra parent.
  Lane B replaces Phases 1b-4 with lane-b.md: you write a brief, not
  blueprints; Astra designs
  and builds in one session; Sol and a fresh Fable both review and the
  lead rules on every finding. Write the lane in the plan, the
  logbook, and the report. Never mix Lane B with Claude builders in the
  initial build.
- **Pick the lane yourself.** From the brief and bcost, pick Lane A (default),
  Lane B (the user names Astra), or Lane C (`budget`/cheap crew), and log the
  choice and reason in RUN.md. Excluded work (money, auth, PII, permissions,
  migration, concurrency, a client-facing release) never takes Lane C
  whatever bcost says - the lead judges excluded from the categories list;
  Lane C's own `jev excluded` gate in lane-c.md stays as the budget lane's
  own check.
- A brief that already states the goal and what done looks like needs no
  question round: restate done in one line and go to the plan. Otherwise
  open with ONE batched round aimed at the real gaps - scope, constraints,
  what done looks like - ask what you need, no fixed minimum, and wait for
  answers.
- No `codex-write=` line in `.fabstra/RUN*.md` for this folder -> run the Codex write probe (transport.md) now, before tagging owners; write its line into RUN.md when the logbook is created.
- Write a short plan: numbered tasks, each sized so one subagent can finish
  it without asking questions, each tagged with its tier from the rubric,
  each with acceptance criteria - the reviewers will grade against these.
- Group a real build's tasks into waves of 3-4 parallel builders, with any
  contract task alone in wave 0 (fanout.md, "Build waves").
- Decide now which of three build classes this run is: a **real build**
  (multi-file, anything a user or client will run, anything whose failure
  costs more than a review), a **contained change**, or a **small change**.
  A small change is trivial single-file, low-stakes work: the user called it
  so, or nothing a user or client runs depends on it. A contained change
  meets ALL of: (1) touches at most 3 files; (2) follows a pattern that
  already exists in the repo, cited file:line in the plan; (3) an existing
  test, or a runnable check the plan names, proves it; (4) not an excluded
  category (money, auth, PII or de-identification, permissions, data
  migration, concurrency, a client-facing release); (5) no architecture or
  data-model decision; (6) no new or changed user-facing surface (that keeps
  the design-pass path). Any doubt -> real build. Real builds get Phase 1b
  and Phase 3; a contained change skips Phase 1b and the `/goal` hand-off
  and gets one Phase 3 review; small changes skip both. Write the class in
  the plan and in the report, with why; never skip silently. A small change
  is still built by a subagent - one Agent call, `model: "haiku"` (or
  `"sonnet"` when it needs judgement, or `model-router:sonnet-max` under a
  Sonnet max pin), no gates; you never make the edit
  yourself.
- A contained change: before building, in both modes, write its plan into
  RUN.md - the task, the six criteria with the pattern citation file:line,
  the verification command, the acceptance criteria; the review spec carries
  that RUN.md plan verbatim in place of the authoritative plan file. Then
  (Orchestrate mode) one builder delegation by tier, or (Lead mode) the lead
  builds it per lead-mode.md's rubric row (routing rubric; Codex side: Sol parents it
  at the routing rubric's tier, same transport as the Sol row), the smoke
  gate as for a real build, then
  exactly one review - Claude-built -> Sol at `--effort high` through the
  Sol review command (transport.md, same transport as the Sol row, only the
  effort differs); Codex-built -> a fresh Fable (`model-router:reviewer`),
  per the pairing rule. No parallel second reviewer. Phase 4 rules apply
  unchanged. A P1 in the review, or the change growing past any criterion
  mid-run, makes it a real build from that point: log the reclassification
  in RUN.md, and the re-review follows the real-build rules. RUN.md still
  gets a short entry: the brief, `class=contained` with the criteria that
  qualified it, the task line, smoke result, review verdict.
- Self-review the plan before showing it: every brief requirement maps to a
  task; no placeholder language ("TBD", "handle errors appropriately" - that
  is a decision you have not made yet); file paths and interface names
  consistent across tasks; parallel tasks genuinely disjoint; every wave
  below 3 wide has its reason written. Paper is the
  cheapest place to fix a plan.
- Show the plan in one screen or less. Get a go signal, then create the
  logbook, then read what the specs depend on (rule 3) and write every
  builder spec (Phase 2 format). The specs are what the gate seat (Astra or Sol, gate seat rubric in SKILL.md) reviews next. That is Lane A. In Lane B write the brief instead (Lane B,
  part 1); Astra's design file is what the reviewers grade against, and no
  blueprint is written.

## Arbitrate the design review (Phase 1b)

**Arbitrate the design review (you):** every finding gets a verdict in the
logbook. Accepted -> revise that blueprint (and any sibling it touches),
then re-run your plan self-review on the changed parts. Rejected -> one-line
reason. A P1 you reject needs a reason you would defend to the user. Do not
send the plan back to the gate seat for a second design pass unless a P1 changed the
shape of two or more tasks; one design review per run is the budget.

Then hand the user ONE line to paste: `/goal <the revised plan's acceptance
criteria as one measurable end state, the check that proves it (build and
test commands exit 0, a smoke-gate PASS line in .fabstra/RUN.md,
.fabstra/REPORT.md written), and "or stop after N turns">`, so that a fresh
evaluator, not you, decides when the run is done; in a headless run skip
the hand-off (the launch prompt already carries the goal).

## Phase 2 - status handling, task sizing, smoke gate

Read the status with `jev report --file <report>` (exit 0 DONE, 1 DONE_WITH_CONCERNS, 2 NEEDS_CONTEXT, 3 BLOCKED, 4 UNCLEAR, 5 skipped for privacy - read an UNCLEAR report yourself). The line also carries `weakened_test` and `verification`: a DONE report with weakened_test=yes or verification below `partial` is verified with slices before it is accepted, and the reason is logged. Status responses: DONE -> verify with slices. DONE_WITH_CONCERNS -> verify,
judge the concern, log it if unresolved. NEEDS_CONTEXT -> answer the
question in a REVISED spec - never resend the same spec unchanged. BLOCKED
-> re-diagnose yourself before re-routing, and spot-check the claim first
(builders misreport failure as well as success).

Task sizing: a feature and its own test belong in ONE task - the builder
then runs the test as its verification. Split into parallel tasks only work
that is genuinely disjoint: different files, no run-time dependency.

When the reports land, verify them in ONE batched Bash call of targeted
slices (`ls`, `grep -c` for acceptance markers, `head` slices). Misses go
back to the same tier - or one tier up on the second miss - with the
evidence attached.

**Smoke gate:** when every task has landed (DONE, or DONE_WITH_CONCERNS
whose concern you judged acceptable and logged), run the project's real
build and test suite ONCE (one Bash call) where the plan states they are
local and isolated and says how that was checked; otherwise run only the
read-only checks and log that the real suite needs the user's approval. A change a user or client sees also runs the project's recorded run recipe (`.claude/skills/run-<name>/SKILL.md`, invoked by its own name or through the bundled `run` skill) against the running app, and the report cites what was observed there, not only the test line; no recipe in the folder -> log it and name it as a follow-up. Self-checks pass in isolation while
the merge breaks - the documented failure mode of parallel builds. A broken
smoke gate means fix delegations now: a reviewer is too expensive to spend
discovering what a build command finds for free. Log the result.

## Phase 4 - FIX AND SHIP (you arbitrate)

- Arbitrate every finding yourself: real -> route a fix delegation (finding
  verbatim, plus the relevant spec, starting with a failing repro test) to
  the builder tier; a design error means you correct the blueprint first,
  and the delegation carries the corrected blueprint rather than a patch
  hint; wrong -> record it as rejected with a one-line reason in the
  logbook. You do not fix code yourself, not even one line.
- Fix tiers, two columns; pick the Codex column by default to keep Claude
  usage down, the Claude column when Codex is blocked or the fix needs
  something only the Claude harness has (a plugin skill, an MCP tool, this
  project's CLAUDE.md in context):

  | Fix looks like | Claude subagent | Codex side (the gate seat as parent, `--write`; a Sol parent does the Opus-tier row itself) |
  |---|---|---|
  | Mechanical: rename, config, doc, one obvious line | Haiku (`model: "haiku"`) in one file; across 2+ files Opus 5.5 low (`subagent_type: "model-router:builder-low"`) | Astra delegating to `spark` (native on Pro) or `luna` (proxy) |
  | Contained, with a written contract: one function, one test, one component | Sonnet (`model: "sonnet"`; `model-router:sonnet-max` under a Sonnet max pin, routing rubric) | Astra delegating to `terra` |
  | Multi-file, design-level, or the reviewer disagreed with the approach | Opus 5.5 (`subagent_type: "model-router:builder"` or `"model-router:builder-medium"` - the arm the effort-trial rule gives this task; excluded work always `builder`) | the gate seat delegating by tier (Astra to `sol`; Sol does it itself) (agent-file xhigh), or Astra itself at the pinned effort (else xhigh) |

- After each fix round, recount open findings in the logbook. Count did not
  go down? The approach is wrong - stop immediately and escalate to Opus
  with the full history; do not spend another round on the same theory.
  Two rounds on the same finding is the hard ceiling either way.
- Re-run the reviewer when fixes touched more than one file or resolved any
  P1 - the same reviewer seat the pairing rule gave the build, unless the
  fixes moved the build across the pairing line (Codex-column fixes on a
  Claude build -> Reviewer C for the re-review). For smaller point fixes,
  verify the specific finding yourself with targeted slices.
- Re-run the smoke gate (the same command set the first gate used, under the
  same isolation condition, one Bash call) after EVERY fix round that changed code, whether or not a re-review
  follows; individually verified fixes are where integration regressions
  hide, and the reviewer is not the smoke gate. Log the result.
- Report briefly, for a reader who did not watch the run. Open with what
  needs the user: decisions left open, approvals, commands only the user can
  run (commits, pushes, uploads). Then what shipped, how
  it was verified, design
  review verdict (findings accepted/rejected), review verdict with findings
  fixed/rejected, which reviewer seats ran and why, anything left open.
  Research or audit claims mark what could not be confirmed and say where
  the lead looked.
