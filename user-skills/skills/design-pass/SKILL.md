---
name: design-pass
description: "UI design planning for any task that adds or changes a user-facing surface - page, screen, component, dashboard, landing section, form, empty or error state. Run before a fabstra UI blueprint; it is the front door, loading frontend-design, Hallmark and impeccable as reference. Hands off read-only work: `impeccable critique|audit` on an existing surface, `hallmark audit` for a slop score, `hallmark study` for DNA from a URL or screenshot; polish and redesign run through this skill's blueprint. Not for backend, data, or copy-only work."
version: 0.2.0
user-invocable: true
argument-hint: "[brief | component <name> | existing <path> | audit <path> | record]"
---

# design-pass

Plans one user-facing surface and emits a blueprint block a builder subagent can execute. It plans; it never builds.

**Precedence.** When frontend-design, impeccable, or hallmark would also fire on a new-UI request, this skill runs first and loads them as reference; they are invoked directly only through step 1's table.

**Who runs it.** Claude Opus 5.5 is the senior seat for design and UI/UX, by the user's standing decision. On an Opus 5.5 session run this skill in-session. On a Fable 5.1, Sonnet 5.5 or Haiku 4.5 session the orchestrator delegates it to `model-router:designer` (Opus 5.5 at xhigh, read-only), which returns the `## Design (from design-pass)` block, and pastes that block into the builder spec. The block's direction stands at every later gate; reviewers report only what will not work.

What each source is, which sections this skill reads, and its exact path: [references/sources.md](references/sources.md).

## 0. Client gate

On client-confidential work, run your own redaction gate first if you have one, before reading any client file, and work in its tokens from then on. Otherwise work on the brief as given. For every client, no client identifier - client, person, or product name - may reach a tool argument: not an Inspo query, not a slug you search for, not a file name in a probe.

State one line: `Pass: CLIENT` or `Pass: INTERNAL`.

## 1. Terminal verbs

Match the request against the table first. Every target handed off here is already washed by step 0; an unwashed client file or URL never reaches hallmark audit/study or impeccable.

READ-ONLY - the orchestrator may run these itself, hand off and stop:

| The request | Hand off to |
| --- | --- |
| Critique or audit a surface that already exists | `impeccable critique\|audit <target>` - edits no product file; critique stores its own snapshot under the project's .impeccable/ directory (reference/critique.md), which is allowed on this route |
| A slop score on a page or a file | `hallmark audit <target>` - read-only; it returns a ranked punch list and edits nothing |
| The DNA of a design from a URL or a screenshot | `hallmark study <screenshot \| URL>` |
| Charts, data tiles, or a dashboard's numbers | the harness `dataviz` skill when this session lists it - it is a built-in, not a file in this folder. If it is absent, apply the Charts lines of [references/gates.md](references/gates.md) and carry on |

MUTATING - the orchestrator does NOT stop here; it continues through steps 2-6 to produce this skill's block, then delegates to a builder with a bounded spec that cites the verb's reference file plus that block:

