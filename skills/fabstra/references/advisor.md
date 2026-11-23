# Advisor - Fable consult by default, the tool on opt-in

Reached from: SKILL.md References (every run, before each Claude seat), the global CLAUDE.md "Fable consult" section (the precedence rule), specs.md "Advisor block", phases.md "The run logbook" (the `advisor=` line, parking and the report), lead-mode-deltas.md (the senior seat), lane-d.md (headless seats)

## What it is

Claude Code's advisor tool (`/advisor <model>`, setting `advisorModel`, flag
`--advisor <model>`; experimental) lets a seat's model consult an
equal-or-higher Claude model mid-task. In fabstra terms it is a server-side
tool inside that seat's own turn: not a subagent, not a routing step, not a
review. Its replies are advice under Rule 6: checked against the spec and the
code, and the lead still rules. A seat that consults it starts no
orchestration flow, so the "delegated seats start no orchestration" rule
holds. It is not Pro consult (pro-consult.md), which is the lead's, sees only
a brief, and cannot read the repo.

## The run's line

Every run logs one line with the plan in RUN.md (JC 2026-11-12; default
flipped to off by JC 2026-11-20):

- `advisor=off` - the default; no word about it in the brief. The Fable
  consult on credits applies (below).
- `advisor=fable` - the brief says "advisor fable".
- `advisor=opus` - the brief says "advisor opus".
- `advisor=off (no advisor)` - the brief says "no advisor": neither the tool
  nor the consult.
- `advisor=off (cli below 2.1.321)` - an opt-in run whose switch-on fell back
  (below); the consult does not replace the tool there.

A logbook with no `advisor=` line (a run started before 1.13.0) counts as
`advisor=off`. An auto run is one logged `advisor=fable` or `advisor=opus`
(opt-in only since 2026-11-20); an opt-out run is one logged `advisor=off`
in any form. Review and experiment seats stay advisor-free on every run (Who
must not consult).

## Fable consult on credits (default)

`scripts/fable-consult.py` asks Fable 5.2 over the plain Messages API on the
pool's plan credits, not the subscription (JC 2026-11-20). It is a plain API
call, not Claude Code, so it works from VS Code too. Command shape:
`python $MODEL_ROUTER_HOME/scripts/fable-consult.py (maintainer's machine only - not shipped) (--brief "<question>" | --brief-file <path>) [--transcript <jsonl> | --session-id <id> | --no-transcript] [--files <path> ...] [--effort high] [--max-usd 2] [--pool pool|client-<slug>] [--out <file>] [--dry-run]`.
By default it attaches this session's transcript (condensed: tool results
trimmed to 2k/8k, thinking dropped). Exit 0 advice; 2 bad arguments or config, no
account, transcript not found, or a pre-flight bound over `--max-usd`
(nothing sent); 3 refusal, max_tokens or empty; 4 API, network, or every
account out of credit. Ledger rows are `"kind": "consult"` in fable-review's
ledger. A client's work bills `--pool client-<slug>`.

**Precedence** (JC 2026-11-20; the single statement of it):

1. Default (`advisor=off`): no subscription advisor tool. The consult
   checkpoints of the global CLAUDE.md "Fable consult" section apply to every
   top-level session, a FabStra lead included. FabStra's plan call (below)
   IS that section's "before committing to a plan" checkpoint, not an extra
   one.
2. "advisor fable" or "advisor opus" in the brief or from JC
   (`advisor=fable|opus`): the subscription tool at those checkpoints INSTEAD
   of the script, never both; the rest of this file runs it, switched on
   before the first checkpoint and off only after the last (Lifecycle). A
   default run never switches the tool on.
3. "no advisor" (`advisor=off (no advisor)`): neither.

A `fable-consult.py` call at a checkpoint that exits 0: weigh the advice under
Rule 6. Any non-zero exit (2, 3 or 4): log it, tell JC once in that reply,
carry on without it, and never switch the tool on as a substitute.

