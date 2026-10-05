# Setup - FabStra + fable-mode on your machine

This is JC's fork of RoboNuggets' `model-router` plugin, with the FabStra flow,
the fable-mode skill, and the shell shims it depends on. Everything
machine-specific is now an environment variable with a sane default. Work
through the steps in order; each one is a few minutes.

## What you need

| Piece | Why | Where |
|---|---|---|
| Claude Code (CLI, desktop, or VSCode) with Claude Fable 5.1 available | Fable is the planner in fabstra; fable-mode runs on Opus 5 / Sonnet 5 / Haiku 4.5 | claude.com/claude-code |
| OpenAI Codex plugin for Claude Code (`openai-codex` marketplace) | The Codex transport - Astra / Sol / Terra / Luna run through its companion script | `/plugin marketplace add openai/codex-plugin-cc` then `/plugin install codex@openai-codex` (check the current name in `/plugin`) |
| Codex desktop app or CLI signed in to a ChatGPT login | The `codex` shim finds the bundled `codex.exe` | openai.com/codex |
| CLIProxyAPI running on `http://127.0.0.1:8317` | The "proxy" - holds your ChatGPT (and other) logins so Claude Code can call GPT models with no API key | github.com/router-for-me/CLIProxyAPI - copy `proxy/config.example.yaml` to `~/cli-proxy-api/config.yaml` |
| A ChatGPT plan that includes GPT-6 Astra (Pro) | Astra is the senior seat. Without it fabstra falls back to Sol review and fable-mode loses its design gate - still usable | chatgpt.com |
| Git Bash (Windows) or any bash, plus Python 3 | The shims and `proxy-key` are bash; the key reader is Python | git-scm.com |

Anthropic's terms ban routing a Claude **subscription** login through third-party
tools. This setup never does: Claude Code stays on its own login and reaches
out to the GPT models via the proxy. Keep it that way.

## Step 1 - environment variables

Set these once (User scope on Windows via `[Environment]::SetEnvironmentVariable(name, value, "User")`,
or in `~/.bashrc` / `~/.zshrc` on Mac/Linux). Only the first is required.

| Variable | Meaning | Default |
|---|---|---|
| `MODEL_ROUTER_HOME` | Where you cloned this repo | none - set it, e.g. `C:\Users\you\fabstra` |
| `CODEX_BIN` | Path to the Codex CLI binary, if the shim cannot find it on its own | Codex desktop bundle on Windows, else any other `codex` on PATH |
| `CLIPROXY_DIR` | CLIProxyAPI install folder (holds `config.yaml`, `.management-key`) | `~/cli-proxy-api` |
| `MODEL_ROUTER_KEY` | The proxy API key (first entry under `api-keys:` in the proxy config) | read from `config.yaml` by `bin/proxy-key` |
| `MODEL_ROUTER_URL` | Proxy URL | `http://127.0.0.1:8317` |
| `CODEX_PRO_HOME` | A second `CODEX_HOME` holding your Pro login, used when Astra must run natively (not via the proxy) | `~/.codex-pro` |
| `PROXY_PRO_AUTHFILE` | The proxy auth-file name for your Pro login, e.g. `codex-you@example.com-plus.json`. Only needed if you run two ChatGPT logins and use `proxy-pin` | unset |

## Step 2 - shims on PATH

Copy `bin/` to `~/bin` and make sure `~/bin` is on PATH (Git Bash and PowerShell
both). The shims:

- `codex` - runs the Codex CLI bundled with the desktop app, routed through the
  proxy (`-c model_provider=router`). `CODEX_DIRECT=1` bypasses the proxy.
  Guards: refuses effort `max`/`ultra` (xhigh is the ceiling) and sends any
  `gpt-6-astra` call to the Pro home natively. Both guards have override env vars
  documented at the top of the file.
- `codex-pro` - same binary, `CODEX_HOME=$CODEX_PRO_HOME`, never via the proxy.
- `proxy-key` - prints the proxy API key. Every skill calls it instead of
  hard-coding the key.
- `proxy-pin team|both|status` - only for a two-login setup: disables or
  re-enables the Pro login inside the proxy's rotation. Skip it with one login.
- `codex-fast on|off|status` - toggles Codex Fast mode (`service_tier = "fast"`)
  in the Pro home's `config.toml`. The skills run it only for a brief that says
  `fast` ("astra fast"); it costs 2.5x on the Pro weekly window and only
  reaches native Pro-home launches, never the proxy or `claude -p`.
- `codex.cmd`, `codex-pro.cmd` - PowerShell / cmd wrappers for the bash shims
  (Windows only). They assume Git for Windows at `C:\Program Files\Git`.
