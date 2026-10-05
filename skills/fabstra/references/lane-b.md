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
IS the design review, and one Astra session costs less than two. Lane B's
only transport is the proxy: the part-2 launch command and the Phase 3 proxy
review command. Never the Codex transport, never `CODEX_DIRECT=1` or the
`codex-pro` shim, whatever the Lane A fallback text or the routing policy
in transport.md says. Nothing listening on 8317: run
`$MODEL_ROUTER_HOME/scripts/start-proxy.ps1 (start-proxy.sh on Mac/Linux)`, retry once, then stop
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
part-1 brief with its own `<name>` and design file and WITHOUT the delegation
clause: every Astra works alone, so each launch drops `Agent` and the three
`ANTHROPIC_DEFAULT_*_MODEL` variables. Effort xhigh; a user effort word pins
as always, and `max` or `ultra` is logged with its token count, because
either costs several times more per slice and `ultra` spawns children on its
own. At most 3 launches in flight, one background Bash call each per part 2;
the rest queue and start as slots free. Smoke-gate each slice as it lands
(part 3), then run ONE review round (part 4) over the merged result with
every slice's design file in `<context>`, findings tagged by slice in the
ledger; a fix round (part 5) goes to that slice's own builder session.
Budget: a solo xhigh Astra slice ran 2-3M input tokens on 2026-09-05, so
three slices cost about one `max` run with children.

**1. The brief (you write it, `<scratch>/astra-solo-<name>.md`).** A brief,
not a blueprint - state the problem and the contract, leave the structure to
Astra. It contains, in order: the goal in two lines; what done looks like as
numbered, testable acceptance criteria; the stack and every hard rule NOT
already in the project's CLAUDE.md (CLAUDE.md itself loads - see the command);
the files and areas in scope and what NOT to touch; the nearest existing
pattern to match, cited file:line from your own reads (rule 2); the
test command; and this contract, verbatim:
"You own the design. If this brief carries a `## Design (from design-pass)`
block, that block is settled visual direction from Claude Opus 5.5, the
user's design lead (2026-09-23): design and build to it; do not redesign it.
Before writing any code, write it down at
`.fabstra/DESIGN-<name>.md` in the project: structure (files, functions,
signatures, call sites), data shapes, the logic decisions for every edge
case, error path, empty state, retry and idempotency question, and the exact
test cases including at least one negative case. Then implement it: test
first, run it to see it fail, implement until it passes. Do not ask
questions - decide, and list every assumption in the design file. Return
NEEDS_CONTEXT only when the brief contradicts the repository. A pre-existing
bug or an unrequested extension goes in your report as a follow-up, not in
the change. Report in 8 lines or fewer, ending with exactly one status: DONE
/ DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED - plus changed paths, the
verification commands you ran this session, and the tail of their output,
and one line reading exactly `delegation: none` or `delegation: <N> Agent
calls succeeded`."
A user-facing surface in the task: get the `## Design (from design-pass)`
block from `model-router:designer` first (run `airlock` before it for client-E
client work only) and paste the block into the brief.
Optional delegation clause, add it only when the task has genuinely disjoint
slices: "The Agent tool is available; on this session `model: "opus"`,
`"sonnet"` and `"haiku"` all resolve to GPT-6.1 Sol. Delegate only
disjoint slices, pass each its slice of your design file verbatim, and
verify their work yourself. Before EVERY Agent call append one line - ISO
time, model, slice - to `.fabstra/DELEGATION-<name>.log`; that log is the
provenance record if this session is cut off. If an Agent call errors,
continue solo." Mark it
UNVERIFIED in the logbook the first time it runs: Agent-tool delegation
through the proxy has not been exercised as of 2026-09-05. A successful
delegation puts Sol-authored code in the build, which changes the reviewer
seat (part 4).

