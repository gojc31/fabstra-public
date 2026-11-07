# Prompt audit (ID letter B)

Two passes over every prompt surface: the official dated-pattern audit, then
a drift pass that catches what the official one does not.

## Inventory first

The prompt surface on this machine: `~/.claude/CLAUDE.md`, `AGENTS.md` and
`CLAUDE.md` in each project the user works in, `~/.claude/agents/*.md`,
plugin agents and commands, skills (the skills audit owns their structure;
this pass reads their wording), output styles, and any system prompt the
user's own apps send to the API. Note the target model for each.

## Pass 1 - the official audit

Use Anthropic's prompt-audit guide shipped with the `claude-api` skill:
`shared/prompt-audit.md` under that skill's base directory (invoke the
`claude-api` skill, or search `~/.claude/plugins/cache` for
`claude-api/shared/prompt-audit.md`; take the newest copy). Follow its steps
0-7 in order: scope and target model, inventory, provenance, the deletion
rule, the anti-pattern groups, report, proposed diff, verify. Its keep list
wins over any urge to trim. If the guide is not on this machine, say so in
"Not checked" and run Pass 2 only.

## Pass 2 - drift

1. **Fossils.** Retired model names and versions (an older Opus, Sonnet or
   Haiku generation; retired skill or agent names) still steering behaviour.
   Check each against the current model list in the `claude-api` skill.
2. **Files that disagree.** The same rule stated differently in two places
   (a global file vs a project file, a skill vs the command that launches
   it). Quote both lines; the fix names the one authoritative home and turns
   the other into a pointer or deletes it.
3. **Stale facts and dates.** "Trial running", "until <date>", "owed" items
   whose date has passed; versions and counts the environment now
   contradicts. Verify against the environment (git log, installed versions),
   not memory.
4. **Trigger clashes.** A phrase a guidance file reserves for one tool that a
   loaded skill's description also triggers on.
5. **Vague pointers.** "See the skills' X section" that does not name the
   file. Fix: name the file.
6. **Always-loaded cost.** Bytes of everything that loads every session in
   the home folder (global CLAUDE.md + AGENTS.md + MEMORY.md + agent and
   skill descriptions). Long agent descriptions that spend most of their
   length on "do not use when..." belong in the body.

## Report notes

Each finding quotes the line, names its file:line, and gives the exact
replacement text. Pass 1's "verify" step is mandatory for any applied
removal: removal is a hypothesis until a run shows behaviour held.
