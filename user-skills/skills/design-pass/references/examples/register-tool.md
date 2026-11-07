# Register example: tool

The dense **tool** register for technical or ops users: a ruled status ledger instead of KPI cards, run detail drawn like the automation canvas, hue reserved for status. Referenced from design-pass step 5(a).

Source: arm A of the 2026-10-18 A/B design trial, copied verbatim below. Both arms got one brief: an "Automation Run Monitor" dashboard screen (header with workspace switcher, search and Cmd/Ctrl-K palette; KPI strip; runs table with status pills and filters; a run-detail drawer with Steps / Logs / Input-Output tabs and Retry; a toast stack; loading, empty and error states; light and dark; React 18 + Vite + TypeScript, plain CSS, framer-motion, lucide-react). JC could not split the two arms on quality. Built result: D:\design-trial-2026-10-18\arm-a.

This is a filled example, not a template: its tokens, copy and seed data belong to that brief.

---

## Design (from design-pass)

Pass: INTERNAL · scope SCREEN · OPEN

Rules (binding):
  The brief's pinned words override every rule below. No eyebrow or kicker label above a heading. No numbered section markers unless the content is a real sequence. No `->` or `→` glyph appended to link or button text. No italic display type. No invented metrics, testimonials, logos, or names. Colours and fonts only from the Tokens block.
  Stack (pinned by the brief): React 18 + Vite + TypeScript, plain CSS with custom properties (one stylesheet per component), framer-motion, lucide-react. No Tailwind, no component library. Open `src/styles/tokens.css` with `/* Hallmark · genre: modern-minimal · macrostructure: index-first (screen) · theme: custom · nav: N4 variant · footer: none */`.

Direction:
  Genre: modern-minimal (impeccable Operate mode: the user is working, not deciding).
  Macrostructure: Index-First, read as a screen layout. The runs ledger is the screen: no hero, no card band, and each run's detail sits behind its row. Hallmark components used: N4 (the search field is the ⌘K palette trigger), C1 outlined chip (filter chips in the ledger), F3 tabular spec sheet (key-value detail inside step nodes). Microinteraction recipes used: palette, toast, tab.
  Hallmark theme: custom. Catalog themes are marketing-page skins. Cobalt is the nearest fit and was rejected: its uppercase mono labels fail gate 12 below (AO55 10a), and a signal accent would compete with status colour.
  Principles: (1) Colour means run status. The chrome is black, white and greys, and every hue on screen is a run state, so scanning for colour means scanning for trouble. (2) Exceptions carry the weight. Succeeded runs stay quiet in an outlined pill. Failed, Maybe sent and Running carry a tint fill and a shape-coded glyph (disc, square, open arc, half-disc), so state reads in greyscale and for colour-blind users. (3) A run is drawn the way it was built. Its steps are node cards on a wire over a dotted canvas, the n8n/Make canvas vocabulary, so a client sees where the run stopped and which steps never ran.
  Boldness: the run path in the drawer's Steps tab (canvas, node cards, wire, failure point, ghosted unreached steps). Everything else stays quiet and disciplined.
  Alignment: left, with numbers right-aligned in the Duration column.
  Changed at review:
    - The KPI strip first came out as four identical stat cards (small label above a big number). That is the SaaS-card kit plus the hero-metric template. It is now one ruled ledger line with the number and an inline label on one baseline, plus failed and maybe-sent counts as filter chips.
    - My first reach was an electric-blue brand accent for buttons, links and focus. It is removed: the primary action is ink, focus is ink, and hue is reserved for status.
    - My first reach was Inter/Geist + JetBrains Mono. It is now Instrument Sans (tabular figures confirmed with fontTools) + Commit Mono, with mono only for logs, JSON and run IDs.
    - My first reach was four equally filled status pills. Succeeded is now outlined and quiet, only exceptions fill, and pill width is fixed so the status column reads as one aligned stripe.
    - Dark theme: a tinted near-black ground became true #000000, with raised surfaces lifted by lightness.
    - Toasts: a 4 s auto-dismiss became 10 s for success (the new table row is the persistent record) and no timer for failure.
    - A left sidebar nav was dropped. This is one screen, and the palette carries navigation.

