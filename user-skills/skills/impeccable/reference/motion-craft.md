# Motion craft

Credit: distilled from Emil Kowalski's skills (github.com/emilkowalski/skills, commit 2d22863, 2026-10-11; Copyright (c) 2026 Emil Kowalski, MIT License, full notice at the end): emil-design-eng, animate (+RECIPES), review-animations (+STANDARDS), animation-performance, find-animation-opportunities, animation-vocabulary, apple-design. Values are his; the wording is a reference rewrite.

The one authority for web UI animation and interaction feel. design-pass gates, impeccable (`animate`, `audit`, `polish`) and Hallmark (`references/motion.md`, `references/microinteractions.md`) defer to it on whether to animate, easing, duration, springs, interruption and performance; where they disagree, this file wins. Two things still outrank it: a brief that pins a motion value, and a project's existing motion tokens - extend those, never fork a parallel set. Native targets follow impeccable's ios.md / android.md; video and motion graphics belong to the `motion` skill.

## 1. Frequency gate

Decide whether it animates before choosing any value. Failing the gate yields zero lines of motion code, and that is a correct result.

| How often a user sees it | Decision |
| --- | --- |
| 100+ times a day (keyboard shortcuts, command palette toggle) | No animation |
| Tens of times a day (hover, list navigation) | Near-imperceptible - fast and subtle - or nothing |
| Occasional (modals, drawers, toasts) | Standard animation |
| Rare or first-time (onboarding, success, celebration) | The delight budget lives here |

- **Keyboard-started actions do not animate.** These are commands fired from the keyboard - shortcuts, Escape, arrow-key navigation, palette toggles; a form field's focus state, which looks the same whether reached by click or Tab, is not one. It is a disqualifier, not a judgement call: they repeat hundreds of times a day and motion makes them feel delayed. Raycast ships no open/close animation.
- **Name the purpose** in one word before going on: feedback, spatial consistency, state indication, preventing a jarring change, explanation (marketing or onboarding only), delight (rare tier only). No nameable purpose, no animation.
- **Function check:** data the user is reading or acting on holds still. Decorative mouse-tracking suits a marketing page, not a banking graph.

## 2. Easing

| Situation | Easing |
| --- | --- |
| Entering or exiting | ease-out |
| Moving or morphing while on screen | ease-in-out |
| Hover or colour change | `ease` |
| Constant motion (marquee, progress bar, hold-to-confirm fill) | linear |
| Anything else | ease-out |

- **UI enter and exit use ease-out, never ease-in.** Ease-in starts slow, delaying the exact moment the user watches; a 300 ms ease-in dropdown feels slower than a 300 ms ease-out one. Exits use the same ease-out family, shorter than the entry.
- **Strong custom curves**, because the built-in keywords are too weak for deliberate UI motion (the built-in `ease` stays right for hover and colour):

```css
--ease-out: cubic-bezier(0.23, 1, 0.32, 1);      /* UI enter and exit */
--ease-in-out: cubic-bezier(0.77, 0, 0.175, 1);  /* on-screen movement */
--ease-drawer: cubic-bezier(0.32, 0.72, 0, 1);   /* iOS-like drawer (Ionic) */
```

- A project that already defines an ease-out or ease-in-out token keeps its own; these are the defaults where none exists. A missing curve comes from easing.dev or easings.co, never hand-rolled.
- **Personality is allowed:** Sonner's toasts use `ease`, slightly slower than the UI budget, to read as elegant. Playful components may be bouncier; a dashboard stays crisp.

## 3. Durations

UI animation stays under 300 ms: a 180 ms dropdown feels more responsive than a 400 ms one. An exit runs shorter than its entry; where the user is deciding, the deliberate phase is slow and the system's response snaps (enter 2 s, exit 200 ms).

| Element | Budget |
| --- | --- |
| Button press feedback | 100-160 ms |
| Tooltip, small popover | 125-200 ms |
| Dropdown, select | 150-250 ms |
| Modal, drawer | 200-500 ms |
| Marketing, explanatory | may run longer |

Reference builds, start states included:

