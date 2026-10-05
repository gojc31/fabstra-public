# Gates

Sources: frontend-design is the Anthropic `frontend-design` plugin skill [FD]; the gate numbers are Hallmark's 58-gate slop test, MIT, Together AI, vendored at commit 13ac0ec7e148 [HM gate N]; the craft-floor checks are impeccable's [IMP]; the three default-style gates below are Anthropic, "Getting the most out of Opus 5.5" (2026-09-22) [AO55].

Checks are pass/fail on the BUILT result. The reviewer runs them, not the planner. A check that does not apply is written `N/A` with its number, never skipped silently.

Take the scope's subset into the blueprint block: PAGE takes every group; SCREEN drops nothing but reads Structure as the screen's layout rather than a landing rhythm; COMPONENT takes Type, Colour, Copy, States, Responsive, Motion; EXISTING: Type, Colour, Copy, States, Responsive, Motion, Chrome; Structure only where the change adds a section; mark the rest N/A; Charts applies only when the surface carries data marks.

## Structure

1. The page shape is the macrostructure named in Direction, not hero then three cards then CTA then footer. [HM gate 8]
2. No card is nested inside another card, and identical cards are not the surface's only structural device. [HM gate 4] [IMP]
3. No eyebrow, kicker, or category label sits above a heading; the heading carries its own weight. [FD] [IMP]
4. Numbered markers (01 / 02 / 03) appear only where the content is a real sequence. [FD]
5. Nav and footer are not the AI defaults: a wordmark-left, inline-links, button-right nav over a hairline, or a four-link-column footer with a social row and a hairline. [HM gates 42, 43]
5a. Buttons are not fully pill-shaped (rounded to a stadium curve) as a default shape; a rounded corner radius is a Direction choice, named as such. [AO55]
6. Sections are separated by a decided device - a rule, a colour shift, real block space - not by identical gaps alone. [HM gate 9]

## Type

7. Prose measure never exceeds 75ch at any width; at 768 and 1280 body prose reaches 60-75ch; at 375 it fills the available inline width minus gutters. [FD] [IMP]
8. Headings and display type are roman; no italic header, and no italicised emphasis word inside an upright one. [HM gate 38a]
9. No single word or phrase in a headline is accented by italic, bold, or a different colour. [FD]
10. Three font families at most, each with a named role. [HM gate 37]
10a. Monospace type is not used for labels, eyebrows, or UI chrome as a default, unless the content itself is code or data. [AO55]
11. Display type steps clearly above body in scale and weight, and every headline wraps inside its container at 375. [HM gate 51] [IMP]

## Colour

12. Body text clears 4.5:1, and large text, icons, and focus rings clear 3:1, against their computed background. [HM gate 40]
13. Interactive text on its own fill keeps >= 4.5:1 in every state, including hover and disabled (disabled may drop to 3:1). [HM gate 41]
14. No gradient text anywhere, including `background-clip: text`. [HM gate 2] [IMP]
15. Black is black: a tinted near-black (#0B0B0B, #111) standing in for it is a default, not a choice. [FD]
15a. Cream or off-white is not the page background as a default; the ground colour is a Direction choice, named as such. [AO55]
16. Every colour and every `font-family` references a named token; no inline hex, `oklch()`, or font stack. [HM gate 48]

## Copy

17. Every number, testimonial, logo, and customer count is one the brief supplied, or a marked placeholder. [HM gate 46]
18. An action keeps one name through the whole flow: the button that says Publish produces a toast that says Published. [FD]
19. Controls name what happens ("Save changes", not "Submit"); an error names the problem and the recovery. [FD] [IMP]
20. No placeholder names (Jane Doe, John Smith) and no startup clichés (Acme, Nexus, Unleash). [HM gate 19]
21. No `->` or `→` glyph is appended to link or button text. [FD]

## States

22. Every interactive component ships all eight states: default, hover, focus-visible, active, disabled, loading, error, success. [HM gate 26]
23. Every screen ships its loading, empty, and error states with real copy, not a spinner alone. [IMP]
24. Focus is visible and instant - a ring at 3:1 or better that does not fade into existence. [HM gate 15]

## Responsive

25. No horizontal scroll at 375, 768, or 1280. A failure is reported with its cause, not hidden by clipping the root. [HM gate 34]
26. No button label, nav link, footer link, tab label, or CTA wraps to two lines at any of the three widths. [HM gate 49]
27. Every grid track holding an image is `minmax(0, 1fr)`, never a bare `1fr`. [HM gate 50]
28. The first viewport holds its essential content - headline, lede, primary action - at 1280x800 without scrolling. [HM gate 44]

## Motion

29. One authored motion moment, not a fade-and-slide entrance on every section. [FD] [IMP]
30. Every transform and every keyframe has a `prefers-reduced-motion: reduce` fallback. [HM gate 27]
31. No `transition: all`, no uniform hover-scale across unrelated elements, no bounce or overshoot easing on UI state. [HM gates 10-12]

## Chrome

32. No hand-drawn browser bar, phone frame, terminal, or IDE chrome: a real screenshot in a `<figure>`, or nothing. [HM gate 47]
33. The browser surfaces the design did not draw - selection, caret, scrollbar, focus ring, underline offset, tabular numerals - are themed from the palette. [IMP]
34. Every decorative element has a semantic anchor in the content; an ornament that means nothing is cut. [HM gate 45]

## Charts

35. One accent plus neutrals carries the series, and colour encodes a variable rather than decorating. [IMP]
36. No 3D, no donut spaghetti, no dual axes: the mark matches the comparison being made. [IMP]
37. A dashboard with more than one metric series uses one chart per series or a shared small-multiples grid; a single chart never carries more than 4 series. [IMP]