Tokens (proposed):
  Core (6):
    --ink #000000 / dark #FFFFFF: headings, values, primary fill, focus ring (21:1 on --paper)
    --paper #FFFFFF / dark #000000: ground, table, top bar
    --ink-2 #2E3035 / dark #D6D7DA: body and table text (13.20:1 / 14.59:1)
    --ink-3 #5F636A / dark #9A9DA4: secondary text, placeholders, column headers (6.04:1 on paper, 5.58:1 on paper-2 / 7.73:1, 6.47:1, 6.72:1 on the dark drawer surface)
    --failed-glyph #D7261E / dark #FF5A4F: the failure signal (5.02:1 / 6.83:1 on paper)
    --running-glyph #2563EB / dark #5B8CFF: the in-flight signal (5.17:1 / 6.64:1 on paper)

  Full set (light / dark):
  | token | light | dark | role |
  |---|---|---|---|
  | --surface | #FFFFFF | #141518 | drawer (raised one step by lightness in dark; not a black stand-in) |
  | --surface-pop | #FFFFFF | #1B1C20 | menus, palette, toasts |
  | --paper-2 | #F5F6F7 | #18191C | sunken: tab track, log/JSON blocks, Steps canvas, control hover |
  | --paper-3 | #ECEDEF | #232428 | pressed, skeleton base, disabled fill, dark palette active item |
  | --row-hover | #F8F9FA | #0E0F11 | table row hover |
  | --row-selected | #EEF0F2 | #1A1B1F | row whose run is open in the drawer |
  | --rule | #E6E7EA | #26272B | hairlines |
  | --rule-strong | #C9CBD0 | #3A3C41 | control borders, dashed not-reached wire and node |
  | --ink-hover | #2B2C30 | #E2E3E6 | primary button hover fill |
  | --on-ink | #FFFFFF | #000000 | label on primary fill (21:1; 13.95:1 / 16.36:1 on hover) |
  | --ink-4 | #7A7D84 | #6C6F76 | disabled text only (4.12:1 on paper, 3.52:1 on paper-3 / 4.17:1, 3.08:1); never informational |
  | --focus | var(--ink) | var(--ink) | 2px ring (21:1 on paper, 19.41:1 / 17.58:1 on paper-2, 17.02:1 on dark popover) |
  | --canvas-dot | #D9DBDF | #2A2B2F | Steps canvas dot grid |
  | --skeleton-hi | #F5F6F7 | #2A2B2F | shimmer highlight |
  | --selection | #D9DBDF | #3A3C41 | ::selection background (text keeps its ink) |
  | --scrim | rgba(0,0,0,.24) | rgba(0,0,0,.64) | modal drawer and palette backdrop |
  | --success-glyph / -label / -tint | #12924F / #0B5B33 / #E6F4EC | #34C77B / #7FDCA8 / #0B2417 | label on tint 7.24 / 9.93; glyph on tint 3.53 / 7.51; glyph on paper 4.00 / 9.60 |
  | --failed-glyph / -label / -tint | #D7261E / #A11A14 / #FCEBEA | #FF5A4F / #FF9C94 / #2C0E0C | label 6.81 / 8.88; glyph 4.35 / 5.81; error text on paper 7.86 / 10.44 |
  | --running-glyph / -label / -tint | #2563EB / #1D4BB8 / #E8EEFC | #5B8CFF / #A9C1FF / #0E1A35 | label 6.57 / 9.66; glyph 4.45 / 5.45 |
  | --maybe-glyph / -label / -tint | #B26A00 / #834700 / #FBF0D9 | #F2A93B / #F6C77A / #2A1C06 | label 6.48 / 10.55; glyph 3.75 / 8.30 |
  | --arrival | var(--running-tint) | var(--running-tint) | tint on a newly landed run row |
  Secondary text on any tint stays ≥ 5.19:1 in light and ≥ 6.10:1 in dark. Every pair above was computed (WCAG 2.1) and none is under 4.5:1 for text or 3:1 for glyphs and disabled text.

  --font-ui: "Instrument Sans Variable", "Instrument Sans", system-ui, sans-serif. Every UI string: headings, labels, buttons, table, KPI values. Package: @fontsource-variable/instrument-sans, wght 400-700, roman only (do not load italic). Numeric cells and values use `font-variant-numeric: tabular-nums`.
  --font-data: "Commit Mono", ui-monospace, monospace. Only log lines, JSON and run IDs, 12.5px/20px. Package: @fontsource/commit-mono 400 and 500.
  Type ramp (fixed px, ratio about 1.15):
    12/16 (kbd, tooltip, palette group label, tracking .01em)
    13/18 (secondary, pills, column headers, meta)
    14/20 (body, table, buttons)
    16/24 (toolbar heading "Runs", palette input; 16px avoids iOS zoom)
    20/28 (drawer title, empty and error headings; 600, -0.01em)
    24/30 (KPI values; 500, -0.01em, tnum; 20/26 under 900px)
    Weights: 400 body, 500 labels, buttons, values and workflow names; 600 headings and step names.
  Spacing (4-pt): --space-1 4 · -2 8 · -3 12 · -4 16 · -5 20 · -6 24 · -8 32 · -10 40 · -12 48 · -16 64. Page padding-inline 24 (16 under 768); content max-width 1600, centred.
  Heights: --h-topbar 56 · --h-control 32 (44 under `(pointer: coarse)`) · --h-row 44 · mobile list row min 64 · ledger 72.
  Radius (a Direction choice, ranked by object): --r-xs 4 (kbd, skeleton bars) · --r-sm 6 (chips, menu items, tooltip, tab highlight) · --r-md 8 (buttons, inputs, tab track, code blocks) · --r-lg 10 (popovers, node cards) · --r-xl 14 (palette) · --r-pill 999 (status pills only, which are non-interactive). Drawer radius 0, flush to the viewport edge. Buttons are never stadium-shaped.
  Shadows (light / dark; dark never glows and gets elevation from lightness plus 1px --rule):
    --shadow-node: 0 1px 2px rgba(0,0,0,.06), 0 1px 1px rgba(0,0,0,.04) / none
    --shadow-pop: 0 2px 4px rgba(0,0,0,.04), 0 8px 24px -4px rgba(0,0,0,.12) / 0 8px 24px rgba(0,0,0,.5)
    --shadow-drawer: -12px 0 32px -8px rgba(0,0,0,.12) / none
    --shadow-palette: 0 2px 6px rgba(0,0,0,.06), 0 24px 64px -12px rgba(0,0,0,.28) / 0 24px 64px rgba(0,0,0,.7)
    --shadow-toast: 0 1px 3px rgba(0,0,0,.06), 0 6px 16px -2px rgba(0,0,0,.10) / 0 6px 16px rgba(0,0,0,.5)
  Motion:
    --ease-out: cubic-bezier(0.23, 1, 0.32, 1)
    --ease-in-out: cubic-bezier(0.77, 0, 0.175, 1)
    --ease-drawer: cubic-bezier(0.32, 0.72, 0, 1)
    hover and colour changes use `ease`
    --dur-press 160ms · --dur-hover 120ms · --dur-pop-in 180ms · --dur-pop-out 120ms · --dur-tab 250ms · --dur-drawer-in 400ms · --dur-drawer-out 240ms · --dur-toast-in 400ms · --dur-toast-out 240ms · --dur-fade 150ms · --dur-arrival 1600ms
  Z-index: --z-sticky 10 · --z-drawer 30 · --z-popover 40 · --z-palette 50 · --z-toast 60 · --z-tooltip 70. Menus, tooltips and toasts are portalled to body so no overflow container clips them.
  Breakpoints: 640 · 768 · 900 · 1024.
  Theme: `html[data-theme="light"|"dark"]` sets `color-scheme`. The default follows prefers-color-scheme and is persisted in localStorage under `rm-theme`.

