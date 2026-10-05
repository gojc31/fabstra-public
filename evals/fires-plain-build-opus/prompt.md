---
model: claude-opus-5-5
max_turns: 12
timeout_seconds: 240
allowed_tools: [Read, Glob, Grep, Skill]
tags: [positive,routing,ambiguous]
runs: 3
description: A plain real build on Fable should route to fabstra, not fabsol (Opus 5.5 session)
---

Add server-side validation to the POST /signup route in server.js (email format, password at least 8 chars) and cover the failure cases in test/signup.test.js.
