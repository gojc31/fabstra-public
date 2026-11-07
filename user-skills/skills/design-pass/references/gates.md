# Gates

Sources: frontend-design is the Anthropic `frontend-design` plugin skill [FD]; the gate numbers are Hallmark's 58-gate slop test, MIT, Together AI, vendored at commit 13ac0ec7e148 [HM gate N]; the craft-floor checks are impeccable's [IMP]; the three default-style gates below are Anthropic, "Getting the most out of Opus 5.5" (2026-09-22) [AO55]; the motion-feel gates are Emil Kowalski's skills, MIT, commit 2d22863, as distilled in impeccable's `reference/motion-craft.md` [EMIL]. The dashboard-screen gates are taste-skill's `references/app-screens.md` (Leonxlnx/taste-skill, MIT, commit 6010f91a9935, read 2026-10-21; distilled from 23 real product screens) [TS]. The copy-and-detail gates marked [JC] are JC's house rules, adopted 2026-10-23. The gates marked [US] are adapted from unslop by Damir Sokolovsky (github.com/heydamir/unslop, CC BY 4.0, creativecommons.org/licenses/by/4.0, commit a6f121e, read 2026-11-05; reworded and changed for design-pass). The gates marked [CL] restate ideas from Charles Liu's reel "20 AI Design Slop Indicators" (Facebook, 2026-11-03) in our own words.

Checks are pass/fail on the BUILT result. The reviewer runs them, not the planner. A check that does not apply is written `N/A` with its number, never skipped silently.

Take the scope's subset into the blueprint block: PAGE takes every group; SCREEN drops nothing but reads Structure as the screen's layout rather than a landing rhythm; COMPONENT takes Type, Colour, Copy, States, Responsive, Motion, plus gates 6a-6d; EXISTING: Type, Colour, Copy, States, Responsive, Motion, Chrome; Structure only where the change adds a section; mark the rest N/A; Charts applies only when the surface carries data marks. Dashboard screens applies to a SCREEN or EXISTING pass on an app screen (dashboard, admin, analytics, settings, inbox, wallet) only where the project has no established look: a brand guide, DESIGN.md or INHERIT pass outranks every gate in it, and where they disagree the gate is `N/A (brand)`.

## Structure

1. The page shape is the macrostructure named in Direction, not hero then three cards then CTA then footer. [HM gate 8]
2. No card is nested inside another card, and identical cards are not the surface's only structural device. [HM gate 4] [IMP]
3. No eyebrow, kicker, or category label sits above a heading; the heading carries its own weight. [FD] [IMP]
4. Numbered markers (01 / 02 / 03) appear only where the content is a real sequence. [FD]
5. Nav and footer are not the AI defaults: a wordmark-left, inline-links, button-right nav over a hairline, or a four-link-column footer with a social row and a hairline. [HM gates 42, 43]
5a. Buttons are not fully pill-shaped (rounded to a stadium curve) as a default shape; a rounded corner radius is a Direction choice, named as such. [AO55]
6. Sections are separated by a decided device - a rule, a colour shift, real block space - not by identical gaps alone. [HM gate 9]
6a. Nested rounded areas are concentric: an inner element's corner radius equals the outer radius minus the padding between them (square once the padding reaches the outer radius). Icons, glyphs and labels align optically - an icon sits on the text's visual centre, a heading's left edge lines up with the body text under it. [JC]
6b. Dithered and ASCII-art imagery is not a default look; it is a Direction choice, named as such. [CL]
6c. A diagram carries only what the reader needs to follow it; detail added for texture fails. [CL]
6d. Metadata tag rows and coloured rounded icon tiles each do a job (filter, status, a real distinction); decorative ones fail. [CL]

## Type

