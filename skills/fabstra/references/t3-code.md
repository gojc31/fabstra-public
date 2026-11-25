# FabStra in T3 Code - seats, login overflow and Antigravity

Contents: When this file applies; Seat map in T3; Claude login overflow; Antigravity in T3; Delegate reviewers are not read-only; Privacy; Credits in T3; Replies in T3; What T3 does not change

Reached from: fabstra SKILL.md - at run start, when `CLAUDE_CODE_ENTRYPOINT=t3-code`

Related:
> Crew, hop rules, write probe, Reviewer fallback, credits seats: transport.md (this file adds T3 rungs only). Gemini seats and the parked agy wrapper: pro-consult.md. Report and asks: decision-page.md.

## When this file applies

- T3 Code runs Claude Code through the Agent SDK; a T3 session has `CLAUDE_CODE_ENTRYPOINT=t3-code` (verified 2026-11-22). JC moved from VS Code to T3 Code on 2026-11-22.
- Check it once at run start and log `surface=t3`. Outside T3 nothing here applies.
- Opus 5.5 stays the session model and daily driver; modes, gate seat rubric, efforts and pairing rule are unchanged.

**T3 delegate basics** (verified 2026-11-22):
- `delegate_task` starts a child thread on any enabled provider instance. `orchestrator_capabilities` lists instances, models and options: call it once per run, before the first `delegate_task`, and log the instance ids used. The session's own id is its `inheritedProviderInstanceId`.
- Effort goes in `target.options`: Claude `effort`, Codex `reasoningEffort`, Antigravity `thought_level`.
- **Full access (JC 2026-11-25):** children inherit the parent thread's `runtimeMode` and cannot exceed it; an Antigravity child in `auto` asks JC to approve every file read. Every Antigravity `delegate_task` passes `runtimeMode: "full-access"`, and every `t3_thread_launch` / `create_threads` passes `runtimeMode: "full-access"`. When `orchestrator_capabilities` shows this thread's `runtimeMode` is not `full-access` (imported and MCP-launched threads start in `auto`), launch no Antigravity seat: tell JC once to switch this thread's access to Full access (no tool can), and route the seat to its non-Antigravity spare meanwhile.
- A child gets only its `task` text (no parent history). Its default cwd is the T3 project root (probed: the home folder, not the repo), so every delegated spec carries absolute paths and an explicit `cd`. Never put a secret in `task`.
- Completion wakes the parent: never poll (`task_status` only after the wake), never sleep; `task_cancel` a child no longer needed; every child finishes before the run ends (SKILL.md rule 4).
- Probe 2026-11-22, Claude slot child (Haiku low on a second login): own `CLAUDE_CONFIG_DIR` slot home, entrypoint `t3-code`; the model-router plugin, fabstra skill and `model-router:builder` all loaded.
- Probe 2026-11-22, `codex-cliproxy` child (`gpt-6.2-sol` low): `CODEX_HOME` is a T3 profile with NO agents directory (it cannot spawn `terra` / `luna` / `spark`); sandbox danger-full-access, not read-only; effort honoured.
- Efforts above xhigh (`max`, `ultra` on Codex; `max` / `ultrathink` on Claude) exist in T3, unused by the rubric; only a user effort word pins `max`.

## Seat map in T3

Every primary path, hop order and fallback ladder in transport.md stays as written; T3 adds rungs only where named here (gate D6).

