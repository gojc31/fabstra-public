# FabStra transport - the crew, the routing policy, and every launch command

Contents: The crew in full (crew table, routing policy); Sol pin; Standing fast window: reviews (retired 2026-10-17); Codex transport; Codex write probe; Reviewer fallback; Phase 1b launch - DESIGN REVIEW; Phase 3 launch - ADVERSARIAL REVIEW

Reached from: fabstra SKILL.md - before the first proxy or Codex launch of a run

Related:
> "Astra blocked, how to read it", the quota windows and the fast pin are in quota.md.
> The spec templates these launches carry are in specs.md; the phase procedure is in phases.md.
> the pairing rule -> phases.md
## The crew in full

| Role | Model | How it runs |
|---|---|---|
| ORCHESTRATOR - align, plan, blueprint, route, arbitrate, report | Claude Fable 5.1, or Claude Opus 5.5 at or above the Orchestrate threshold (SKILL.md) (session model) | this session; never builds, never edits code; owns every decision |
| LEAD (Lead mode) - plan, build or delegate by tier, arbitrate, report | Claude Opus 5.5 / Sonnet 5.5 / Haiku 5.5 (session model) | this session; builds the authoritative plan and owns every decision - lead-mode.md |
| DESIGN REVIEWER - critiques the plan and blueprints before build | GPT-6 Astra on the Astra row, GPT-6.1 Sol on the Sol row (gate seat rubric, SKILL.md), effort per the effort rubric | `claude -p` through the local proxy, read-only tools, background Bash call (Phase 1b); Codex transport read-only is its fallback |
| BUILDER - complex implementation | Claude Opus 5.5 at xhigh | Agent tool subagent, `subagent_type: "model-router:builder"` (it pins its own model and effort); `model-router:builder-medium` on alternate tasks during the effort trial (SKILL.md, Effort) |
| SUPPORT - well-specified medium tasks | Claude Sonnet 5.5 | Agent tool subagent, `model: "sonnet"` |
| SONNET MAX - Sonnet-tier tasks, only when the user pins it | Claude Sonnet 5.5 at max | Agent tool subagent, `subagent_type: "model-router:sonnet-max"` (pins its own model and effort); rule: phases.md routing rubric, Sonnet max pin |
| MECHANIC - lookups, commands, single-file mechanical edits | Claude Haiku 5.5 | Agent tool subagent, `model: "haiku"` |
| MECHANIC (multi-file) - mechanical edits spanning 2+ files | Claude Opus 5.5 at low | Agent tool subagent, `subagent_type: "model-router:builder-low"` (it pins its own model and effort); outside the effort trial, logged `arm=builder-low eligible=no` |
| BUILDER (routed) - the Codex side, keep Claude usage down | the gate seat (Astra on the Astra row, Sol on the Sol row) as the parent thread, effort per the rubric | headless on the Codex CLI through the Codex transport below (`task --background --write --model gpt-6-astra`); Astra spawns the `sol` (GPT-6.1 Sol xhigh, Opus-tier), `terra` (GPT-5.6 Terra high, Sonnet-tier), `luna` (GPT-6 Luna medium, mechanic), and `spark` (GPT-5.3-Codex-Spark medium, fast mechanic; Pro home only, its own quota pool so it never draws on the general Codex window) custom agents from `~/.codex/agents` (`spark` only in `~/.codex-pro/agents`) |
| SOLO BUILDER (Lane B) - designs and builds a task end to end from a brief | GPT-6 Astra, xhigh (Sol xhigh when Astra's quota is spent) | `claude -p` through the local proxy, acceptEdits, no `--bare` so CLAUDE.md and skills load; see lane-b.md |
| REVIEWER A - adversarial review of Claude-built work | GPT-6 Astra on the Astra row, GPT-6.1 Sol on the Sol row (gate seat rubric, SKILL.md), effort per the rubric | `claude -p` through the local proxy, read-only tools, background Bash call (Phase 3); Codex transport read-only is its fallback |
| REVIEWER B - Astra's quota fallback for Claude-built work | GPT-6.1 Sol, at the same effort the Astra call would have used | same `claude -p` command with `--model gpt-6.1-sol`; Codex transport read-only is its fallback; never reviews Codex-built work (same family) |
| REVIEWER C - adversarial review of Codex-built work; also the parallel second reviewer on an xhigh row (pairing rule, phases.md); fallback only when the proxy itself is down, or for excluded work when Astra and Sol are both cooling (Astra and Sol both cooling otherwise routes the review seat and the Phase 1b design gate to Lane C instead) | fresh Claude Fable 5.1 context | Agent tool, `subagent_type: "model-router:reviewer"` (read-only tools enforced), same review spec |
| PRO CONSULT - advisory second opinion, never a gate or review seat | GPT-6 Astra Pro (`chatgpt-web/gpt-6-pro`) on JC's ChatGPT Pro chat allowance | `astrapro` wrapper, background Bash; see pro-consult.md |
| BUDGET CREW (Lane C) - orchestrator, build, and review when Claude and every ChatGPT login are both spent | `glm-5.3-flash` orchestrates; `deepseek-v4.1-flash` builds all coding (empty-200 retry, `glm-5.3-flash` fallback); `glm-5.3-flash` and `deepseek-v4-pro` review; `deepseek-v4-flash` takes the design gate and mechanic - all OpenRouter, via the proxy | `claude -p` through the local proxy only - no Agent tool, no Codex transport; see lane-c.md |
| ROUTED ORCHESTRATOR (Lane D) - the session model is itself a proxy model and leads the run | `gpt-6-astra` (default) or `glm-5.3-flash`; not `deepseek-v4.1-flash` (0/5 as lead, see Lane D) | the session; spawns proxy-served seats through the Agent tool (`model-router:worker` / `support-routed` / `mechanic-routed` / `builder-budget` / `reviewer-routed` / `astra-routed` / `deepseek41-routed`). Claude seats only by stripped-env headless `claude -p`, never the Agent tool - see lane-d.md |

**Routing policy.**
Astra is the default senior seat for every Astra-eligible call - design
review, build parent, adversarial review - and it rides the proxy like every
other model, rotating over every ChatGPT login in the proxy (`verify-codex-logins`
lists them; six on 2026-09-12: $CODEX_BIZ_LOGIN premium, $CODEX_BIZ2_LOGIN,
three $CODEX_TEAM_LOGIN seats, gojc31 Pro).
Companion launches for Astra run on the main Codex home with no `CODEX_HOME`
/ `CODEX_DIRECT` prefix (except during the standing fast window in quota.md,
on since 2026-09-28, no end date: native, round-robin over `.codex-pro` / `.codex-biz` via `codex-fast-home`); the `codex` shim adds `-c model_provider=router`.
The standing pin is `proxy-pin both`; check `proxy-pin status` at the start
of a run and log it, and pin `team` only when JC asks by name. Two native
homes are opt-in, each for what only it can do, and a run that needs one
launches its Astra parent natively and says so in the logbook: `.codex-pro`
(`codex-pro` shim, gojc31 Pro) is the FAST-PIN home (JC's standing choice
since 2026-09-14, after the Business seat ran out of credits) and keeps the
Browser / Computer Use / image_gen surfaces and `spark`; `.codex-biz`
(`codex-biz` shim, or the `CODEX_HOME="${CODEX_BIZ_HOME:-$HOME/.codex-biz}"
CODEX_DIRECT=1` prefix; $CODEX_BIZ_LOGIN Business premium seat, added
2026-09-10) is opt-in only when JC asks for it by name. **Sol holds the Sol row of the gate seat rubric (SKILL.md) without being named, and stays one word away for every other seat:** a brief that names Sol (`sol`, `gpt-6
sol`, `gpt-6.1 sol`, `sol xhigh`) pins Sol for that seat instead of Astra, the Sol effort
rubric and the Sol builder tier are unchanged, and Reviewer A/B seats keep
their existing rules. Sol cooling on the Sol row with Astra available -> Astra at the Sol row's effort for that seat, logged "Sol quota spent, Astra gated/reviewed". When Astra is spent on every login, or Sol and Astra are both cooling, or the proxy is down, the seat falls back by the table in "Reviewer fallback" below (one table for the design gate and Reviewers A/B/C; excluded work never takes a Lane C seat - SKILL.md, Excluded categories).
`--output-format json` with the spec fed on stdin (`< spec.md`, so stdin
reaches EOF) is what stops the nested `claude -p` from hanging after it
prints; the spec is not a command-line argument, so its length is not
capped (a 40 KB spec has passed); the commands below carry both.

## Sol pin

**GPT-6.1 Sol (2026-09-30).** Every Sol seat runs `gpt-6.1-sol` (released 2026-09-29; same price as GPT-6 Sol, cached input half). Native Codex launches need Codex CLI 0.159.2 or later: the desktop app's bundled 0.158.0-alpha.2.1 rejects the model, so `%LOCALAPPDATA%\OpenAI\Codex\bin\npm-0.159.2\` holds the npm 0.159.2 binaries and the `codex` shim picks it as the newest folder; delete that folder to roll back. Since 2026-10-13 the model list advertises the fast (`priority`) tier for `gpt-6.1-sol` ("2x speed, increased usage"), and a native fast home sends `tier=priority` for Sol exactly as for Astra (verified by trace on `.codex-pro`), so the fast pin and the standing fast window speed Sol calls too. Sol through the proxy (`claude -p`, `bcode sol`) stays at standard speed: fast reaches only a native home. **500k window (2026-10-13).** OpenAI raised `gpt-6.1-sol`'s default context to 500k on 2026-10-12; Claude Code assumes 200k for a model id it does not know and compacts there. So every proxy `claude -p` launch with `--model gpt-6.1-sol` puts `CLAUDE_CODE_MAX_CONTEXT_TOKENS=500000` in its env prefix next to `ANTHROPIC_BASE_URL` (verified: `modelUsage` contextWindow 200000 -> 500000). Never on `gpt-6-sol` (272k) or an Astra launch. Native Codex picks 500k up from the model list by itself. Fallback pin: a `gpt-6.1-sol` call that fails with a model-not-supported or unknown-model error re-runs once with `--model gpt-6-sol` at the same effort, logged "6.1 unavailable, gpt-6-sol ran".

A brief that names Sol (`sol`, `gpt-6 sol`, `gpt-6.1 sol`, `sol xhigh`) pins Sol for the Astra
seats: builds and reviews run the same commands with `--model gpt-6.1-sol`, at
the rubric row's effort or the user's effort word, which pins every Sol call
in the run, build and review.

- **Sol builds on the Codex transport** (`task --background --fresh --write
  --model gpt-6.1-sol ...`, job id in `<scratch>/sol-job-<name>.txt`): native
  sandbox and `spawn_agent`. A Sol parent does the Opus-tier work itself and
  spawns only `terra` (contained sub-task with a written contract) and `luna`
  (mechanical; `spark` natively on Pro), never `sol`; leave the delegation
  clause out for a task that fits one thread - each spawn costs a fresh
  context.
- **Sol as parent - the delegation clause changes.** When Sol holds the parent seat, do not paste the specs.md parent-thread clause; paste this complete Sol-parent clause instead: "You are the parent thread. Do multi-file and design-level sub-tasks yourself; spawn `terra` for a self-contained sub-task with a written contract and `spark` for mechanical steps (`luna` if `spark` is not defined in your home); never spawn `sol`. You own the plan as written, the integration, and the single final report; pass each sub-agent its slice of the blueprint and the stack rules verbatim and the same DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED protocol; never delegate your own verification. Sub-agents you spawn never spawn agents of their own. The blueprint fixes the interface, the file set, and the acceptance criteria: keep those. Inside them, resolve implementation details yourself rather than stopping, and list each decision in your report. Return NEEDS_CONTEXT only when the blueprint contradicts the repository or would require changing an interface or a file the spec did not name. You are done when every acceptance criterion passes and the integration works - not at a first implementation."
- **Sol reviews through the proxy `claude -p`** (the Phase 3 command with `--model gpt-6.1-sol`). Evidence for this transport predates 6.1: benchmarked 2026-09-04 on the 5-bug fixture with the Sol of that day, xhigh, n=3 each - proxy 112-203 s, Codex 195-337 s, identical recall (5/5) and zero false positives on both - and it can save the findings file, which the Codex read-only sandbox cannot. Each transport is the other's fallback.
- **Pairing under the pin:** Claude built -> Sol reviews; Sol built -> the
  fresh Fable (Reviewer C); Sol never reviews Sol.
- `/codex:adversarial-review` takes no effort flag and cannot be invoked by
  the orchestrator, so it is not a transport.
- Runs started under the retired `/fabsol` kept their logbook at
  `.fabsol/RUN.md`: resume such a run from there; new runs write
  `.fabstra/RUN.md`.

## Standing fast window: reviews (retired 2026-10-17)

From 2026-10-17 (JC) the design review and Reviewer A/B use the proxy
`claude -p` commands in "Phase 1b launch" and "Phase 3 launch" below as
primary, rotating every login at standard speed. The fast window covers
builds only (quota.md). The read-only Codex transport fallback for a review
keeps the `codex-fast-home` prefix of the Codex transport section. The old
recipe is in the 2026-10-17 backup of this file.

## Codex transport (the gate seat as parent for routed builds and Codex-column fixes; read-only fallback for both reviews) - launch and wait inside one background Bash call

`$C` = `$(ls -d ~/.claude/plugins/cache/openai-codex/codex/*/scripts/codex-companion.mjs | sort -V | tail -1)`
(the version segment moves when the codex plugin updates - `ls` the parent
directory if the path fails). Every Codex call is two Bash calls from the
orchestrator; the `codex:rescue` skill is not a fabstra transport.
The local proxy CLIProxyAPI 7.3.12 (upgraded and verified 2026-09-23;
7.2.157 did not know them) serves `gpt-6-astra`, `gpt-6-sol` and
`gpt-6-luna`, so GPT-6 Sol and GPT-6 Luna run both through the proxy and on
the native Codex homes. `gpt-6.1-sol` verified served 2026-09-30 (proxy 7.3.12; native Codex needs CLI 0.159.2+).

1. **Launch + wait** - one Bash call with `run_in_background: true`, timeout
   600000, cwd = the project directory. The standing fast window (on since 2026-09-28, no end date; quota.md) covers builds
   (`--write`) as well as reviews, so the block opens with the native-home prefix: no on/off. A fast pin on a run with the window closed: `codex-fast on`
   once before the first launch, `codex-fast off` after the last native job
   of the run - the companion has no `-c` passthrough, the config switch is
   the only door, and a fast run puts `CODEX_HOME="${CODEX_PRO_HOME:-$HOME/.codex-pro}"
   CODEX_DIRECT=1` in front of the launch below because the tier reaches only
   a native home, and JC put fast on that login:
   ```bash
   H=$(codex-fast-home) || H=; echo "home=${H:-router}"
   if [ -n "$H" ]; then export CODEX_HOME="$H" CODEX_DIRECT=1; else unset CODEX_HOME CODEX_DIRECT; fi
   node "$C" task --background --fresh [--write] --model gpt-6-astra --effort <per the effort rubric> --prompt-file <scratch>/fabstra-<name>.md | tee <scratch>/astra-job-<name>.txt
   J=$(grep -oE "task-[a-z0-9]+-[a-z0-9]+" <scratch>/astra-job-<name>.txt | head -1); echo "job=$J"
   node "$C" status "$J" --wait --timeout-ms 3300000 --poll-interval-ms 30000 --json
   ```
   Drop the two prefix lines only when JC turns the standing window off
   (quota.md says how); an empty `H` means every fast home is skipped, and
   the `unset` makes the launch a router launch (standard tier) even if the
   shell inherited a native selection - log `fast window: all homes skipped,
   router launch`. Surface jobs (surfaces.md, Codex surface rules) keep
   `CODEX_HOME="${CODEX_PRO_HOME:-$HOME/.codex-pro}"` and do not use the picker.
   `--prompt-file` hands the companion the spec file itself
   (codex-companion.mjs:614), so the seat never spends a tool call reading it
   and a seat without local file access still gets it; the path resolves
   against the launch cwd, so pass it absolute. `--write` for builds
   only; `--fresh` on every launch, including a NEEDS_CONTEXT re-send (which
   carries a REVISED spec with the answer folded in). Never use
   `--resume-last` or `--resume` in this flow: the companion has no per-job
   resume - both flags pick the newest task in the workspace and fail while
   any other task is running, so with parallel builders they would resume
   the wrong thread. The companion's effort flag stops at `xhigh` (`max` is
   rejected). The turn returns to you at once; the job id is in
   `astra-job-<name>.txt` within seconds; the notification arrives when the
   job ends. Write the next spec or slice-verify meanwhile. If the wait ends
   with the job still running, issue only the `status --wait` line again with
   that id (background Bash call) - do not relaunch.
   Why one call: the Codex child inherits the launching shell's Windows job
   object (verified 2026-09-04: `IsProcessInJob` true for a `--background`
   child), so it must be launched from a shell the harness keeps alive across
   turns - a background Bash call - not from a foreground call that a user
   message can kill.
