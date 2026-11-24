Upstream: https://github.com/pbakaus/impeccable (Apache-2.0; see LICENSE and NOTICE in this folder). No upstream commit was recorded at install time.

Local edits 2026-09-26 (prompt-audit pass 2, Decision 4, JC):
- SKILL.md frontmatter `description` narrowed: was a broad "use when the user wants to design, redesign, shape, critique..." trigger list; now scopes impeccable to critique/audit/refinement verbs and names it as a reference-only source for the `design-pass` skill (the front door for new UI), per `~/.claude/CLAUDE.md`'s design-pass precedence line.
- SKILL.md (opening paragraph) — removed the migration-relative "Whereas before, your design work would have been safe, timid and measured..." framing and inflated register; kept the substantive instruction (design director stance, production-grade code, clear POV, exceptional craft).
- SKILL.md "Core principles" — removed "Go all out. No hedging, no shortcuts." and "Dream big and bold." boosters (over-apply on current models, and pulled against design-pass's "everything around it stays quiet"); replaced with plain statements of the same intent (deliverable completeness, distinct work within brief constraints).

## Known gaps vs Anthropic skill best practices (audit 2026-10-02)
Upstream text left as shipped; recorded here instead of patched.
- 15 reference files over 100 lines have no table of contents.
- Several reference files are not named in SKILL.md.
- Scripts import npm packages with no package.json and no dependency list in SKILL.md.
- Local change 2026-10-03: the frontmatter description was reworded to remove angle-bracket placeholders.

## Local edits 2026-10-05 (prompt audit)

- U8 reference/overdrive.md: browser section is now "Verify in the browser" with the bounded verify cycle; closing line "Spend the fix batch on those details."
- U15 SKILL.md: step 2 and "Otherwise" route new surfaces to design-pass; no init/new-work from here.
- U17 reference/adapt.md, distill.md, extract.md, harden.md, onboard.md, optimize.md, quieter.md, overdrive.md: removed bold CRITICAL/IMPORTANT/EXTRA IMPORTANT labels, kept sentences.
- U17 reference/distill.md: deleted "Be ruthless."
- U17 reference/adapt.md + optimize.md: real-device line replaced with the emulation sentence.
- U18 reference/audit.md + audit.native.md: IMPORTANT/NEVER block replaced with one actionable-report sentence.

## Local edits 2026-10-18 (Emil Kowalski motion layer, fabstra T3)

- NEW reference/motion-craft.md: the single motion and interaction-feel reference that design-pass, impeccable and Hallmark defer to. Distilled from github.com/emilkowalski/skills at commit 2d22863 (2026-10-11), MIT, Copyright (c) 2026 Emil Kowalski; the MIT notice is carried at the file's end and a value -> file:line source map sits above it. Not an upstream impeccable file.
- reference/animate.md "Timing and easing": pointer line to motion-craft.md added; the `cubic-bezier(0.16, 1, 0.3, 1)` line kept as an example only, with exits on ease-out and bounce limited to momentum gestures.
- reference/craft-floor.md Motion bullet: conditional pointer to motion-craft.md (load it when the work evaluates or changes motion or interaction feel; its never-ship table is the checklist builder specs cite).
- reference/audit.md: motion-craft.md load line after the Diagnostic Scan intro (each never-ship row present is a finding).
- reference/critique.md Hard Invariants: motion-craft.md load line after the browser-inspection invariant, matching audit.md's wording.
- reference/motion-craft.md Never ship: the layout-property row exempts the measured-height accordion (matches emil-skills animate/SKILL.md:85).
- reference/motion-craft.md + design-pass gates.md 31d: keyboard-started = commands fired from the keyboard; field focus states are not (Emil animate/SKILL.md:43,48).
- Pre-edit copies: `C:\Users\<you>\.claude\backups\emil-gov-2026-10-18\skills\impeccable\`.

## Local edits 2026-11-25 (audit 2026-11-24, C7)

- reference/critique.md Assessment B: never run `detect.mjs` on a URL (its URL path, `scripts/detector/engines/browser/detect-url.mjs:27,35`, launches its own Chrome through Puppeteer, against JC's browser-harness rule).
- reference/critique.md overlay step 1: browser-harness `own_tab(url)` replaces the "fall back to a custom Playwright/Puppeteer script" line; no harness means the browser step is reported skipped. Scripts unchanged.
