# FabStra transport - the crew, the routing policy, and every launch command

Contents: The crew in full (crew table, routing policy); Sol pin; Standing fast window: reviews (always on since 2026-11-01); Codex transport; Codex write probe; Reviewer fallback; Claude on credits seat (pool); Phase 1b launch - DESIGN REVIEW; Phase 3 launch - ADVERSARIAL REVIEW

Reached from: fabstra SKILL.md - before the first proxy or Codex launch of a run

Related:
> "Astra blocked, how to read it", the quota windows and the fast pin are in quota.md.
> The spec templates these launches carry are in specs.md; the phase procedure is in phases.md.
> the pairing rule -> phases.md
## The crew in full

| Role | Model | How it runs |
|---|---|---|
| ORCHESTRATOR - align, plan, blueprint, route, arbitrate, report | Claude Fable 5.2, or Claude Opus 5.5 at or above the Orchestrate threshold (SKILL.md) (session model) | this session; never builds, never edits code; owns every decision |
| LEAD (Lead mode) - plan, build or delegate by tier, arbitrate, report | Claude Opus 5.5 / Sonnet 5.5 / Haiku 5.5 (session model) | this session; builds the authoritative plan and owns every decision - lead-mode.md |
| DESIGN REVIEWER - critiques the plan and blueprints before build | GPT-6 Astra on the Astra row, GPT-6.1 Sol on the Sol row (gate seat rubric, SKILL.md), effort per the effort rubric | `claude -p` through the local proxy, read-only tools, background Bash call (Phase 1b); Codex transport read-only is its fallback |
| BUILDER (hard tier) - multi-file features, architecture or data-model decisions, tricky algorithms, integration surfaces, debugging where the first theory might be wrong | Claude Opus 5.5 at high | Agent tool subagent, `subagent_type: "model-router:builder"`, `effort: "high"` (it pins its own model; the call passes the effort); logged `seat=model-router:builder effort=high`; every tier and seat: phases.md, "Claude seat efforts" |
| BUILDER (hard tier, xhigh) - a hard-tier task in an excluded category (SKILL.md), or any task after its second miss at high | Claude Opus 5.5 at xhigh | Agent tool subagent, `subagent_type: "model-router:builder"`, `effort: "xhigh"` (it pins its own model; the call passes the effort); logged `seat=model-router:builder effort=xhigh` |
| SUPPORT (contract tier) - a self-contained change with a written contract | Claude Opus 5.5 at medium | Agent tool subagent, `subagent_type: "model-router:builder"`, `effort: "medium"` (it pins its own model; the call passes the effort); logged `seat=model-router:builder effort=medium` |
| SONNET MAX - contract-tier tasks, only when the user pins it | Claude Sonnet 5.5 at max | Agent tool subagent, `subagent_type: "model-router:sonnet-max"` (pins its own model and effort); rule: phases.md routing rubric, Sonnet max pin |
| MECHANIC (mechanical tier, any file count) - exact-text or known-pattern edits | Claude Opus 5.5 at low | Agent tool subagent, `subagent_type: "model-router:builder"`, `effort: "low"` (it pins its own model; the call passes the effort); logged `seat=model-router:builder effort=low`; lookups and commands stay in the lead's own loop (phases.md, "Delegate or keep") |
| BUILDER (routed) - the Codex side, keep Claude usage down | the gate seat (Astra on the Astra row, Sol on the Sol row) as the parent thread, effort per the rubric | headless on the Codex CLI through the Codex transport below (`task --background --write --model gpt-6-astra`); Astra spawns the `sol` (GPT-6.1 Sol xhigh, hard tier), `terra` (GPT-6.1 Terra high, contract tier), `luna` (GPT-6 Luna medium, mechanical tier), and `spark` (GPT-5.3-Codex-Spark medium, fast, mechanical tier; Pro home only, its own quota pool so it never draws on the general Codex window) custom agents from `~/.codex/agents` (`spark` only in `~/.codex-pro/agents`) |
| SOLO BUILDER (Lane B) - designs and builds a task end to end from a brief | GPT-6 Astra, xhigh (Sol xhigh when Astra's quota is spent) | `claude -p` through the local proxy, acceptEdits, no `--bare` so CLAUDE.md and skills load; see lane-b.md |
| REVIEWER A - adversarial review of Claude-built work | GPT-6 Astra on the Astra row, GPT-6.1 Sol on the Sol row (gate seat rubric, SKILL.md), effort per the rubric | `claude -p` through the local proxy, read-only tools, background Bash call (Phase 3); Codex transport read-only is its fallback |
| REVIEWER B - Astra's quota fallback for Claude-built work | GPT-6.1 Sol, at the same effort the Astra call would have used | same `claude -p` command with `--model gpt-6.1-sol`; Codex transport read-only is its fallback; never reviews Codex-built work (same family) |
| REVIEWER C - adversarial review of Codex-built work; also the parallel second reviewer on an xhigh row (pairing rule, phases.md); also the design gate and review fallback when the proxy itself is down, or Astra and Sol are both cooling and the API seat failed (Phase 3: and no qualifying app-path Carbon answer (skipped, failed, or answered only through Hydrogen)) (Reviewer fallback) | fresh Claude Fable 5.2 context (high; xhigh on a build in an excluded category) | Agent tool, `subagent_type: "model-router:reviewer"`, `effort: "high"`, or `effort: "xhigh"` on a build in an excluded category (phases.md, "Claude seat efforts") (read-only tools enforced), same review spec; first transport in Phase 3: "Reviewer C on credits (fable-review.py)" |
| PRO CONSULT - advisory second opinion, never a gate or review seat | GPT-6 Astra Pro (`chatgpt-web/gpt-6-pro`) on JC's ChatGPT Pro chat allowance | `astrapro` wrapper, background Bash; see pro-consult.md |
| GEMINI CONSULT - advisory build sheet beside Pro consult (test cases, thresholds, edge cases) and on every real-build plan; the Carbon report check of a research or audit report before delivery; those items are leads the lead verifies; never blocks, never a gate, never a pass/fail. REVIEWER G - Carbon beside the pairing-rule seat(s) in every review round of a real build (round 1 and each re-review); its items are findings ruled like any reviewer's once the lead confirms them against the code; it never passes a build alone and never replaces the pairing-rule seat - except as stand-in when Astra and Sol are out, when its confirmed items are that round's review; a skipped or failed launch never blocks (pro-consult.md, "Reviewer G") | Gemini 4 Carbon (`gemini-carbon`) in the Gemini app on JC's Google AI Pro login | `geminipro` wrapper, background Bash; see pro-consult.md, "Gemini consult"; API backup: the wrapper itself sends the same brief once to `gemini-4-hydrogen` through the `gemini-api` CLI when the app path exits 2 or 8 (pro-consult.md, "API backup") |
| HYDROGEN - quick check (a small change's diff after its build, a contained change's RUN.md plan before it), the Hydrogen fix check (a code-changing Phase 4 fix round that gets no re-review, on its diff after its smoke-gate re-run; a re-reviewed real-build round gets Reviewer G instead; a contained change keeps the Hydrogen fix check) and Carbon's fallback (a Carbon launch that exits 4 `model_not_available`); advisory, never blocks, never a gate, never Reviewer A/B/C, never a pass/fail | Gemini Hydrogen (`gemini-4-hydrogen`), same Gemini app login | `geminipro ... --model gemini-4-hydrogen`, background Bash; see pro-consult.md, "Gemini consult"; API backup: `gemini-4-hydrogen` through the `gemini-api` CLI, run by the wrapper itself when the app path exits 2 or 8 (pro-consult.md, "API backup") |
| QUOTA FALLBACK - Claude subscription spent | the Claude on credits seat (pool) builds when usable - terminal or scheduled launch only, see "Claude on credits seat (pool)"; Lane C (OpenRouter budget crew: DeepSeek builds, GLM reviews/leads) retired 2026-11-15; archive/2026-11-15-lane-c/ | otherwise, and whenever every ChatGPT login is spent too, the run waits for quota, logged in RUN.md |
| ROUTED ORCHESTRATOR (Lane D) - the session model is itself a proxy model and leads the run | `gpt-6-astra` (default) or another proxy alias the user names | the session; spawns proxy-served seats through the Agent tool (`model-router:worker` / `support-routed` / `mechanic-routed` / `astra-routed`). Claude seats, the reviewer included, only by stripped-env headless `claude -p`, never the Agent tool - see lane-d.md |

**Routing policy.**
Astra is the default senior seat for every Astra-eligible call - design
review, build parent, adversarial review - and it rides the proxy like every
other model, rotating over every ChatGPT login in the proxy (`verify-codex-logins`
lists them; six on 2026-09-12: $CODEX_BIZ_LOGIN premium, $CODEX_BIZ2_LOGIN,
three $CODEX_TEAM_LOGIN seats, the Pro login).
Companion launches for Astra run on the main Codex home with no `CODEX_HOME`
/ `CODEX_DIRECT` prefix (except during the standing fast window in quota.md,
on since 2026-09-28, no end date: native, round-robin over `.codex-pro` / `.codex-biz` via `codex-fast-home`); the `codex` shim adds `-c model_provider=router`.
The standing pin is `proxy-pin both`; check `proxy-pin status` at the start
of a run and log it, and pin `team` only when JC asks by name. Two native
homes are opt-in, each for what only it can do, and a run that needs one
launches its Astra parent natively and says so in the logbook: `.codex-pro`
(`codex-pro` shim, the Pro login) is the FAST-PIN home (JC's standing choice
since 2026-09-14, after the Business seat ran out of credits) and keeps the
Browser / Computer Use / image_gen surfaces and `spark`; `.codex-biz`
(`codex-biz` shim, or the `CODEX_HOME="${CODEX_BIZ_HOME:-$HOME/.codex-biz}"
CODEX_DIRECT=1` prefix; $CODEX_BIZ_LOGIN Business premium seat, added
2026-09-10) is opt-in only when JC asks for it by name. **Sol holds the Sol row of the gate seat rubric (SKILL.md) without being named, and stays one word away for every other seat:** a brief that names Sol (`sol`, `gpt-6
sol`, `gpt-6.1 sol`, `sol xhigh`) pins Sol for that seat instead of Astra, the Sol effort
rubric and the Sol builder tier are unchanged, and Reviewer A/B seats keep
their existing rules. Sol cooling on the Sol row with Astra available -> Astra at the Sol row's effort for that seat, logged "Sol quota spent, Astra gated/reviewed". When Astra is spent on every login, or Sol and Astra are both cooling, or the proxy is down, the seat falls back by the table in "Reviewer fallback" below (one table for the design gate and Reviewers A/B/C).
`--output-format json` with the spec fed on stdin (`< spec.md`, so stdin
reaches EOF) is what stops the nested `claude -p` from hanging after it
prints; the spec is not a command-line argument, so its length is not
capped (a 40 KB spec has passed); the commands below carry both.

## Sol pin

**GPT-6.1 Sol (2026-09-30).** Every Sol seat runs `gpt-6.1-sol` (released 2026-09-29; same price as GPT-6 Sol, cached input half). Native Codex launches need Codex CLI 0.159.2 or later: the desktop app's bundled 0.158.0-alpha.2.1 rejects the model, so `%LOCALAPPDATA%\OpenAI\Codex\bin\npm-0.159.2\` holds the npm 0.159.2 binaries and the `codex` shim picks it as the newest folder; delete that folder to roll back. Since 2026-10-13 the model list advertises the fast (`priority`) tier for `gpt-6.1-sol` ("2x speed, increased usage"), and a native fast home sends `tier=priority` for Sol exactly as for Astra (verified by trace on `.codex-pro`), so the fast pin and the standing fast window speed Sol calls too. Sol through the proxy (`claude -p`, `bcode sol`) stays at standard speed: fast reaches only a native home. **Context windows (2026-10-13; 2026-11-15).** OpenAI raised `gpt-6.1-sol`'s default context to 500k on 2026-10-12, so every proxy `claude -p` launch with `--model gpt-6.1-sol` puts `CLAUDE_CODE_MAX_CONTEXT_TOKENS=500000` in its env prefix next to `ANTHROPIC_BASE_URL` (verified: `modelUsage` contextWindow 200000 -> 500000). Since Claude Code 2.1.323 a model id it does not know is assumed to have a 1M window (200k before). That fits `gpt-6-astra` (real window 1.05M), so Astra launches carry no context variable. Every other proxy model (Terra, Luna, any other alias) carries `CLAUDE_CODE_DISABLE_1M_CONTEXT=1` (200k), the credits pool seat too (its section), so it auto-compacts before its real limit instead of failing every turn until `/clear`. The launch scripts (`scripts/session.*`, `worker.*`) set these. Native Codex picks 500k up from the model list by itself. A failed `gpt-6.1-sol` call follows the Astra and Reviewer fallback rules (Routing policy above; Reviewer fallback). Known gap: Lane D Agent-tool seats inherit the lead session's environment, so under an Astra lead (nothing set) Terra and Luna seats assume 1M. GPT-6.2 Astra and GPT-6.2 Sol (IDs `gpt-6.2-astra`, `gpt-6.2-sol`, in OpenAI's Codex catalogue 2026-11-17) run only on the API seat for now; the subscription seats move once a re-probe on or after 2026-11-21 shows a ChatGPT login and the proxy serving them.

