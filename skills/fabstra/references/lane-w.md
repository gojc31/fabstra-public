# Lane W - non-gating second opinion (ChatGPT chat pool)

Reached from: fabstra SKILL.md -> transport.md crew table

Related:
> The crew-table row and the "SECOND OPINION (Lane W)" seat are in transport.md.
> The Lane W fallback wording (cannot close the gate) is in quota.md.

## Status: non-gating

A reviewer that cannot open a file or grep for callers cannot complete Phase
1b or Phase 3 on a real build, and Lane W's seat CANNOT execute tools here
(0xC0000142 under read-only; "blocked by OpenAI's safety checks" under
workspace-write), so Lane W is a non-gating second opinion: it never closes
a gate and it never sits in the reviewer fallback chain. What it
is for: an extra pair of eyes on an inlined diff or plan when the
orchestrator wants one, and the only available critic when every gating seat
is cooling - in which case the gate stays OPEN and the report says so.
Excluded work never goes to Lane W unless JC names it for the run.

A Lane W critique never satisfies Phase 1b or Phase 3. When every gating
seat is unavailable, the gate stays open and the report says which gate is
open and why.

## What it is

Working launch: `CODEX_DIRECT=1 codex exec --skip-git-repo-check -s
read-only -m "chatgpt-web/high" < spec.md` (exit 0, correct answer).
`CODEX_DIRECT=1` is mandatory (`~/bin/codex:26-32` bypasses the
router injection only then). Spec on stdin; a positional prompt with `-s
workspace-write` hung on "Reading additional input from stdin".

`codex exec` stdout ends with: the `codex` marker line, the answer, `tokens
used`, a number, then the answer AGAIN - so "everything after the marker" is
NOT the report. Use `codex exec --output-last-message <file>` (0.155
supports it); see "Reading the result" below for the exact parse if it does
not.

Every run logs a 426 websocket error (harmless, slower) and a "service tier
priority ... omitted" warning (harmless).

Bridge: `127.0.0.1:17841`, `/healthz` 200 when up; doctor command is in
"Preflight" below (the bridge's `cli.js` usage text lists `doctor` and
`--home`).

Config: the bridge patched ONLY `~/.codex/config.toml` (`openai_base_url` ->
the bridge; `[features] multi_agent = true`, `multi_agent_v2 = false`;
`[agents] max_depth = 2`; an `[[hooks.Interrupt]]` hook running its
`bun.exe`). `.codex-pro` keeps `max_depth = 1`; `.codex-biz` untouched;
`[model_providers.router]` survived.

Models `chatgpt-web/light|medium|high|extra-high|pro` = GPT-5.6 Sol on the
web; single account gojc31 (chat allowance, invisible to `bcost`); 2-6 chat
messages per Codex turn.

## When to use it

The orchestrator wants a second opinion on an inlined diff or plan; or every
gating seat is cooling and JC wants a critique meanwhile; entered only by
the orchestrator's own choice or JC saying "web lane". Never a builder,
never Lane B, never an Astra seat, never for excluded work unless JC names
it.

## Preflight

Launch only if BOTH pass:

```bash
# Lane W preflight - launch only if BOTH pass
curl -s -m 3 -o /dev/null -w "%{http_code}\n" http://127.0.0.1:17841/healthz   # expect 200
V="$(ls -d ~/.codex-chatgpt-web/versions/*/ | sort -V | tail -1)"   # newest install, the one the lanew wrapper picks
"${V}runtime/bun.exe" "${V}app/cli.js" --home ~/.codex-chatgpt-web doctor   # no "error" entries; warnings are normal
```

## Launch

Launch through `lanew <run> <name> [model] < spec.md` (Git Bash; `bin/lanew`
+ `bin/lanew.cmd`), never a raw `codex exec` call. The wrapper runs the
preflight above itself, validates the model against the allowlist, and
logs a two-phase job to `scripts/lanew_log.py`'s usage log (`check` before
launch, `record start` immediately before, `record end` immediately
after) before doing anything else. See "What lanew measures and what it
cannot" - the wrapper is a fail-closed admission gate around the launch,
not a usage-accounting or hard-budget tool.

Manual fallback ONLY if `lanew` is unavailable (ONE background Bash call,
job-object reason as in transport.md):

