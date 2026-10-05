---
name: careful
description: "Blocks destructive commands (rm -rf, DROP TABLE, force-push, git reset --hard, kubectl delete, terraform destroy, and similar) for the rest of the session via a PreToolUse guard on Bash and PowerShell. Turn on with /careful before touching production, a client's live prod data, or a connected live n8n / Supabase / GHL instance."
disable-model-invocation: true
hooks:
  PreToolUse:
    - matcher: "Bash|PowerShell"
      hooks:
        - type: command
          command: python
          args:
            - '{{SKILLS_DIR}}\careful\guard.py'
---

# careful

The user types `/careful` right before a command touches production: a client's live data, or a connected live n8n / Supabase / GHL instance. It never fires on its own.

**What it does.** Registers a PreToolUse guard on the `Bash` and `PowerShell` tools (`guard.py`, stdlib only). Every command those tools run is checked first; the guard denies anything that destroys data or history and lets everything else through unchanged, silently.

**It lasts until the session ends.** There is no `/careful off`. Once the guard is on, it stays registered and checking every `Bash` and `PowerShell` command for the rest of this session — invoking the skill again does not toggle it off.

**Blocked, case-insensitive except where noted:** `rm -rf` / `rm -fr` / `rm -r` on a non-temp path, `Remove-Item -Recurse -Force`, cmd.exe `rd /s` / `rmdir /s`, `git push --force` / `-f` / `--force-with-lease`, `git reset --hard`, `git clean -f`, SQL `DROP TABLE|DATABASE|SCHEMA`, `TRUNCATE`, `DELETE FROM` without `WHERE`, `supabase db reset`, `kubectl delete`, `terraform destroy`. `git branch -D` is case-sensitive: uppercase `-D` (or `-d` combined with `-f`/`--force`) is blocked; lowercase `-d` alone deletes only an already-merged branch and passes.

**When a block is wrong.** The guard does not ask for confirmation — it denies and names the pattern it matched. Do not rephrase the command to dodge the pattern. Ask the user: the user runs the command themselves (in their own terminal, or with the `!` prefix in this one), or starts a fresh session without `/careful` if the guard should not have been on for the rest of this one.