A brief that names Sol (`sol`, `gpt-6 sol`, `gpt-6.1 sol`, `sol xhigh`) pins Sol for the Astra
seats: builds and reviews run the same commands with `--model gpt-6.1-sol`, at
the rubric row's effort or the user's effort word, which pins every Sol call
in the run, build and review.

- **Sol builds on the Codex transport** (`task --background --fresh --write
  --model gpt-6.1-sol ...`, job id in `<scratch>/sol-job-<name>.txt`): native
  sandbox and `spawn_agent`. A Sol parent does the hard-tier work itself and
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

## Standing fast window: reviews (always on - JC 2026-11-01; quota.md)

JC 2026-11-01 restored this after the 2026-10-17 retirement: gates and
reviews always run fast on the native homes, accepting the 2.5x drain on
the Pro login. A skipped home (`~/.codex-fast-skip`) stays out of the
round-robin, so with `biz` skipped every review lands on `.codex-pro`.

While the window is open, the design review (Phase 1b) and Reviewer A/B
(Phase 3) do not use the proxy `claude -p` commands below as primary. They
run on the Codex transport (next section) read-only - no `--write` - on a
fast native home picked round-robin: the launch line becomes
```bash
H=$(codex-fast-home) || { unset CODEX_HOME CODEX_DIRECT; echo "codex-fast-home: no fast home - use the proxy claude -p command below"; exit 1; }; echo "home=$H"
CODEX_HOME="$H" CODEX_DIRECT=1 node "$C" task --background --fresh --model gpt-6-astra --effort <effort> --prompt-file <spec> | tee <scratch>/astra-job-<name>.txt
```
When the picker exits non-zero (every fast home skipped, quota.md) the call stops before any launch: run the proxy `claude -p` command of this review instead, as written, and log it; never launch with an empty `CODEX_HOME`.
Sol row / Reviewer B: `--model gpt-6.1-sol`, effort as the proxy command
would use. Same spec files, same review contract. The read-only sandbox
cannot write, so the spec's save line is harmless and the orchestrator
saves the findings: `node "$C" result <job-id> > <scratch>/fabstra-review-<name>-findings.md`
(design review: `fabstra-design-<name>-findings.md`). Log `fast (standing
window, <home>)` in RUN.md. Fallbacks, in order: a usage-limit error on
one home -> skip file (`echo pro >> ~/.codex-fast-skip`, quota.md) and relaunch on the other; both homes
spent (the picker exits 3), or the Codex CLI failing for a non-quota reason -> the proxy
`claude -p` command below, as written (standard tier, rotates the other
logins). A dead 8317 does not block this path (native homes skip the
proxy), so the "nothing on 8317" rules below apply only to the fallback.
After the window closes this section is void.

