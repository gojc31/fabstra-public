# Reference builds

Source: the evidence ledger, authority order, verification manifest, correction loop and readiness verdict below are adapted from `design-to-code` by Atharv Jadav (github.com/Atharvsinh-codez/skills, `design-to-code/references/reference-forensics.md` and `verification.md`, MIT, Copyright (c) 2026 Atharv Jadav, read 2026-11-04) [D2C]. Keep this notice with any copy of this file. Rewritten for design-pass and JC's tools; nothing here is pasted.

## When this file applies

Load it when a build has an authoritative visual target: a screenshot, a Figma frame or export, or a live page that the result must match. Typical cases: an REA rebuild, a brief that says "match this" or "make it look like this", and repair of an existing surface against a screenshot of how it should look.

It does not apply to an OPEN pass that only uses Inspo or gallery screenshots as inspiration; those are references for composition, not targets. `hallmark study` still owns pulling a design's DNA from a URL or screenshot; this file owns proving that a build matches one.

What it adds to the blueprint block: a ledger (before the build) and a manifest plus a verdict (after it). The builder's spec cites this file; the reviewer checks the manifest and the verdict.

## Rights

Third-party branding, logos, copy and imagery are reproduced only when the person who owns them, or JC on their behalf, has authorised it (a client rebuilding its own site, a licensed template). Otherwise the build keeps the layout, rhythm and behaviour and substitutes the brand, copy and images, and each one is a Substituted row in the ledger. A sign-in, checkout or payment surface copied from a third party never takes live input: its submissions are inert or mocked unless the user supplied an authorised backend. [D2C]

## Authority order

When sources disagree, the higher one wins:

1. What the user said, including later corrections.
2. Assets and content the user supplied and is entitled to use.
3. The pixels and behaviour visible in the authoritative reference.
4. Other references: further viewports, states, routes, themes, motion samples.
5. The project's own design system and repository conventions.
6. design-pass defaults and the scope's gates.
7. The smallest inference that can be undone later.

A brand guide or DESIGN.md sits at 5 for a rebuild of someone else's page, and above 3 when the job is "our product, matching this layout" - say which in the ledger's first row. [D2C]

## Before the build: the evidence ledger

First list every reference: file or URL, route, CSS viewport and device-pixel ratio, theme, visible state, scroll position, and whether it is primary or supporting. Write `unknown` for anything not knowable; never guess a viewport from a cropped image and present it as fact. Read every image at full detail; when it is dense, crop and enlarge it with Pillow per the global dense-images rule rather than reading the downscaled whole. A crop is a closer look at existing evidence, never a new authoritative reference.

Then keep one row per material decision (container width, grid, type family and scale, colour tokens, image crops, nav behaviour at narrow widths, motion):

| Element | Status | Source | Decision | Checked by |
| --- | --- | --- | --- | --- |
| Hero container | Observed | desktop 1440 ref | max-width 1200px, 24px gutters | overlay, pass 2 |
| Mobile nav | Inferred | desktop ref only | disclosure menu | keyboard + 375 check |
| Display face | Substituted | licensed face unavailable | metric-matched fallback | headline wrap compared |

Three statuses only:

- **Observed** - visible in the reference, measured from it, or supplied.
- **Inferred** - not visible; derived from the layout's relationships or from conventional behaviour.
- **Substituted** - replaced for rights, availability, accessibility or a technical limit. The row says why and what visible difference remains.

An Inferred or Substituted decision is never described as an exact match, in the block, the build report or the commit message. [D2C]

## After the build: the verification loop

**Manifest.** One row per authoritative target, kept in the run's evidence folder:

| Route | Viewport / DPR | Theme / locale | State / scroll | Reference | Build capture | Diff | Largest mismatch | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/` | 1440x900 / 1 | light / en | default / top | ref/home-1440.png | out/home-1440.png | out/home-1440-diff.png | hero image 40px low | fail |

Never compare captures that differ in route, viewport, DPR, fonts, theme, content or animation state - the diff then measures the setup, not the build.

**Deterministic capture.** Before each capture, fix: CSS viewport and DPR (CDP `Emulation.setDeviceMetricsOverride` through browser-harness, matching the reference's), browser zoom at 100%, fonts finished loading (`document.fonts.ready`, and `document.fonts` confirming the intended faces rendered), theme and `prefers-reduced-motion`, animations and timers frozen or run to their end state, scroll position, open overlays and focus. Wait on a real ready signal (an element, a font, a data state), not a fixed sleep. Capture with browser-harness `capture_screenshot(path, full=...)` - first viewport for hierarchy, full page for rhythm, `zoom(...)` crops for type and small controls - in the run's evidence folder, never on the user's active tab (`new_tab`).

**Compare.** Side by side first, then an overlay or a pixel diff (Pillow `ImageChops.difference`, or OpenCV `absdiff` plus a threshold to box the coherent regions). Ignore scattered antialiasing noise; chase coherent shapes and repeated offsets. There is no universal pass percentage: rasterisation and fonts differ, so record the coherent differences that remain instead of a number.

**Correct one cause per pass**, the largest mismatch first, in this order - a fix higher up often clears dozens of apparent errors lower down:

1. Wrong route, content, data, theme or state.
2. Page shell, section order and height, container geometry.
3. Grid, alignment edges, overlaps, sticky offsets, dominant image placement.
4. Font files and real weights, scale, measure, line height, tracking, wrapping.
5. Image bounds, crop, focal point, masks.
6. Spacing rhythm.
7. Colour tokens, surfaces, borders, radii, shadows.
8. Icons, dividers, optical nudges.
9. Interaction states and motion timing.

Recapture under identical conditions after each fix and update the manifest row. A nontrivial rebuild gets at least two compare-and-correct passes, and continues while an ordinary viewer would spot a material difference at the target size. Hiding a defect with a global `overflow: hidden`, a screenshot overlay, or per-viewport coordinate hacks is a fail, not a fix. [D2C]

## The verdict

The build report ends with exactly one of:

- **READY** - every target, state and gate passes; what differences remain are immaterial.
- **READY WITH SUBSTITUTIONS** - every gate passes, but authorised substitutions remain; list each one and its visible effect (the ledger's Substituted rows).
- **NOT READY** - a target, state, gate or material mismatch still fails; name the blocker and the next action.
- **UNVERIFIED** - the build exists but the browser comparison could not run; the result is never called exact or pixel-perfect. [D2C]

The scope's gates from [gates.md](gates.md) still run on the built result as usual; this verdict is about fidelity to the reference, and does not replace them.
