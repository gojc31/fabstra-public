# FabStra quota, failure signatures, and the fast pin

Contents: Why Astra holds the critic seats; The fast pin; Astra blocked, how to read it

Reached from: fabstra SKILL.md - on any 429/400/502/stream error, and before honouring a "fast" word

Related:
> The launch commands these errors come out of are in transport.md.
> The rest of the effort rubric the fast pin belongs to is in phases.md.
> the Codex transport -> transport.md
## Why Astra holds the critic seats

Each model sits where it leads: Fable in the planner seat, Astra in the
critic and executor seats (evidence: bench/results/results.csv).

**Astra's quota: every ChatGPT login in the proxy is a separate pool.** All
logins in `~/.cli-proxy-api/codex-*.json` serve `gpt-6-astra` and
`gpt-6.1-sol`; meters are per seat, not per workspace, and the same email in
two workspaces is two pools. Never quote a percentage from memory: run
`bcost` (windows per login) or `verify-codex-logins` (pool + disabled flags)
at the start of a run. Business seats have a 5-hour and a 7-day window,
premium and Pro seats one 7-day window; the proxy cools a 429'd login down
and rotates on. $CODEX_PRO_LOGIN (Pro) also has separate GPT-5.3-Codex-Spark
windows that only `spark` draws on (verified 2026-09-06: Astra native on Pro
spawned `spark` and the child rollout ran on `gpt-5.3-codex-spark`). With
`proxy-pin both` (standing) every login rotates; `proxy-pin team` disables
only the Pro file. "Out of credits" is NOT a 429: a seat that runs dry keeps
being round-robined until the credit check disables it. The proxy
remembers a credential's last error per model, so a login that once answered
"not supported" for a model is not retried until the proxy restarts. Never
edit a `~/.cli-proxy-api/*.json` file in place to nudge it - a failed
rewrite can leave it empty; restart the proxy instead. Spend Astra on the Astra-row gates - design review and build review of excluded and architecture work - and let Sol hold the Sol row and Terra/Luna do the routed typing.

## The fast pin (last bullet of the effort rubric)

- **Standing fast window, on since 2026-09-28, no end date - JC 2026-10-03:
  stays on until JC says stop (opened by JC 2026-09-28 to spend weekly
  quota before the reset).** `.codex-pro` (gojc31 Pro) and
  `.codex-biz` ($CODEX_BIZ_LOGIN) both hold `service_tier = "fast"` for
  the whole window: no `fast` word needed, and runs do NOT end with
  `codex-fast off`. Every Codex-transport launch (Codex-side builds,
  Codex-column fixes, the Codex review fallback) goes native, round-robin
  over the two homes: `H=$(codex-fast-home); CODEX_HOME="$H" CODEX_DIRECT=1
  node "$C" task ...` (`~/bin/codex-fast-home` alternates .codex-pro /
  .codex-biz and prints the home; `codex-fast-home peek` shows the next one
  without advancing). A usage-limit error on one home -> `echo pro >
  ~/.codex-fast-skip` (or `biz`) so the picker skips it for the rest of the
  window, and relaunch; both spent -> the router launch with no prefix
  (standard tier, rotating the other logins), logged. Log `fast
  (standing window, <home>)` beside the effort in RUN.md. **Reviews move
  too (JC, 2026-09-28):** the design review and Reviewer A/B run on this
  fast native path instead of the proxy `claude -p` - recipe under
  "Standing fast window: reviews" in transport.md. Only Lane B stays on
  `claude -p` (standard tier), because Astra builds inside that session. The scheduled task
  `CodexFastOff-2026-10-04` is disabled (2026-10-03); turning the window off
  is a manual `codex-fast off pro` + `off biz` when JC says so - then this
  bullet is void: run `codex-fast status pro` / `status biz`, turn off
  anything still on, `rm -f ~/.codex-fast-rr ~/.codex-fast-skip`, and fall
  back to the rules below.

