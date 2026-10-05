---
model: claude-fable-5-1
max_turns: 12
timeout_seconds: 240
allowed_tools: [Read, Glob, Grep, Skill]
tags: [positive,routing,budget]
runs: 3
description: An explicit budget-crew ask must still route to fabstra after the topic words leave the description
---

Use the budget crew to add a slug column to the posts table in db/schema.sql and write the migration that backfills it from title.
