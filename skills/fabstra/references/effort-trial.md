# Claude seat efforts - evidence, and the 2026-09 builder effort trial

Reached from: fabstra SKILL.md - Effort; phases.md - Claude seat efforts

## Current method (2026-11-10, FabStra 1.11.0)

The seat table is in phases.md, "Claude seat efforts". JC set the crew on
2026-11-10 - Fable 5.2 orchestrates, Opus 5.5 subagents build, a fresh
Fable 5.2 reviews - and delegated the effort design ("you design the
effort"). The design rests on:

- Anthropic, "Prompting Claude Fable 5.2" (fetched 2026-11-10): start Fable 5.2 at `high`; most of its capability gain is in by `high`; `xhigh` raised Anthropic's internal coding scores slightly for many more tokens; at `xhigh` and `max` it starts subagents to review its own work; levels are not carried over from Fable 5.1 or Opus 5.5, so the sweep is re-run on the new model.
- claude.dev, "Which Claude model should you build with?" (2026-11-09), Opus 5.5 on SWE-bench Pro relative to `high`: `medium` about 2.5 points lower at about 70% of the cost, `low` about 8 points lower at about a third, `xhigh` about 1.4 points higher at 2.5 times. With an automatic check, `low` with the failures re-run at `high` passed about 97% of tasks against 95.3% for every task at `high`, for less. When a model falls short: first give it a way to verify its work, then raise effort one level, then move up a model.
- Anthropic, "When to fold subagents into your main agent loop" (2026-10-22): a subagent hands back a lossy summary and adds a nested loop; keep one for parallel work in a fresh context or for black-box verification; split by context, not by kind of problem.
- Reviewer C at `high`: the Fable 5.2 guide's starting level, and the review floor for anything a user or client runs (phases.md, Effort rubric). Measured 2026-11-10 on the local hard fixture (`bench/results/results.csv`, `FIXTURE=hard`, n=3 each): Fable 5.2 at `high` found 8/8 planted bugs with 0 false positives in 103-122 s; at `xhigh` it found the same 8/8 with 0 false positives in 321-575 s (the scorer read one `xhigh` report as 1/8 because of its layout; that report's verdict table lists all 8). The fixture tops out at 8/8, so it cannot show a gain above `high`. On a build in an excluded category Reviewer C runs at `xhigh` (`model-router:reviewer` with `effort: "xhigh"`): JC's decision, 2026-11-10; on this fixture `xhigh` added no recall and took about 4 times the wall time.

Not measured on this flow yet: `model-router:builder` at high against xhigh on real tasks, Reviewer C on Fable 5.2 at `high`, the designer's effort, and Fable 5.2 as lead at `medium` against `high`. RUN.md's `seat`, `effort`, `elapsed` and `first_pass` fields are the record a re-tune reads.

## Old patterns

Opus 5.5 builder effort trial, 2026-09-24 to 2026-10-08. Eligible: Opus-tier tasks outside the excluded categories (SKILL.md, Excluded categories). Eligible tasks alternate arms in launch order across runs in the same project folder: read the last `arm=` of an eligible task in `.fabstra/RUN*.md` and take the other arm; a folder with no history starts on `builder`. Arms: `subagent_type: "model-router:builder"` (Opus 5.5 xhigh) and `"model-router:builder-medium"` (Opus 5.5 medium). Excluded tasks always take `builder` and are logged `eligible=no`. Log `arm=` and `eligible=` beside every Opus-tier task and tag every review finding with its task. Readout on 2026-10-08 compares elapsed (launch to accepted), first-pass acceptance, and reproduced findings per arm; until then neither arm is the default.

**After 2026-10-08** every Opus-tier task takes `subagent_type: "model-router:builder"` (Opus 5.5 xhigh), excluded categories included; log `arm=builder eligible=post-trial`. The alternation above applies only through the trial. `model-router:builder-low` (`arm=builder-low eligible=no`) is unchanged.

### Readout inputs (added 2026-09-29)

The 2026-10-08 readout weighs each of these:

- Anthropic guidance (claude.dev "Spending your effort" and "What a task costs on Opus 5.5", both 2026-09-25): Opus 5.5 defaults to medium; a level thinks more on Opus 5.5 than on Opus 5, so levels are not carried over; medium for well-scoped work, high where verification and edge cases matter (brownfield bug fixes), xhigh/max only where a gain was measured; higher effort fixes missed edge cases, not a wrong approach; if xhigh hits the same problem twice, change model or approach.
- Watchdog stalls per arm: in `~/.fabstra/RUN-2026-09-28-082056.md` round 2 the xhigh arm stalled at the 600 s watchdog 3 times (Signal after writing, Almanac twice before writing) while builder-medium finished 5/5; count stalls per arm in the readout.
- Session effort: `~/.claude/settings.json` effortLevel=high and modelSettings claude-opus-5-5 effortLevel=high were carried over, not measured; JC decided 2026-09-29 to keep high until this readout; decide medium vs high here.
- builder-low vs Haiku: compare first-pass acceptance of multi-file mechanical edits on `model-router:builder-low` against earlier Haiku runs.
- Designer effort: the designer agent (`agents/designer.md`) runs Opus 5.5 at xhigh, carried over and unmeasured; the official Opus 5.5 prompting guide (fetched 2026-10-01) says reserve xhigh/max for measured gains, so decide designer effort at this readout.
- Sonnet 5.5 effort: its levels are recalibrated (official Sonnet 5.5 guide, fetched 2026-10-01: medium for well-specified agentic work, high for harder or longer work); `general-purpose` Sonnet subagents inherit the session effort, so weigh that when setting the session effort.

Readout done 2026-10-18 (`~/.fabstra/audit-2026-10-18/effort-trial-readout.md`): JC kept `model-router:builder` (xhigh) as the Opus-tier build seat.

- 2026-10-18 to 2026-11-10 (through 1.10.50): Fable 5.1 orchestrated; every Opus-tier task took `model-router:builder` (xhigh), logged `arm=builder eligible=post-trial`; Sonnet- and Haiku-tier tasks took `general-purpose` with `model: "sonnet"` / `"haiku"`; Reviewer C was a fresh Fable 5.1.
- 2026-11-16 (1.15.0): the four builder files and the two reviewer files merged into `model-router:builder` and `model-router:reviewer`; effort passes per Agent call (JC, Anthropic subagent guidance). Names above this line are historical.
