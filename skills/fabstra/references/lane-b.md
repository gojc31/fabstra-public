# FabStra Lane B - Astra solo

Contents: Lane B - Astra solo (one section: fan-out; 1 brief; 2 launch; Astra quota spent; 3 smoke gate; 4 review; 5 fix rounds and agreement; 6 report and log)

Reached from: fabstra SKILL.md - "astra solo", "let Astra design and build", or a count of Astras

Related:
> The transport and the crew table are in transport.md; quota fallbacks are in quota.md.
> the Phase 3 proxy command with -> transport.md
> the same Phase 3 review spec -> specs.md
> (rule 3: context budget, not read caps) -> the root SKILL.md
> (rule 2: specs carry the decisions that must not drift) -> the root SKILL.md
## Lane B - Astra solo (Astra designs and builds, Sol and Fable review)

Use this lane only when the user named Astra as the builder (Phase 1 lane
choice). Astra owns the design; you own the brief, the smoke gate, the
review, the arbitration, the logbook, and the report. Fable still never
writes code. Lane A's Phase 1b is skipped here on purpose: Astra's design
is the design review, and one Astra session costs less than two. Lane B's
only transport is the proxy: the part-2 launch command and the Phase 3 proxy
review command. Never the Codex transport, never `CODEX_DIRECT=1` or the
`codex-pro` shim, whatever the Lane A fallback text or the routing policy
in transport.md says. Nothing listening on 8317: run
`powershell -NoProfile -File '$MODEL_ROUTER_HOME/scripts/start-proxy.ps1 (start-proxy.sh on Mac/Linux)'` (it exits 1 naming the port and exe when it cannot start), retry once, then stop
and tell the user - there is no other door in this lane. The fast pin has no
effect here (proxy transport): log "fast requested, no effect in Lane B" and
say so in the report rather than switching lanes for it.

**Fan-out - "spawn 3 astra subagents", "a few astras on this", "astra x3".**
The user gives a goal and a count and never writes a brief; you turn the
count into N briefs. Slice the goal into disjoint pieces - disjoint means no
two slices edit the same file or interface. Where two pieces overlap, merge
them into one slice, or run the second after the first lands with its diff
cited in the brief. Fewer slices than the count asked for is the normal
outcome; the report names the seam that forced it. Each slice is a full
part-1 brief with its own `<name>` and design file and without the delegation
clause: every Astra works alone, so each launch drops `Agent` and the three
`ANTHROPIC_DEFAULT_*_MODEL` variables. Effort xhigh; a user effort word pins
as always (never below xhigh on an excluded-category build), and `max` or `ultra` is logged with its token count, because
either costs several times more per slice and `ultra` spawns children on its
own. At most 3 launches in flight, one background Bash call each per part 2;
the rest queue and start as slots free. Smoke-gate each slice as it lands
(part 3), then run one review round (part 4) over the merged result with
every slice's design file in `<context>`, findings tagged by slice in the
ledger; a fix round (part 5) goes to that slice's own builder session.
Budget: a solo xhigh Astra slice ran 2-3M input tokens on 2026-09-05, so
three slices cost about one `max` run with children.