Root overflow: not clipped. html and body keep their default overflow, and `html { scrollbar-gutter: stable }` stops layout shifting when the modal drawer or palette locks body scroll. Overflow is prevented by construction instead:
  - minmax(0,1fr) name track with ellipsis
  - Trigger column hidden under 900, list rows under 768
  - log and JSON blocks use `white-space: pre-wrap; overflow-wrap: anywhere`
  - closed drawer, palette, menus and tooltips are unmounted, not parked offscreen
  A horizontal scroll at any width is a bug the reviewer reports with its cause.

References (0-2 rows):
  none - no external references (a SCREEN pass skips Inspo per step 4).
  Local studies I looked at before writing direction:
    - <scratchpad>\render\type-sample.png: six sans and four mono candidates rendered on this brief's strings.
    - <scratchpad>\render\mock-1280.png: rough first viewport. It confirms that a quiet Succeeded plus filled exceptions reads at a glance.

Layout (first viewport, 1280x800, light; values shown are illustrative and are computed from the seed; glyphs stand in for lucide icons and status marks):
```
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│ [mark] Run Monitor │ Production ⇅                 [⌕ Search workflows and runs   Ctrl K] [☾] │ 56 top bar, sticky, --rule below
├────────────────────────────────────────────────────────────────────────────────────────────┤
│ 25 runs today   │ 78.3% succeeded [■ 3 failed] [◐ 2 maybe sent] │ 4.2 s median duration │ $0.84 AI spend today │ 72 ledger
├────────────────────────────────────────────────────────────────────────────────────────────┤   value 24/500 ink + label 14 ink-3, one baseline; 1px vertical rules
│ Runs 25                                  [Status: All ⌄] [Workflow: All ⌄] [⌕ Filter runs  /] │ 56 toolbar ("Runs" 16/600, count 14 ink-3)
│ Workflow                        Trigger      Status           Started             Duration   │ 36 header, sticky at top:56, 13/500 ink-3, sentence case
│────────────────────────────────────────────────────────────────────────────────────────────│
│ Inbound call summary  Vapi      ⚲ Webhook    (◌ Running    )  10:41:50                38 s › │ 44 rows, --rule separators
│ New lead to CRM  n8n            ⚲ Webhook    (● Succeeded  )  10:39:13               3.8 s › │ Succeeded = outlined pill, label ink-2
│ Invoice reminder email  Make    ◷ Schedule   (■ Failed     )  10:30:02              12.1 s › │ exceptions = tint fill + coloured label
│ Weekly report to Slack  n8n     ◷ Schedule   (◐ Maybe sent )  10:00:00               6.4 s › │
│ … 10 more rows visible above the fold                                                        │
└────────────────────────────────────────────────────────────────────────────────────────────┘
Columns ≥900: minmax(0,1fr) | 136 | 136 | 152 | 104 right | 32 chevron.
768-899: Trigger column hidden; its 14px icon (with sr-only text) moves before the workflow name.
Pills: fixed 112px wide, 22px tall, padding-left 8, 10px glyph, 6px gap, label 13/500.
```
Drawer (pointer-opened from a row; ≥1024: non-modal 520px panel with no scrim and the table stays live; 640-1023: modal 520px + scrim; <640: full-screen modal):
```
┌──────────────────────────────────────────────────┐
│ (■ Failed)  run_7f3a9c [copy]                [×] │ 16/20 padding
│ Invoice reminder email                           │ 20/600 ink
│ ◷ Schedule   Started 10:30:02   Took 12.1 s   Make │ 13 ink-3 labels, ink-2 values, 16px gaps (no middle dots)
│ ┌──────────────────────────────────────────────┐ │ callout on --failed-tint, r-md, no side stripe
│ │ ■ Stopped at step 2, Draft reminder with AI: │ │
│ │   OpenAI returned 429 Too Many Requests.     │ │
│ └──────────────────────────────────────────────┘ │
│ [  Steps  |  Logs  |  Input/Output  ]            │ segmented tabs, 32 tall, track --paper-2
├──────────────────────────────────────────────────┤
│ ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  │ canvas: --paper-2 + 1px dot grid every 16px
│  ┌────────────────────────────────────────────┐  │
│  │ [◷] 1  Schedule fired              0.1 s ● │  │ node card, r-lg, --shadow-node
│  └──o─────────────────────────────────────────┘  │
│     │  wire, traversed: 2px --ink-3              │
│  ┌──o─────────────────────────────────────────┐  │ border 1px --failed-glyph, expanded by default
│  │ [AI] 2  Draft reminder with AI    11.9 s ■ │  │
│  │   Error   429 Too Many Requests …          │  │ F3 spec rows (dt 13 ink-3 / dd 13 ink-2)
│  │   View in logs                             │  │
│  └──o─────────────────────────────────────────┘  │
│     ┊  wire, not reached: 2px dashed --rule-strong│
│  ┌┄┄o┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┐  │ dashed border, transparent fill, text ink-3
│  ┆ [✉] 3  Send email          Not reached ○ ┆  │
│  └┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┘  │
├──────────────────────────────────────────────────┤
│ Retry runs the workflow again with the same input.  [↻ Retry run] │ sticky footer 64, --rule above
└──────────────────────────────────────────────────┘
```
390 / 375 (compact):
```
┌─────────────────────────────────┐
│ [mark] Production ⇅      [⌕] [☾] │ 56: wordmark hidden, switcher max 160px with ellipsis, search = icon button opening the palette
├────────────────┬────────────────┤
│ 25             │ 78.3%          │ ledger 2x2: value 20/500, label 13 ink-3 below the value
│ runs today     │ succeeded      │
├────────────────┼────────────────┤
│ 4.2 s          │ $0.84          │
│ median duration│ AI spend today │
├────────────────┴────────────────┤
│ [■ 3 failed] [◐ 2 maybe sent]   │ chips row
├─────────────────────────────────┤
│ Runs 25                         │
│ [⌕ Filter runs                ] │ full width, 44 tall
│ [Status: All ⌄][Workflow: All ⌄]│ two 50% buttons, 44 tall
├─────────────────────────────────┤
│ Inbound call summary (◌ Running)│ list row, min 64: name 14/500 with ellipsis + pill right
│ ⚲ Webhook   10:41:50   38 s     │ line 2: 13 ink-3, tnum, 12px gaps
├─────────────────────────────────┤
```