- `lanew`, `lanew.cmd` - launches a Lane W job (see
  `skills/fabstra/references/lane-w.md`) through `scripts/lanew_log.py`'s
  fail-closed check and two-phase usage log. It is a diagnostic logger, not
  a hard budget - see lane-w.md, "What lanew measures and what it cannot".
  Needs `python` on PATH and Git Bash; `lanew.cmd` delegates to it the same
  way `codex.cmd` delegates to `codex`.

Codex needs a `router` provider in `~/.codex/config.toml` pointing at the proxy:

```toml
[model_providers.router]
name = "model-router"
base_url = "http://127.0.0.1:8317/v1"
env_key = "MODEL_ROUTER_KEY"
wire_api = "responses"
```

## Step 2b - Codex agents and provider

Copy the custom agents and merge the provider block:

```bash
mkdir -p ~/.codex/agents
cp "$MODEL_ROUTER_HOME"/codex/agents/{sol,terra,luna}.toml ~/.codex/agents/
cat "$MODEL_ROUTER_HOME"/codex/config.example.toml >> ~/.codex/config.toml   # or merge by hand
# Pro home only (spark is GPT-5.3-Codex-Spark, its own quota pool; the proxy cannot serve it):
PRO="${CODEX_PRO_HOME:-$HOME/.codex-pro}"; mkdir -p "$PRO/agents"
cp "$MODEL_ROUTER_HOME"/codex/agents/spark.toml "$PRO/agents/"
cp "$MODEL_ROUTER_HOME"/codex/cua-headless.mjs "$PRO/"    # only if you will use "use computer use"
```

Optionally seed `~/.codex/AGENTS.md` from `codex/AGENTS.example.md` (one rule:
follow a spec or review contract exactly). Codex reads that file; Claude Code
reads `~/.claude/CLAUDE.md`; neither reads the other's, and this repo ships no
root `CLAUDE.md` or `AGENTS.md`, so cloning or installing it injects nothing
into your existing sessions.

`sol`, `terra`, and `luna` are what the parent Astra (or Sol) thread spawns for
routed builds. Without them the Codex side fails with an unknown-agent error.
`spark` is optional: Astra prefers it for mechanical steps when running natively
on the Pro home and falls back to `luna` when it is missing.
If you already have a `[model_providers.router]` block or a top-level `model =`
line, keep yours and skip those parts of the example.

## Step 3 - the proxy

Follow `README.md` steps 1-4 (install CLIProxyAPI, log in your ChatGPT account(s),
copy `proxy/config.example.yaml`). Start it with `scripts/start-proxy.ps1` or
`scripts/start-proxy.sh`. Verify:

```bash
curl -s "$MODEL_ROUTER_URL/v1/models" -H "Authorization: Bearer $(proxy-key)"
```

You should see `gpt-6-astra` and `gpt-5.6-sol` (or whatever your plan serves)
in the list.

## Step 3b - run the doctor

```bash
bash "$MODEL_ROUTER_HOME/scripts/doctor.sh"      # Mac / Linux / Git Bash
powershell -ExecutionPolicy Bypass -File scripts\doctor.ps1   # Windows
```

One line per check. `FAIL` lines are blockers with the fix named; `warn` lines
are optional pieces (Astra on a non-Pro plan, the Pro home login). Re-run it
until it ends with "All required checks passed."

## Step 4 - install into Claude Code

Plugin route (recommended - one command, updates with `git pull`):

```
/plugin marketplace add gojc31/fabstra-public
/plugin install model-router@gojc31
```

Commands are then `/model-router:fabstra <brief>`, `/model-router:fabsol <brief>`,
and the skills load as `model-router:fabstra`, `model-router:fabsol`,
`model-router:fable-mode`, `model-router:model-router`.

Manual route: copy `skills/*` into `~/.claude/skills/`, `commands/*.md` into
`~/.claude/commands/`, and `agents/*.md` into `~/.claude/agents/`. Then the
commands are plain `/fabstra` and `/fabsol`.

## AGENTS.md and CLAUDE.md in your own projects

