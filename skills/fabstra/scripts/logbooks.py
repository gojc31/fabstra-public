#!/usr/bin/env python3
"""Which fabstra logbooks in a folder are held by another open Claude Code session.

Usage: python logbooks.py [folder]      (default: the current directory)

Prints one line per logbook (.fabstra/RUN.md and .fabstra/RUN-<slug>.md; timestamp-named
archives are skipped), tab-separated: state, file, title, detail. Last line:
`this-session: <id> pid=<pid>` - this run copies it onto its `owner:` line verbatim.

States (phases.md, "The run logbook"):
  live        owner process (pid=, else session id) is open -> leave it alone
  maybe-live  no owner line; a session open in this folder was already open when the
              logbook was last written                -> leave it alone
  mine        owner is this session                    -> carry on
  unfinished  owner gone, or nobody else open here     -> mention; ask only if the brief is about it
  parked      status: parked (or legacy Handoff)       -> mention; ask only if the brief is about it
  done        finished                                 -> nothing to ask
  old         unfinished but untouched 21+ days        -> ignore unless the user names it

Open sessions come from ~/.claude/sessions/<pid>.json (the registry Claude Code keeps for
open sessions); an entry whose process has exited, or untouched for 7 days, is ignored.
The owner is matched by pid first: /clear gives a process a new session id but its registry
entry keeps the old one. An owner not found falls through to the folder rule.
Parsing mirrors the jc-mods run-handoff hook (hooks/runlog.ts) line for line; keep them in step.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

STATUS = re.compile(r"^\s*(?:[-*]\s*)?(?:\*\*)?status:(?:\*\*)?\s*(running|parked|done)\b", re.I)
OWNER = re.compile(r"^\s*(?:[-*]\s*)?(?:\*\*)?owner:(?:\*\*)?\s*([0-9a-f]{8}-[0-9a-f-]{27})(?:\s+pid=(\d+))?", re.I)
FINISHED_LINE = re.compile(r"^\s*(?:-\s*)?(?:DONE|SHIPPED|FINISHED|CLOSED)\b")
STRICT_FINISHED_LINE = re.compile(r"^(?:DONE|SHIPPED|FINISHED|CLOSED)\b")  # inside a Handoff section
SECTION_END = re.compile(r"^#{1,2}\s")
REPORT_HEADING = re.compile(r"^#{1,3}\s*(?:report|done)\b", re.I)
HANDOFF = re.compile(r"^##\s+Handoff\b", re.I)
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
SLUG_LOG = re.compile(r"^RUN-[A-Za-z][\w.-]*\.md$")
FALLBACK_LIVE_SECONDS = 3600  # only when the session registry cannot be read
REGISTRY_MAX_AGE_MS = 7 * 86400 * 1000
CONFIG = Path.home() / ".claude" / "mod-data" / "jc-mods" / "config.json"


def stale_seconds() -> float:
    """The run-handoff hook's staleDays (default 21), so both agree on what is too old to ask about."""
    try:
        v = json.loads(CONFIG.read_text(encoding="utf-8"))["run-handoff"]["staleDays"]
        if isinstance(v, (int, float)) and v > 0:
            return v * 86400
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return 21 * 86400


def norm(path: str) -> str:
    return str(path).replace("\\", "/").rstrip("/").lower()


def pid_alive(pid: int) -> bool:
    if os.name == "nt":
        import ctypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        code = ctypes.c_ulong()
        ok = k.GetExitCodeProcess(h, ctypes.byref(code))
        k.CloseHandle(h)
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def open_sessions() -> list[dict] | None:
    reg = Path.home() / ".claude" / "sessions"
    if not reg.is_dir():
        return None
    out = []
    for f in reg.glob("*.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8").strip("\x00 \r\n"))
        except (OSError, ValueError):
            continue  # half-written or zeroed entry
        if not (isinstance(d, dict) and d.get("sessionId") and isinstance(d.get("pid"), int)):
            continue
        touched = d.get("updatedAt") or d.get("startedAt") or 0
        if time.time() * 1000 - touched > REGISTRY_MAX_AGE_MS or not pid_alive(d["pid"]):
            continue
        out.append(d)
    return out


