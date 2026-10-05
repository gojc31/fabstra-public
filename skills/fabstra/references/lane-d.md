# FabStra Lane D - Routed orchestrator

Contents: Lane D - Routed orchestrator (one section: trigger; the hard boundary; seats; reviewer rule; deepseek-v4.1-flash is not an orchestrator; what does not change)

Reached from: fabstra SKILL.md - the session model is itself a proxy model and leads the run

Related:
> The crew table that names this lane is in transport.md.
> the Phase 3 spec verbatim -> specs.md
> Lane C already accepted a routed session as the orchestrator -> lane-c.md
## Lane D - Routed orchestrator (the session model is a proxy model and leads)

JC (2026-09-11): "allowing astra gpt 6 and deepseek v4.1 to orchestrate other
models." Lane C already accepted a routed session as the orchestrator, but only
as the budget crew. Lane D is the general case: whatever proxy alias the session
runs on plans, routes, arbitrates, and reports, exactly as Fable does in the main
flow, and spawns the routed seats through the Agent tool.

**Trigger.** The session model is a proxy alias (`gpt-6-astra`,
`glm-5.3-flash`, `gpt-6.1-sol`, ... - not `deepseek-v4.1-flash`) AND the user wants
that model to lead rather than to be delegated to. Launch: `bcode <folder>
astra` / `bcode <folder> glm` for a VSCode window, `scripts/session.ps1
gpt-6-astra` for a terminal session, or `budget 41` for the DeepSeek alias.

**The hard boundary - VERIFIED 2026-09-11.** A routed session can spawn any
model the PROXY serves and no Claude model at all. Measured both ways from a
`gpt-6-astra` session: an Agent call on a `gpt-5.6-luna`-pinned subagent
returned clean with both aliases in `modelUsage`; an Agent call on a
`sonnet`-pinned subagent failed with `400 unknown provider for model
claude-sonnet-5`. The proxy serves no Anthropic models by design (routing a
Claude subscription login through it is banned), so in Lane D `model: "opus"`,
`"sonnet"`, `"haiku"`, `model-router:reviewer` are all
unreachable THROUGH THE AGENT TOOL. The one legitimate way to a Claude seat
from a routed session is headless delegation on the user's own Claude login -
Claude Code calling Claude Code, which is not a third-party tool - by stripping
the proxy env from the child (VERIFIED 2026-09-11: from a proxied env,
`env -u ANTHROPIC_BASE_URL -u ANTHROPIC_AUTH_TOKEN -u ANTHROPIC_API_KEY claude -p
--model haiku ...` answered on `claude-haiku-4-5` with no auth warning). Strip all
three: leaving `ANTHROPIC_API_KEY` in place bills the API key, not the
subscription. Shape, one background Bash call per task, cwd = the project:

```bash
env -u ANTHROPIC_BASE_URL -u ANTHROPIC_AUTH_TOKEN -u ANTHROPIC_API_KEY timeout 1500 claude -p --model opus|sonnet|haiku --permission-mode acceptEdits --max-turns 60 --output-format json < <scratch>/lane-d-task-N.md > <scratch>/lane-d-task-N.md.out 2>&1
```

No `--bare` here: on Claude Code 2.1.280 bare mode disables the subscription
login and the child answers 'Not logged in' (verified 2026-09-23); the child
therefore loads CLAUDE.md, which is fine for a Claude seat. The designer route
uses this same command with `--model claude-opus-5-5 --effort xhigh`.

Reviewer the same way, read-only: `--model claude-fable-5-1 --permission-mode
default --allowedTools "Read,Grep,Glob,Bash"` with the Phase 3 spec verbatim.
Spend it knowingly - it draws on the Claude window the routed session was
chosen to protect - and log every such call as `login: claude`. Do not plan a
seat you cannot fill otherwise: if a run needs Claude seats and the Claude
window is the problem, say so instead of burning it.

**Seats.** One Agent tool call per task, `subagent_type` as named:

| Seat | Agent | Model |
|---|---|---|
| ORCHESTRATOR | the session itself | `gpt-6-astra` (default) or `glm-5.3-flash`; never `deepseek-v4.1-flash` |
| BUILDER - complex implementation | `model-router:worker` | `gpt-6.1-sol` |
| SUPPORT - contained, contract written | `model-router:support-routed` | `gpt-5.6-terra` |
| MECHANIC - trivial, fully specified | `model-router:mechanic-routed` | `gpt-6-luna` |
| BUILDER (OpenRouter default) - all coding on the cheap lane; empty-200 retry, see Lane C | `model-router:deepseek41-routed` | `deepseek-v4.1-flash` |
| BUILDER (cheapest fallback) - three empty-200s on one task, or cost is the constraint | `model-router:builder-budget` | `glm-5.3-flash` |
| REVIEWER - fresh context, read-only, GPT or GLM builder | `model-router:reviewer-routed` | `deepseek-v4-flash` |
| REVIEWER - fresh context, read-only, DeepSeek builder | `model-router:reviewer-glm` | `glm-5.3-flash` |
| ASTRA as a seat (design gate / review / hardest slice) when GLM or DeepSeek leads | `model-router:astra-routed` | `gpt-6-astra` |
| CLAUDE seats (Opus / Sonnet / Haiku build, Fable review) | stripped-env headless `claude -p`, see below | the user's Claude login |

**Reviewer rule, unchanged in spirit:** the reviewer is never the orchestrator's
own alias and never the builder's family. Pick it from the BUILDER:
`reviewer-routed` (`deepseek-v4-flash`) for a GPT or GLM builder;
`reviewer-glm` (`glm-5.3-flash`) whenever the builder is DeepSeek, which is
now the OpenRouter default (`deepseek41-routed`). Two collisions and their
outs: a GLM orchestrator with a DeepSeek builder puts `reviewer-glm` on the
orchestrator's own alias - accept it as Lane C does (fresh context,
cross-family to the builder wins) and say so, or lead on `gpt-6-astra`
instead, which clears it; a DeepSeek orchestrator with a DeepSeek builder
leaves `reviewer-glm` clean on both counts. Log any swap. A run that reviewed
on the builder's own family is a same-family review - say so in the report.

**`deepseek-v4.1-flash` is NOT an orchestrator - measured 2026-09-11.** Ten
interleaved runs on the same proxy, same minute, same task (delegate a file
write to a `gpt-5.6-luna` subagent, verify with Bash, report in a fixed 3-line
format, hard 120 s cap): `glm-5.3-flash` 5/5 PASS in 20-35 s, 3 turns each;
`deepseek-v4.1-flash` 0/5 - every run delegated correctly (the file appeared)
and then never returned, killed at 120 s. That is the worst failure mode a lead
seat can have: the plan stalls silently. That is why the 2026-09-12 change
seats it as the DEFAULT BUILDER and as a reviewer
(`model-router:deepseek41-routed`, empty-200 retry) and never as the
session model; `bcode <folder> 41` exists for that lane but a fabstra run on it
must stop at the Session check and say so. Lead seats: `gpt-6-astra` (quality)
or `glm-5.3-flash` (cost; Lane C's default).

**What does not change.** All five gates still apply, the logbook is still
`.fabstra/RUN.md`, and the excluded categories (money, auth, PII or
de-identification, permissions, data migration, concurrency, a client-facing
release) still never take an OpenRouter seat - on this lane that means
`deepseek41-routed`, `builder-budget`, `reviewer-glm` and `reviewer-routed` are
all out for that work, leaving the GPT seats; if the review seat cannot be filled without OpenRouter, stop and tell the
user rather than shipping unreviewed.
