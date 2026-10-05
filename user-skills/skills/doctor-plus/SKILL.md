---
name: doctor-plus
description: Runs Claude Code's /doctor health check, then audits the workspace's loaded context against Anthropic's six context-engineering shifts for the Claude 5 models. Reports first; fixes only on approval.
disable-model-invocation: true
---

# Doctor Plus

The standard /doctor checkup, plus a workspace audit for the 6 then & now shifts from Anthropic's context-engineering article (Thariq @trq212, Jul 2026 - they cut ~80% of the Claude Code system prompt for the Claude 5 models). Read the article if a check needs the original reasoning: https://x.com/trq212/status/2080710971228918066

## The 6 shifts (the principles part 2 audits against)

| # | Then | Now | The principle |
|---|---|---|---|
| 1 | Give Claude rules | Let Claude use judgement | constrain Claude only where a wrong call is genuinely costly; judgement covers the rest |
| 2 | Give Claude examples | Design interfaces | a well-designed parameter, name, or field teaches use better than worked examples |
| 3 | Put it all upfront | Use progressive disclosure | the right context at the right time; always-loaded files must earn every line |
| 4 | Repeat yourself | Simple tool descriptions | every instruction has one authoritative home; everything else points there |
| 5 | Memory in CLAUDE.md | Auto-memory | facts about the user and the work belong in the memory system, not guidance files |
| 6 | Simple specs | Rich references | the highest-fidelity reference wins: code, test suites, HTML mockups, rubrics |

## Workflow

### Part 1 - the standard checkup
1. Run `claude doctor` via Bash with a 60s timeout. If it completes, summarize its findings.
2. If it hangs or needs an interactive screen, note "run /doctor in your session for the built-in half" and move on. Never block on it.

### Part 2 - the 6 shift checks
Scope: whatever the workspace actually loads as context - guidance files (CLAUDE.md and kin), skills, rules, memory indexes. Map that set first; don't assume the workspace's layout. Always exclude version-control internals, sync backups, node_modules, caches, temp folders, and generated output.

**Audit the principles, not surface patterns.** This audit itself follows shift 1: judge each file against the principle, don't pattern-match for keywords. Read the context the way Claude receives it - what loads always, what loads on demand - and ask per shift: is this workspace still living in the THEN column? The smells below are illustrations, not definitions; something can smell fine and still break the principle, and vice versa.

1. **Judgement over rules** - is Claude constrained where judgement would serve better? Smell: absolute directives about matters of taste or style, or two directives that pull against each other. Safety and money rules are legitimately hard - never flag those.
2. **Interfaces over examples** - do skills teach by boxing Claude into worked examples where a clearer interface (better parameters, names, structure) would carry it?
3. **Progressive disclosure over upfront loading** - does every always-loaded line earn its place? Smell: detail that's only occasionally needed sitting in files that load every session instead of a tree read on demand.
4. **One home over repetition** - does each instruction have one authoritative home? Smell: the same guidance restated in several places, especially copies that have drifted apart.
5. **Auto-memory over guidance-file memory** - are facts about the user or the work (preferences, dates, decisions) living as prose in guidance files instead of the memory system?
6. **Rich references over simple specs** - are active builds steered by plain markdown descriptions where a higher-fidelity reference (code, a test suite, an HTML mockup, a rubric) exists or would be cheap to make?

### Part 3 - report, then wait
Output one findings table: shift, verdict (PASS or FLAG), worst offender, suggested fix. Mirror /doctor's manner: **show everything first, change nothing until the user approves.** After approval, apply fixes one shift at a time and re-verify.

## Rules
- Every finding cites the actual file and the actual passage that breaks the principle. No vibes, no trend commentary.
- A zero-hit search at root is not proof of absence - look again narrowed before reporting PASS.
- Most workspaces keep some hard rules on purpose (approvals, backups, destructive actions, money). Never recommend softening those.