| Seat | Primary route in T3 | T3 delegate route (when) | Notes |
|---|---|---|---|
| Claude builders (every tier) | Agent seat `model-router:builder` on this login, effort by tier | another Claude login (Claude login overflow) | no credits-pool build seat in T3 |
| Fresh-Fable seats (Reviewer C, design gate fallback, Lead-mode independent reviewer) | transport.md's attempt order: `fable-review.py` on plan credits first when its "Use it when" and PARTIAL rules allow (a non-git repo such as model-router runs in folder mode, by `--diff-file` from the pre-edit backups or `--plan-file`; with no complete diff to build, the Agent seat), then `model-router:reviewer` (interim pin 2026-11-21: Opus 5.5 on the subscription; Fable only on plan credits) | none (gates D5, D8) | no unrestricted delegate precedes the restricted Agent reviewer |
| Gate seat, Reviewer A / B (Sol, Astra) | unchanged: transport.md's full ladder, its harness-failure rung ("Reviewer A on the Codex CLI (fallback)") included | none | a T3 Codex child on the router instance reaches the same 8317 router and is not read-only |
| Codex-side builder | the Codex companion CLI (main home has `terra` / `luna`; `spark` only on the Pro home, `~/.codex-pro/agents`) | single-seat delegate child when the companion fails to start (below) | Codex-built -> fresh Fable reviews |
| Gemini seats | Reviewer G, Hydrogen, Gemini consult on `geminipro` | Reviewer AG and a builder (Antigravity in T3) | |
| Lane B, Lane D | unchanged: Lane B's Reviewer S + fresh Fable; Lane D's stripped-env headless Claude route (lane-b.md, lane-d.md) | none | T3 overflow never applies inside them |

