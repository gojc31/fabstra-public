# Use cases - what to type, what happens, what you get back

Ten worked briefs. Each one names the session model it expects, the exact
thing to type, which seats fire, and what lands in your repo. Effort words
(`xhigh`, `high`, `medium`) anywhere in a brief pin the Astra and Sol effort
for that run; leave them out and the skill's effort rubric picks.

Legend: **Fable** = Claude Fable 5.2 (orchestrates and never codes when it is
your session model; also the fresh-context reviewer). **Opus** = Claude Opus
5.5 (orchestrates or leads as the session model; every Claude build seat, at
low / medium / high / xhigh by tier). **Sonnet / Haiku** = Claude Sonnet 5.5 /
Haiku 5.5 (lead as the session model; Sonnet max builds only on a pin).
**Astra** = GPT-6 Astra (the gate seat for excluded-category, architecture and
data-model plans; runs the Codex side). **Sol** = GPT-6.1 Sol (the gate seat
for every other real build; the hard-tier Codex agent). **Terra / Luna** =
GPT-6.1 Terra / GPT-6 Luna, the contract and mechanical Codex agents. Claude
seats run via the Agent tool on your normal Claude login.

---

## 1. A real feature, start to finish (`/model-router:fabstra`)

**Session model:** Fable 5.2, or Opus 5.5 (auth is an excluded category, so
Opus orchestrates this one too).

```
/model-router:fabstra Add a "forgot password" flow to the Next.js app: request page,
signed one-hour token emailed via Resend, reset page, and a rate limit of 3 requests
per email per hour. Supabase auth is already wired. Tests for the token and the limit.
```

What happens: Fable reads the repo and writes a plan with one spec per task
(outcome, interfaces and file ownership, test names, acceptance). Auth is an
excluded category, so Astra holds the gate seat at xhigh and critiques the
plan and specs before anything is built; Fable rules on every finding. Tasks
tagged Claude go to the Opus 5.5 build seats (auth work takes the
excluded-category floor: `builder` at xhigh for hard tasks, `builder-high`
for the rest); tasks tagged Codex go to Astra's thread, which spawns Sol
(hard), Terra (contract), or Luna / Spark (mechanical). Astra adversarially
reviews the Claude-built parts, with a fresh Fable context
(`reviewer-xhigh`) in parallel on this xhigh row; a fresh Fable context
reviews the Codex-built parts. Fable arbitrates every finding and logs why.

You get: the code, the tests run green in a smoke gate, `.fabstra/RUN.md` in
the project with the plan, every finding, and every decision, and a short
report that separates verified from assumed, with anything that needs you
asked in chat.

## 2. Let Astra design and build alone (Lane B, "astra solo")

**Session model:** Fable 5.2 (any Claude session runs Lane B the same way).

```
/model-router:fabstra astra solo: turn scripts/export.py into a proper CLI with
subcommands (csv, json, sheets), a --since date filter, and a --dry-run flag. Keep
the current behaviour as the default `csv` subcommand. xhigh
```

What happens: instead of per-task specs, Fable writes a brief. Astra runs through
the proxy as a single long session and designs plus builds end to end. Sol at
xhigh and a fresh Fable context both review, in parallel and independently,
and the lead rules on every finding before it ships. Use it when the design space is wide and you'd rather one strong model
own the whole shape than split it into tasks.

## 3. Fan out several Astras on disjoint slices

**Session model:** Fable 5.2.

```
/model-router:fabstra spawn 3 astra subagents: migrate the three legacy jobs in
jobs/ (nightly-report, invoice-sync, lead-scoring) from cron shell scripts to the
new Worker base class in lib/worker.py. One job per Astra, no shared files.
```

What happens: Lane B fan-out. Fable splits the work into disjoint slices, runs
up to three solo Astras in flight, and each slice gets the same Sol plus Fable
double review. Best for repetitive-but-not-mechanical migrations where the
slices don't touch the same files.

## 4. You are on Sonnet or Haiku, or on Opus below the threshold (Lead mode)

**Session model:** Sonnet 5.5 or Haiku 5.5 (Opus 5.5 leads a plan with fewer
than 2 independent tasks and no excluded category; this one is money, so
Opus orchestrates it as in case 1).

```
/model-router:fabstra the checkout webhook handler double-charges on Stripe
retries. Find the real cause and fix it - I have already tried adding an
idempotency key on the client and it still happens.
```

What happens: the skill runs Lead mode and its five gates (scope, evidence,
adversarial reasoning, verify, calibrated report). Your session drafts a
plan; the gate seat - Astra here, because money is an excluded category -
reads it plus the repo read-only and tries to break it, and your session
rules on every finding: accepted by revising the plan, rejected with one
logged line. Your session builds the authoritative plan (itself, or through
the Opus 5.5 build seats by tier), launches any Codex side work, runs the
smoke gate, and the gate seat reviews the finished build, with a fresh Fable
in parallel on this xhigh row. On a debugging brief like this the plan gate
usually kills the first theory before you spend an hour on it.

The `fable-mode` skill is a retired alias for this; run `/model-router:fabstra`
instead.

## 5. Pin Sol for the gate and review seats (name Sol in the brief)

**Session model:** any Claude session (Fable 5.2 orchestrates; Opus 5.5,
Sonnet 5.5 and Haiku 5.5 as the session switch says).

```
/model-router:fabstra sol: Replace the hand-rolled retry loop in lib/http.py with
tenacity, same backoff (0.5s, x2, max 5 tries), and update the three call sites.
```

