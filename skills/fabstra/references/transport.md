# FabStra transport - the crew, the routing policy, and every launch command

Contents: The crew in full (crew table, routing policy); Model pins (GPT-6.2); Standing fast window: reviews (always on since 2026-11-01); Codex transport; Codex write probe; Reviewer fallback; Claude on credits seat (pool); Phase 1b launch - DESIGN REVIEW; Phase 3 launch - ADVERSARIAL REVIEW

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
| DESIGN REVIEWER - critiques the plan and blueprints before build | the gate seat: GPT-6.2 Sol by default, GPT-6.2 Astra on an Astra row (gate seat rubric, SKILL.md; lead-mode.md), effort per the effort rubric | `claude -p` through the local proxy, read-only tools, background Bash call (Phase 1b); Codex transport read-only is its fallback |
| BUILDER (hard tier) - multi-file features, architecture or data-model decisions, tricky algorithms, integration surfaces, debugging where the first theory might be wrong | Claude Opus 5.5 at high | Agent tool subagent, `subagent_type: "model-router:builder"`, `effort: "high"` (it pins its own model; the call passes the effort); logged `seat=model-router:builder effort=high`; every tier and seat: phases.md, "Claude seat efforts" |
| BUILDER (hard tier, xhigh) - a hard-tier task in an excluded category (SKILL.md), or any task after its second miss at high | Claude Opus 5.5 at xhigh | Agent tool subagent, `subagent_type: "model-router:builder"`, `effort: "xhigh"` (it pins its own model; the call passes the effort); logged `seat=model-router:builder effort=xhigh` |
| SUPPORT (contract tier) - a self-contained change with a written contract | Claude Opus 5.5 at medium | Agent tool subagent, `subagent_type: "model-router:builder"`, `effort: "medium"` (it pins its own model; the call passes the effort); logged `seat=model-router:builder effort=medium` |
| SONNET MAX - contract-tier tasks, only when the user pins it | Claude Sonnet 5.5 at max | Agent tool subagent, `subagent_type: "model-router:sonnet-max"` (pins its own model and effort); rule: phases.md routing rubric, Sonnet max pin |
| MECHANIC (mechanical tier, any file count) - exact-text or known-pattern edits | Claude Opus 5.5 at low | Agent tool subagent, `subagent_type: "model-router:builder"`, `effort: "low"` (it pins its own model; the call passes the effort); logged `seat=model-router:builder effort=low`; lookups and commands stay in the lead's own loop (phases.md, "Delegate or keep") |
| BUILDER (routed) - the Codex side, keep Claude usage down | the gate seat (Sol by default, Astra on an Astra row) as the parent thread, effort per the rubric | headless on the Codex CLI through the Codex transport below (`task --background --write --model gpt-6.2-sol --effort <effort>`, `gpt-6.2-astra` on an Astra row); the parent clauses are in specs.md, "Codex parent clauses", pasted for the model that actually runs as parent (hops and retries: hop rules, Model pins): a Sol parent spawns `terra`, `luna` and `spark`, never `sol`; an Astra parent also spawns `sol`, except while Sol is cooling or rejected (the Sol-unavailable line, specs.md). The children: `sol` (GPT-6.2 Sol xhigh, hard tier, on the main/router home; the native `.codex-pro` / `.codex-biz` agent files stay on 6.1 until a re-probe passes), `terra` (GPT-6.1 Terra high, contract tier), `luna` (GPT-6 Luna medium, mechanical tier), and `spark` (GPT-5.3-Codex-Spark medium, fast, mechanical tier; Pro home only, its own quota pool so it never draws on the general Codex window) custom agents from `~/.codex/agents` (`spark` only in `~/.codex-pro/agents`) |
| SOLO BUILDER (Lane B) - designs and builds a task end to end from a brief | GPT-6.2 Astra (`gpt-6.2-astra`), xhigh (GPT-6.2 Sol at the same effort when Astra is spent or rejected on every pair, lane-b.md) | `claude -p` through the local proxy, acceptEdits, no `--bare` so CLAUDE.md and skills load; see lane-b.md |
| REVIEWER A - adversarial review of Claude-built work | the gate seat: GPT-6.2 Sol by default, GPT-6.2 Astra on an Astra row (gate seat rubric, SKILL.md; lead-mode.md), effort per the rubric | `claude -p` through the local proxy, read-only tools, background Bash call (Phase 3); Codex transport read-only is its fallback |
| REVIEWER B - the cooldown seat for Claude-built work: the other GPT model of the pair when the row's model is cooling or rejected on every pair (hop rules, Model pins) | GPT-6.2 Astra when Sol is out, GPT-6.2 Sol when Astra is out, at the same effective effort the row's call would have used (an excluded build: xhigh) | same `claude -p` command with the other model's `--model` and context variable (Model pins); Codex transport read-only is its fallback; after a Claude build only, never reviews Codex-built work (same family) |
| REVIEWER C - adversarial review of Codex-built work; also the parallel second reviewer on an xhigh row (pairing rule, phases.md); also the design gate and review fallback when the proxy itself is down, or Astra and Sol are both cooling and the API seat failed (Phase 3: and no qualifying Neon (API) or Carbon (either path) answer (skipped, failed, answered only through Hydrogen, or a `model_mismatch`)) (Reviewer fallback) | fresh Claude Fable 5.2 context (high; xhigh on a build in an excluded category) | Agent tool, `subagent_type: "model-router:reviewer"`, `effort: "high"`, or `effort: "xhigh"` on a build in an excluded category (phases.md, "Claude seat efforts") (read-only tools enforced), same review spec; first transport in Phase 3: "Reviewer C on credits (fable-review.py)" |
| PRO CONSULT - advisory second opinion, never a gate or review seat | GPT-6 Astra Pro (`chatgpt-web/gpt-6-pro`) on JC's ChatGPT Pro chat allowance | `astrapro` wrapper, background Bash; see pro-consult.md |
| GEMINI CONSULT - advisory build sheet beside Pro consult (test cases, thresholds, edge cases) and on every real-build plan; the Gemini report check of a research or audit report before delivery; those items are leads the lead verifies; never blocks, never a gate, never a pass/fail. REVIEWER G - the Gemini seat (Carbon, `--model gemini-carbon`) beside the pairing-rule seat(s) in every review round of a real build (round 1 and each re-review); its items are findings ruled like any reviewer's once the lead confirms them against the code; it never passes a build alone and never replaces the pairing-rule seat - except as stand-in when Astra and Sol are out, when its confirmed items are that round's review; a skipped or failed launch never blocks (pro-consult.md, "Reviewer G") | Gemini 4 Neon by default, except Reviewer G (Carbon) (`gemini-neon`; API model `gemini-4-neon`, thinking_level medium; API only, since 2026-11-19), Carbon the spare and Reviewer G's model (`gemini-carbon`; API model `gemini-4-carbon`: the paid Gemini API first, the Gemini app on JC's Google AI Pro login as fallback) | `geminipro` wrapper, background Bash; API first through the `gemini-api` CLI on the paid key, app fallback (Carbon only) only when the API provably did not answer; an exit 4 follows pro-consult.md, "Fallback ladder"; a qualifying Neon (API) or Carbon (either path) answer counts for Reviewer G (pro-consult.md, "Gemini consult" and "API primary") |
| HYDROGEN - quick check (a small change's diff after its build, a contained change's RUN.md plan before it), the Hydrogen fix check (a code-changing Phase 4 fix round that gets no re-review, on its diff after its smoke-gate re-run; a re-reviewed real-build round gets Reviewer G instead; a contained change keeps the Hydrogen fix check) and the last rung of the fallback ladder (a Carbon launch that exits 4 `model_not_available`; pro-consult.md, "Fallback ladder"); advisory, never blocks, never a gate, never Reviewer A/B/C, never a pass/fail | Gemini Hydrogen (`gemini-4-hydrogen`), same route: the paid Gemini API first, the same Gemini app login as fallback | `geminipro ... --model gemini-4-hydrogen`, background Bash; API first through the `gemini-api` CLI on the paid key, app fallback only when the API provably did not answer (pro-consult.md, "Gemini consult" and "API primary") |
| REVIEWER AG / ANTIGRAVITY BUILDER (parked 2026-11-18: no Ultra account) - Reviewer AG reads the repo and reviews beside Reviewer G in Phase 3 round 1 of a real build on an allowlisted own repo; the builder runs only when JC names it, reviewed by a fresh Fable (Reviewer C); items are leads the lead confirms against the code; advisory, never a gate, never Reviewer A/B/C, never a pass/fail; a non-zero exit never blocks | Gemini 4 Carbon in the Antigravity CLI (agy) on the dedicated Ultra account (AGYSEAT_ACCOUNT) | agyseat wrapper, background Bash; see pro-consult.md, "Antigravity seat (agyseat)" |
| QUOTA FALLBACK - Claude subscription spent | the Claude on credits seat (pool) builds when usable - terminal or scheduled launch only, see "Claude on credits seat (pool)"; Lane C (OpenRouter budget crew: DeepSeek builds, GLM reviews/leads) retired 2026-11-15; archive/2026-11-15-lane-c/ | otherwise, and whenever every ChatGPT login is spent too, the run waits for quota, logged in RUN.md |
| ROUTED ORCHESTRATOR (Lane D) - the session model is itself a proxy model and leads the run | `gpt-6.2-sol` (default), `gpt-6.2-astra` when the user names Astra, or another proxy alias the user names | the session; spawns proxy-served seats through the Agent tool (`model-router:worker` / `support-routed` / `mechanic-routed` / `astra-routed`). Claude seats, the reviewer included, only by stripped-env headless `claude -p`, never the Agent tool - see lane-d.md |