| The request | Hand off to |
| --- | --- |
| Polish, or another impeccable transform, on a surface that already exists | continue through steps 2-6, then delegate to a builder: a bounded spec citing `{{SKILLS_DIR}}\impeccable\reference\polish.md` (or the named verb's own reference file - its Commands table also owns bolder, quieter, distill, harden, clarify, adapt, optimize) plus this skill's block |
| A structural redesign that keeps the information architecture and the copy | continue through steps 2-6, then delegate to a builder: a bounded spec citing `{{SKILLS_DIR}}\hallmark\references\verbs\redesign.md` plus this skill's block - impeccable's preserve rules still bind: routes, component ownership, copy intent, brand, IA |

A MUTATING match also continues at step 2, the same as anything else below; it is never a hand off and stop. For both mutating rows, DESIGN.md and `.hallmark/log.json` writes are deferred to step 7 (post-review).

Anything else - a new page, screen, or component, or a change inside a surface that already has a look - continues at step 2.

## 2. Scope

Name one scope in one line. Two signals decide it.

| Scope | Signals |
| --- | --- |
| **PAGE** | a public URL is the deliverable; the visitor decides and acts; the brief names sections rather than controls |
| **SCREEN** | the user is signed in; the brief names a task and the data it moves; loading, empty and error states are part of the ask |
| **COMPONENT** | the brief names one element (button, input, card, modal, dropdown, tab strip, chip, banner, date picker); it runs under 30 words and refers to one element; the target is a single component file; the user says "just the X" or "only the Y" |
| **EXISTING** | the target file already carries a palette or a type stack; the ask is a section, state, or field inside a surface that ships; the brief says add, fix, or match |

When PAGE and SCREEN both fit, ask one question: is the visitor deciding, or working?

## 3. What is already true

Before any direction, read what the surface already commits to: DESIGN.md or tokens.css at the project root, the token block of the entry stylesheet, one representative component, and a screenshot of one existing page if one runs. A missing DESIGN.md does not make the project greenfield - a coherent identity already in code is the authority.

Outcome, one word:

- **INHERIT** - an established world exists. Every EXISTING pass, and most COMPONENT passes, land here.
- **OPEN** - no visual authority anywhere in the project.

INHERIT skips step 4, and skips the direction-picking in step 5. Its references are the incumbent's own surfaces (file paths plus the screenshot you took), and its direction resolves the composition of the new piece only: purpose, content, hierarchy, states, and how the addition joins what surrounds it. Never restart an established world; a durable system change needs the user's approval and is its own task.

## 4. Evidence (Inspo)

Only on an OPEN pass with scope PAGE. SCREEN, INHERIT, COMPONENT and EXISTING passes skip this step entirely: the archive is marketing pages, and on the 2026-09-20 bench its evidence added nothing to an operator screen (bench notes are not shipped).

One pass, never repeated. The call budget:

1. `mcp__inspo__get_filters()` - zero input, cheap; pick valid enum values from what it lists.
2. At most three of: one `mcp__inspo__recommend(brief, pageType, device, maxTokens: 4000)`; then, only if that shortlist is thin, one `mcp__inspo__search_screens(query, detail: "concise", limit: 5, maxTokens: 3000)`; optionally one `mcp__inspo__get_screen(slug)` for the exemplar you choose.

Omit `mode` unless light or dark is already decided - it is the light/dark axis, not a visitor mode. Never call `mcp__inspo__get_design_system` with `live` true; prefer not calling it at all. The `maxTokens` cap is approximate: the top result and all URLs survive it.

Pick one macrostructure and up to two exemplars. Download one or two exemplar screenshots with curl into the session scratch directory and Read them: you must have SEEN a reference before you write direction.

Fallbacks, each terminal - take it and go to step 5:

- Inspo is not connected: write "no external references", continue from the brief alone, and say so in the block.
- Both list calls return empty: the same.

Two exemplars are a target, not a requirement. The block's References sub-block accepts 0, 1, or 2 entries.

## 5. Direction

frontend-design's two passes, condensed. Load that file as reference only; do not run its build step.

**(a) The plan.** Write, compactly:

- 4-6 named hex colours, each with its role. Before the plan leaves, compute the contrast of every text-on-fill pair the tokens imply (action fill with its label, error text on its surface, quiet text on the ground) and write the ratio beside the token; any pair under 4.5:1 is changed here, never handed to the builder. The 2026-09-20 bench shipped a 4.4:1 action button in four of six pages because this step trusted a hex by eye.
- Timed dismissals (undo bars, toasts) are stated as a minimum of 10 seconds with a persistent inline alternative, or as no timer at all; an 8-second undo was flagged as an accessibility weakness on every treated bench page.
- 1-2 typefaces with their roles; if two, make them clearly distinct.
- An ASCII wireframe of the first viewport, and the alignment decision (left, centred, justified).
- Three principles - what makes this surface this one and not a similar one.
- The one element that gets the boldness. Everything around it stays quiet and disciplined.
- The Hallmark genre by name: editorial, modern-minimal, atmospheric, or playful.
- The macrostructure by name from Hallmark's macrostructure index (reference-only).

**(b) The review, before the plan leaves.** Check it against the five saturated-default clusters in frontend-design's Process section, and against Hallmark's structural-variety rule: two surfaces for two briefs must not share one hero-features-CTA-footer rhythm. Where the brief pinned an axis, follow the brief exactly. Where the brief left an axis free and the plan landed on a default, change it and write one line naming what changed.

COMPONENT scope skips the macrostructure and requires the eight interactive states: default, hover, focus-visible, active, disabled, loading, error, success.

These are PROPOSED tokens. They live in the blueprint block, not in DESIGN.md.

## 6. Emit the blueprint block

Load [references/blueprint-section.md](references/blueprint-section.md) and fill every placeholder. A slot with nothing to say gets the word `none`, never a blank.

Gates: take the scope's subset from [references/gates.md](references/gates.md), number them inside the block, and write `N/A` against anything that does not apply rather than dropping the line.

Verify: screenshots at 375, 768 and 1280 through browser-harness, first navigation `new_tab(url)`, never `goto_url`.

State, under the block: "paste under the builder spec's Conventions; the reviewer spec gets Gates + Verify".

## 7. Record

After the build passes review, not before. `design-pass record` is the argument that runs this step alone.

The orchestrator delegates both parts to one Haiku task:

- **DESIGN.md at the project root.** Create it - 45 lines at most, tokens by semantic role, type roles, spacing scale, the fingerprint, the reference slugs - only when none exists AND the world was OPEN. When one exists and this pass added a new surface, back it up beside itself as `DESIGN.md.bak-<YYYY-MM-DD>` first, then append a `## Surface: <name>` section. An EXISTING or INHERIT pass composed inside a surface that already ships, so it has no new surface to record and writes no DESIGN.md at all. Never rewrite what is already there.
- **The log line.** Append one line to `.design-pass/log.md` at the project root in the format in [references/record.md](references/record.md).

If the pass ran a `hallmark redesign` at PAGE or SCREEN scope, the same Haiku task also appends the entry `hallmark/references/verbs/redesign.md` specifies to `.hallmark/log.json` (create it if absent); COMPONENT and EXISTING passes never write that file, and no other route does either.

## Rules

- The brief wins over every rule here. A pinned colour, era, material, face, or layout is followed exactly, including when it names a default.
- Inherit before invent: a section, component, feature, or state inside an established surface inherits that surface.
- The sources are reference only. Never enter Hallmark's Design flow or its three-question gate, and never run impeccable's concept-seed tournament, from inside this skill.
- One Inspo pass, capped, carrying INTERNAL, redacted, or name-free text only in its arguments - for every client, no client, person, or product name.
- No invented metrics, testimonials, logos, or customer counts: a number the brief did not supply ships as a marked placeholder or the section is built another way.
- Headers stay roman, a heading carries its own weight with no eyebrow above it, numbered sections appear only on a real sequence, and link text ends in a word rather than an arrow glyph.
- Root overflow is decided per surface and written into the block. Hallmark's `overflow-x: clip` mandate is not adopted as a default here, because clipping the root hides an overflow bug instead of naming it.
- Every gate is a pass/fail check on the built result, run by the reviewer - never a promise made at plan time.
- Write nothing outside the session scratch directory until step 7.