2. **Fetch** - `node "$C" result <job-id>` from the same cwd (jobs are listed per
   workspace) and read the report from stdout. Verified 2026-09-05 with
   `--model gpt-6-astra`: launched, waited, fetched in 10 s.

## Codex write probe (once per folder, before the first CODEX-owned task)

Codex builds write through the Codex sandbox, which is blocked in some
folders (client-F and a client dashboard project hit EPERM on 2026-09-24; client-A
built and fixed through it the same week). Before the first `--write`
launch in a folder, run one probe job from that folder in a background Bash
call (`$C` resolved as in "Lead mode delta - transports", lead-mode-deltas.md).
Launch it on the environment the builds will use: the same picker and
prefix lines as the build launch above, except the picker is `peek`: the
probe reads the next home without advancing the round-robin, so the build
launch that follows (plain `codex-fast-home`) takes that same home. A probe
that advanced the state would hand the build the other home, and "probe that
home first" would never catch up:

```bash
H=$(codex-fast-home peek) || H=; echo "home=${H:-router}"
if [ -n "$H" ]; then export CODEX_HOME="$H" CODEX_DIRECT=1; else unset CODEX_HOME CODEX_DIRECT; fi
printf 'Probe task. Create the file .fabstra/codex-write-probe.txt containing the current UTC date and the word ok, then report DONE with the file path. Do nothing else.\n' > <scratch>/fabstra-probe-<name>.md
node "$C" task --background --fresh --write --model gpt-6.1-sol --effort low --prompt-file <scratch>/fabstra-probe-<name>.md | tee <scratch>/probe-job-<name>.txt
J=$(grep -oE "task-[a-z0-9]+-[a-z0-9]+" <scratch>/probe-job-<name>.txt | head -1); node "$C" status "$J" --wait --timeout-ms 600000 --poll-interval-ms 15000 --json
```

