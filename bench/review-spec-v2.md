<task>
Read-only review. Adversarially review this module. You are the red team - find what is WRONG.
Brief: util.py provides slugify, paginate, parse_price, dedupe, and retry.
Done means: every docstring in util.py is true of its function for ordinary and edge inputs.
Project stack and hard rules: plain Python 3.12, standard library only.
</task>
<context>
Files changed:
- util.py - new module; all five functions are new in this build
Entry points and callers you already know: none yet (library module, no callers in the repo)
Test command: none (no test suite; probe with python -c under SCRATCH)
Diff:
__DIFF__
</context>
<review_scope>
Start from the diff: verify it first, then follow every edge it touches -
callers, templates, configs, sibling files, the other side of any contract
it changes. The diff is where you start, not where you stop; a change that
is correct in isolation and breaks a caller is still a P1.
</review_scope>
<turn_budget>
You have 30 tool calls in total. Spend them on verification, not discovery:
read whole files rather than line windows; find callers with one grep pass
over the tree, not one per symbol; chain shell commands into one call.
Do not save findings one at a time - every save is a tool call. If you
reach your 20th tool call without having written the report, save what
you have confirmed so far to SCRATCH/findings.md in one Bash call; at
your 26th, stop exploring and write the final report.
</turn_budget>
<grounding_rules>
Ground every finding in file:line evidence or command output you ran.
Never present an inference as fact; label hypotheses as hypotheses.
Verify with what Bash gives you; if you cannot verify either way, mark it UNVERIFIED - do not silently pass it.
</grounding_rules>
<dig_deeper_nudge>
After the first plausible issue, keep going: empty states, error paths,
edge inputs, ordering, and whether each docstring is actually met rather than approximately met.
</dig_deeper_nudge>
<action_safety>
Never modify the reviewed files. Run code freely; write probe files only under the directory named SCRATCH below.
</action_safety>
<structured_output_contract>
Return exactly: (1) per function: PASS or FAIL with evidence;
(2) findings ranked by severity - P1 breaks the docstring, P2 should fix, P3
minor - each with file:line, what breaks, how you proved it, and your
confidence 0-100. Report only findings you are 80+ confident in and would
personally act on: precision over recall. (3) nothing else. Finding
nothing wrong is a legitimate result - do not manufacture findings.
Before finishing, save this same report via Bash to SCRATCH/findings.md.
</structured_output_contract>
SCRATCH = __SCRATCH__
