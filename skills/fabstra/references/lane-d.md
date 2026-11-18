# FabStra Lane D - Routed orchestrator

Contents: Lane D - Routed orchestrator (one section: trigger; the hard boundary; seats; reviewer rule; what does not change)

Reached from: fabstra SKILL.md - the session model is itself a proxy model and leads the run

Related:
> The crew table that names this lane is in transport.md.
> the Phase 3 spec verbatim -> specs.md
## Lane D - Routed orchestrator (the session model is a proxy model and leads)

JC (2026-09-11): "allowing astra gpt 6 ... to orchestrate other models."
Lane D: the proxy alias the session runs on plans, routes, arbitrates, and
reports, exactly as Fable does in the main flow, and spawns the routed seats
through the Agent tool. History: the 2026-09-11 lead test measured
`deepseek-v4.1-flash` 0/5 as a lead (it delegated, then never returned); the
OpenRouter seats and GLM lead left with Lane C, retired 2026-11-15
(archive/2026-11-15-lane-c/).

**Trigger.** The session model is `gpt-6.2-sol` (the default lead since JC's
2026-11-18 decision; `gpt-6.2-astra` only when the user names Astra, or
another proxy alias the user names - not an OpenRouter model) and the user
wants that model to lead rather than to be delegated to. Launch:
`scripts/session.ps1` for a terminal session on the default
(`MODEL_ROUTER_MODEL`, `gpt-6.2-sol`), `scripts/session.ps1 gpt-6.2-astra` for
an Astra lead, `bcode <folder> sol` or `bcode <folder> astra` for a VSCode
window. The lead's context variable comes from the launch scripts (Sol
500000, Astra 272000; transport.md, Model pins). The terminal launcher
(`scripts/session.ps1` / `.sh`) passes `--effort` to the interactive lead:
its effort parameter, else `MODEL_ROUTER_EFFORT`, else high; the VS Code
launchers (`bcode`) pass none, so that lead runs at the extension's own
effort setting. Every seat call the lead makes (Agent tool
`effort`, headless `--effort`) passes one, because GPT-6.2's Codex catalogue
default is low and the proxy's medium. History: the 2026-09-11 lead was `gpt-6-astra`,
the default until 2026-11-18.

