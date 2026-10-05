# Use cases - what to type, what happens, what you get back

Ten worked briefs. Each one names the session model it expects, the exact
thing to type, which seats fire, and what lands in your repo. Effort words
(`xhigh`, `high`, `medium`) anywhere in a brief pin the Astra and Sol effort
for that run; leave them out and the skill's effort rubric picks.

Legend: **Fable** = Claude Fable 5.1 (your session model, plans only).
**Astra** = GPT-6 Astra (senior reviewer, runs the Codex side). **Sol / Terra /
Luna** = GPT-5.6 tiers on Codex. **Opus / Sonnet / Haiku** = Claude builders
via the Agent tool on your normal Claude login.

---

## 1. A real feature, start to finish (`/model-router:fabstra`)

**Session model:** Fable 5.1.

```
/model-router:fabstra Add a "forgot password" flow to the Next.js app: request page,
signed one-hour token emailed via Resend, reset page, and a rate limit of 3 requests
per email per hour. Supabase auth is already wired. Tests for the token and the limit.
```

What happens: Fable reads the repo and writes a plan with one blueprint per
task (files, function signatures, test names). Astra design-reviews the plan
before anything is built and can block it. Tasks tagged Claude go to Opus or
Sonnet subagents; tasks tagged Codex go to Astra's thread, which spawns Sol
(hard), Terra (medium), or Luna (mechanical). Astra adversarially reviews the
Claude-built parts; a fresh Fable context reviews the Codex-built parts. Fable
arbitrates every finding and logs why.

You get: the code, the tests run green in a smoke gate, `.fabstra/RUN.md` in
the project with the plan, every finding, and every decision, and a calibrated
report that separates verified from unverified.

## 2. Let Astra design and build alone (Lane B, "astra solo")

**Session model:** Fable 5.1.

```
/model-router:fabstra astra solo: turn scripts/export.py into a proper CLI with
subcommands (csv, json, sheets), a --since date filter, and a --dry-run flag. Keep
the current behaviour as the default `csv` subcommand. xhigh
```

What happens: instead of blueprints, Fable writes a brief. Astra runs through
the proxy as a single long session and designs plus builds end to end. Sol at
xhigh and a fresh Fable context both review; the three must agree before it
ships. Use it when the design space is wide and you'd rather one strong model
own the whole shape than split it into tasks.

## 3. Fan out several Astras on disjoint slices

**Session model:** Fable 5.1.

```
/model-router:fabstra spawn 3 astra subagents: migrate the three legacy jobs in
jobs/ (nightly-report, invoice-sync, lead-scoring) from cron shell scripts to the
new Worker base class in lib/worker.py. One job per Astra, no shared files.
```

What happens: Lane B fan-out. Fable splits the work into disjoint slices, runs
up to three solo Astras in flight, and each slice gets the same Sol plus Fable
double review. Best for repetitive-but-not-mechanical migrations where the
slices don't touch the same files.

## 4. You are on Sonnet or Opus, not Fable (`fable-mode`)

**Session model:** Opus 5, Sonnet 5, or Haiku 4.5.

```
fable mode: the checkout webhook handler double-charges on Stripe retries. Find
the real cause and fix it - I have already tried adding an idempotency key on
the client and it still happens.
```

What happens: the skill loads the five gates (scope, evidence, adversarial
reasoning, verify, calibrated report). Your session drafts a plan; Astra reads
it plus the repo and returns the authoritative plan, which binds. Your session
builds it (itself, or through Sonnet / Haiku subagents), launches any Codex
side work, runs the smoke gate, and Astra reviews the finished build. On a
debugging brief like this the plan gate usually kills the first theory before
you spend an hour on it.

Trigger phrases that also work: "think like Fable", "slow down and do this
right", "have Astra check the plan".

## 5. Medium change, no design review needed (`/model-router:fabsol`)

**Session model:** Fable 5.1.

```
/model-router:fabsol Replace the hand-rolled retry loop in lib/http.py with
tenacity, same backoff (0.5s, x2, max 5 tries), and update the three call sites.
```

What happens: Fable specs, Opus / Sonnet / Haiku or Sol build, Sol at xhigh or
a fresh Fable context reviews. Cheaper than fabstra because there is no Astra
design gate. Reach for it when the shape of the change is obvious and you want
the build plus adversarial review without the full crew.

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
Do not change behaviour." gpt-5.6-sol medium
```

What happens: one `claude -p` run on Sol through the proxy with edits allowed
and a 20-turn cap. This is the raw building block the flows use; call it
directly for chores you would not bother orchestrating.

## 8. A whole Claude Code session on a routed model

**Any terminal or VSCode.** Requires the proxy running.

```bash
scripts/session.sh gpt-5.6-sol        # terminal
scripts/vscode.sh gpt-5.6-sol         # separate VSCode profile on that model
```

What happens: Claude Code starts with Sol as its model, on your ChatGPT login
via the proxy. Everything in the session (subagents included) runs there. Use
it to burn ChatGPT capacity on exploratory work while your Claude quota rests.
Never point this at a Claude subscription login; see "Play it safe" in the
README.

## 9. Design mockups before the build (Pro home only)

**Session model:** Fable 5.1, with Codex's image generation on a Pro login.

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
proxy-pin team       # Sol / Terra / Luna draw on the team login only
proxy-pin both       # put the Pro login back in rotation
```

What happens: `proxy-pin` flips one login's `disabled` flag through the
proxy's management API, no restart. The default policy in the skills is Astra
native on the Pro login (`codex-pro`), proxy pinned to the second login for
everything else, so an Astra build never empties the pool your Sol reviews
depend on. With one login, ignore this entirely.

---

## Picking a flow

| You want | Type | Cost |
|---|---|---|
| A feature with design review and adversarial review | `/model-router:fabstra <brief>` | highest, best for anything you'd hate to redo |
| One strong model owning the design end to end | `... astra solo: <brief>` | one long Astra session plus two reviews |
| Several independent slices in parallel | `... spawn N astra subagents: <brief>` | N Astra sessions |
| Build plus review, no design gate | `/model-router:fabsol <brief>` | medium |
| The Fable discipline on an Opus / Sonnet session | `fable mode: <brief>` | Astra plan gate plus Astra review |
| Someone to break a plan | `astra review: <plan>` | one read-only Astra call |
| A chore on a GPT model | `scripts/worker.sh "<task>"` | one headless run |
| A whole session on a GPT model | `scripts/session.sh <model>` | your ChatGPT quota |

Trivial one-file edits and lookups: none of the above. Just ask the session.
