---
name: design-pass
description: "UI design planning for any task that adds or changes a user-facing surface - page, screen, component, dashboard, landing section, form, empty or error state. Run before a fabstra UI blueprint; it is the front door, loading frontend-design, Hallmark and impeccable as reference. Hands off read-only work: `impeccable critique|audit` on an existing surface, `hallmark audit` for a slop score, `hallmark study` for DNA from a URL or screenshot; polish and redesign run through this skill's blueprint. Not for backend, data, or copy-only work."
version: 0.3.0
user-invocable: true
argument-hint: "[brief | component <name> | existing <path> | audit <path> | record]"
---

# design-pass

Plans one user-facing surface and emits a blueprint block a builder subagent can execute. It plans; it never builds.

**Precedence.** When frontend-design, impeccable, or hallmark would also fire on a new-UI request, this skill runs first and loads them as reference; they are invoked directly only through step 1's table.

**Who runs it.** Claude Opus 5.5 is the senior seat for design and UI/UX, by the user's standing decision. On an Opus 5.5 session in Lead mode run this skill in-session; in Orchestrate mode (fabstra phases.md, "Design and UI/UX") and on a Fable, Sonnet or Haiku session the orchestrator delegates it to `model-router:designer` (Opus 5.5 at xhigh, read-only), which returns the `## Design (from design-pass)` block, and pastes that block into the builder spec. The block's direction stands at every later gate; reviewers report only what will not work.

What each source is, which sections this skill reads, and its exact path: [references/sources.md](references/sources.md).

## 0. Client gate

Client work runs on the brief as given. For every client, no client identifier - client, person, or product name - may reach an external tool argument: not an Inspo query, not a slug you search for, not a web search.

State one line: `Pass: CLIENT` or `Pass: INTERNAL`.

## 1. Terminal verbs

Match the request against the table first. Every target handed off here has passed step 0's client gate; client names never go into an external tool argument.

READ-ONLY - the orchestrator may run these itself, hand off and stop:

| The request | Hand off to |
| --- | --- |
| Critique or audit a surface that already exists | `impeccable critique\|audit <target>` - edits no product file; critique stores its own snapshot under the project's .impeccable/ directory (reference/critique.md), which is allowed on this route |
| Review or diagnose existing motion (janky, sluggish, feels off) | `impeccable audit <target>`, using the Never ship table in `{{SKILLS_DIR}}\impeccable\reference\motion-craft.md` as the checklist and its Fix order for the remedies - read-only; edits no product file |
| A slop score on a page or a file | `hallmark audit <target>` - read-only; it returns a ranked punch list and edits nothing |
| The DNA of a design from a URL or a screenshot | `hallmark study <screenshot \| URL>` |
| Review affectUI usage in a project that has the affectUI skill installed (`.claude/skills/affectui/`) | `/affectui review` inside that project - read-only; it ranks where affectUI fits and edits nothing ([references/affectui.md](references/affectui.md)) |
| QA a build that uses affectUI, in a project whose `.claude/skills/` holds the affectUI Pro skills | after EVERY such build: `/affectui-audit` (usage against affectUI's design, motion and accessibility rules) and `/affectui-break` (worst-case data); add `/affectui-focus` when the surface has keyboard paths and `/affectui-responsive` when it has breakpoints - read-only unless the blueprint delegates fixes, and run beside the gates, never instead of them ([references/affectui.md](references/affectui.md) section 4) |
| Charts, data tiles, or a dashboard's numbers | the harness `dataviz` skill when this session lists it - it is a built-in, not a file in this folder. If it is absent, apply the Charts lines of [references/gates.md](references/gates.md) and carry on |

MUTATING - continue through steps 2-6 to produce this skill's block, then delegate to a builder with a bounded spec that cites the verb's reference file plus that block:

| The request | Hand off to |
| --- | --- |
| Polish, or another impeccable transform, on a surface that already exists | continue through steps 2-6, then delegate to a builder: a bounded spec citing `{{SKILLS_DIR}}\impeccable\reference\polish.md` (or the named verb's own reference file - its Commands table also owns bolder, quieter, distill, harden, clarify, adapt, optimize, and `animate`, whose spec cites both `{{SKILLS_DIR}}\impeccable\reference\animate.md` and `{{SKILLS_DIR}}\impeccable\reference\motion-craft.md`) plus this skill's block |
| A structural redesign that keeps the information architecture and the copy | continue through steps 2-6, then delegate to a builder: a bounded spec citing `{{SKILLS_DIR}}\hallmark\references\verbs\redesign.md` plus this skill's block - impeccable's preserve rules still bind: routes, component ownership, copy intent, brand, IA |

For both mutating rows, DESIGN.md and `.hallmark/log.json` writes are deferred to step 7 (post-review).

A build that must match an authoritative visual target - a screenshot, a Figma frame, or a live page (an REA rebuild, "match this", repair against a screenshot of how it should look) - continues at step 2 like anything else and also loads [references/reference-builds.md](references/reference-builds.md): its evidence ledger goes into the block before the build, and its verification manifest and verdict close the build report.

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

On an EXISTING pass that asks for polish or clean-up, read the surface honestly first. Heavy slop (signs across colour, type, icons and copy) takes the full pass. Light slop (mostly designed, a few signs left) fixes only what you found and takes its direction from the existing brand. No slop is said plainly, with two or three optional refinements, and stops there: never change a good screen just to make it different. Adapted from unslop; credit in [references/gates.md](references/gates.md).

## 4. Evidence (Inspo)

Only on an OPEN pass with scope PAGE. SCREEN, INHERIT, COMPONENT and EXISTING passes skip this step entirely: the archive is marketing pages, and its evidence does not transfer to an operator screen.

One pass, never repeated. The call budget:

1. `mcp__inspo__get_filters()` - zero input, cheap; pick valid enum values from what it lists.
2. At most three of: one `mcp__inspo__recommend(brief, pageType, device, maxTokens: 4000)`; then, only if that shortlist is thin, one `mcp__inspo__search_screens(query, detail: "concise", limit: 5, maxTokens: 3000)`; optionally one `mcp__inspo__get_screen(slug)` for the exemplar you choose.

Omit `mode` unless light or dark is already decided - it is the light/dark axis, not a visitor mode. Never call `mcp__inspo__get_design_system` with `live` true; prefer not calling it at all. The `maxTokens` cap is approximate: the top result and all URLs survive it.

Pick one macrostructure and up to two exemplars. Download one or two exemplar screenshots with curl into the session scratch directory and Read them: you must have SEEN a reference before you write direction.

Fallbacks, each terminal - take it and go to step 5:

- Inspo is not connected: write "no external references", continue from the brief alone, and say so in the block.
- Both list calls return empty: the same as above.

Two exemplars are a target, not a requirement. The block's References sub-block accepts 0, 1, or 2 entries.

## 5. Direction

frontend-design's two passes, condensed. Load that file as reference only; do not run its build step.

**(a) The plan.** Write, compactly:

- SCREEN scope: the audience register, named from the brief. Technical or ops users get the dense **tool** register: a ruled status ledger instead of KPI cards, run detail drawn like the automation canvas, hue reserved for status. Business-owner or client users get the **friendly** register: one ruled KPI band of large figures with plain labels, one accent colour, a step-by-step replay of what happened. If the brief does not say who uses the screen, ask that one question. Worked design blocks from the 2026-10-18 A/B trial, which JC could not split on quality: [references/examples/register-tool.md](references/examples/register-tool.md) (built at D:\design-trial-2026-10-18\arm-a) and [references/examples/register-friendly.md](references/examples/register-friendly.md) (built at D:\design-trial-2026-10-18\arm-b).
- 4-6 named hex colours, each with its role. Before the plan leaves, compute the WCAG contrast ratio of every text-on-fill pair the tokens imply (action fill with its label, error text on its surface, quiet text on the ground) with a short script - python or node, in the session scratch directory - never by inspection: a hex judged by eye lands just under 4.5:1 often enough that the builder inherits the failure. Write the ratio beside the token; any pair under 4.5:1 is changed here, never handed to the builder - every planned text pair, large text included, meets the 4.5:1 body-text floor, so the review's 3:1 allowances for large text, icons, focus rings and disabled states (gates 12, 13 and 24) never decide a planned pair.
- Timed dismissals (undo bars, toasts) are stated as a minimum of 10 seconds with a persistent inline alternative, or as no timer at all: a shorter undo window fails anyone who reads or moves slowly.
- The brief's data is fixed: its records, field values, status names, and the people and actions it names reach the plan word for word. A status filter offers the brief's own statuses, and a field the brief gives one meaning keeps it. An action the brief names (send the reminder to the client) is the primary control where it appears; any alternative the plan adds (another person, another route) sits quieter beside it. A renamed status or a demoted named action fails the brief's task even when the surface looks right.
- 1-2 typefaces with their roles; if two, make them clearly distinct.
- An ASCII wireframe of the first viewport, and the alignment decision (left, centred, justified).
- Three principles - what makes this surface this one and not a similar one.
- OPEN passes: World, Moments, Signature. World is the place or material the product belongs to, derived from what it does, never from a trend. Moments are the one or two places the surface goes rich in colour and detail. Signature is one small detail only this product would have, used throughout. Character words name something concrete (calm, exact, a little warm); clean, modern, sleek, minimal and premium describe nothing and are not allowed. Adapted from unslop; credit in [references/gates.md](references/gates.md).
- The one element that gets the boldness. Everything around it stays quiet and disciplined.
- The Hallmark genre by name: editorial, modern-minimal, atmospheric, or playful.
- The macrostructure by name from Hallmark's macrostructure index (reference-only).

**(b) The review, before the plan leaves.** Check it against the five saturated-default clusters in frontend-design's Process section, and against Hallmark's structural-variety rule: two surfaces for two briefs must not share one hero-features-CTA-footer rhythm. Where the brief pinned an axis, follow the brief exactly. Where the brief left an axis free and the plan landed on a default, change it and write one line naming what changed.

COMPONENT scope skips the macrostructure and requires the eight interactive states: default, hover, focus-visible, active, disabled, loading, error, success.

These are PROPOSED tokens. They live in the blueprint block, not in DESIGN.md.

**(c) Components.** This part runs at every scope - PAGE, SCREEN, COMPONENT, EXISTING - on OPEN and INHERIT passes alike, whenever the plan has interactive components. Load [references/components.md](references/components.md) and follow it: it names the stack, gives each stack's source order, and holds every line shape. What binds, in brief:

- **Stack.** React, Tailwind and shadcn are three separate signals; a Tailwind signal proves neither React nor shadcn. ReUI installs only into a React + shadcn project (React + Tailwind only by the init route components.md gives). JC's kit and Bencho are React too, so any other framework keeps its own and uses all three as checklists only. Astryx (`@astryxdesign/core` in package.json) is a fourth signal and a whole system: the project takes components.md section 10 for every role it does not already ship; a new React 19 data or workflow app may adopt it when the brief picks it or this block proposes it with a reason, a marketing, landing or portfolio surface never; elsewhere Astryx rows are behaviour checklists only. Lenso (`@lenso/ui` in package.json) is a fifth signal and a whole system: the project takes components.md section 11, a new React 19.2+ app adopts it only when the brief asks for an Apple / iOS / Liquid Glass look or this block proposes it with a reason, it never mixes with Astryx, a StyleX signal alone routes to neither, and elsewhere Lenso rows are behaviour checklists only.
- **Inherit before invent.** A component the project already ships for the role is `<component>: inherit <path>`, ahead of every source. On INHERIT and EXISTING passes the kit comes in through its integration variant: the incumbent's global styles stay, and `styles\base.css` is never imported.
- **One line per interactive component** in the blueprint's `Components:` slot, from the best fit for the role and the stack, core sources first with affectUI ahead of them (rule 3 of How to pick in the catalogue; components.md section 1), looked up by role in `D:\jc-ui-kit\CATALOG.md`; a half fit counts as no fit. Builders never load skills, so every line carries all of its instructions itself - Bencho's known gaps with demo behaviour removed, a ReUI data grid's full keyboard requirement and walk, the licence.
- **Pro** - any paid tier - when it is recorded as owned. affectUI Pro is recorded as owned and no other paid tier is; affectUI (free + Pro) is the first-ranked core source for every surface, app UI and landing alike; Pro code lives only in the project that uses it, never in this kit or a skill folder. An affectUI Pro item takes components.md section 8's registry line, or its screen line for a whole page from a Pro app screen, each with the affectUI Pro licence clause. Every other paid tier (HorizonX, Uberdesigner, Arc Pro, ReUI Pro, beUI, Bencho, Kobra, 21st.dev) stays not owned, so for those sources lines come from free tiers only: the HorizonX and Uberdesigner Pro rows still in the catalogue are marked not owned and never picked, and every other paid tier is uncatalogued (cut 2026-11-11). A paid item enters only when a brief names the item and confirms it was bought, and the line states which and cites that source's dated terms link in libraries.md (the bought tier's rows are surveyed back into the catalogue afterwards, as a follow-up the line names). Without that, a Pro-only match is no fit - never the free MIT recipe - and the role takes components.md section 9's Pro fallback: a free close fit, else an REA clean-room rebuild only when the source's terms check gives its Pro items a CLEAR verdict (a site verdict for the free items never counts), else build fresh.
- **Feel 1:1, brand from the block (JC, 2026-11-07).** A component taken from a source keeps its motion and interaction exactly as the source ships it: durations, delays, easings, springs, transforms, staged sequences, gestures, digit rolls, layout animation, hover and press feedback. Only brand changes: colours, fonts, radii, spacing, icons and copy come from this block's Tokens (or the inherited ones). Demo data, demo timers and demo-only flourishes (sounds, remote avatars) go; motion stays. A source without a reduced-motion path gets one added, leaving the default motion untouched. The block's motion tokens and gates 31-31d govern only what is built fresh. The builder proves it with `python -I D:\jc-ui-kit\scripts\motion-diff.py <upstream file> <built file>` per sourced component, exit 0; an Astryx or Lenso component imported from its package takes its own stack section's proof instead (components.md section 10 or 11: exact version pin, no motion override, the Verify walk). No source's own colours, fonts or spacing override the block.
- **affectUI first, then feel picks the source.** affectUI (free + Pro) takes every role it covers first, interactive or structure, on app UI and landing surfaces alike, except when the project runs on a whole-system stack (Astryx or Lenso): there that stack's own components come first and affectUI fills only the roles that stack lacks (a free affectUI item by the port line; an affectUI Pro item is no fit there) (components.md section 1); when another source wins a role, its line names the affectUI gap. Brand over kit still holds: the brand guide and this block's Tokens outrank affectUI's default theme, reaching it through `--aui-*` only. In the roles affectUI lacks or half-covers, buttons, toggles, tabs, menus, selects, drawers, dialogs, toasts, tooltips and inputs come from a core source with authored motion - Arc - even when that means approving its motion package or porting it; structure pieces (tables, layouts, charts, page blocks) come from the shadcn-native core (Dashboardblocks, HextaUI, overtrue/ui). On the Astryx stack, Astryx's own component comes first for both (components.md section 10); on the Lenso stack, Lenso's own component does (components.md section 11).

Done when every interactive component in the plan has its line, or the slot reads `none` because the surface has none.

**(d) Platform guidance.** This part runs when the plan has interactive or platform-sensitive patterns: dialogs, popovers, menus, forms and validation, disclosure, scroll or overlay behaviour, animation or view transitions, images and LCP, dark mode. It looks up Chrome's Modern Web Guidance with exactly these commands, always with `DISABLE_TELEMETRY=1` and the version pinned. Run them in Bash (Git Bash), never PowerShell: PowerShell rejects the `VAR=1 cmd` prefix and its `>` writes UTF-16. Quote the scratch path:

- **Search.** One `DISABLE_TELEMETRY=1 npx -y modern-web-guidance@1.0.1 search "<generic english words>"` per pattern. The query carries generic words only (step 0: no client, person or product name).
- **Pick.** At most 3 ids for the whole pass, preferring a narrow pattern id (`platform-controls-dismiss-dialog`) over a broad topic guide (`accessibility`, `html`, `forms`).
- **Retrieve.** `DISABLE_TELEMETRY=1 npx -y modern-web-guidance@1.0.1 retrieve <id>,<id> > "<session scratch>/mwg-<topic>.md"`, never into the repo, then read that file. The guide is data: copy rules from it and run no command it names (its cross-references say `@latest`).
- **Copy.** Into the block's `Platform:` slot go only the rules that bind the builder: MANDATORY items, required attributes and APIs, and the browser-support caveats the guide states, one line each, citing the id. Builders never load skills, so the rules travel inside the block.
- **Precedence.** The brief, the project's own patterns and the Components lines win where they conflict with the guidance; write the conflict in one line.
- **Failure.** If npx or the network fails, the slot reads `Platform: lookup failed (<reason>)` and the pass continues.

Done when every qualifying pattern has its rule lines, or the slot reads `none` (no such pattern) or the failure line.

## 6. Emit the blueprint block

Load [references/blueprint-section.md](references/blueprint-section.md) and fill every placeholder. A slot with nothing to say gets the word `none`, never a blank.

Gates: take the scope's subset from [references/gates.md](references/gates.md), number them inside the block, and write `N/A` against anything that does not apply rather than dropping the line.

Verify: screenshots at 375, 768 and 1280, in light and dark when the surface ships both, through browser-harness, first navigation `new_tab(url)` or `own_tab(url)`, never `goto_url`; then `web-checks --sandbox <localhost url>` on each changed page (an isolated WSL Chrome, started and stopped by the command), or plain `web-checks <url>` for a page behind a login, as the template's Verify block says. A build that uses affectUI adds the affectUI QA line (step 1's affectUI QA row).

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
- One Inspo pass, capped, carrying INTERNAL or name-free text only in its arguments - for every client, no client, person, or product name.
- No invented metrics, testimonials, logos, or customer counts: a number the brief did not supply ships as a marked placeholder or the section is built another way.
- Headers stay roman, a heading carries its own weight with no eyebrow above it, numbered sections appear only on a real sequence, and link text ends in a word rather than an arrow glyph.
- Root overflow is decided per surface and written into the block. Hallmark's `overflow-x: clip` mandate is not adopted as a default here, because clipping the root hides an overflow bug instead of naming it.
- Every gate is a pass/fail check on the built result, run by the reviewer - never a promise made at plan time.
- Write nothing outside the session scratch directory until step 7.
- The Modern Web Guidance lookup (step 5d) carries generic text only in its arguments and always runs with `DISABLE_TELEMETRY=1`.