**Codex delegate hop (gate D6).** One hop target for a Codex BUILD whose companion launch fails to start; not a quota hop (quota follows the hop rules, transport.md "Model pins").
- A single-seat child: ONE hard- or contract-tier task, no children, so the spec omits the parent clauses. Model per the row (`gpt-6.2-sol`; Astra row `gpt-6.2-astra`); `reasoningEffort` per the rubric, always passed (T3's default is low).
- Order, by role (ids from `orchestrator_capabilities`, logged): the Codex instance routing through the local 8317 router (e.g. `codex-cliproxy`; the router home in the tried-pairs list) first, then a T3-managed Codex profile with its own login (e.g. `codex`, home `t3-codex`). The business instance (e.g. `codex-business`) only when JC names it.
- Before the first write build on a home, run transport.md's "Codex write probe" on that instance: a child creates one probe file in the repo and leaves it; the LEAD verifies the file and its content, records the verdict per home in RUN.md, then removes the file.
- A failed probe splits by cause: a write denial (`EPERM`, blocked or sandboxed write) follows hop rule 7 (the task goes to the Claude builders); a quota error follows hop rule 1, a model rejection hop rules 2-3 (the next untried pair, then the other model), as transport.md's "Codex write probe" says.

**Family follows the model, not the transport** (pairing rule): an Antigravity Gemini seat is the Gemini family (as Reviewer G); a Claude model served by Antigravity is Claude and is never used.

## Claude login overflow

JC 2026-11-22: overflow "when this one is near its limit". Targets: JC's personal Max/Pro logins (never billing extra usage) and Team premium seats under 90% of a capped pay-as-you-go (never into it; refused if the org pushed settings). Never Enterprise.

**Envelope:** the default T3 profile (`~/.t3`) only, not `T3CODE_HOME` or `--base-dir`; the picker fails closed, never mirroring T3.

**Single login** (no `~/.claude-slots/rotation.json` or picker script): no picker; read only `oauthAccount.hasExtraUsageEnabled` in current's `.claude.json`: exactly `false` -> the Agent seat, else the no-Claude order. Log `picker: skipped (single login) extra_usage=<off|not-off>`.

**Per build wave:**
1. Once: `timeout 150 python <claude-usage helper> > <scratch>/usage-<wave>.json` (150 s: serial, <=20 s per login). A timeout or empty file makes the picker exit 2.
2. Before each Claude builder launch: `python "${CLAUDE_PLUGIN_ROOT}/scripts/t3-pick-login.py" --current <this session's instance id> --usage-json <scratch>/usage-<wave>.json --launch-root <the T3 project root> --only <instances supporting the seat's model and effort> --threshold 90 --json`. Resolve `${CLAUDE_PLUGIN_ROOT}` to the installed plugin root (gate D10). `--launch-root` = the child's real start dir: this thread's T3 project root (`t3_project_read` workspace root); the overflow `delegate_task` never sets worktree isolation or a workspace strategy.

**Interface** (read-only, no network, no subprocess, never prints a token, email, cap / spend amount or settings value):

| Flag | Meaning |
|---|---|
| `--current` (required) | the session's own instance id (`inheritedProviderInstanceId`, e.g. `claudeAgent`); ids here and in `rotation.json` must match `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$` (else exit 2, value-free; bad T3 `providerInstances` keys are ignored) |
| `--usage-json` (required) | the wave's usage file; missing, unreadable or not a JSON list -> exit 2; the picker never runs the helper. Team seats read a row's `extra` (check 4) |
| `--threshold` | near-limit percent (default 90) |
| `--only` | candidate allowlist, applied BEFORE ranking; current is not affected |
| `--launch-root` (required) | the child's real start dir (step 2); missing -> exit 2 |
| `--slots-dir`, `--main-home`, `--t3-settings` | `~/.claude-slots` (`rotation.json`, `limits.json`), `~/.claude`, `~/.t3/userdata/settings.json` (`providerInstances`) |
| `--t3-runtime` | default `~/.t3/userdata/server-runtime.json` (only `managedPolicy` is read) |
| `--now` | timezone-aware ISO8601 (tests); naive or malformed -> exit 2 |

**Checks** (a login's first failing check is its `refused` reason; only not-found confirms absence, any other probe error fails closed):
1. `no-home` - instance absent, disabled, another driver, or home dir missing (strict resolve); undecidable whether the built-in shares the sibling `~/.claude.json` -> `no-home`. The built-in `claudeAgent` uses `--main-home`; ANY `config.homePath` key on it -> `no-home:envelope`. A non-built-in instance whose home resolves to the main home -> `no-home:ambiguous`. Two or more rotation ids (built-in included) whose homes are one directory, or cannot be compared -> `no-home:duplicate` for each (`no-home:ambiguous` still wins for a slot on the main home). The built-in is never a candidate (it inherits the T3 server's unseen env): `no-home:builtin`.
   - Then, candidates only: `privacy:t3-instance:<key>` - the T3 `providerInstances` entry sets a non-empty `environment`, `config.binaryPath` or `config.launchArgs` (`<key>` = the field); entry or `config` not an object -> `privacy:t3-instance:config`.
2. `identity-mismatch` - account email differs from (or is absent in) `rotation.json`'s for that instance; unreadable `.claude.json` -> `unreadable:.claude.json`.
3. `org:<label>` - `organizationType` not `claude_max`, `claude_pro` or exactly `claude_team`: `org:enterprise` (contains "enterprise"), `org:missing` (absent or null), else `org:unknown` (never echoed).
4. `money:extra-usage` - `hasExtraUsageEnabled` true, missing or not a bool. Team seats instead (`extra.enabled` untrusted) use only the slot's own row (`slot` = the home's folder name, home directly under `--slots-dir`, email = rotation's; other slots' rows are ignored, for `used` too), first failing: no such row with an `extra` object, or two disagreeing -> `money:team-unknown`; `cap` null or absent -> `money:team-uncapped`; `cap` not a finite number > 0 or `spent` not finite >= 0 -> `money:team-unknown`; `cap_reached` true -> `money:team-cap`, not exactly false -> `money:team-unknown`; `spent` >= 90% of `cap` (exact: `spent*10 >= cap*9`) -> `money:team-cap`; `5h` and `week` not both valid -> `money:team-unknown` (never the first unknown); usage file mtime over 30 min old or future -> `money:team-stale-usage`.
5. `privacy:<file>` - non-empty `remote-settings.json` or `managed-settings.json` in the home (`{}` passes). Team: `remote-settings.json` absent (never fetched) -> `privacy:remote-settings.json:absent`; its mtime over 24 h old, future or unreadable -> `privacy:remote-settings.json:stale`.
6. `privacy:<file>:<name>` - the home's `settings.json` / `settings.local.json` sets a gated env name (`GATED_ENV`: telemetry, API keys, tokens, their file descriptors, custom headers, base URLs, Bedrock / Vertex / Foundry, HTTP(S) proxy, `CLAUDE_CONFIG_DIR`; `OTEL_*`, `CLAUDE_CODE_MANAGED*`) or an `apiKeyHelper`, `otelHeadersHelper`, `awsAuthRefresh` or `awsCredentialExport` key; odd key names show as `OTEL_*` / `env`; `env` not an object -> `privacy:<file>:env`; unreadable -> `privacy:unreadable:<file>`.
7. `privacy:hooks:<file>` - the home's `hooks` differ (JSON-aware: `true` is not `1`) from the main login's same-named file.
8. `limited` - `limits.json` limits it until a later time (a malformed entry counts as limited: `limits:malformed`).
- Known used at or over the threshold -> `near-limit`.
- Global checks (every candidate refused, listed once as instance `*`): a gated name in the picker's own env -> `privacy:process-env` (`CLAUDE_CONFIG_DIR` exempt only for a slot current whose located home it names, as T3 sets it; always gated in settings env); `T3CODE_HOME` set -> `privacy:t3-home`; launch root not an absolute existing directory -> `privacy:launch-root:missing`; its `.claude/settings*.json` trips check 6 -> `privacy:launch-root:<file>:<name>` (unreadable: `privacy:launch-root:unreadable:<file>`), hooks unequal to the main home's -> `privacy:launch-root-hooks:<file>`; T3 policy (Privacy) -> `privacy:t3-policy`; Claude Code managed settings present or undeterminable (`C:\Program Files\ClaudeCode`, `C:\ProgramData\ClaudeCode`, `SOFTWARE\Policies\ClaudeCode` in HKLM 64/32-bit or HKCU; always off Windows; none here 2026-11-22) -> `privacy:cc-managed`.
- Any `"type": "http"` hook, even when equal to main: in a candidate's settings -> `privacy:http-hook:<file>`; in the launch root's -> `privacy:http-hook:.claude/<file>` (instance `*`).

**Current login:** `current_verified` = passes checks 1, 2 and 4. Picked when verified, not limited, and used under the threshold or unknown; else overflow. `current_reason`: `current-ok` / `current-unknown` when picked, else current's first failing reason (`no-home`, `no-home:ambiguous`, `no-home:envelope`, `no-home:duplicate`, `unreadable:.claude.json`, `identity-mismatch`, `money:extra-usage`, `limited`, `limits:malformed`, `near-limit`). A built-in current with `CLAUDE_CONFIG_DIR` in the picker's env (any value, even `~/.claude`) is outside the envelope: `current_verified: false`, `current_reason: no-home:envelope`, `current_extra_usage: unknown`, and `privacy:process-env` refuses all. A Team current keeps these rules.

**Overflow:** rotation order, minus current, restricted by `--only`, minus logins failing a check or at/over the threshold. Lowest known used wins; ties -> rotation order; none known -> the first unknown. Reason `overflow`; none left -> exit 3, `none-usable`.

**Known limits** (accepted, JC 2026-11-22):
1. The current-login Agent seat runs under the lead session's own machine, org and hook settings: a global privacy refusal blocks overflow only, not the current seat.
2. A slot's credentials file is trusted to match its `.claude.json` account.
3. Hooks identical to the main login's, and plugin hooks, are trusted as JC's own baseline.
4. The child fetches and silently applies org settings at start (non-interactive); the cache check cannot close that window, and an mtime proves only that something wrote the file.
5. The usage snapshot can be up to 30 min old and a build can cross 90% mid-run: the monthly cap is the bound, not zero.

**Output:** `--json`: `instance` (id or null), `reason`, `used` (pct or null), `current_verified`, `current_extra_usage` (`off` / `on` / `unknown`), `current_reason`, `refused` [{`instance`, `reason`}]; plain: the first six as `key=value` (null: `none` / `unknown`). Exit 0 picked, 3 none usable, 2 bad input or internal error (one fixed line naming the flag, file or exception class, never a value). No exit 1.

**What the lead does:**
- `current-ok` / `current-unknown` -> the Agent seat as today; log the reason.
- Lead thread in a worktree, or the child's start dir unknown -> no overflow: the Agent seat here if the picker's `current_verified` is true, `current_extra_usage` `off` and `current_reason` not `limited` / `limits:malformed` (pick ignored), else the no-Claude order.
- `overflow` -> `delegate_task` with `target: {providerInstanceId: <picked>, model: <m>, options: {effort: <e>}}` (the seat's effective model and effort), `role: "implementation"`, the builder spec as `task`. Gate N3: `claude-opus-5-5` at the tier effort; a Sonnet max pin `claude-sonnet-5-5` at `max`; a user effort pin carries through; `--only` lists the instances whose `orchestrator_capabilities` entry offers that model and effort. The `task` opens with "You are a delegated FabStra build seat (model-router:builder rules): follow this spec, start no orchestration flow." then the absolute repo path and an explicit `cd`. Log `seat=t3-delegate instance=<id> model=<m> effort=<e> reason=<reason> used=<pct>`.
- Exit 3 -> the Agent seat on this login ONLY on `current_verified: true`, `current_extra_usage: "off"` AND `current_reason: "near-limit"` (gates D1, N2); never on `limited` or `limits:malformed`. Otherwise **no-Claude order**: no Claude launch; the Codex side if the tier allows, else the Antigravity builder (case b), else the run waits for quota (transport.md quota row).
- Exit 2 -> fail closed: no delegate, no Agent seat; fix the input (usually: re-run the usage helper), re-run the picker once; a second exit 2 -> the no-Claude order; log the error.
- The delegate route skips the Agent guard: the lead always passes model and effort.

**Money rule scope (gate D1).** The picker places Claude BUILD seats only; the lead and its Agent reviewers stay on JC's chat login; when `current_extra_usage` is not `off`, report line 4 says so once.

**Privacy scope (gate D2).** The child's `cd` into a repo does not reload its `.claude/settings*.json`; anything else changing a child's effective settings is outside the gate (Privacy, below).

## Antigravity in T3

JC 2026-11-22 chose "Reviews + builds, everywhere", told Google may train on consumer-plan chats, citing Theo (T3's maker), https://x.com/theo/status/2124264935505199294, 2026-11-21: "T3 Code has officially supported Antigravity with their provided integration for months now. There is zero risk to using Gemini subs in T3 Code." That is the integrator's statement, not Google's: Google's FAQ still says wrapping `agy` in third-party agents is unsupported on consumer plans, and consumer Interactions may be used for training (report 2026-11-17). JC accepted both, for client repos too.

- **Route:** `delegate_task` to the Antigravity instance from `orchestrator_capabilities` (e.g. `antigravity`) (T3's managed copy of Google's official ACP agent). Never `agy -p`, never CLIProxyAPI's antigravity login: those stay banned (pro-consult.md).
- **Models** (`orchestrator_capabilities` 2026-11-22; the T3 route's first live call, the Carbon build probe, PASSED 2026-11-24 - see "Antigravity builder" below): `gemini-4-neon` (thought_level low|medium|high|xhigh, default medium), `gemini-4-carbon` (low|medium|high|xhigh per orchestrator_capabilities 2026-11-24, default high; on the Pro plan), `gemini-4-hydrogen` (low..xhigh). `gemini-4-argon` and `gemini-3.8-flash` are removed by Google on 2026-11-30 (antigravity.google/docs/models): never route to them after that date. The instance's Claude Opus / Sonnet 5.5 are never used (Claude work stays on the Claude logins).
- **Round check first (JC 2026-11-23, narrowing JC's 2026-11-22 every-round choice):** Reviewer AG, the "Paid Reviewer G in T3" cases below and their default skip log apply to round 1 of a real build only; a later round runs only Reviewer G as stand-in (case 3; pro-consult.md, "Reviewer G as stand-in"), never AG. Any other re-review round launches no Neon seat, writes no skip record and waits for none; the pending live AG re-review test is void, because Neon no longer reviews re-reviews.
- **Reviewer AG (Antigravity first, JC 2026-11-23):** reads the repo and is the round's Neon reviewer in round 1 of a real build, any repo, client repos included (read in place), with no secrets in its `task`. Skips: a `no gemini` brief; an excluded-category build (unlike Reviewer G); Gemini-built work. Advisory: items are leads the lead confirms against the code; never a gate, Reviewer A/B/C or pass/fail; a failure never blocks. `gemini-4-neon` at thought_level high; spare `gemini-4-carbon` high on a Neon quota, limit or model-removed error, then `gemini-4-hydrogen` (in T3 this Antigravity Carbon is also the spare before the paid `geminipro` Carbon, JC 2026-11-24). Run the no-write check below around it.
- **Paid Reviewer G in T3** (pro-consult.md, "Reviewer G"): the free Antigravity pool carries the default round, so a T3 session launches the paid Neon seat only when one of these holds:
  1. an excluded-category build (AG skips it);
  2. an xhigh row;
  3. the gate seat is down - Sol and Astra both cooling (G's stand-in clause), or a transport.md fallback row needs a qualifying Neon or Carbon answer;
  4. AG gives no answer this round: skipped by the cap, quota or limit on every spare model, a failure, an empty answer, or nothing within 1,200 s.
  Cases 1-3 launch G in the same message as the review seats. Case 4 launches G when AG ends, and the round waits for G's answer, skip or failure. With none holding, log `seat=gemini mode=review skipped: t3 antigravity-first leads=0 real=0`. A `no gemini` brief skips both; sessions outside T3 have no AG and keep Reviewer G in round 1 and its stand-in rounds.
- **Every other Gemini seat goes to Antigravity first (JC 2026-11-25).** In a T3 session these seats go to Antigravity `delegate_task` first: Gemini plan mode, the Gemini report check, the Hydrogen quick check and fix check, and every Gemini consult (beside a Pro consult, or alone as a quick second opinion). geminipro's paid API is the backup only.
  - **The task:** the same brief text the geminipro brief file would carry, with no secrets, plus "Answer in text. Do not edit, create or delete any file." Pass `runtimeMode: "full-access"` and run the no-write check below around it.
  - **Models:** `gemini-4-neon` at thought_level high for plan mode, the report check and consults. `gemini-4-hydrogen` at thought_level medium for the quick check and fix check. Spares: Neon falls to `gemini-4-carbon` high, then Hydrogen; Hydrogen falls to Neon medium. A switch is logged `antigravity pool switch <from> -> <to>`.
  - **Backup:** the geminipro launch the seat's own section names (pro-consult.md), only when Antigravity cannot answer: this thread is not in full access, every model above returned a quota, limit or model-removed error, the weekly Gemini bar is at 90% or more, the cap below is reached, or there is no answer within 1,200 s. Log the reason on the geminipro record as `agy-first fallback=<reason>`.
  - **Cap:** 8 dispatches per run, spare hops included, separate from Reviewer AG's 6. Log `seat=agyseat-t3 mode=<plan|report|consult|quick|fix> dispatch=<k>/8` before each, and the answer as `seat=agyseat-t3 mode=<mode> model=<m> level=<l> leads=<n> real=<m>`.
  - **Unchanged:** a `no gemini` brief skips both routes, and the seat's triggers, brief rules and the way you handle its answer stay as pro-consult.md says. Sessions outside T3 keep geminipro.
- **Antigravity builder:** `gemini-4-carbon` (thought_level high; JC 2026-11-24; probe build PASSED 2026-11-24: one mechanical task, tests untouched, no writes outside its folder; `gemini-4-argon` is never used after 2026-11-30; spare `gemini-4-neon` high on a quota, limit or model-removed/not-found error) builds (a) any task JC names ("antigravity builds T2", "use antigravity for T<n>"), and (b) by default, contract- and mechanical-tier tasks in a T3 session (JC 2026-11-23: use the Pro plan before buying Ultra), and in the picker's no-Claude order (above). Hard-tier tasks stay on `model-router:builder` unless JC names them, and so does a contract or mechanical task on the critical path (a later wave waits on it). On Carbon and Neon both limited, a default-routed task goes to `model-router:builder` at the tier's effort, logged `seat=antigravity-builder fallback=claude`; in the no-Claude order it follows that order's next step instead. Every Antigravity builder spec (Carbon is unbenched; the Argon bench below is the reason) names every existing caller and stored-data format the change must keep working, and says in so many words that existing tests are never edited - a clash with one is reported, not fixed (bench 2026-11-23, 26 Argon runs: review recall 8/8 like Neon at half the time; builds pass hidden tests, but on conflict or unstated compatibility Argon changed the guard - an old caller's data, an existing test - in 4 of 4 runs). Argon runs 3-6x slower than Claude.
  - Never on a `no gemini` brief (gate N1: checked before any task text or repo path is sent). Never a hard-tier or excluded-category task unless JC names it. The spec carries absolute paths and the verify rule (verify-rule.md).
  - Review (gate D7), by family: the gate seat (Sol / Astra per the rubric, Reviewer A) is accountable, plus a fresh Fable on an xhigh row; with Sol and Astra both out, a fresh Fable (Reviewer C) is the cross-family fallback. Reviewer G / AG never review Gemini-built work; Reviewer G's stand-in clause never applies to it.
  - Mixed builds: the plan gives every task one owner and names each seam (shared interface or file) with its owning task; the smoke gate runs over all of them.
  - Log `seat=antigravity-builder model=<m> level=<l> reason=<named|default|overflow>`.
- **Pools** (JC 2026-11-24: there is no separate Argon weekly pool any more): one shared Gemini pool (5-hour and weekly) for every Gemini 4 model, and a Claude & GPT pool FabStra never uses. Builds and Reviewer AG draw on the same pool: when the T3 usage panel shows the weekly bar at 80% or more, default-routed builds go to `model-router:builder` so reviews keep their quota. A quota error on one seat's model switches it to its spare, logged `antigravity pool switch <from> -> <to>`.
- **Caps:** Reviewer AG 6 dispatches per run, spare-model hops included: log `seat=agyseat-t3 dispatch=<k>/6` before each; a 7th is skipped (`seat=agyseat-t3 skipped: cap`). The builder: the tasks the plan assigns. Log AG answers as `seat=agyseat-t3 model=<m> level=<l> leads=<n> real=<m>`.
- **Supersedes, for T3 sessions only,** the "Parked" status and the agyseat rule that a fresh Fable always reviews the Antigravity builder. The agy CLI wrapper (`scripts/agyseat.py`) stays parked as pro-consult.md says.

## Delegate reviewers are not read-only

Gate D8. T3 children are not tool-restricted and start in the T3 project root with full access, so a delegate seat (Reviewer AG, and the other Antigravity Gemini seats above) is advisory, never a replacement for a tool-restricted seat that can run. Best-effort no-write check around each:
1. Before launch, hash every file under the repo (sha256 of path + content; skip `.git/` and `node_modules/`; `.fabstra/` specs and logbooks ARE included, so an edit there shows).
2. The lead lists the writes it expects during the review: its own logbook entries, and files another active run's logbook names.
3. After it lands, hash again, diff the inventories (added, removed, changed) and subtract the expected writes.
4. Any other change: log `unattributed change during Reviewer AG: <paths>` and show it in report line 4; it is attributed to AG only with evidence (AG's own transcript showing a write tool call). Confirmed findings still count; the change is preserved (reverting needs JC's go). An unattributed change in a deliverable file landed after the smoke gate, so the smoke gate re-runs and that round's accountable reviewer covers the changed files before sign-off (gate N5); a change only in `.fabstra/` logbooks is reported, nothing more.

Writes outside the repo are not detectable this way.

## Privacy

Best-effort, not a guarantee. JC 2026-11-22: "make sure ... admins can't see our prompts/chats for the accounts".
- Facts (2026-11-22): T3 delegate children run non-interactive, so org-pushed (server-managed) settings apply there with no approval dialog and no cache write (code.claude.com/docs/en/server-managed-settings.md). Team-plan admins see usage metrics only, not prompts (code.claude.com/docs/en/analytics.md); Enterprise orgs can read Claude Code transcripts through the Compliance API (platform.claude.com/docs/en/manage-claude/compliance-sessions).
- Every Claude login FabStra delegates to passes the picker's checks (above).
- T3 managed policy is a presence rule (T3 server bundle, 2026-11-20): all refused `privacy:t3-policy` when the policy file exists with any content (Windows `C:\Program Files\T3Code\policy.json`, macOS `/Library/Application Support/T3Code/policy.json`, Linux `/etc/t3code/policy.json`), the Windows key `HKLM\SOFTWARE\Policies\T3Tools\T3Code` exists, or the running server's `managedPolicy` (`--t3-runtime`) is not `null`; a source that cannot be determined, or a missing or invalid runtime file, also refuses. No policy on this PC (2026-11-22).
- The gate reads cached settings at pick time; the child fetches its own at start, so a setting pushed in between is not seen.
- The lead never forwards a login's settings content. A refused login is logged with its reason and skipped.
- JC's own T3 chats on a Team login carry the same org-settings exposure; `claude-slots status` shows `ORG PUSHED SETTINGS` when a cache is non-empty.

## Credits in T3

JC 2026-11-22: "we need to also use fable 5.2 via our api credits pool right". Yes:
- Every fresh-Fable seat keeps `fable-review.py` on plan credits FIRST in T3 wherever transport.md's eligibility and PARTIAL rules allow (plain Messages API, not blocked by the entrypoint; two `fable-consult.py` calls on acct1 ran from a T3 session 2026-11-22). The Fable consult checkpoints keep `fable-consult.py`.
- Only the Opus credits-pool BUILD seat (`claude -p` on 8318) is unavailable from a T3 thread: entrypoint `t3-code` is treated like an IDE (1.18.5 added it to IDE_MARKERS so it fails fast), so the subscription seats build. Any other pool `claude -p` seat transport.md allows only from a plain terminal or scheduled task is likewise dry here.
- Never fake or strip `CLAUDE_CODE_ENTRYPOINT`. Whether `claude` typed in T3's own terminal counts as a plain terminal is unverified (credits-test OWED since 2026-11-22).

## Replies in T3

The short report (decision-page.md) still holds; in T3 its status lines render as one `html_render` card (theme variables, no outer background), and every choice is AskUserQuestion buttons (global rule "Replies in T3 Code"). No Artifact.

## What T3 does not change

- Excluded categories (SKILL.md); the pairing rule (phases.md).
- The hop rules and the "Reviewer fallback" table (transport.md).
- The credits pool rules outside T3 (transport.md).
- Lane B and Lane D (lane-b.md, lane-d.md).
- The logbook rules (phases.md, "The run logbook").
