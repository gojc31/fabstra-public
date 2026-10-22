# Decision page - what JC sees when a run needs JC

Reached from: fabstra SKILL.md "Report"; lead-mode.md plan gate and Gate 5; phases.md Phase 1 and Phase 4 - whenever a run hands JC something to decide or approve.

JC reads pages, not walls of text: JC's attention is the scarce resource and
tokens are cheap, so a run spends tokens to make each decision fast. Two
outputs exist, and every run uses the short report; the decision page is
added when the fork below says so.

## Report file

The run's report file pairs with its logbook: `RUN.md` -> `.fabstra/REPORT.md`,
`RUN-<slug>.md` -> `.fabstra/REPORT-<slug>.md`. Write it once, when the run
completes: `scripts/logbooks.py` reads a report newer than its logbook as a
finished run, so a mid-run hand-off keeps its detail on the decision page and
in the logbook, never in the report file.

## The short report (end of run; mid-run hand-offs use lines 1 and 4)

Strict shape, at most 6 lines in chat:

1. **Needs you:** the decision or approval in one line, plus the page link
   when there is one - or "Nothing needs you."
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
the crew lines, the finding ledger, the fast-pin note.

## Fork - page or chat line

- **Decision page:** the hand-off has 2+ open decisions; or an approval for
  an excluded category (SKILL.md) or a merge/ship of one; or a choice between
  visual or UX options; or one decision whose options JC cannot judge
  without seeing evidence (a diff, a screenshot, a diagram).
- **Chat line:** one plain question with obvious options - ask it in line 1
  of the short report (AskUserQuestion where the session has it).

## Build the page (lead's job, Orchestrate mode included - it is a report, not code)

1. **Collect the evidence** the decision rests on: what changed (files,
   behaviour), the smoke-gate and review results with counts, what the run
   could not do or verify, and for a UI choice a screenshot or render of
   each option (surfaces.md). Done when every question has the evidence that
   settles it.
2. **Write one HTML file** at `.fabstra/<page-id>.html`, where the page id
   is `decision-<run>-<n>` and stays fixed for that decision; each re-publish
   of it raises the revision `r1`, `r2`, ... shown on the page. Design it
   for this situation - no fixed template; let the content choose the form
   (mockups side by side, a before/after, a small diagram, a checks table).
   The Artifact tool's own contract (quickstart, design guidance) applies.
   The page holds, top to bottom:
   - the ask in one sentence and what it blocks;
   - what changed, in plain words;
   - the evidence: visuals first, then checks run and their results;
   - what the run could not do or verify;
   - one card per question (`Q1`, `Q2`, ...): the task it blocks, 2-4
     options as clickable choices with ids `a`, `b`, `c`, `d`, the
     recommended one first and marked, one line on what each option leads
     to, and an "other" free-text field;
   - a **Copy response** button that copies the response block below, plus
     the same block in a read-only textarea that selects itself on click,
     because clipboard access can be blocked inside the frame.
3. **Response block** (strict - the run parses it):
   ```
   DECISIONS <page-id> r<revision> <YYYY-MM-DD>
   Q1: <option id, or other> | <option label> | <note or ->
   Q2: <option id, or other> | <option label> | <note or ->
   ```
   The page writes one line per question and leaves an unanswered one as
   `Q<n>: -`; in a note it turns line breaks into spaces and `|` into `/`.
   Before publishing, log in RUN.md: the page id, revision, URL, and each
   question with its option ids and the tasks it blocks.
4. **Keep secrets and personal data off the page:** name the file or field,
   never paste a key, token, `.env` value, password or a person's personal
   details; client screenshots are cropped or masked to what the decision
   needs.
5. **Publish** with the Artifact tool, private, from that file path; an
   update to the same decision re-publishes the same path (same URL). Then
   send the short report with the link in line 1. Done when the publish
   result returns a URL.
6. **On JC's reply:** match the block's page id and revision to the current
   revision logged in RUN.md, and each answer to a logged question and
   option id. Each matched answer goes into the plan under its task as "user
   decision <date>" and into RUN.md, and unblocks its tasks. A stale
   revision, an unknown page, question or option, a duplicate, or `-` keeps
   its tasks blocked and gets one chat line naming what is still open.

## No Artifact tool (headless `claude -p`, routed lanes)

Write the same HTML file, skip step 5's publish, and put the file path in
line 1 of the short report; JC opens it locally and pastes the block back.
