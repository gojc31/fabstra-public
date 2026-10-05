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
