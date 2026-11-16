"""Acceptance checks for the fabstra / fable-mode merge (2026-09-24).

Runs the merge spec's acceptance list against the plugin tree and prints one
line per check, then `RESULT: PASS` (exit 0) or `RESULT: FAIL` (exit 1).
Standard library only.
2026-11-10 (FabStra 1.11.0): seat pins, Fable 5.2 session switch row, retired wording,
short reference names, and all four builder agents.
2026-11-12 (1.12.0): the advisor - advisor.md, its builder paragraph, and its state-check names.
2026-11-12 (1.13.0): the automatic advisor - advisor.md names its switch script, and the
superseded 'never write advisorModel' rule stays out.
2026-11-12 (1.13.0 fix round 1): advisor.md pins `advisor-wrote=` (only a run that wrote the
setting switches it off) and `advisor-phase=post-build` (no re-enable after the last builder).
2026-11-12 (1.13.0 fix round 2): advisor.md pins `equals the run's model` (ownership re-checked
before every off) and `fable_ok=yes` (the Fable CLI check on every confirm path).

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
TRIAL_POINTER = 'Hard-tier builder: `model-router:builder` at `effort: "high"`'  # phases.md names the hard-tier seat (2026-11-16)
NOTHING_WRONG = "Finding nothing wrong is a legitimate result"
SEPARATE = "Separate verified from assumed"
ARCHIVE = "RUN-<YYYY-MM-DD-HHMMSS>"
# the builder spec's advisor paragraph, verbatim in specs.md and advisor.md (2026-11-12)
ADVISOR_PARA = ("An advisor model is attached to this session. Consult it before you settle how to build the "
                "feature, and again before you report DONE; it reads your whole transcript, so ask in one line. "
                "Its reply is advice: check it against this spec and the code before you act on it. In your "
                "report, list each consult and what you did with its advice.")
# names the advisor state check cannot drop silently (design gate P1, 2026-11-12;
# the per-seat re-read, review F1, 2026-11-12)
ADVISOR_STATE = ("CLAUDE_CODE_DISABLE_ADVISOR_TOOL=1", "advisorModel", "before each Claude seat",
                 "advisor-state.py", "advisor-wrote=", "advisor-phase=post-build",
                 "equals the run's model", "fable_ok=yes")
# the 1.12.0 rule the automatic advisor (1.13.0, 2026-11-12) superseded: the lead now switches it
ADVISOR_SUPERSEDED = ("Never write `advisorModel`",)
FABLE_MODE_ALLOWED = ("retired", "alias", "lead-mode.md")
REF_RE = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/skills/fabstra/references/([A-Za-z0-9_.-]+\.md)")
# a backticked reference name in the SKILL.md References section, with or without the path prefix
REF_SHORT_RE = re.compile(r"`(?:\$\{CLAUDE_PLUGIN_ROOT\}/skills/fabstra/references/)?([A-Za-z0-9_.-]+\.md)`")
# each Claude seat file and the frontmatter lines it must hold (contract D2, 2026-11-10;
# merged roster 2026-11-16: one builder and one reviewer, effort passed per call, fallback high)
SEAT_PINS = {
    "builder.md": {"model": "claude-opus-5-5", "effort": "high"},
    "reviewer.md": {"model": "claude-fable-5-2", "effort": "high"},
}
# retired by the 2026-11-16 roster merge (effort now passed per call to builder.md / reviewer.md)
RETIRED_AGENTS = ("builder-low.md", "builder-medium.md", "builder-high.md", "reviewer-xhigh.md")
SONNET_MAX_PINS = {"model": "claude-sonnet-5-5", "effort": "max"}
TOP_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(.*)$")  # a frontmatter key at column 0
# wording retired by 1.11.0; allowed only inside an "## Old patterns" section
RETIRED = [re.compile(re.escape("Fable 5.1")), re.compile(re.escape("fable-5-1")),
           re.compile(r"(?i)(opus|sonnet|haiku)[- ]tier"), re.compile(re.escape("arm=")),
           re.compile(re.escape("eligible="))]


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
    """The UTF-8 text of `p`, or None when it is missing, unreadable, or not valid UTF-8."""
    try:
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def size(p: Path) -> int | None:
    """The byte size of `p`, or None when it is missing or cannot be stat-ed."""
    try:
        return p.stat().st_size if p.is_file() else None
    except OSError:
        return None


def md_files(d: Path) -> list[Path]:
    return sorted(p for p in d.rglob("*.md") if p.is_file())


def frontmatter_keys(text: str | None) -> dict[str, list[str]]:
    """Top-level (column-0) keys of the block between the first two '---' lines, each with every value seen."""
    lines = (text or "").splitlines()
    if not lines or lines[0].rstrip() != "---":
        return {}
    keys: dict[str, list[str]] = {}
    for ln in lines[1:]:
        if ln.rstrip() == "---":
            return keys
        m = TOP_KEY_RE.match(ln)
        if m:
            keys.setdefault(m.group(1), []).append(m.group(2).strip())
    return {}  # no closing '---': no frontmatter


def pin_problems(name: str, text: str | None, want: dict[str, str]) -> list[str]:
    """What is wrong with `name`'s top-level pins: missing file, missing key, duplicated key, or wrong value."""
    if text is None:
        return [f"{name} missing or unreadable"]
    keys = frontmatter_keys(text)
    out = []
    for key, value in want.items():
        found = keys.get(key, [])
        if not found:
            out.append(f"{name} lacks top-level '{key}: {value}'")
        elif len(found) > 1:
            out.append(f"{name} has {len(found)} top-level '{key}:' lines {found}")
        elif found[0] != value:
            out.append(f"{name} {key} is '{found[0]}', want '{value}'")
    return out


