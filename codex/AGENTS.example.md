# Global Codex instructions (~/.codex/AGENTS.md)

Codex reads this file at the start of every session, the way Claude Code reads
`~/.claude/CLAUDE.md`. The two tools never read each other's file. Only the
first bullet matters for FabStra / FabSol / fable-mode; add your own rules
below it. If you keep a second Codex home for a Pro login (`CODEX_PRO_HOME`),
copy this file there too.

- When a prompt gives you a spec or review contract, follow it exactly and
  return only what it asks for.
