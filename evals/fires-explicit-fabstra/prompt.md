---
model: claude-fable-5-1
max_turns: 12
timeout_seconds: 240
allowed_tools: [Read, Glob, Grep, Skill]
tags: [positive,routing]
runs: 3
description: Explicit fabstra ask on a Fable session must load fabstra
---

Use fabstra to add a GET /health endpoint to the Express server in this repo that returns {status:'ok'} and a test for it.