def classify(path: Path, folder: str, me: str, my_pid: int | None, sessions: list[dict] | None,
             old_seconds: float) -> tuple[str, str, str]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    status = owner = owner_pid = None
    title = ""
    finished_at = handoff_at = -1
    in_handoff = False
    for i, line in enumerate(lines):
        if HANDOFF.match(line):
            handoff_at, in_handoff = i, True
        elif in_handoff and SECTION_END.match(line):
            in_handoff = False
        if status is None and (m := STATUS.match(line)):
            status = m.group(1).lower()
        if owner is None and (m := OWNER.match(line)):
            owner, owner_pid = m.group(1).lower(), (int(m.group(2)) if m.group(2) else None)
        if not title and (m := HEADING.match(line.strip())):
            title = m.group(1)
        if HANDOFF.match(line):
            continue
        # Inside a handoff section only an unindented, non-bullet DONE line counts.
        finished = (STRICT_FINISHED_LINE if in_handoff else FINISHED_LINE).match(line)
        if finished or REPORT_HEADING.match(line):
            finished_at = i
    report = path.parent / path.name.replace("RUN", "REPORT", 1)  # RUN.md <-> REPORT.md, RUN-x.md <-> REPORT-x.md
    mtime = path.stat().st_mtime
    if time.time() - mtime > old_seconds:
        return "old", title, ""
    if status == "done":
        return "done", title, ""
    if status == "parked":
        return "parked", title, ""
    if report.exists() and report.stat().st_mtime >= mtime:
        return "done", title, f"{report.name} is newer"
    if finished_at >= 0 and not handoff_at > finished_at:
        return "done", title, "finished marker"
    if status is None and owner is None and handoff_at >= 0:
        return "parked", title, "legacy Handoff section"
    if owner is not None and (owner == me or (owner_pid is not None and owner_pid == my_pid)):
        return "mine", title, ""
    if sessions is None:
        age = time.time() - mtime
        if age < FALLBACK_LIVE_SECONDS:
            return "maybe-live", title, f"session registry unreadable; written {int(age // 60)} min ago"
        return "unfinished", title, "session registry unreadable"
    label = lambda s: f"{s.get('name', str(s['sessionId'])[:8])} ({s.get('status', '?')})"  # noqa: E731
    if owner is not None:
        holder = next((s for s in sessions if owner_pid is not None and s["pid"] == owner_pid), None) \
            or next((s for s in sessions if str(s["sessionId"]).lower() == owner), None)
        if holder:
            return "live", title, f"owner {label(holder)} is open"
        # Owner not found: fall through to the folder rule rather than declaring it abandoned.
    # A session can only be running it if it was open in this folder when the file was last written.
    here = [s for s in sessions if str(s["sessionId"]).lower() != me and s["pid"] != my_pid
            and norm(s.get("cwd", "")) == folder
            and isinstance(s.get("startedAt"), (int, float)) and s["startedAt"] / 1000 <= mtime]
    if here:
        why = "owner not open" if owner else "no owner line"
        return "maybe-live", title, f"{why}; open here since before its last write: {', '.join(map(label, here))}"
    return "unfinished", title, "no session that could be writing it is open"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # titles carry dashes and arrows; Windows consoles default to cp1252
    folder = Path(sys.argv[1] if len(sys.argv) > 1 else os.getcwd()).resolve()
    me = os.environ.get("CLAUDE_CODE_SESSION_ID", "").lower()
    pid_env = os.environ.get("CLAUDE_PID", "")
    my_pid = int(pid_env) if pid_env.isdigit() else None
    logdir = folder / ".fabstra"
    files = []
    if logdir.is_dir():
        files = [p for p in sorted(logdir.iterdir()) if p.is_file() and (p.name == "RUN.md" or SLUG_LOG.match(p.name))]
    sessions = open_sessions() if files else []
    for p in files:
        state, title, detail = classify(p, norm(str(folder)), me, my_pid, sessions, stale_seconds())
        print(f"{state}\t.fabstra/{p.name}\t{title}\t{detail}")
    if not files:
        print("none\t-\t-\tno logbook in this folder")
    print(f"this-session: {me or 'unknown'} pid={my_pid or 'unknown'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