## Codex transport (the gate seat as parent for routed builds and Codex-column fixes; read-only fallback for both reviews) - launch and wait inside one background Bash call

`$C` = `$(ls -d ~/.claude/plugins/cache/openai-codex/codex/*/scripts/codex-companion.mjs | sort -V | tail -1)`
(the version segment moves when the codex plugin updates - `ls` the parent
directory if the path fails). Every Codex call is two Bash calls from the
orchestrator; the `codex:rescue` skill is not a fabstra transport.
The local proxy CLIProxyAPI 7.3.12 (upgraded and verified 2026-09-23;
7.2.157 did not know them) serves `gpt-6-astra`, `gpt-6.1-sol` (verified
2026-09-30; native Codex needs CLI 0.159.2+) and `gpt-6-luna`, so Sol and
GPT-6 Luna run both through the proxy and on the native Codex homes.

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
| Astra and Sol both cooling on every ChatGPT login and every fast native home (for both models: proxy 429 `All credentials ... cooling down`, 429 `usage_limit_reached`, or 503 `auth_unavailable: no auth available (providers=codex ...)` (seen 2026-11-17 with an upstream 402 `deactivated_workspace`); and `codex-fast-home` exit 3), confirmed as quota, not a 60-second transient cooldown: every login's usage endpoint shows >= 95% or `limit_reached` for both models, or one retry of the same seat after ~60 s fails the same way | API seat on JC's OpenAI API credits through 8319 - GPT-6.2 Sol for a Sol-row call, GPT-6.2 Astra for an Astra-row call, as the effort-suffixed id `<model>-<effort>` ("API seat (OpenAI credits)" below), at the effort the subscription call would have used; log "API seat, OpenAI credits" | Reviewer G stands in as Reviewer A / B (pro-consult.md, "Reviewer G as stand-in"); a round with no qualifying app-path Carbon answer (skipped, failed, or answered only through Hydrogen) takes the API seat instead, and so does a contained change's one review; log "Reviewer G stood in" or "API seat, OpenAI credits" |
| Astra and Sol both cooling and the API seat failed (Phase 3: and no qualifying app-path Carbon answer (skipped, failed, or answered only through Hydrogen)), work not excluded | fresh Fable (Reviewer C), `model-router:reviewer` at effort high; log "same-family review, GPT seats cooling" | the same fresh Fable seat and log line |
| Astra and Sol both cooling and the API seat failed (Phase 3: and no qualifying app-path Carbon answer (skipped, failed, or answered only through Hydrogen)), work excluded (SKILL.md, Excluded categories) | fresh Fable (Reviewer C), `model-router:reviewer` at effort xhigh; log "same-family review, GPT seats cooling, excluded work" | the same fresh Fable seat and log line - nothing sensitive leaves the Claude login |
| Fable limit hit (429 "You've hit your Fable limit") wherever any row of this table or the pairing rule calls a fresh Fable | `pool/claude-fable-5-2` (a client's work: `client-<slug>/claude-fable-5-2` with its own `client-<slug>: usable` line, haiku mapping on the same prefix) headless on the credits pool ("Claude on credits seat (pool)" below; the review or design spec as the prompt, read-only tools) at the Fable seat's effort - only when the run was launched from a plain terminal or a scheduled task and the pool is usable; otherwise - a dry pool, or VS Code or the desktop app (credits refuse those `claude -p` children) - a fresh Opus 5.5 context (`subagent_type: "model-router:reviewer"`, `model: "opus"`, the same effort; tools stay Read, Grep, Glob, Bash; JC 2026-11-17; a Lane D session: lane-d.md, "Reviewer rule"); log which seat ran | the same seat and log line |
| Proxy 8317 still dead after one restart (`powershell -NoProfile -File '$MODEL_ROUTER_HOME/scripts/start-proxy.ps1 (start-proxy.sh on Mac/Linux)'`, retry once) | fresh Fable (Reviewer C), logged as a same-family review | fresh Fable (Reviewer C), same log |

Never skip the design review on a real build because the gate seat is down; never run it twice with the same spec. Codex-built work always goes to Reviewer C (pairing rule), whatever this table says for Claude-built work. `--bare` children load no ~/.claude hooks: the excluded-work check runs on the parent's launch command, and the auth-JSON guard does not reach inside the child.

## API seat (OpenAI credits)

JC 2026-11-17: the last-resort seat for Astra / Sol runs GPT-6.1 Sol on JC's OpenAI API credits, automatically and with no per-run cap, when the Reviewer fallback table's API row applies: Astra and Sol both cooling on every ChatGPT login and every fast native home (for both models: proxy 429 `All credentials ... cooling down`, 429 `usage_limit_reached`, or 503 `auth_unavailable: no auth available (providers=codex ...)` (seen 2026-11-17 with an upstream 402 `deactivated_workspace`); and `codex-fast-home` exit 3). It is a separate CLIProxyAPI instance on 127.0.0.1:8319 that holds only JC's OpenAI API keys and no ChatGPT login, so subscription traffic on 8317 never reaches it. Keys are read at each start from the `OPENAI_API_KEY` line of `~/.config/watch/.env` plus every `OPENAI_API_KEY_<NAME>` line of `~/.openai-api/keys.env` (JC adds accounts there); the proxy rotates across them and cools a key that hits its quota. `-Status` names the keys loaded, never their values. JC 2026-11-18: the seat serves GPT-6.2 Sol and GPT-6.2 Astra (Astra is allowed on the API seat from 2026-11-18, overriding the 2026-11-17 Sol-only rule), with GPT-6.1 Sol as the fallback; Astra costs about 4x Sol per token (Artificial Analysis $8/$40 vs $2/$10 per 1M, unverified against OpenAI's pricing page) and runs automatically and uncapped like Sol.

