# Run record

The file is `.design-pass/log.md` at the project root. It is append-only: one line per pass, added at step 7 after the build has passed review. Never rewrite or reorder earlier lines. Create the directory and the file on the first pass.

One line, pipe-separated, in this field order:

```
date | project | scope | INHERIT/OPEN | inspo calls (n) and total result KB | slugs | screenshot paths | gates failed at review (numbers) | rework rounds | design-pass version | hallmark commit | inspo-mcp version
```

Field notes:

- **date** - `YYYY-MM-DD`, the day the build passed review.
- **project** - the project folder name. On a CLIENT pass this is your redaction token if you used one, never the client's name.
- **scope** - `PAGE`, `SCREEN`, `COMPONENT`, or `EXISTING`.
- **inspo calls (n) and total result KB** - `0 / 0 KB` when step 4 was skipped or Inspo was not connected.
- **slugs** - the exemplar slugs picked, comma-separated; `none` when there were none.
- **screenshot paths** - the reference screenshots that were downloaded and read; `none` when there were none.
- **gates failed at review (numbers)** - the gate numbers as they were numbered in the blueprint block; `none` when the build passed first time.
- **rework rounds** - how many times the builder was sent back.
- **design-pass version** - the `version` in this skill's frontmatter.
- **hallmark commit** - the commit in `{{SKILLS_DIR}}\hallmark\VENDORED.md`.
- **inspo-mcp version** - the server version the session reports; `n/a` when Inspo was not called.

Worked line:

```
2026-09-20 | dispatch-tool | SCREEN | OPEN | 0 / 0 KB | none | none | 12, 25 | 1 | 0.1.0 | 13ac0ec7e148 | n/a
```

The deferred three-arm comparison (design-pass versus the sources invoked directly versus no design pass) reads this file: it is the only durable record of what each pass cost and what the reviewer caught, so a skipped line is a lost data point.
