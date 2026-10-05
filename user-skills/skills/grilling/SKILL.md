---
name: grilling
description: Interview the user in batched rounds to settle a design before building. Run when the user types /grilling or says 'grill me'. Not for single-step changes, one-node fixes, or any job smaller than the interview itself.
disable-model-invocation: true
---

## Right-size before you start

<!-- Local addition, not upstream mattpocock/skills. -->

**The interview must cost less than the thing it de-risks.** Judge the build before round 1:

- **Don't grill.** One system, reversible in minutes, no live client data, or the whole job is smaller than the questions. Say what you'll do in one line and build it. Offer the grilling only if the user pushes back.
- **Grill.** Several interacting steps, two or more live systems, real client data, money or messages leaving the building, or a decision that is expensive to unpick later.
- **Unsure?** Ask one question — "quick build, or grill this first?" — and take the answer. Do not open a round to decide whether to open a round.

Relentless applies _inside_ a grilling that is worth running, never to the choice of whether to run one. **Stop early when a round stops producing surprises.** A round that only confirms what the user already told you means the tree is settled — that is a finished grilling, not a lazy one. Simple and working beats thorough and unbuilt.

## The method

Interview the user relentlessly until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled — the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask the whole frontier in one round: number each question and give your recommended answer. Then wait for the user's answers before the next round.

Each question should be formatted like so:

```
❓ **Q1** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>
```

Each round the user answers reshapes the tree — settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.

Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), dispatch a sub-agent to find it — don't ask the user for anything you could look up yourself. Don't block on it: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the sub-agent to report — ask the rest of the frontier now. The _decisions_ are the user's — put each to them and wait.

## Standing frontier — automation and integration builds

<!-- Local addition, not upstream mattpocock/skills. -->

Applies when the build **runs unattended on live client data** — an n8n workflow, a Make scenario, a GoHighLevel automation, a Zapier zap, a webhook handler, a VAPI agent, a Supabase Edge Function. These four are cheap to decide now and expensive to retrofit once the build is live, so put each on the frontier as its prerequisites settle.

**Skip any of the four that plainly does not apply, and say which you skipped and why.** A manually-triggered internal script needs no idempotency key. A one-way notification needs no dead-letter queue. Asking anyway is the over-engineering this section exists to prevent — the point is to catch the expensive omission, not to run a checklist.

- **Webhook contract** — what payload arrives, which fields are guaranteed present, and what proves the sender is genuine (signature, shared secret, IP allowlist)? ➡️ Recommend the strictest check the sender supports, and a schema assertion on every guaranteed field.

- **Failure path** — when a downstream call fails, does the run retry, dead-letter (park the failed item for a human to inspect), or drop it? How many retries, over what backoff, and who gets alerted? ➡️ Recommend explicit dead-lettering over silent retry — a silent retry loop hides the outage until the client finds it.

- **Idempotency** — if the same event arrives twice, does the second run duplicate the work? Which key makes a repeat safe to ignore? ➡️ Recommend an idempotency key on every write to an external system. Assume every webhook fires at least twice.

- **Credential ownership** — whose account holds each connection, yours or the client's? What breaks at handover, and what happens when the token expires? ➡️ Recommend client-owned credentials for anything that outlives the engagement, and note the expiry date of every OAuth token in the design.

The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed. Do not act on it until the user confirms you have reached a shared understanding.