- Confirm quota before starting 8319: the trigger must be confirmed as quota, not a 60-second transient cooldown: every login's usage endpoint shows >= 95% or `limit_reached` for both models, or one retry of the same seat after ~60 s fails the same way. A retry that succeeds is the subscription seat's answer, and 8319 is not started.
- Start, once per run, before the first API call: `powershell -NoProfile -File '$MODEL_ROUTER_HOME/scripts/start-api-proxy.ps1 (maintainer's machine only - not shipped)'` (exit 1 -> the seat failed: take the next row). A start that prints `api proxy running with an old model list (missing: ...)` means the running instance predates the effort-suffixed ids: `-Stop` it (never `-Force` while another session is connected), then start again.
- **Effort reaches OpenAI only through the model id.** 8319 exposes `<model>-<effort>` ids (model `gpt-6.2-sol`, `gpt-6.2-astra`, `gpt-6.1-sol`; effort `low`, `medium`, `high`, `xhigh`, `max`), each with a proxy payload rule that sets `reasoning.effort`; CLIProxyAPI 7.3.12 drops `--effort` on this path (verified 2026-11-18: no `reasoning` field upstream, OpenAI default medium), so every API-seat call before 2026-11-18 ran at medium whatever RUN.md logged. A plain 6.2 id fails with "unknown provider"; plain `gpt-6.1-sol` is the one deprecated exception (legacy note at the end of this bullet). `--effort` is still passed (it sets Claude Code's own budget) and must equal the suffix. Legacy note: the plain `gpt-6.1-sol` id still answers on 8319 (no effort rule, OpenAI default medium) only so older sessions keep working; new launches never use it.
- Launch: the Phase 1b or Phase 3 proxy `claude -p` command of this file, unchanged except `ANTHROPIC_BASE_URL=http://127.0.0.1:8319` and `--model <model>-<effort>` with `--effort <effort>`, plus a context variable: `CLAUDE_CODE_MAX_CONTEXT_TOKENS=500000` on Sol ids (`gpt-6.2-sol-*`, `gpt-6.1-sol-*`, transport.md "Sol pin"), and, added on this seat although subscription Astra launches carry none, `CLAUDE_CODE_MAX_CONTEXT_TOKENS=272000` on `gpt-6.2-astra-*` ids (OpenAI Codex catalogue window; the API window is unverified). Model choice for every API call (design gate, Reviewer A / B stand-in, a contained change's review), at the effort the subscription call would have used: a Sol-row call -> `gpt-6.2-sol-<effort>`, an Astra-row call -> `gpt-6.2-astra-<effort>`; a 6.2 call that fails upstream with a model-not-found / unsupported-model error from OpenAI (not the proxy's own `unknown provider for model` 400, which the seat-failed bullet below covers) -> one retry on `gpt-6.1-sol-<effort>`, logged `api-seat fallback 6.1`. The Codex transport and Codex-side builds never use it; builds fall back to the Claude builders as before.
- Log each call in RUN.md: `api-seat model=<model>-<effort> effort=<effort> s=<seconds> in=<input tokens> out=<output tokens> cache=<cache-read tokens>` from the result JSON's `modelUsage` (the model id carries the effort); Claude Code's `total_cost_usd` prices unknown models at Opus rates, so a dollar figure in the report is labelled "Claude Code estimate (Opus rates)" and the real spend is on the OpenAI usage page.
- `python scripts/fabstra-review-round.py` does these steps - `build`, `diff`, `quota`, `launch`, `extract` (`launch` takes `--model gpt-6.2-sol|gpt-6.2-astra|gpt-6.1-sol`, default `gpt-6.2-sol`, and `--effort low|medium|high|xhigh|max`, and builds the suffixed id itself); the lead still writes the prior-findings block and, from round 3, the `<review_scope>` text (`--tail-section review_scope=FILE`), and rules on findings; `launch` needs `--native-checked` after the lead has checked the native homes (`codex-fast-home` exit 3).
- A 401, a 429 `insufficient_quota`, a 429 `cooling down` or a 503 `auth_unavailable` from 8319 (every key cooling), or a dead 8319 after one restart -> the seat failed: take the next row of "Reviewer fallback". An `unknown provider for model` 400 from 8319 on a suffixed id means the running instance predates the alias list: restart it as the Start bullet says and retry once; if it fails again, the seat failed. When `-Stop` answers "api proxy in use" (another session is connected), the seat failed for this call: take the next row of "Reviewer fallback"; never `-Force` another session's connection.
- Stop at the end of the run (and when parking): `powershell -NoProfile -File '$MODEL_ROUTER_HOME/scripts/start-api-proxy.ps1 (maintainer's machine only - not shipped)' -Stop`. `-Stop` leaves the instance running while another session holds a connection to it (`-Stop -Force` overrides it only when that connection is this run's own; never force another session's connection).

## Claude on credits seat (pool)

JC (2026-10-09): the Max/Team plans grant monthly Claude API credits into a linked Console org, and the pool proxy serves Claude models from those orgs' API keys - `pool/claude-sonnet-5-5`, `pool/claude-haiku-5-5`, `pool/claude-opus-5-5` for JC's own and cross-client work; `client-<slug>/claude-...` only for that client's own work. This seat is headless only: credits cover the API, Batches, Managed Agents and Agent SDK / `claude -p` run yourself with a linked org's key, and do NOT cover interactive Claude Code (terminal, IDE, desktop, web) or runs started by the GitHub Action, an IDE extension or the desktop app - so this seat is `claude -p` and never an interactive session.

**Order.** When the Claude subscription is spent and the run was launched from a plain terminal or a scheduled task and `python scripts/credits-pool.py status` shows a usable pool (it applies the keys, skips and the health probe that `credits.py --json` does not), the Claude build seats run on the pool by the command below: the builder `pool/claude-sonnet-5-5` at the effort the task's tier gets in phases.md, "Claude seat efforts"; the mechanic `pool/claude-haiku-5-5`; `pool/claude-opus-5-5` for hard-tier tasks (a client's work: the same models on `client-<slug>/`, haiku mapping included). The design gate and the reviewers stay on their normal seats and "Reviewer fallback" above (Reviewer C's first transport is "Reviewer C on credits (fable-review.py)" below) (a build with no available review seat waits for one before it ships). The seat is usable only when `status` exits 0 AND prints a line `pool: usable <account>` (for a client's work, `client-<slug>: usable <account>`); a non-zero exit (pool proxy down or not ours, unreadable skip list) or a `dry (...)` line means a dry pool. A dry pool, or a launch from VS Code or the desktop app (the seat is dry there): the run waits for quota, logged in RUN.md. That wait applies to the build seats only; a Fable review or design seat that finds the pool dry takes the fresh Opus 5.5 seat of the Fable-limit row in "Reviewer fallback".

