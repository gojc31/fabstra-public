---
name: brief
description: Turn a one-line ask into a finished brief (goal, done, completion, effort, verification, execution) and start the work. Use when the user types /brief followed by a one-line ask.
disable-model-invocation: true
---

# Brief

The user's ask: $ARGUMENTS

Draft the brief yourself from the ask, the project's CLAUDE.md, and memory. Fill every line; guess sensibly where the ask is silent and mark the guess. Show it in six lines, then start the work in the same turn. Stop for an answer only where two readings would produce materially different builds.

```
Goal: <what and why, one sentence>
Done when: <observable checks, the ones a reviewer would run>
Completion: what I will decide alone, and the one thing (if any) I will stop to ask
Effort: <high | xhigh for planning- or review-heavy | medium for mechanical> and why
Verification: <how each done-check will be proven before reporting>
Execution: <what runs in parallel, what gets delegated, what stays in-session>
```

A hard task (anything where the first idea might be wrong: several files, live systems, client data, debugging, research with claims) then goes through `/model-router:fabstra` with this brief as its input; its plan phase skips the question round because goal and done are already stated.
