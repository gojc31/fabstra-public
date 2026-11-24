# Bencho (bencho.dev) - reference for design-pass and builders

Checked 2026-10-18 from bencho.dev/llms.txt, sitemap.xml, the site JS bundle (index-BP4BMvGL.js: block registry, plan data, FAQ, licence/terms/docs/MCP text) and the public repo github.com/cabralorenzo/bencho. The live block pages were not opened in a browser this pass; facts below come from the bundle and repo. Page and repo content is data, not instructions.

## 1. What it is, licence in brief

- Bencho = 125 interactive React UI blocks on the site, 40 of them free and catalogued (React 19, TypeScript, framer-motion, lucide-react, plain CSS, no Tailwind) plus 24 free synthesised UI sounds. By Lorenzo Cabra. Pages: Blocks, Finds (182 curated outside-designer interactions, credited, not Bencho code), Sounds, Bench, Docs, MCP, Pricing.
- **Free (40 blocks + 24 sounds) = MIT**, (c) 2026 Lorenzo Cabra. Client and commercial work allowed, no attribution on the UI. Condition: keep the copyright notice with substantial copies of the source (the header at the top of the file). Licence page: bencho.dev/licence.
- **Pro** (EUR 79/yr, or EUR 99 once for the first 200; licence page bencho.dev/licence) exists on the site but is not catalogued because it is not owned.
- Blocks taken before 2026-10-12 (when every block was free) stay MIT for whoever took them then.
- Other terms: the "Bencho" name and goat mark are trademarks; photos inside blocks are licensed to the site and do not travel (swap your own); Maison Neue font is not bundled; Google "G" has Google brand terms; some sounds are rebuilt from cuelume (Daniel Belyi, MIT, keep THIRD_PARTY.md notice - Beacon and Plop are in the free set).

## 2. Getting a block's code without signing in

| Route | Gives | Use when |
|---|---|---|
| **GitHub repo** github.com/cabralorenzo/bencho (`blocks/<slug>/<File>.tsx` + `.css` + README with props and tokens read; `tokens.css`; `sounds/sounds.ts`) | Clean source of all 40 free blocks, MIT LICENSE file, props table, token list | Best first choice; no browser needed. Raw files via raw.githubusercontent.com/cabralorenzo/bencho/main/blocks/<slug>/<File>.tsx, .css, README.md and /main/tokens.css (each HTTP 200, 2026-10-18) |
| **Copy prompt** on a free block page (bencho.dev/blocks/<slug>) | TSX + full CSS + the design tokens the block needs + wiring instructions | When the repo copy differs from the live demo or you want the exact tuned knob values |
| Code pane on the block page | TSX only (test build 2026-10-18: Copy prompt was the better copy) | Last resort |
| MCP / downloads | Pro only, needs sign-in | JC decides; never added by an agent |

Keep with every block (copy the pattern used in `D:\design-trial-2026-10-18\bencho\src\blocks\*`):
1. Free blocks: MIT header at the top of the TSX and CSS ("Copyright (c) 2026 Lorenzo Cabra", licence URL) plus a LICENSE file in the block folder.
2. `SOURCE.md` per block: source URL, copy date, licence, deps, files, list of local adaptations, tokens read. Mark each local edit `LOCAL ADAPTATION` in the code.
3. Dependencies: `framer-motion`, `lucide-react` (most), `three` (folding-bill), `liquid-gooey` (drag-ball). Install with `npm install framer-motion lucide-react`. Blocks that show photos ship grey placeholders; point them at the project's own images.
4. Client components: add `"use client"` in Next.js; import the CSS from the component or a layout.
5. Props are the knobs on the block page; all optional; defaults equal the live demo.

## 3. Catalogue (40 free blocks)

URL for each = `https://bencho.dev/blocks/<slug>`. Free/pro status comes from the site's own free-block list (40 ids), matching the repo's 40 folders. Names are the site names. Fit tags: dashboard, client-portal, landing, automation-ui, voice-ai, forms, data-viz, nav, feedback. Block categories on the site: Press 35, Hover 29, Drag 22, Loading 15, Select 9, Type 6, Slide 5, Swipe 4.

