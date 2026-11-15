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

**Trigger.** The session model is `gpt-6-astra` (or another proxy alias the
user names - not an OpenRouter model) and the user wants that model to lead
rather than to be delegated to. Launch: `bcode <folder> astra` for a VSCode
window, `scripts/session.ps1 gpt-6-astra` for a terminal session.

**The hard boundary - VERIFIED 2026-09-11.** A routed session can spawn any
model the proxy serves and no Claude model at all. Measured both ways from a
`gpt-6-astra` session: an Agent call on a `gpt-5.6-luna`-pinned subagent
returned clean with both aliases in `modelUsage`; an Agent call on a
`sonnet`-pinned subagent failed with `400 unknown provider for model
claude-sonnet-5`. The proxy serves no Anthropic models by design (routing a
Claude subscription login through it is banned), so in Lane D `model: "opus"`,
`"sonnet"`, `"haiku"` and the Claude-pinned agents
(`model-router:builder-low`, `model-router:builder-medium`,
`model-router:builder-high`, `model-router:builder`, `model-router:reviewer`, `model-router:reviewer-xhigh`,
`model-router:designer`) are all unreachable through the Agent tool. The one legitimate way to a Claude seat
from a routed session is headless delegation on the user's own Claude login -
Claude Code calling Claude Code, which is not a third-party tool - by stripping
the proxy env from the child (VERIFIED 2026-09-11: from a proxied env,
`env -u ANTHROPIC_BASE_URL -u ANTHROPIC_AUTH_TOKEN -u ANTHROPIC_API_KEY claude -p
--model haiku ...` answered on the Claude login with no auth warning; `haiku`
resolves to `claude-haiku-5-5` - the settings env pin and the CLI agree, specs.md). Strip all
three: leaving `ANTHROPIC_API_KEY` in place bills the API key, not the
subscription. Shape, one background Bash call per task, cwd = the project:

```bash
env -u ANTHROPIC_BASE_URL -u ANTHROPIC_AUTH_TOKEN -u ANTHROPIC_API_KEY timeout 1500 claude -p --model claude-opus-5-5 --effort <low|medium|high|xhigh> --permission-mode acceptEdits --max-turns 60 --output-format json < <scratch>/lane-d-task-N.md > <scratch>/lane-d-task-N.md.out 2>&1
```

Advisor state (advisor.md): every run logs `advisor=fable` unless the brief opts out (`advisor=off`) or asks for `advisor=opus`; on a run that logs `advisor=<model>` add `--advisor <model>`, only after that launch's state check found `CLAUDE_CODE_DISABLE_ADVISOR_TOOL` not set to a true value in the lead's environment or a settings `env` block - that preflight covers the on-form, so the child inherits no disable variable and the form adds no `-u` for it; on an `advisor=off` run add `CLAUDE_CODE_DISABLE_ADVISOR_TOOL=1` after the three `-u` flags. The designer and reviewer launches below take the off form.

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
| ORCHESTRATOR | the session itself | `gpt-6-astra` (default) or another proxy alias the user names |
| BUILDER - complex implementation | `model-router:worker` | `gpt-6.1-sol` |
| SUPPORT - contained, contract written | `model-router:support-routed` | `gpt-6.1-terra` |
| MECHANIC - trivial, fully specified | `model-router:mechanic-routed` | `gpt-6-luna` |
| ASTRA as a fresh-context seat (design gate / review fallback / hardest slice) | `model-router:astra-routed` | `gpt-6-astra` |
| CLAUDE seats (Opus 5.5 build, Fable 5.2 review) | stripped-env headless `claude -p`, see above | the user's Claude login |

**Reviewer rule (2026-11-15).** Every proxy seat is GPT, so no cross-family
proxy reviewer exists. The reviewer is the stripped-env headless Fable
command above (`--model claude-fable-5-2 --effort high`, `--effort xhigh` for
a build in an excluded category), logged `login: claude`. If the Claude
window is the problem: a fresh-context `model-router:astra-routed` review
(same family - say so in the report) plus the Hydrogen quick check on the
diff (pro-consult.md, "Gemini consult - the build-sheet seat"). Excluded
work with no Claude window -> stop and tell the user rather than ship
unreviewed.

**What does not change.** All five gates still apply, the logbook is still
`.fabstra/RUN.md`, and the excluded categories (SKILL.md, Excluded categories)
keep their rules.