**1. The brief (you write it, `<scratch>/astra-solo-<name>.md`).** A brief,
not a blueprint - state the problem and the contract, leave the structure to
Astra. It contains, in order: the goal in two lines; what done looks like as
numbered, testable acceptance criteria; the stack and every hard rule not
already in the project's CLAUDE.md (CLAUDE.md itself loads - see the command);
the files and areas in scope and what not to touch; the nearest existing
pattern to match, cited file:line from your own reads (rule 2); the
test command; this contract, verbatim; and last the "What I will check"
line. The contract carries the GPT-6.2 rules that bind a builder (specs.md,
"GPT-6.2 seats - prompting rules": rules b, e, f, g, i, worded as specs.md's
Codex-side lines) because the brief is sent as-is:
"You own the design. If this brief carries a `## Design (from design-pass)`
block, that block is settled visual direction from Claude Opus 5.5, the
user's design lead (2026-09-23): design and build to it; do not redesign it.
Before writing any code, write it down at
`.fabstra/DESIGN-<name>.md` in the project: structure (files, functions,
signatures, call sites), data shapes, the logic decisions for every edge
case, error path, empty state, retry and idempotency question, and how each
acceptance criterion is verified, including at least one negative case.
Then implement it. Preserve the behavior existing callers rely on. The
acceptance criteria and the test command this brief names are the tests it
requests; beyond them, add a new test only when the repository requires it
or one is needed to catch a specific regression the existing tests would
miss. Write readable code: fewer lines, short names, minified formatting or
dense one-liners are not substitutes for simplicity. Avoid unnecessary
indirection and abstraction. Do not end your turn on a suggested next step,
a plan, or a question about a routine decision when an authorized next step
exists: take it within this brief's scope and list every assumption you made
in the design file. Stop only for a significant scope change, a concrete
block, a decision the user must make, or an irreversible or destructive
action; this brief stands in for the user, so report those as NEEDS_CONTEXT
or BLOCKED, and a brief that contradicts the repository as NEEDS_CONTEXT. You
are done when every acceptance criterion passes and the test command is
green, not at a first implementation. A pre-existing
bug or an unrequested extension goes in your report as a follow-up, not in
the change. The checks that judge the build (the tests the brief names,
lint, type and CI configuration, hooks, REVIEW.md) stay as they are unless
the brief names them. A flaky test gets its root cause fixed; retrying,
sleeping or skipping hides the failure, so one you cannot fix stays in place
and goes in your report. This machine is shared: consider how many builds or
tests run at once and leave CPU and memory for other work. Before your
report, stop every background command you started and remove the temporary
files you created. End the report with exactly one status: DONE
/ DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED - plus changed paths, the
verification commands you ran this session, and the tail of their output,
and one line reading exactly `delegation: none` or `delegation: <N> Agent
calls succeeded`. Write the report self-contained and anew for the
orchestrator who reads it, with no shorthand carried over from your
reasoning, tool calls or sub-agent messages."
Then end the brief with the "What I will check" line (rule a), filled in:
`What I will check: <the acceptance criteria by name, what counts as finished, and where the review will be exhaustive - the callers, invariants and bug classes it tests first>.`
The report format is the status, paths, verification and delegation lines
above; it has no line cap (GPT-6.2 writes concisely by default, and a cap
works against a self-contained report, rules g and h). Any further working
or completion rule goes in specs.md, "GPT-6.2 seats - prompting rules", not
in this template.
A user-facing surface in the task: get the `## Design (from design-pass)`
block from `model-router:designer` first (client briefs as given, client-E
included - JC 2026-10-31) and paste the block into the brief.
Optional delegation clause, add it only when the task has genuinely disjoint
slices: "The Agent tool is available; on this session `model: "opus"`,
`"sonnet"` and `"haiku"` all resolve to GPT-6.2 Sol. Delegate only
disjoint slices, pass each its slice of your design file verbatim, and
verify their work yourself. Every Agent call passes `effort: "xhigh"`. Before every Agent call append one line - ISO
time, model, slice - to `.fabstra/DELEGATION-<name>.log`; that log is the
provenance record if this session is cut off. If an Agent call errors,
continue solo." The lead writes the brief's effort word in place of xhigh
when the user pinned one (never below xhigh on an excluded-category build). Mark it
UNVERIFIED in the logbook the first time it runs (the haiku mapping rides
`--settings` because `~/.claude/settings.json` pins
`ANTHROPIC_DEFAULT_HAIKU_MODEL=claude-haiku-5-5` and user-settings env beats
a shell variable - verified 2026-10-08 on CLI 2.1.289; a `--settings` flag
beats user settings): Agent-tool delegation
through the proxy has not been exercised as of 2026-09-05. A successful
delegation puts Sol-authored code in the build, which changes the reviewer
seat (part 4). A Sol child inherits the Astra session's environment, so it
runs with Astra's 272k window (`CLAUDE_CODE_MAX_CONTEXT_TOKENS=272000`), not
Sol's 500k (transport.md, Model pins): accepted for a slice; a slice that
needs Sol's own window is not delegated.

