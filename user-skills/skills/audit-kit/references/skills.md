# Skills audit (ID letter C)

Whether each loaded skill earns its context, triggers when it should, and
holds together.

## Inventory first

Every skill that can load: `~/.claude/skills/*`, project `.claude/skills/*`
in the user's folders, plugin skills and commands (`claude plugin list`),
skills synced from claude.ai, and agents in `~/.claude/agents`. Record for
each: source, invocation (model-invoked or user-invoked), description length,
SKILL.md size. Built-in `/skill-doctor` gives per-skill token cost and
invocation history; run it first if this Claude Code has it.

## Checks

1. **Usage.** `/skill-doctor`, where this Claude Code has it, is the
   authoritative inventory and invocation history; where it and the script
   disagree, it wins. `scripts/skill_usage.py` is a heuristic: run
   `python scripts/skill_usage.py --days 30` from this skill's folder (a few
   minutes on a large transcript folder - run it in the background). It
   counts Skill tool calls and typed commands (a typed command counts only
   when it opens a user message) in `~/.claude/projects` transcripts by each
   event's own timestamp, prints the oldest event date it saw, and lists
   skills with zero uses. When a transcript cannot be read it prints
   INCOMPLETE and exits 3: the zero-use list is then not definitive. Its
   inventory is `~/.claude/skills` plus the plugins that
   `~/.claude/settings.json` `enabledPlugins` turns on, read from their
   `skills/*/SKILL.md` only: plugins enabled in project or managed settings,
   and skill paths a plugin manifest declares, are missing from it - check
   those by hand before calling a skill unused.
   A model-invoked skill with zero uses in 30 days pays its description every
   turn for nothing: propose user-invoked (`disable-model-invocation: true`),
   disabling, or keeping it with a reason. Transcripts older than the cleanup
   period are gone, so say the window the data really covers, from the oldest
   event date.
2. **Hard limits.** Frontmatter parses; `name` matches the folder;
   description present and under the platform limit; SKILL.md under ~500
   lines; every file the skill points at exists (ignore names created at run
   time).
3. **Duplicates and overlaps.** Two skills that claim the same trigger (two
   document skills from different plugins, two "review a diff" skills, two
   handoff skills). Show both descriptions; propose one owner.
4. **Trigger clashes with guidance files.** A description that fires on a
   phrase CLAUDE.md reserves for something else.
5. **Retired but listed.** A retired or alias skill or command that is still
   model-invocable.
6. **Internal contradictions.** Two lines in one skill (or a skill and its
   references) that pull opposite ways after an edit.
7. **Vendored skills.** Upstream text that contradicts the user's own rules
   (e.g. it reaches for a browser tool the user's rules forbid); fixes are
   logged in the skill's VENDORED.md or equivalent so the next upstream
   update can re-apply them.
8. **Must-not-miss rules late in a long SKILL.md.** After compaction only the
   first ~5,000 tokens of each skill come back; a safety rule past that point
   can vanish.

## How to judge

Read each skill the way the model receives it: description always, body on
invocation, references on demand. For judgement findings across many skills,
split the inventory among read-only subagents with this file as the rubric,
then re-read the cited lines yourself for the top findings before reporting.
