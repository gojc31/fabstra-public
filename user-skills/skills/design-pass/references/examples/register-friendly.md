# Register example: friendly

The **friendly** register for business-owner or client users: one ruled KPI band of large figures with plain labels, one accent colour, a step-by-step replay of what happened. Referenced from design-pass step 5(a).

Source: arm B of the 2026-10-18 A/B design trial, copied verbatim below. Both arms got one brief: an "Automation Run Monitor" dashboard screen (header with workspace switcher, search and Cmd/Ctrl-K palette; KPI strip; runs table with status pills and filters; a run-detail drawer with Steps / Logs / Input-Output tabs and Retry; a toast stack; loading, empty and error states; light and dark; React 18 + Vite + TypeScript, plain CSS, framer-motion, lucide-react). JC could not split the two arms on quality. Built result: D:\design-trial-2026-10-18\arm-b.

This is a filled example, not a template: its tokens, copy and seed data belong to that brief. Its "Arm B exclusions" list is a trial condition (that arm ran without Hallmark); a real pass keeps every step and every gate.

---

## Design (from design-pass)

Pass: INTERNAL · scope SCREEN · OPEN

Arm B exclusions (I skipped these on purpose and left nothing silently out):
- Hallmark was never read.
- Step 5 parts I skipped: the Genre line, the Macrostructure line, and the 5(b) structural-variety check.
- Gates skipped from gates.md because they carry an [HM] tag: 1, 2, 5, 6, 8, 10, 11, 12, 13, 14, 16, 17, 20, 22, 24, 25, 26, 27, 28, 30, 31, 32, 34. This includes the dual-tagged 2, 11, 14 and 31.
- Where impeccable, frontend-design, Emil (motion-craft.md), design-pass's own rules or WCAG state the same check on their own, I wrote a replacement gate. It carries only that non-Hallmark tag.
- Inspo was not called, because design-pass step 4 skips SCREEN scope.

Rules (binding):
- The brief's pinned words override every rule below.
- No eyebrow or kicker label above a heading.
- No numbered section markers unless the content is a real sequence.
- No `->` or `→` glyph appended to link or button text.
- No italic display type.
- No invented metrics, testimonials, logos, or names.
- Colours and fonts come only from the Tokens block.
- Stack is fixed by the brief: React 18 + Vite + TypeScript, plain CSS (CSS variables; one stylesheet per component; tokens in `src/styles/tokens.css`), framer-motion, lucide-react.
- No Tailwind and no component library.
- Every number on screen is computed from the seeded demo dataset (see Seed data). The header always shows the "Demo data" tag.

