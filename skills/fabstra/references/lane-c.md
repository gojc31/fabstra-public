# FabStra Lane C - Budget crew

Contents: Lane C - Budget crew (one section: seats; empty-200 retry; reviewer-alias overlap; commands; bench; rules; failure signatures; cost; logbook and report)

Reached from: fabstra SKILL.md - an explicit budget-crew ask, or a session already routed to OpenRouter

Related:
> The pairing rule that routes a seat here is in phases.md.
> Phase 1b's spec -> specs.md
> Phase 3 XML review spec -> specs.md
> (0/5, see Lane D) -> lane-d.md
## Lane C - Budget crew (OpenRouter, cheap models only)

JC (2026-09-10) added an OpenRouter pay-per-use key to the local proxy so a
build is never blocked when the Claude limit AND every ChatGPT login are
spent. Trigger for the FULL crew, either of: (a) the user says `budget`,
`cheap crew`, `openrouter`, or `deepseek` in the ask - pins the lane
regardless of quota; (b) the session itself already runs on a routed
OpenRouter model (`scripts/session.ps1 glm-5.3-flash` - the `budget` shim's
default - or any other lane alias: `deepseek-v4-pro`
for `pro`) - the Session check (phases.md) accepts that session model for this
lane only, logged as such; that is what "the Claude limit is the problem"
looks like. Astra AND Sol both cooling on a Fable session does NOT by
itself pull in the full crew: the Claude builders keep building, and only
the review seat and the Phase 1b design gate change to Lane C (Reviewer A
and the design gate) - see the pairing rule (phases.md) and "Astra blocked,
how to read it" (quota.md). Excluded categories (money, auth, PII or de-identification,
permissions, data migration, concurrency, a client-facing release) never
take a Lane C seat, not even for the review or the design gate: with Astra
and Sol both cooling, that review goes to the fresh Fable (Reviewer C)
instead, logged as "same-family review, GPT seats cooling, Lane C
excluded", so nothing sensitive leaves the Claude login. `pro` anywhere in
the ask moves the orchestrator to `deepseek-v4-pro`. Reviewer A stays
`glm-5.3-flash` (cross-family to the DeepSeek builder either way, and on a
`pro` run it is no longer the orchestrator's alias, so both reviewer
properties hold); Reviewer B moves off `deepseek-v4-pro` to
`deepseek-v4-flash` so no reviewer sits on the orchestrator's own alias; and
the design gate moves to `glm-5.3-flash`, since `deepseek-v4-flash` would
otherwise be checking a DeepSeek-led plan. A full-lane
request (trigger (a) or (b)) on excluded work: money, auth, PII or
de-identification, permissions, data migration, concurrency, a
client-facing release - refuse with one line ("budget lane excluded for
this kind of work; wait for the Claude or ChatGPT window") and stop.
Gate it with `jev excluded "<prompt>"` (exit 3 = excluded, including the
0.4-0.6 conservative fallback) before any prompt leaves for OpenRouter; the
`budget` shim runs the same check as a UserPromptSubmit hook
(`assets/budget-settings.json` -> `scripts/jev-gate.py`), so a session opened
through it refuses excluded prompts on its own.

**Seats.**

| Seat | Model | Why |
|---|---|---|
| ORCHESTRATOR | `glm-5.3-flash` (`deepseek-v4-pro` for `pro`) | the `budget` shim's default; a session is token-heavy and this is the cheapest per turn. NEVER `deepseek-v4.1-flash`, which hangs as a lead (0/5, see Lane D) |
| DESIGN GATE (multi-file only) | `deepseek-v4-flash` (`glm-5.3-flash` on a `pro` run) | cross-family check on a GLM-orchestrated plan |
| BUILDER / WORKER - all coding | `deepseek-v4.1-flash` | JC (2026-09-12): the build seat is v4.1. Benched best of the four - fastest (23-122 s), 5/5 recall x3, 0 FP, contract ok twice. It costs ~3x `glm-5.3-flash` and fails ~1 call in 5 as an empty HTTP 200, so the retry rule below is mandatory, not optional |
| BUILDER fallback | `glm-5.3-flash` | after three empty-200s on one task, or when the user asks for the cheapest build; log the fallback |
| MECHANIC / bulk | `deepseek-v4-flash` | cheapest raw tokens; renames, scaffolds, docs, triage scans. Same family as the builder, which is fine - it is not a review seat |
| REVIEWER A (LANE C) | `glm-5.3-flash`, fresh context | cross-family to the DeepSeek builder; 5/5 recall x3, 0 FP. Its contract drifts to partial on two runs in three, so the review spec must restate the required report format verbatim |
| REVIEWER B (LANE C, multi-file only) | `deepseek-v4-pro`, fresh context (`deepseek-v4-flash` on a `pro` run) | the careful second seat; on the default configuration it is the builder's family, so the report says the second review was same-family and Reviewer A carries the cross-family check |

Hard rule: Reviewer A (Lane C) must not be the builder's family. It is now
GLM because the builder is DeepSeek; if a run ever puts the same family in
both seats, the report says the review was same-family. With only two
families on this lane some alias reuse is forced - Reviewer B sits on the
builder's family on multi-file work, `deepseek-v4-flash` covers both the
design gate and the mechanic, and Reviewer A shares the default
orchestrator's alias (see "the reviewer-alias overlap" below) - but the
load-bearing property holds in every configuration: Reviewer A is never the
builder's family. The design gate and MECHANIC run the `deepseek-v4-flash`
shape (design gate read-only at effort high on Phase 1b's spec unchanged;
mechanic `acceptEdits` at effort medium, `--max-turns 30`). The BUILDER runs
Phase 2's blueprint spec at effort high with the required report format
restated verbatim, and every one of its calls goes through the empty-200
retry below. REVIEWER A (LANE C) runs at effort high, fresh context, on the
existing Phase 3 XML review spec, with the report format restated verbatim
because GLM drifts to partial format on two runs in three. REVIEWER B (LANE
C) runs at effort high, fresh context. Single-file work: builder + Reviewer
A (Lane C) only.

Review scope limit: a Lane C review seat reads about 40 KB of findings and
diff inside its 30 turns, not more. Hand it a larger scope and it spends
every turn reading and writes nothing: on 2026-09-26 four attempts (glm and
deepseek-v4-pro, full and halved scopes of ~100 KB) all ended at
`error_max_turns` with no report, while a fresh Fable (Reviewer C) reviewed
the same scope in one pass. So split a review above ~40 KB into slices of
that size, one seat call per slice, and make every Lane C review spec say
"write the findings file by your 8th call and overwrite it as you go". When
a slice still returns no report, send that slice to Reviewer C and log it;
do not relaunch the same seat on it.

**Empty-200 retry - MANDATORY on every builder call (JC, 2026-09-12).**
`deepseek-v4.1-flash` holds the build seat because it benches best, but its
OpenRouter providers (Io Net, Novita, Parasail, measured 2026-09-11) sit on a
contended shared pool and about 1 call in 5 comes back as an empty HTTP 200 -
a `.out` file whose `result` is empty or missing while the exit code is 0. So a
builder launch is not done when the command returns; it is done when the output
is non-empty. After every builder or fixer call:

1. Read the `.out` file. If `result` is empty, whitespace, or absent, that is
   the empty-200 signature - not a build with nothing to say.
2. Re-run the IDENTICAL command. Up to two retries, three attempts total.
3. Three empty attempts: rerun that task on `glm-5.3-flash` with the same spec
   and log `builder fallback: v4.1 empty-200 x3 -> glm-5.3-flash`.

Never report a task complete on an empty result, and never swap the builder
without that log line. `deepseek-v4.1-flash` is a BUILDER and a REVIEWER seat
only - never the orchestrator and never the session model (0/5 as a lead, see
Lane D).

**The reviewer-alias overlap, accepted deliberately.** This lane has two
families, DeepSeek and GLM. With a DeepSeek builder the only cross-family
reviewer is `glm-5.3-flash`, which is also the default orchestrator's alias, so
the two reviewer properties cannot both hold on the default configuration.
Cross-family to the builder wins: Reviewer A runs in a fresh context with none
of the orchestrator's session state, which makes the shared alias far weaker
than a shared family would be. Say so in the report ("Reviewer A shares the
orchestrator's alias, fresh context, cross-family to the builder"). A `pro`
run, or a Lane D run led by `gpt-6-astra`, clears the overlap entirely.

**Commands.** Every call is a proxy `claude -p` inside its own
`run_in_background` Bash call, the Astra/Sol shape (`--output-format json`
with the spec fed on stdin), key pulled the same way:
`KEY=$(python -c "import re;t=open(r'${CLIPROXY_DIR:-~/cli-proxy-api}/config.yaml').read();print(re.search(r'api-keys:\s*\n\s*-\s*\"?([^\"\n]+)\"?',t).group(1).strip())")`.
Builder (mechanic swaps model/effort/turns):

```bash
ANTHROPIC_BASE_URL=http://127.0.0.1:8317 ANTHROPIC_AUTH_TOKEN="$KEY" timeout 1500 claude -p --model deepseek-v4.1-flash --effort high --bare --permission-mode acceptEdits --max-turns 60 --output-format json < <scratch>/budget-build-<name>.md > <scratch>/budget-build-<name>.md.out 2>&1
```

Mechanic swaps in `--model deepseek-v4-flash --effort medium --max-turns 30`,
same `acceptEdits` shape. Reviewer A (Lane C) (Reviewer B (Lane C) swaps
`--model deepseek-v4-pro`, or `--model deepseek-v4-flash` on the one run
where the orchestrator is itself `deepseek-v4-pro`):

```bash
ANTHROPIC_BASE_URL=http://127.0.0.1:8317 ANTHROPIC_AUTH_TOKEN="$KEY" timeout 1500 claude -p --model glm-5.3-flash --effort high --bare --max-turns 30 --permission-mode default --allowedTools "Read,Grep,Glob,Bash" --output-format json < <scratch>/budget-review-<name>.md > <scratch>/budget-review-<name>.md.out 2>&1
```

Design gate (multi-file only, before any builder launch) reuses the
reviewer command's read-only shape with `--model deepseek-v4-flash`
(`glm-5.3-flash` on a `pro` run), spec file `budget-design-<name>.md`. No `Agent` tool, no delegation, no Codex
transport, no `ANTHROPIC_DEFAULT_*_MODEL` variable - this lane spawns
nothing.

**Bench** (5-bug fixture, `bench/run.sh proxy <alias> high 3`, 2026-09-11;
re-read `bench/results/results.csv` before quoting a number - more runs land
as the week continues):

| Model | Runs (s) | Turns | Recall | False positives | Contract |
|---|---|---|---|---|---|
| deepseek-v4.1-flash | 122, 25, 23 | 10, 8, 6 | 5/5 x3 | 0, 0, 0 | ok, partial, ok |
| glm-5.3-flash | 53, 145, 52 | 5, 6, 6 | 5/5 x3 | 0, 0, 0 | partial, ok, partial |
| deepseek-v4-flash | 121, 149, 167 | 6, 12, 18 | 5/5 x3 | 0, 2, 0 | partial, ok, partial |
| deepseek-v4-pro | 340, 173, 391 | 18, 15, 16 | 5/5 x3 | 0, 0, 0 | ok, partial, partial |

For comparison on the same fixture: Sol xhigh 112-369 s (ten proxy runs,
two hung outliers excluded), Astra xhigh 234-262 s. DeepSeek V4.1 Flash has
the best bench of the four - 0 FP, contract ok twice, fastest - which is why
JC put it in the BUILDER seat on 2026-09-12; its OpenRouter providers are an
unreliable shared pool, so the empty-200 retry above is the price of that
seat. GLM 5.3 Flash is cheap with 5/5 recall and 0 FP, now the orchestrator,
Reviewer A, and the builder fallback; its contract drifts to partial on two
of three runs, hence the report-format rule above. DeepSeek V4 Flash finds
the same bugs and is the most reliable of the four (0/10 failures measured
2026-09-11), hence the design gate and the mechanic - but it has 2 false
positives on one run in three and is now the builder's family, so it no
longer holds a Lane C review seat. DeepSeek V4 Pro is most careful and
slowest, hence Reviewer B (Lane C), not the builder.

**Rules.** Fix rounds: max two, then ESCALATED to the user, same ceiling as
Lane B.

Fix rounds in this lane are a new BUILDER `claude -p` launch on
`deepseek-v4.1-flash` (the builder command above, empty-200 retry included),
carrying the finding(s) verbatim plus the affected file list - never the
mechanic alias, and never the reviewer's; the re-review goes to Reviewer A
(Lane C, `glm-5.3-flash` as usual), which stays cross-family to the DeepSeek
fixer. Two rounds, then
ESCALATED to the user, unchanged.

Ship gate: the ledger is all FIXED (confirmed by re-review), WITHDRAWN by the lead with a logged reason, or ESCALATED; reviewers advise, the lead rules. Privacy: prompts leave the machine to
OpenRouter, which picks a host per call from the providers this account's
privacy filter allows - `budget cost` names the one it routed to just now;
Airlock rules are unchanged, and never edit OpenRouter's privacy settings
from a run. A privacy 404/503 on an alias means that model's CURRENT
endpoints are non-compliant, not that the model is banned forever - re-probe
before quoting an exclusion, because provider coverage changes (as it did
for `deepseek-v4.1-flash` between 2026-09-10 and 2026-09-11) - and never
loosen the account settings to make one pass. Non-flash `glm-5.3`, any
`muse-spark-*-contributor` tier, and the never-configured `fable-or` /
`astra-or` are not available in this lane - a spec or report naming one is a
mistake to fix, not a lane to widen.

**Failure signatures.** An OpenRouter model can return HTTP 200 with
`content: []`, `model: ""`, and zero `usage` - that is an upstream 429 on a
contended shared provider pool, not an empty answer. Retry once
immediately, then once after 30 s; if it still comes back empty, switch to
another alias and log the swap - never treat an empty content array as "the
model had nothing to say" (the standing remedy outside a run: adding a
provider key at openrouter.ai/settings/integrations moves that model off
the shared pool). Proxy 503 `auth_unavailable ... 404 ... data policy` =
alias excluded by privacy settings - swap alias, never loosen the settings.
OpenRouter 402 = key out of credits - tell the user to top up at
openrouter.ai/credits and stop. OpenRouter 429 = provider rate limit, the
same cause and cure as the silent empty-response signature above - retry
immediately, then again after 30 s, then swap alias and log the swap.

**Cost.** Prices move per call - OpenRouter picks the endpoint and this
account's privacy filter narrows the pool further, so no stored number is
reliable, including a per-M anchor. Run `budget cost` for what the account
is actually routed to right now (`budget cost list` shows the unfiltered
list price); a call's true cost is in its `usage.cost` field when the
request sets `usage.include` - never quote a stored price. The only stable
fact is the ordering: `glm-5.3-flash` and `deepseek-v4-flash` are the cheap
tier, `deepseek-v4.1-flash` roughly 3x that, `deepseek-v4-pro` roughly
15-20x the cheap tier. Since 2026-09-12 the BUILDER seat sits on the 3x tier
by JC's choice - the lane is still an order of magnitude under the Claude and
Codex seats, and `glm-5.3-flash` remains one flag away when cost is the
constraint.

**Logbook and report.** Log `lane: budget`, each call's alias and effort,
and the real cost from that call's `usage.cost` field (set `usage.include`
on the request; run `budget cost` for current per-model rates) - never a
stored price; one `usage-log.csv` row per build/review call. The report names the lane, every alias used, the cost recorded
this way, and which reviewer seats ran and why any were skipped.


