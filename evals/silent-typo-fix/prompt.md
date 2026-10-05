---
model: claude-fable-5-1
max_turns: 12
timeout_seconds: 240
allowed_tools: [Read, Glob, Grep, Skill]
tags: [negative,routing]
runs: 3
description: A trivial one-line fix must not load any orchestration skill
---

There is a typo 'recieve' somewhere in README.md. Tell me the corrected spelling and which line it is on; do not edit anything.