Excluded work MAY run on `pool/` and `client-<slug>/` seats (JC 2026-10-09: this is Anthropic's own API with JC's own key), and the PreToolUse hook needs no excluded marker on those launches (`scripts/fabstra-guard.py`: a `pool/` or `client-<slug>/` credits seat is never refused, marker or not). The pool has its own proxy instance on 127.0.0.1:8318, started by `credits-pool.py sync` (the main proxy on 8317 is untouched), so this seat's command points at 8318. The haiku mapping rides `--settings` because user-settings env beats a shell variable (lane-b.md, Agent-tool delegation note). The command shows `--effort high`; set the effort the task's tier gets, and a hard-tier task swaps the model for `pool/claude-opus-5-5`:

```bash
KEY=$(proxy-key) || exit 1; CLAUDE_CODE_DISABLE_1M_CONTEXT=1 ANTHROPIC_BASE_URL=http://127.0.0.1:8318 ANTHROPIC_AUTH_TOKEN="$KEY" timeout 1500 claude -p --model pool/claude-sonnet-5-5 --settings '{"env":{"ANTHROPIC_DEFAULT_HAIKU_MODEL":"pool/claude-haiku-5-5"}}' --effort high --bare --append-system-prompt-file "$MODEL_ROUTER_HOME/skills/fabstra/references/verify-rule.md" --permission-mode acceptEdits --max-turns 60 --output-format json < <scratch>/fabstra-build-<name>.md > <scratch>/fabstra-build-<name>.md.out 2>&1
```

