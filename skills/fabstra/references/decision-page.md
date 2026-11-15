# Asking JC in chat - what JC sees when a run needs JC

Reached from: fabstra SKILL.md "Report"; lead-mode.md plan gate and Gate 5; phases.md Phase 1 and Phase 4 - whenever a run hands JC something to decide or approve.

JC's attention is the scarce resource and tokens are cheap, so a run spends
tokens to make each decision fast. Every run uses the short report; every
decision or approval is asked in chat with AskUserQuestion (below). No
Artifact is published for a decision or a report unless JC explicitly asks
for a page.

## Report file

The run's report file pairs with its logbook: `RUN.md` -> `.fabstra/REPORT.md`,
`RUN-<slug>.md` -> `.fabstra/REPORT-<slug>.md`. Write it once, when the run
completes: `scripts/logbooks.py` reads a report newer than its logbook as a
finished run, so a mid-run hand-off keeps its detail in the logbook and an
evidence file, never in the report file.

Write the report file for a reader who did not watch the run and has none of
its context: the result first, full sentences, plain words, and every label
or abbreviation the run coined spelled out as what it is.

## The short report (end of run; mid-run hand-offs use lines 1 and 4)

Strict shape, at most 6 lines in chat:

1. **Needs you:** the decision or approval in one line, plus the evidence
   file's path when there is one - or "Nothing needs you."
2. **Shipped:** what now exists, one line.
3. **Verified:** the check that proves it and its result, one line.
4. **Not done / risks:** anything unverified, failed, skipped or left open,
   one line; omit the line only when there is none.
5. **Detail:** the report file's path (Report file, above).

A failure, a P1, an unverified claim or a skipped gate always shows in lines
1-4 in plain words; the short shape moves detail, never bad news. Mid-run
status notes are one line each.

The report file carries everything else the report rules ask for
(lead-mode.md Gate 5; phases.md Phase 4): verified versus assumed, citations,
the crew lines, the finding ledger, the fast-pin note, and the count of
Gemini consults run (0 is stated, with the skip reason).

## Ask in chat (lead's job, Orchestrate mode included)

1. **Collect the evidence** the decision rests on: what changed (files,
   behaviour), the smoke-gate and review results with counts, what the run
   could not do or verify, and for a UI choice a screenshot or render of
   each option (surfaces.md). Evidence JC must see (diff, screenshot, table)
   goes into a local file `.fabstra/decision-<run>-<n>.md` (or the image
   file); its path goes in the question text or line 1 of the short report.
   Done when every question has the evidence that settles it.
2. **Log in RUN.md before asking:** one entry per question - id (`Q1`,
   `Q2`, ...), its option labels, and the tasks it blocks.
3. **Ask with AskUserQuestion:** at most 4 questions per call, a second
   call for the rest. Each question names the task it blocks; 2-4 options,
   the recommended one first and labelled "(Recommended)", one line on what
   each option leads to. The free-text "Other" answers any question.
4. **Keep secrets and personal data out of questions and evidence files:**
   name the file or field, never paste a key, token, `.env` value, password
   or a person's personal details; client screenshots are cropped or masked
   to what the decision needs.
5. **On JC's answer:** match each answer to its logged question and option.
   Each matched answer goes into the plan under its task as "user decision
   <date>" and into RUN.md, and unblocks its tasks. An unknown option, a
   skipped question or an empty answer keeps its tasks blocked and gets one
   chat line naming what is still open.

## No AskUserQuestion (headless `claude -p`, routed lanes)

Put the questions as numbered lines in line 1 of the short report (or in a
local `.fabstra/decision-<run>-<n>.md` file whose path goes in line 1), in
the same shape: question, task it blocks, options with the recommended one
first. Log them in RUN.md as in step 2. JC answers in chat by number and
option; step 5 matches the reply.