**Routing policy.**
Sol (GPT-6.2 Sol) is the default senior seat - gate seat (design review),
Codex-side parent, Reviewer A - for every real build, excluded categories
included (xhigh), and whenever unsure (JC, 2026-11-18). Astra (GPT-6.2 Astra)
is the hard-reasoning seat and Sol's backup: it holds the gate seat only for
an architecture or data-model decision, a plan whose check you cannot state,
a "break it" ask, or a re-review after a Sol miss on a P1 (an Astra trigger
wins over the excluded row, which then sets the xhigh floor; rubric:
lead-mode.md). Both ride the proxy like every
other model, rotating over every ChatGPT login in the proxy (`verify-codex-logins`
lists them; six on 2026-09-12: $CODEX_BIZ_LOGIN premium, $CODEX_BIZ2_LOGIN,
three $CODEX_TEAM_LOGIN seats, the Pro login).
Companion launches for Sol and Astra run on the main Codex home with no `CODEX_HOME`
/ `CODEX_DIRECT` prefix (except during the standing fast window in quota.md,
on since 2026-09-28, no end date: native, round-robin over `.codex-pro` / `.codex-biz` via `codex-fast-home`); the `codex` shim adds `-c model_provider=router`.
The standing pin is `proxy-pin both`; check `proxy-pin status` at the start
of a run and log it, and pin `team` only when JC asks by name. Two native
homes are opt-in, each for what only it can do, and a run that needs one
launches its Codex parent natively and says so in the logbook (neither home is
proven for 6.2 yet - Model pins): `.codex-pro`
(`codex-pro` shim, the Pro login) is the FAST-PIN home (JC's standing choice
since 2026-09-14, after the Business seat ran out of credits) and keeps the
Browser / Computer Use / image_gen surfaces and `spark`; `.codex-biz`
(`codex-biz` shim, or the `CODEX_HOME="${CODEX_BIZ_HOME:-$HOME/.codex-biz}"
CODEX_DIRECT=1` prefix; $CODEX_BIZ_LOGIN Business premium seat, added
2026-09-10) is opt-in only when JC asks for it by name. **Naming a seat pins it:** a brief that names Sol (`sol`, `gpt-6.2 sol`, `sol xhigh`) or Astra (`astra`, `gpt-6.2 astra`) pins that model for that seat, at the rubric row's effort or the user's effort word; an excluded-category build stays at xhigh over any lower effort word (phases.md, "Pins"). **A cooling or rejected model hops** by the hop rules in "Model pins" below; when no hop is left, or the proxy is down, the seat falls back by the table in "Reviewer fallback" below (one table for the design gate and Reviewers A/B/C).
`--output-format json` with the spec fed on stdin (`< spec.md`, so stdin
reaches EOF) is what stops the nested `claude -p` from hanging after it
prints; the spec is not a command-line argument, so its length is not
capped (a 40 KB spec has passed); the commands below carry both.

