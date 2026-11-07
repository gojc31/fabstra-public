# Memory audit (ID letter D)

The auto-memory system: the `MEMORY.md` index loads every session, so it must
stay short, current and true.

## Inventory first

Each project's memory folder under `~/.claude/projects/<project>/memory/`
(start with the home folder's): `MEMORY.md` and the memory files it indexes.
Record bytes, line count, and the longest lines of each `MEMORY.md`.

## Checks

1. **Size.** Bytes and lines of `MEMORY.md`. The index is cut once it passes
   the startup cap (25 KB / 200 lines at last check - confirm the current cap
   in the memory docs); anything past it is not loaded at session start
   (Claude can still open it on demand, but nothing tells it to). Over ~60 %
   of the cap is a P2.
2. **Long lines.** Index lines over ~200 characters. An index line is a hook:
   current state plus a resume pointer, around 150 characters. Version
   history and commit hashes belong in the linked file.
3. **Stale and contradicting items.** "OWED", "pending", "until <date>" lines
   whose date has passed or whose work the environment shows as done (check
   git log, installed versions, the file itself). The same open item repeated
   on several lines. Mods or tools described as live that are uninstalled.
4. **Index integrity.** Every index line points at a file that exists; every
   memory file has an index line (an unindexed file is in the same position as
   lines past the cap: not loaded at session start, and nothing tells Claude
   to open it).
5. **Index vs file.** An index line that says something its file
   contradicts. The file is usually newer; the fix rewrites the index line.
6. **Wrong home.** Facts about the user or the work sitting as prose in
   CLAUDE.md or a skill instead of memory; how-to guidance sitting in memory
   that belongs in a skill or CLAUDE.md.

## Fix rules

Trimming the index is meaning-preserving: history moves into the linked file
before it leaves the index, and the loss audit (`loss-audit.md`) runs after.
A memory that turns out wrong is corrected or deleted, never left beside its
correction. Dated items the user must confirm (done, dropped, re-dated) go to
"Needs you".
