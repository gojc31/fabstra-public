Vendored from https://github.com/Nutlope/hallmark  path skills/hallmark  commit 13ac0ec7e148  on 2026-09-20. Licence: MIT, full text in ./LICENSE (copyright Together AI and contributors) - keep it with any copy.
Local edit: SKILL.md frontmatter `description` narrowed so the `design-pass` skill is the front door for new UI. Everything else is upstream verbatim.
Re-sync: clone, checkout the new commit, copy skills/hallmark and LICENSE over this folder, re-apply the description edit, update the commit here.
Original description: Anti-AI-slop design skill for greenfield pages, audits, redesigns, and design extraction from URLs or screenshots. Use when the user asks to build a new app or landing page, wants to redesign something, invokes Hallmark by name, or uses audit/redesign/study.

Local edits 2026-09-26 (prompt-audit pass 2, Decision 4, JC):
- SKILL.md:282 (theme axis values) — removed the dead link to `site/css/tokens.css` (never vendored); now points to `references/themes/<theme>.md` when it exists, else says to state an estimate.
- SKILL.md:389-391 — removed the "Human-only (do NOT auto-load)" block linking `../../docs/recipes.md` and `../../docs/study-examples.md`; neither file was vendored.
- SKILL.md:430 (Slop-test preview row) — was self-contradictory (told the model to run Step 7 before Build in a pre-Build preview row); now says `pending (run after Build)` pre-build, filled in after Step 7.
- SKILL.md:272 — "Specimen ... is no longer a default" (migration-relative) reworded to "Specimen ... is opt-in".
- SKILL.md:357 — dropped the "~30 lines ... vs. 660 lines for the old monolith" maintainer-history aside.
- SKILL.md:294 — dropped "the single most-violated rule in practice" and the Curio/Sprout/Tally/Mixtape upstream test-harness example from the nav/footer diversification rule; kept the rule itself.
- SKILL.md:228 — collapsed the stacked "There is no ... exception" sentences into one plain sentence carrying the same rule.

## Known gaps vs Anthropic skill best practices (audit 2026-10-02)
Upstream text left as shipped; recorded here instead of patched.
- SKILL.md body is 549 lines (guide: under 500).
- 25 reference files over 100 lines have no table of contents.
- Component and macrostructure files sit two levels deep from SKILL.md.
- Local change 2026-10-03: the frontmatter description was reworded to remove angle-bracket placeholders.

## Local edits 2026-10-05 (prompt audit)

- U3 references/custom-theme.md: catalog-axes sentence now points at references/themes/<theme>.md or SKILL.md Step 2; dropped tokens.css links (site/ never vendored).
- U3 references/themes/cobalt.md: dropped tokens.css and site/examples/cobalt-01 link clauses (lines 5, 146).
- U3 references/themes/carnival.md: dropped tokens.css link clause.
- U3 references/themes/lumen.md: dropped tokens.css link sentence.
- U3 references/themes/hum.md: dropped tokens.css link sentence.
- U3 references/hero-enrichment.md: dropped two site/_tests links from the Tracejam and Maple Street examples.
- U4 SKILL.md: "Build with this DNA" builds from studied DNA, stamps theme: studied-DNA; both stamp examples updated.
- U5 references/anti-patterns.md: gradient-fill fix says weight, accent colour, or display face (no italic).
- U7 SKILL.md: description routes redesigns to design-pass; direct use is audit or study.
- U13 references/macrostructures.md + macrostructures/10-specimen.md: Specimen marked opt-in.
- U14 references/themes/lumen.md: dropped "previous italic-pivot retired" clause; CSS comment "upright only".
- U14 references/themes/hum.md: dropped "the old" history clauses; first-paint wobble rule restated.
- U14 references/slop-test.md: dropped "(the old Manifesto / Sport / Brutal default)".
- U16 SKILL.md: default mode row routes new UI to design-pass.

## Local edits 2026-10-18 (Emil Kowalski motion layer: motion precedence)

Motion and interaction feel now defer to `../impeccable/reference/motion-craft.md`, distilled from github.com/emilkowalski/skills at commit 2d22863 (MIT). Where a Hallmark motion line and motion-craft disagree, motion-craft wins. Pre-edit copies: `~/.claude/backups/emil-gov-2026-10-18/skills/hallmark/`.
- SKILL.md Step 6 "Always" motion lines: the easing mandate defers to motion-craft (`--ease-out` for entrances and exits, `--ease-in-out` for on-screen moves, `ease` for hover and colour, no ease-in on UI, bounce only on a momentum gesture's spring); `transform`/`opacity` is the default, not an absolute; a Motion precedence line puts motion-craft over every Hallmark motion rule (these lines, motion.md, microinteractions.md, the component and craft references, slop-test gate 14; slop-test.md itself unedited), naming its property exceptions and component curves (measured-height accordion, `clip-path` reveal, Sonner-style toast on `ease`).
- references/motion.md: deference line at the top; `--ease-in` token removed (exits reuse `--ease-out` at the shorter duration); menu close and accordion easing moved to `--ease-out`; the `ease` and `linear` bans narrowed; momentum-gesture spring exception to the bounce ban.
- references/microinteractions.md: the ease-in exit token and the button, toast, modal, menu and tab-content exits moved to `--ease-out`; the `ease` ban narrowed to entrances, exits and moves; key-shortcut opens, keyboard-focus tooltips, arrow-key tab changes and command-palette selection change instantly (frequency gate); focus rings dropped from the 150-200 ms fade row.
- references/export-formats.md: `--ease-in` dropped from the token table and from the tokens.css and Tailwind `@theme` exports, matching motion.md's token set.
- references/components/n13-inline-cmdk-pill.md: palette open/close transitions removed; a command palette is a 100+/day, keyboard-first surface, so no trigger animates it.
- references/components/n11-mega-menu.md: keyboard-started open or close (Esc, Enter/Space on a trigger) is instant via `.is-instant`; pointer opens keep the fade.
- references/components/n1b-saas-three-section.md: the dropdown transition applies on hover only; keyboard `:focus-within` opens and closes instantly.
- references/components/n11-mega-menu.md and n1b-saas-three-section.md: the menu `transform` transition moved from `var(--ease-spring)` (an overshoot curve that fails design-pass gate 31 and is undefined outside the Hum theme) to `var(--ease-out)`.
- references/microinteractions.md: dropdown Escape close and tooltip Escape dismiss are instant (keyboard-started, design-pass gate 31d).