A client's work replaces `pool/` with `client-<slug>/` in BOTH `--model` and the haiku mapping (`client-<slug>/claude-haiku-5-5`), never mixing prefixes. `--bare` skips CLAUDE.md, so `--append-system-prompt-file` carries the global "Verify by running" rule (references/verify-rule.md) into this build seat; any other headless `--bare` build launch carries the same flag.

`pool/claude-*` ids are unknown to Claude Code, so since 2.1.323 they would get the 1M default (2.1.325's `CLAUDE_CODE_MAX_CONTEXT_TOKENS` fix covers only ids that start with `claude-`); the prefix keeps this seat at 200k, as before 2.1.323 (JC 2026-11-15).

Credits do not cover runs started from an IDE extension, the desktop app or the GitHub Action, even with `claude -p` (https://support.claude.com/en/articles/17154008; verified live 2026-10-09: a `claude -p` child launched from a VS Code session got upstream 400 "Credit balance is too low", $0 spent, while direct Messages API calls through the same pool returned 200). So this seat works only when the session that launches it is a plain terminal or a scheduled task. From VS Code or the desktop app it is dry, and a build waits for quota (a Fable seat takes Opus 5.5, "Reviewer fallback"). `scripts/credits-run.py` refuses (exit 3) in that case. Never strip or fake the entrypoint. Setup requirement: every linked org is credits-only (no purchased credits, auto-reload off, no invoicing), because the org stops at zero only then. The tracker estimates left = grant - cost-report spend; cost data lags and the pool sync runs every 15 min, so spend can overshoot the $5 floor - on a credits-only org the overshoot just fails requests. Setup: accounts in `~/.claude-credits/accounts.json` (example: `scripts/credits-accounts.example.json`; an account may give only its API key - untracked: the pool checks credit with a tiny Haiku call; balances on the Console dashboard), keys in `~/.claude-credits/secrets.env`, `python scripts/credits-pool.py sync` (every 15 min and at logon via `scripts/register-credits-pool.ps1`; it starts the pool proxy if down, `credits-pool.py stop` stops it; `credits-pool.py skip <id>` after a credit-balance 400 (tracked accounts only; untracked accounts are re-probed every sync)), balances in `bcost`.

## Reviewer C on credits (fable-review.py)

JC 2026-11-17: every Phase 3 Reviewer C call (a fresh Fable review: Codex-built work, the parallel second review on an xhigh row, the fresh-Fable rows of "Reviewer fallback", Lane B, re-reviews) runs first on `scripts/fable-review.py`, Fable 5.2 over the plain Messages API, billed to Anthropic plan credits instead of JC's subscription; the Agent seat (`model-router:reviewer`, "Phase 3 launch" below) is the fallback. A fresh-Fable design gate (Phase 1b) has no diff to review and stays on the Agent seat. Bench 2026-11-17 (hard reviewer fixture, adapted spec, effort high): recall 8/8, 0 false positives, 0 decoy hits, 2 turns, $0.22 - the same as the Agent seat at high. It is a plain API call, not Claude Code, so it runs from any session, VS Code included (support article 17154008 covers Claude Code runs only; measured on acct1 2026-11-17). Excluded work may run on it (Anthropic's own API on the pool's own keys, as on the pool seat above).

- **Use it when** the project is a git repo, the review needs nothing run beyond reading (the smoke gate already ran the tests), and diff + spec stay under 400k chars. Otherwise - or when the review needs commands run (tests, probes) that the smoke gate did not already cover - the Agent seat, as before.
- **Adapt the spec** into `<scratch>/fabstra-review-<name>.md`: the seat has only read-only tools (read_file, grep, list_files over git-tracked files) and no Bash, so remove every Bash, save and probe obligation (the `<turn_budget>` checkpoint save, the `<structured_output_contract>` overwrite: "return the report as your final message"; `--out` saves it) and every `git show <base>:<path>` base-proof step, as for the read-only Codex transport (specs.md, "Review spec (Phase 3)", end). Base evidence the reviewer needs goes into the spec as pasted text; when it cannot, take the Agent seat. The script's system prompt asks for the final `END OF REVIEW` line, so the spec need not.
- **Command**, one background Bash call (timeout 1800000): `python "$MODEL_ROUTER_HOME/scripts/fable-review.py (maintainer's machine only - not shipped)" --repo <project> (--range <base>..HEAD | --working) --spec-file <scratch>/fabstra-review-<name>.md --effort <high|xhigh per the Reviewer C row, phases.md "Claude seat efforts"> --out <scratch>/fabstra-review-findings-fable.md --no-fallback`. `--no-fallback` keeps the review on Fable 5.2, the seat the bench measured: a refusal ends INCOMPLETE and goes to the Agent seat instead of a substitute model. Pool: JC's own and cross-client work uses the default pool (`pool`); a client's work adds `--pool client-<slug>`, the only way to bill a client's account (client credits fund only that client's work). The script picks the pool account with the least fable-review spend this cycle (ledger `~/.claude-credits/fable-review-usage.jsonl`) and moves to the next account on a credit-balance 400 at the first request.
- **Outcomes:** exit 0 COMPLETE -> its findings count as the Agent seat's would; exit 0 PARTIAL (budget reached) -> its findings count, and the lead sends the parts named on its `PARTIAL:` line to the Agent seat - a PARTIAL with no `PARTIAL:` line, or one too vague to scope, gets a full Agent-seat review (its verified findings still count); exit 3 INCOMPLETE or exit 4 (API or network error, or every account of the pool out of credit) -> the Agent seat reviews, log why; exit 2 (bad arguments or config, diff + spec over 400k, no usable account) -> fix the call, or take the Agent seat.
- **Cost:** measured 2026-11-17 at effort high: $0.22 on the hard fixture, $2.68 on a 19-file docs commit; `--max-usd` defaults to $6 (JC). It is checked after each turn, so a run can end one turn above it (a $3 cap finished at $3.06; a final turn can add more); the tools stop and ask for the report at 70%. Strict pre-turn enforcement is a script follow-up.
- **Log** in RUN.md from the report footer's `account:` and `est. cost:` lines: `review seat: Reviewer C via fable-review (account <id>, $<est>)`; an Agent-seat fallback logs the exit code and reason.

The Fable-limit row of "Reviewer fallback" governs the Agent seat only; this transport does not draw on the subscription's Fable limit.

## Phase 1b launch - DESIGN REVIEW (the gate seat - Astra or Sol - before any builder launches)

Mandatory for real builds. The cheapest bug is one caught on paper: the gate seat
reads the plan, every blueprint, and the repository, and reports where the
design will fail before Opus spends twenty minutes building it.

**Transport (fallback - the primary is the fast path in "Standing fast window: reviews" above):** write the design-review spec to
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
argument, so its length is not capped (a 40 KB spec has passed)). `--bare` skips CLAUDE.md, so the spec carries every stack rule. Since
Claude Code 2.1.323 an unknown model id is assumed to have a 1M window
(200k before), which fits Astra's real 1.05M, so the command carries no
context variable. Keep `--max-turns 30`. **Fallback:** the Codex transport
above without `--write` (read-only sandbox; the report arrives only through
`result`). **Astra blocked** (quota.md, "Astra blocked, how to read it"), Sol
cooling too, an excluded category, or a dead proxy: take the design gate
column of "Reviewer fallback" above. Never skip the design review on a real
build because the gate seat is down; never run it twice with the same spec.