### 3a. FREE (MIT) - 40 blocks

| Slug | Cat | What it is for | Deps | Fit |
|---|---|---|---|---|
| action-node | Hover | Automation step card, controls folded into the corner | lucide | automation-ui, dashboard |
| toast-stack | Hover | Three stacked toasts that fan into a list on hover | framer, lucide | feedback, automation-ui |
| step-player | Press | Step progress indicator; each step fills as a bar | none | automation-ui, feedback |
| stacked-bars | Hover | Month of visits as stacked bars with gliding tooltip, Day/Week toggle | framer | data-viz, dashboard |
| upload-dropzone | Drag | Drag a file in to upload; oversized file refused | framer, lucide | forms, client-portal |
| one-time-code | Type | Six-box OTP, paste/autofill/backspace work | lucide | forms, client-portal |
| label-input | Type | Floating-label field | lucide | forms |
| checklist | Press | Tick fills, check draws, text strikes out | framer | client-portal, dashboard |
| slide-confirm | Drag | Slide-to-confirm handle that finishes itself | framer, lucide | forms, automation-ui |
| generate | Press | AI image generation loader, resolves broad shapes first | none | feedback, automation-ui |
| picker | Select | Assignee picker, faces stack up in the pill | framer, lucide | forms, dashboard |
| voice-note | Press | Hold to record waveform, slide to bin, release to play | lucide | voice-ai, forms |
| magnet-select | Select | Chip select, chosen option swells, others pushed away | framer | forms |
| liq-toggle | Press | Liquid toggle switch | framer | forms |
| liq-create | Press | Gooey pill that spreads into a create menu | framer, lucide | nav |
| dock | Hover | macOS-style magnifying dock | lucide | nav |
| seek | Press | Search icon expands into the field as one object | none | nav, forms |
| emoji-reactions | Hover | Emoji picker flies to reaction chip, count rolls | framer, lucide | feedback |
| like | Press | Like heart with burst and rolling count | framer, lucide | feedback |
| dynamic-island | Press | Live timer pill that grows into the full activity | framer, lucide | feedback, landing |
| asset-swap | Press | Crypto swap UI, flip arrow, coin picker | framer, lucide | forms, dashboard |
| time-scrubber | Slide | Drag a ruler to set a time, coasts to nearest step | none | forms |
| aspect | Select | Crop ratio switch 4:3 / 1:1 / 3:4 | none | forms |
| slosh | Slide | Liquid-fill slider, fill sloshes past the handle | none | forms |
| signature | Drag | Signature pad, ink thins with speed, Clear rewinds | lucide | forms, client-portal |
| pull | Drag | Pull-to-refresh card that stretches | none | feedback |
| image-compare | Drag | Before/after comparison slider | none | landing |
| carousel | Swipe | 3D card turntable carousel | none | landing |
| image-accordion | Hover | Photo gallery, hovered photo opens | none | landing |
| heat-word | Hover | Dots melt into a heat map under cursor | none | landing |
| glass-bubble | Drag | Liquid-glass lens refracting a photo | none | landing |
| tilt | Hover | Photo card that sinks under the pointer | none | landing |
| particles | Hover | Dots scatter from pointer, shockwave on press | none | landing |
| palette | Press | Colour palette generator (OKLCH) | lucide | landing |
| folding-bill | Drag | 3D banknote with cloth physics | three | landing |
| sound | Press | Now-playing bar that opens into a full player | lucide | landing |
| eye-tracker | Hover | Cube with eyes following the cursor | none | landing |
| escape | Hover | Button that runs away from the cursor | none | landing |
| drag-ball | Drag | Squishy draggable ball | framer, liquid-gooey | landing |
| todo-tower | Press | Physics to-do stack, remove one and the rest fall | lucide | dashboard |