- **The lead's plan call.** An Opus 5.5 orchestrator or lead on a default run
  makes its one plan call (Lifecycle: after the plan and task split, before
  the gate) as `fable-consult.py --brief "<the plan question>" --files
  <scratch>/fabstra-plan-<name>.md` with the session transcript, and logs
  `consult-plan=yes` (a failed call: `consult-plan=failed (exit <n>)`). A
  Fable 5.2 lead skips it.
- **Builders.** A builder may call `fable-consult.py --no-transcript --files
  <the files it is deciding on> --brief "..."` at most twice - before
  settling the approach and before DONE - as the builder spec's consult block
  says (specs.md, "Advisor block"); the lead logs the count as `consults=<n>`.
- **Never.** Review, gate and grading seats never consult (Who must not
  consult).

## The switch

`python $MODEL_ROUTER_HOME/scripts/advisor-state.py` with `status
--project <dir>`, `on <fable|opus>` or `off`. Spell it with exactly that
prefix: JC's allow rule is `Bash(python
$MODEL_ROUTER_HOME/scripts/advisor-state.py *)`, and any other
spelling meets a permission prompt. `on` and `off` write `advisorModel` in
the user settings file (`~/.claude/settings.json`) only, keeping every other
byte; they cannot set or clear the project's `.claude/settings.json` or
`.claude/settings.local.json`. Exit codes: 0 ok, 1 backup not written
(nothing written), 2 bad model, 3 Fable refused below CLI 2.1.321, 4 settings
unreadable or invalid (nothing written), 5 write not confirmed (file left as
it is, backup named), 6 settings changed by another writer (nothing written).

Every status read in this file is
`python $MODEL_ROUTER_HOME/scripts/advisor-state.py status --project <the seat's project dir>`.
The effective state is that output's `effective=` line (local beats project
beats user, and `CLAUDE_CODE_DISABLE_ADVISOR_TOOL` set to a true value in the
lead's environment or a settings `env` block makes it `off`). A bare `status`
reads the user file only and never counts as a state check. Any
`*_advisorModel=invalid` line blocks: the lead records the status output in
RUN.md and asks JC.

`/advisor <model>` and `/advisor off` stay JC's manual override: they write
the same user setting, and the run reads whatever is effective at its next
status read.

## Lifecycle

An Opus 5.5 orchestrator or lead on an auto run makes one advisor call per
plan (a default run makes it through `fable-consult.py`, above): after drafting the plan and task split, before the plan goes to the
gate seat (JC 2026-11-16). It weighs the reply under Rule 6 and logs
`advisor-plan=yes` in RUN.md. A Fable orchestrator skips it, since a Fable 5.2
advisor adds nothing to a Fable 5.2 lead. Past that call the lead consults
only at the global checkpoints (Precedence above); the lead session holds it while it is on
(verified 2026-11-12). Only auto runs switch. An opt-out run never runs
`on` or `off` - not at a mismatch, not when it stops early, not when it
parks: the shared setting may belong to another live run.

An auto run logs two more lines beside its `advisor=` line and keeps them
current: `advisor-wrote=yes|no` (whether this run wrote the setting that is
on now) and `advisor-phase=build|post-build`. Only a run logged
`advisor-wrote=yes` ever runs `off`, and only after the ownership re-check
(Switch off): the flag is re-checked, not remembered.

**Fable CLI check** - every branch that would confirm or adopt `fable` (the
already-equal fast path, the confirm after `on`, and the build-phase launch
and re-assert below) also requires `fable_ok=yes` in the same status output.
`fable_ok=no` or `fable_ok=unknown` takes the exit-3 path below: the run goes
advisor-free, logs `advisor=off (cli below 2.1.321)`, writes nothing, does
not clear an existing setting, never sends the builder paragraph, tells JC
once, and is an opt-out run from then on (no `on`, no `off`).

**Switch on** - an auto run switches on before its first checkpoint: before
the lead's plan call (after drafting the plan, before the gate; a Fable lead,
which makes no plan call: before its first Claude seat). It starts with the
status read and writes nothing before it:

- `user_advisorModel=unset`, no project or local override, the disable
  variable unset in both places and no `invalid` scope: `on <model>`, then
  the status read again (exits below).