**2. Launch (one Bash call, `run_in_background: true`, timeout 3400000 (above the child's `timeout 3300`; see transport.md, design call), cwd =
the project directory).** Run `proxy-pin status` and note it in the logbook;
the standing pin is `both` and this lane never changes it.
Before the launch, a non-git project copies its judging checks (the tests and
fixtures, lint, type and CI configuration, hooks) and REVIEW.md to
`<scratch>/fabstra-prebuild/`: the base for part 3's judging-checks diff and
part 4's reviewer diff.
If it reads `team`, log that and continue - every login except the Pro one
still serves Astra. Then:

```bash
KEY=$(proxy-key) || exit 1
CLAUDE_CODE_MAX_CONTEXT_TOKENS=272000 ANTHROPIC_BASE_URL=http://127.0.0.1:8317 ANTHROPIC_AUTH_TOKEN="$KEY" ANTHROPIC_DEFAULT_OPUS_MODEL=gpt-6.2-sol ANTHROPIC_DEFAULT_SONNET_MODEL=gpt-6.2-sol ANTHROPIC_DEFAULT_HAIKU_MODEL=gpt-6.2-sol timeout 3300 claude -p --model gpt-6.2-astra --settings '{"env":{"ANTHROPIC_DEFAULT_HAIKU_MODEL":"gpt-6.2-sol"}}' --effort xhigh --max-turns 200 --permission-mode acceptEdits --allowedTools "Read,Grep,Glob,Edit,Write,MultiEdit,Bash,Agent,Skill,TodoWrite" --output-format json < <scratch>/astra-solo-<name>.md > <scratch>/astra-solo-<name>.md.out 2>&1
```

`CLAUDE_CODE_MAX_CONTEXT_TOKENS=272000` pins GPT-6.2 Astra's Codex window
(transport.md, Model pins). A cooling or model-rejected seat hops by the hop
rules there; this lane's only home is the router (the proxy), so each
model's pairs are its 6.2 id and its fallback pin there. An Astra builder
rejected on every pair is handled like "Astra quota spent" below (Sol builds
solo, logged "Sol built solo, Astra rejected on every pair"). Reviewer S
takes its own fallback pin (hop rule 2) but never hops to Astra (Astra never
reviews its own build) and never enters the "Reviewer fallback" table: a Sol
that is cooling, or rejected on every pair, leaves Reviewer S unavailable
(part 4).

No `--bare`: the project's CLAUDE.md chain, skills, and hooks load exactly
as they do for a Claude session, which is the point of building in this
harness. Add `--strict-mcp-config` when the task needs no MCP server; it
skips every configured server and cuts startup time. Keep `Agent` in `--allowedTools`, and the three `ANTHROPIC_DEFAULT_*_MODEL` variables, only when the brief carries the delegation clause; otherwise drop both from the command, so an uninvited delegation cannot happen. The variables exist only so an Agent call inside the session resolves to Sol instead of a Claude id the proxy cannot serve; they apply to this call alone. Those Agent calls carry an explicit `effort` (the delegation clause) rather than rely on inheritance. Effort: xhigh for builds; `max` only for a final
review - on 2026-09-05 a max-effort Astra build spent its first ten minutes
reading every test file. A user effort word in the brief pins this call like
any other, except that an excluded-category build stays at xhigh. `--output-format json` with the spec fed on stdin (`< spec.md`,
so stdin reaches EOF) is what stops the nested `claude -p` from hanging
after it prints; the spec is not a command-line argument, so its length
is not capped (a 40 KB spec has passed); the report is
the `result` field of the last JSON line in the `.out` file. If the 3300 s timeout ends the run, the files Astra wrote are still on disk:
read `.fabstra/DESIGN-<name>.md` and the working tree, then relaunch with a
brief that says "continue from the design file; do not redesign" - never
relaunch the original brief blind. Before relaunching, read
`.fabstra/DELEGATION-<name>.log`: any line means Sol-authored code is in the
build; if `Agent` was in that launch's `--allowedTools` and the log cannot be read, treat it the same. Write `delegation: <N> Agent calls in a prior session` into the continuation brief - or `delegation: unknown (log unreadable), treat as delegated` when the count cannot be established - so the next report carries it forward;
the active reviewer set (part 4) then shrinks to Reviewer C. At most two
continuation launches per run (three sessions in all): a third timeout stops
the run - log the design file and the working tree state and escalate to
the user; continuations do not consume review rounds, which is why they
need their own ceiling. Write the next spec or the review skeleton while
Astra works; never leave the run in flight when the session ends.

**Astra quota spent** (429 "cooling down" or "usage_limit_reached", per the
"how to read it" list in quota.md). Before any code landed: the same command
with `--model gpt-6.2-sol`, the same `--effort` and `CLAUDE_CODE_MAX_CONTEXT_TOKENS=500000` in place of 272000 in the env prefix (a hop: transport.md, Model pins) - Sol builds solo in the same
lane - logged "Sol built solo, Astra quota spent". Mid-build: Sol continues
from the design file with the continuation brief ("continue from
`.fabstra/DESIGN-<name>.md`; do not redesign"), same log line - never the
original brief. Once Astra is out it stays out for this run: every later fix
round goes to Sol the same way. In both cases the review is a single fresh Fable (Reviewer C) - Sol never reviews
Sol - and the report says consensus was reduced to one reviewer because Sol
built. Sol cooling down on every login as
well: no model swap supplies capacity, because Astra and Sol draw on the
same per-account windows - stop, log it, and tell the user when the windows
reset (each account's `chatgpt.com/backend-api/codex/usage` gives the time).

**3. Smoke gate (you).** When the report lands, verify it in one batched Bash
call of targeted slices (rule 3: context budget), confirm
`.fabstra/DESIGN-<name>.md` exists and names every changed file, then run
the project's real build and test suite once, plus phases.md "Phase 2"
smoke gate's app check (the verify skill, else the run recipe, and the
verify-skill offer when none exists) and its judging-checks diff. A broken gate goes back to
the solo builder (Astra, or Sol once Astra is out) as a fix round (part 5),
not to the reviewer.

**4. Review - two reviewers, the lead rules on every finding.** The ACTIVE REVIEWER SET is
normally two seats, run in parallel on the same build with the same Phase 3
review spec: Reviewer S, Sol at xhigh through the proxy (the Phase 3 proxy
command with `--model gpt-6.2-sol --effort xhigh` and its 500000 context
variable; ledger ids `S<n>`; named S, not B, because Reviewer B is the
cooldown seat after a Claude build, transport.md), and Reviewer C, a fresh
Fable 5.2 at high (one Agent tool call, `subagent_type: "model-router:reviewer"` at `effort: "high"`, or `effort: "xhigh"` on a build in an excluded category,
the spec verbatim). Launch both in the same message. Give each seat its own
findings file: substitute `fabstra-review-findings-sol.md` and
`fabstra-review-findings-fable.md` for the spec's `fabstra-review-findings.md`
so parallel saves never overwrite each other. Front-load each spec's
`<context>` block with the diff (`git diff <base>` plus every untracked
file's contents; a non-git project: the diff against `<scratch>/fabstra-prebuild/`
for the files copied there (part 2) plus the full text of every other changed file) and the full text
of `.fabstra/DESIGN-<name>.md`, so both grade the code against the design
the builder committed to. Neither reviewer sees the other's report. Astra
never reviews its own solo build; Astra's reviewer seat is for Lane A only.
The set shrinks to Reviewer C alone - logged "consensus reduced to one
reviewer" - when Sol built or continued the build under the quota rule, or
when `.fabstra/DELEGATION-<name>.log` has any line or the report's
delegation line says any Agent call succeeded: Sol never reviews
Sol-authored code. When Sol is unavailable for Reviewer S (cooling, or
rejected on every pair: transport.md, hop rules), log Reviewer S
"unavailable (Sol <reason>)" and run the round with the single Reviewer C
already in the set, plus Reviewer G; no second fresh Fable is launched, and
the report says consensus was reduced to one reviewer because Sol was
unavailable. Wherever parts 5 and 6 say "the reviewers" or "the active
set", they mean this set as it stands, recomputed after every round: the
rebuttal re-check and the re-review apply to the reviewers that actually
ran. Two
reviewers cost twice the review time and quota; that is the user's choice
(2026-09-05) for this lane, do not skip one to save time. Log the seats,
their durations, and why any seat was skipped. In every round, launch
Reviewer G (Carbon; pro-consult.md, "Reviewer G") in the same message as
Reviewers S and C; it sits outside the active set, its rows are `G<n>`
findings ruled like S's and C's once you confirm each against the code (an
unconfirmed one is WITHDRAWN with one line; a confirmed one is tagged `G`,
part 5), and a skipped or failed launch never blocks.

**5. Fix rounds and agreement (the solo builder fixes its own design).** The
SOLO BUILDER is Astra, or Sol once Astra is out under the quota rule. The
logbook's findings ledger - not any model's report - is the record of
agreement. (a) Merge: collapse duplicates (same file and defect), tag every
finding by source - S, C, `G` (a Reviewer G `G<n>` row you confirmed;
pro-consult.md, "Reviewer G"), or a combination such as S+C or
S+G - and enter each in the ledger as OPEN. Do not
pre-filter: the lead may WITHDRAW a finding at any stage with one logged line of reason; unanimity is not required. (b) Send
every open finding to the solo builder, verbatim, tagged, and with its bug class, in a new brief:
"these findings are against your design at `.fabstra/DESIGN-<name>.md`;
answer each one FIXED (with the verification you ran) or REBUTTED (with
evidence); for each finding's bug class, grep the build's files and fix
every instance, listing each one; keep the design file current; report the same way", launched
with the part-2 command (a new session - the findings live in the brief).
The builder may not drop a finding silently: an unanswered finding is
REBUTTED without evidence and stays OPEN. (c) Close the ledger: FIXED stays
OPEN until the re-review in (e) confirms it, then FIXED. REBUTTED on an S+C
finding is real unless the rebuttal shows a fact both reviewers got wrong -
you rule and log why: WITHDRAWN ("ruled by orchestrator") or OPEN for the
next brief. REBUTTED on a single-source S or C finding earns one re-check: send the finding, the rebuttal, and its evidence to the reviewer that raised it - or, if that seat has since left the active set (Sol, once Sol built or continued the build or a delegation landed, or while Sol is unavailable, part 4), to the fresh Fable in its place - on that seat's own transport, read-only, asking for WITHDRAWN or HELD with a reason; WITHDRAWN closes it; HELD means you rule and log why: WITHDRAWN or
OPEN. A combined S+G or C+G finding is re-checked by its S or C seat the
same way; an S+C+G finding is ruled like S+C. REBUTTED on a `G`-only finding
has no reviewer to re-check it: you rule on your own re-check of the
evidence, with one logged line - WITHDRAWN or OPEN. Its FIXED is confirmed
by the active set's re-review in (e), as for every finding. Each finding gets at most one re-check and at most two fix briefs;
after that it is ESCALATED - it goes to the user with each party's
position. You never edit a builder's report: withdrawals live in the
ledger, and the next fix brief lists them under "withdrawn, no action" so
the builder's next report can carry them. (d) A Claude builder takes a fix
only when it needs something the solo session cannot reach (a plugin skill
with `disable-model-invocation`, a Claude-only MCP tool); log it. It is
re-reviewed like any other change, by the active set - Sol reviewing
Claude-written code is a cross-family check, so the set does not shrink for
it. (e) Re-run the smoke gate after every code-changing round, then re-run
the ACTIVE REVIEWER SET (part 4, recomputed) on the changed files; each seat's spec carries `<prior_findings>` from this ledger under the round rules, ledger transitions and PRE-EXISTING routing of phases.md "Phase 4", and its `VERIFIED FIXED: <id>` lines are the confirmation (c) and (f) wait for. Reviewer G runs in each re-review (part 4); its rows never confirm a fix. A code-changing round with no re-review gets the Hydrogen fix check instead, once its smoke gate passes (pro-consult.md; snapshot before the fix brief launches). (f) SHIP GATE = the lead's verdict: the ledger shows every finding FIXED (confirmed by the re-review), WITHDRAWN (by the lead, one logged line), or ESCALATED to the user; every seat of the active set still runs (both, unless part 4 reduced it to Reviewer C), and every code-changing round is still re-reviewed by the active set. A taste-only finding against the Design block is WITHDRAWN by the
orchestrator with one line (the arbitration rule in phases.md) and never goes
back to the solo builder; a feasibility finding against it is handled like
any other. An ESCALATED finding blocks shipping until the user rules.
Nothing ships without this gate. Ceilings: findings count not dropping
means the design is wrong - stop and escalate with the full history; two
fix rounds after the initial review is the hard ceiling, after which every
still-open item is ESCALATED.

**6. Report and log.** The report names the lane, the builder model
and effort, the smoke-gate result, both reviewer seats and their durations
(or why one was skipped), agreement reached yes/no, findings by source (S,
C, `G`, or a combination such as S+C or S+G) with each marked FIXED, WITHDRAWN, or ESCALATED, whether the proxy pin
was restored, and anything open. The commit stamp and the REVIEW.md rule
proposals of phases.md "Phase 4" apply to Lane B as written there.