Direction:
  Genre: not used. Arm B excludes Hallmark, and the genre list is a Hallmark source.
  Macrostructure: not used, for the same reason. In plain words the screen is an instrument panel: a header on the ground, a title row, one KPI band, one dense runs table, and a peek drawer on demand. There is no sidebar, because one screen does not need fake navigation.
  Principles:
  (1) Colour is for exceptions. Normal stays ink and grey. Only Failed, Maybe sent and Running carry saturated marks, ranked loudest to quietest in that order, so a scan finds trouble in a second. This is the control-room HMI convention from ISA-101.
  (2) Show the run as the workflow it is. Run detail is the automation's own node chain on a wire, with the failure written on the node that failed, not a log dump.
  (3) Instant where repeated, moving where it explains.
  - Keyboard actions, the palette, list highlight and arrow-key tab switching change state with zero animation.
  - Only these move, each on a named curve: pointer-opened menus and drawers, toasts, and the retry replay.
  Boldness: the Steps tab node chain and its retry replay.
  - Icon tiles sit on a 2px wire. The wire is solid ink-2 where data flowed and dashed where a step never ran.
  - The failing node is ringed in red, with its error and the recovery written inside its card.
  - On Retry run the chain replays node by node.
  - Header, KPI band and table stay flat, grey and quiet.
  Alignment: left throughout. Duration is right-aligned. All numerals use tabular figures (IBM Plex Sans figures are tabular by default; I checked: every digit is 600 units wide).
  Changed at review (frontend-design's five clusters, plus the dashboard defaults):
  (a) Four identical KPI cards with big numbers, delta chips and sparklines (the SaaS-card kit and the hero-metric template) became one bordered band. It has four cells split by 1px rules, and each figure reads as one 24px line: "{n} runs today".
  (b) A dark-first near-black with a neon accent became a light-first cool panel grey. Dark theme is a slate night panel. The theme default follows the system, picked from the use scene (clients checking in office hours), not by category.
  (c) The Inter/Geist default face became IBM Plex Sans. It was designed around people and machines, and it suits the automation subject. IBM Plex Mono is limited to data (run IDs, logs, JSON).
  (d) ALL-CAPS column headers and log levels became sentence case and lowercase.
  (e) Middle-dot meta strings in the drawer header became a two-column definition list.
  (f) One radius on everything became a radius scale by role.
  (g) Tinting whole failed rows, or a red left stripe, became the pill alone, ranked by loudness.
  (h) A violet or indigo AI accent became one Signal blue, reserved for system activity, focus and selection. Primary actions are ink-filled.

Tokens (proposed):

Core named colours (light / dark): Panel grey ground, White surface, Slate ink, Signal blue, Run green, Fault red, Caution amber. Full sets are below, with measured contrast beside each text pair.

```css
:root, [data-theme="light"] {
  color-scheme: light;
  --c-ground: #ECEEF1;        /* Panel grey: app ground behind panels. Direction choice (control-room grey), not cream */
  --c-surface: #FFFFFF;       /* panels, drawer, menus, palette, toasts, node cards */
  --c-surface-2: #F5F6F8;     /* thead, row hover, code/log blocks, kbd chips, disabled fill */
  --c-press: #EBEDF0;         /* row :active, menu item :active */
  --c-ground-hover: #E3E6EA;  /* hover for controls sitting on the ground (header) */
  --c-line: #DDE0E5;          /* 1px borders, dividers, overlay borders */
  --c-line-strong: #C5CAD2;   /* control borders, dashed not-run wire, drag handle, link underline */
  --c-skeleton: #E3E6EA;
  --c-ink: #1A212B;           /* Slate ink: primary text 16.20 surface / 13.94 ground / 14.98 s2; primary button fill; tooltip bg */
  --c-ink-hover: #2B3441;     /* primary button hover fill */
  --c-on-ink: #FFFFFF;        /* label on ink 16.20, on ink-hover 12.57 */
  --c-ink-2: #525C69;         /* secondary text: 6.79 surface, 5.84 ground, 6.28 s2, 5.79 press, 5.84 blue-tint; executed wire */
  --c-ink-3: #646D7A;         /* placeholder, pending icons: 5.24 surface, 4.84 s2, 4.50 ground */
  --c-disabled: #7F8793;      /* disabled labels: 3.63 surface, 3.35 s2 */
  --c-blue: #2350C8;          /* Signal blue: running glyph, focus ring, caret: 6.88 surface, 5.92 ground */
  --c-blue-tint: #E8EEFC;     /* running pill bg, selected row, ::selection, new-row flash */
  --c-blue-ink: #1C43A8;      /* running pill label 7.47 on tint */
  --c-green: #1E7A4C;         /* Run green, glyph only: 5.33 surface, 4.92 s2, 4.58 blue-tint, 4.54 press */
  --c-red: #C8312F;           /* Fault red glyph + node ring: 4.63 on red-tint */
  --c-red-tint: #FCEBEA;      /* failed pill bg, node error block, error log line */
  --c-red-ink: #A3221F;       /* failed label 6.49 on tint; error text; "{f} failed" link 7.48 on surface */
  --c-amber: #A86200;         /* Caution amber glyph + ring: 4.22 on tint (icon, >=3:1) */
  --c-amber-tint: #FCF0D9;
  --c-amber-ink: #844C00;     /* maybe-sent label/text 6.17 on tint; warn log text 6.97 surface */
  --c-scrim: rgb(0 0 0 / 0.32);   /* pure black alpha: black is black */
  --shadow-pop: 0 1px 2px rgb(0 0 0 / 0.06), 0 8px 24px -6px rgb(0 0 0 / 0.18);   /* menus, tooltips, toasts */
  --shadow-panel: 0 2px 8px rgb(0 0 0 / 0.06), 0 24px 56px -16px rgb(0 0 0 / 0.28); /* drawer, sheet, palette */
}
[data-theme="dark"] {
  color-scheme: dark;
  --c-ground: #191E26;        /* Night panel: a named slate, not a near-black standing in for black */
  --c-surface: #20262F;  --c-surface-2: #272E39;  --c-press: #2E3643;  --c-ground-hover: #232933;
  --c-line: #333B47;  --c-line-strong: #46505E;  --c-skeleton: #2A313C;
  --c-ink: #E7EAEE;           /* 12.61 surface / 13.87 ground / 11.33 s2 */
  --c-ink-hover: #FFFFFF;  --c-on-ink: #191E26;     /* 13.87 on ink, 16.73 on hover */
  --c-ink-2: #A2ABB8;         /* 6.56 surface, 7.21 ground, 5.89 s2, 5.25 press, 5.93 blue-tint */
  --c-ink-3: #929BA8;         /* 5.42 surface, 4.87 s2, 5.96 ground */
  --c-disabled: #6E7785;      /* 3.36 surface, 3.02 s2 */
  --c-blue: #7EA2FF;          /* 6.16 surface, 6.77 ground */
  --c-blue-tint: #1F2C4D;  --c-blue-ink: #B5C9FF; /* 8.37 */
  --c-green: #4CC38A;         /* 6.87 surface, 6.21 blue-tint */
  --c-red: #FF7B72;  --c-red-tint: #3A2124;  --c-red-ink: #FFB3AD;       /* 5.85 / 8.65 on tint */
  --c-amber: #E5A13A;  --c-amber-tint: #3A2C17;  --c-amber-ink: #F5C77A; /* 6.11 / 8.59 on tint */
  --c-scrim: rgb(0 0 0 / 0.55);
  --shadow-pop: 0 1px 2px rgb(0 0 0 / 0.4), 0 8px 24px -6px rgb(0 0 0 / 0.5);
  --shadow-panel: 0 2px 8px rgb(0 0 0 / 0.3), 0 24px 56px -12px rgb(0 0 0 / 0.6);
}
```

  --font-sans: "IBM Plex Sans", "Helvetica Neue", Arial, sans-serif — all UI text. Self-host via @fontsource/ibm-plex-sans, weights 400, 500 and 600.
  --font-mono: "IBM Plex Mono", ui-monospace, monospace — only for run IDs, log lines, JSON blocks and the error detail line. Use @fontsource/ibm-plex-mono, weights 400 and 500.

Type scale is fixed rem, not fluid. Format is size/line-height weight:
  - 12/16 at 500: meta, column headers, pill labels, kbd, palette group headings.
  - 13/20 at 400 and 500: table cells, secondary copy, toasts body.
  - 14/20 at 400 and 500: controls, body, palette items, toast title, node titles.
  - 16/24 at 600: drawer title, empty and error headings.
  - 20/28 at 600, letter-spacing -0.01em: page title "Runs".
  - 24/32 at 500, letter-spacing -0.015em: KPI values.
  - Code and logs: 12/18 mono.
  - Every input is 16px below 640px, so iOS does not zoom.
  - Use font-variant-numeric: tabular-nums on every number.

Spacing (4px base): 4, 8, 12, 16, 20, 24, 32, 40, 48.
  - Gutter: 24px at ≥1024, 20px at 640–1023, 16px below 640.
  - Gap from header to title row: 0 (title row is 48px). Title row to KPI band: 12px. KPI band to table panel: 16px.

Sizes:
  - Header 56px. Title row 48px. KPI band 72px.
  - Toolbar 52px. Thead 36px. Row 44px. Mobile list item 64px.
  - Controls 32px (40px below 640px). Icon button 32×32 with a 16px icon (40×40 below 640px).
  - Drawer 480px wide. Palette 600px wide, with a 48px input and 40px items.
  - Toast 360px wide.

Radius by role:
  - --r-xs 4: kbd, checkbox, skeleton bars, Demo data tag.
  - --r-sm 6: buttons, inputs, menu items, tooltips, node icon tiles, node error block.
  - --r-md 8: node cards, code blocks.
  - --r-lg 10: panels, menus, toasts.
  - --r-xl 12: drawer, sheet top corners, palette.
  - --r-pill 999: status pills only, because the brief names them pills.

Z-index: sticky thead 5, drawer and sheet 40, menus 50, tooltips 60, palette 70, toasts 80.

Motion tokens:
  - --ease-out: cubic-bezier(0.23, 1, 0.32, 1). Used for UI enter and exit.
  - --ease-in-out: cubic-bezier(0.77, 0, 0.175, 1). Used for movement on screen.
  - --ease-drawer: cubic-bezier(0.32, 0.72, 0, 1).
  - Durations (ms):

    | Use | Duration |
    | --- | --- |
    | hover | 120 |
    | press | 160 |
    | tooltip in / out | 125 / 80 |
    | menu in / out | 200 / 140 |
    | tab indicator | 250 |
    | state crossfade | 150 |
    | accordion | 200 |
    | drawer in / out | 360 / 240 |
    | sheet in / out | 500 / 300 |
    | toast in / out | 400 / 200 |
    | new-row flash | 1200 |
    | spinner | 800 |
    | skeleton pulse | 1200 |

Root overflow: not clipped.
  - The root keeps the default overflow, so a width bug shows instead of hiding.
  - `scrollbar-gutter: stable` on html stops the page shifting when the sheet or palette locks scroll.
  - Drawer, sheet, palette, menus, tooltips and toasts are position: fixed portals, unmounted when closed, so nothing parked off-canvas adds width.
  - Below 640px the table becomes a stacked list instead of scrolling sideways.
  - Long names truncate with an ellipsis (min-width: 0 on flex and grid children).
  - Code blocks may scroll horizontally inside their own box.
  - The table panel uses `overflow: clip` (not hidden) so the sticky thead still sticks to the viewport.

References: none — no external references. SCREEN scope skips Inspo per step 4, and arm B excludes Hallmark.

Layout (first viewport):

Glyph key for these wireframes only (the UI uses lucide-react):
- ⌁ Webhook
- ◷ Clock
- ⟳ LoaderCircle
- ✕ CircleX
- ✓ CircleCheck
- ◌ CircleDashed
- ⎔ BrainCircuit
- # Hash
- ⇕ ChevronsUpDown
- ⌄ ChevronDown
- ⌕ Search
- ☾ Moon / Sun
- ↻ RefreshCw
- ⧉ Copy
- {…} = a value computed from the seed data

```
1280 x 800, light, drawer closed. Ground = panel grey; panels = surface, 1px --c-line, r10, no shadow.
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ [mark] Run Monitor │ Operations ⇕ [Demo data]          [⌕ Search workflows and runs  ⌘K] [☾]│ 56 header on ground, no border
│ Runs                                                                Updated 14:32:10 [↻] │ 48 title row
│ ┌──────────────────────┬────────────────────────────┬──────────────────────┬────────────┐│ 72 KPI band: ONE panel,
│ │ {n} runs today       │ {p}% succeeded  {f} failed │ {d} median duration  │ {$} AI sp… ││ 4 equal cells, 1px rules,
│ └──────────────────────┴────────────────────────────┴──────────────────────┴────────────┘│ value 24/500 + label 14 ink-2
│ ┌────────────────────────────────────────────────────────────────────────────────────────┐│ on one baseline
│ │ [Status ⌄] [Workflow ⌄] [⌕ Filter by workflow or run ID     ]         {x} of {y} runs ││ 52 toolbar
│ ├────────────────────────────────────────────────────────────────────────────────────────┤│
│ │ Workflow                             Trigger     Status          Started      Duration ││ 36 thead s2, sticky top 0
│ │ New lead to CRM  n8n                 ⌁ Webhook   (⟳ Running)     14:31:52          18s ││ 44 rows, 13px
│ │ Missed-call text back  GHL           ⌁ Webhook   (✕ Failed)      14:29:07         2.4s ││ failed = red-tint pill
│ │ Appointment reminder call  VAPI      ◷ Schedule   ✓ Succeeded    14:00:00        48.1s ││ succeeded = glyph + ink-2 label
│ │ New lead to CRM  n8n                 ⌁ Webhook   (◌ Maybe sent)  13:52:40        12.0s ││ amber-tint pill
│ │ … about 10 rows visible above the fold                                                  ││
```
Columns at ≥640: table-layout fixed. Workflow takes the rest. Trigger 128px, Status 144px, Started 112px, Duration 96px right-aligned. Cell padding is 0 16px, with 20px on the first cell.

```
1280, drawer open. Non-modal: no scrim; rows stay clickable; selected row = --c-blue-tint.
                                   ┌── drawer 480w, inset 8 top/right/bottom, r12, shadow-panel, 1px line ──┐
                                   │ Missed-call text back                             [↺ Retry run] [✕] │ 20 pad; title 16/600
                                   │ (✕ Failed)                                                          │
                                   │ Started   18 Oct, 14:29:07          Trigger  ⌁ Webhook              │ dl 2 cols; label 13
                                   │ Duration  2.4s                      Run ID   R-8F3K2Q [⧉]           │ ink-2, value 13 ink
                                   ├─────────────────────────────────────────────────────────────────────┤
                                   │ Steps    Logs    Input-Output                                       │ 40 tabs, 1px bottom line
                                   │ ═════                                                               │ 2px ink indicator
                                   ├──────────── panel scrolls (overscroll-behavior: contain) ───────────┤
                                   │ [⌁] ┌ Call missed webhook                            0.1s  ✓ ┐       │ rail 32 | card r8
                                   │  ┃  └ Trigger: Webhook                                       ┘       │ pad 10/12, gap 12
                                   │  ┃                                                                  │ 2px wire ink-2 = ran
                                   │ [⎔] ┌ Write reply with LLM                           1.9s  ✓ ┐       │
                                   │  ┃  └ LLM step: 1,240 tokens, $0.004                         ┘       │
                                   │ (#) ┌ Post to #front-desk                            0.4s  ✕ ┐       │ tile ringed 2px red,
                                   │     │ Slack post to #front-desk                                │       │ bg red-tint
                                   │     │ ┌ Slack returned channel_not_found for #front-desk. …  ┐│       │ error block r6,
                                   │     │ └ View error log                                       ┘│       │ no side stripe
                                   │     └──────────────────────────────────────────────────────────┘       │
                                   └─────────────────────────────────────────────────────────────────────┘
```

```
390 x 844 (also the 375 check)
┌──────────────────────────────────────┐
│ [mark] Operations ⇕          [⌕] [☾] │ 56; ⌕ opens the palette; wordmark hidden
│ Runs  [Demo data]     14:32:10  [↻]  │ 44; tag moves beside the title below 640
│ ┌─────────────────┬─────────────────┐│ KPI 2x2; value 24 above label 13
│ │ {n}             │ {p}%            ││
│ │ runs today      │ succeeded       ││
│ │                 │ {f} failed      ││ link on its own line
│ ├─────────────────┼─────────────────┤│
│ │ {d}             │ {$}             ││
│ │ median duration │ AI spend today  ││
│ └─────────────────┴─────────────────┘│
│ ┌────────────────────────────────────┐│
│ │ [Status ⌄      ] [Workflow ⌄     ] ││ 40 high, 2 equal columns; count hidden
│ │ [⌕ Filter by workflow or run ID  ] ││ full width, 16px text
│ ├────────────────────────────────────┤│
│ │ Missed-call text back   (✕ Failed) ││ 64 list item (button), pad 12/16
│ │ ⌁ Webhook   14:29:07   2.4s        ││ 13 ink-2, 12px gaps, no middle dots
│ ├────────────────────────────────────┤│
```
At 640–1023 the layout matches 1280, with these changes:
- The palette trigger is 200px wide.
- Each KPI cell stacks its value above its label.
- The drawer is min(480px, 100vw - 16px) wide.

Below 640px the drawer becomes a bottom sheet:
- Height calc(100dvh - 48px), top corners r12.
- A 36×4 drag handle (r2, --c-line-strong) sits 8px from the top.
- It is modal, with the scrim and a focus trap.

Components and states (hover rules always sit inside `@media (hover: hover) and (pointer: fine)`; focus ring = `outline: 2px solid var(--c-blue); outline-offset: 2px`, no transition):

**Header**
- Mark: a 20px custom SVG of three 5px rounded squares joined by a 1.5px line, stepping down to the right. It is --c-ink, with the last square in --c-blue, echoing the node chain.
- Wordmark: "Run Monitor" at 14/600.
- Divider: 1px × 16px in --c-line.
- Workspace switcher: transparent trigger with the workspace name at 14/500 ink and a ChevronsUpDown 14px icon in ink-2.
- "Demo data" tag: 20px tall, 12/500, ink-2 text, surface fill, 1px line border, r4. Tooltip: "Sample runs generated for this demo".
- Palette trigger: looks like a search field. 280px wide, surface fill, 1px line border, r6. Search icon in ink-2, the text "Search workflows and runs" in ink-3, and a kbd chip on the right reading "⌘K" on Mac or "Ctrl K" elsewhere. This one control fills both the brief's "search" and "palette trigger".
- Theme icon button.

**Primary button** (Retry run; Try again)
- Default: ink fill, on-ink label at 14/500, 32px tall, r6, padding 0 12px, 16px icon with a 6px gap.
- Hover: fill changes to --c-ink-hover.
- Focus-visible: the standard ring.
- Active: scale(0.97).
- Disabled: surface-2 fill, 1px line border, --c-disabled label, cursor not-allowed. Use aria-disabled so the tooltip stays reachable. Retry is disabled while the run is running, with the tooltip "This run is still running."
- Loading: label "Retrying" (or "Trying again") with a spinning LoaderCircle. Lock min-width to the wider label so nothing jumps. Set aria-busy.
- Error: the button never turns red. It returns to its default label, and the failure shows on the node, the pill and the toast.
- Success: returns to default; the outcome shows on the pill and the toast.

**Secondary button** (Refresh runs, Clear filters, Copy logs, Copy input, Copy output)
- Default: surface fill, 1px line-strong border, ink label.
- Hover: surface-2 fill.
- Focus-visible: the standard ring.
- Active: scale(0.97).
- Disabled: --c-disabled label, --c-line border.
- Loading: a spinner replaces the icon, and the label changes, e.g. "Refreshing".
- Error: "Copy failed" in red-ink for 2s when the clipboard rejects the write.
- Success: "Copied" with a green Check for 2s.

**Icon button**
- Default: ink-2 icon.
- Hover: --c-ground-hover background when on the ground, --c-surface-2 when on a surface; the icon turns ink.
- Focus-visible: the standard ring.
- Active: scale(0.97).
- Disabled: --c-disabled icon.
- Loading: the refresh icon spins.
- Error and success: n/a.
- Every icon button has an aria-label and a tooltip.

**Text-link button** ("{f} failed", "View run", "View error log", "See connected workflows", "Retry of R-…")
- Default: 13/500 in ink or red-ink depending on context. Underline in --c-line-strong, offset 3px, 1px thick.
- Hover: the underline takes currentColor.
- Focus-visible: ring with r4.
- Active: underline thickness 2px. No scale on inline text.
- Disabled: n/a; the link is hidden when it has nothing to do (for example "{f} failed" when f is 0).
- Loading, error, success: n/a.

**Dropdown triggers** (Status, Workflow)
- Default: surface fill, 1px line-strong border, r6, 32px tall, label "Status" in ink-2 with a ChevronDown.
- Active filter: label "Status: Failed" or "Status: 2 selected" in ink.
- Hover: surface-2 fill.
- Open: aria-expanded, surface-2 fill.
- Focus-visible: the standard ring.
- Active: scale(0.97).
- Disabled: during loading and error states, --c-disabled label.
- Loading, error, success: n/a, because the data is local.

**Menus**
- Container: a portal at position: fixed, 4px below the trigger. Flip above the trigger when there is no room. Surface fill, 1px line border, r10, --shadow-pop, padding 4px. Minimum width is max(trigger width, 220px).
- Items: 32px tall, r6, 14px text.
- Highlight from pointer hover or arrow keys: surface-2 background, instant. Keyboard-highlighted items also show the ring with offset -2px. Use roving tabindex, so this is plain :focus-visible.
- Pressed: --c-press background.
- Checkbox: 16px, r4, 1px line-strong border. Checked = ink fill with a 12px Check in on-ink. Toggles instantly.
- Status menu items: the status glyph, the label, and the count in ink-2 on the right. A "Clear" text button at the bottom.
- Workflow menu items: name, with the platform in ink-2 on the right.
- Workspace menu: three radio items with a Check on the current one.
- Disabled item: --c-disabled label, and arrow keys skip it.
- Keys: Esc closes and returns focus to the trigger. Tab closes. Space or Enter toggles.

**Table filter input**
- 32px tall, 280px wide, surface fill, 1px line-strong border, r6.
- Search icon in ink-2. Placeholder "Filter by workflow or run ID" in ink-3.
- Focus: border turns --c-blue, plus the standard ring.
- An X clear button (aria "Clear filter text") appears only when the input has text. Esc clears.
- Disabled during loading and error states.
- Matches on workflow name or run ID.

**Table row**
- The first cell holds a `<button>` whose accessible name is "{workflow}, {status}, started {time}". Click anywhere on the row to open.
- Hover: surface-2 background.
- Focus-visible: the ring on the row with outline-offset -2px.
- Active: --c-press background. No scale on a full-width row.
- Selected (drawer open): --c-blue-tint background.
- Just inserted: background fades from --c-blue-tint to --c-surface.
- Loading: 8 skeleton rows with bars sized to each column (r4, --c-skeleton).
- Disabled, error, success: n/a.
- Arrow Up/Down move focus between rows. When the drawer is open it follows the focused row with an instant content swap. Enter opens the drawer.

**Status pill**
- Size: 22px tall, padding 0 8px 0 6px, r999, 14px icon with a 6px gap, label 12/500.
- Succeeded: no fill. Green CircleCheck, ink-2 label "Succeeded". This is the quiet one.
- Running: blue-tint fill, blue LoaderCircle spinning, blue-ink label "Running". Duration ticks live, updated every 1s.
- Maybe sent: amber-tint fill, amber CircleDashed, amber-ink label "Maybe sent".
- Failed: red-tint fill, red CircleX, red-ink label "Failed". This is the loudest.
- Tooltip with the meaning (see Copy deck), shown on hover only. The text label carries the meaning for screen readers.

**Node card** (Steps tab, an `<ol>`)
- Layout: a grid with a 32px rail and a 1fr card. The rail holds a 32×32 r6 tile with a 16px icon.
- Wire: a 2px line centred on the rail, running from tile bottom +4px to the next tile top -4px.
- Card: surface fill, 1px line border, r8, padding 10px 12px.
  - Title at 14/500 ink.
  - Kind line at 12/16 ink-2.
  - On the right: duration (13, ink-2, tabular) and a 16px status glyph.
- States:
  - Pending: s2 tile, ink-3 icon, glyph Circle in ink-3, meta "Waiting".
  - Running: tile ring `box-shadow: 0 0 0 2px var(--c-blue)` (drawn on a pseudo-element; animate its opacity). Glyph LoaderCircle, duration ticking.
  - Succeeded: s2 tile, ink icon, green CircleCheck.
  - Failed: red-tint tile, red-ink icon, red 2px ring, red CircleX. Below the kind line goes an error block: red-tint fill, r6, padding 8px 10px, 13/20 red-ink text, then the "View error log" link.
  - Maybe sent: amber-tint tile, amber ring, amber CircleDashed, and an amber-tint block in amber-ink.
  - Skipped: tile with a 1px dashed line-strong border and an ink-3 icon. The card text is ink-2: "Skipped: an earlier step failed".
- Wire style: a segment whose downstream step ran is solid --c-ink-2. A segment into a step that never ran is dashed: `repeating-linear-gradient` in --c-line-strong, 4px on, 4px off.
- "View error log" switches to the Logs tab, then scrolls the error line to the centre and focuses it. Scroll is smooth, or instant under reduced motion.

**Tabs** (Steps / Logs / Input-Output)
- Tabs are 40px tall with padding 0 12px. Labels are 14/500 in both layers, so the width never shifts. A 1px --c-line bottom border runs the full width.
- Technique: duplicate the tab list. The base layer is ink-2 text. The aria-hidden overlay layer has ink text and a 2px ink bottom indicator on each tab. Clip the overlay with `clip-path: inset(0 R 0 L)`, measured from the active tab's rect, and remeasure with a ResizeObserver.
- Hover: the base-layer text turns ink.
- Focus-visible: ring with offset -2px and r6.
- Active: scale(0.97) on the tab button.
- Disabled, loading, error, success: n/a.
- Keys: Left/Right move and activate (automatic activation). Home/End jump to the ends.
- The panel swap is instant.

**Logs**
- Toolbar row with the "Copy logs" button on the right.
- Block: s2 fill, 1px line border, r8, 12/18 mono.
- Each line is a grid: time (84px, ink-2), level (48px, lowercase), message (1fr, ink).
- Levels: info in ink-2. warn in amber-ink on an amber-tint row. error in red-ink at 500 on a red-tint row.
- Lines use white-space: pre-wrap and overflow-wrap: anywhere.

**Input-Output**
- Two sections, "Input" and "Output", each with a 14/600 heading and a "Copy input" / "Copy output" button.
- Mono 12/18 block: s2 fill, r8, padding 12px, max-height 320px, scrolls inside itself.
- Keys in ink-2, values in ink.
- When a run failed: "No output. The run stopped at step {n}." in ink-2.

**Drawer**
- Header and tabs stay fixed at the top; the panel scrolls.
- Desktop: role="dialog" with aria-modal="false" and aria-labelledby pointing at the title.
- Opening moves focus to the title (tabindex -1). Closing returns focus to the row.
- Clicking another row swaps the content instantly. Clicking the ground or the header, outside any row, menu or toast, closes it.
- Esc closes the topmost layer first, in this order: tooltip, menu, palette, drawer.
- Below 640px it is the modal sheet.

**Command palette**
- Opens with ⌘/Ctrl-K from anywhere (preventDefault) or by clicking the trigger.
- Modal, centred, 20vh from the top. Width min(600px, 100vw - 24px). Below 640px: 8px from the top and sides.
- Surface fill, r12, --shadow-panel, 1px line border, with the --c-scrim behind it. Focus is trapped.
- Input row: 48px, Search icon, 16px input, "Esc" kbd on the right.
- List: max-height 360px.
  - Group headings at 12/500 ink-2, sentence case.
  - Items 40px, r6, 16px icon, 14px ink label, 13px ink-2 subtext.
  - Highlight: surface-2, instant. Pointer movement moves the highlight. Keyboard highlight also shows the ring at -2px.
  - Disabled items show --c-disabled text and are skipped.
- Footer: 12px ink-2 text with kbd chips: "↑ ↓ to move", "↵ to run", "Esc to close".
- Groups when the query is empty: "Actions" (Retry last failed run, Toggle theme), then "Jump to workflow" (all workflows). Matching is fuzzy.
- "Jump to workflow" closes the palette, sets the Workflow filter to that workflow, and focuses its first row.
- No results: "Nothing matches "{q}"."
- Loading and error: n/a (local data). In the error workspace, the workflow group shows one disabled row: "Workflows are unavailable while the run source cannot be read".

**Toasts**
- Stack: fixed, 16px from the bottom and right. Below 640px: 8px from the sides and bottom plus the safe-area inset. Width 360px.
- Container: `<section aria-label="Notifications">`. Success toasts are role="status"; failure toasts are role="alert".
- Toast: surface fill, 1px line border, r10, --shadow-pop, padding 12px 14px.
  - Glyph: green CircleCheck or red CircleX.
  - Title at 14/500.
  - Body at 13 ink-2.
  - "View run" text button.
  - X close button (aria "Dismiss notification"). It shows on hover or focus with a pointer, and always on touch.
- Collapsed stack: toast i (0 is newest) sits at `translateY(calc(-10px * i)) scale(calc(1 - 0.05 * i))`. Toasts with i>0 hide their content (opacity 0) and take the front toast's height.
- Expanded (hover or focus-within the stack): the real stacked offsets with 8px gaps, scale 1, content visible. A pseudo-element fills the gaps so hover holds.
- At most 3 visible. A 4th arrival fades the oldest out and removes it.
- Timers:
  - Success toasts dismiss after 10s. The timer pauses on hover, on focus-within, and while document.hidden, and resumes with the time that was left.
  - Failure toasts have no timer.
  - The table row and the drawer pill are the persistent record.
- Write each toast's offset to the toast element itself, never as a variable on the parent.

**Tooltip**
- --c-ink fill, --c-on-ink text at 12/16, r6, padding 4px 8px, max-width 240px, --shadow-pop.
- Sits 6px from the trigger. No arrow.

**KPI band**
- Loading: skeleton bars 64×24 for the value and 80×12 for the label.
- Empty:
  - Runs cell: "0 runs today".
  - Success-rate and median cells: "No runs yet" at 14 ink-2, in place of the value.
  - Spend cell: "$0.00 AI spend today".
- Error: one full-width cell with a TriangleAlert in ink-2 and "Today's figures are unavailable because the run source could not be read." Never 0.

**Screen states**

These are the triggers:
- First load shows the skeleton for 600ms.
- Switching workspace shows the skeleton for 400ms.
- The workspace "Support desk" is the empty state.
- The workspace "Marketing" is the error state.
- `?state=loading|empty|error` forces a state; loading holds forever.

Loading:
- The toolbar count slot reads "Loading runs".
- A visually hidden live region says the same.
- aria-busy is set on the table region.
- The header stays usable.

Empty, shown inside the table panel (centred, max 56ch):
- A 40px tile with r10, s2 fill, and a Workflow icon in ink-2.
- The heading.
- The body.
- A "Refresh runs" secondary button and a "See connected workflows" link, which opens the palette on "Jump to workflow".

Error, shown the same way:
- The tile has a red-tint fill with a TriangleAlert in red-ink.
- The heading.
- The body.
- A mono detail line at 12px ink-2.
- A primary "Try again" button.

Filter with no matches: "No runs match these filters." and a "Clear filters" button, shown inside the table body.

**Theme**
- Initial theme comes from localStorage, falling back to prefers-color-scheme. An inline script in index.html sets `data-theme` on `<html>` before React mounts.
- During a switch, `html[data-theme-switching] * { transition: none !important }` is applied for one frame.
- The header button reads "Switch to dark theme" or "Switch to light theme".

**Browser surfaces**
- `::selection` uses --c-blue-tint with --c-ink text.
- `caret-color` is --c-blue.
- `scrollbar-color: var(--c-line-strong) transparent` with `scrollbar-width: thin` on the drawer panel, palette list and code blocks.
- Text-underline-offset is 3px.

Motion (motion-craft.md is the authority; "kbd" = what happens when the action was started from the keyboard; RM = what happens under prefers-reduced-motion: reduce):

| Element | Trigger | Property: from → to | In | Curve | Out | Kbd | RM |
|---|---|---|---|---|---|---|---|
| Buttons, triggers, icon buttons, tabs | pointer :active | transform scale(1) → 0.97 (palette trigger 0.98) | 160ms | --ease-out | release 160ms | no scale | no scale |
| Hover (bg, color, border-color) | hover, gated | named properties only | 120ms | ease | 120ms | n/a | same |
| Focus ring | :focus-visible | outline | 0 | — | 0 | instant | instant |
| Menus (workspace, Status, Workflow) | pointer open | opacity 0 → 1, scale 0.95 → 1, origin at trigger edge (top left; top right if right-aligned) | 200ms | --ease-out | opacity → 0, scale → 0.97, 140ms --ease-out | 0ms both ways | opacity only 120ms ease |
| Menu or palette highlight, checkbox | hover or arrows | background | 0 | — | 0 | 0 | 0 |
| Tooltip | hover after 500ms (focus: no delay) | opacity 0 → 1, scale 0.97 → 1, origin at trigger side | 125ms | --ease-out | opacity 80ms --ease-out | — | opacity only |
| Tooltip, next one within 400ms | hover a neighbour | none | 0, no delay | — | 0 | — | — |
| Tab indicator and colour | pointer click | overlay clip-path inset → new tab rect | 250ms | --ease-in-out | — | 0ms | 0ms |
| Tab panel and drawer content swap | any | none | 0 | — | — | — | — |
| Drawer, ≥640px | pointer row click or "View run" | transform "translateX(105%)" → "translateX(0%)" | 360ms | --ease-drawer | close click: → 105%, 240ms --ease-drawer | Enter opens and Esc closes instantly | opacity 0 → 1 160ms ease |
| Sheet, <640px | tap | transform translateY(100%) → 0; scrim opacity 0 → 1 in sync | 500ms | --ease-drawer | 300ms --ease-drawer | n/a | opacity 200ms |
| Sheet drag | pointer on handle or header | transform tracks 1:1 after 10px of vertical movement; above the top it rubber-bands by (o·h·0.55)/(h+0.55·\|o\|) | — | — | release dismisses if offset >25% of height or velocity >0.11 px/ms: animate from the current value to 100% in 240ms --ease-out. Otherwise spring back {type: "spring", duration: 0.4, bounce: 0.15} | — | snap, no spring |
| Palette and its scrim | ⌘/Ctrl-K or click | none: mount and unmount | 0 | — | 0 | 0 | 0 |
| Toast enter | retry completes | transform translateY(100%) → 0, opacity 0 → 1, via a CSS transition with a data-mounted flag (not keyframes) | 400ms | ease (Sonner) | — | same | opacity 200ms ease |
| Toast reflow and expand | new toast, hover or focus-within | transform, opacity | 400ms | ease | 400ms | — | no scale, offsets instant |
| Toast exit | close or timer | front: translateY(100%) + opacity 0. Others: opacity 0 + scale 0.96 | 200ms | --ease-out | — | — | opacity 150ms |
| Toast swipe | pointer drag on x | style.transform set directly, 1:1 after 10px | — | — | release: if \|dx\| >56px or velocity >0.11, translateX(±110%) + opacity 0 in 200ms --ease-out. Otherwise snap back 240ms --ease-out | — | instant |
| Status pill change (row, drawer) | data change | incoming pill: opacity 0 → 1, filter blur(2px) → 0; outgoing removed | 150ms | ease | — | — | opacity only |
| Button label swap (Retrying, Copied) | state change | opacity and blur(2px) crossfade | 150ms | ease | — | — | opacity only |
| Spinners (running, loading buttons, refresh) | while busy | rotate 0 → 360deg, infinite | 800ms | linear | — | — | static icon, opacity 1 ↔ 0.5 at 1200ms ease-in-out alternate |
| Retry replay (the one authored moment) | retry starts | see sequence below | — | — | — | runs (it is progress, not open/close) | opacity steps only |
| Node error block | node fails during replay | height 0 → measured px (never auto), opacity 0 → 1 | 200ms | --ease-out | — | — | opacity only, height instant |
| New-row flash | retry inserts its row | background-color --c-blue-tint → --c-surface (a colour fade, not movement) | 1200ms | ease | — | same | same |
| Skeleton | loading | opacity 1 → 0.55, infinite alternate | 1200ms | ease-in-out | — | — | static at 0.8 |
| Skeleton to content | data ready | content opacity 0 → 1; no slide, no stagger | 200ms | --ease-out | — | same | same |
| Theme switch, checkbox, KPI number change | any | none | 0 | — | — | — | — |

Retry replay sequence. It runs on the store, so closing the drawer never cancels it and reopening shows the live state. Input is never blocked.
1. t=0: the button shows "Retrying". A new run row is inserted at the top of the table as Running, with the flash, and "Retry of R-…" in ink-2 beside the platform. The drawer swaps instantly to the new run, and every node is set to Pending.
2. Node 1 runs for 300ms, then becomes Succeeded. The glyph swap is opacity plus scale 0.9 → 1 at 150ms --ease-out. The ring fades in and out over 150ms ease.
3. Wire segment 1→2 fills. A 2px --c-ink-2 overlay goes from transform scaleY(0) → 1, origin top, 200ms linear.
4. Node 2 runs for 1200ms, with its duration ticking in tabular figures, then becomes Succeeded or Failed.
5. Wire segment 2→3 fills the same way.
6. Node 3 runs for 500ms, then becomes Succeeded or Failed.
7. If a node fails, its error block opens, and every later node becomes Skipped with a dashed wire into it.
8. Completion: the pills crossfade in the drawer and the table, the KPIs recompute instantly, the button returns to "Retry run", and the toast enters.
9. Total is about 2.4s.
10. Under reduced motion every change is an opacity step of 150ms or less, and the wire fill fades in instead of scaling.

Copy deck (sentence case everywhere; no middle dots in UI copy):

Header and title
- Wordmark: "Run Monitor".
- Workspace switcher: aria "Switch workspace, current: {name}".
- Palette trigger: "Search workflows and runs". Below 640px it is an icon button with aria "Search and commands".
- Title row: "Runs", then "Updated {HH:MM:SS}".
- Refresh: "Refresh runs", becoming "Refreshing". It simulates 600ms.

KPI band
- "{n} runs today"
- "{p}% succeeded", where p = succeeded ÷ (succeeded + failed + maybe sent), and running runs are excluded.
- "{f} failed" link, which sets Status = Failed.
- "{d} median duration", formatted "4.2s" or "1m 12s".
- "{$} AI spend today", formatted with Intl, USD.

Toolbar
- Filter triggers: "Status", "Workflow".
- Count: "{x} of {y} runs".
- "Clear filters" appears when any filter or text is set.

Table
- Column headers: "Workflow", "Trigger", "Status", "Started", "Duration".
- Trigger labels: "Schedule", "Webhook".

Status tooltips
- Succeeded: "Every step finished."
- Failed: "A step failed. Open the run to see which one."
- Running: "This run is in progress."
- Maybe sent: "The last step timed out after sending. It may have gone through."

Drawer
- Definition-list labels: "Started", "Duration", "Trigger", "Run ID". The copy button reads "Copy run ID" and shows the tooltip "Copied" afterwards.
- Close button: "Close run details".

Node kind lines
- "Trigger: Webhook" or "Trigger: Schedule".
- "LLM step: {tokens} tokens, {cost}".
- "Slack post to #{channel}".

Node errors
- F1: "Slack returned channel_not_found for #front-desk. The channel may have been renamed or archived. Update the channel in the workflow, then retry."
- F2: "The LLM provider returned 429 rate_limit_exceeded. This is usually temporary, so a retry should work."
- F3: "Slack returned rate_limited, so the post was not sent. A retry should work."
- Maybe sent: "The Slack post timed out after it was sent, so it may have reached #{channel}. Check the channel before you retry, or the message may post twice."

Toasts
- Success: "Retry succeeded" / "{workflow} ran in {d}."
- Failure: "Retry failed" / "{workflow} failed at step {n}: {short error}."
- Both have the action "View run".

Palette
- Placeholder: "Type a command or search workflows".
- Retry item: "Retry last failed run", with subtext "{workflow}, failed at {HH:MM}". When disabled, the subtext is "No failed runs today".
- Theme item: "Toggle theme", with subtext "Switch to dark" or "Switch to light".

Empty state
- Heading: "No runs yet"
- Body: "This workspace has {k} connected workflows. Their runs appear here as soon as a schedule fires or a webhook arrives."

Error state
- Heading: "The run source could not be read"
- Body: "Run Monitor could not read this workspace's run history from Make, so no runs can be shown. This only affects this view; it does not stop your workflows. Try again in a minute. If it keeps failing, ask your automation team to reconnect Make."
- Detail line: "Make API responded 401 Unauthorized at {HH:MM:SS}". After a failed "Try again" it updates to "Still could not read the source at {HH:MM:SS}".

Seed data (generate relative to Date.now(), all today, newest first; deterministic):

Workspaces
- "Operations" is the default. It holds the 7 workflows and 25 runs below.
- "Support desk" has 3 workflows and 0 runs, so it shows the empty state.
- "Marketing" has a source that cannot be read (Make 401), so it shows the error state.

Workflows: each is 3 steps, trigger → LLM step → Slack post.

| # | Workflow | Platform | Trigger | Slack channel |
|---|---|---|---|---|
| 1 | New lead to CRM | n8n | webhook | #sales |
| 2 | Missed-call text back | GHL | webhook | #front-desk |
| 3 | Appointment reminder call | VAPI | schedule | #bookings |
| 4 | Invoice follow-up | Make | schedule | #finance |
| 5 | Review request | GHL | webhook | #reviews |
| 6 | Support ticket triage | n8n | webhook | #support |
| 7 | Daily pipeline digest | Make | schedule | #leadership |

Runs: 19 Succeeded, 3 Failed, 2 Maybe sent, 1 Running.

| Run | Workflow | Detail | Retry result |
|---|---|---|---|
| Running | 1 | Newest run; it finishes as Succeeded 20s after load, with a pill crossfade and no toast | — |
| F1 | 2 | Fails at step 3 | fails again |
| F2 | 6 | Fails at step 2; step 3 is Skipped | succeeds |
| F3 | 5 | Fails at step 3 | succeeds |
| Maybe sent | 1 and 3 | Step 3 timed out | succeeds |

Other seed values
- Durations: 0.8–20s, and 30–75s for VAPI.
- LLM tokens: 400–3,000. Cost = tokens × $0.000003.
- Run IDs: "R-" plus 6 base32 characters.
- Logs: 6–10 lines per run, in the form "{HH:MM:SS.mmm} {info|warn|error} {message}". An error run ends with "error Slack API error: channel_not_found", then "info Run stopped at step 3 of 3".
- Input JSON uses 555-01xx numbers only.
- No person names anywhere.

Gates (reviewer runs these on the built result; N/A is written, not skipped). Source tags:
- [FD] frontend-design
- [IMP] impeccable craft-floor.md / operate.md
- [EMIL] motion-craft.md
- [AO55]
- [DP] design-pass's own rules and steps
- [WCAG] WCAG 2.2

Structure (read as the screen's layout):
  1. No card sits inside a card, and the screen is not built from same-size cards. The KPI strip is one ruled band; the node cards in the drawer are the only cards. [IMP]
  2. No eyebrow, kicker or category label sits above any heading (page title, drawer title, empty and error headings). [FD] [IMP]
  3. Numbered markers appear only on a real sequence. The step chain is an `<ol>` and shows no "01/02/03". [FD]
  4. Buttons use the 6px control radius. Only the status pills are fully rounded, because the brief names them pills. [AO55]
  5. No coloured border-left or border-right stripe over 1px on rows, node cards, error blocks, notices or toasts. [IMP]
  6. Menus, tooltips, palette, drawer, sheet and toasts render in fixed-position portals and are never clipped by the table panel. [IMP]

Type:
  7. Prose measure never exceeds 75ch. Empty, error and node-error copy is capped at 60ch. [FD] [IMP]
  8. Headings are roman, with no italic anywhere. [DP]
  9. No single word in a heading is accented by weight, italic or colour. [FD]
  10. Only IBM Plex Sans and IBM Plex Mono render, each through its token. Mono appears only on run IDs, log lines, JSON and the error detail line, never on labels or chrome. [DP] [AO55]
  11. The type steps are visible: 24/500, 20/600, 16/600, 14, 13, 12. All real copy fits at every width. [IMP]
  12. Every numeral in KPIs, Started, Duration, tokens and costs uses tabular figures, and the columns align. [IMP]

Colour:
  13. Every pair in the Tokens contrast notes measures as written in both themes, including hover, selected and pressed rows. That means ≥4.5:1 for text and placeholder, and ≥3:1 for icons, focus ring and disabled labels. [IMP] [WCAG 1.4.3, 1.4.11] [DP]
  14. No gradient text, no gradient washes, and no decorative glass or blur. [IMP]
  15. Black is black. Scrims and shadows are pure black alpha, and no #0B0B0B/#111-style near-black stands in for black. [FD]
  16. The ground is the named Panel grey or Night panel, not a default cream or off-white. [AO55]
  17. Every colour, shadow and font-family references a token. There is no inline hex, rgb or oklch outside tokens.css. [DP]
  18. On Operations at 1280, the only saturated fills in the first viewport are the Failed, Maybe sent and Running pills and the "{f} failed" link. Succeeded rows carry only the green glyph. [DP]

Copy:
  19. Every figure is computed from the seed, and the "Demo data" tag is visible at every width. There are no testimonials, logos or person names, and workspace and workflow names are functional. [DP]
  20. One name per action: Retry run, Retrying, Retry succeeded / Retry failed. Try again, Trying again. Refresh runs, Refreshing. Copy logs, Copied. [FD]
  21. Controls name what happens, and every error names the problem and the recovery. The error state says the source could not be read and never says "no runs". [FD] [IMP]
  22. No `->` or `→` glyph is appended to link or button text. [FD]

States:
  23. Every component ships the states listed in Components and states, with any n/a written there. [IMP]
  24. Loading (skeleton plus "Loading runs"), empty and error ship with the Copy deck text. Loading uses skeletons, never a lone centred spinner. [IMP]
  25. Focus is visible on every control, including keyboard-highlighted menu and palette items. It is a 2px Signal-blue ring with no transition on outline. [IMP] [WCAG 2.4.7]
  26. Success toasts last 10s or more and pause on hover, focus and hidden tab. Failure toasts have no timer. The table row and drawer pill keep the record. [DP]

Responsive:
  27. No horizontal page scroll at 375, 768 or 1280: documentElement.scrollWidth equals innerWidth. The root is not clipped, and any failure is reported with its cause. [DP] [IMP]
  28. No button, tab, filter-trigger, menu or palette label wraps to two lines at any width. Long workflow names truncate with a tooltip. [IMP]
  29. Below 640px: the table becomes the stacked list, the drawer becomes the bottom sheet, touch targets are ≥40px, and inputs are 16px. [IMP]

Motion:
  30. There is one authored motion moment, the retry replay. Sections, the KPI band and rows have no load entrances; skeleton to content is a 200ms opacity fade only. [FD] [IMP]
  31. Every transform and keyframe has the reduced-motion path from the Motion table. Opacity and colour stay; movement goes. [EMIL]
  32. No `transition: all`. Every transition names its properties. [EMIL]
  33. No bounce or overshoot on any UI state. The only spring is the sheet's drag release (bounce 0.15). [EMIL]
  34. No UI element enters or exits on ease-in, and exits run shorter than entrances. The toast's 400ms `ease` passes because motion-craft names it. [EMIL]
  35. No entrance starts from scale(0). Scaled entrances start at 0.95–0.97 with opacity 0. [EMIL]
  36. Menus and tooltips scale from their trigger edge (check transform-origin). The palette stays centred and does not animate. [EMIL]
  37. These change state with no animation: ⌘/Ctrl-K, the palette from any input, Enter-opened drawer, Esc close, arrow-key tab switching, keyboard-opened menus, and list highlight. [EMIL]
  38. Every hover rule sits inside `@media (hover: hover) and (pointer: fine)`. [EMIL]
  39. Toasts and toggles use CSS transitions, not keyframes. Drawer and sheet animate a full transform string, not framer x/y shorthands. Only transform, opacity, clip-path, filter and background-color animate; the one exception is the node error block's height. [EMIL]

Chrome:
  40. The browser's own surfaces are themed: ::selection, caret-color, scrollbar-color on the drawer, palette and code, the focus ring, underline offset, tabular numerals, and color-scheme per theme. [IMP]

Charts:
  41. N/A. The surface carries no data marks; the KPI band is figures only. [IMP]
  42. N/A, for the same reason. [IMP]
  43. N/A, for the same reason. [IMP]

Verify:
  - Screenshot at 375, 768 and 1280 through browser-harness, in both light and dark. 375 also covers the brief's 390 floor.
  - First navigation is new_tab(<dev server url>); never goto_url.
  - Report each width pass/fail with the cause of any failure.

  States to exercise:
  - Switch workspace to "Support desk" (empty) and "Marketing" (error), and load `?state=loading`.
  - Confirm the error copy says the source could not be read, and that the KPI band shows no zeros.

  Retry flows:
  - Open the F1 run and press Retry run. Watch the replay end in "Retry failed" with a toast that stays put.
  - Open the F2 run and retry. It should end in "Retry succeeded". That toast auto-dismisses at 10s and pauses on hover.
  - Run "Retry last failed run" from the palette 4 times quickly. No more than 3 toasts are visible, and stack hover expands them.

  Keyboard-only pass:
  - Tab order runs header, refresh, "{f} failed", toolbar, rows.
  - ⌘/Ctrl-K opens the palette with no animation, and arrows move the highlight instantly.
  - Enter on a row opens the drawer instantly. Esc closes it instantly and returns focus to the row.
  - Arrow keys switch tabs with no indicator slide. A menu opened from the keyboard appears without animation.

  Pointer pass, then repeat in the DevTools Animations panel at 10% speed:
  - Menus scale from the trigger corner.
  - The drawer takes 360ms in and 240ms out.
  - The tab indicator clip slides in 250ms, and the text colour changes in sync with no double state.
  - No ease-in anywhere, and every exit is shorter than its entrance.

  Emulate prefers-reduced-motion: reduce:
  - Drawer, toasts and menus fade only.
  - Spinners pulse instead of spinning.
  - The replay is still readable.

  At 375, sheet and toasts:
  - A flick down dismisses the sheet; a short slow drag springs back.
  - A swipe dismisses a toast.
  - Toasts are full width.

  Last checks:
  - Theme switch shows no colour-transition flash.
  - Spot-check the computed contrast of pill labels and ink-2 on the ground in both themes.

Do-not-touch: none. This is a greenfield demo; the stack limits are in Rules.

Handoff: paste under the builder spec's Conventions; the reviewer spec gets Gates + Verify.