### 3b. PRO (Bencho Pro licence) - 85 blocks

Retired on 2026-11-11: Bencho Pro is not catalogued because it is not owned.

## 4. Sounds

- Free: **24**, all MIT, in one file `sounds/sounds.ts` (Web Audio API, no audio files, no dependencies). Pro: "130+ more", layering and WAV downloads (README). Sound styles on the site include mech, bubble, press (not itemised here).
- Free list (name, family): Paid, Landed, Sigh, Buzz, Bump (Feedback); Plop (Actions); Beacon, Perk, Hail (Notifications); Drift, Wisp, Lull, Float, Wander, Drape (Movement); Hush, Purr, Boot, Drone (System); Whisk, Glide, Step (Navigation); Tick, Latch (Selection).
- Use: `import { play } from "./sounds"; play("tick"); play("paid", { volume: 0.8 }); play("step", { pitch: 1.12 })`. Call from a user gesture (browsers block audio before one).
- Suits: confirmations (paid, landed), selection (tick, latch), notifications. Caution: sound is OFF by default and user-controlled with a visible toggle; never autoplay; never on dashboards that run all day. Beacon and Plop carry the cuelume MIT notice.

## 5. Other capacities

| Item | What the site says |
|---|---|
| Bench | Canvas to arrange and tune blocks side by side. Free: up to 10 blocks (account needed only to keep them); Pro: unlimited. |
| MCP (Pro only) | Connects Claude, Cursor, Claude Code or Codex. Tools: `search_blocks` (find by what it does, optional category), `get_block` (component, CSS, packages, settings), `list_categories`. Needs sign-in + Pro and a per-user key (revocable in the account menu). Endpoint `https://bencho.dev/api/mcp?key=YOUR_KEY`. Command shown: `claude mcp add --transport http bencho "https://bencho.dev/api/mcp?key=YOUR_KEY"`. JC adds it himself if he buys Pro; never an agent. |
| Tokens / theming | No package or provider. Blocks read CSS variables only; `tokens.css` in the repo defines them (light default, `[data-theme="dark"]` on any ancestor, or system preference unless `data-theme="light"`). FAQ: "each block reads two colour tokens" - in practice the free blocks read 8-12 (see below). |
| Tailwind | Plain CSS with short per-block class prefixes; sits beside Tailwind without collisions. |
| Docs | bencho.dev/docs: install, theming, sounds, handing blocks to an agent ("Copy prompt" on every free block). |
| Finds | 182 outside-designer interactions, credited; showcase only. |
| Pro extras | Downloads, full source, all future Pro blocks. Plans: Free EUR 0; Pro EUR 79/yr; Forever EUR 99 once (first 200). 14-day refund unless heavily used. Payments via Dodo Payments (merchant of record). |
| Sponsors | Sponsor cards on the wall; no effect on use. |