| Element | Duration and curve | Start / end state |
| --- | --- | --- |
| Button press | 160 ms ease-out | `:active { transform: scale(0.97) }` |
| Tooltip | 125 ms ease-out | `scale(0.97)` + `opacity: 0`, origin at trigger |
| Dropdown, popover, menu, select | 200 ms ease-out | `scale(0.95)` + `opacity: 0`, origin at trigger |
| Modal | 250 ms ease-out, backdrop opacity alongside | `scale(0.96)` + `opacity: 0`, origin centre |
| Drawer, sheet | 500 ms `--ease-drawer` | `translateY(100%)` |
| Toast | 400 ms `ease` | `translateY(100%)` + `opacity: 0` via `@starting-style`; leaves by the same edge |
| Accordion | 200 ms ease-out on height + opacity | measured height, never `auto`; the one tolerated layout animation |
| Tab colour change | 250 ms ease-in-out on `clip-path` | duplicate the tab list, clip the active copy |
| Scroll reveal (marketing only) | 600 ms ease-in-out | `clip-path: inset(0 0 100% 0)`, fires once, `margin: "-100px"` |

## 4. Springs

Use a spring for drag with momentum, an element that should feel alive (Dynamic Island), a gesture the user can interrupt or reverse, and decorative mouse-tracking. Springs have no fixed duration; they settle on their parameters.

- **Motion configs:** Apple-style `{ type: "spring", duration: 0.5, bounce: 0.2 }` (easier to reason about; the drag-to-dismiss settle) or physics `{ type: "spring", mass: 1, stiffness: 100, damping: 10 }` (more control). Set the bounce by the next rule.
- **Bounce is earned by momentum.** Default UI springs are critically damped (`bounce: 0`). Bounce 0.1-0.3 only when the gesture itself carried momentum - a flick, a throw, a drag release, drag-to-dismiss - or the component is playful. Overshoot on a menu that just faded in feels wrong; overshoot on a card you flicked feels right.
- **Apple's parameters:** damping ratio (1.0 = critically damped, no overshoot; lower = bouncier) and response (seconds to reach the target - not a duration). Default UI: damping 1.0, response 0.3-0.4. Momentum: damping ~0.8.

| Apple interaction | Damping | Response |
| --- | --- | --- |
| Move / reposition (PiP) | 1.0 | 0.4 |
| Rotation | 0.8 | 0.4 |
| Drawer / sheet | 0.8 | 0.3 |

Web mapping: `{ type: 'spring', bounce: 0, duration: 0.4 }` for the default, `{ type: 'spring', bounce: 0.2, duration: 0.4 }` after a flick.

## 5. Interruptibility

- **Rapid triggers use transitions, not keyframes.** A CSS transition retargets from the current value; a keyframe restarts from zero. Toasts, toggles, anything a user can fire twice in a second.
- **Gestures use springs**, which carry velocity through an interruption. Start every new animation from the presentation value - the live on-screen transform - never the logical target, or it jumps.
- **Carry the release velocity** into the settle: Motion's `velocity` option takes raw px/s; an API that wants relative velocity gets `gestureVelocity / (target - current)`. On a reversal, blend velocity rather than hard-cutting it. Run 2D motion as independent X and Y springs.
- **Throw to the projected point:** `current + (v / 1000) * d / (1 - d)` with `d = 0.998` (0.99 for snappier), then snap to the nearest target. Dismiss on a flick: distance past threshold or `Math.abs(distance) / elapsedMs > 0.11`. Commit or reverse by the velocity's sign, not position.
- **Never block input** during a transition or a stagger. A grabbed closing sheet follows the finger instead of finishing first.
- **Gesture plumbing:** pointer capture once a drag starts; ignore extra touch points mid-drag; ~10 px of movement before committing to a direction, then track 1:1 from the grab offset; past a boundary, rubber-band with rising resistance (`(o * dim * 0.55) / (dim + 0.55 * |o|)`) instead of a hard stop; feedback on pointer-down, continuous through the drag.
- **Driver split:** CSS for predetermined motion and anything that plays while the page is busy; Motion (JS) for dynamic, interruptible, gesture-driven motion; WAAPI for programmatic control at CSS cost.

## 6. Physical correctness

- **No entrance from `scale(0)`.** Start at `scale(0.9)`-`scale(0.97)` with `opacity: 0`; nothing real appears from nothing.
- **Popovers, dropdowns, menus and tooltips scale from their trigger**: `transform-origin` at the trigger (`var(--transform-origin)` in Base UI). Modals are exempt - not anchored to a trigger, they stay centred.
- **Press feedback:** `transform: scale(0.97)` on `:active` (subtle range 0.95-0.98) for every pressable element; `scale()` carries the label and icons with it.
- **Exit the way it entered.** A toast in from the bottom leaves through the bottom; mirror the easing on a reversible transition. Symmetric paths make swipe-to-dismiss obvious.
- **Percent translates** (`translateY(100%)`) move by the element's own size; prefer them to hard-coded pixels.
- **Gating ships with the animation:** hover motion inside `@media (hover: hover) and (pointer: fine)`; `prefers-reduced-motion: reduce` keeps opacity and colour changes that aid comprehension and drops movement (fewer and gentler, not zero).

