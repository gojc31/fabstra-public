"""Acceptance checks for the fabstra / fable-mode merge (2026-09-24).

Runs the merge spec's acceptance list against the plugin tree and prints one
line per check, then `RESULT: PASS` (exit 0) or `RESULT: FAIL` (exit 1).
Standard library only.

    python scripts/check-fabstra.py [--root <model-router dir>] [--home <user home>]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FORBIDDEN = [
    "Two batched reads",
    "Never read a whole built file",
    "do not lower it",
    "builder is the hands",
    "loosening the process",
    "fabstra5",
    "fable5-mode",
    "reviewer5",
]

RULES = [
    "1. Orchestrate mode: you never write code; builders build, reviewers review, you write specs, verdicts, and the report. Lead mode: you build what the authoritative plan says, delegating sizeable independent tracks by tier.",
    "2. Specs carry the decisions that must not drift: outcome, invariants, scope and non-goals, shared interfaces and file ownership, grounded pointers, acceptance, verification. Builders own everything inside those lines and report each decision.",
    "3. Context budget, not read caps: read what a decision depends on, whole files included; verify landed work with targeted slices; batch searches into one call; nothing rides in context that a later turn will not use.",
    "4. Independent tasks launch in parallel and builders run in the background; every delegation finishes before the session ends.",
    "5. The logbook `.fabstra/RUN.md` is the source of truth; resume from it, never re-plan from memory.",
    "6. One accountable lead. Astra and every reviewer advise. A finding is accepted by revising the plan or code, or rejected with one logged line; never silently dropped, never applied unread. Only the user overrules the lead.",
    "7. Finding nothing wrong is a legitimate result. Never manufacture findings.",
]
CONTEXT_RULE = ("Context budget, not read caps: read what a decision depends on, whole files included; "
                "verify landed work with targeted slices; batch searches into one call; nothing rides in "
                "context that a later turn will not use.")
TIME_LINE = ("Time matters here: do not spend time that can be avoided, and the earlier a correct result "
             "is obtained, the better.")
EXPLORE_LINE = ("Before taking any action, explore broadly with tool calls: list and open the emails, "
                "documents, spreadsheet tabs and records across the available apps that could be relevant "
                "to this task, including ones the task does not explicitly mention, and use what you find.")
TRIAL_FIRST = "Opus 5.5 builder effort trial, 2026-09-24 to 2026-10-08."
TRIAL_POINTER = "Opus-tier builder arm: effort-trial.md"  # phases.md points at the trial rule (2026-10-03)
NOTHING_WRONG = "Finding nothing wrong is a legitimate result"
SEPARATE = "Separate verified from assumed"
ARCHIVE = "RUN-<YYYY-MM-DD-HHMMSS>"
FABLE_MODE_ALLOWED = ("retired", "alias", "lead-mode.md")
REF_RE = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/skills/fabstra/references/([A-Za-z0-9_.-]+\.md)")


class Report:
    def __init__(self) -> None:
        self.failed = False

    def ok(self, name: str, detail: str = "") -> None:
        print(f"PASS {name}" + (f" - {detail}" if detail else ""))

    def fail(self, name: str, detail: str) -> None:
        self.failed = True
        print(f"FAIL {name} - {detail}")

    def warn(self, name: str, detail: str) -> None:
        print(f"WARN {name} - {detail}")

    def check(self, cond: bool, name: str, detail: str) -> None:
        (self.ok if cond else self.fail)(name, detail)


def read(p: Path) -> str | None:
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return None


def md_files(d: Path) -> list[Path]:
    return sorted(p for p in d.rglob("*.md") if p.is_file())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--home", type=Path, default=Path.home())
    args = ap.parse_args()
    root: Path = args.root
    fabstra = root / "skills" / "fabstra"
    refs = fabstra / "references"
    skill = fabstra / "SKILL.md"
    lead = refs / "lead-mode.md"
    phases = refs / "phases.md"
    trial = refs / "effort-trial.md"
    specs = refs / "specs.md"
    fable_dir = args.home / ".claude" / "skills" / "fable-mode"
    fable_alias = fable_dir / "SKILL.md"
    fabsol_alias = root / "skills" / "fabsol" / "SKILL.md"
    cmd_fabstra = root / "commands" / "fabstra.md"
    cmd_fabsol = root / "commands" / "fabsol.md"
    r = Report()

    # 1. size caps
    for path, cap in [(skill, 6800), (lead, 20480), (fable_alias, 600), (fabsol_alias, 600), (cmd_fabsol, 500)]:
        if not path.is_file():
            r.fail(f"size {path.name}", f"missing: {path}")
            continue
        n = path.stat().st_size
        r.check(n <= cap, f"size {path.parent.name}/{path.name}", f"{n} bytes, cap {cap}")

    # 2. forbidden strings under skills/fabstra/ and in the two aliases
    scan = md_files(fabstra) + [p for p in (fable_alias, fabsol_alias) if p.is_file()]
    hits = []
    for p in scan:
        for i, line in enumerate((read(p) or "").splitlines(), 1):
            for s in FORBIDDEN:
                if s in line:
                    hits.append(f"{p.relative_to(p.anchor)}:{i} '{s}'")
    r.check(not hits, "forbidden strings", "; ".join(hits) if hits else f"0 hits in {len(scan)} files")

    # 3. `fable-mode` only on retired / alias / lead-mode.md lines
    bad = []
    for p in md_files(fabstra) + [cmd_fabstra]:
        for i, line in enumerate((read(p) or "").splitlines(), 1):
            if "fable-mode" in line and not any(w in line.lower() for w in FABLE_MODE_ALLOWED):
                bad.append(f"{p.name}:{i}")
    r.check(not bad, "fable-mode mentions", ", ".join(bad) if bad else "only retired/alias/lead-mode.md lines")

    # 4. required verbatim strings (each must sit on one line, as grep sees it)
    required = [(skill, f"rule {n}", s) for n, s in enumerate(RULES, 1)]
    required += [
        (skill, "context-budget rule", CONTEXT_RULE),
        (phases, "context-budget rule", CONTEXT_RULE),
        (specs, "time-matters line", TIME_LINE),
        (specs, "explore-broadly line", EXPLORE_LINE),
        (trial, "effort trial", TRIAL_FIRST),
        (phases, "effort-trial pointer", TRIAL_POINTER),
        (skill, "nothing-wrong line", NOTHING_WRONG),
        (skill, "separate-verified line", SEPARATE),
        (lead, "separate-verified line", SEPARATE),
        (phases, "archive name", ARCHIVE),
    ]
    for path, name, needle in required:
        text = read(path)
        r.check(text is not None and needle in text, f"verbatim {name} in {path.name}",
                "present" if text is not None and needle in text else "missing")

    # 5. every reference cited in SKILL.md exists
    cited = sorted(set(REF_RE.findall(read(skill) or "")))
    missing = [c for c in cited if not (refs / c).is_file()]
    r.check(bool(cited) and not missing, "SKILL.md references exist",
            f"missing {missing}" if missing else f"{len(cited)} cited, all present")

    # 6. no duplicate H2 inside any file under skills/fabstra/
    dups = []
    for p in md_files(fabstra):
        seen: dict[str, int] = {}
        for line in (read(p) or "").splitlines():
            if line.startswith("## "):
                seen[line] = seen.get(line, 0) + 1
        dups += [f"{p.name}: {h}" for h, c in seen.items() if c > 1]
    r.check(not dups, "duplicate H2", "; ".join(dups) if dups else "none")

    # 7. fable-mode folder holds SKILL.md only
    if fable_dir.is_dir():
        entries = sorted(e.name for e in fable_dir.iterdir())
        r.check(entries == ["SKILL.md"], "fable-mode folder", f"contents {entries}")
    else:
        r.fail("fable-mode folder", f"missing: {fable_dir}")

    # 8. builder agents carry the time-matters line
    for name, soft in [("builder.md", False), ("builder-medium.md", True)]:
        p = root / "agents" / name
        text = read(p)
        if text is None:
            (r.warn if soft else r.fail)(f"agents/{name}", "not there yet" if soft else "missing")
        else:
            r.check("Time matters here" in text, f"agents/{name}", "has 'Time matters here'"
                    if "Time matters here" in text else "lacks 'Time matters here'")

    # 9. sonnet-max seat pins Claude Sonnet 5.5 at max (2026-10-01)
    sm = read(root / "agents" / "sonnet-max.md")
    fm = sm.split("---", 2)[1] if sm and sm.startswith("---") and sm.count("---") >= 2 else ""
    fm_lines = {ln.strip() for ln in fm.splitlines()}
    sm_ok = "model: claude-sonnet-5-5" in fm_lines and "effort: max" in fm_lines
    r.check(sm_ok, "agents/sonnet-max.md", "model claude-sonnet-5-5, effort max" if sm_ok
            else ("frontmatter lacks model: claude-sonnet-5-5 / effort: max" if sm else "missing"))

    # 10. the SKILL.md session switch table names Sonnet 5.5
    m = re.search(r"^## Session switch\n(.*?)(?=^## )", (read(skill) or "").replace("\r\n", "\n"), re.S | re.M)
    rows = [ln for ln in (m.group(1) if m else "").splitlines() if ln.startswith("|")]
    has_row = any("Sonnet 5.5" in ln for ln in rows)
    r.check(has_row, "session switch Sonnet 5.5",
            "row present" if has_row else ("no Sonnet 5.5 row" if m else "no '## Session switch' section"))

    # 11. the contained-change build class is stated in both modes (2026-10-02)
    for path in (phases, lead):
        low = (read(path) or "").lower()
        gaps = [s for s in ("contained change", "at most 3 files") if s not in low]
        r.check(not gaps, f"contained change in {path.name}",
                "class and 3-file criterion present" if not gaps else f"missing {gaps}")
    tlow = (read(refs / "transport.md") or "").lower()
    r.check("contained change" in tlow, "contained change in transport.md",
            "review seat clause present" if "contained change" in tlow else "missing ['contained change']")

    print("RESULT: FAIL" if r.failed else "RESULT: PASS")
    return 1 if r.failed else 0


if __name__ == "__main__":
    sys.exit(main())