- Pattern: tool-agnostic facts in `AGENTS.md`; a thin `CLAUDE.md` whose first line is `@AGENTS.md` plus Claude-only rules. The import is the deterministic way to give Claude the file.
- Claude Code, default policy (`claude-md-or-agents-md`): reads `AGENTS.md` on its own only when none of `CLAUDE.md`, `.claude/CLAUDE.md`, `CLAUDE.local.md` exists in the working directory or above (2.1.277+, and not in every session); `~/.claude/CLAUDE.md` and `.claude/rules/` always load alongside. Setting `pluginConfigs."agents-md@builtin".options.instructionFiles` to `claude-md-and-agents-md` loads both files.
- Codex: reads `AGENTS.md` from the project root (git root) down to the working directory, one file per directory, `AGENTS.override.md` first, then `AGENTS.md`, then any `project_doc_fallback_filenames` entry configured for that Codex home; combined budget `project_doc_max_bytes` (32 KiB default); no import syntax, so a pointer-only file delivers nothing. A non-git directory is searched at the working directory only.
- Treat the presence of a rule in a file as separate from a seat having received it: when a delegated Codex task must obey a safety or business rule, put it in the task's own prompt unless you have checked what that Codex home actually loads.
- This repository itself ships no root instruction file.

## Step 5 - the always-on rule (optional but how JC runs it)

Add this to your global `~/.claude/CLAUDE.md` so every hard task goes through
the method without being asked:

```markdown
## The Fable Method - always on

Applies to every non-trivial task. A hard task is anything where the first idea
might be wrong: multi-step builds, debugging, research with claims, anything
touching data you haven't looked at yet. On Fable 5.1 a real build goes through
`/model-router:fabstra` (Fable plans and never codes). On Opus 5, Sonnet 5, or
Haiku 4.5, invoke the `fable-mode` skill for any hard task.

Always: convert relative to absolute (dates, versions); confirm before
irreversible or outward-facing actions; preserve by default; script anything
mechanical repeating 3+ times; surface constraints before they bite.

Skip the gates entirely for trivial one-file edits and simple lookups.
```

## Two ChatGPT logins (optional)

The skills describe a routing policy where Astra runs natively on a Pro login
(`codex-pro`, `CODEX_PRO_HOME`) and the proxy is pinned to a second "team"
login for Sol / Terra / Luna (`proxy-pin team`). That is how JC's machine is
set up and it protects the Pro weekly window. With a single login:

- ignore `proxy-pin` and `PROXY_PRO_AUTHFILE`;
- point `CODEX_PRO_HOME` at your one `CODEX_HOME` (or leave `~/.codex-pro`
  and log in there once with `codex-pro login`);
- everything else works unchanged - the skills fall back to Sol review when
  Astra's quota is spent.

## Optional extras

- `scripts/codex-credit-check.py` + `register-credit-check.ps1` - a scheduled
  task that drops a Codex login out of the proxy rotation when it runs out of
  credits and puts it back when refilled. Windows only as written.
- `bench/` - the harness JC used to benchmark the Codex transport against the
  proxy (2026-09-04). Results are not shipped; `bench/run.sh` regenerates them.