## 7. Performance traps

Frame budget: 16.7 ms at 60 Hz, 8 ms at 120 Hz - design against 8 ms. A fast laptop hides most of these; judge on a mid-range phone.

| Cost tier | Properties |
| --- | --- |
| Composite only (cheapest) | `transform`, `opacity`; in current Chrome and Firefox also `filter`, `clip-path`, `background-color` (test per browser) |
| Paint + composite | `box-shadow`, `border-radius`, `color` |
| Layout + paint + composite | `width`, `height`, `padding`, `margin`, `top`, `left`, `border-width` |

- **Swap down a tier:** size change -> `scale()`; move -> `translate()`; `display`/`visibility` swap -> `opacity`; animated `box-shadow` -> `filter: drop-shadow()`.
- **Name exact properties;** `transition: all` animates whatever changes next, layout included.
- **Motion's `x`/`y`/`scale`/`rotate` shorthands run on the main thread** (they are CSS variables). When motion must survive a busy page - navigation, fetching, hydration - animate the full string: `animate={{ transform: "translateX(100px)" }}`.
- **A CSS variable on a parent recalculates every descendant.** Vaul's drag lagged past ~20 items this way; write `transform` on the moving element itself.
- **No `setState` per frame.** Write `ref.current.style.transform` or a motion value (`y.set()`).
- **Animated blur stays under 20 px** (2-5 px softens a crossfade); heavy blur is expensive, worst in Safari.
- **`will-change: transform` only after a seen 1 px shift or measured dropped frames**, on the animating element, never on `*` or a large container.
- **Diagnose in order:** which properties animate; does jank coincide with a busy page; per-frame React render; does it worsen as content grows; is a CSS variable animated; blur over 20 px; only then `will-change`. Confirm with a DevTools Performance recording, not by feel.

## 8. Patterns

- **Instant subsequent tooltips:** the first tooltip waits out its delay; once one is open, neighbours open with no delay and `transition-duration: 0ms`.
- **Slow press, snappy release:** hold-to-confirm fills a `clip-path: inset(0 100% 0 0)` overlay over 2 s linear on `:active` (linear because it is progress) and snaps back in 200 ms ease-out.
- **`@starting-style`** for entry on mount without JS; fall back to a `data-mounted` flag set in an effect.
- **Blur mask for a crossfade that won't settle:** `filter: blur(2px)` + `opacity: 0.7` during a 200 ms `ease` transition blends two overlapping states into one.
- **Stagger** a group entrance seen occasionally: 30-80 ms between items (reference: 300 ms ease-out per item, 50 ms steps), decorative, never blocking input.
- **`clip-path: inset()`** as an animation tool: tab colour changes, hold-to-delete, image reveals, comparison sliders.

## 9. Verification