Components and states (each ships these states; "n/a" means the state cannot be reached by construction):
- Primary button ("Retry run", "Try again"): ink fill, --on-ink label 14/500, r-md, h 36 desktop / 44 coarse, padding 0 14, 16px icon left.
  - hover: --ink-hover
  - focus-visible: 2px --focus outline, offset 2px, instant
  - active: scale(.97)
  - disabled: --paper-3 fill, --ink-4 label, `aria-disabled`, not-allowed cursor, with a visible reason in the footer helper. Succeeded run: "This run succeeded. There is nothing to retry." Running run: "Retry is available when this run finishes."
  - loading: LoaderCircle spinning replaces the icon, label "Retrying…", `aria-busy`, width locked to the default width, visible at least 400ms
  - success: Check icon + "Retry started" for 2000ms, then default. Helper: "New run started at 10:15:02." plus a "View run" text button.
  - error: label returns to default; helper in --failed-label: "Last retry failed at 10:15:02."
  - Maybe sent: first activation changes the label to "Retry anyway" and the helper to "Slack may get this post twice. Check the channel first." A second activation retries. Blur out of the footer or Esc reverts. No timer.
- Secondary button ("Clear filters", "Copy logs", "Copy error details", "Switch workspace", filter triggers): transparent, 1px --rule-strong border, ink-2 label.
  - hover: --paper-2
  - focus-visible: ring
  - active: scale(.97) + --paper-3
  - disabled: --rule border, --ink-4 label
  - loading: spinner replaces the icon
  - success (copy buttons): Copy icon becomes Check and the label becomes "Copied" for 2000ms
  - error: "Couldn't copy" for 2000ms, with a failed glyph
- Icon button (close, theme, copy run ID, mobile search): 32 visual, 44 hit area on coarse pointers via an `::before` inset of -6px, r-md, 16px icon ink-2, `aria-label` required. Same states as secondary; loading and success apply only to copy.
- Search trigger (header; a `<button>` styled as a field, 300px): 1px --rule-strong border, magnifier, placeholder text "Search workflows and runs" in ink-3, kbd chip "⌘K" on Mac or "Ctrl K" elsewhere (12px, r-xs, --paper-2).
  - hover: --paper-2
  - focus-visible: ring
  - active: --paper-3 (no scale on a wide control)
  - disabled, loading, error, success: n/a
- Filter input ("Filter runs"): border 1px --rule-strong in every state, with a transparent 2px outline reserved so focus never shifts layout.
  - hover: --paper-2
  - focus: 2px --focus outline, offset 1px
  - disabled: while workspace data loads, opacity .55
  - Matches workflow name or run ID, debounced 120ms. A clear "x" appears when there is a value. A "/" kbd hint shows when empty (desktop only), and "/" focuses the field.
  - Result count updates "Runs 8 of 25" (aria-live polite).
  - loading, error, success: n/a
- Dropdown trigger + menu (Workspace, Status, Workflow):
  - Trigger: secondary button with "Status: All" (label ink-3, value ink-2 500, ChevronDown 14). Open state: --paper-2 + `aria-expanded`. Active filter: value reads "Failed" or "2 selected" with ellipsis.
  - Menu: --surface-pop, 1px --rule, --shadow-pop, r-lg, padding 4, min-width 240 (max: 100vw - 32).
  - Items: 32px (44 coarse), r-sm, 14px. Status items: checkbox + glyph + label + count right (tnum ink-3). The Workflow menu adds a "Find workflow" input on top (8 workflows) and a "Clear" text button at the bottom.
  - Selection filters live and the menu stays open for multi-select.
  - Item states: highlighted --paper-2 (instant); keyboard highlight also adds a 2px inset --focus outline; pressed --paper-3; checked shows a Check icon; disabled shows --ink-4.
  - Keys: arrows, Home/End, typeahead, Space toggles, Esc/Tab/outside-click closes and focus returns to the trigger.
  - Workspace items: Production "25 runs today"; Staging "No runs yet"; Sandbox "Source unreadable" with a failed glyph. Choosing one shows the loading skeleton.
- Ledger chips ("3 failed", "2 maybe sent"; C1 outlined chip): 24px tall, r-sm, 1px --rule-strong, 8px glyph + 13/500 ink-2.
  - hover: --paper-2
  - focus: ring
  - active: scale(.97)
  - pressed (filter applied, `aria-pressed=true`): --paper-3 fill + 1px --ink border
  - zero count: the chip is replaced by plain ink-3 text, e.g. "No failures"
- Table row (CSS-grid rows with role=table/rowgroup/row/columnheader/cell; the name cell holds `<button class="row-open">` with a stretched ::after covering the row):
  - hover: --row-hover; the chevron (ink-4) goes from opacity 0 to 1
  - focus-visible: 2px inset --focus ring on the row via `:has(.row-open:focus-visible)`
  - active: --paper-3, instant
  - selected: --row-selected + `aria-current="true"`
  - loading: skeleton row
  - Keys: Up/Down move focus between rows; Enter opens the drawer.
  - Running rows tick their elapsed duration once per second in ink-3 (aria-live off).
  - disabled, error, success: n/a (state lives in the pill)
