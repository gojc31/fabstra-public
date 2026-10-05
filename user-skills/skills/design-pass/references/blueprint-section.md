# Blueprint section

Paste under the builder spec's Conventions; the reviewer spec gets the Gates and Verify sub-blocks.

```
## Design (from design-pass)

Pass: <CLIENT | INTERNAL> · scope <PAGE | SCREEN | COMPONENT | EXISTING> · <INHERIT | OPEN>

Rules (binding):
  The brief's pinned words override every rule below. No eyebrow or kicker label above a heading. No numbered section markers unless the content is a real sequence. No `->` or `→` glyph appended to link or button text. No italic display type. No invented metrics, testimonials, logos, or names. Colours and fonts only from the Tokens block.

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

Gates (reviewer runs these on the built result; N/A is written, not skipped):
  1. <gate text> [<source tag>]
  2. <gate text> [<source tag>]
  <... the scope's subset from gates.md, renumbered from 1>

Verify:
  Screenshot at 375, 768, 1280 through browser-harness.
  First navigation is new_tab(<url>); never goto_url.
  Report each width pass/fail with the cause of any failure.
  <any surface-specific check: a state to exercise, a flow to walk>

Do-not-touch:
  <files, routes, components, copy, tokens the builder must leave alone, or "none">
```
