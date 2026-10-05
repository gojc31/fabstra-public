# FabStra fan-out sizing

Contents: Build waves (real builds); Audit fan-out - when to fan out; 1 count units; 2 seat count; 3 partition; 4 launch; 5 merge and log

Reached from: fabstra SKILL.md - before launching any audit, review, browser QA, or research seat; phases.md Phase 1 and lead-mode.md Gate 2 - while writing a real-build plan (both modes, every lane).

## Build waves (real builds)

A **wave** is the set of builder tasks launched together in one message. Plan a real build as waves of **3-4 builders**: on 2026-09-19..10-03, 82% of fabstra launches sent one agent and 44% of sessions never ran two at once, so builds ran as one long chain.

- Width comes from the plan, never from splitting one spec: each task in a wave owns disjoint files (specs.md, "Shared interfaces and file ownership") and has no run-time dependency on another task in the same wave. Two builders on one spec edit the same files and the merge breaks.
- Cut along seams: per page or route, per feature area, per integration. When tasks share an interface, a **contract task** goes first, alone, in wave 0 (types, schema, API shape, shared component props); wave 1 then builds against it in parallel. A feature and its own test stay one task (phases.md, task sizing).
- A real build with 3+ tasks and a widest wave below 3 states one reason per narrow wave in the plan: a shared file, a run-time dependency, or a contract still unsettled. Every task in a wave is real work; when the honest plan has 2 tasks, the wave is 2.
- Cap 4 builders per wave: past that, Opus seats spend the weekly limit faster than they save time and the smoke gate finds more seam breaks. Contained and small changes stay one task.
- Builders that drive a browser each run `BU_NAME=<task>` (Audit fan-out, step 4).
- Slice-verify each task as it lands. The smoke gate runs once after the last wave, and also between waves when the next wave builds on the previous wave's code.
- The plan and RUN.md show each task's wave (`wave=K`), and each launch logs `wave=K width=W`.

## Audit fan-out

One seat over a whole site or dashboard is the slow path: on 2026-10-03 a single designer polish audit took 20.9 min, a single Sol review hit its 30-turn cap at 23 min on a 20k-line diff, and a single designer camera audit took 45.3 min. Seats over disjoint slices run in parallel, so wall-clock is the slowest slice, not the sum.

### When to fan out

Every audit, review, browser QA, or research job is sized here before its first seat launches, including a Phase 3/4 review whose diff is large. The pairing rule (phases.md) still decides WHICH seat reviews; this file decides HOW MANY copies of it run and over which slice each.

### 1 - Count units

| Job | One unit |
|---|---|
| Browser audit or QA of a site or dashboard | one route or page (all its viewports and states count inside it) |
| Code audit or review | one directory or feature area; weigh it by size in KB of source or diff |
| Research | one independent question |

List the units in RUN.md before sizing. For a browser job, take them from the router or sitemap, not from memory.

### 2 - Seat count

Seat capacity (starting values; retune from the logged elapsed in step 5):

| Seat | Capacity per seat |
|---|---|
| Browser seat (Claude Agent driving browser-harness) | 4 pages |
| Proxy `claude -p` seat (Astra, Sol; 30-turn cap) | ~40 KB of source or diff |
| Claude Agent review seat (fresh Fable, designer, builder) | ~100 KB of source or diff |
| Research seat | 2 questions |

N = ceil(units / capacity), plus one cross-cutting seat when step 3 calls for it. Below 2 units, one seat. Cap: 6 Claude Agent seats and 3 proxy seats in flight at once (each proxy seat spends the same login pool, quota.md); above the cap, raise the per-seat load rather than queueing a second batch, and log it.

### 3 - Partition

Slice by surface, never by dimension: each seat owns a disjoint set of units (a page group, a directory, a question set) and applies the WHOLE rubric to it. A dimension split (one seat for a11y, one for copy, one for perf) makes every seat read the whole surface, so it costs N full reads and saves no time.

Group units that share a template or data source into one slice, so one seat sees each pattern once and reports it once.

Add one **cross-cutting seat** when the surface has shared parts - app shell, nav, design tokens, shared components, a shared data model, auth. It owns those parts and every seam between slices; slice seats report a shared-part defect as one line pointing at the cross-cutting seat, not as a finding.

### 4 - Launch

- Every seat gets the same rubric (Design block, review spec, or audit checklist), the same report format, its own slice list, and the cross-cutting seat's ownership line. Shared material goes in one file every spec points at; a slice spec carries only its slice.
- Each seat writes `<scratch>/findings-<slice>.md` and overwrites it as it goes.
- Browser seats each run their own daemon: `BU_NAME=<slice>` on every browser-harness call, open new tabs only, close only their own tabs. On 2026-10-03 builders sharing the default daemon moved each other's tabs.
- All seats launch in one message (multiple Agent calls; proxy seats as background Bash launches per transport.md).

### 5 - Merge and log

- Merge findings by root cause: one defect seen on five pages is one finding with five locations. Every finding keeps its slice tag, and its verdict follows the normal ledger (phases.md Phase 4 / lead-mode.md).
- A slice that returns no report goes to one fresh seat of the same type, once; log it.
- RUN.md logs `fanout=N units=U capacity=C` at launch and each seat's elapsed when it lands. When a seat type lands well under or over 10 min repeatedly, change its capacity in the table above.
