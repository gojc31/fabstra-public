# Opus 5.5 builder effort trial (2026-09-24 to 2026-10-08)

Reached from: fabstra SKILL.md - Effort

Opus 5.5 builder effort trial, 2026-09-24 to 2026-10-08. Eligible: Opus-tier tasks outside the excluded categories (money, auth, PII, permissions, migration, concurrency, client-facing release). Eligible tasks alternate arms in launch order across runs in the same project folder: read the last `arm=` of an eligible task in `.fabstra/RUN*.md` and take the other arm; a folder with no history starts on `builder`. Arms: `subagent_type: "model-router:builder"` (Opus 5.5 xhigh) and `"model-router:builder-medium"` (Opus 5.5 medium). Excluded tasks always take `builder` and are logged `eligible=no`. Log `arm=` and `eligible=` beside every Opus-tier task and tag every review finding with its task. Readout on 2026-10-08 compares elapsed (launch to accepted), first-pass acceptance, and reproduced findings per arm; until then neither arm is the default.

## Readout inputs (added 2026-09-29)

The 2026-10-08 readout weighs each of these:

- Anthropic guidance (claude.dev "Spending your effort" and "What a task costs on Opus 5.5", both 2026-09-25): Opus 5.5 defaults to medium; a level thinks more on Opus 5.5 than on Opus 5, so levels are not carried over; medium for well-scoped work, high where verification and edge cases matter (brownfield bug fixes), xhigh/max only where a gain was measured; higher effort fixes missed edge cases, not a wrong approach; if xhigh hits the same problem twice, change model or approach.
- Watchdog stalls per arm: in `~/.fabstra/RUN-2026-09-28-082056.md` round 2 the xhigh arm stalled at the 600 s watchdog 3 times (Signal after writing, Almanac twice before writing) while builder-medium finished 5/5; count stalls per arm in the readout.
- Session effort: `~/.claude/settings.json` effortLevel=high and modelSettings claude-opus-5-5 effortLevel=high were carried over, not measured; JC decided 2026-09-29 to keep high until this readout; decide medium vs high here.
- builder-low vs Haiku: compare first-pass acceptance of multi-file mechanical edits on `model-router:builder-low` against earlier Haiku runs.
- Designer effort: the designer agent (`agents/designer.md`) runs Opus 5.5 at xhigh, carried over and unmeasured; the official Opus 5.5 prompting guide (fetched 2026-10-01) says reserve xhigh/max for measured gains, so decide designer effort at this readout.
- Sonnet 5.5 effort: its levels are recalibrated (official Sonnet 5.5 guide, fetched 2026-10-01: medium for well-specified agentic work, high for harder or longer work); `general-purpose` Sonnet subagents inherit the session effort, so weigh that when setting the session effort.