def first_cell_parts(row: str) -> list[str]:
    """The first cell of a markdown table row, split on '/' and stripped."""
    cells = row.strip().strip("|").split("|")
    return [part.strip() for part in cells[0].split("/")] if cells else []


def file_lines(p: Path, problems: list[str], label: str) -> list[str]:
    """The lines of `p`; a missing or unreadable file is recorded in `problems` and yields no lines."""
    text = read(p)
    if text is None:
        problems.append(f"{label} missing or unreadable")
        return []
    return text.splitlines()


def h2_section(text: str, heading: str) -> str | None:
    """The body of the H2 `heading` up to the next H2 or the end of the file."""
    m = re.search(rf"^## {re.escape(heading)}[ \t]*\n(.*?)(?=^## |\Z)", text.replace("\r\n", "\n"), re.S | re.M)
    return m.group(1) if m else None


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
    advisor = refs / "advisor.md"
    fable_dir = args.home / ".claude" / "skills" / "fable-mode"
    fable_alias = fable_dir / "SKILL.md"
    fabsol_alias = root / "skills" / "fabsol" / "SKILL.md"
    cmd_fabstra = root / "commands" / "fabstra.md"
    cmd_fabsol = root / "commands" / "fabsol.md"
    r = Report()

    # 1. size caps
    for path, cap in [(skill, 6800), (lead, 20480), (fable_alias, 600), (fabsol_alias, 600), (cmd_fabsol, 500)]:
        n = size(path)
        if n is None:
            r.fail(f"size {path.parent.name}/{path.name}", f"missing or unreadable: {path}")
            continue
        try:
            path.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            r.fail(f"size {path.parent.name}/{path.name}", f"not valid UTF-8: {path}")
            continue
        except OSError:
            r.fail(f"size {path.parent.name}/{path.name}", f"missing or unreadable: {path}")
            continue
        r.check(n <= cap, f"size {path.parent.name}/{path.name}", f"{n} bytes, cap {cap}")

    # 2. forbidden strings under skills/fabstra/ and in the two aliases
    scan = md_files(fabstra) + [p for p in (fable_alias, fabsol_alias) if p.is_file()]
    hits: list[str] = []
    for p in scan:
        for i, line in enumerate(file_lines(p, hits, p.relative_to(p.anchor).as_posix()), 1):
            for s in FORBIDDEN:
                if s in line:
                    hits.append(f"{p.relative_to(p.anchor)}:{i} '{s}'")
    r.check(not hits, "forbidden strings", "; ".join(hits) if hits else f"0 hits in {len(scan)} files")

    # 3. `fable-mode` only on retired / alias / lead-mode.md lines
    bad: list[str] = []
    for p in md_files(fabstra) + [cmd_fabstra]:
        for i, line in enumerate(file_lines(p, bad, p.relative_to(root).as_posix()), 1):
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
        (specs, "advisor paragraph", ADVISOR_PARA),
        (advisor, "advisor paragraph", ADVISOR_PARA),
    ]
    for path, name, needle in required:
        text = read(path)
        if text is None:
            r.fail(f"verbatim {name} in {path.name}", f"{path.name} missing or unreadable")
            continue
        r.check(needle in text, f"verbatim {name} in {path.name}", "present" if needle in text else "missing")

    # 5. every reference cited in SKILL.md exists
    skill_read = read(skill)
    skill_text = skill_read or ""
    ref_section = h2_section(skill_text, "References") or ""
    cited = sorted(set(REF_RE.findall(skill_text)) | set(REF_SHORT_RE.findall(ref_section)))
    missing = [c for c in cited if not (refs / c).is_file()]
    if skill_read is None:
        r.fail("SKILL.md references exist", "SKILL.md missing or unreadable")
    else:
        r.check(bool(cited) and not missing, "SKILL.md references exist",
                f"missing {missing}" if missing else f"{len(cited)} cited, all present")

    # 6. no duplicate H2 inside any file under skills/fabstra/
    dups: list[str] = []
    for p in md_files(fabstra):
        seen: dict[str, int] = {}
        for line in file_lines(p, dups, p.name):
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

    # 8. the builder agent carries the time-matters line
    for name in ("builder.md",):
        p = root / "agents" / name
        text = read(p)
        if text is None:
            r.fail(f"agents/{name}", "missing or unreadable")
        else:
            r.check("Time matters here" in text, f"agents/{name}", "has 'Time matters here'"
                    if "Time matters here" in text else "lacks 'Time matters here'")

    # 9. sonnet-max seat pins Claude Sonnet 5.5 at max (2026-10-01)
    sm_bad = pin_problems("sonnet-max.md", read(root / "agents" / "sonnet-max.md"), SONNET_MAX_PINS)
    r.check(not sm_bad, "agents/sonnet-max.md", "; ".join(sm_bad) if sm_bad
            else "model claude-sonnet-5-5, effort max")

    # 10. the SKILL.md session switch table names Sonnet 5.5
    m = re.search(r"^## Session switch\n(.*?)(?=^## )", skill_text.replace("\r\n", "\n"), re.S | re.M)
    rows = [ln for ln in (m.group(1) if m else "").splitlines() if ln.startswith("|")]
    no_section = "SKILL.md missing or unreadable" if skill_read is None else "no '## Session switch' section"
    has_row = any("Sonnet 5.5" in first_cell_parts(ln) for ln in rows)
    r.check(has_row, "session switch Sonnet 5.5",
            "row present" if has_row else ("no Sonnet 5.5 row" if m else no_section))

    # 11. the contained-change build class is stated in both modes (2026-10-02)
    for path in (phases, lead):
        text = read(path)
        if text is None:
            r.fail(f"contained change in {path.name}", f"{path.name} missing or unreadable")
            continue
        gaps = [s for s in ("contained change", "at most 3 files") if s not in text.lower()]
        r.check(not gaps, f"contained change in {path.name}",
                "class and 3-file criterion present" if not gaps else f"missing {gaps}")
    ttext = read(refs / "transport.md")
    if ttext is None:
        r.fail("contained change in transport.md", "transport.md missing or unreadable")
    else:
        tlow = ttext.lower()
        r.check("contained change" in tlow, "contained change in transport.md",
                "review seat clause present" if "contained change" in tlow else "missing ['contained change']")

    # 12. each Claude seat pins its model and effort (2026-11-10)
    bad_pins: list[str] = []
    for name, want in SEAT_PINS.items():
        bad_pins += pin_problems(name, read(root / "agents" / name), want)
    r.check(not bad_pins, "seat pins", "; ".join(bad_pins) if bad_pins
            else f"{len(SEAT_PINS)} seat files pin model and effort")

    # 12b. the four agent files the 2026-11-16 roster merge retired stay out of agents/
    retired_present = [f"agents/{n} present" for n in RETIRED_AGENTS if (root / "agents" / n).exists()]
    r.check(not retired_present, "retired agents", ", ".join(retired_present) if retired_present
            else f"none of {len(RETIRED_AGENTS)} retired agent files present")

    # 13. the SKILL.md session switch table names Fable 5.2 (2026-11-10)
    has_fable = any("Fable 5.2" in first_cell_parts(ln) for ln in rows)
    r.check(has_fable, "session switch Fable 5.2",
            "row present" if has_fable else ("no Fable 5.2 row" if m else no_section))

    # 14. no retired wording outside an "## Old patterns" section (2026-11-10)
    retired_scan = [skill] + [p for p in md_files(refs) if p.name != "effort-trial.md"] + [cmd_fabstra]
    retired_hits: list[str] = []
    for p in retired_scan:
        in_old = False
        for i, line in enumerate(file_lines(p, retired_hits, p.relative_to(root).as_posix()), 1):
            if line.startswith("## "):
                in_old = line.rstrip() == "## Old patterns"  # history runs from this exact H2 to the next H2
            if not in_old and any(rx.search(line) for rx in RETIRED):
                retired_hits.append(f"{p.relative_to(root).as_posix()}:{i}")
    r.check(not retired_hits, "retired wording", ", ".join(retired_hits) if retired_hits
            else f"0 hits in {len(retired_scan)} files")

    # 15. the advisor reference exists and keeps its state-check names (2026-11-12)
    adv_text = read(advisor)
    r.check(adv_text is not None, "advisor.md exists", "present" if adv_text is not None
            else f"missing or unreadable: {advisor}")
    adv_gaps = [s for s in ADVISOR_STATE if s not in (adv_text or "")]
    r.check(not adv_gaps, "advisor state check", f"advisor.md lacks {adv_gaps}" if adv_gaps
            else "advisor.md names " + " and ".join(ADVISOR_STATE))
    adv_old = [s for s in ADVISOR_SUPERSEDED if s in (adv_text or "")]
    r.check(not adv_old, "advisor superseded rule", f"advisor.md still says {adv_old}" if adv_old
            else "advisor.md drops " + " and ".join(ADVISOR_SUPERSEDED))

    print("RESULT: FAIL" if r.failed else "RESULT: PASS")
    return 1 if r.failed else 0


if __name__ == "__main__":
    sys.exit(main())