In the same message as the gate seat, launch the plan-mode Gemini consult
(pro-consult.md, "Gemini consult - the build-sheet seat").

While the gate seat reviews, do not launch builders. Do prepare: the review-spec
skeleton for Phase 3, the smoke-gate command, and the logbook entries.

## Phase 3 launch - ADVERSARIAL REVIEW (Astra, Sol, or a fresh Fable context)

Mandatory for real builds; skip only for a small change as Phase 1 defines
it, and say so in the report. Pick the reviewer by the pairing rule: Claude built -> Reviewer A (the gate seat: Astra on the Astra row, Sol on the Sol row); Codex side built -> Reviewer C (fresh Fable); a contained change (phases.md Phase 1): Claude built -> Sol at `--effort high`, Codex built -> Reviewer C, no second seat; a mixed build -> Reviewer A on the BUILDER tasks and Reviewer C on the CODEX tasks plus every seam, partitioned (pairing rule, phases.md); an xhigh row adds Reviewer C in parallel with Reviewer A on the BUILDER tasks; Astra blocked after a Claude build -> Reviewer B (Sol, same effort). The review spec template below is the contract for every reviewer
and every transport. In the same message as each review round's seat(s) of a real build, launch Reviewer G (Carbon; pro-consult.md, "Reviewer G"): its items are findings ruled like any reviewer's once the lead confirms them, it never passes a build alone, and a skipped or failed launch never blocks the round.

**Reviewer A through the proxy (fallback - the primary is the fast path in "Standing fast window: reviews" above; Astra row shown, Sol row swaps the model):** write the review spec to
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

**Reviewer C, fresh Fable 5.2 context:** one Agent tool call,
`subagent_type: "model-router:reviewer"`, `effort: "high"` (Fable 5.2 at high with Read, Grep,
Glob, and Bash only, enforced by the agent definition), prompt = the review spec
verbatim. A build in an excluded category takes `effort: "xhigh"` on the same seat (Fable 5.2 at xhigh, the same tools) - phases.md, "Claude seat efforts". It has seen none of the build, which is the point - never paste
your session context into it. Run it as the review when the Codex side
built, and as the fallback "Reviewer fallback" names (log it as a
same-family review); Astra and Sol both cooling with the proxy still up reaches
this seat only through that table's two rows after the API seat (the API seat failed, and in Phase 3 no qualifying app-path Carbon answer (skipped, failed, or answered only through Hydrogen)): work not excluded
(`model-router:reviewer` at effort high) and work excluded (the same seat at effort xhigh);
pairing rule in phases.md.
First transport for every Reviewer C call: "Reviewer C on credits (fable-review.py)" above; this Agent call is its fallback.