The file exists afterwards -> the folder passes on that home: log
`codex-write=ok <date> home=<home>` (the `home=` line the probe
echoed, or `router`) in RUN.md and carry the line into later logbooks of that folder. It
does not, or the report says EPERM / BLOCKED -> log `codex-write=blocked
<date> home=<home>`; a blocked home sends every CODEX-owned task bound for
it to BUILDER for the run. The verdict is per folder and home: a build whose
picker returns a home with no verdict for this folder probes that home
first (peek, probe, then launch the build: it gets the probed home), because
a router-home pass does not cover a native home. A
result stands until the Codex CLI, the companion, or the sandbox
config changes; then probe again. Never skip the probe by assuming.

## Reviewer fallback

One table for the design gate (Phase 1b) and Reviewers A/B/C (Phase 3). Every row is logged with its reason in RUN.md.

| Situation | Design gate | Reviewer A / B (Phase 3) |
|---|---|---|
| Astra available | Astra (Sol on the Sol row), effort per the rubric | Reviewer A: the gate seat, per the pairing rule (phases.md) |
| Astra available, Sol cooling (Sol row) | Astra at the Sol row's effort; log "Sol quota spent, Astra gated" | Astra at the Sol row's effort; log "Sol quota spent, Astra reviewed" |
| Astra spent on every login (proxy 429 "All credentials for model gpt-6-astra are cooling down", or every usage endpoint >= 95%) | Sol through the proxy at the same effort the Astra call would have used (the pin or the rubric row, never a fixed xhigh); log "design review by Sol, Astra quota spent" | Reviewer B: Sol, same effort, only after a Claude build; log "Astra quota spent, Sol reviewed at <effort>" |
| Astra and Sol both cooling, work not excluded | Lane C gate: the same read-only command with `--model deepseek-v4-flash --effort high --max-turns 30` (lane-c.md; the command ends `# excluded: no - <reason>`); log "design review by Lane C gate, Astra and Sol cooling" | Reviewer A (Lane C), `glm-5.3-flash`, cross-family to the DeepSeek builder (lane-c.md); log why |
| Astra and Sol both cooling, work excluded (SKILL.md, Excluded categories) | fresh Fable (Reviewer C), `model-router:reviewer`; log "same-family review, GPT seats cooling, Lane C excluded" | the same fresh Fable seat and log line - nothing sensitive leaves the Claude login |
| Proxy 8317 still dead after one restart (`powershell -NoProfile -File '$MODEL_ROUTER_HOME/scripts/start-proxy.ps1 (start-proxy.sh on Mac/Linux)'`, retry once) | fresh Fable (Reviewer C), logged as a same-family review | fresh Fable (Reviewer C), same log |