## Model pins (GPT-6.2)

Formerly "Sol pin". JC 2026-11-18: every Sol and Astra subscription seat runs GPT-6.2. Every launch line in this file uses these ids and, on a proxy `claude -p` launch, this context variable in the env prefix next to `ANTHROPIC_BASE_URL`:

| Seat | Primary id | Proxy `claude -p` context env | Fallback pin (only on a model-rejected / unsupported-model error) |
|---|---|---|---|
| Sol | `gpt-6.2-sol` | `CLAUDE_CODE_MAX_CONTEXT_TOKENS=500000` | `gpt-6.1-sol` (same 500000) |
| Astra | `gpt-6.2-astra` | `CLAUDE_CODE_MAX_CONTEXT_TOKENS=272000` (Codex catalogue window; `claude -p` otherwise assumes 1M) | `gpt-6-astra` (the same 272000: the Codex catalogue, ~/.codex/models_cache.json, lists it at 272000 on 2026-11-18) |

- **Verified 2026-11-18.** 8317 serves `gpt-6.2-sol` and `gpt-6.2-astra` (/v1/models and live calls). Effort reaches OpenAI on 8317: the Responses API echoes the sent effort (no effort sent -> medium), and `claude -p --effort` low vs xhigh on `gpt-6.2-sol` tracks the Responses-API reasoning counts (low 314 / xhigh 524 output tokens vs 218 / 483). A Codex companion router launch `--model gpt-6.2-sol --effort low` answered in 16 s. OpenAI: "Use GPT-6.2 Astra for the most demanding tasks or GPT-6.2 Sol for complex work at lower cost." API price per 1M: Astra $8 in / $40 out, Sol $2 / $10; both 1.05M context, 128k output.
- **Always pass effort.** GPT-6.2's Codex catalogue default effort is low and the proxy's default is medium; `none` is rejected by the API. Every Sol and Astra launch carries `--effort`; the companion still stops at xhigh.
- **Native homes are not proven for 6.2.** `.codex-pro` hit a usage limit until 2026-11-21 15:27 (re-probe on or after then); `.codex-biz` rejected 6.2 at login on 2026-11-18. Their agent files stay on 6.1 until a re-probe passes. A model-rejected native 6.2 launch hops by the hop rules below.
- **Hop rules** - the single home for hop behaviour; every other file states only its local consequence and points here. A hop replaces the model, id or home of one seat call (the design gate, Reviewer A/B, a Codex-side build, fix or write probe, a Lane B or Lane D seat, a surface job) that cannot run as launched. **Tried pairs bound every walk, not a hop count:** each seat call keeps a list of the (home, model id) pairs it has launched, and a hop never relaunches a pair on its list. A home is a native Codex home (`.codex-pro`, `.codex-biz`) or the router: a Codex launch with no `CODEX_HOME` and a proxy `claude -p` call both reach 8317 and count as one home, the router (a log line may name it `proxy`). The same id moved from a native home to the router, and an id swapped for its fallback pin, are each a new pair. A model's walk, in order: for a call that needs its native home (the fast pin, a surface job), (that home, 6.2 id) then (that home, fallback pin); for every other call, (the native home it started on, 6.2 id) when it started on one, and (the other native home, 6.2 id) when a usage limit moved it there (step 1), then (router, 6.2 id), then (router, fallback pin).
  1. **Cooling** (a quota error: quota.md, "Astra blocked, how to read it"). A usage limit on one native home, for a call that may leave it, retires only that pair: the call first takes the standing fast window's skip-file relaunch on the other home (a new pair; a `--write` build follows step 7), then the router. A quota error on the last home the call may use (the router, the model cooling on every login; for a call that needs its native home, that home: surfaces.md) retires that model for the rest of the call -> the other model of the pair, logged as the "Reviewer fallback" row says; say so in the report (the other GPT model gated or reviewed in place of the rubric's seat). After a Claude build the review seat it fills is Reviewer B. A model never takes over a review of its own build (pairing rule): Lane B's Reviewer S never hops to Astra, it is logged unavailable instead (lane-b.md, part 4).
  2. **Model-rejected** (a model-rejected / unsupported-model error, no quota error) -> the next untried pair of the same model's walk: from a native home, the same id on the router (the launch's prefix lines replaced by `unset CODEX_HOME CODEX_DIRECT`; a review's router route is its proxy `claude -p` command), or the fallback pin on that home when the call needs that home (the fast pin; a surface job, surfaces.md); from the router, the fallback pin there. Log `model-rejected <id> on <home|proxy>, relaunched <router|fallback pin>`. A rejection is not a usage limit: it never goes in `~/.codex-fast-skip`.
  3. **One model rejected on every pair** (no untried pair of that model's walk is left, each one rejected or retired by a native-home usage limit under step 1, at least one rejected, and no quota error on the last home the call may use; a native-home rejection alone leaves the router pairs to try unless the call needs that home) -> the other model at the same effective effort, exactly as step 1, on the home the last pair ran on, walking its own pairs by step 2 (logged "<model> rejected on every pair, <other> gated/reviewed/built"). Only when every pair of both models is rejected or cooling (the other model rejected on every pair too, or retired by step 1) take the "Model rejected on every route" row of "Reviewer fallback" (a design gate or review: the fresh Fable; a Codex build, fix or write probe: the Claude builders take the task); never the API seat. Restart the proxy afterwards so it re-probes (it remembers a credential's last error per model).
  4. **Effort.** Every hop carries the effective effort after the excluded-category floor (phases.md, "Effort rubric (Sol and Astra)"): the row's effort or the user's effort word, and xhigh on an excluded-category build whatever lower word the user gave. The write probe is the one exception: it stays at low on every pair ("Codex write probe").
  5. **Fresh launch, no ping-pong.** Every hop is a new launch whose env prefix is recomputed for the new id (Sol and `gpt-6.1-sol` 500000; Astra and `gpt-6-astra` 272000), so a long Sol context never rides into Astra: `--fresh` on the Codex transport, a new invocation for a proxy `claude -p` call - never a model switch inside a running thread (OpenAI: GPT-6.2 drops reasoning items after model changes). The list only grows: a hop never relaunches a pair on it or a model retired by step 1, so a failing hop goes to the next untried pair, then the next step, then the next row of "Reviewer fallback", and every walk ends within the two models' pairs.
  6. **Parent clause.** A Codex build or fix launch that hops or retries re-assembles its packet (specs.md, "Codex-side tasks") with the clause of the model that now runs as parent: Sol or `gpt-6.1-sol` -> the Sol-parent clause; Astra or `gpt-6-astra` -> the Astra-parent clause, plus the Sol-unavailable line whenever Sol is cooling or rejected (specs.md, "Codex parent clauses"); never the other model's clause. A one-thread task that omitted the clause still omits it.
  7. **A write build changes home only to a probed home.** A hop that moves a `--write` build or fix to another home (native -> router, router -> native, or one native home to the other) launches only on a home with a `codex-write=ok` verdict for this folder; a home with no verdict gets the write probe first ("Codex write probe"), launched with that home's own prefix lines (the router: `unset CODEX_HOME CODEX_DIRECT`; a native home: `CODEX_HOME=<home> CODEX_DIRECT=1`), not the picker's `peek`, then the build, and a `blocked` home sends the task to the Claude builders. The probe itself needs no verdict - it creates one: a probe that is model-rejected hops by rules 2-3 (a usage-limited one by rule 1) and its result is the verdict for the home it finally ran on; a probe whose hop lands on a home that already holds a verdict for this folder stops there and that verdict stands. The build then launches on that same home with its own pair list (its id hops by step 2 if rejected there), not on the picker's next home.