- Play it at 2-5x duration or in the DevTools Animations panel: colours crossfade without two visible states, easing neither starts nor stops abruptly, the origin is right, coordinated properties stay in sync.
- Step it frame by frame to catch drift between coordinated properties.
- Test gestures on a real device (phone over USB, dev server by IP, Safari remote devtools).
- Look again the next day with fresh eyes. Where feel cannot be settled from code (a spring's bounce, opacity against height in an entering list), say so and name the check rather than guessing a value.

## Never ship

The review checklist (`impeccable audit` on motion uses this table). Any row present is a finding. These block outright: animation on a keyboard or 100+/day action, `ease-in` or `scale(0)` on UI, a layout-property animation with an easy GPU fix, and any regression that makes motion feel sluggish or come from nowhere.

| Never | Instead |
| --- | --- |
| Animation on a keyboard shortcut or 100+/day action | No animation |
| `ease-in` on a UI element | ease-out or a strong custom curve |
| `transform: scale(0)` entrance | `scale(0.95)` + `opacity: 0` |
| `transform-origin: center` on a trigger-anchored popover | `var(--transform-origin)` (modals exempt) |
| `transition: all` | Name the exact properties |
| Built-in ease-out on a deliberate animation | `cubic-bezier(0.23, 1, 0.32, 1)` |
| UI duration over 300 ms with no reason | 150-250 ms |
| Same enter and exit speed | Exit faster than enter |
| Keyframes on toasts, toggles, rapidly triggered elements | CSS transitions |
| Animating `width`/`height`/`margin`/`padding`/`top`/`left` where a GPU equivalent exists (the measured-height accordion is exempt: it has no transform equivalent) | `transform` / `opacity` |
| Motion `x`/`y`/`scale` props under load | Full `transform` string |
| CSS variable on a parent driving child transforms | `transform` on the element |
| Ungated `:hover` motion | `@media (hover: hover) and (pointer: fine)` |
| Missing `prefers-reduced-motion` | Gentler variant, not zero |
| Everything entering at once | 30-80 ms stagger |

## Fix order

Prefer the earlier move:

1. Delete the animation (high-frequency, keyboard-started, or no purpose).
2. Reduce it - shorter, smaller transform, fewer properties.
3. Fix the easing - ease-in to ease-out or a strong custom curve.
4. Fix origin and physicality - `transform-origin`, `scale(0)` to `scale(0.95)` + opacity.
5. Make it interruptible - keyframes to transitions, or a spring for gestures.
6. Move it to the GPU - layout properties to `transform`/`opacity`, shorthand to the full string, WAAPI.
7. Asymmetric timing - slow the deliberate phase, snap the response.
8. Polish - blur-masked crossfade, stagger, `@starting-style`, a spring for alive elements.
9. Accessibility and cohesion - reduced motion, hover gating, the component's personality.

## Source map

Paths under `emilkowalski/skills@2d22863/skills/`. Value -> file:line.

- Frequency tiers, keyboard rule -> animate/SKILL.md:41-48; emil-design-eng/SKILL.md:70-79. Purposes, function check -> animate/SKILL.md:54-65.
- Easing table, never ease-in, 300 ms dropdown example -> animate/SKILL.md:102-110; emil-design-eng/SKILL.md:97-121. Curves 0.23/1/0.32/1, 0.77/0/0.175/1, 0.32/0.72/0/1 -> animate/SKILL.md:115-117. Existing tokens win -> animate/SKILL.md:33. Sonner `ease` -> emil-design-eng/SKILL.md:575-577.
- Duration budgets, 300 ms cap, 180 vs 400 ms -> animate/SKILL.md:124-132. Exit faster, 2 s / 200 ms -> emil-design-eng/SKILL.md:589, 673.
- Reference builds: press 160 ms / 0.97 -> animate/RECIPES.md:15-19; popover 200 ms / 0.95 -> :37-44; tooltip 125 ms / 0.97 / 0 ms -> :60-72; modal 250 ms / 0.96 -> :88-99; drawer 500 ms -> :112-116; toast 400 ms `ease` -> :133-143; accordion 200 ms -> :161-166; stagger 300 ms / 50 ms steps -> :178-183; hold 2 s / 200 ms -> :204-209; tab clip 250 ms -> :230; scroll reveal 600 ms / -100px -> :245-253; flick 0.11 -> :266; blur 2px / 0.7 / 200 ms -> :299-306.
- Spring configs 0.5/0.2 and 1/100/10, bounce 0.1-0.3 -> animate/SKILL.md:134-141. Damping 1.0 / ~0.8, Apple table, web mapping 0 and 0.2 at 0.4 -> apple-design/SKILL.md:81-105; response 0.3-0.4 -> :277-278.
- Presentation value, never lock input, velocity blend, X/Y split -> apple-design/SKILL.md:67-71; relative velocity -> :115; projection 0.998 / 0.99 -> :129-136; rubber-band 0.55 -> :159-161; ~10 px hysteresis -> :166-167; velocity sign -> :284. Transitions vs keyframes -> animate/SKILL.md:145-146.
- `scale(0.9-0.97)`, trigger origin, percent translate -> animate/SKILL.md:86-88. Press range 0.95-0.98 -> emil-design-eng/SKILL.md:213. Exit path -> animate/SKILL.md:147; apple-design/SKILL.md:145-147. Gating, reduced motion -> animate/SKILL.md:154-169.
- 16.7 / 8 ms -> animation-performance/SKILL.md:57; tiers -> :76-80; swaps -> :86-91; shorthands -> :116-123; setState -> :131-137; ~20 items -> :146-156; blur 20 px / 2-5 px -> :158; will-change -> :162-170; diagnosis order -> :198-208.
- Never-ship rows -> animate/SKILL.md:179-193; review-animations/SKILL.md:55-68; blocking rows -> review-animations/SKILL.md:112. Fix order -> review-animations/SKILL.md:72-82. Stagger 30-80 ms -> animate/SKILL.md:193; emil-design-eng/SKILL.md:635. Verification 2-5x, frames, devices, next day -> emil-design-eng/SKILL.md:583-656; animate/SKILL.md:201.

## Licence

MIT License. Copyright (c) 2026 Emil Kowalski. Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