- Status pill: non-interactive display, fixed 112px.
  - Succeeded: transparent fill, 1px --rule, --success-glyph disc, --ink-2 label.
  - Failed: --failed-tint fill, square glyph, --failed-label.
  - Running: --running-tint fill, open-arc glyph that spins, --running-label.
  - Maybe sent: --maybe-tint fill, half-disc glyph, --maybe-label.
  - Glyphs are authored 12x12 SVG (disc r5; rounded square 8 r1.5; 270° arc stroke 1.75; ring stroke 1.5 with the left half filled), `aria-hidden`; the word carries meaning.
  - In the drawer, a not-reached step uses a hollow --rule-strong ring and the text "Not reached".
- Segmented tabs (Steps / Logs / Input/Output; WAI tabs with automatic activation): track --paper-2, r-md, padding 2; tabs equal width, min 88; label 13/500.
  - default: ink-3 label
  - hover: ink-2 label
  - selected: ink label on a --surface (dark: --paper-3) highlight, r-sm, --shadow-node
  - focus-visible: ring offset 1px
  - active: scale(.97)
  - loading: the panel shows a skeleton for 300ms on first Logs open
  - error: the panel reads "Couldn't load logs for this run." with "Try again"
  - Input/Output for a running run: "Output appears when the run finishes."
  - disabled, success: n/a