Never skip the design review on a real build because the gate seat is down; never run it twice with the same spec. Codex-built work always goes to Reviewer C (pairing rule), whatever this table says for Claude-built work. `--bare` children load no ~/.claude hooks: the excluded-work check runs on the parent's launch command, and the auth-JSON guard does not reach inside the child.

## Phase 1b launch - DESIGN REVIEW (the gate seat - Astra or Sol - before any builder launches)

Mandatory for real builds. The cheapest bug is one caught on paper: the gate seat
reads the plan, every blueprint, and the repository, and reports where the
design will fail before Opus spends twenty minutes building it.

**Transport (primary):** write the design-review spec to
`<scratch>/fabstra-design-<name>.md`, then one Bash call,
`run_in_background: true`, timeout 1600000 (above the child's `timeout 1500`: Claude Code 2.1.285+ stops a background command when its Bash timeout runs out, and 2.1.288 lifts that only for interactive sessions, so a `-p` parent still enforces it), cwd = the project directory:

```bash
KEY=$(proxy-key) || exit 1
ANTHROPIC_BASE_URL=http://127.0.0.1:8317 ANTHROPIC_AUTH_TOKEN="$KEY" timeout 1500 claude -p --model gpt-6-astra --effort <effort> --bare --max-turns 30 --permission-mode default --allowedTools "Read,Grep,Glob,Bash" --output-format json < <scratch>/fabstra-design-<name>.md > <scratch>/fabstra-design-<name>.md.out 2>&1
```
Sol row: the same command with `--model gpt-6.1-sol` (effort per the rubric: high; xhigh on its xhigh rows).

The report is the `result` field of the last JSON line in the `.out` file
(a warning line precedes it; `--output-format json` with the spec fed on
stdin (`< spec.md`, so stdin reaches EOF) is what stops the nested
`claude -p` from hanging after it prints; the spec is not a command-line
argument, so its length is not capped (a 40 KB spec has passed)). `--bare` skips CLAUDE.md, so the spec carries every stack rule. The
"unrecognized model, assuming 200k window" line is noise; Astra's real
window is 1.05M. Keep `--max-turns 30`. **Fallback:** the Codex transport
above without `--write` (read-only sandbox; the report arrives only through
`result`). **Astra blocked** (quota.md, "Astra blocked, how to read it"), Sol
cooling too, an excluded category, or a dead proxy: take the design gate
column of "Reviewer fallback" above. Never skip the design review on a real
build because the gate seat is down; never run it twice with the same spec.

While the gate seat reviews, do not launch builders. Do prepare: the review-spec
skeleton for Phase 3, the smoke-gate command, and the logbook entries.

## Phase 3 launch - ADVERSARIAL REVIEW (Astra, Sol, or a fresh Fable context)

Mandatory for real builds; skip only for a small change as Phase 1 defines
it, and say so in the report. Pick the reviewer by the pairing rule: Claude built -> Reviewer A (the gate seat: Astra on the Astra row, Sol on the Sol row); Codex side built -> Reviewer C (fresh Fable); a contained change (phases.md Phase 1): Claude built -> Sol at `--effort high`, Codex built -> Reviewer C, no second seat; a mixed build -> Reviewer A on the BUILDER tasks and Reviewer C on the CODEX tasks plus every seam, partitioned (pairing rule, phases.md); an xhigh row adds Reviewer C in parallel with Reviewer A on the BUILDER tasks; Astra blocked after a Claude build -> Reviewer B (Sol, same effort). The review spec template below is the contract for every reviewer
and every transport.

**Reviewer A through the proxy (primary; Astra row shown, Sol row swaps the model):** write the review spec to
`<scratch>/fabstra-review-<name>.md`, then one Bash call, `run_in_background: true`, timeout 1600000 (above the child's `timeout 1500`, same reason as the design call), cwd = the project directory:

```bash
KEY=$(proxy-key) || exit 1
ANTHROPIC_BASE_URL=http://127.0.0.1:8317 ANTHROPIC_AUTH_TOKEN="$KEY" timeout 1500 claude -p --model gpt-6-astra --effort <effort> --bare --max-turns 30 --permission-mode default --allowedTools "Read,Grep,Glob,Bash" --output-format json < <scratch>/fabstra-review-<name>.md > <scratch>/fabstra-review-<name>.md.out 2>&1
```
Sol row: the same command with `--model gpt-6.1-sol` at the rubric effort; a contained change (phases.md Phase 1): Claude built -> Sol at `--effort high`, Codex built -> Reviewer C, no second seat.

   The report is the `result` field of the last JSON line in the `.out` file. Astra on this path can write, so the spec's save line lands the findings file in scratch. `--bare` skips CLAUDE.md, so the spec must carry every stack rule. Keep `--max-turns 30`; never raise it. With the diff and callers front-loaded in the spec (below), 30 tool calls cover a normal review; a run that hits the ceiling still leaves its incremental findings file.

**Reviewer A, Astra on the Codex CLI (fallback):** use it when the
`claude -p` harness fails for a reason that is neither quota nor the proxy
itself: a non-zero exit with no `result`, or `claude -p` hanging past its
timeout. Run the Codex transport above without `--write` (read-only sandbox;
the report arrives only through `result <job-id>`, the save line is
harmless). `--fresh` on every launch. **Nothing listening on 8317 is not a
case for this fallback** - the Codex shims go through the same proxy, so
Astra and Sol are both unreachable: run
`powershell -NoProfile -File '$MODEL_ROUTER_HOME/scripts/start-proxy.ps1 (start-proxy.sh on Mac/Linux)'`
(it exits 1 naming the port and exe when it cannot start), retry once, and if
the port is still dead take the last row of "Reviewer fallback".

**Reviewer B, Sol (Astra's quota fallback):** the same proxy command with
`--model gpt-6.1-sol` and the same `--effort` the Astra call would have
used (the pin or the rubric row, not a fixed xhigh); the Codex transport
with `--model gpt-6.1-sol` is its fallback. Use only after a Claude build
when Astra is blocked. Log "Astra quota spent, Sol reviewed at <effort>".

**Reviewer C, fresh Fable 5.1 context:** one Agent tool call,
`subagent_type: "model-router:reviewer"` (Fable 5.1 with Read, Grep, Glob,
and Bash only, enforced by the agent definition), prompt = the review spec
verbatim. It has seen none of the build, which is the point - never paste
your session context into it. Run it as the review when the Codex side
built, and as the fallback "Reviewer fallback" names (log it as a
same-family review); Astra and Sol both cooling with the proxy still up is
that table's two "Astra and Sol both cooling" rows, work not excluded (Lane C
in lane-c.md) and work excluded (fresh Fable); pairing rule in phases.md.