```bash
CODEX_DIRECT=1 timeout 1500 codex exec --skip-git-repo-check -s read-only -m "chatgpt-web/high" --output-last-message <scratch>/lanew-<name>.report.md < <scratch>/lanew-<name>.md > <scratch>/lanew-<name>.out 2>&1
```

(verify `--output-last-message` exists; adjust to the documented parse in
"What it is" if not). Effort rides in the model id: high ->
`chatgpt-web/high`, xhigh -> `chatgpt-web/extra-high`, `pro` only when JC
names it. A manual-fallback launch is NOT logged by `lanew_log.py` -
`check`/`report` will not see it, so prefer the wrapper whenever it is
installed.

## Two spec adaptations

Never the Phase 3 template as-is:

(a) **Snapshot-build critique.** `<task>` with the brief and acceptance
criteria; `<context>` that ALWAYS inlines the full diff and the full text of
every changed file it needs (never a path to fetch); no `<turn_budget>`;
`<action_safety>` = "You have no working tools on this transport. Call none.
Judge only what is inlined; mark anything you would need to open as
UNVERIFIED - never infer a PASS."; output contract = findings ranked with
confidence, and per criterion PASS / FAIL / UNVERIFIED, returned as the
final message.

(b) **Snapshot-design critique.** `<task>` with the brief and plan;
`<blueprints>` inlined; the same no-tools and UNVERIFIED rules; output = per
task SOUND / REVISE / UNVERIFIED plus findings.

Neither adaptation authorizes building or delegation.

## Reading the result

Exit status AND content. A completed critique = exit 0 AND a non-empty last
message that follows the contract. Anything else is NOT a critique and is
logged as such: nonzero exit; empty or contract-violating last message; a
last message that is a safety-block or tool-attempt error; the 1500 s
timeout. In all those cases: log, do not retry Lane W in the run, and (if a
gate was waiting) the gate stays open. Classify bridge-down ONLY by
evidence: healthz not 200, or a nonzero exit whose output names the
bridge/port - never by elapsed time (the shim can also exit fast for a
missing executable).

The web seat may markdown-escape its final message (underscores, asterisks,
backticks); compare any marker or literal string against the captured bytes
only after unescaping, or use a marker that contains none of those
characters (verified 2026-09-20: `LANEW_OK` came back as `LANEW\_OK`).

If `--output-last-message` is unavailable, use the documented fallback
parse instead of "everything after the marker" (see "What it is"): the
report is the block between the FINAL line that is exactly `codex` and the
line `tokens used`; everything from `tokens used` onward is metadata and a
repeated answer - discard it.

## Budget

One job at a time; log each job's turn count in RUN.md; stop Lane W for the
run at 25 turns total; Discussion #309 allowances UNVERIFIED for this
account.

## Failure signatures

426 websocket = slower, continue; `exited -1073741502` (0xC0000142) or
"blocked by OpenAI's safety checks" = tools do not work here, which is why
this lane is non-gating; positional-prompt hang = feed stdin; "service tier
priority ... omitted" = harmless.

## Config facts

The main-home changes above (see "What it is"); the app restores the route
when the bridge is turned off.

## What lanew measures and what it cannot

`lanew` and `scripts/lanew_log.py` are a diagnostic LOGGER with a
fail-closed admission check, NOT usage accounting and NOT a hard budget.
State this plainly to anyone reading a `report`:

- It logs jobs, assistant-message markers (transcript lines that are
  exactly `codex` - a diagnostic count, never a verified count of model
  requests or turns: a prompt or a model's own answer can itself contain
  a standalone `codex` line) and Codex-side reported tokens.
- ChatGPT chat messages and this account's remaining chat allowance are
  NOT observable from this machine at all - not estimated, not
  approximated, simply absent. The documented conversion (2-6 chat
  messages per Codex turn, above) means a job that looks fine in
  `lanew_log.py`'s terms can still have spent real chat allowance.
- The per-run ceiling (`LANEW_RUN_JOB_CEILING`, default 8) counts JOBS as
  a proxy, because turns themselves are not measurable from here - it is
  not a message-budget enforcement, and admission under the ceiling is
  not a claim that allowance remains.
- A failed or uncertain job (unknown usage from a `started` record with
  no terminal record, or any non-`ok` terminal status) latches the run:
  `check` refuses every further launch in that run until a human
  reconciles it. This is the docs' no-retry-in-the-run rule, enforced by
  the logger instead of by memory.