- **Other proxy models.** Terra, Luna and any other alias carry `CLAUDE_CODE_DISABLE_1M_CONTEXT=1` (200k), the credits pool seat too (its section), so they auto-compact before their real limit instead of failing every turn until `/clear`. The launch scripts (`scripts/session.*`, `worker.*`) set these. Native Codex picks the window up from the model list by itself. Proxy context pins apply per launch only: an Agent-tool child inherits its lead's environment (Lane D, Lane B children), so a child on the other model inherits the wrong window; where the pin matters use a separate headless launch (lane-d.md).
- **Speed.** The Codex catalogue advertises the fast (`priority`) tier for both 6.2 ids, so the fast pin and the standing fast window speed Sol and Astra on a native home; through the proxy (`claude -p`, `bcode sol`) they run at standard speed. Native Codex launches need Codex CLI 0.159.2 or later: the desktop app's bundled 0.158.0-alpha.2.1 rejects 6.1 Sol, so `%LOCALAPPDATA%\OpenAI\Codex\bin\npm-0.159.2\` holds the npm 0.159.2 binaries and the `codex` shim picks it as the newest folder; delete that folder to roll back.

History. **GPT-6.1 Sol (2026-09-30).** Every Sol seat ran `gpt-6.1-sol` (released 2026-09-29; same price as GPT-6 Sol, cached input half). Since 2026-10-13 the model list advertised the fast tier for `gpt-6.1-sol` ("2x speed, increased usage"), and a native fast home sent `tier=priority` for Sol exactly as for Astra (verified by trace on `.codex-pro`). **Context windows (2026-10-13; 2026-11-15).** OpenAI raised `gpt-6.1-sol`'s default context to 500k on 2026-10-12, so its proxy launches put `CLAUDE_CODE_MAX_CONTEXT_TOKENS=500000` in the env prefix (verified: `modelUsage` contextWindow 200000 -> 500000). Since Claude Code 2.1.323 a model id it does not know is assumed to have a 1M window (200k before); that fitted `gpt-6-astra` (real window 1.05M), so its launches carried no context variable - still true for the `gpt-6-astra` fallback pin, false for `gpt-6.2-astra`. Correction 2026-11-18 (fix round 1): the Codex catalogue (~/.codex/models_cache.json) lists `gpt-6-astra` at 272000, like `gpt-6.2-astra`, so the fallback pin now carries `CLAUDE_CODE_MAX_CONTEXT_TOKENS=272000` too (Model pins). GPT-6.2 Astra and Sol entered OpenAI's Codex catalogue on 2026-11-17 and ran only on the API seat until the 2026-11-18 probes above.

