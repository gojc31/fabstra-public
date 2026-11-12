![model-router](assets/banner.png)

> **This is JC's fork.** It adds the **FabStra** flow (`/model-router:fabstra`), the
> Claude build and review agents it calls, and the shell shims it depends on, and it replaces every
> machine-specific path with an env var. **Start with [SETUP.md](SETUP.md)** - it is the
> short version of everything below plus the fork-specific pieces. Original work by
> RoboNuggets under CC BY 4.0; install with `/plugin marketplace add gojc31/fabstra-public`
> then `/plugin install model-router@gojc31`. Worked examples of every flow are in
> [USE-CASES.md](USE-CASES.md).

# model-router

Run Claude Code on every subscription you already pay for.

Your main Claude session stays exactly as it is. This resource adds a local
"switchboard" (a proxy) that holds your OTHER subscription logins - ChatGPT,
Gemini, Grok, Kimi - and lets Claude Code send work to those models three
ways: as headless build workers, as whole terminal or VSCode sessions, or as
subagents. No API keys, no per-token bills - just the subscriptions you
already have. Every default (model, effort, turn cap) is changeable.

## FabStra - the flow that combines them

**FabStra lives in its own folder: [`skills/fabstra/`](skills/fabstra/SKILL.md).**
It is the flagship of this resource, and one flow serves every Claude session
model. Claude Fable 5.2 always orchestrates - it plans, writes one
self-contained spec per task (outcome, invariants, interfaces and file
ownership, acceptance, verification), routes, and arbitrates, and never
writes code. Claude Opus 5.5 orchestrates the same way when the plan has 2+
independent tasks or touches an excluded category (money, auth, PII,
permissions, data migration, concurrency, a client-facing release), and
otherwise leads (Lead mode: it plans, builds or delegates by tier, and
arbitrates); Claude Sonnet 5.5 and Haiku 5.5 always lead. Claude Opus 5.5
subagents build, all on your normal Claude login, never through the proxy,
and each seat pins its effort by tier: `builder-low` (mechanical),
`builder-medium` (contract), `builder-high` (hard), and `builder` at xhigh
(hard work in an excluded category, or any task after its second miss at
high; the miss ladder otherwise moves a task one seat up). The
gate seat - GPT-6 Astra for an excluded category, an architecture or
data-model decision, or a plan whose check you cannot state; GPT-6.1 Sol for
every other real build - critiques the plan before any builder launches,
parents the Codex side (spawning the `sol`, `terra`, `luna` and `spark` Codex
agents for routed tasks), and adversarially reviews Claude-built work. A
fresh Fable 5.2 context with read-only tools (`reviewer` at high,
`reviewer-xhigh` on a build in an excluded category) reviews Codex-built work
and adds a parallel second review on xhigh rows, so builder and reviewer are
different model families. Astra and Sol run on your ChatGPT logins through
the proxy or the Codex CLI, moving that burn onto the second subscription's
spare capacity; the skills' standing fast window sends gates, reviews and
Codex-side builds to fast native Codex homes first, with the proxy as the
fallback (SETUP.md, "Two ChatGPT logins"). The working discipline includes a durable run logbook
(`.fabstra/RUN.md`), test-first builds with a four-state builder status
protocol, a smoke gate before any review, severity- and confidence-gated
review findings that the lead accepts or rejects with a logged line, a miss
ladder that moves a task one seat up after its second miss, and a short
report that separates verified from assumed. Lanes beyond the default: B
("astra solo" - Astra designs and builds, Sol xhigh and a fresh Fable
review), C (an explicit budget ask - a cheap OpenRouter crew through the
proxy, never for an excluded category), and D (a proxy session model leads).

Invoke it as `/model-router:fabstra <brief>` (plugin install) or `/fabstra <brief>`
(manual install). `/model-router:fabsol` and the `fable-mode` skill are retired
aliases: run `/model-router:fabstra` instead, and name Sol in the brief (`sol`,
`sol xhigh`) to pin Sol for the gate seats. Everything else in this resource
exists to support that flow.

## Play it safe (read this first)

Anthropic's terms (updated Feb 2026) ban using a Claude **subscription** login
inside third-party tools - so this resource NEVER routes your Claude login
through the proxy. The design is one-directional: Claude Code runs on its
normal direct login and REACHES OUT to the other models. Keep it that way.