- Step node card (a button with `aria-expanded`; F3 rows inside): r-lg, 1px --rule, --surface, --shadow-node, min-height 64, padding 12 14, grid `36px 1fr auto`, gap 12.
  - Icon tile: 36px, r-md, --paper-2, lucide 18 ink-2.
  - Line 1: step number 12 ink-3, then name 14/600 ink.
  - Line 2: meta 13 ink-3 as separate spans with 12px gaps, e.g. "OpenAI   1,240 tokens   $0.004".
  - Right side: duration 13 tnum ink-3 + glyph.
  - hover: --rule-strong border
  - focus: ring
  - active: scale(.985)
  - expanded: dl rows + "View in logs" text button (underline offset 3px), which switches to Logs, centres the line and tints it
  - failed: border --failed-glyph. Maybe sent: border --maybe-glyph + explanation. Running: border --running-glyph.
  - disabled = not reached: dashed --rule-strong border, transparent fill, `aria-disabled`, not expandable
  - Failed and Maybe sent nodes start expanded.
  - Wire: 2px wide, centred under the icon tile (x = 31px from the card's left), spanning the 20px gap. 8px port dots (--surface fill, 2px border in the wire colour) at the bottom of node n and the top of node n+1. Traversed wires are solid --ink-3; unreached wires are dashed --rule-strong. The wire into a running step carries the pulse described under Motion.
- Logs panel: --paper-2, Commit Mono 12.5/20, padding 12 16. Columns: time (ink-3, 96px), level (40px: INFO ink-3, WARN --maybe-label, ERROR --failed-label), message ink-2, pre-wrap. "Copy logs" at the top.
- Input/Output panel: headings "Input" and "Output" (13/600). Each block is --paper-2, r-md, padding 12, Commit Mono: keys ink-3, strings ink, numbers and booleans ink-2 500. Hue is never used for syntax. A copy icon button sits top-right of each block. A failed run's output reads "No output. The run stopped at step 2."
- Command palette (native `<dialog>` with showModal(), opened by ⌘K/Ctrl+K or a click on the search trigger):
  - Panel: centred, top 14vh, width min(640px, 100% - 32px), r-xl, --surface-pop, 1px --rule, --shadow-palette, --scrim backdrop.
  - Input row: 52px, 16px text, placeholder "Search workflows, runs and commands", Esc kbd chip.
  - Listbox: max-height 360 (60dvh on mobile), `aria-activedescendant`. Group labels "Workflows" and "Commands" (12/500 ink-3, sentence case).
  - Items: 40px, r-md, inset 6; icon 16 + label 14 + right meta. Workflows show platform + last-run glyph; "Retry last failed run" shows workflow + time.
  - Commands: "Retry last failed run", "Show failed runs", "Switch to dark theme" / "Switch to light theme"; workflows: "Go to New lead to CRM" (applies the Workflow filter and closes).
  - Item states: highlighted --paper-2 (dark --paper-3); pressed --paper-3; disabled "Retry last failed run" with no failures shows --ink-4 and meta "No failed runs today".
  - Empty: "Nothing matches “{q}”. Try a workflow name, a run ID, or “retry”."
  - Focus returns to the opener on close.
- Toasts (Sonner-style stack): region fixed bottom 24 / right 24, width 360 (<640: inset 16 + safe-area), max 3, role="region" aria-label "Notifications". Each toast: --surface-pop, 1px --rule, --shadow-toast, r-lg, padding 12 14, grid `16px 1fr auto`; title 14/600, body 13 ink-3; text-button action; close icon button always visible.
  - Success: role="status", success disc, auto-dismiss after 10 s. The timer pauses on region hover or focus-within and while document.hidden, and resumes with the remaining time.
  - Failure: role="alert", failed square, no timer.
  - Hover: the stack expands and the timer pauses.
- Skeleton (initial load and workspace switch): appears after a 150ms delay and stays at least 300ms. Ledger shows value bars 56x20 and label bars 80x12; the table shows 8 rows of bars at column widths (pill-shaped 112x22 in Status). Toolbar controls are disabled, and the header stays real.
- Empty (Staging): small lucide Workflow icon (24, ink-3); heading "No runs in Staging yet" (20/600); body "Runs appear here a few seconds after a workflow in Staging is triggered by its schedule or a webhook." (max 62ch); action: secondary "Switch workspace", which opens the switcher.
- Filtered empty: "No runs match these filters." + "Clear filters".
- Error, source unreadable (Sandbox): failed square glyph (24); heading "Couldn't read runs from n8n"; body "Run Monitor could not read the run history for Sandbox. n8n answered 401 Unauthorized at 10:14, so its API key may have been revoked. Your workflows may still be running."; actions: primary "Try again" (loading state) + secondary "Copy error details". The ledger shows "—" in every value with an aria-label like "Runs today unavailable"; never zeros.
- Partial source (`?state=partial`): a banner above the table on --maybe-tint, r-md, maybe glyph: "Make runs could not be read since 10:02. Showing runs from n8n, HighLevel and Vapi only." + "Try again".
- Product mark: authored 20px SVG of two filled r3 dots joined by a 2px wire, in --ink, + "Run Monitor" 15/600 at -0.01em.
- Icons: lucide-react only, size 16, strokeWidth 1.75 everywhere (18 in node tiles).
  - Clock: Schedule
  - Webhook: Webhook
  - BrainCircuit: LLM step (never Sparkles)
  - Send: Slack post
  - Mail: email
  - MessageSquare: SMS
  - PhoneCall: Vapi call
  - Database: CRM
  - RotateCcw: retry
  - ChevronsUpDown, ChevronDown, ChevronRight, X, Copy, Check, Search, Sun, Moon, LoaderCircle, ListFilter

Motion (sourced from motion-craft.md; keyboard-started and 100+/day actions never animate. A tiny input-modality hook records the last input as pointer or keyboard, and each overlay reads it at open time):
| # | Element | Trigger | Property: from → to | Duration · curve | Reduced motion |
|---|---|---|---|---|---|
| 1 | Every button, chip, icon button | pointer :active | transform scale(1) → scale(.97) | 160ms --ease-out | scale dropped; colour kept |
| 2 | Buttons, rows, chips, node cards, menu items | hover inside `@media (hover:hover) and (pointer:fine)` | background-color, border-color, color | 120ms ease | same |
| 3 | Row, menu, palette item highlight and press | pointer or arrow keys | background-color | 0ms (instant) | same |
| 4 | Menus (workspace, status, workflow) | pointer open | opacity 0 → 1, scale(.96) → 1; transform-origin at the trigger corner (top left or top right; bottom when flipped) | in 180ms --ease-out; out 120ms --ease-out to opacity 0, scale(.98) | opacity only, 120 / 80ms |
| 5 | Same menus | keyboard open (Enter, Space, ArrowDown) or Esc close | none | instant | instant |
| 6 | Command palette + backdrop | ⌘K/Ctrl+K or click | none | instant open and close | instant |
| 7 | Drawer | row click | framer `transform: "translateX(100%)" → "translateX(0%)"` as a full transform string | in 400ms --ease-drawer; out (close button or scrim) 240ms --ease-out | opacity 0 → 1, 150ms ease-out, no translate |
| 8 | Drawer scrim (<1024) | with the drawer | opacity 0 → 1 | 400ms --ease-out in / 240ms out | 150ms |
| 9 | Drawer | Enter on a row, Esc, J/K between runs, clicking another row while open | none; content swaps instantly | instant | instant |
| 10 | Tab highlight (duplicate tab list layer; clip-path set to the active tab's bounds) | pointer click | clip-path: inset(...) | 250ms --ease-in-out | instant |
| 11 | Tab highlight + panel | arrow keys; panel content on any change | none | instant | instant |
| 12 | Step node expand | pointer | grid-template-rows 0fr → 1fr + opacity; chevron rotate 0 → 180° | 200ms --ease-out; collapse 150ms --ease-out | height instant, opacity 120ms |
| 13 | Running arc glyph | while running | transform rotate 0 → 360° | 1000ms linear, infinite | static arc |
| 14 | Running wire pulse (drawer) | while a step runs | 8px --running-glyph segment inside an overflow-hidden wire, transform translateY(-8px → 28px) | 1100ms linear, infinite | static solid --running-glyph wire |
| 15 | Toast enter | toast created | translateY(100%), opacity 0 → its stack slot via `@starting-style` (data-mounted flag as fallback) | 400ms ease | opacity only, 200ms |
| 16 | Toast stack (collapsed / expanded) | new toast; region hover, focus-within or tap | collapsed: toast i at translateY(i * -10px) scale(1 - i*.05), origin bottom centre, older toasts' content opacity 0 and height clamped to the front toast. Expanded: translateY(-(sum of newer heights + 8*i)px) scale(1), content opacity 1 | 400ms ease, CSS transitions only (never keyframes) | transform instant, opacity 150ms |
| 17 | Toast exit | close, timeout, swipe | translateY(calc(100% + 24px)), opacity 0 | 240ms --ease-out; a 4th toast evicts the oldest with opacity only, 200ms --ease-out | opacity 150ms |
| 18 | Toast swipe (drag offset lives on an inner wrapper so it never fights the stack transform) | pointer drag down after 10px of travel | translateY follows the pointer 1:1; upward drag rubber-bands | release: dismiss if dy > 45px or velocity > 0.11 px/ms (continue 200ms --ease-out), else framer spring `{type:"spring", bounce:0.2, duration:0.4}` back to 0 (the only bounce, earned by momentum) | snap back 150ms --ease-out |
| 19 | AUTHORED MOMENT: retry lands | "Run retried" | new row inserted at the top; existing rows FLIP via framer `layout="position"`; new row opacity 0 → 1 with --arrival background held 600ms, then faded to transparent | rows 280ms --ease-out; new row 200ms --ease-out; tint fade 1600ms --ease-out | no FLIP (rows jump); opacity 150ms; tint fade kept |
| 20 | Status resolution (a Running row resolves; seeded rows resolve 6 s and 11 s after load) | status change | pill inner layer crossfade: opacity + filter blur(0 ↔ 2px); pill background-color and border-color | 200ms ease | opacity 150ms, no blur |
| 21 | Skeleton shimmer | while loading | ::after gradient translateX(-100% → 100%) | 1600ms linear, infinite | static |
| 22 | Skeleton → content | data arrives | opacity 0 → 1 (no translate) | 150ms --ease-out | same |
| 23 | Tooltip (truncated names, full timestamps) | hover after 700ms (instant within 400ms of the last tooltip closing) / keyboard focus at 0ms | opacity, scale(.97) → 1, origin toward the trigger | 125ms --ease-out in, 80ms out; keyboard focus shows it with no animation | opacity only |
| 24 | Log line from "View in logs" | click | background-color --failed-tint → transparent (hold 600ms) + scrollIntoView(center) | 1600ms --ease-out; smooth scroll | auto scroll; tint kept |
| 25 | Theme toggle | click or palette | none: `[data-theme-switching] * { transition: none !important }` for one frame | instant | instant |
| 26 | Focus rings | focus | none | instant, always | same |
KPI values never tick or count up; a value change is instant. There is no page-load entrance choreography. Name every transitioned property; `transition: all` is banned. Use `will-change` only after a measured dropped frame.

Copy (one name per action through the flow):
- Retry: "Retry run" → "Retrying…" → toast "Run retried" with body "A new run of {workflow} started at {time}." and action "View run". For a Maybe sent run, the body adds "Check Slack for a duplicate post."
- Retry failure: "Retry failed" with body "n8n refused the retry because Invoice reminder email is turned off. Turn it on in n8n, then retry." and action "Retry again".
- Maybe sent explanation: "Slack did not confirm this post within 10 seconds. It may have been delivered. Check the channel before retrying, or it may post twice."
- Failed callout: "Stopped at step {n}, {step}: {cause}."
- Running callout: "Running for {elapsed}. Step {n} of {total}: {step}."
- Status words: Succeeded, Failed, Running, Maybe sent.
- Durations: "3.8 s" (one decimal under 10 s), "41 s", "1 min 12 s".
- Started: "10:41:50" today, "Yesterday 17:03" yesterday; full date in a tooltip.
- Sentence case everywhere. Curly quotes and a real ellipsis (…).

Data and review harness:
- `src/data/seed.ts` starts with the comment "Demo data". It holds 25 Production rows, timestamped relative to page load so every row is today: 18 Succeeded, 3 Failed, 2 Running, 2 Maybe sent.
- 8 workflows (task names, no company or person names):
  - New lead to CRM (n8n)
  - Missed-call text back (HighLevel)
  - Appointment reminder call (Vapi)
  - Invoice reminder email (Make)
  - Weekly report to Slack (n8n)
  - Review request SMS (HighLevel)
  - Inbound call summary (Vapi)
  - Lead enrichment (Make)
- Each run has 3-5 steps; the brief's chain "trigger, LLM step, Slack post" appears on New lead to CRM. Each run carries an aiCostUsd.
- Retrying Invoice reminder email always fails (failure toast). Every other retry succeeds: a new Running row lands, then resolves to Succeeded after 3 s.
- KPIs are computed from the rows:
  - runs today = row count
  - success rate = Succeeded / (Succeeded + Failed + Maybe sent)
  - median duration of finished runs
  - AI spend = sum of aiCostUsd
- Staging has no rows (empty state). Sandbox is unreadable (error state).
- URL params: `?state=loading|empty|error|partial` and `?theme=light|dark`.
- Shortcuts:
  - ⌘K/Ctrl+K: palette
  - "/": filter input
  - Up/Down + Enter: rows
  - J/K: previous/next run while the drawer is open
  - Esc closes the topmost layer: tooltip, then menu, then palette, then drawer
- Drawer focus: on open, focus goes to the drawer title (tabindex -1). On close, it returns to the row button. Under 1024 the drawer is modal: focus trapped, `inert` background, body scroll locked.

Gates (reviewer runs these on the built result; N/A is written, not skipped):
  1. The screen shape is Index-First as named: the runs ledger is the screen. No hero, no feature-card band, no marketing rhythm. [HM gate 8]
  2. No card is nested inside another card (node cards sit on the canvas panel, not inside a card), and identical cards are not the screen's only structural device. [HM gate 4] [IMP]
  3. No eyebrow, kicker, or category label sits above a heading. Palette group labels are listbox headers, and the ledger labels sit inline after the number. [FD] [IMP]
  4. Numbered markers appear only on drawer steps, which are a real sequence. [FD]
  5. Nav and footer are not the AI defaults: the app bar has no inline link row and no CTA button. Footer: N/A (the screen has no footer). [HM gates 42, 43]
  6. Buttons are not stadium-shaped: buttons use 8px (r-md), and the stadium shape is only on non-interactive status pills, a named choice. [AO55]
  7. Regions are separated by decided devices: hairlines between bar, ledger and table; vertical rules between ledger cells; a colour shift plus dot grid for the Steps canvas. [HM gate 9]
  8. Prose measure never exceeds 75ch at any width. Empty and error bodies and drawer callouts are capped at 62ch at 768 and 1280, and fill the width minus gutters at 375. [FD] [IMP]
  9. Headings and display type are roman; no italic face is loaded. [HM gate 38a]
  10. No single word in a heading is accented by italic, bold, or colour. [FD]
  11. At most three families: Instrument Sans + Commit Mono (2). [HM gate 37]
  12. Monospace appears only on log lines, JSON and run IDs; never on labels, pills, kbd chips, durations or timestamps. [AO55]
  13. KPI values (24/500) and drawer titles (20/600) step clearly above 14/400 body, and every heading wraps inside its container at 375. [HM gate 51] [IMP]
  14. Body text clears 4.5:1, and glyphs, focus rings and large text clear 3:1, against their computed background in both themes (Tokens table). [HM gate 40]
  15. Interactive text keeps ≥ 4.5:1 on its own fill in every state, including hover. Disabled text keeps ≥ 3:1. [HM gate 41]
  16. No gradient text anywhere, including `background-clip: text`. [HM gate 2] [IMP]
  17. Black is black: light --ink and the dark ground are #000000, and raised dark surfaces are named lifted greys, not near-black stand-ins. [FD]
  18. The ground is #FFFFFF / #000000 by Direction choice; no cream or off-white page ground. [AO55]
  19. Every colour and every `font-family` references a named token; no inline hex, rgba, oklch or font stack outside tokens.css. [HM gate 48]
  20. Every number on screen is computed from the seed (flagged "Demo data"). No marketing metrics, logos or testimonials. [HM gate 46]
  21. An action keeps one name through the flow: "Retry run", "Retrying…", "Run retried" / "Retry failed"; "Clear filters"; "Switch workspace". [FD]
  22. Controls name what happens, and the source-unreadable error names the source, the failure and the recovery. It never says "no runs". [FD] [IMP]
  23. No placeholder people or startup-cliché names. Workflows are task names; workspaces are Production, Staging and Sandbox. [HM gate 19]
  24. No `->` or `→` glyph appended to any link or button text. [FD]
  25. Every interactive component ships every state in the Components and states list, and the states marked n/a cannot be reached. [HM gate 26]
  26. Loading skeleton, empty (Staging), filtered-empty, error (Sandbox) and partial-source states all ship with real copy, not a spinner alone. [IMP]
  27. Focus is visible and instant on every control: a 2px --focus ring at ≥ 3:1 that never fades in. [HM gate 15]
  28. No horizontal scroll at 375, 390, 768 or 1280, in both themes, with the drawer open and closed. Any failure is reported with its cause, not hidden by clipping the root. [HM gate 34]
  29. No button label, tab label, filter trigger, pill label or palette item wraps to two lines at any tested width. [HM gate 49]
  30. Grid tracks holding images: N/A (no images). The table's name track uses minmax(0, 1fr). [HM gate 50]
  31. At 1280x800 the top bar, the full KPI ledger, the toolbar and at least 10 run rows are visible without scrolling. [HM gate 44]
  32. One authored motion moment (the retry landing, row 19). No entrance animation on page load, and no fade-and-slide on regions. [FD] [IMP]
  33. Every transform and keyframe has the `prefers-reduced-motion: reduce` fallback listed in the Motion table. [HM gate 27]
  34. No `transition: all` and no uniform hover-scale. The only bounce is the toast swipe release spring (bounce 0.2). [HM gates 10-12] [EMIL]
  35. No UI enters or exits on `ease-in`. Exits are shorter than entrances; toast entry on 400ms `ease` passes. [EMIL]
  36. No entrance starts from scale(0): menus start at .96 and tooltips at .97; the drawer and toasts translate. [EMIL]
  37. Menus and tooltips scale from their trigger (transform-origin at the trigger corner); the palette stays centred. [EMIL]
  38. Keyboard-started and 100+/day actions change state with no animation: palette open and close, drawer open by Enter or close by Esc, J/K, arrow navigation in rows, menus, palette and tabs, keyboard-opened menus, and theme toggle. [EMIL]
  39. No hand-drawn browser bar, phone frame, terminal or IDE chrome; the log panel is a plain sunken block. [HM gate 47]
  40. Browser surfaces are themed: ::selection (--selection), caret-color (--ink), thin scrollbars (`scrollbar-color: var(--rule-strong) transparent`), focus ring, link underline offset 3px, tabular numerals on every number column, and `accent-color: var(--ink)` on checkboxes. [IMP]
  41. Every decorative element has a semantic anchor: the dot grid appears only on the Steps canvas (the workflow canvas), and the product mark is two nodes and a wire. [HM gate 45]
  42. Charts: N/A. The screen has no charts or data marks; the ledger is text figures. [IMP]
  43. Chart mark match: N/A, no charts. [IMP]
  44. Series per chart: N/A, no charts. [IMP]

Verify:
  Screenshot at 375, 768, 1280 through browser-harness (also at 390, the brief's floor), in light and dark.
  First navigation is new_tab(<dev server url>); never goto_url.
  Report each width pass/fail with the cause of any failure.
  Exercise every state: `?state=loading`, `?state=empty`, `?state=error`, `?state=partial`; switch workspaces Production, Staging, Sandbox.
  Walk the flows:
  - Click a Failed row: the drawer slides in, the failed node is expanded and the wire turns dashed after it.
  - Press Enter on a focused row: the drawer appears with no animation. Esc closes it instantly and focus returns to the row.
  - Retry a failed New lead to CRM run: the button shows loading then success, the "Run retried" toast appears, the new row lands with FLIP and the arrival tint, then resolves to Succeeded.
  - Retry Invoice reminder email: the "Retry failed" toast appears and has no timer.
  - Retry a Maybe sent run: the two-step "Retry anyway" appears.
  - Fire 4 retries quickly: the stack caps at 3, the oldest evicts, and hover expands the stack.
  - Ctrl+K opens the palette instantly; "Retry last failed run" and "Switch to dark theme" both work.
  - Keyboard through the Status menu, then click it open: the click animates from the trigger, the keyboard open does not.
  Emulate `prefers-reduced-motion: reduce` and repeat the drawer, toast and retry flows.
  In DevTools Animations at 5x slow, confirm the menu origin is at the trigger, the drawer curve has no slow start, and the toast and stack transforms stay in sync.
  Check the ledger's counts and success rate match the table rows exactly.
  Check computed `font-variant-numeric: tabular-nums` and digit alignment in Started and Duration.

Do-not-touch:
  none. Greenfield, with the stack pinned by the brief (React 18 + Vite + TS, plain CSS, framer-motion, lucide-react; no Tailwind, no component library).

paste under the builder spec's Conventions; the reviewer spec gets Gates + Verify