What happens: naming Sol pins GPT-6.1 Sol for every gate and review seat in
the run instead of Astra; the plan gate and the reviews run the same
commands with `--model gpt-6.1-sol`, at the rubric's effort (high for a
refactor like this) or the effort word in the brief. A refactor with a clear
before/after takes the Sol row without being named; the pin matters when the
run would otherwise reach an Astra row. Claude built -> Sol reviews; Sol
built -> a fresh Fable reviews; Sol never reviews Sol. Reach for it when you
want to keep Astra's quota for something else.

`/model-router:fabsol` is a retired alias for this pin; run
`/model-router:fabstra` and name Sol in the brief instead.

## 6. Plan review only - no build

**Session model:** any.

```
astra review: here is my plan for moving sessions from Redis to Postgres
(docs/plan-sessions.md). Break it before I start.
```

What happens: Astra reads the plan and the repo with read-only tools and
returns findings ranked by severity with file:line evidence. Nothing is
written. Good the night before a migration.

## 7. Headless one-shot on a GPT model (no orchestration)

**Any terminal.** Requires the proxy running.

```bash
scripts/worker.sh "Write docstrings for every public function in lib/parsers.py. \
Do not change behaviour." gpt-6.1-sol medium
```

What happens: one `claude -p` run on Sol through the proxy with edits allowed
and a 20-turn cap. This is the raw building block the flows use; call it
directly for chores you would not bother orchestrating.

## 8. A whole Claude Code session on a routed model

**Any terminal or VSCode.** Requires the proxy running.

```bash
scripts/session.sh gpt-6.1-sol        # terminal, on Sol
scripts/vscode.sh path/to/project     # separate VSCode profile, opened on that folder
```

What happens: `session.sh` starts Claude Code with `--model gpt-6.1-sol` (no
argument: `MODEL_ROUTER_MODEL`, else `gpt-5.6-sol`), on your ChatGPT login
via the proxy. `vscode.sh` (Windows: `scripts\vscode.ps1`) takes a folder, not
a model (no argument: the current folder): it sets `ANTHROPIC_BASE_URL` from
`MODEL_ROUTER_URL` and `ANTHROPIC_AUTH_TOKEN` from `MODEL_ROUTER_KEY`, then
opens a new VSCode window on that folder with its own profile directory, so
the Claude Code sessions in that window talk to the proxy; neither VSCode
script takes or sets a model. Everything in the session (subagents included)
runs there. Use
it to burn ChatGPT capacity on exploratory work while your Claude quota rests.
Never point this at a Claude subscription login; see "Play it safe" in the
README.

## 9. Design mockups before the build (Pro home only)

**Session model:** any Claude session (Fable 5.2 orchestrates; Opus 5.5,
Sonnet 5.5 and Haiku 5.5 as the session switch says), with Codex's image
generation on a Pro login.

```
/model-router:fabstra Build the onboarding wizard (3 steps: workspace name,
invite teammates, connect Slack). Render each step as a mockup first so I can
approve the layout before any React is written.
```

What happens: fabstra's mockup rule sends the render request to the Codex side
on the Pro home, one image per named screen, capped at three. You approve or
redirect, then the build proceeds against the approved layout. Skip this if
your plan has no image generation; the flow works without it.

## 10. Two ChatGPT logins - protect the Pro weekly window

**Any terminal.** Only if you run two logins in the proxy.

```bash
proxy-pin status     # which logins are in rotation
proxy-pin team       # proxy calls draw on the team login only
proxy-pin both       # put the Pro login back in rotation
```

What happens: `proxy-pin` flips one login's `disabled` flag through the
proxy's management API, no restart. The standing pin in the skills is
`proxy-pin both`: proxy calls rotate over every login in the proxy, and
`proxy-pin team` keeps the Pro login out of the rotation when you want its
weekly window spared. The pin governs the proxy path only: the skills'
standing fast window (always on, no end date) sends the design review,
Reviewer A/B and every Codex-transport build to a fast native Codex home
first, and the proxy is the fallback (SETUP.md, "Two ChatGPT logins"). With
one login, ignore `proxy-pin` entirely.

---

## Picking a flow

| You want | Type | Cost |
|---|---|---|
| A feature with design review and adversarial review | `/model-router:fabstra <brief>` | highest, best for anything you'd hate to redo |
| One strong model owning the design end to end | `... astra solo: <brief>` | one long Astra session plus two reviews |
| Several independent slices in parallel | `... spawn N astra subagents: <brief>` | N Astra sessions |
| Build plus review, no design gate (a contained change, all six of: at most 3 files; an existing repo pattern cited file:line; an existing test or named check proves it; no excluded category; no architecture or data-model decision; no new or changed user-facing surface) | `/model-router:fabstra <brief>` - the lead classes it | one review: Sol high if Claude built it, a fresh Fable if Codex built it |
| Sol in every seat Astra would hold (Sol-built work still goes to a fresh Fable) | `/model-router:fabstra sol: <brief>` | Sol's quota instead of Astra's |
| The same flow on a Sonnet / Haiku session, or an Opus session below the Orchestrate threshold (fewer than 2 independent tasks, no excluded category) | `/model-router:fabstra <brief>` (Lead mode) | gate-seat plan gate plus gate-seat review |
| Someone to break a plan | `astra review: <plan>` | one read-only Astra call |
| A chore on a GPT model | `scripts/worker.sh "<task>"` | one headless run |
| A whole session on a GPT model | `scripts/session.sh <model>` | your ChatGPT quota |

Trivial one-file edits and lookups: none of the above. Just ask the session.