- **Codex-side builds** (`task --background --fresh --write --model gpt-6.2-sol --effort <effort> ...`, `--model gpt-6.2-astra` on an Astra row, job id in `<scratch>/codex-job-<name>.txt`): native sandbox and `spawn_agent`. Paste the clause of the model that actually runs as parent, from specs.md, "Codex parent clauses" (their single home; no copy here): the Sol-parent clause for a Sol launch (the default), the Astra-parent clause for an Astra launch; a hop or retry re-assembles it (hop rules above), never the rubric row alone. specs.md adds the clause to every Codex-side build spec; the one exception is a task that fits one thread, which may omit it - each spawn costs a fresh context - and its spec's wrap-up line (specs.md, "Codex-side tasks") still carries the shared-machine rule.
- **Reviews through the proxy `claude -p`** (the Phase 3 command, `--model gpt-6.2-sol`, `gpt-6.2-astra` on an Astra row, with the context variable above). Evidence for this transport predates 6.2: benchmarked 2026-09-04 on the 5-bug fixture with the Sol of that day, xhigh, n=3 each - proxy 112-203 s, Codex 195-337 s, identical recall (5/5) and zero false positives on both - and it can save the findings file, which the Codex read-only sandbox cannot. Each transport is the other's fallback.
- **Pairing:** Claude built -> the gate seat reviews (Reviewer A; Reviewer B when the row's model is cooling); Sol built -> the fresh Fable (Reviewer C); Sol never reviews Sol; Astra never reviews its own build.
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
CODEX_HOME="$H" CODEX_DIRECT=1 node "$C" task --background --fresh --model gpt-6.2-sol --effort <effort> --prompt-file <spec> | tee <scratch>/codex-job-<name>.txt
```
When the picker exits non-zero (every fast home skipped, quota.md) the call stops before any launch: run the proxy `claude -p` command of this review instead, as written, and log it; never launch with an empty `CODEX_HOME`.
Astra row, or Reviewer B when Sol is out: `--model gpt-6.2-astra` (Reviewer B
when Astra is out: `gpt-6.2-sol`), effort as the proxy command would use. A
cooling or model-rejected launch hops by the hop rules (Model pins; this
review's router route is its proxy `claude -p` command). Same spec files, same review contract. The read-only sandbox
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
GPT-6 Luna run both through the proxy and on the native Codex homes. Since
2026-11-18 it also serves `gpt-6.2-sol` and `gpt-6.2-astra` on 8317 (Model
pins); the native homes are not proven for 6.2 yet.

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
   node "$C" task --background --fresh [--write] --model gpt-6.2-sol --effort <per the effort rubric> --prompt-file <scratch>/fabstra-<name>.md | tee <scratch>/codex-job-<name>.txt
   J=$(grep -oE "task-[a-z0-9]+-[a-z0-9]+" <scratch>/codex-job-<name>.txt | head -1); echo "job=$J"
   node "$C" status "$J" --wait --timeout-ms 3300000 --poll-interval-ms 30000 --json
   ```
   Astra row: `--model gpt-6.2-astra`, same lines. A cooling or
   model-rejected launch hops by the hop rules (Model pins); a `--write`
   build or fix moves only to a home with a write verdict, probed first
   where it has none (hop rule 7).
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
   `codex-job-<name>.txt` within seconds; the notification arrives when the
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
   `--model gpt-6-astra`: launched, waited, fetched in 10 s; 2026-11-18 a
   router launch `--model gpt-6.2-sol --effort low` answered in 16 s.

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
node "$C" task --background --fresh --write --model gpt-6.2-sol --effort low --prompt-file <scratch>/fabstra-probe-<name>.md | tee <scratch>/probe-job-<name>.txt
J=$(grep -oE "task-[a-z0-9]+-[a-z0-9]+" <scratch>/probe-job-<name>.txt | head -1); node "$C" status "$J" --wait --timeout-ms 600000 --poll-interval-ms 15000 --json
```

The write probe is a sandbox capability check, not a judgement call: it runs at low effort whatever the build's effort or the excluded floor.

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
config changes; then probe again. Never skip the probe by assuming. A probe
that fails with a model-rejected / unsupported-model error is no write
verdict: it hops by hop rules 2-3 and needs no verdict on the home it moves
to; its result is the verdict for the home it finally ran on, and the build
follows it to that home (Model pins, hop rule 7); log the hop beside the
verdict.

## Reviewer fallback

One table for the design gate (Phase 1b) and Reviewers A/B/C (Phase 3). Every row is logged with its reason in RUN.md.

| Situation | Design gate | Reviewer A / B (Phase 3) |
|---|---|---|
| The gate seat's model available | the gate seat (Sol by default, Astra on an Astra row), effort per the rubric | Reviewer A: the gate seat, per the pairing rule (phases.md) |
| The row's model cooling, or rejected on every pair (Model pins, hop rules 1 and 3), the other available | the other model at the row's effective effort (excluded: xhigh); log "Sol quota spent, Astra gated" or "Astra quota spent, Sol gated" (a rejection: "rejected on every pair" in place of "quota spent") | Reviewer B: the other model at the row's effective effort (excluded: xhigh), only after a Claude build; log "Sol quota spent, Astra reviewed at <effort>" or "Astra quota spent, Sol reviewed at <effort>" (a rejection: "rejected on every pair" in place of "quota spent") |
| One model spent on every login (proxy 429 "All credentials for model gpt-6.2-sol are cooling down", or the same for `gpt-6.2-astra`, or every usage endpoint >= 95% for that model) | the other model through the proxy at the same effort the spent model's call would have used (the pin or the rubric row, never a fixed xhigh; an excluded build stays at xhigh over any pin), for every later call of the run that model would have taken; same log line as the row above, naming which model is spent | Reviewer B: the other model, same effort, only after a Claude build; same log line as the row above |
| Astra and Sol both cooling on every ChatGPT login and every fast native home (for both models: proxy 429 `All credentials ... cooling down`, 429 `usage_limit_reached`, or 503 `auth_unavailable: no auth available (providers=codex ...)` (seen 2026-11-17 with an upstream 402 `deactivated_workspace`); and `codex-fast-home` exit 3), confirmed as quota, not a 60-second transient cooldown: both 6.2 ids return a quota form on two probes 60 s apart (`python scripts/fabstra-review-round.py quota`), and until the GPT-6.2 re-probe passes a 503 `auth_unavailable` also needs every login's usage endpoint at >= 95% or `limit_reached` ("API seat (OpenAI credits)" below) | API seat on JC's OpenAI API credits through 8319 - GPT-6.2 Sol for a Sol-row call, GPT-6.2 Astra for an Astra-row call, as the effort-suffixed id `<model>-<effort>` ("API seat (OpenAI credits)" below), at the effort the subscription call would have used; log "API seat, OpenAI credits" | Reviewer G stands in as Reviewer A / B (pro-consult.md, "Reviewer G as stand-in"); a round with no qualifying Neon (API) or Carbon (either path) answer (skipped, failed, answered only through Hydrogen, or a `model_mismatch`) takes the API seat instead, and so does a contained change's one review; log "Reviewer G stood in" or "API seat, OpenAI credits" |
| Astra and Sol both cooling and the API seat failed (Phase 3: and no qualifying Neon (API) or Carbon (either path) answer (skipped, failed, answered only through Hydrogen, or a `model_mismatch`)), work not excluded | fresh Fable (Reviewer C), `model-router:reviewer` at effort high; log "same-family review, GPT seats cooling" | the same fresh Fable seat and log line |
| Astra and Sol both cooling and the API seat failed (Phase 3: and no qualifying Neon (API) or Carbon (either path) answer (skipped, failed, answered only through Hydrogen, or a `model_mismatch`)), work excluded (SKILL.md, Excluded categories) | fresh Fable (Reviewer C), `model-router:reviewer` at effort xhigh; log "same-family review, GPT seats cooling, excluded work" | the same fresh Fable seat and log line - nothing sensitive leaves the Claude login |
| Model rejected on every route: one model rejected on every pair of its walk (its 6.2 id and its fallback pin answer with a model-rejected / unsupported-model error, no quota error) and the other model rejected on every pair too or cooling (Model pins, hop rule 3) | fresh Fable (Reviewer C), `model-router:reviewer` at the row's effective effort (excluded: xhigh); log "model rejected on every route" | the same fresh Fable seat and log line; a Codex build, fix or write probe in this state goes to the Claude builders; this row never authorizes the API seat |
| Fable limit hit (429 "You've hit your Fable limit") wherever any row of this table or the pairing rule calls a fresh Fable | `pool/claude-fable-5-2` (a client's work: `client-<slug>/claude-fable-5-2` with its own `client-<slug>: usable` line, haiku mapping on the same prefix) headless on the credits pool ("Claude on credits seat (pool)" below; the review or design spec as the prompt, read-only tools) at the Fable seat's effort - only when the run was launched from a plain terminal or a scheduled task and the pool is usable; otherwise - a dry pool, or VS Code or the desktop app (credits refuse those `claude -p` children) - a fresh Opus 5.5 context (`subagent_type: "model-router:reviewer"`, `model: "opus"`, the same effort; tools stay Read, Grep, Glob, Bash; JC 2026-11-17; a Lane D session: lane-d.md, "Reviewer rule"); log which seat ran | the same seat and log line |
| Proxy 8317 still dead after one restart (`powershell -NoProfile -File '$MODEL_ROUTER_HOME/scripts/start-proxy.ps1 (start-proxy.sh on Mac/Linux)'`, retry once) | fresh Fable (Reviewer C), logged as a same-family review | fresh Fable (Reviewer C), same log |

Never skip the design review on a real build because the gate seat is down; never run it twice with the same spec. Codex-built work always goes to Reviewer C (pairing rule), whatever this table says for Claude-built work. `--bare` children load no ~/.claude hooks: the excluded-work check runs on the parent's launch command, and the auth-JSON guard does not reach inside the child.

## API seat (OpenAI credits)

JC 2026-11-17, updated 2026-11-18: the last-resort seat for Sol / Astra runs GPT-6.2 Sol or GPT-6.2 Astra (GPT-6.1 Sol as the fallback) on JC's OpenAI API credits, automatically and with no per-run cap, when the Reviewer fallback table's API row applies: Astra and Sol both cooling on every ChatGPT login and every fast native home (for both models: proxy 429 `All credentials ... cooling down`, 429 `usage_limit_reached`, or 503 `auth_unavailable: no auth available (providers=codex ...)` (seen 2026-11-17 with an upstream 402 `deactivated_workspace`); and `codex-fast-home` exit 3). It is a separate CLIProxyAPI instance on 127.0.0.1:8319 that holds only JC's OpenAI API keys and no ChatGPT login, so subscription traffic on 8317 never reaches it. Keys are read at each start from the `OPENAI_API_KEY` line of `~/.config/watch/.env` plus every `OPENAI_API_KEY_<NAME>` line of `~/.openai-api/keys.env` (JC adds accounts there); the proxy rotates across them and cools a key that hits its quota. `-Status` names the keys loaded, never their values. JC 2026-11-18: the seat serves GPT-6.2 Sol and GPT-6.2 Astra (Astra is allowed on the API seat from 2026-11-18, overriding the 2026-11-17 Sol-only rule), with GPT-6.1 Sol as the fallback; Astra costs about 4x Sol per token (Artificial Analysis $8/$40 vs $2/$10 per 1M, unverified against OpenAI's pricing page) and runs automatically and uncapped like Sol.

- Confirm quota before starting 8319: the trigger must be confirmed as quota, not a 60-second transient cooldown: BOTH 6.2 ids (`gpt-6.2-sol` and `gpt-6.2-astra`) return a quota form on two probes 60 s apart; one seat or one model retried is not enough. Prefer `python scripts/fabstra-review-round.py quota`, which does exactly that (exit 0 only when every probe of both ids is a quota form; 1 when any probe answers; 2 on any other answer); its `launch` without `--skip-quota` runs the same check before it starts the proxy (`--skip-quota` skips it, so it is never used to start a paid seat on an unconfirmed trigger). Until the native/login re-probe for GPT-6.2 passes (on or after 2026-11-21 15:27), a 503 `auth_unavailable` alone is not proof of spent quota, because the proxy can remember a per-login model rejection (quota.md): also check each login's usage endpoint (>= 95% or `limit_reached`) before starting 8319. A probe that answers is the subscription seat's answer, and 8319 is not started.
- Start, once per run, before the first API call and only after the Confirm bullet passed (this manual path included; prefer `fabstra-review-round.py launch` without `--skip-quota`, which re-runs the check itself): `powershell -NoProfile -File '$MODEL_ROUTER_HOME/scripts/start-api-proxy.ps1 (maintainer's machine only - not shipped)'` (exit 1 -> the seat failed: take the next row). A start that prints `api proxy running with an old model list (missing: ...)` means the running instance predates the effort-suffixed ids: `-Stop` it (never `-Force` while another session is connected), then start again.
- **Effort reaches OpenAI only through the model id.** 8319 exposes `<model>-<effort>` ids (model `gpt-6.2-sol`, `gpt-6.2-astra`, `gpt-6.1-sol`; effort `low`, `medium`, `high`, `xhigh`, `max`), each with a proxy payload rule that sets `reasoning.effort`; CLIProxyAPI 7.3.12 drops `--effort` on this path (verified 2026-11-18: no `reasoning` field upstream, OpenAI default medium), so every API-seat call before 2026-11-18 ran at medium whatever RUN.md logged. A plain 6.2 id fails with "unknown provider"; plain `gpt-6.1-sol` is the one deprecated exception (legacy note at the end of this bullet). `--effort` is still passed (it sets Claude Code's own budget) and must equal the suffix. Legacy note: the plain `gpt-6.1-sol` id still answers on 8319 (no effort rule, OpenAI default medium) only so older sessions keep working; new launches never use it.
- Launch: the Phase 1b or Phase 3 proxy `claude -p` command of this file, unchanged except `ANTHROPIC_BASE_URL=http://127.0.0.1:8319` and `--model <model>-<effort>` with `--effort <effort>`, plus a context variable: `CLAUDE_CODE_MAX_CONTEXT_TOKENS=500000` on Sol ids (`gpt-6.2-sol-*`, `gpt-6.1-sol-*`, "Model pins"), and `CLAUDE_CODE_MAX_CONTEXT_TOKENS=272000` on `gpt-6.2-astra-*` ids (as on the subscription Astra launches: OpenAI Codex catalogue window; the API window is unverified). Model choice for every API call (design gate, Reviewer A / B stand-in, a contained change's review), at the effort the subscription call would have used: a Sol-row call -> `gpt-6.2-sol-<effort>`, an Astra-row call -> `gpt-6.2-astra-<effort>`; a 6.2 call that fails upstream with a model-not-found / unsupported-model error from OpenAI (not the proxy's own `unknown provider for model` 400, which the seat-failed bullet below covers) -> one retry on `gpt-6.1-sol-<effort>`, logged `api-seat fallback 6.1`. The Codex transport and Codex-side builds never use it; builds fall back to the Claude builders as before.
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

## Phase 1b launch - DESIGN REVIEW (the gate seat - Sol or Astra - before any builder launches)

Mandatory for real builds. The cheapest bug is one caught on paper: the gate seat
reads the plan, every blueprint, and the repository, and reports where the
design will fail before Opus spends twenty minutes building it.

**Transport (fallback - the primary is the fast path in "Standing fast window: reviews" above):** write the design-review spec to
`<scratch>/fabstra-design-<name>.md`, then one Bash call,
`run_in_background: true`, timeout 1600000 (above the child's `timeout 1500`: Claude Code 2.1.285+ stops a background command when its Bash timeout runs out, and 2.1.288 lifts that only for interactive sessions, so a `-p` parent still enforces it), cwd = the project directory:

```bash
KEY=$(proxy-key) || exit 1
CLAUDE_CODE_MAX_CONTEXT_TOKENS=500000 ANTHROPIC_BASE_URL=http://127.0.0.1:8317 ANTHROPIC_AUTH_TOKEN="$KEY" timeout 1500 claude -p --model gpt-6.2-sol --effort <effort> --bare --max-turns 30 --permission-mode default --allowedTools "Read,Grep,Glob,Bash" --output-format json < <scratch>/fabstra-design-<name>.md > <scratch>/fabstra-design-<name>.md.out 2>&1
```
Astra row: the same command with `--model gpt-6.2-astra` and `CLAUDE_CODE_MAX_CONTEXT_TOKENS=272000` in place of 500000 (effort per the rubric).

The report is the `result` field of the last JSON line in the `.out` file
(a warning line precedes it; `--output-format json` with the spec fed on
stdin (`< spec.md`, so stdin reaches EOF) is what stops the nested
`claude -p` from hanging after it prints; the spec is not a command-line
argument, so its length is not capped (a 40 KB spec has passed)). `--bare` skips CLAUDE.md, so the spec carries every stack rule. Since
Claude Code 2.1.323 an unknown model id is assumed to have a 1M window
(200k before), so the context variable pins each model's real window (Model
pins) and is recomputed on every model hop. Keep `--max-turns 30`. **Fallback:** the Codex transport
above without `--write` (read-only sandbox; the report arrives only through
`result`). **The gate seat's model blocked** (quota.md, "Astra blocked, how to
read it", which reads the same for either model), the other cooling too, an
excluded category, or a dead proxy: take the design gate
column of "Reviewer fallback" above. Never skip the design review on a real
build because the gate seat is down; never run it twice with the same spec.

In the same message as the gate seat, launch the plan-mode Gemini consult
(pro-consult.md, "Gemini consult - the build-sheet seat").

While the gate seat reviews, do not launch builders. Do prepare: the review-spec
skeleton for Phase 3, the smoke-gate command, and the logbook entries.

## Phase 3 launch - ADVERSARIAL REVIEW (Sol, Astra, or a fresh Fable context)

Mandatory for real builds; skip only for a small change as Phase 1 defines
it, and say so in the report. Pick the reviewer by the pairing rule: Claude built -> Reviewer A (the gate seat: Sol by default, Astra on an Astra row); Codex side built -> Reviewer C (fresh Fable); a contained change (phases.md Phase 1): Claude built -> Sol at `--effort high`, Codex built -> Reviewer C, no second seat; a mixed build -> Reviewer A on the BUILDER tasks and Reviewer C on the CODEX tasks plus every seam, partitioned (pairing rule, phases.md); an xhigh row adds Reviewer C in parallel with Reviewer A on the BUILDER tasks; the row's model cooling after a Claude build -> Reviewer B (the other model, same effort; excluded: xhigh). The review spec template below is the contract for every reviewer
and every transport. In the same message as each review round's seat(s) of a real build, launch Reviewer G (Carbon; pro-consult.md, "Reviewer G"): its items are findings ruled like any reviewer's once the lead confirms them, it never passes a build alone, and a skipped or failed launch never blocks the round.

**Reviewer A through the proxy (fallback - the primary is the fast path in "Standing fast window: reviews" above; Sol shown, an Astra row swaps the model and the context variable):** write the review spec to
`<scratch>/fabstra-review-<name>.md`, then one Bash call, `run_in_background: true`, timeout 1600000 (above the child's `timeout 1500`, same reason as the design call), cwd = the project directory:

```bash
KEY=$(proxy-key) || exit 1
CLAUDE_CODE_MAX_CONTEXT_TOKENS=500000 ANTHROPIC_BASE_URL=http://127.0.0.1:8317 ANTHROPIC_AUTH_TOKEN="$KEY" timeout 1500 claude -p --model gpt-6.2-sol --effort <effort> --bare --max-turns 30 --permission-mode default --allowedTools "Read,Grep,Glob,Bash" --output-format json < <scratch>/fabstra-review-<name>.md > <scratch>/fabstra-review-<name>.md.out 2>&1
```
Astra row: the same command with `--model gpt-6.2-astra` and `CLAUDE_CODE_MAX_CONTEXT_TOKENS=272000` in place of 500000, at the rubric effort; a contained change (phases.md Phase 1): Claude built -> Sol (`gpt-6.2-sol`) at `--effort high`, Codex built -> Reviewer C, no second seat.

   The report is the `result` field of the last JSON line in the `.out` file. The seat on this path can write, so the spec's save line lands the findings file in scratch. `--bare` skips CLAUDE.md, so the spec must carry every stack rule. Keep `--max-turns 30`; never raise it. With the diff and callers front-loaded in the spec (below), 30 tool calls cover a normal review; a run that hits the ceiling still leaves its incremental findings file.

**Reviewer A on the Codex CLI (fallback):** use it when the
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

**Reviewer B, the other GPT model (the cooldown seat):** the same proxy
command with the other model's `--model` and context variable (Astra when Sol
is out: `gpt-6.2-astra`, 272000; Sol when Astra is out: `gpt-6.2-sol`, 500000)
and the same effective `--effort` (hop rules, Model pins); the
Codex transport with that `--model` is its
fallback. Use only after a Claude build when the row's model is cooling or
rejected on every pair; it never reviews Codex-built work. Log "Sol quota spent, Astra reviewed at
<effort>" or "Astra quota spent, Sol reviewed at <effort>".

**Reviewer C, fresh Fable 5.2 context:** one Agent tool call,
`subagent_type: "model-router:reviewer"`, `effort: "high"` (Fable 5.2 at high with Read, Grep,
Glob, and Bash only, enforced by the agent definition), prompt = the review spec
verbatim. A build in an excluded category takes `effort: "xhigh"` on the same seat (Fable 5.2 at xhigh, the same tools) - phases.md, "Claude seat efforts". It has seen none of the build, which is the point - never paste
your session context into it. Run it as the review when the Codex side
built, and as the fallback "Reviewer fallback" names (log it as a
same-family review); Astra and Sol both cooling with the proxy still up reaches
this seat only through that table's two rows after the API seat (the API seat failed, and in Phase 3 no qualifying Neon (API) or Carbon (either path) answer (skipped, failed, answered only through Hydrogen, or a `model_mismatch`)): work not excluded
(`model-router:reviewer` at effort high) and work excluded (the same seat at effort xhigh);
pairing rule in phases.md.
First transport for every Reviewer C call: "Reviewer C on credits (fable-review.py)" above; this Agent call is its fallback.