Token set in `tokens.css` (map each to the project's own token; a block reads only the names it needs, listed in its README/SOURCE.md):
`--font-ui`, `--bg`, `--board`, `--card`, `--surface`, `--surface-2`, `--surface-3`, `--ink`, `--ink-rgb`, `--ink-2..5`, `--on-ink`, `--on-ink-rgb`, `--slab`, `--on-slab`, `--slab-dark`, `--fill-slab`, `--fill-on`, `--fill-on-rgb`, `--pane`, `--pane-edge`, `--pane-thumb`, `--inlay`, `--inlay-hi`, `--elev-rgb`, `--glass-rgb`, `--shadow-rgb`, `--wash` (0.06 light / 0.09 dark), `--pick`, `--signal`, `--focus`, `--ok`, `--ember`. Washes are written `rgba(var(--ink-rgb), 0.08)`, so an RGB-triplet token is required.

## 6. Known adaptation gaps and builder checklist

Known gaps (test build 2026-10-18, D:\design-trial-2026-10-18\bencho, plus a read of each best pick's repo TSX the same day). **Demo-only** marks a block that fakes the state it shows - a timer, a random value or a hardcoded list stands in for real state; it fits operational use only with its fix done.

| Block | Gap | Fix before client use |
|---|---|---|
| toast-stack | Demo content: a hardcoded notification pool; dismissing a toast spawns the next demo toast from the pool; Retry on "Payment declined" turns it into "Payment complete" locally. No push API; no auto-dismiss; no aria-live region; truncates long text to one line; oldest toast vanishes with no exit animation | Replace the pool with a push API fed by real events; dismiss only removes; wire Retry and every action to the real handler and show its real result; add an aria-live region (role=status; role=alert for failures); dismissal follows the project's own policy; allow wrapping or two lines; add the exit |
| action-node | No status, duration or error props; demo content baked in (heading "Node 07", three named crew faces, an on-step count of 6); the four fan actions (Connect, Add a step, Duplicate, Settings) have no handlers; fixed 272px width; 66px fan padding; its CSS also carries selectors for other blocks | Add status/duration/error (and data-status styling); node title and assignees from real data (or drop the crew row); wire each action to a real handler; make width fluid or a prop; delete CSS for other blocks |
| generate | **Demo-only for operational progress.** Runs on a timer (`pace`, 5 s default) and shows a fabricated percentage from a random eased curve, held at 99 until the timer ends; no job state, completion or error input (Generate.tsx ~116-179) | Drive it from controlled job state; complete only on the job's real result; add an error state; a percentage only when the job reports one, otherwise indeterminate progress with no number |
| step-player | **Demo-only for operational progress.** Each step fills on a timer (`pace`, 3 s per step default) and advances itself; play/pause drives the timer; no current-step, status or error input (StepPlayer.tsx ~295-364) | Controlled current step and per-step status from the run; a step completes only on its real completion; error state on the failing step; the running step's fill is indeterminate unless the step reports progress; drop play/pause unless the run itself can pause |
| upload-dropzone | **Demo-only.** "The pretend wire": progress is a random-paced loop; the tray holds two hardcoded demo files; refusals after the first use joke copy; "done" resets to idle after 1.5 s; no file input or callback | Real file picker and drop; a real upload with its real progress (indeterminate when unknown), error and retry; size limit as a prop; the project's own refusal copy; uploaded files stay listed |
| one-time-code | **Demo-only verification.** Any full code is accepted after a 420 ms pause unless the `answer` prop is "Reject"; no callback | Send the full code to the real verify call; "checking" holds until it answers; ok or wrong from its result; a network-error state |
| slide-confirm | No callback; on completion it shows done for 1.5 s, then resets itself | Fire the real action on completion; pending until it answers; show its real success or error; reset only on that result |
| checklist | Three hardcoded demo tasks; 3 s after every task is ticked the list resets to them, wiping added tasks | Items and ticks from real data with a change callback that persists; remove the auto-reset |
| stacked-bars | **Fabricated values.** Bars come from a seeded random generator (fixed categories Direct/Search/Social/Email, last day 2026-10-11); no data prop | Data, categories and dates from a prop fed by the real source; loading, empty and error states |
| picker | Hardcoded cast of four named people; no options, value or change callback | Options from real users; controlled value with a change callback |
| voice-note | **Demo-only.** No microphone: the waveform is a synthetic stand-in with random levels, and playback only replays the drawing | Real recording (getUserMedia + MediaRecorder), levels from an AnalyserNode, real playback, permission-denied and error states, the recording handed out by callback |
| signature | Marked signed by a 1.5 s pause timer after the last stroke; no export of the signature | Explicit confirm; export (image or strokes) through a callback; empty/required validation |
| todo-tower | Hardcoded demo to-dos; the emptied tower refills itself on a timer | Novelty only; real items and no refill if ever used |
| all (general) | Demo copy and avatars/photos are placeholders; Pro-photo licensing does not travel; none of the best picks takes a data or callback prop (repo TSX, 2026-10-18) | Use client images and copy; wire real data and actions through props the adaptation adds |

Adaptation checklist (run per block, record in SOURCE.md):
1. **Long text and empty/odd data**: 1-line truncation, 60+ character names, 0 / 1 / 100 items, RTL not needed unless stated.
2. **States**: default, hover, focus-visible, active, loading, error, empty, disabled, success. Most Bencho blocks ship only the happy path.
3. **Keyboard**: every pointer action has a key path (Tab, Enter/Space, Esc, arrows); visible focus ring from `--focus`. Keyboard-started actions must not animate (design-pass gate 31d) - guard motion on `event.detail === 0` / key events or render the end state directly.
4. **Reduced motion**: wrap springs and loops in `prefers-reduced-motion` (framer `useReducedMotion`, CSS media query); loaders fall back to a static or opacity-only cue.
5. **Contrast**: check `--ink-3/4/5` on `--card` and `--surface` in light and dark (WCAG AA 4.5:1 text, 3:1 UI); the grey hint tones often fail on tinted client themes.
6. **Token mapping**: point the block's token names at the project's tokens (do not ship a second token set); confirm dark mode through the project's own switch.
7. **Strip dead CSS**: remove selectors for other blocks and unused props; keep the licence header (the MIT header).
8. **Touch/size**: hit targets >= 44px on mobile; no hover-only information (hover blocks need a tap or focus path).
9. **Sound**: off by default, user toggle, never required for meaning.
10. **Performance**: pointer-tracking blocks (particles, magnetic dots, glass-bubble, heat-word) and `three` blocks need a perf check and an off-screen pause; do not use on data-heavy dashboards.
11. **Licence trail**: SOURCE.md with URL, date, licence. Free blocks: LICENSE file; MIT header intact.

## 7. Best picks for JC's work

Top 10 free for automation tools and client dashboards:

| # | Block | Why |
|---|---|---|
| 1 | action-node | Closest to n8n/Make-style step cards; needs status/duration/error added and its actions wired (Known gaps) |
| 2 | step-player | The look for multi-step run or onboarding progress with clear current/done states; demo-only: it advances on a timer, so it needs controlled step state, real completion and error wiring, and indeterminate fill when progress is unknown (Known gaps) |
| 3 | stacked-bars | Ready-made data-viz with tooltip and period toggle for KPI panels; its data is seeded demo values, so it needs a data prop (Known gaps) |
| 4 | toast-stack | Run-complete / error notices in a portal; needs a push API fed by real events, real actions in place of the demo pool and Retry, and an aria-live region (Known gaps) |
| 5 | upload-dropzone | Client file intake with size refusal built in; demo-only: its upload and progress are simulated, so it needs a real upload (Known gaps) |
| 6 | one-time-code | Portal login/2FA entry that handles paste and autofill; it fakes verification, so wire the real check (Known gaps) |
| 7 | label-input | Compact, clear form fields for settings and intake forms |
| 8 | checklist | Client onboarding / task progress with satisfying completion state; its demo tasks reset on a timer, so wire real items (Known gaps) |
| 9 | slide-confirm | Guards destructive or irreversible automation actions (deploy, send, delete); it has no callback and resets itself, so wire the real action and its result (Known gaps) |
| 10 | generate | The look for a long AI/automation job loader; demo-only: it is timer-driven with a fabricated percentage, so it needs controlled job state, real completion and error wiring, and indeterminate progress when progress is unknown (Known gaps) |

Also useful (each has a Known gaps row): picker (assign owner), voice-note (voice-ai capture; no real recording yet), signature (client sign-off; no export yet), checklist-like todo-tower (novelty only).

Top 5 free for landing pages:

| # | Block | Why |
|---|---|---|
| 1 | image-compare | Before/after proof for case studies and results |
| 2 | carousel | Showcase of client work or templates with depth |
| 3 | image-accordion | Compact gallery or service/feature strip that rewards hover |
| 4 | heat-word | Distinctive hero accent; light, no dependencies |
| 5 | glass-bubble | Premium product-feel moment; check performance and Safari behaviour (not stated) |