## What's inside

| Folder | What it is |
|---|---|
| `skills/fabstra/` | **the FabStra flow** (the flagship) - the session switch (Fable 5.2 orchestrates; Opus 5.5 orchestrates or leads; Sonnet 5.5 / Haiku 5.5 lead), the routing rubric, the Claude seats, the Astra / Sol gate seat, and Lanes B ("astra solo": Astra designs and builds, Sol xhigh and a fresh Fable both review, the lead rules on every finding), C (budget crew) and D (routed orchestrator); `references/` holds the long form |
| `skills/fabsol/` | retired alias - run `/model-router:fabstra` and name Sol in the brief |
| `skills/fable-mode/` | retired alias - run `/model-router:fabstra`; Sonnet 5.5 / Haiku 5.5 sessions run fabstra's Lead mode, and Opus 5.5 sessions orchestrate at 2+ independent tasks or an excluded category, else lead |
| `bin/` | `codex`, `codex-pro`, `codex-fast`, `proxy-key`, `proxy-pin` shims - copy to `~/bin` (see SETUP.md) |
| `codex/` | `agents/sol,terra,luna,spark.toml` - the Codex custom agents the Astra / Sol parent thread spawns (`spark` is Pro-home only); `cua-headless.mjs` - headless Computer Use for "use computer use" runs (Windows); `config.example.toml` - the router provider block for `~/.codex/config.toml`; `AGENTS.example.md` - the one Codex-side rule the flows rely on |
| `scripts/doctor.sh` / `.ps1` | readiness check: env, shims, proxy, models, Codex CLI, agents, plugin |
| `skills/model-router/` | the routing knowledge - three usage modes, model switching |
| `commands/fabsol.md` | command for the retired fabsol alias - run `/model-router:fabstra` instead |
| `commands/fabstra.md` | thin command that invokes the fabstra skill with your brief |
| `agents/` | the Claude seats fabstra calls - `builder-low`, `builder-medium`, `builder-high`, `builder` (Opus 5.5 at low / medium / high / xhigh), `reviewer` and `reviewer-xhigh` (fresh Fable 5.2 at high / xhigh), `sonnet-max` (only on a "sonnet max" pin) - plus `worker.md`, the build-worker subagent for routed sessions |
| `scripts/` | start-proxy, worker, session, vscode - each as `.sh` (Mac/Linux) and `.ps1` (Windows) |
| `proxy/config.example.yaml` | ready-to-copy proxy config |

## Install - steps for the agent setting this up

Work through these in order. Ask the user for their preference where a step
offers a choice.

**Step 1 - install the proxy.** Download the latest
[CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI/releases) release
for the user's OS and unzip it somewhere stable (suggest `~/cli-proxy-api`).

**Step 2 - configure it.** Copy this resource's `proxy/config.example.yaml`
to `config.yaml` next to the proxy binary. Have the user pick their own value
for the `api-keys` entry (any string - it is the local password between
Claude Code and the proxy; `my-proxy-key` is the placeholder this README
assumes).

**Step 3 - log in to the other subscription(s).** Run from the proxy folder;
each opens a browser once and stores the login locally in `~/.cli-proxy-api`:

```bash
./cli-proxy-api -config config.yaml -codex-login        # ChatGPT / Codex (default worker)
# also available, same pattern:
#   -antigravity-login   Google Antigravity / Gemini
#   -xai-login           xAI Grok
#   -kimi-login          Kimi
```

**Step 4 - set the four env vars** in the user's shell profile (these are the
shipped defaults - see "Change the defaults" below):

```bash
# Mac/Linux (~/.zshrc or ~/.bashrc)
export MODEL_ROUTER_URL="http://127.0.0.1:8317"
export MODEL_ROUTER_KEY="my-proxy-key"        # the key from step 2
export MODEL_ROUTER_MODEL="gpt-5.6-sol"       # default worker model
export MODEL_ROUTER_EFFORT="low"              # default worker effort
```

```powershell
# Windows (persist once, from PowerShell)
[Environment]::SetEnvironmentVariable("MODEL_ROUTER_URL", "http://127.0.0.1:8317", "User")
[Environment]::SetEnvironmentVariable("MODEL_ROUTER_KEY", "my-proxy-key", "User")
[Environment]::SetEnvironmentVariable("MODEL_ROUTER_MODEL", "gpt-5.6-sol", "User")
[Environment]::SetEnvironmentVariable("MODEL_ROUTER_EFFORT", "low", "User")
```