7. Prose measure never exceeds 75ch at any width; at 768 and 1280 body prose reaches 60-75ch; at 375 it fills the available inline width minus gutters. [FD] [IMP]
8. No italic anywhere in the interface - headings, body, labels, captions, quotes or emphasis; emphasis comes from weight or colour, and only where gate 9 allows. [HM gate 38a] [JC]
9. No single word or phrase in a headline is accented by italic, bold, or a different colour. [FD]
10. Three font families at most, each with a named role. [HM gate 37]
10a. Monospace type is not used for labels, eyebrows, or UI chrome as a default, unless the content itself is code or data. [AO55]
11. Display type steps clearly above body in scale and weight, and every headline wraps inside its container at 375. [HM gate 51] [IMP]
11a. A surface uses four font sizes at most, three where the content allows, and none below 12px; further hierarchy comes from weight, colour and spacing. An overlay (drawer, dialog, popover) counts as its own surface. [JC]
11b. Instrument Serif is not a default face; using it is a Direction choice, named as such. [CL]
11c. Labels, table headers and captions are sentence case; uppercase tracked labels appear only where Direction names them. [US]

## Colour

12. Body text clears 4.5:1, and large text, icons, and focus rings clear 3:1, against their computed background. [HM gate 40]
13. Interactive text on its own fill keeps >= 4.5:1 in every state, including hover and disabled (disabled may drop to 3:1). [HM gate 41]
14. No gradient text anywhere, including `background-clip: text`. [HM gate 2] [IMP]
15. Black is black: a tinted near-black (#0B0B0B, #111) standing in for it is a default, not a choice. [FD]
15a. Cream or off-white is not the page background as a default; the ground colour is a Direction choice, named as such. [AO55]
16. Every colour and every `font-family` references a named token; no inline hex, `oklch()`, or font stack. [HM gate 48]

## Copy

17. Every number, testimonial, logo, and customer count is one the brief supplied, or a marked placeholder. [HM gate 46]
17a. Every record, field value, status name and named person or action is the brief's own, unrenamed; the action the brief names is the primary control where it appears. [JC]
18. An action keeps one name through the whole flow: the button that says Publish produces a toast that says Published. [FD]
19. Controls name what happens ("Save changes", not "Submit"); an error names the problem and the recovery. [FD] [IMP]
20. No placeholder names (Jane Doe, John Smith) and no startup clichés (Acme, Nexus, Unleash). [HM gate 19]
21. No `->` or `→` glyph is appended to link or button text. [FD]
21a. Inline items are separated by layout (a gap, a line break, a column) or plain punctuation (a comma; an en dash in a range); the middle dot `·` never serves as a separator. This governs rendered copy: code comments such as the Hallmark stamp at the top of the stylesheet are exempt, so a Verify grep for `·` searches the markup and the scripts' UI strings, never the stylesheet. [JC]
21b. Every line of copy does a job the label, heading or control cannot: no sentence that restates them or explains the obvious. Length fits the spot: a label is a few words. No helper, hint, explainer or "source" text under labels, fields, charts or sections; a short note appears only where without it the user would misread a number or make an error (a password rule, a unit, a destructive consequence), and then it is a few words. Words are the audience's own - plain, not chatty, no coined terms. [JC]
21c. Headlines, subheads, labels, buttons and captions end without a full stop; only copy of several sentences keeps them. A title's full stop passes only where Direction names it. [US]
21d. A change names what it compares to: `+12% vs last month`, never a bare `+12%`. [US]
21e. Numbers of one kind share one format across a screen: not `$48,210` beside `$124,860.40`. [US]

## States

22. Every interactive component ships all eight states: default, hover, focus-visible, active, disabled, loading, error, success. [HM gate 26]
23. Every screen ships its loading, empty, and error states with real copy, not a spinner alone. [IMP]
24. Focus is visible and instant - a ring at 3:1 or better that does not fade into existence. [HM gate 15]
24a. An OTP field submits on its last digit, sets `autocomplete="one-time-code"`, and gives feedback for each state (typing, checking, error, success). [CL]

## Responsive

25. No horizontal scroll at 375, 768, or 1280. A failure is reported with its cause, not hidden by clipping the root. [HM gate 34]
26. No button label, nav link, footer link, tab label, or CTA wraps to two lines at any of the three widths. [HM gate 49]
27. Every grid track holding an image is `minmax(0, 1fr)`, never a bare `1fr`. [HM gate 50]
28. The first viewport holds its essential content - headline, lede, primary action - at 1280x800 without scrolling. [HM gate 44]

## Motion

29. One authored motion moment, not a fade-and-slide entrance on every section. [FD] [IMP]
30. Every transform and every keyframe has a `prefers-reduced-motion: reduce` fallback. [HM gate 27]
31. No `transition: all`, no uniform hover-scale across unrelated elements, and no bounce or overshoot on UI state - menus, buttons, tooltips, modals, state changes - where nothing earned it. Exception: a momentum-driven gesture (a flick or drag release, drag-to-dismiss) may settle on a spring with bounce 0.1-0.3 (Apple: damping ~0.8), because the user's own momentum carries the overshoot. [HM gates 10-12] [EMIL]
31a. No UI element enters or exits on `ease-in`: both directions use an ease-out curve, and the exit runs shorter than the entrance; a component curve motion-craft names explicitly (e.g. the Sonner-style toast on 400 ms `ease`) passes. [EMIL]
31b. No entrance starts from `scale(0)`; an entrance that scales starts at `scale(0.9)`-`scale(0.97)` with `opacity: 0`. Translation-only entrances (a drawer or toast from `translateY(100%)`) and `clip-path` reveals pass. [EMIL]
31c. Popovers, dropdowns, menus and tooltips scale from their trigger (`transform-origin` at the trigger); modals stay centred. [EMIL]
31d. An action started from the keyboard, or one a user repeats 100+ times a day (a shortcut, Escape, the command palette toggle, arrow-key list navigation), changes state with no animation; a form field's focus state, reached by click or Tab alike, is not such an action. [EMIL]
31e. A component taken from a source moves exactly as it does on the source's own demo: `python -I D:\jc-ui-kit\scripts\motion-diff.py <upstream> <built>` exits 0 for each one (a port without the motion package may pass with `--allow-port`, its springs sampled into `linear()`), and only brand values differ. Gates 29 and 31-31d judge only motion built fresh. [JC]
31f. Every interactive element built fresh answers the pointer and the keyboard: a hover change, a press response, and an eased transition on every state change, within gates 31-31d. [JC]

## Chrome

32. No hand-drawn browser bar, phone frame, terminal, or IDE chrome: a real screenshot in a `<figure>`, or nothing. [HM gate 47]
33. The browser surfaces the design did not draw - selection, caret, scrollbar, focus ring, underline offset, tabular numerals - are themed from the palette. [IMP]
34. Every decorative element has a semantic anchor in the content; an ornament that means nothing is cut. [HM gate 45]

## Charts

35. One accent plus neutrals carries the series, and colour encodes a variable rather than decorating. [IMP]
36. No 3D, no donut spaghetti, no dual axes: the mark matches the comparison being made. [IMP]
37. A dashboard with more than one metric series uses one chart per series or a shared small-multiples grid; a single chart never carries more than 4 series. [IMP]

## Dashboard screens

38. Colour goes on data, status and the one primary action, never on chrome: coloured pixels stay near 5% of the screen or less, and the main data element carries the screen's one hue. [TS]
39. KPIs are type, not tiles: no icon in a tinted circle and no sparkline on a KPI; the largest figure answers the screen's one question and is read first. [TS]
40. Surfaces are flat: cards take a 1px line or one tone step, not a shadow. [TS]
41. No hero header on an app screen: the title is 24px or less, and no welcome line or greeting. [TS]
42. A single-series chart has no legend; gridlines are 3-7 faint lines or none. [TS]
43. Navigation recedes: the active item is a neutral grey fill or a text-colour change, not a coloured pill. [TS]
44. Tables are rules and alignment: no zebra striping, no header band, numbers right-aligned in tabular figures. [TS]
45. Data states are honest: a zero prints as 0, a missing value as a grey dash, an empty section keeps its frame; every total and change recomputes from the values as displayed. [TS]
46. The screen carries substance, not just restraint: the product's real data (or realistic sample data), every block the brief names on the first screen, and blocks that share the screen's left and right edges with no dead strip or card stopping short. [TS]
47. One chart leads: it is clearly the largest on the screen, and every other chart sits smaller. Data that needs no trend is a figure, a ranked list or a table, not another chart. Gate 37 still applies; a small-multiples grid counts as one chart. [US]