- `user_advisorModel` already equal to the run's model, `effective=<the run's
  model>`, `fable_ok=yes` when that model is `fable`, and no other blocker:
  write nothing; on is confirmed; log `advisor-wrote=no`.
- Another model in the user file, a project or local override, the disable
  variable set to a true value, or any `invalid` scope: write nothing, log
  `advisor-wrote=no`, stop and ask JC.

The run logs `advisor-phase=build` once on is confirmed. After `on`:

- Exit 0, no `invalid` scope, `effective=<the run's model>` and
  `fable_ok=yes` when that model is `fable`: on; log `advisor-wrote=yes`.
- Exit 0 but `effective` differs from the run's model: log
  `advisor-wrote=yes`, stop and ask JC - never declared matched.
- Exit 3: nothing written; the run continues advisor-free, logs
  `advisor=off (cli below 2.1.321)` and `advisor-wrote=no`, tells JC once,
  and is an opt-out run from then on.
- Exit 6: the status read, then this switch-on path once more; a second 6
  logs `advisor-wrote=no` and goes to JC.
- Exit 5: the status read, compare `advisorModel` with the named backup,
  stop and ask JC; log `advisor-wrote=yes` only once JC confirms the file
  holds this run's write, else `advisor-wrote=no`.
- Exit 1, 2 or 4, or a permission denial: nothing written; log
  `advisor-wrote=no`, stop and ask JC (a denial means the allow rule above is
  missing or the script's path changed).

**Before each Claude seat** - every run re-reads the effective state with the
status read before each Claude seat it launches, not only the first: consults
are model-driven, the setting is shared by every session in every folder, and
another run or JC may have changed it since the last seat.

- Auto run in the build phase, before a builder seat:
  - effective state matches its line (with `fable_ok=yes` on a `fable`
    run; otherwise the Fable CLI check above): launch;
  - effective state `off` with `user_advisorModel=unset` and no other
    blocker (another run switched it off): re-assert through the switch-on
    path above (`on <model>` and the status read again); a write there logs
    `advisor-wrote=yes`;
  - any other mismatch (another model in the user file, a project or local
    override, the disable variable set to a true value): stop and ask JC.
    The lead never overwrites another run's model and never unsets the
    disable variable silently.
- Auto run, before a seat that is not a builder (reviewers, gates, graders),
  and before any seat in the post-build phase: the status read only, never
  `on`. The spec carries the do-not-consult line on every run.
- A post-build fix round that needs a builder again re-enters the build
  phase through the switch-on path (log `advisor-phase=build`); it switches
  off only as Switch off says (below).
- Opt-out run, an advisor effective: stop before that launch and ask JC. It
  must not switch off a setting another live run may need.
- Headless `claude -p` Claude seats always carry an explicit state:
  `--advisor <model>` on an auto run, only after that launch's status read
  found the disable variable unset; `CLAUDE_CODE_DISABLE_ADVISOR_TOOL=1` in
  the child's env on an opt-out run, as the pilot's control arm did (lane-d.md).

The builder paragraph (specs.md "Advisor block") goes into a builder spec only
when the effective state matches the run's line; otherwise the lead asks JC
before launching and never sends the paragraph to a seat without an advisor.
Review, gate and grading seats get the do-not-consult line (below) on every
run.

**Switch off** - an auto run logged `advisor-wrote=yes` runs `off`, then the
status read:

- after its last builder has landed (after the final accepted fix round)
  and the lead's pre-done checkpoint has run (global CLAUDE.md), before the
  report; once cleanup is confirmed it logs
  `advisor-phase=post-build`;
- whenever it parks (logbook `parked`, `/clear-prep`) or stops early.

Before every `off` the lead re-checks ownership with the status read: it runs
`off` only when `advisor-wrote=yes` and `user_advisorModel`
equals the run's model. If the user setting is now a different model or
already unset, someone else changed it (JC's `/advisor`, another run): do not run `off`, set
`advisor-wrote=no`, log what the status read showed, and tell JC in one line.
No question is needed, unless an advisor is still effective after the run's
last builder - then the ask-JC rule of the shutdown policy below applies.

A run that never wrote the setting (`advisor-wrote=no`: blocked at switch-on,
already equal, exit 3, an opt-out run) never runs `off`; it logs
`advisor-phase=post-build` once its last builder has landed. Other live auto
runs re-assert at their next builder seat, so `off` never needs to know about
them. Shutdown policy, for every `off` that does run:

- Exit 0, and the status read shows no `*_advisorModel=invalid`,
  `user_advisorModel=unset` and `effective=off`: cleanup confirmed; log it in
  RUN.md and set `advisor-wrote=no` (nothing left to clean).
- Exit 6: the status read, then `off` once more.
- Exit 5, 1 or 4, a second 6, any `invalid` scope, or an advisor still
  effective after `off` (a project or local override that `off` cannot
  clear): cleanup is not logged as done; the lead records the status output
  in RUN.md and asks JC.

## Pairing

The advisor must rank at or above the seat's model (equal is allowed): Opus
5.5 seats take an Opus or Fable advisor; a Fable 5.2 session accepts only a
Fable 5.2 advisor, so an Opus advisor never attaches to a Fable orchestrator
or Reviewer C. An invalid pair in `-p` mode prints a warning and runs without
it (local probe, CLI 2.1.318; the docs say it exits at launch). Fable 5.2 as
advisor needs CLI 2.1.321+ (the switch refuses it below, exit 3); this
machine runs 2.1.322 (2026-11-12).

## Cost and limits

No call cap. Each consult re-reads the whole transcript uncached at the
advisor's rate (about 55k input tokens on a fresh headless seat), and the
seat's stream pauses while it runs. The Fable advisor spends JC's Fable
allowance on every consult - about $1.78 per medium build in the pilot. While
it is on, every new Claude session in every folder gets it too, not only this
run's seats; the switch-off steps above end that.

## Who must not consult

Review seats (Reviewer A/B/C, the design gate, the gate's re-check calls),
blind graders, and experiment and trial seats. On every run, their specs carry
this line, verbatim:

"Do not consult the advisor tool or fable-consult.py in this session; this seat's judgment must be its own."

The orchestrator consults only at the global checkpoints (Precedence), its
plan call (Lifecycle) being one.

A Haiku lead asks it first on a judgment call (lead-mode-deltas.md, the
senior seat).

## What the builder does

Only when the effective state matches the run's line (Lifecycle), its spec
carries the advisor block (specs.md), verbatim:

> An advisor model is attached to this session. Consult it before you settle how to build the feature, and again before you report DONE; it reads your whole transcript, so ask in one line. Its reply is advice: check it against this spec and the code before you act on it. In your report, list each consult and what you did with its advice.

The builder lists each consult and what it did with the advice in its report;
the lead logs the count on the task line (`consults=<n>`). On a default run the
builder spec carries the consult block instead (specs.md, "Advisor block").

## Evidence

Pilot 2026-11-12 (`~/.fabstra/RUN-advisor.md`): headless Opus 5.5 builders at
medium effort, tasks B/D/E of the ownership-test harness, n=9 runs per arm,
under these specs:

| Arm | All hidden tests passing | Median cost per run | Median wall |
|---|---|---|---|
| No advisor | 6/9 | $0.48 | 79 s |
| Opus 5.5 advisor | 6/9 | $1.31 | 176 s |
| Fable 5.2 advisor | 7/9 (one task-E run caught the header-row rule) | $2.61 (Fable advisor share $1.78) | 262 s |

Every advisor run consulted twice. The blind grade found no behaviour changes
in any arm. Under the bar set before the pilot (2 or more additional passing
runs) neither advisor showed a measured gain.

Decision (JC, 2026-11-12, superseded 2026-11-20): the advisor ran
automatically on every run with Fable 5.2 - JC's choice, not a recommendation
the data made. Since 2026-11-20 the tool is opt-in and the Fable consult on
credits takes its place (The run's line).