**The hard boundary - VERIFIED 2026-09-11.** A routed session can spawn any
model the proxy serves and no Claude model at all. Measured both ways from a
`gpt-6-astra` session: an Agent call on a `gpt-5.6-luna`-pinned subagent
returned clean with both aliases in `modelUsage`; an Agent call on a
`sonnet`-pinned subagent failed with `400 unknown provider for model
claude-sonnet-5`. The proxy serves no Anthropic models by design (routing a
Claude subscription login through it is banned), so in Lane D `model: "opus"`,
`"sonnet"`, `"haiku"` and the Claude-pinned agents
(`model-router:builder`, `model-router:reviewer`,
`model-router:designer`) are all unreachable through the Agent tool. The one legitimate way to a Claude seat
from a routed session is headless delegation on the user's own Claude login -
Claude Code calling Claude Code, which is not a third-party tool - by stripping
the proxy env from the child (VERIFIED 2026-09-11: from a proxied env,
`env -u ANTHROPIC_BASE_URL -u ANTHROPIC_AUTH_TOKEN -u ANTHROPIC_API_KEY claude -p
--model haiku ...` answered on the Claude login with no auth warning; `haiku`
resolves to `claude-haiku-5-5` - the settings env pin and the CLI agree, specs.md). Strip all
three: leaving `ANTHROPIC_API_KEY` in place bills the API key, not the
subscription. Strip the two proxy context variables too
(`CLAUDE_CODE_MAX_CONTEXT_TOKENS`, `CLAUDE_CODE_DISABLE_1M_CONTEXT`), or the
lead's window pin (Sol 500000, Astra 272000) rides into the Claude child;
the credits-pool route keeps its own deliberate
`CLAUDE_CODE_DISABLE_1M_CONTEXT=1` (transport.md, "Claude on credits seat
(pool)") but drops the lead's pin: from a Lane D lead, that section's command
replaces its leading `CLAUDE_CODE_DISABLE_1M_CONTEXT=1` (after the `KEY=`
statement) with
`env -u CLAUDE_CODE_MAX_CONTEXT_TOKENS CLAUDE_CODE_DISABLE_1M_CONTEXT=1`.
Shape, one background Bash call per task, cwd = the project:

```bash
env -u ANTHROPIC_BASE_URL -u ANTHROPIC_AUTH_TOKEN -u ANTHROPIC_API_KEY -u CLAUDE_CODE_MAX_CONTEXT_TOKENS -u CLAUDE_CODE_DISABLE_1M_CONTEXT timeout 1500 claude -p --model claude-opus-5-5 --effort <low|medium|high|xhigh> --permission-mode acceptEdits --max-turns 60 --output-format json < <scratch>/lane-d-task-N.md > <scratch>/lane-d-task-N.md.out 2>&1
```

Advisor state (advisor.md): every run logs `advisor=fable` unless the brief opts out (`advisor=off`) or asks for `advisor=opus`; on a run that logs `advisor=<model>` add `--advisor <model>`, only after that launch's state check found `CLAUDE_CODE_DISABLE_ADVISOR_TOOL` not set to a true value in the lead's environment or a settings `env` block - that preflight covers the on-form, so the child inherits no disable variable and the form adds no `-u` for it; on an `advisor=off` run add `CLAUDE_CODE_DISABLE_ADVISOR_TOOL=1` after the five `-u` flags. The designer and reviewer launches below take the off form.

No `--bare` here: on Claude Code 2.1.280 bare mode disables the subscription
login and the child answers 'Not logged in' (verified 2026-09-23); the child
therefore loads CLAUDE.md, which is fine for a Claude seat. The build effort
follows the task's tier as in phases.md, "Claude seat efforts". The designer route
uses this same command with `--model claude-opus-5-5 --effort xhigh`.

Reviewer the same way, read-only: `--model claude-fable-5-2 --effort high --permission-mode
default --allowedTools "Read,Grep,Glob,Bash"` with the Phase 3 spec verbatim, and `--effort xhigh` for a build in an excluded category
(the Lane D review seat - reviewer rule below).
Spend it knowingly - it draws on the Claude window the routed session was
chosen to protect - and log every such call as `login: claude`. Do not plan a
seat you cannot fill otherwise: if a run needs Claude seats and the Claude
window is the problem, say so instead of burning it.

**Seats.** One Agent tool call per task, `subagent_type` as named:

| Seat | Agent | Model |
|---|---|---|
| ORCHESTRATOR | the session itself | `gpt-6.2-sol` (default), `gpt-6.2-astra` when the user names Astra, or another proxy alias the user names |
| BUILDER - complex implementation | `model-router:worker` | `gpt-6.2-sol` |
| SUPPORT - contained, contract written | `model-router:support-routed` | `gpt-6.1-terra` |
| MECHANIC - trivial, fully specified | `model-router:mechanic-routed` | `gpt-6-luna` |
| ASTRA as a fresh-context seat (design gate / review fallback / hardest slice) | `model-router:astra-routed` | `gpt-6.2-astra` |
| CLAUDE seats (Opus 5.5 build, Fable 5.2 review) | stripped-env headless `claude -p`, see above | the user's Claude login |

**Routed build briefs (specs.md rules a and g).** Every build brief this
lane sends to a routed seat (`worker`, `support-routed`, `mechanic-routed`,
and `astra-routed` on the hardest slice), by Agent call or headless proxy
launch, carries this sentence verbatim in its report instructions: "Write
the report self-contained and anew for the orchestrator who reads it, with
no shorthand carried over from your reasoning, tool calls or sub-agent
messages." and ends with the check line, filled in: `What I will check:
<the acceptance cases by name, what counts as finished, and where the review
will be exhaustive - the callers, invariants and bug classes it tests
first>.` A review seat takes the Phase 3 spec verbatim, whose report contract carries
rule g.

**Context windows (known gap, D6).** Proxy context pins apply per launch
only, and an Agent-tool seat inherits the lead session's environment: under
a Sol lead (500000) the `astra-routed` seat runs with Sol's 500k window
instead of Astra's 272k, and under an Astra lead (272000) the `worker` seat
runs with Astra's 272k instead of Sol's 500k; Terra and Luna seats inherit
the lead's window instead of their 200k. A seat that needs its own window
runs as a headless proxy `claude -p` launch with that model's context
variable (transport.md, Model pins), not through the Agent tool. A
cooling or model-rejected seat hops by the hop rules (transport.md, Model
pins); where they reach a fresh Fable or the Claude builders, in this lane
those are the stripped-env launches above.

**Reviewer rule (2026-11-15).** Every proxy seat is GPT, so no cross-family
proxy reviewer exists. The reviewer is the stripped-env headless Fable
command above (`--model claude-fable-5-2 --effort high`, `--effort xhigh` for
a build in an excluded category), logged `login: claude`. Fable unavailable:
`pool/claude-fable-5-2` (a client's work: `client-<slug>/claude-fable-5-2`
with its own `client-<slug>: usable` line, haiku mapping on the same prefix)
headless on the credits pool at the same effort, with the read-only flags above
and the pool-route `env -u CLAUDE_CODE_MAX_CONTEXT_TOKENS` form (8318 is Anthropic's own API on JC's key, not the banned subscription proxy
route; plain terminal or scheduled launch and a usable pool only;
transport.md, "Claude on credits seat (pool)"). Otherwise, on a Fable limit:
the stripped-env headless `claude -p --model claude-opus-5-5` on the Claude
login (never 8317), same flags, logged `login: claude`; when the Claude window
is the problem: a fresh-context `model-router:astra-routed` review (same
family - say so in the report) plus the Hydrogen quick check on the diff
(pro-consult.md, "Gemini consult - the build-sheet seat"). Excluded work with
no Claude seat (pool dry and, on a Fable limit, no Opus; or the Claude window
is the problem) -> stop and tell the user rather than ship unreviewed;
`astra-routed` never reviews excluded work alone.

**What does not change.** All five gates still apply, the logbook is still
`.fabstra/RUN.md`, and the excluded categories (SKILL.md, Excluded categories)
keep their rules.
