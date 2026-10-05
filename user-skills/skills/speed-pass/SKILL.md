---
name: speed-pass
description: Latency pass over any web app or service, graded against the twenty (the 20-point web-performance checklist) - audit, slice, build, prove nothing broke, ship. Use when the user asks to optimize an app, reduce latency, speed up a slow site, page or API, or names the twenty or the Facebook reel checklist. For a single known slow query or one component, fix it directly instead.
disable-model-invocation: true
---

# Speed pass

A speed pass grades an app against **the twenty**, fixes what the grades justify in reviewable **slices**, and proves each slice changed speed and nothing else. The twenty is the rubric, never the to-do list: most items come back "already handled" or "the platform's job", and saying so with evidence is a finding.

The method is stack-agnostic. Step 1 identifies the stack; every later step uses that project's own router, database, build tool and test gates.

## 1. Baseline

Identify the stack: framework and rendering model (server-rendered, single-page, static, API-only), database and how it is reached, auth provider, host. Record the commit, confirm the working tree is clean, fetch the remote, and rebase onto the default branch. Run the project's own gates (type check, lint, tests, build) and write down every failure that exists before you touch anything.

Done when: you can name the stack in one line and the base commit, and every pre-existing failure is listed with proof it fails on the untouched base.

## 2. Audit the twenty

Launch four read-only audit agents in one message, each writing a full report to the scratchpad and returning a short summary. Give each its share of [reference/the-twenty.md](reference/the-twenty.md) and the stack line from step 1:

| Agent | Items |
|---|---|
| Server data flow | caching, computed results, N+1, waterfalls, streaming and skeletons, payload size |
| Database | indexes, N+1 at the query level, pooling, query-level pagination |
| Client | code splitting, lazy loading, images, minify, rerenders, debounce, render-side pagination, unused deps, deferred scripts |
| Measurement | build output, bundle contents, gate baselines, dependency check |

An API-only service drops the Client agent; a static site drops Database. Say which agents ran and why.

Done when: every one of the twenty has a **verdict** with file:line evidence - `fix`, `already handled`, `platform's job`, `not applicable`, or `needs a decision`.

## 3. Slice

Group the `fix` verdicts into slices, smallest blast radius first. A slice is one reviewable pull request: no new dependency, no schema change to production data, and no policy change unless that change is the slice's whole point. Everything tagged `needs a decision` goes into a written ask for whoever owns that decision, with the measured numbers attached.

Done when: every `fix` verdict sits in exactly one slice, and every `needs a decision` verdict names its owner.

## 4. Build one slice

Read [reference/traps.md](reference/traps.md) first, and the matching file in `reference/stacks/` if one exists for this stack. Hand the slice to the project's build flow; where an orchestrated build-and-review flow is installed, use it. Parallel tasks own disjoint files. Every memo or cache added in a speed pass lives for one request unless the owner of the data policy has approved longer.

Done when: the project's gates match the step 1 baseline exactly, plus any new guard the slice added, registered wherever the project registers guards.

## 5. Measure

Follow [reference/measure.md](reference/measure.md). Report counted things - queries per page render, bytes on first load - as before and after on the same data. State plainly when a measurement was inconclusive.

Done when: each change in the slice has either a before/after number or a verify script that failed on the old code and passes on the new.

## 6. Prove nothing broke

Two proofs, both required before a pull request:

- **Caller table.** For every changed or newly wrapped export, grep every call site and rule it `UNCHANGED`, `CHANGED`, or `UNVERIFIED` with file:line evidence. Give one reviewer at most seven exports; split wider scopes across reviewers running in parallel, and have each write its report early.
- **Route crawl.** Run `scripts/crawl.py` over every route on the branch, then on the base, restarting the server after each checkout. Diff status codes and error markers. [reference/measure.md](reference/measure.md) covers building the routes file and crawling behind a login.

Done when: every call site has a ruling, every route's status is identical on both sides or the difference is written into the pull request description, and the repository is back on the slice branch with a clean tree.

## 7. Ship

One commit per slice, with the verification summary and every known behaviour change in the message. Later slices stack: branch slice N+1 from slice N, open its pull request against slice N's branch, and retarget it to the default branch after slice N merges. Fold review fixes into their owning commit with `git commit --fixup` and `GIT_SEQUENCE_EDITOR=true git rebase -i --autosquash <base>`, then re-point the earlier slice's branch.

Done when: each pull request shows exactly one commit, its description lists every behaviour change the proofs found, and the owner of each `needs a decision` item has the written ask.

## Growing the skill

When a project teaches a trap that holds across stacks, add it to `reference/traps.md`. When it is specific to one framework, database or provider, add or extend a file in `reference/stacks/`, named for that stack.