**Step 5 - install the pieces into Claude Code.** Two options, either works:

- *Plugin route:* run `/plugin marketplace add gojc31/fabstra-public`
  then `/plugin install model-router@gojc31`. Commands are namespaced:
  `/model-router:fabstra`.
- *Manual route:* copy `skills/fabstra/` and `skills/model-router/` (plus the
  retired `skills/fabsol/` and `skills/fable-mode/` aliases, if you want those
  names to point you to fabstra) into `~/.claude/skills/`, `commands/*.md` into
  `~/.claude/commands/` (gives plain `/fabstra`), and `agents/*.md` (the
  build, review and worker seats) into `~/.claude/agents/`.
- *Either route:* copy `bin/` to `~/bin` and put `~/bin` on PATH (SETUP.md,
  Step 2), install the OpenAI Codex plugin for Claude Code (SETUP.md, "What
  you need"), copy `codex/agents/{sol,terra,luna}.toml` into `~/.codex/agents/`
  (and `spark.toml` into `$CODEX_PRO_HOME/agents/`), and merge
  `codex/config.example.toml` into `~/.codex/config.toml`.

**Step 6 - verify.** Start the proxy (`scripts/start-proxy.sh` or `.ps1`),
then confirm the worker model is served:

```bash
curl -s "$MODEL_ROUTER_URL/v1/models" -H "Authorization: Bearer $MODEL_ROUTER_KEY"
```

With the proxy running, run `scripts/doctor.sh` (or `.ps1`) to confirm every
piece is in place - it fails without a proxy answering, and it checks that the
proxy serves the models the Codex agents and skills pin (`gpt-6.1-sol`,
`gpt-6.1-terra`, `gpt-6-luna`; `gpt-6-astra` and the worker default
`gpt-5.6-sol` warn only). Re-run it until it ends with "All required checks
passed."

Then run one cheap end-to-end test:

```bash
scripts/worker.sh "Reply with exactly: routing works"    # Windows: scripts\worker.ps1 "..."
```

If both answer, the setup is live. Try `/model-router:fabstra build me a small test page`.

## Your skills on another machine

`user-skills/` carries JC's own Claude Code skills (17) and two agents, scrubbed for
sharing; every vendored one keeps its upstream licence
([user-skills/THIRD_PARTY.md](user-skills/THIRD_PARTY.md)). After cloning this repo:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install-user-skills.ps1 -DryRun   # preview
powershell -ExecutionPolicy Bypass -File scripts\install-user-skills.ps1
```

On Git Bash, macOS or Linux: `bash scripts/install-user-skills.sh [--dry-run]`. To update,
`git pull` and run it again. Full steps and requirements: [SETUP.md](SETUP.md), "Your
skills on another machine".

## Keep the setup clean - `/audit-kit`

`user-skills/skills/audit-kit` holds every audit JC runs on a Claude Code machine, in one
user-invoked skill: `doctor` (install, settings, hooks, plugins, MCP, processes,
disk), `context` (doctor-plus: always-loaded context vs the six context-engineering
shifts), `prompts` (Anthropic's prompt-audit guide plus a drift pass), `skills`
(usage from transcripts, limits, overlaps, trigger clashes), `memory` (MEMORY.md
size and stale items), `loss` (did a fix pass drop anything) and `leak` (names,
emails, home paths and secrets before a public push). Each audit is read-only and
writes `~/.claude/audits/<date>/REPORT.md`; fixes run only after you approve them,
with backups first. Run `/audit-kit` (all five main audits) monthly, `/audit-kit doctor`
after a CLI upgrade, `/audit-kit prompts` when a new Claude model ships, and
`/audit-kit leak` before publishing a repo.

## Change the defaults (everything is adjustable)

The resource SHIPS with: worker = `gpt-5.6-sol`, effort = `low`,
turn cap = `20`. Change any of them:

| What | How |
|---|---|
| Worker model, script default | set `MODEL_ROUTER_MODEL` to any ID your proxy serves - it changes the default of `scripts/worker.*` and `scripts/session.*` only; the `worker` subagent pins its own model in the `model:` line of `agents/worker.md` (edit that line to change it), and the FabStra seats pin theirs |
| Worker model, one call | pass it as an argument (`scripts/worker.sh "task" gemini-3.5-flash`); in a `/model-router:fabstra` brief, naming `sol` pins Sol for the gate seats |
| Worker effort | set `MODEL_ROUTER_EFFORT` (`low` ships; raise to `medium` if builds miss acceptance criteria - higher mostly burns tokens: in our tests xhigh made the worker grind 2-3x more turns for the same output) |
| Turn cap | edit `--max-turns 20` in `scripts/worker.*` (one-shot workers); the proxy design-review and review calls keep `--max-turns 30`, which `skills/fabstra/references/transport.md` says never to raise |
| Proxy address / key | the proxy's `config.yaml` sets where it listens (`host`, `port`) and the keys it accepts (`api-keys`); `MODEL_ROUTER_URL` / `MODEL_ROUTER_KEY` tell the worker, session and VSCode scripts, `scripts/start-proxy.sh` and the doctor where it is and which key to send (`scripts/start-proxy.ps1` reads only the URL's port). The fabstra skill's proxy commands and the Codex `router` provider (`codex/config.example.toml`) use `http://127.0.0.1:8317` as written, so keep the proxy there for the flow |

**Which models can you point at?** Any ID your proxy serves. Discover them:

```bash
curl -s "$MODEL_ROUTER_URL/v1/models" -H "Authorization: Bearer $MODEL_ROUTER_KEY"
```

| Provider | Login flag | Example models |
|---|---|---|
| OpenAI / Codex | `-codex-login` | `gpt-5.6-sol` (the worker scripts' default), `gpt-6-astra`, `gpt-6.1-sol`, `gpt-6-luna`, GPT-5.5 family |
| Google Antigravity / Gemini | `-antigravity-login` | Gemini 3.5 Flash, Gemini 3.1 Pro, newer tiers where served |
| xAI Grok | `-xai-login` | Grok 4.5, Grok Composer 2.5 Fast |
| Kimi | `-kimi-login` | Kimi K2.7 Code, K2.6 |
| Google Vertex | `-vertex-import key.json` | your Vertex-served models |

Only providers you've logged into appear. Model IDs vary by CLIProxyAPI
version - always trust your own `/v1/models` list over this table.

## Launch Claude Code ON the routed model

Besides FabStra (where your normal session delegates), you can run a whole
Claude Code session on the routed model:

**Terminal:**

```bash
scripts/session.sh              # default worker model
scripts/session.sh grok-4.5     # any model your proxy serves
```

Windows: `scripts\session.ps1 [model]`. Or by hand - set the two env vars and
launch (scoped to that terminal, closes with it):

```powershell
$env:ANTHROPIC_BASE_URL = "http://127.0.0.1:8317"
$env:ANTHROPIC_AUTH_TOKEN = "my-proxy-key"
claude --model gpt-5.6-sol
```

**VSCode:**

```bash
scripts/vscode.sh [folder]      # Windows: scripts\vscode.ps1 [folder]
```

Opens a VSCode window whose Claude Code sessions run on the routed model. It
uses a separate VSCode profile folder on purpose: an already-running VSCode
ignores env vars from new launches, so this is the way that always works.
Alternative if you prefer your normal profile: fully close VSCode, set the two
env vars in a terminal, then run `code .` from that terminal.

In a routed session (terminal or VSCode), the plugin's `worker` subagent
resolves too - so even subagents run on routed models there.

## Troubleshooting

- **"Connection refused" on delegation** - the proxy isn't running. Run the
  start-proxy script.
- **Auth error from the proxy** - your provider login expired. Re-run the login
  flag for that provider (step 3).
- **"Unknown provider for model X"** - that provider isn't logged in, or the ID
  is wrong. Check the `/v1/models` list.
- **VSCode window doesn't route** - VSCode was already running with its normal
  env. Use `scripts/vscode.sh` (Windows: `scripts\vscode.ps1`; separate
  profile), or close VSCode fully first.
- **Worker output is weak** - the spec is doing too little work. The
  orchestrator must make every creative/architectural call in the spec; the
  worker just types. Raising `MODEL_ROUTER_EFFORT` to `medium` is the second lever.

## License

CC BY 4.0 - free to use, adapt, and share with attribution to RoboNuggets (original) and JC / gojc31 (this fork). See LICENSE.