**2. Launch (ONE Bash call, `run_in_background: true`, timeout 3400000 (above the child's `timeout 3300`; see transport.md, design call), cwd =
the project directory).** Run `proxy-pin status` and note it in the logbook;
the standing pin is `both` and this lane never changes it.
If it reads `team`, log that and continue - every login except the Pro one
still serves Astra. Then:

```bash
KEY="${MODEL_ROUTER_KEY:-$(proxy-key)}"
ANTHROPIC_BASE_URL=http://127.0.0.1:8317 ANTHROPIC_AUTH_TOKEN="$KEY" ANTHROPIC_DEFAULT_OPUS_MODEL=gpt-6.1-sol ANTHROPIC_DEFAULT_SONNET_MODEL=gpt-6.1-sol ANTHROPIC_DEFAULT_HAIKU_MODEL=gpt-6.1-sol timeout 3300 claude -p --model gpt-6-astra --effort xhigh --max-turns 200 --permission-mode acceptEdits --allowedTools "Read,Grep,Glob,Edit,Write,MultiEdit,Bash,Agent,Skill,TodoWrite" --output-format json < <scratch>/astra-solo-<name>.md > <scratch>/astra-solo-<name>.md.out 2>&1
```

No `--bare`: the project's CLAUDE.md chain, skills, and hooks load exactly
as they do for a Claude session, which is the point of building in this
harness. Add `--strict-mcp-config` when the task needs no MCP server; it
skips every configured server and cuts startup time. Keep `Agent` in `--allowedTools`, and the three `ANTHROPIC_DEFAULT_*_MODEL` variables, ONLY when the brief carries the delegation clause; otherwise drop both from the command, so an uninvited delegation cannot happen. The variables exist only so an Agent call inside the session resolves to Sol instead of a Claude id the proxy cannot serve; they apply to this call alone. Effort: xhigh for builds; `max` only for a final
review - on 2026-09-05 a max-effort Astra build spent its first ten minutes
reading every test file. A user effort word in the brief pins this call like
any other. `--output-format json` with the spec fed on stdin (`< spec.md`,
so stdin reaches EOF) is what stops the nested `claude -p` from hanging
after it prints; the spec is not a command-line argument, so its length
is not capped (a 40 KB spec has passed); the report is
the `result` field of the last JSON line in the `.out` file. If the 3300 s timeout ends the run, the files Astra wrote are still on disk:
read `.fabstra/DESIGN-<name>.md` and the working tree, then relaunch with a
brief that says "continue from the design file; do not redesign" - never
relaunch the original brief blind. Before relaunching, read
`.fabstra/DELEGATION-<name>.log`: any line means Sol-authored code is in the
build; if `Agent` was in that launch's `--allowedTools` and the log cannot be read, treat it the same. Write `delegation: <N> Agent calls in a prior session` into the continuation brief - or `delegation: unknown (log unreadable), treat as delegated` when the count cannot be established - so the next report carries it forward;
the active reviewer set (part 4) then shrinks to Reviewer C. At most TWO
continuation launches per run (three sessions in all): a third timeout stops
the run - log the design file and the working tree state and escalate to
the user; continuations do not consume review rounds, which is why they
need their own ceiling. Write the next spec or the review skeleton while
Astra works; never leave the run in flight when the session ends.

**Astra quota spent** (429 "cooling down" or "usage_limit_reached", per the
"how to read it" list in quota.md). Before any code landed: the same command
with `--model gpt-6.1-sol --effort xhigh` - Sol builds solo in the same
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

**3. Smoke gate (you).** When the report lands, verify it in ONE batched Bash
call of targeted slices (rule 3: context budget), confirm
`.fabstra/DESIGN-<name>.md` exists and names every changed file, then run
the project's real build and test suite ONCE. A broken gate goes back to
the solo builder (Astra, or Sol once Astra is out) as a fix round (part 5),
not to the reviewer.

**4. Review - two reviewers, the lead rules on every finding.** The ACTIVE REVIEWER SET is
normally two seats, run IN PARALLEL on the same build with the same Phase 3
review spec: Reviewer B, Sol at xhigh through the proxy (the Phase 3 proxy
command with `--model gpt-6.1-sol --effort xhigh`), and Reviewer C, a fresh
Fable 5.1 (ONE Agent tool call, `subagent_type: "model-router:reviewer"`,
the spec verbatim). Launch both in the same message. Give each seat its own
findings file: substitute `fabstra-review-findings-sol.md` and
`fabstra-review-findings-fable.md` for the spec's `fabstra-review-findings.md`
so parallel saves never overwrite each other. Front-load each spec's
`<context>` block with the diff (`git diff <base>` plus every untracked
file's contents, or full file text for a non-git project) AND the full text
of `.fabstra/DESIGN-<name>.md`, so both grade the code against the design
the builder committed to. Neither reviewer sees the other's report. Astra
never reviews its own solo build; Astra's reviewer seat is for Lane A only.
The set shrinks to Reviewer C alone - logged "consensus reduced to one
reviewer" - when Sol built or continued the build under the quota rule, or
when `.fabstra/DELEGATION-<name>.log` has any line or the report's
delegation line says any Agent call succeeded: Sol never reviews
Sol-authored code. Wherever parts 5 and 6 say "the reviewers" or "the active
set", they mean this set as it stands, recomputed after every round. Two
reviewers cost twice the review time and quota; that is the user's choice
(2026-09-05) for this lane, do not skip one to save time. Log the seats,
their durations, and why any seat was skipped.

**5. Fix rounds and agreement (the solo builder fixes its own design).** The
SOLO BUILDER is Astra, or Sol once Astra is out under the quota rule. The
logbook's findings ledger - not any model's report - is the record of
agreement. (a) Merge: collapse duplicates (same file and defect), tag every
finding B, C, or B+C, and enter each in the ledger as OPEN. Do not
pre-filter: the lead may WITHDRAW a finding at any stage with one logged line of reason; unanimity is not required. (b) Send
EVERY open finding to the solo builder, verbatim and tagged, in a new brief:
"these findings are against your design at `.fabstra/DESIGN-<name>.md`;
answer each one FIXED (with the verification you ran) or REBUTTED (with
evidence); keep the design file current; report the same way", launched
with the part-2 command (a new session - the findings live in the brief).
The builder may not drop a finding silently: an unanswered finding is
REBUTTED without evidence and stays OPEN. (c) Close the ledger: FIXED stays
OPEN until the re-review in (e) confirms it, then FIXED. REBUTTED on a B+C
finding is real unless the rebuttal shows a fact both reviewers got wrong -
you rule and log why: WITHDRAWN ("ruled by orchestrator") or OPEN for the
next brief. REBUTTED on a single-source finding earns ONE re-check: send the finding, the rebuttal, and its evidence to the reviewer that raised it - or, if that seat has since left the active set (Sol, once Sol built or continued the build or a delegation landed), to the fresh Fable in its place - on that seat's own transport, read-only, asking for WITHDRAWN or HELD with a reason; WITHDRAWN closes it; HELD means you rule and log why: WITHDRAWN or
OPEN. Each finding gets at most one re-check and at most two fix briefs;
after that it is ESCALATED - it goes to the user with each party's
position. You never edit a builder's report: withdrawals live in the
ledger, and the next fix brief lists them under "withdrawn, no action" so
the builder's next report can carry them. (d) A Claude builder takes a fix
only when it needs something the solo session cannot reach (a plugin skill
with `disable-model-invocation`, a Claude-only MCP tool); log it. It is
re-reviewed like any other change, by the active set - Sol reviewing
Claude-written code is a cross-family check, so the set does not shrink for
it. (e) Re-run the smoke gate after EVERY code-changing round, then re-run
the ACTIVE REVIEWER SET (part 4, recomputed) on the changed files. (f) SHIP GATE = the lead's verdict: the ledger shows every finding FIXED (confirmed by the re-review), WITHDRAWN (by the lead, one logged line), or ESCALATED to the user; both reviewer seats still run, and every code-changing round is still re-reviewed by the active set. A taste-only finding against the Design block is WITHDRAWN by the
orchestrator with one line (the arbitration rule in phases.md) and never goes
back to the solo builder; a feasibility finding against it is handled like
any other. An ESCALATED finding blocks shipping until the user rules.
Nothing ships without this gate. Ceilings: findings count not dropping
means the design is wrong - stop and escalate with the full history; two
fix rounds after the initial review is the hard ceiling, after which every
still-open item is ESCALATED.

**6. Report and log.** The report names the lane, the builder model
and effort, the smoke-gate result, both reviewer seats and their durations
(or why one was skipped), agreement reached yes/no, findings by source (B,
C, B+C) with each marked FIXED, WITHDRAWN, or ESCALATED, whether the proxy pin
was restored, and anything open.

