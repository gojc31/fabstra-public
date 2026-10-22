"""lanew_log - two-phase usage LOGGER for the Lane W wrapper (`bin/lanew`).

HONEST SCOPE, read before trusting this module for anything: this is a
DIAGNOSTIC LOGGER with a fail-closed admission check, NOT a hard usage
budget. Nothing observable on this machine measures ChatGPT chat-message
consumption - see skills/fabstra/references/lane-w.md, "What lanew
measures and what it cannot", for the full statement. Concretely:

  - `assistant_message_markers` counts transcript lines that are exactly
    `codex` (the Codex CLI's own turn marker in a captured .out file).
    It is a DIAGNOSTIC count only, never a verified count of model
    requests or turns: a prompt or a model's own answer can itself
    contain a standalone `codex` line (see the `echo-only` fixture in
    tests/test_lanew_log.py), and a real job can emit more than one exec
    attempt without a matching number of markers.
  - `tokens_used` is the Codex-side reported token count for that job,
    not the ChatGPT chat-message allowance the docs say this lane
    actually spends (2-6 chat messages per Codex turn, per lane-w.md).
  - `web_messages` is always null in every record: there is no supported
    way to read it from here.
  - The per-run job ceiling (`LANEW_RUN_JOB_CEILING`, default 8) counts
    JOBS, as a proxy, because turns themselves are not measurable from
    this machine. It is not a message-budget enforcement, and a job
    admitted under the ceiling can still push real chat-message usage
    past whatever chat allowance actually matters.
  - Even a fully "usage_complete" run's log tells you nothing about
    OTHER ChatGPT activity on the same account. Remaining allowance is
    always UNVERIFIED from this log alone.

Log format: JSON Lines at LANEW_LOG (env override) or
~/.cli-proxy-api/lanew-usage.jsonl, one record per job-state transition.
Two-phase per job: `record start` writes a `started` reservation line
BEFORE the job is launched; `record end` writes the terminal line for
the same job_id after the job finishes (or after a preflight failure,
via `record preflight-failed`, which writes both halves at once because
the job never launched). A `started` line with no terminal line means
usage for that job is UNKNOWN - `check` refuses further launches in the
run until that is reconciled by hand; it never assumes zero usage.

In-flight rule (added 2026-10-17 for bin/astrapro, which runs up to 3
jobs of one run in parallel): a `started` record may carry `owner_pid`,
the Windows pid of the wrapper process that owns the job (`record start
--pid` / `admit --pid`). A started-without-terminal job whose owner_pid
is present AND still alive is IN FLIGHT, not unknown: it counts toward
the run's job ceiling but does not refuse. A started-without-terminal
job with no owner_pid, or a dead one, stays "usage unknown -> refuse",
exactly as before. So does one whose ts_start is older than
IN_FLIGHT_MAX_AGE_S (2,700 s) or unreadable, even with a live
owner_pid: no astrapro job can outlive slot wait + state lock + launch +
its 1,500 s cap, so a live pid that old is a reused pid, not the owner.
A started record may also carry `owner_created` (`--pid-created`, added
2026-10-17 for astrapro T4): the owner process's creation time
(pid_created - Windows FILETIME ticks, POSIX /proc start ticks). When it
is recorded, the job is in flight only if the live owner_pid's creation
time EQUALS it; a mismatch is a reused pid -> usage unknown -> refuse.
Records without owner_pid (every bin/lanew record), and records without
owner_created, behave exactly as they always did. Latch and ceiling rules are
unchanged. `admit` closes the admission race between parallel wrappers:
it runs the `check` logic and appends the started record inside ONE
critical section under the log's lock file, so two callers at
ceiling-1 can never both be admitted.

Record fields: job_id (uuid4 hex, immutable per job), run, name, model,
owner_pid (int; started records only, and only when given), owner_created
(int; likewise), ts_start, ts_end, codex_exit (raw, nullable until terminal), duration_s,
assistant_message_markers, tokens_used (nullable int), web_messages
(always null), usage_complete (bool), status, out_path, report_path,
stop_latch (bool - true on any non-ok terminal status; a latched run
refuses every further `check` until reconciled by hand, honoring the
docs' no-retry-in-the-run rule).

CLI: `record start|end|preflight-failed` (`record start` takes optional
`--pid` and `--pid-created`), `check --run R`, `admit --run R ... [--pid P]
[--pid-created C]` (atomic check +
record start), `report [--days N] [--run R]`. See each function's docstring for the
Python API; the CLI is a thin wrapper over it for bin/lanew.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

try:  # Windows
    import msvcrt
except ImportError:  # pragma: no cover - POSIX
    msvcrt = None
try:  # POSIX
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None

DEFAULT_LOG = os.path.join(os.path.expanduser("~"), ".cli-proxy-api", "lanew-usage.jsonl")
LOG_PATH = os.environ.get("LANEW_LOG") or DEFAULT_LOG
RUN_JOB_CEILING = int(os.environ.get("LANEW_RUN_JOB_CEILING", "8"))

IN_FLIGHT_MAX_AGE_S = 2700  # longest possible astrapro job; see the in-flight rule

LOCK_TRIES = 500
LOCK_SLEEP = 0.02  # ~10 s worst case, generous for two local processes

_MARKER_RE = re.compile(r"(?m)^\s*codex\s*$", re.IGNORECASE)
_TOKENS_RE = re.compile(r"tokens used\s*\n\s*([0-9][0-9,]*)", re.IGNORECASE)
_BRIDGE_RE = re.compile(r"\b17841\b|\bbridge\b", re.IGNORECASE)
_SAFETY_RE = re.compile(r"blocked by openai's safety checks", re.IGNORECASE)
_TOOL_EXIT_RE = re.compile(r"-1073741502")
_EXEC_EVENT_RE = re.compile(r"(?m)^exec\b")


class LogCorrupt(Exception):
    """Raised by _read_log when a line in the log is not valid JSON."""


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _parse_iso(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _duration(ts_start, ts_end):
    a, b = _parse_iso(ts_start), _parse_iso(ts_end)
    if a is None or b is None:
        return None
    return round((b - a).total_seconds(), 3)


def pid_alive(pid) -> bool:
    """True when pid names a live process. Never raises.

    Windows: OpenProcess + GetExitCodeProcess == STILL_ACTIVE (259), the
    skills/fabstra/scripts/logbooks.py pattern - never os.kill(pid, 0)
    there, because signal 0 on Windows is CTRL_C_EVENT.
    """
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes
            k = ctypes.windll.kernel32
            h = k.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return False
            try:
                code = ctypes.c_ulong()
                ok = k.GetExitCodeProcess(h, ctypes.byref(code))
            finally:
                k.CloseHandle(h)
            return bool(ok) and code.value == 259  # STILL_ACTIVE
        except Exception:  # pragma: no cover - ctypes unavailable
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def pid_created(pid):
    """The creation time of live process pid as an int, or None. Never raises.

    Windows: OpenProcess + GetProcessTimes creation FILETIME (100 ns ticks
    since 1601). POSIX: /proc/<pid>/stat field 22 (start time in clock
    ticks since boot). Used with pid_alive so a reused pid never passes for
    the original process (module docstring, owner_created).
    """
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        return None
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes
            k = ctypes.WinDLL("kernel32", use_last_error=True)
            k.OpenProcess.restype = wintypes.HANDLE
            k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            k.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(ctypes.c_uint64)] * 4
            k.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            k.CloseHandle.argtypes = [wintypes.HANDLE]
            h = k.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return None
            try:
                times = [ctypes.c_uint64() for _ in range(4)]
                ok = k.GetProcessTimes(h, *[ctypes.byref(t) for t in times])
                code = wintypes.DWORD()
                k.GetExitCodeProcess(h, ctypes.byref(code))
            finally:
                k.CloseHandle(h)
            if not ok or code.value != 259 or not times[0].value:  # STILL_ACTIVE
                return None
            return int(times[0].value)
        except Exception:  # pragma: no cover - ctypes unavailable
            return None
    try:
        with open("/proc/%d/stat" % pid, "r", encoding="ascii", errors="replace") as f:
            stat = f.read()
        return int(stat.rsplit(")", 1)[1].split()[19])
    except (OSError, ValueError, IndexError):
        return None


def _read_text(path) -> str:
    if not path:
        return ""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _is_fresh(report_path, ts_start) -> bool:
    """True when report_path's mtime is at/after this job's own ts_start.

    A stale report left behind by a previous job that reused the same
    output path must never be mistaken for this job's result. A missing
    file or an unparsable ts_start is never treated as fresh.
    """
    start = _parse_iso(ts_start)
    if start is None or not report_path:
        return False
    try:
        mtime = os.path.getmtime(report_path)
    except OSError:
        return False
    mtime_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
    return mtime_dt >= start - timedelta(seconds=1)  # slack for FS clock granularity


# --------------------------------------------------------------------------
# locking / append (Windows msvcrt.locking / POSIX fcntl.flock, like jev_log)
# --------------------------------------------------------------------------

def _lock(fd) -> bool:
    for _ in range(LOCK_TRIES):
        try:
            if msvcrt is not None:
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            elif fcntl is not None:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError:
            time.sleep(LOCK_SLEEP)
    return False


def _unlock(fd) -> None:
    try:
        if msvcrt is not None:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        elif fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError:
        pass


def append_line_verified(path: str, line: str) -> bool:
    """Append one line to path under an OS lock; verify by re-reading it.

    A single os.write on an O_APPEND fd, under a lock file held for the
    duration (never the log file itself, so a concurrent reader is never
    blocked by the writer's own open). Returns True only when the write
    happened AND the file, re-read afterwards, ends with exactly the
    bytes just written. Never raises - a False return is the caller's
    signal to treat usage as unknown and fail closed.
    """
    locked, ok = _with_log_lock(path, lambda: _append_unlocked(path, line))
    return bool(locked and ok)


def _with_log_lock(path: str, fn):
    """Run fn() while holding path's lock file. Returns (locked, fn_result).

    The lock is `path + ".lock"`, never the log file itself, so a
    concurrent reader is never blocked by a writer's own open. locked is
    False (and fn never runs) when the lock file cannot be opened or the
    lock cannot be taken within LOCK_TRIES. fn must not take the lock
    again (msvcrt locks are per handle, so a nested take would time out).
    """
    parent = os.path.dirname(path)
    binary = getattr(os, "O_BINARY", 0)
    try:
        if parent:
            os.makedirs(parent, exist_ok=True)
        lock_fd = os.open(path + ".lock", os.O_RDWR | os.O_CREAT | binary, 0o600)
    except OSError:
        return False, None
    try:
        if not _lock(lock_fd):
            return False, None
        try:
            return True, fn()
        finally:
            _unlock(lock_fd)
    finally:
        try:
            os.close(lock_fd)
        except OSError:
            pass


def _append_unlocked(path: str, line: str) -> bool:
    """Append + verify one line; the CALLER holds the lock. Never raises."""
    binary = getattr(os, "O_BINARY", 0)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | binary, 0o600)
        try:
            os.write(fd, line.encode("utf-8"))
        finally:
            os.close(fd)
    except OSError:
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return False
    return content.endswith(line)


def _read_log(path: str) -> "list[dict]":
    """Read every JSON line in path. [] if the file does not exist.

    Raises LogCorrupt on the first line that is not a valid JSON object -
    `check` treats that as a refusal, never a partial read.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return []
    entries = []
    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except ValueError as exc:
            raise LogCorrupt("line %d: %s" % (i + 1, exc)) from exc
        if not isinstance(entry, dict):
            raise LogCorrupt("line %d: not a JSON object" % (i + 1))
        entries.append(entry)
    return entries


# --------------------------------------------------------------------------
# diagnostics-only parsing and status classification
# --------------------------------------------------------------------------

def parse_out(text: "str | None") -> dict:
    """Diagnostics only from a Codex exec .out transcript - never a status.

    Returns {"assistant_message_markers": int, "tokens_used": int|None,
    "flags": {"safety_block": bool, "tool_violation": bool,
    "bridge_evidence": bool}}.

    assistant_message_markers counts lines that are EXACTLY `codex`; see
    the module docstring for why this is diagnostic only. tokens_used
    strips thousands separators from the number on the line right after
    the first "tokens used" line; a missing or non-numeric value is
    None, never 0. bridge_evidence looks for "17841" or the word
    "bridge" - the harmless 426 websocket line lane-w.md documents on
    every run never matches either on its own.
    """
    text = text or ""
    markers = len(_MARKER_RE.findall(text))
    tokens = None
    m = _TOKENS_RE.search(text)
    if m:
        raw = m.group(1).replace(",", "")
        if raw.isdigit():
            tokens = int(raw)
    flags = {
        "safety_block": bool(_SAFETY_RE.search(text)),
        "tool_violation": bool(_TOOL_EXIT_RE.search(text)) or bool(_EXEC_EVENT_RE.search(text)),
        "bridge_evidence": _bridge_evidence(text),
    }
    return {"assistant_message_markers": markers, "tokens_used": tokens, "flags": flags}


def _bridge_evidence(text: str) -> bool:
    """True when 17841/"bridge" appears OUTSIDE the routine harmless-426 line.

    lane-w.md documents a "426 Upgrade Required" websocket warning on
    EVERY run, and that line itself names the bridge's port
    (ws://127.0.0.1:17841/...) - so matching "17841" anywhere would flag
    every single run as bridge evidence. Only a mention outside that
    known-harmless line counts.
    """
    for line in text.splitlines():
        if "426" in line:
            continue
        if _BRIDGE_RE.search(line):
            return True
    return False


def classify(exit_code, report_text, signals, contract_ok, report_fresh) -> str:
    """Return a terminal status string from evidence, in fixed precedence.

    exit_code: raw process exit code (int) or None if unknown.
    report_text: the captured --output-last-message content (or the
        lane-w.md fallback parse), possibly empty.
    signals: the dict parse_out() returned for the paired .out transcript.
    contract_ok: bool - whether report_text satisfies the job's declared
        contract (caller decides what the contract is; this function
        only orders that verdict against the other evidence).
    report_fresh: bool - whether the report file's mtime postdates this
        job's own ts_start (see _is_fresh).

    Precedence: timeout (124) > safety block > tool/delegation violation
    > evidenced bridge failure (nonzero exit AND port 17841 / "bridge"
    in evidence - a harmless 426 websocket line alone never trips this)
    > other nonzero exit > empty/stale report > contract invalid > ok.
    """
    flags = (signals or {}).get("flags") or {}
    report_text = report_text or ""

    if exit_code == 124:
        return "timeout"
    if flags.get("safety_block") or _SAFETY_RE.search(report_text):
        return "blocked"
    if flags.get("tool_violation"):
        return "tool_violation"
    nonzero = exit_code not in (0, None)
    if nonzero and flags.get("bridge_evidence"):
        return "bridge_failure"
    if nonzero:
        return "exit_nonzero"
    if not report_fresh:
        return "stale_report"
    if not report_text.strip():
        return "empty_report"
    if not contract_ok:
        return "contract_invalid"
    return "ok"


# --------------------------------------------------------------------------
# two-phase record API
# --------------------------------------------------------------------------

def _base_entry(job_id, run, name, model, out_path, report_path):
    return {
        "job_id": job_id,
        "run": run,
        "name": name,
        "model": model,
        "ts_start": None,
        "ts_end": None,
        "codex_exit": None,
        "duration_s": None,
        "assistant_message_markers": None,
        "tokens_used": None,
        "web_messages": None,
        "usage_complete": False,
        "status": None,
        "out_path": out_path,
        "report_path": report_path,
        "stop_latch": False,
    }


def _started_entry(run, name, model, out_path, report_path, owner_pid=None,
                   owner_created=None) -> dict:
    entry = _base_entry(uuid.uuid4().hex, run, name, model, out_path, report_path)
    entry["ts_start"] = _now_iso()
    entry["status"] = "started"
    if owner_pid is not None:
        entry["owner_pid"] = int(owner_pid)
    if owner_created is not None:
        entry["owner_created"] = int(owner_created)
    return entry


def record_start(run, name, model, out_path, report_path, log_path=None,
                 owner_pid=None, owner_created=None) -> dict:
    """Write the `started` reservation line BEFORE launch. Returns the entry.

    entry["_append_ok"] is False when the append could not be verified -
    the caller (the CLI, then bin/lanew) must treat that as "usage
    unknown, do not launch" and exit nonzero rather than proceed.
    owner_pid (optional int) is stored as `owner_pid`, owner_created
    (optional int, see pid_created) as `owner_created`; omitted, the record
    is exactly what it always was (module docstring, in-flight rule).
    """
    if log_path is None:
        log_path = LOG_PATH
    entry = _started_entry(run, name, model, out_path, report_path, owner_pid, owner_created)
    ok = append_line_verified(log_path, json.dumps(entry, sort_keys=True) + "\n")
    entry["_append_ok"] = ok
    return entry


def record_end(job_id, run, name, model, ts_start, codex_exit, out_path, report_path,
                log_path=None) -> dict:
    """Write the terminal record for job_id. Returns the entry (with status).

    Reads out_path (for parse_out diagnostics) and report_path (for the
    emptiness/contract checks in classify) from disk; a missing file is
    empty/absent evidence, never a passing result. Sets stop_latch True
    whenever status != "ok" (the docs' no-retry-in-the-run rule).
    """
    if log_path is None:
        log_path = LOG_PATH
    out_text = _read_text(out_path)
    report_text = _read_text(report_path)
    signals = parse_out(out_text)
    report_fresh = _is_fresh(report_path, ts_start)
    contract_ok = bool(report_text) and report_text.strip().lower() not in ("", "codex")
    ts_end = _now_iso()
    status = classify(codex_exit, report_text, signals, contract_ok, report_fresh)

    entry = _base_entry(job_id, run, name, model, out_path, report_path)
    entry["ts_start"] = ts_start
    entry["ts_end"] = ts_end
    entry["codex_exit"] = codex_exit
    entry["duration_s"] = _duration(ts_start, ts_end)
    entry["assistant_message_markers"] = signals["assistant_message_markers"]
    entry["tokens_used"] = signals["tokens_used"]
    entry["usage_complete"] = True
    entry["status"] = status
    entry["stop_latch"] = status != "ok"
    ok = append_line_verified(log_path, json.dumps(entry, sort_keys=True) + "\n")
    entry["_append_ok"] = ok
    return entry


def record_preflight_failed(run, name, model, log_path=None) -> dict:
    """Write a started+terminal pair for a job that never launched.

    Step 3 of bin/lanew (preflight) can fail before codex exec ever
    runs. Both halves are written together, with zero markers and null
    tokens, because launch definitely did not occur. stop_latch is set
    (a preflight failure is not "ok" and the run should not retry blind).
    """
    if log_path is None:
        log_path = LOG_PATH
    job_id = uuid.uuid4().hex
    ts = _now_iso()
    start_entry = _base_entry(job_id, run, name, model, None, None)
    start_entry["ts_start"] = ts
    start_entry["status"] = "started"
    ok1 = append_line_verified(log_path, json.dumps(start_entry, sort_keys=True) + "\n")

    end_entry = _base_entry(job_id, run, name, model, None, None)
    end_entry["ts_start"] = ts
    end_entry["ts_end"] = ts
    end_entry["codex_exit"] = None
    end_entry["duration_s"] = 0.0
    end_entry["assistant_message_markers"] = 0
    end_entry["tokens_used"] = None
    end_entry["usage_complete"] = True
    end_entry["status"] = "preflight_failed"
    end_entry["stop_latch"] = True
    ok2 = append_line_verified(log_path, json.dumps(end_entry, sort_keys=True) + "\n")

    end_entry["_append_ok"] = ok1 and ok2
    return end_entry


# --------------------------------------------------------------------------
# check / report
# --------------------------------------------------------------------------

def check(run, log_path=None, ceiling=None):
    """Return (ok: bool, reason: str). ok True means the run may launch.

    Fails closed: log unreadable, any job with a started-but-no-terminal
    record (unknown usage), any latched terminal record, or the run's
    counted-job total at/over the ceiling, all refuse. A started-but-no-
    terminal job whose `owner_pid` is present and alive is IN FLIGHT
    (module docstring): counted toward the ceiling, never a refusal by
    itself - unless its recorded owner_created differs from that live
    pid's creation time (a reused pid: refuse). A log file that
    does not exist at all, with therefore no prior record of ANY run
    including this one, is the first-run bootstrap case and passes -
    that is the one place "missing" is not treated as a failure.
    """
    if log_path is None:
        log_path = LOG_PATH
    if ceiling is None:
        ceiling = RUN_JOB_CEILING
    if not os.path.exists(log_path):
        return True, "no log yet at %s (first run) - nothing to check" % log_path
    try:
        entries = _read_log(log_path)
    except LogCorrupt as exc:
        return False, "log is corrupt: %s" % exc

    jobs = {}
    latched = False
    for e in entries:
        if e.get("run") != run:
            continue
        jid = e.get("job_id")
        if not jid:
            continue
        state = jobs.setdefault(jid, {"started": False, "terminal": False, "owner_pid": None,
                                      "owner_created": None, "ts_start": None})
        if e.get("status") == "started":
            state["started"] = True
            state["ts_start"] = e.get("ts_start")
            pid = e.get("owner_pid")
            if isinstance(pid, int) and not isinstance(pid, bool):
                state["owner_pid"] = pid
            created = e.get("owner_created")
            if isinstance(created, int) and not isinstance(created, bool):
                state["owner_created"] = created
        else:
            state["terminal"] = True
        if e.get("stop_latch"):
            latched = True

    if not jobs:
        return True, "no prior record of run %r - first-run case" % run

    open_jobs = [s for s in jobs.values() if s["started"] and not s["terminal"]]
    now = datetime.now(timezone.utc)

    def _young(s):
        started = _parse_iso(s["ts_start"])
        return started is not None and (now - started).total_seconds() <= IN_FLIGHT_MAX_AGE_S

    def _owner_live(s):
        if not pid_alive(s["owner_pid"]):
            return False
        # owner_created recorded: the live pid must be that very process, not a reuse
        return s["owner_created"] is None or pid_created(s["owner_pid"]) == s["owner_created"]

    in_flight = [s for s in open_jobs
                 if s["owner_pid"] is not None and _young(s) and _owner_live(s)]
    unknown = [s for s in open_jobs if s not in in_flight]
    if unknown:
        return False, ("%d job(s) in run %r have a started record with no terminal "
                        "record - usage unknown, refusing" % (len(unknown), run))
    if latched:
        return False, "run %r is latched (a prior job was not ok) - no further launches" % run

    counted = len(jobs)
    flying = (" (%d in flight)" % len(in_flight)) if in_flight else ""
    if counted >= ceiling:
        return False, ("run %r has %d counted job(s)%s, at or over the ceiling (%d jobs - a "
                        "proxy, since turns are not measurable from here)"
                        % (run, counted, flying, ceiling))
    return True, ("run %r has %d counted job(s)%s, under the ceiling (%d)"
                  % (run, counted, flying, ceiling))


def admit(run, name, model, out_path, report_path, owner_pid=None, log_path=None,
          ceiling=None, owner_created=None):
    """Atomic `check` + `record start`. Returns (status, reason, entry).

    Under the log's lock file, in ONE critical section: run the check()
    logic and, only if it passes, append the started record (with
    owner_pid / owner_created when given). Two parallel callers at ceiling-1 therefore
    can never both be admitted. status is "admitted" (entry is the
    started record), "refused" (check said no; NOTHING appended; entry
    None) or "log_error" (lock not taken, or the append could not be
    verified - usage unknown, the caller must not launch).
    """
    if log_path is None:
        log_path = LOG_PATH

    def critical():
        ok, reason = check(run, log_path=log_path, ceiling=ceiling)
        if not ok:
            return "refused", reason, None
        entry = _started_entry(run, name, model, out_path, report_path, owner_pid,
                               owner_created)
        appended = _append_unlocked(log_path, json.dumps(entry, sort_keys=True) + "\n")
        entry["_append_ok"] = appended
        if not appended:
            return "log_error", "failed to write the started reservation", entry
        return "admitted", reason, entry

    locked, result = _with_log_lock(log_path, critical)
    if not locked:
        return "log_error", "could not take the log lock %s.lock" % log_path, None
    return result


def report(days=None, run=None, log_path=None) -> str:
    """Return a formatted usage report. See module docstring for scope."""
    if log_path is None:
        log_path = LOG_PATH
    try:
        entries = _read_log(log_path)
    except LogCorrupt as exc:
        return "lanew usage report: LOG CORRUPT (%s)" % exc

    if days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        kept = []
        for e in entries:
            ts = _parse_iso(e.get("ts_start"))
            if ts is not None and ts >= cutoff:
                kept.append(e)
        entries = kept
    if run is not None:
        entries = [e for e in entries if e.get("run") == run]

    terminal = [e for e in entries if e.get("status") != "started"]
    lines = ["lanew usage report", ""]
    if not terminal:
        lines.append("(no terminal jobs recorded)")
    else:
        header = "%-16s %-16s %-18s %8s %10s  %s" % (
            "run", "name", "status", "markers", "tokens", "day")
        lines.append(header)
        for e in sorted(terminal, key=lambda x: x.get("ts_start") or ""):
            day = (e.get("ts_start") or "")[:10]
            lines.append("%-16s %-16s %-18s %8s %10s  %s" % (
                str(e.get("run"))[:16], str(e.get("name"))[:16], str(e.get("status"))[:18],
                str(e.get("assistant_message_markers")), str(e.get("tokens_used")), day))
    lines.append("")
    lines.append("jobs: %d" % len(terminal))
    lines.append("")
    lines.append("web_messages are not observable; this is not remaining allowance.")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _cli_record(argv) -> int:
    if not argv:
        print("lanew_log record: expected start|end|preflight-failed", file=sys.stderr)
        return 2
    sub = argv[0]
    rest = argv[1:]
    if sub == "start":
        p = argparse.ArgumentParser(prog="lanew_log record start")
        p.add_argument("--run", required=True)
        p.add_argument("--name", required=True)
        p.add_argument("--model", required=True)
        p.add_argument("--out", required=True)
        p.add_argument("--report", required=True)
        p.add_argument("--pid", type=int, default=None, dest="owner_pid")
        p.add_argument("--pid-created", type=int, default=None, dest="owner_created")
        args = p.parse_args(rest)
        entry = record_start(args.run, args.name, args.model, args.out, args.report,
                             owner_pid=args.owner_pid, owner_created=args.owner_created)
        if not entry.get("_append_ok"):
            print("lanew_log: failed to write the started reservation - usage unknown, "
                  "refusing to launch", file=sys.stderr)
            return 3
        print(json.dumps({"job_id": entry["job_id"], "ts_start": entry["ts_start"]}))
        return 0
    if sub == "end":
        p = argparse.ArgumentParser(prog="lanew_log record end")
        p.add_argument("--job-id", required=True)
        p.add_argument("--run", required=True)
        p.add_argument("--name", required=True)
        p.add_argument("--model", required=True)
        p.add_argument("--ts-start", required=True)
        p.add_argument("--exit", required=True, type=int, dest="codex_exit")
        p.add_argument("--out", required=True)
        p.add_argument("--report", required=True)
        args = p.parse_args(rest)
        entry = record_end(args.job_id, args.run, args.name, args.model, args.ts_start,
                            args.codex_exit, args.out, args.report)
        print("status=%s report=%s" % (entry["status"], entry["report_path"]))
        if not entry.get("_append_ok"):
            print("lanew_log: failed to write the terminal record - usage unknown, "
                  "latching (in-memory) this invocation", file=sys.stderr)
            return 3
        return 0 if entry["status"] == "ok" else 1
    if sub == "preflight-failed":
        p = argparse.ArgumentParser(prog="lanew_log record preflight-failed")
        p.add_argument("--run", required=True)
        p.add_argument("--name", required=True)
        p.add_argument("--model", required=True)
        args = p.parse_args(rest)
        entry = record_preflight_failed(args.run, args.name, args.model)
        print("status=%s" % entry["status"])
        if not entry.get("_append_ok"):
            print("lanew_log: failed to write the preflight-failure record", file=sys.stderr)
        return 2
    print("lanew_log record: unknown subcommand %r" % sub, file=sys.stderr)
    return 2


def _cli_check(argv) -> int:
    p = argparse.ArgumentParser(prog="lanew_log check")
    p.add_argument("--run", required=True)
    args = p.parse_args(argv)
    ok, reason = check(args.run)
    print(reason)
    return 0 if ok else 1


def _cli_admit(argv) -> int:
    p = argparse.ArgumentParser(prog="lanew_log admit")
    p.add_argument("--run", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--pid", type=int, default=None, dest="owner_pid")
    p.add_argument("--pid-created", type=int, default=None, dest="owner_created")
    args = p.parse_args(argv)
    status, reason, entry = admit(args.run, args.name, args.model, args.out, args.report,
                                  owner_pid=args.owner_pid, owner_created=args.owner_created)
    if status == "admitted":
        print(json.dumps({"job_id": entry["job_id"], "ts_start": entry["ts_start"]}))
        return 0
    if status == "refused":
        print(reason, file=sys.stderr)
        return 1
    print("lanew_log admit: %s - usage unknown, refusing to launch" % reason, file=sys.stderr)
    return 3


def _cli_report(argv) -> int:
    p = argparse.ArgumentParser(prog="lanew_log report")
    p.add_argument("--days", type=float, default=None)
    p.add_argument("--run", default=None)
    args = p.parse_args(argv)
    print(report(days=args.days, run=args.run))
    return 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("usage: lanew_log.py {record start|record end|record preflight-failed"
              "|check --run R|admit --run R ...|report [--days N] [--run R]}", file=sys.stderr)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "record":
        return _cli_record(rest)
    if cmd == "check":
        return _cli_check(rest)
    if cmd == "admit":
        return _cli_admit(rest)
    if cmd == "report":
        return _cli_report(rest)
    print("lanew_log: unknown command %r" % cmd, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
