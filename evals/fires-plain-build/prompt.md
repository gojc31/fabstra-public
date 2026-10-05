---
model: claude-fable-5-1
max_turns: 12
timeout_seconds: 240
allowed_tools: [Read, Glob, Grep, Skill]
tags: [positive,routing,ambiguous]
runs: 3
description: A plain real build on Fable should route to fabstra, not fabsol
---

Add server-side validation to the POST /signup route in server.js (email format, password at least 8 chars) and cover the failure cases in test/signup.test.js.
