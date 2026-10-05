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
