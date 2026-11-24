# Blueprint section

Paste under the builder spec's Conventions; the reviewer spec gets the Gates and Verify sub-blocks.

```
## Design (from design-pass)

Pass: <CLIENT | INTERNAL> · scope <PAGE | SCREEN | COMPONENT | EXISTING> · <INHERIT | OPEN>

Rules (binding):
  The brief's pinned words override every rule below. No eyebrow or kicker label above a heading. No numbered section markers unless the content is a real sequence. No `->` or `→` glyph appended to link or button text. No italic anywhere. No helper or explainer text under labels, fields, charts or sections. No invented metrics, testimonials, logos, or names. Colours and fonts only from the Tokens block.

Direction:
  Genre: <editorial | modern-minimal | atmospheric | playful>
  Macrostructure: <name, or "n/a - component scope">
  Principles: <one>; <two>; <three>
  Boldness: <the one element that carries it; everything else stays quiet>
  Alignment: <left | centred | justified>
  Changed at review: <what landed on a saturated default and what replaced it, or "none">

Tokens (proposed):
  <--color-name: #hex — role>        (4-6 lines, one role each)
  <--font-display: Face — role>
  <--font-body: Face — role>
  <spacing scale, radius, motion tokens the surface needs, or "none">
  (INHERIT pass: replace this whole sub-block with "inherit: <path to DESIGN.md / tokens file>")

Root overflow: <the decision for this surface, and why>

References (0-2 rows; write "none - no external references" when empty):
  1. <slug> · <url> · take this: <the one thing being borrowed>
  2. <slug> · <url> · take this: <the one thing being borrowed>
  (INHERIT pass: rows are incumbent paths plus the screenshot taken, e.g.
   "src/routes/settings/+page.svelte · <scratch>/incumbent-375.png · take this: the surface's own rhythm")

Layout (first viewport):
  <ASCII wireframe - boxes, labels, what sits where and at what scale>

Components (one line per interactive component, or "none" when the surface has none; each line comes from the best fit for the role and the stack, core sources first (rule 3 of How to pick in the catalogue), looked up by role in D:\jc-ui-kit\CATALOG.md, and takes, written out in full, the shape references/components.md gives for that source - builders never load skills; a sourced component takes the Tokens above for brand - colours, fonts, radii, spacing, icons - and keeps its source motion and interaction 1:1, proven by D:\jc-ui-kit\scripts\motion-diff.py (an Astryx or Lenso package import: by its exact version pin and the Verify walk, references/components.md section 10 or 11); interactive pieces come from a core source with authored motion (Arc), structure pieces from the shadcn-native core; on the Astryx stack, Astryx's own components first, by references/components.md section 10; on the Lenso stack, Lenso's own components first, by references/components.md section 11):
  Stack: <React | the framework> [+ Astryx <version> | + Lenso <version>] + <Tailwind | Tailwind <3 | 4> when Astryx is present | plain CSS> + <shadcn | no shadcn> · from <the signals: package.json react, tailwind.config.*, @import "tailwindcss", components.json, @astryxdesign/core, @lenso/ui, the brief, or "none found">
  <component>: inherit <path>
  (The project already ships a component for that role, on any stack or pass - on a shadcn project that includes its own shadcn or ReUI components.)
  <component>: <the components.md shape for its source, stack and pass>
  (What must survive onto the lines: a ReUI install only on React + shadcn, or React + Tailwind through the init route; on any other framework kit, Bencho and ReUI ride as checklists only. A kit component on an INHERIT or EXISTING pass takes the integration variant, never importing styles\base.css. Every data-grid line carries its keyboard clause and grid walk. Bencho lines carry their known gaps and checklist; Pro lines - any paid tier - only for a tier JC owns (SKILL.md, the Pro bullet) or on the brief's confirmation; else no Pro fit, and the role takes components.md section 9's Pro fallback, whose rebuild line always names what the builder builds until the rebuild lands. On React + Tailwind a line whose component has a kit counterpart may end "· behaviour reference: D:\jc-ui-kit\components\<Name>\README.md Motion and Keyboard sections", whichever source supplied the markup.)

Platform (from SKILL.md step 5d; one line per binding rule, or "none" when 5d did not apply, or "lookup failed (<reason>)"):
  <pattern>: <rule> [mwg <id>]
  (Only MANDATORY items, required attributes and APIs, and stated browser-support caveats. Where the brief, the project's own patterns or a Components line conflicts with a rule, the line reads "<pattern>: conflict - <what wins and why> [mwg <id>]".)

Gates (reviewer runs these on the built result; N/A is written, not skipped):
  1. <gate text> [<source tag>]
  2. <gate text> [<source tag>]
  <... the scope's subset from gates.md, renumbered from 1>

Verify:
  Screenshot at 375, 768, 1280 through browser-harness.
  First navigation is new_tab(<url>); never goto_url.
  Report each width pass/fail with the cause of any failure.
  Run web-checks --sandbox <localhost url> on each changed page (layout shift, reduced motion, dark-mode response, dialog focus); it runs in an isolated WSL Chrome that starts and stops itself. A page behind a login runs as plain web-checks <url> in JC's Chrome, because the sandbox has no logins and would check the login screen. A fail row is a finding for the builder; an inconclusive or error row, or a run with no result table, gets a manual look. A single-theme page runs with --skip color-scheme; a dialog whose trigger is not discoverable needs --dialog-selector <css>.
  <any surface-specific check: a state to exercise, a flow to walk; a data grid's keyboard walk, copied from its Components line>

Do-not-touch:
  <files, routes, components, copy, tokens the builder must leave alone, or "none">
```