- **Fast pin - "astra fast", `/fabstra ... fast`.** The word `fast` in the
  invocation or brief turns on Codex Fast mode (`service_tier = "fast"`)
  for this run's launches on the `.codex-pro` home (gojc31 Pro; JC's
  standing choice since 2026-09-14, after the Business seat ran out of
  credits): `codex-fast on` before the first launch,
  `codex-fast off` after the run's last native job ends (fix rounds
  included), `fast` written beside the effort in RUN.md and in the usage-log
  notes. Bare targets `.codex-pro` by default; pass `biz` to `codex-fast`
  only when JC asks for the Business seat by name. The launch then carries
  the `CODEX_HOME="${CODEX_PRO_HOME:-$HOME/.codex-pro}" CODEX_DIRECT=1` prefix (or uses
  the `codex-pro` shim) - the config switch alone does nothing if the job
  runs through the router. Fast is a service tier, not an effort: Astra
  streams about 2x faster, Sol / Terra / Luna 1.5x (GPT-6 Sol; `gpt-6.1-sol` does not advertise the priority tier as of 2026-09-30 and runs at standard speed), every request on that
  login's pool costs 2.5x, and children Astra spawns inherit it (`spark`
  has no fast tier and stays standard, and is Pro-home only - a fast run
  on `.codex-pro` can use `spark` directly). It reaches ONLY a
  native home - verified 2026-09-06 on Pro and 2026-09-10 on `.codex-biz`
  (`x-codex-routing-hint: model=gpt-6-astra;tier=priority` on the websocket
  handshake): the `claude -p` transport (design review, Reviewer A/B, Lane
  B) and anything through the proxy ignore it - so a fast run still has
  standard-speed reviews, and the report says so. A `-c service_tier=fast`
  flag on the command line is NOT enough (verified 2026-09-10: the turn
  showed `service_tier: None` and no handshake hint); the config switch is
  the only door. Without the word, standard tier; a slow run is never a
  reason to turn it on yourself. The fast pin and the Pro-home surfaces
  (surfaces.md) are the two reasons to launch Astra on a native home;
  otherwise Astra rotates over every login in the proxy.

## Astra blocked, how to read it (Phase 3)

**Astra blocked, how to read it:** quota errors are 429 "All credentials
for model gpt-6-astra are cooling down" (every login spent or cooling) or
"usage_limit_reached" from the proxy, or a Codex job that fails within
seconds with the same text. A 400 "not supported when using Codex with a
ChatGPT account" means that login has lost or not yet gained the model:
probe the other logins directly, restart the proxy so it re-probes, and if
only the proxy binary is old upgrade it; do not fall back. A 502 from the
proxy on `gpt-6-astra` is usually a proxy binary that predates the model -
check `cli-proxy-api.exe --version` (7.3.12 is the verified version for
`gpt-6-astra`, `gpt-6-sol` and `gpt-6-luna`; 7.2.157 lacked Sol and Luna)
before concluding that; a current proxy can also
relay an upstream 502, which a retry a minute later tells apart. `gpt-6.1-sol` verified served 2026-09-30 (proxy 7.3.12; native Codex needs CLI 0.159.2+). A `result`
that reads "API Error: stream error: stream disconnected before completion"
after a few turns is an upstream stream drop, not quota (seen 2026-09-05 at
turn 9 of an Astra review with the account at 7% used): check the usage
endpoint first (`allowed: true`, `limit_reached: false` = not quota), then
relaunch the same spec once (`--fresh` on the Codex transport; the proxy command as-is,
it has no such flag). Sol's
quota errors read the same with `gpt-6.1-sol` and cover every login.

Lane W (ChatGPT-web second opinion) was retired 2026-09-27; there is no non-gating fallback seat.
Codex-only breakages: "Codex CLI is not installed" means the PATH shims are
missing; an auth error on the router path is the proxy key or a proxy
credential (`MODEL_ROUTER_KEY` vs config.yaml, then `expired`/`disabled` in
the `~/.cli-proxy-api/codex-*.json` files) before it is `codex login`, which
only matters for `CODEX_DIRECT=1`; a job whose pid
is dead while its record still says running is most often a mid-turn
message that killed a foreground launch - read the job log's last lines
first (a crash or timeout looks different), then relaunch it through the
background call. These are diagnoses to check, not verdicts. Always say
which reviewer and transport ran and why.

Your own pass over the build is never the only review; never silently skip
review. Effort comes from the effort rubric; never drop below its floor to
save time.