- Browser / Computer Use / image generation sections in the fabstra skill assume
  Codex's Browser and Computer Use plugins on the Pro home and a dedicated
  Chrome profile at `%USERPROFILE%\ChromeAstra`. Skip them if you don't use
  those surfaces; nothing else depends on them. Headless Computer Use needs
  `codex/cua-headless.mjs` copied into the Pro home (Windows only; it drives
  `codex-computer-use.exe` from the desktop app's bundled runtime) and the
  `node_repl` / `cua_repl` MCP blocks copied from `~/.codex/config.toml` into
  the Pro home's `config.toml` - re-copy them after every Codex app update,
  the runtime hashes in those paths change.

## Moving to a second machine (a VM, a client box)

Nothing personal is in git: no logins, no keys, no proxy binary. On the new
machine, in order:

1. Sign in: Claude Code with your Claude login, the Codex desktop app (or
   `codex login`) with your ChatGPT login. One ChatGPT login is enough - see
   "Two ChatGPT logins" above for what to skip.
2. `git clone https://github.com/gojc31/fabstra-public` and set
   `MODEL_ROUTER_HOME` to the clone (Step 1).
3. Install CLIProxyAPI, copy `proxy/config.example.yaml` to
   `$CLIPROXY_DIR/config.yaml`, set your own `api-keys:` entry, log the
   ChatGPT account into the proxy (Step 3). The key never leaves the machine.
4. Copy `bin/` to `~/bin` and the Codex agents + provider block (Steps 2, 2b).
   With one login, `CODEX_PRO_HOME` can point at your only `CODEX_HOME`.
5. `/plugin marketplace add gojc31/fabstra-public` + `/plugin install model-router@gojc31`
   (Step 4), then the CLAUDE.md rule (Step 5) if you want it always on.
6. `bash scripts/doctor.sh` until it passes. `spark`, the Pro home login, and
   `cua-headless.mjs` are warn-only; everything else is a blocker.

Update later with `git pull` in the clone; the plugin route re-reads the
files, the manual route needs the copies redone.

## Your skills on another machine

`user-skills/` ships JC's own skills - brief, bro, careful, design-pass,
doctor-plus, grilling, hallmark, handoff, impeccable, prompt-master,
speed-pass, to-questionnaire, triage, wait-what, wizard, writing-for-agents -
and two agents, automation-governance-architect and
engineering-frontend-developer. fable-mode is not in that folder because the
plugin ships it. Licences and provenance: `user-skills/THIRD_PARTY.md`.

**Requirements**

- Git for Windows (git-scm.com): needed for `git clone` and for the bash installer.
- Python 3 on PATH as `python`: careful's and triage's hooks run
  `python <skills dir>\<skill>\guard.py`. pytest is needed only to run their tests.
  It must be a real install (python.org, tick "Add python.exe to PATH"): a fresh
  Windows machine has only the Microsoft Store stub, which does not run them.
- Node.js for impeccable's scripts (`scripts/*.mjs`).
- Optional: browser-harness, for speed-pass's browser mode and design-pass's
  screenshot check.
- design-pass expects hallmark and impeccable, both shipped here. It works
  without the Inspo MCP and without browser-harness.

**First install (Windows; the user name does not matter)**

1. Plugin, in Claude Code: `/plugin marketplace add gojc31/fabstra-public`, then
   `/plugin install model-router@gojc31`.
2. Clone the repo anywhere, e.g.
   `git clone https://github.com/gojc31/fabstra-public "$HOME\fabstra"`.
3. Preview: `powershell -ExecutionPolicy Bypass -File "$HOME\fabstra\scripts\install-user-skills.ps1" -DryRun`
4. Install: the same command without `-DryRun`. Start a new Claude Code session
   so it loads the skills.
5. Optional check: `cd "$HOME\.claude\skills\careful"; python -m pytest -q`, and
   the same in `triage`.

On Git Bash, macOS or Linux use `bash ~/fabstra/scripts/install-user-skills.sh --dry-run`,
then the same without the flag.

**What the installer does.** It copies each skill folder to
`~/.claude/skills/<name>` and each agent to `~/.claude/agents/` (with the agents'
licence as `user-skills-agents-LICENSE`, a name Claude Code ignores), writing the
real skills folder wherever the repo copy says `{{SKILLS_DIR}}` (careful's and
triage's hook paths, design-pass's cross-references). A skill folder or agent
file that already exists and differs is first backed up to
`~/.claude/backups/user-skills-<timestamp>/`, then replaced whole, so any file
you added inside a shipped skill folder is in that backup. Skills and agents
that are not in the repo are never touched. It prints new / updated /
unchanged per item. `-Home <dir>` (`--home <dir>`) installs under another
folder, for testing.

**Update**

1. `git -C "$HOME\fabstra" pull`, then run the installer again (dry run first if
   you like). Unchanged skills are left alone.
2. Plugin: `/plugin marketplace update gojc31`, then `/plugin update model-router@gojc31`.

**Refresh the export (JC's machine only)**

1. In JC's private model-router working copy, run
   `python scripts/export-user-skills.py` (it sits next to `port-to-fabstra.py`
   and is not part of this repo). It mirrors the listed skills from `~/.claude/skills` into
   `user-skills/`, applies its scrub table, writes the licences, `THIRD_PARTY.md`
   and `MANIFEST.txt`, then runs its leak gate over this whole repo (not `.git`)
   and exits non-zero on any hit. If a scrubbed source line has changed, the
   export stops and names it: update the scrub table and rerun. `--scan-repo`
   runs the repo-wide gate alone, for example after a port.
2. Check `git diff --stat user-skills/`, then do the usual port, mirror and push
   steps.
3. Licence texts live in `user-skills/_licenses/`, fetched with
   `gh api repos/<owner>/<repo>/contents/LICENSE --jq .content | base64 -d`, so the
   export runs offline.

## Where to go next

Read [USE-CASES.md](USE-CASES.md) - ten worked briefs covering fabstra,
the Astra solo lane, fable-mode on Sonnet, fabsol, headless workers, and
routed sessions.

## Troubleshooting

- `proxy-key: ... not found` - set `CLIPROXY_DIR` or `MODEL_ROUTER_KEY`.
- `codex shim: no codex.exe` - install the Codex desktop app, or edit the shim's
  `d=` line to your Codex CLI location.
- Nothing on 8317 - start the proxy (`scripts/start-proxy.*`); the skills retry
  once and then stop rather than fall through to a paid API.
- Astra `model not found` - your ChatGPT plan doesn't serve `gpt-6-astra`; the
  fabstra skill's "Fallback reviewer" section covers running with Sol only.
