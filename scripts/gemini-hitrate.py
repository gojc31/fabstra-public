"""Total the Gemini / Hydrogen hit-rate counts logged in FabStra RUN.md files.

One record per line (pro-consult.md, "Handling the answer"): a line whose first
token, after optional indentation and an optional `- ` or `* ` list marker, is
`seat=gemini` or `seat=hydrogen`, and which ends with `leads=<n> real=<m>`: n
items raised, m items the lead verified and used. Lines that mention seat=
anywhere else are not records; counts on a following line are not joined.
This script reads logbooks and writes nothing.

An API-backup launch (the brief went to the Gemini API because the app path
could not run) carries the whitespace-delimited token `via=api` anywhere after
the seat token: `seat=hydrogen mode=<m> via=api <free text> leads=<n> real=<m>`.
A record with no `via=` token, or with any other `via=<x>` token, is an app
launch. The seat names the model that answered, so an API-backup record is
`seat=hydrogen` even when Carbon was asked for. App and API launches are
separate rows (`via` = app | api); the totals cover every row.

    python scripts/gemini-hitrate.py [PATH ...] [--json]

PATH is a folder (scans its .fabstra/RUN*.md) or a file. With no PATH it scans
<home>/.fabstra/RUN*.md, <home>/*/.fabstra/RUN*.md and D:/*/.fabstra/RUN*.md
(one-level globs, never recursive; an absent D:/ is skipped). The env var
GEMINI_HITRATE_ROOTS (os.pathsep-separated folders) replaces those defaults;
each root is scanned as <root>/.fabstra/RUN*.md and <root>/*/.fabstra/RUN*.md.

Per seat+mode+via: launches = scored + unscored + invalid + skipped.
  skipped  - `skipped:` directly after the mode=<m> token (a launch, never summed)
  scored   - terminal counts present and real <= leads (summed)
  invalid  - terminal counts present and real > leads (counted, not summed)
  unscored - no `leads=<n> real=<m>` pair at the end of the line
A file that cannot be read is skipped and counted as unreadable.
Exit 0 normally; exit 2 when a PATH given on the command line does not exist;
exit 64 on a usage error (unknown option).
Standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

# A record starts with seat=<gemini|hydrogen> as its first token, after optional
# indentation and an optional "- " / "* " list marker; any other line is not a record.
RECORD_RE = re.compile(r"^\s*(?:[-*]\s+)?seat=(gemini|hydrogen)(?=\s|$)(.*)$")
# the record's first mode= token; `skipped:` counts only as the very next token
MODE_RE = re.compile(r"(?:^|\s)mode=([A-Za-z0-9_-]+)(\s+skipped:)?")
# the terminal count pair: the last thing on the line (trailing whitespace allowed)
COUNTS_RE = re.compile(r"(?:^|\s)leads=(\d+)\s+real=(\d+)\s*$")
# an API-backup launch: the exact token via=api anywhere after the seat token
VIA_RE = re.compile(r"(?:^|\s)via=api(?=\s|$)")
COUNT_KEYS = ("launches", "scored", "unscored", "invalid", "skipped", "leads", "real")


def d_root() -> Path:
    # Overridable for tests; the default is the D: drive.
    return Path(os.environ.get("GEMINI_HITRATE_D_ROOT", "D:/"))


def run_files_in(folder: Path) -> list[Path]:
    return sorted(p for p in (folder / ".fabstra").glob("RUN*.md") if p.is_file())


def default_files() -> list[Path]:
    env = os.environ.get("GEMINI_HITRATE_ROOTS")
    files: list[Path] = []
    if env:
        for root in filter(None, env.split(os.pathsep)):
            r = Path(root)
            if r.is_dir():  # same one-level shape as the home default
                files += run_files_in(r)
                files += sorted(p for p in r.glob("*/.fabstra/RUN*.md") if p.is_file())
        return files
    home = Path.home()
    files += run_files_in(home)
    files += sorted(p for p in home.glob("*/.fabstra/RUN*.md") if p.is_file())
    d = d_root()
    try:
        if d.is_dir():
            files += sorted(p for p in d.glob("*/.fabstra/RUN*.md") if p.is_file())
    except OSError:
        pass
    return files


def dedupe(files: list[Path]) -> list[Path]:
    seen: dict[str, Path] = {}
    for f in files:
        key = os.path.normcase(str(f.resolve()))
        seen.setdefault(key, f)
    return [seen[k] for k in sorted(seen)]


def empty_counts() -> dict:
    return {k: 0 for k in COUNT_KEYS}


def hit_rate(c: dict):
    return round(100.0 * c["real"] / c["leads"], 1) if c["leads"] else None


def tally(files: list[Path]) -> dict:
    rows: dict[tuple[str, str, str], dict] = {}
    read = unreadable = 0
    for f in files:
        try:
            text = f.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:  # PermissionError, a vanished file, a locked share
            unreadable += 1
            continue
        read += 1
        for line in text.splitlines():
            rec = RECORD_RE.match(line)
            if not rec:
                continue
            rest = rec.group(2)
            mode = MODE_RE.search(rest)
            via = "api" if VIA_RE.search(rest) else "app"
            key = (rec.group(1), mode.group(1) if mode else "unknown", via)
            c = rows.setdefault(key, empty_counts())
            c["launches"] += 1
            if mode and mode.group(2):
                c["skipped"] += 1
                continue
            counts = COUNTS_RE.search(rest)
            if not counts:
                c["unscored"] += 1
                continue
            n, m = int(counts.group(1)), int(counts.group(2))
            if m > n:
                c["invalid"] += 1
                continue
            c["scored"] += 1
            c["leads"] += n
            c["real"] += m
    out_rows = []
    totals = empty_counts()
    for (seat, mode, via), c in sorted(rows.items()):
        out_rows.append({"seat": seat, "mode": mode, "via": via, **c, "hit_rate": hit_rate(c)})
        for k in COUNT_KEYS:
            totals[k] += c[k]
    totals["hit_rate"] = hit_rate(totals)
    return {"rows": out_rows, "totals": totals, "files_read": read, "unreadable": unreadable}


def fmt_rate(v) -> str:
    return "-" if v is None else f"{v:.1f}%"


def print_table(data: dict) -> None:
    head = ["seat", "mode", "via", "launches", "scored", "skipped", "leads", "real", "hit"]
    body = [[r["seat"], r["mode"], r["via"], *(str(r[k]) for k in ("launches", "scored", "skipped", "leads", "real")),
             fmt_rate(r["hit_rate"])] for r in data["rows"]]
    t = data["totals"]
    body.append(["TOTAL", "", "", *(str(t[k]) for k in ("launches", "scored", "skipped", "leads", "real")),
                 fmt_rate(t["hit_rate"])])
    widths = [max(len(row[i]) for row in [head, *body]) for i in range(len(head))]
    for row in [head, *body]:
        print("  ".join(cell.ljust(w) if i < 3 else cell.rjust(w)
                        for i, (cell, w) in enumerate(zip(row, widths))).rstrip())
    print(f"unscored lines: {t['unscored']}")
    print(f"invalid lines (real > leads): {t['invalid']}")
    print(f"files read: {data['files_read']}")
    print(f"unreadable files: {data['unreadable']}")


class _Parser(argparse.ArgumentParser):
    def error(self, message):  # usage errors exit 64 (EX_USAGE); exit 2 stays "path missing"
        self.print_usage(sys.stderr)
        self.exit(64, f"{self.prog}: error: {message}\n")


def main(argv=None) -> int:
    ap = _Parser(description="Total Gemini/Hydrogen leads and real counts from FabStra RUN.md files.")
    ap.add_argument("paths", nargs="*", help="folder (scans .fabstra/RUN*.md) or file")
    ap.add_argument("--json", action="store_true", help="print one JSON object")
    args = ap.parse_intermixed_args(argv)
    if args.paths:
        files: list[Path] = []
        for raw in args.paths:
            p = Path(raw)
            if not p.exists():
                print(f"gemini-hitrate: path does not exist: {raw}", file=sys.stderr)
                return 2
            files += run_files_in(p) if p.is_dir() else [p]
    else:
        files = default_files()
    data = tally(dedupe(files))
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print_table(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
