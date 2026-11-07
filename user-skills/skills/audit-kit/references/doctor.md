# Doctor audit (ID letter A)

The health of the Claude Code install itself: CLI, settings, hooks, plugins,
MCP servers, permission rules, processes and disk. Commands below are
examples; adapt them to the shell and OS of this machine (PowerShell on
Windows, bash elsewhere).

## Inventory first

- CLI version (`claude --version`) and the latest published one
  (`npm view @anthropic-ai/claude-code version`, or the release notes).
- Settings files that load: `~/.claude/settings.json`, `~/.claude/settings.local.json`,
  `~/.claude.json`, and `.claude/settings*.json` in the folders the user works in.
- Hooks named in those settings, plugins (`claude plugin list`), marketplaces
  (`~/.claude/plugins/known_marketplaces.json`).
- MCP servers, read from config only, each with its command or URL:
  `mcpServers` in `~/.claude.json` (top level and per-project entries),
  project `.mcp.json` files, and the servers enabled plugins declare (their
  `plugin.json` `mcpServers` or `.mcp.json`). A live health check
  (`claude mcp list`, `/mcp`) starts the servers - stdio commands and
  `headersHelper` scripts run - so it is a fix-phase step after approval
  (SKILL.md, Rules), named under "Needs you".

## Checks

1. **`claude doctor`**, a read-only diagnostic, run via the shell with a 60 s
   timeout. Summarise every warning. If it hangs or needs an interactive
   screen, note "run /doctor in a session" and move on.
2. **CLI drift.** Installed vs latest; whether auto-update is on and actually
   firing (doctor prints the last update attempt). Several builds behind with
   auto-update "on" is a finding; the user skipping versions on purpose is not.
3. **Settings parse.** Every settings JSON parses, and none starts with a UTF-8
   BOM (a BOM breaks some readers on Windows): read the first three bytes.
4. **Redundant or conflicting settings.** The same value set in two places
   (e.g. `effortLevel` and a per-model `effortLevel`), user and project files
   pulling opposite ways, global `additionalDirectories` that only one project
   needs.
5. **Permission rules.** Rules pointing at paths that no longer exist (old
   scratchpads, deleted scripts), one-off rules for a single past command,
   rules for one client that belong in that client's project settings, and
   rules `claude doctor` flags as not working as written (a wildcard before the
   rest of the command). Note over-broad allows (`Bash(python -c *)`) without
   recommending changes to deliberate safety rules.
6. **Hooks.** Inspect each hook named in settings: its command path exists;
   its command and script, read for what they do and any obvious cost (a
   network call, a heavy interpreter start, work on every tool call); timing
   evidence the setup already has (debug logs, a hook's own log). When only a
   run would settle a question (real timing, whether its tests pass), name
   that run under "Needs you": running a hook or its tests is a fix-phase step
   (SKILL.md, Rules). Files in `~/.claude/hooks` that no setting references
   are orphans.
7. **Plugins.** `~/.claude/plugins/installed_plugins.json`: duplicate
   records for the home folder - the same plugin with a user record and a
   project record whose `projectPath` is the home folder. Likely cause, a
   hypothesis to confirm: in the home folder `~/.claude/settings.json` is both
   the user and the project settings file, so a project-scope install or
   update run there writes a second record. Fix: back up the file, remove the
   duplicate project record, and install with an explicit `--scope user`.
   Also: project records whose version lags the user record; disabled plugins
   that still auto-update; uninstalled plugins still in the cache. Cache size:
   keep every version a running session uses; old versions go only after
   those sessions restart, then keep the current version and one back.
8. **Plugin packaging leaks.** A plugin source folder that ships `bench/`,
   `backups/`, test junk or its own `.claude/skills` into every install cache.
9. **MCP servers.** From the config inventory: a server whose command path
   no longer exists; on Windows, the same project recorded under `C:/` and
   `c:/` keys in `~/.claude.json` with different server lists (VS Code
   launches lower-case), and entries for deleted folders. A server that
   "Needs authentication" or fails to connect every session is known from the
   user's own session or from the approved live check.
10. **Marketplaces.** Third-party marketplaces with `autoUpdate` unset and a
    last update months old.
11. **Processes.** Count `claude` processes and their memory; sessions idle
    for 12 h+; orphaned children whose parent is dead (browser daemons, Codex
    trees, MCP servers). Report, never kill.
12. **Disk.** Free space per drive; `~/.claude/projects` (transcripts) size
    and whether `cleanupPeriodDays` is set; Claude Code session scratchpads
    (on Windows `%LOCALAPPDATA%\Temp\claude`) - nothing prunes them; plugin
    cache; npm and other caches; WSL / Docker virtual disks on the system
    drive; git worktrees nobody has touched for 14+ days. Measure, do not
    infer; where sizing did not finish, say so.
13. **Stale temp files.** `*.tmp*` leftovers next to credentials or manifests.
    Report; deleting them needs the user's yes and Claude closed.

## Known false alarms

- A folder-scoped skill showing up because the home folder contains a plugin
  cache: a packaging issue (check 8), not a broken skill.
- Unix permission bits on Windows (`.env` reads 644): meaningless there.
