"""astrapro - send ONE brief to GPT-6 Astra Pro through the local, browser-only
codex-chatgpt-web bridge (the "Codex Web GPT" launcher); the answer lands in a
report file.

Usage: astrapro <run> <name> [--keep-open] < brief.md
(bin/astrapro and bin/astrapro.cmd are thin shims that run this file.)

The brief must carry a line `brief-check: clean - <why it is clean>` (the
author's attestation: no client PII, no money figures tied to a client, no
credentials), be valid UTF-8 of at most 20,000 characters (a leading BOM is
stripped) and pass the jev_privacy secret scan. Only the brief leaves the
machine: codex runs read-only in an empty directory this wrapper owns, with
its own CODEX_HOME, never ~/.codex.

Exit codes (documented verbatim elsewhere - keep them):
  0    ok
  1    run refused by the logger (cap reached, latched, unknown-usage job)
  2    bridge/preflight refused (launcher not healthy within the deadline, mode
       not browser-only, cwd/AGENTS/git-tree/home guard, launcher identity
       check failed)
  3    logging failure
  4    model not allowed
  5    no free slot within the wait, the state lock busy, or the total
       deadline (the reason says which)
  6    the job ran and did not end ok (the `record end` status is in the JSON)
  7    brief gate
  64   usage error (run/name must match [A-Za-z0-9._-]{1,80})
  130  interrupted (Ctrl-C / Ctrl-Break)
Stdout: exactly one JSON status line on every exit path (keys tool, exit,
status, reason, run, name, model, job_id, report, out). Steps log one line
each to stderr.

Env: ASTRAPRO_MODEL (chatgpt-web/gpt-6-pro default | chatgpt-web/gpt-6-sol),
  ASTRAPRO_MAX_PARALLEL (default 3, clamped to 1..3), ASTRAPRO_RUN_JOB_CEILING
  (default 4), ASTRAPRO_SLOT_WAIT (s, default 600), ASTRAPRO_TOTAL_DEADLINE (s
  from process start, default 3300), ASTRAPRO_CODEX_HOME (default
  ~/.codex-web), ASTRAPRO_LAUNCHER (default %LOCALAPPDATA%/Programs/Codex Web
  GPT/Codex Web GPT.exe), CLIPROXY_DIR (default ~/.cli-proxy-api: usage log,
  outputs and the astrapro.d state dir live under it).
Test-only, honoured ONLY with ASTRAPRO_DRY_RUN=1 (exit 2 otherwise):
  ASTRAPRO_LAUNCHER_CMD (command line, split with POSIX shlex rules - use
  forward slashes - started instead of the launcher), ASTRAPRO_HEALTH_URL
  (default http://127.0.0.1:17841/healthz), ASTRAPRO_LAUNCH_DEADLINE (default
  300 s), ASTRAPRO_STATE_LOCK_WAIT (default 360 s), ASTRAPRO_LAUNCHER_IMAGE
  (image name of the test launcher, default its argv[0] name),
  ASTRAPRO_SUPERVISOR_JSON (default ~/.codex-chatgpt-web/runtime/
  launcher-supervisor.json), ASTRAPRO_DRY_RUN_SLEEP (seconds the fake job
  runs), and every ASTRAPRO_TEST_* hook: _SPAWN_PAUSE (after the launcher
  Popen, before its marker is published), _STOP_PAUSE (in the stop path,
  after the decision, before the releases), _CHILD_PAUSE (right after the job
  child exists), _FAIL_KILL=1 (every kill is skipped: a failed stop),
  _KILL_CONFIRM (seconds to wait for a killed tree, default 15),
  _FAIL_DAEMON_KILL=1 (the daemon kill is skipped), _SIGINT_AFTER_DAEMON=1
  and _SIGINT_IN_ACTIVE_LOCK=1 (raise SIGINT at those points),
  _JOB_GRANDCHILD=<pidfile> (the fake job leaves a sleeper behind).
  ASTRAPRO_DRY_RUN=1 replaces `codex exec` with a local fake job (a python
  sleeper started exactly like codex); without ASTRAPRO_LAUNCHER_CMD it also
  skips the bridge entirely.

Design (T4, 2026-10-17):
- Locks are OS locks: a non-blocking exclusive lock on byte 0 of
  astrapro.d/state.lock and astrapro.d/slot-1..3.lock (msvcrt.locking on
  Windows, fcntl.flock elsewhere), polled until a deadline. The OS releases
  them when the holder dies; lock files are never deleted, never broken.
- One time budget: ASTRAPRO_TOTAL_DEADLINE (default 3300 s) from process
  start bounds the start path and the job; every wait is clamped to it
  (slot, state lock, launch: each leaves the job 60 s + a 180 s reserve, or
  exit 5 "deadline"), and cleanup is clamped to 90 s past it, so the whole
  process ends within ASTRAPRO_TOTAL_DEADLINE + 90 s (3,390 s by default).
- Start: slot lock (ASTRAPRO_SLOT_WAIT) -> state lock (360 s) -> resolve the
  ownership marker -> healthz: up and browser-only = use it (owned only when
  the marker's process provably serves it); down = refuse (exit 2) if any
  other job is ACTIVE on the bridge, else spawn the launcher (Popen of the
  exe, detached, no shell), publish the marker, wait for healthz (300 s)
  still holding the state lock, verify mode and ownership -> take this
  slot's active lock (astrapro.d/active-N.lock, held until the stop path) ->
  release the state lock -> total-deadline check -> admit (atomic check +
  started record, owner pid + creation time) -> job -> record end.
- Ownership marker astrapro.d/launcher-owned: {"pid", "created",
  "spawner_pid", "spawner_created"}; before the Popen an intent marker
  {"spawner_pid", "spawner_created", "spawned_at"}. A marker matches only a
  live process with the same pid AND creation time - checked before every
  kill. A launcher is stopped only by its marker pid's tree (taskkill /PID
  <pid> /T /F), never by image name - plus, when its ownership was verified
  through launcher-supervisor.json, the daemon recorded then (pid, creation
  time and image checked). A failed stop keeps the marker for the next run.
- Stop (finally, every exit path): state lock -> probe the other slots ->
  stop the launcher only when no other slot is held, the marker matches and
  no keep-open marker exists -> release own active lock and slot -> release
  the state lock. A job that never held the state lock drops its slot at once.
- The codex child runs in a Job Object with KILL_ON_JOB_CLOSE: right before
  admit the wrapper puts ITSELF in a new such job, so the child is born in
  it (no window between creation and membership) and a hard-killed wrapper
  takes its job tree with it - a freed slot is a free seat. The launcher is
  spawned earlier, never later, so it is not in the job.
- A hard kill cannot run cleanup: the OS frees the locks, the next job
  adopts or stops the orphan launcher by its marker, and the started record
  stays without an end, so the logger refuses that run (fail closed).
"""
import contextlib
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import lanew_log  # noqa: E402 - sits next to this file

try:  # Windows
    import msvcrt
except ImportError:  # pragma: no cover - POSIX
    msvcrt = None
try:  # POSIX
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None

WINDOWS = os.name == "nt"
USAGE = "usage: astrapro <run> <name> [--keep-open] < brief.md"
NAME_RE = re.compile(r"[A-Za-z0-9._-]{1,80}")
MODELS = ("chatgpt-web/gpt-6-pro", "chatgpt-web/gpt-6-sol")
ATTEST_RE = re.compile(r"(?m)^brief-check: clean - (\S[^\r\n]*)")
MAX_BRIEF = 20000            # jev_privacy.has_secret scans only this much
HARD_MAX = 3                 # slot lock files slot-1..3
DEFAULT_HEALTH_URL = "http://127.0.0.1:17841/healthz"
LAUNCH_DEADLINE = 300        # cold start: ~120 s of hash checks before healthz answers
STATE_LOCK_WAIT = 360        # must exceed LAUNCH_DEADLINE: the launch happens under the lock
TOTAL_DEADLINE = 3300        # from process start; docs give the Bash call 3,600,000 ms
JOB_CAP = 1500               # codex job timeout = min(JOB_CAP, remaining - JOB_RESERVE)
JOB_RESERVE = 180
JOB_MIN = 60                 # less than this for the job -> exit 5 "deadline"
CLEANUP_GRACE = 90           # cleanup may run this long past the total deadline (R3):
                             # the process ends by ASTRAPRO_TOTAL_DEADLINE + 90 s
STOP_RESERVE = 30            # cleanup's state-lock wait leaves this much for the stop
KILL_TIMEOUT = 20            # one taskkill call
KILL_CONFIRM = 15            # wait for a killed tree to be gone
HEALTH_TIMEOUT = 3           # one whole healthz request + read, wall clock
AGENTS_FILES = ("AGENTS.md", "AGENTS.override.md")
TEST_ONLY = ("ASTRAPRO_LAUNCHER_CMD", "ASTRAPRO_HEALTH_URL", "ASTRAPRO_LAUNCH_DEADLINE",
             "ASTRAPRO_STATE_LOCK_WAIT", "ASTRAPRO_LAUNCHER_IMAGE", "ASTRAPRO_DRY_RUN_SLEEP",
             "ASTRAPRO_SUPERVISOR_JSON")
DRY_JOB = ("import subprocess, sys, time\n"
           "if len(sys.argv) > 3:  # test hook: leave a descendant behind\n"
           "    g = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'],\n"
           "                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,\n"
           "                         stderr=subprocess.DEVNULL)\n"
           "    open(sys.argv[3], 'w').write(str(g.pid))\n"
           "time.sleep(float(sys.argv[1]))\n"
           "print('dry run: no codex exec', flush=True)\n"
           "open(sys.argv[2], 'w', encoding='utf-8').write('DRY-RUN-OK\\n')\n")

DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200

pid_alive = lanew_log.pid_alive
pid_created = lanew_log.pid_created
_TEST = {"fail_kill": False, "fail_daemon_kill": False}  # test-only hooks (dry run only)


def log(msg):
    try:
        print("astrapro: " + msg, file=sys.stderr, flush=True)
    except (OSError, ValueError):
        pass


class Exit(Exception):
    """Ends the run with one exit code, status and reason (the JSON line)."""

    def __init__(self, code, status, reason):
        super().__init__(reason)
        self.code, self.status, self.reason = code, status, reason


class Budget:
    """One time budget for the whole process (R3), on an injectable clock.

    deadline = start + ASTRAPRO_TOTAL_DEADLINE: the start path and the job end
    by it - every start-path wait (slot, state lock, launch) leaves the job its
    JOB_MIN plus JOB_RESERVE, and the job timeout is min(JOB_CAP, left -
    JOB_RESERVE). end = deadline + CLEANUP_GRACE: every cleanup wait (job kill,
    state lock, launcher stop) is clamped to it, so the process ends by then.
    """

    def __init__(self, total, clock=time.monotonic, t0=None):
        self.clock = clock
        self.t0 = clock() if t0 is None else t0
        self.deadline = self.t0 + total
        self.end = self.deadline + CLEANUP_GRACE

    def left(self):
        return self.deadline - self.clock()

    def start_wait(self, want):
        return max(0.0, min(want, self.left() - JOB_RESERVE - JOB_MIN))

    def job_timeout(self):
        return min(JOB_CAP, self.left() - JOB_RESERVE)

    def cleanup_left(self):
        return self.end - self.clock()

    def cleanup_wait(self, want, reserve=0.0):
        return max(0.0, min(want, self.cleanup_left() - reserve))


# --------------------------------------------------------------------------
# signals: SIGINT / SIGBREAK raise Interrupted once; deferred() holds it back
# across a few critical steps so bookkeeping never half-happens.
# --------------------------------------------------------------------------

class Interrupted(BaseException):
    def __init__(self, signame):
        super().__init__(signame)
        self.signame = signame


_SIG = {"pending": None, "armed": True, "defer": 0}


def _signame(signum):
    for name in ("SIGINT", "SIGBREAK", "SIGTERM"):
        if getattr(signal, name, None) == signum:
            return name
    return str(signum)


def _on_signal(signum, _frame):
    if _SIG["pending"] is None:
        _SIG["pending"] = _signame(signum)
    if _SIG["armed"] and _SIG["defer"] == 0:
        _SIG["armed"] = False
        raise Interrupted(_SIG["pending"])


@contextlib.contextmanager
def deferred():
    _SIG["defer"] += 1
    try:
        yield
    finally:
        _SIG["defer"] -= 1
    if _SIG["defer"] == 0 and _SIG["pending"] and _SIG["armed"]:
        _SIG["armed"] = False
        raise Interrupted(_SIG["pending"])


def install_signals():
    for name in ("SIGINT", "SIGBREAK", "SIGTERM"):
        sig = getattr(signal, name, None)
        if sig is not None:
            try:
                signal.signal(sig, _on_signal)
            except (ValueError, OSError):  # pragma: no cover - not the main thread
                pass


def disarm():
    _SIG["armed"] = False


# --------------------------------------------------------------------------
# OS locks
# --------------------------------------------------------------------------

class FileLock:
    """Exclusive OS lock on byte 0 of path; freed by the OS when the holder dies."""

    def __init__(self, path):
        self.path = path
        self.fd = None

    @property
    def held(self):
        return self.fd is not None

    def try_acquire(self):
        if self.fd is not None:
            return True
        with deferred():
            fd = os.open(self.path, os.O_RDWR | os.O_CREAT | getattr(os, "O_BINARY", 0)
                         | getattr(os, "O_NOINHERIT", 0), 0o600)
            try:
                if msvcrt is not None:
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                os.close(fd)
                return False
            self.fd = fd
            if getattr(self, "test_sigint", False):  # test hook: a signal inside the region
                self.test_sigint = False
                signal.raise_signal(signal.SIGINT)
        return True

    def acquire(self, timeout, poll=0.1):
        end = time.monotonic() + max(0.0, timeout)
        while True:
            if self.try_acquire():
                return True
            if time.monotonic() >= end:
                return False
            time.sleep(poll)

    def release(self):
        fd, self.fd = self.fd, None
        if fd is None:
            return
        try:
            if msvcrt is not None:
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass
        finally:
            os.close(fd)


# --------------------------------------------------------------------------
# processes: identity, snapshot, tree kill, job object
# --------------------------------------------------------------------------

if WINDOWS:
    import ctypes
    from ctypes import wintypes

    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)

    def _proto(name, restype, *argtypes):
        fn = getattr(_k32, name)
        fn.restype = restype
        fn.argtypes = list(argtypes)
        return fn

    class _PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
                    ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                    ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_wchar * 260)]

    class _BASIC_LIMIT(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64),
                    ("PerJobUserTimeLimit", ctypes.c_int64), ("LimitFlags", wintypes.DWORD),
                    ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t),
                    ("ActiveProcessLimit", wintypes.DWORD), ("Affinity", ctypes.c_size_t),
                    ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]

    class _IO_COUNTERS(ctypes.Structure):
        _fields_ = [(n, ctypes.c_uint64) for n in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class _EXTENDED_LIMIT(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", _BASIC_LIMIT), ("IoInfo", _IO_COUNTERS),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t)]

    _INVALID = ctypes.c_void_p(-1).value
    _OpenProcess = _proto("OpenProcess", wintypes.HANDLE, wintypes.DWORD, wintypes.BOOL,
                          wintypes.DWORD)
    _CloseHandle = _proto("CloseHandle", wintypes.BOOL, wintypes.HANDLE)
    _Snapshot = _proto("CreateToolhelp32Snapshot", wintypes.HANDLE, wintypes.DWORD,
                       wintypes.DWORD)
    _Process32FirstW = _proto("Process32FirstW", wintypes.BOOL, wintypes.HANDLE,
                              ctypes.POINTER(_PROCESSENTRY32W))
    _Process32NextW = _proto("Process32NextW", wintypes.BOOL, wintypes.HANDLE,
                             ctypes.POINTER(_PROCESSENTRY32W))
    _GetCurrentProcess = _proto("GetCurrentProcess", wintypes.HANDLE)
    _GetSystemTimeAsFileTime = _proto("GetSystemTimeAsFileTime", None,
                                      ctypes.POINTER(ctypes.c_uint64))
    _CreateJobObjectW = _proto("CreateJobObjectW", wintypes.HANDLE, ctypes.c_void_p,
                               wintypes.LPCWSTR)
    _SetInformationJobObject = _proto("SetInformationJobObject", wintypes.BOOL, wintypes.HANDLE,
                                      ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
    _AssignProcessToJobObject = _proto("AssignProcessToJobObject", wintypes.BOOL,
                                       wintypes.HANDLE, wintypes.HANDLE)

    def _winerr(what):
        return OSError("%s failed (winerror %d)" % (what, ctypes.get_last_error()))


def process_snapshot():
    """{pid: (parent pid, lower-case image name)} for every live process."""
    procs = {}
    if WINDOWS:
        snap = _Snapshot(0x2, 0)  # TH32CS_SNAPPROCESS
        if not snap or snap == _INVALID:
            return procs
        try:
            pe = _PROCESSENTRY32W()
            pe.dwSize = ctypes.sizeof(pe)
            more = _Process32FirstW(snap, ctypes.byref(pe))
            while more:
                procs[pe.th32ProcessID] = (pe.th32ParentProcessID, pe.szExeFile.lower())
                more = _Process32NextW(snap, ctypes.byref(pe))
        finally:
            _CloseHandle(snap)
        return procs
    for entry in os.listdir("/proc"):  # pragma: no cover - POSIX best effort
        if not entry.isdigit():
            continue
        try:
            with open("/proc/%s/stat" % entry, encoding="ascii", errors="replace") as f:
                stat = f.read()
            comm = stat[stat.index("(") + 1:stat.rindex(")")]
            procs[int(entry)] = (int(stat.rsplit(")", 1)[1].split()[1]), comm.lower())
        except (OSError, ValueError):
            continue
    return procs


def same_process(pid, created):
    """True when pid is alive AND is the very process created at `created`."""
    if not isinstance(pid, int) or isinstance(pid, bool) or not isinstance(created, int):
        return False
    return pid_created(pid) == created


def in_tree(root_pid, root_created, pid, snap=None):
    """True when live `pid` is root or a descendant of it through LIVE parents.

    Each link must be a live process created no later than its child, so a
    reused parent pid never links an unrelated process into the tree.
    """
    snap = process_snapshot() if snap is None else snap
    cur, cur_created, seen = pid, pid_created(pid), set()
    while cur and cur not in seen and cur_created is not None:
        if cur == root_pid:
            return cur_created == root_created
        seen.add(cur)
        parent = snap.get(cur, (0, ""))[0]
        parent_created = pid_created(parent)
        if not parent or parent_created is None or parent_created > cur_created:
            return False
        cur, cur_created = parent, parent_created
    return False


@contextlib.contextmanager
def pinned(pid):
    """Hold a handle on pid so it cannot be reused between a check and a kill."""
    h = None
    if WINDOWS and isinstance(pid, int) and pid > 0:
        h = _OpenProcess(0x00100000 | 0x1000, False, pid)  # SYNCHRONIZE | QUERY_LIMITED
    try:
        yield
    finally:
        if h:
            _CloseHandle(h)


def filetime_now():
    """Now as a FILETIME int (process creation times use the same units), or None."""
    if not WINDOWS:  # pragma: no cover - POSIX
        return None
    ft = ctypes.c_uint64()
    _GetSystemTimeAsFileTime(ctypes.byref(ft))
    return int(ft.value)


def descendants(root_pid, root_created, snap=None):
    """[(pid, created)] of live descendants of root (which may itself be dead).

    Walks the snapshot's parent links down from root; every link needs the
    child created no earlier than its parent, so a process that merely
    inherited a recycled parent pid is never taken for a descendant. Parents
    listed before their children.
    """
    if root_created is None:
        return []
    snap = process_snapshot() if snap is None else snap
    children = {}
    for p, (pp, _image) in snap.items():
        if p != pp:
            children.setdefault(pp, []).append(p)
    out, queue, seen = [], [(root_pid, root_created)], {root_pid}
    while queue:
        parent, parent_created = queue.pop(0)
        for c in children.get(parent, []):
            if c in seen:
                continue
            c_created = pid_created(c)
            if c_created is None or c_created < parent_created:
                continue
            seen.add(c)
            out.append((c, c_created))
            queue.append((c, c_created))
    return out


def kill_tree(pid, timeout=None):
    """Kill pid and its descendants - by pid, never by image name."""
    if _TEST["fail_kill"]:
        log("test hook: the kill of pid %s is skipped (a simulated failed kill)." % pid)
        return
    timeout = KILL_TIMEOUT if timeout is None else timeout
    if timeout <= 0:  # F1: no budget left - never stretch a clamped 0 into a real kill
        log("no time left in the budget to kill pid %s - skipping taskkill." % pid)
        return False
    if WINDOWS:
        taskkill = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32",
                                "taskkill.exe")
        try:
            subprocess.run([taskkill, "/PID", str(pid), "/T", "/F"], stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout)
        except (OSError, subprocess.SubprocessError):
            pass
        return True
    for kill in (lambda: os.killpg(pid, signal.SIGKILL), lambda: os.kill(pid, signal.SIGKILL)):
        try:  # pragma: no cover - POSIX
            kill()
            return True
        except OSError:
            continue
    return True


def join_kill_job():
    """Put THIS process in a new KILL_ON_JOB_CLOSE job object; return its handle.

    R2, race-free: CreateProcess puts a child in its parent's job atomically,
    so every process this wrapper creates afterwards is a job member from its
    first instruction - there is no window between creation and membership.
    The wrapper holds the only handle, so its death (even TerminateProcess)
    closes it and the job's processes die with it. The handle is never closed
    while the wrapper lives (that would end the wrapper too). Called after the
    launcher spawn and never before one, so the launcher stays outside.
    POSIX: None (the child gets its own session instead).
    """
    if not WINDOWS:  # pragma: no cover - POSIX
        return None
    job = _CreateJobObjectW(None, None)
    if not job:
        raise _winerr("CreateJobObjectW")
    info = _EXTENDED_LIMIT()
    info.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not _SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
        err = _winerr("SetInformationJobObject")
        _CloseHandle(job)
        raise err
    if not _AssignProcessToJobObject(job, _GetCurrentProcess()):
        err = _winerr("AssignProcessToJobObject")
        _CloseHandle(job)
        raise err
    return job


def start_job_child(argv, pause=0.0, **kw):
    """Popen the job child (codex, or the dry-run sleeper); stderr joins stdout.

    On Windows the caller is already in its kill-on-close job (join_kill_job),
    so the child is born in it. POSIX: a new session, killed as a group later.
    """
    kw.update(stderr=subprocess.STDOUT, close_fds=True)
    if not WINDOWS:  # pragma: no cover - POSIX best effort
        return subprocess.Popen(argv, start_new_session=True, **kw)
    proc = subprocess.Popen(argv, **kw)
    if pause:  # test-only: the earliest point after the child exists
        time.sleep(pause)
    return proc


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

_NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def health(url, limit=HEALTH_TIMEOUT):
    """(200, dict) when healthz answers 200; (code or None, None) otherwise.

    F1: the whole request and read are bounded by `limit` seconds of wall
    clock (a socket timeout alone lets a slow-drip response run forever):
    the fetch runs in a daemon thread that is abandoned at the limit. Under
    1 s of limit nothing is probed at all.
    """
    if limit < 1.0:
        return None, None
    box = {}

    def fetch():
        try:
            with _NO_PROXY.open(url, timeout=limit) as r:
                box["r"] = (r.status, r.read(65536))
        except urllib.error.HTTPError as exc:
            box["r"] = (exc.code, None)
        except Exception:
            box["r"] = (None, None)

    t = threading.Thread(target=fetch, daemon=True)
    t.start()
    t.join(limit)
    code, body = box.get("r", (None, None))
    if code != 200 or body is None:
        return code, None
    try:
        data = json.loads(body.decode("utf-8"))
    except ValueError:
        data = {}
    return 200, data if isinstance(data, dict) else {}


def win_path(p):
    """An MSYS path (/c/x) as a Windows one (C:/x); anything else unchanged."""
    if WINDOWS and p:
        m = re.match(r"^/([A-Za-z])(/|$)(.*)$", p)
        if m:
            return m.group(1).upper() + ":/" + m.group(3)
    return p


def canon(p):
    return os.path.normcase(os.path.realpath(os.path.expanduser(win_path(p)))).rstrip("\\/")


def fwd(p):
    return os.path.abspath(p).replace("\\", "/")


def read_json(path):
    """(exists, dict or None) - None when the file is unreadable or not a JSON object."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        return False, None
    except OSError:
        return True, None
    try:
        data = json.loads(raw)
    except ValueError:
        return True, None
    return True, data if isinstance(data, dict) else None


def write_json_atomic(path, obj):
    tmp = "%s.tmp.%d" % (path, os.getpid())
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f)
    os.replace(tmp, path)


def remove(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def resolve_codex():
    """The codex command: on Windows the codex.cmd shim on PATH (~/bin), else `codex`."""
    for name in (("codex.cmd", "codex") if WINDOWS else ("codex",)):
        found = shutil.which(name)
        if found:
            return found
    return None


# --------------------------------------------------------------------------
# the wrapper
# --------------------------------------------------------------------------

class Wrapper:
    def __init__(self, argv, env, clock=time.monotonic):
        self.clock = clock
        self.t0 = clock()
        self.budget = Budget(TOTAL_DEADLINE, clock, self.t0)
        self.argv, self.env = list(argv), dict(env)
        self.run = self.name = self.model = None
        self.job_id = self.ts_start = self.out = self.report = None
        self.keep_open = False
        self.dry = False
        self.bridge = False
        self.slot = self.slot_index = None
        self.active = None         # held from a successful start path to the stop path (R1)
        self.state = None
        self.state_ever_held = False
        self.spawned = None        # own launcher spawn not yet verified: {"pid", "created"}
        self.spawn_stop_failed = False
        self.launcher_proc = None  # keeps the spawned pid's handle open (no reuse)
        self.job_proc = self.job_handle = None
        self.job_created = None
        self.job_ended = False
        self.brief_tmp = None
        self.notes = []            # failures worth surfacing in the JSON reason (R4)
        self.kill_confirm = KILL_CONFIRM
        self.child_pause = 0.0
        self.sigint_after_daemon = self.sigint_in_active = False
        self.job_grandchild = ""
        self.my_pid = os.getpid()
        self.my_created = pid_created(self.my_pid)

    # ---- steps ---------------------------------------------------------------
    def main(self):
        self.parse_args()
        self.configure()
        self.model = self.env.get("ASTRAPRO_MODEL") or MODELS[0]
        if self.model not in MODELS:
            log("model %r is not allowed (%s) - refusing." % (self.model, " | ".join(MODELS)))
            raise Exit(4, "model_refused", "model %s not allowed" % self.model)
        log("step 1/8: run=%s name=%s model=%s keep_open=%d dry_run=%d"
            % (self.run, self.name, self.model, self.keep_open, self.dry))
        data = sys.stdin.buffer.read()
        chars = self.brief_gate(data)
        log("step 2/8: brief gate passed (%d characters)." % chars)
        self.local_guards()
        log("step 3/8: local guards ok (cwd %s empty, no AGENTS in %s)."
            % (self.empty_cwd, self.codex_home))
        self.deadline_check("before the slot wait")
        self.pre_check()
        self.take_slot()
        self.start_bridge()
        budget = self.deadline_check("before admit")
        self.enter_job()
        self.admit()
        self.launch_job(data)
        rc = self.wait_job(budget)
        self.end_job(rc)

    def parse_args(self):
        pos = []
        for a in self.argv:
            if a == "--keep-open":
                self.keep_open = True
            elif a in ("-h", "--help"):
                print(USAGE, file=sys.stderr)
                raise Exit(64, "usage_error", "help requested")
            elif a.startswith("-"):
                print(USAGE, file=sys.stderr)
                raise Exit(64, "usage_error", "unknown option %s" % a)
            else:
                pos.append(a)
        if len(pos) != 2:
            print(USAGE, file=sys.stderr)
            raise Exit(64, "usage_error", "expected <run> <name>")
        for v in pos:
            if not NAME_RE.fullmatch(v) or v in (".", ".."):
                print(USAGE, file=sys.stderr)
                raise Exit(64, "usage_error", "run and name must match [A-Za-z0-9._-]{1,80}: %r" % v)
        self.run, self.name = pos

    def configure(self):
        e = self.env
        dry = (e.get("ASTRAPRO_DRY_RUN") or "0").strip()
        if dry not in ("0", "1"):
            raise Exit(64, "usage_error", "ASTRAPRO_DRY_RUN must be 0 or 1")
        self.dry = dry == "1"
        test_set = sorted(k for k, v in e.items()
                          if v and (k in TEST_ONLY or k.startswith("ASTRAPRO_TEST_")))
        if test_set and not self.dry:
            log("%s: test-only (needs ASTRAPRO_DRY_RUN=1) - refusing." % ", ".join(test_set))
            raise Exit(2, "preflight_refused",
                       "test-only override set outside dry run: %s" % ", ".join(test_set))

        def num(key, default):
            raw = (e.get(key) or "").strip() or str(default)
            if not re.fullmatch(r"[0-9]+(\.[0-9]+)?", raw):
                raise Exit(64, "usage_error", "numeric setting expected for %s, got %r" % (key, raw))
            return float(raw)

        parallel = int(num("ASTRAPRO_MAX_PARALLEL", HARD_MAX))
        self.max_parallel = min(HARD_MAX, max(1, parallel))
        if self.max_parallel != parallel:
            log("ASTRAPRO_MAX_PARALLEL=%d is outside 1..%d - using %d."
                % (parallel, HARD_MAX, self.max_parallel))
        self.slot_wait = num("ASTRAPRO_SLOT_WAIT", 600)
        self.ceiling = int(num("ASTRAPRO_RUN_JOB_CEILING", 4))
        self.budget = Budget(num("ASTRAPRO_TOTAL_DEADLINE", TOTAL_DEADLINE), self.clock, self.t0)
        self.launch_deadline = num("ASTRAPRO_LAUNCH_DEADLINE", LAUNCH_DEADLINE)
        self.state_wait = num("ASTRAPRO_STATE_LOCK_WAIT", STATE_LOCK_WAIT)
        self.dry_sleep = num("ASTRAPRO_DRY_RUN_SLEEP", 0)
        self.spawn_pause = num("ASTRAPRO_TEST_SPAWN_PAUSE", 0)
        self.stop_pause = num("ASTRAPRO_TEST_STOP_PAUSE", 0)
        self.child_pause = num("ASTRAPRO_TEST_CHILD_PAUSE", 0)
        self.kill_confirm = num("ASTRAPRO_TEST_KILL_CONFIRM", KILL_CONFIRM)
        _TEST["fail_kill"] = bool(num("ASTRAPRO_TEST_FAIL_KILL", 0))
        _TEST["fail_daemon_kill"] = bool(num("ASTRAPRO_TEST_FAIL_DAEMON_KILL", 0))
        self.sigint_after_daemon = bool(num("ASTRAPRO_TEST_SIGINT_AFTER_DAEMON", 0))
        self.sigint_in_active = bool(num("ASTRAPRO_TEST_SIGINT_IN_ACTIVE_LOCK", 0))
        self.job_grandchild = e.get("ASTRAPRO_TEST_JOB_GRANDCHILD") or ""
        self.health_url = e.get("ASTRAPRO_HEALTH_URL") or DEFAULT_HEALTH_URL

        home = os.path.expanduser("~")
        self.cliproxy = os.path.abspath(win_path(e.get("CLIPROXY_DIR") or
                                                 os.path.join(home, ".cli-proxy-api")))
        self.state_dir = os.path.join(self.cliproxy, "astrapro.d")
        self.out_dir = os.path.join(self.cliproxy, "astrapro-out")
        self.usage_log = os.path.join(self.cliproxy, "astrapro-usage.jsonl")
        self.empty_cwd = os.path.join(self.state_dir, "empty-cwd")
        self.marker_path = os.path.join(self.state_dir, "launcher-owned")
        self.keep_path = os.path.join(self.state_dir, "keep-open")
        self.codex_home = os.path.abspath(win_path(e.get("ASTRAPRO_CODEX_HOME") or
                                                   os.path.join(home, ".codex-web")))
        self.main_homes = [os.path.join(home, ".codex")] + \
            ([e["CODEX_HOME"]] if e.get("CODEX_HOME") else [])
        launcher = e.get("ASTRAPRO_LAUNCHER") or os.path.join(
            e.get("LOCALAPPDATA") or os.path.join(home, "AppData", "Local"),
            "Programs", "Codex Web GPT", "Codex Web GPT.exe")
        self.launcher = os.path.abspath(win_path(launcher))
        cmd = e.get("ASTRAPRO_LAUNCHER_CMD") or ""
        if cmd:
            self.launcher_argv = shlex.split(cmd)
            if not self.launcher_argv:
                raise Exit(64, "usage_error", "ASTRAPRO_LAUNCHER_CMD is empty")
            image = os.path.basename(self.launcher_argv[0])
            if WINDOWS and not os.path.splitext(image)[1]:
                image += ".exe"
        else:
            self.launcher_argv = [self.launcher]
            image = os.path.basename(self.launcher)
        self.launcher_cmd = bool(cmd)
        self.launcher_image = (e.get("ASTRAPRO_LAUNCHER_IMAGE") or image).lower()
        self.supervisor = e.get("ASTRAPRO_SUPERVISOR_JSON") or os.path.join(
            home, ".codex-chatgpt-web", "runtime", "launcher-supervisor.json")
        self.bridge = not (self.dry and not cmd)

    def brief_gate(self, data):
        def refuse(why):
            log("step 2/8: brief gate REFUSED - %s. Nothing launched, nothing logged." % why)
            raise Exit(7, "brief_refused", why)

        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            refuse("brief is not valid UTF-8")
        if text.startswith("\ufeff"):
            text = text[1:]
        if not text.strip():
            refuse("brief is empty")
        if len(text) > MAX_BRIEF:
            refuse("brief is %d characters - over the 20,000 the secret scan covers" % len(text))
        try:
            import jev_privacy
            hit = jev_privacy.has_secret(text)
        except Exception as exc:  # fail closed
            refuse("secret scan failed (%s) - refusing" % type(exc).__name__)
        if hit is not False:
            refuse("brief contains secret-looking text")
        if not any(not m.group(1).startswith("<reason>") for m in ATTEST_RE.finditer(text)):
            refuse("brief has no 'brief-check: clean - <why>' attestation line")
        return len(text)

    def local_guards(self):
        def refuse(why):
            log("%s - refusing." % why)
            raise Exit(2, "preflight_refused", why)

        try:
            for d in (self.cliproxy, self.out_dir, self.state_dir, self.empty_cwd):
                os.makedirs(d, exist_ok=True)
        except OSError as exc:
            refuse("cannot create %s (%s)" % (self.state_dir, exc))
        if os.listdir(self.empty_cwd):
            refuse("job cwd not empty: %s" % self.empty_cwd)
        mine = canon(self.codex_home)
        for main in self.main_homes:
            if mine == canon(main):
                refuse("ASTRAPRO_CODEX_HOME is the main Codex home (%s)" % main)
        for f in AGENTS_FILES:
            if os.path.lexists(os.path.join(self.codex_home, f)):
                refuse("%s present in the codex home %s (codex would send it)" % (f, self.codex_home))
        git = shutil.which("git")
        if git:
            try:
                r = subprocess.run([git, "-C", self.empty_cwd, "rev-parse",
                                    "--is-inside-work-tree"], stdin=subprocess.DEVNULL,
                                   capture_output=True, timeout=30)
            except (OSError, subprocess.SubprocessError):
                r = None
            if r is not None and r.returncode == 0 and r.stdout.strip() == b"true":
                refuse("job cwd inside a git work tree")
        self.codex = None
        if not self.dry:
            self.codex = resolve_codex()
            if not self.codex:
                refuse("codex not found on PATH")

    def remaining(self):
        return self.budget.left()

    def health(self):
        """healthz, bounded by min(HEALTH_TIMEOUT, what is left of the whole budget)."""
        limit = min(HEALTH_TIMEOUT, self.budget.cleanup_left())
        if limit < 1.0:
            log("under 1 s of the budget left - skipping the healthz probe.")
            return None, None
        return health(self.health_url, limit)

    def note(self, msg):
        log(msg)
        self.notes.append(msg)

    def deadline_check(self, where):
        budget = self.budget.job_timeout()
        if budget < JOB_MIN:
            why = ("deadline: %.0fs of the total deadline left %s - the job needs %ds plus a "
                   "%ds reserve" % (max(0.0, self.budget.left()), where, JOB_MIN, JOB_RESERVE))
            log(why + " - launching nothing.")
            raise Exit(5, "deadline", why)
        return budget

    def pre_check(self):
        try:
            ok, reason = lanew_log.check(self.run, log_path=self.usage_log, ceiling=self.ceiling)
        except Exception as exc:
            raise Exit(3, "log_failure", "check failed: %r" % exc)
        log("step 4/8: check --run %s -> %s" % (self.run, reason))
        if not ok:
            raise Exit(1, "run_refused", reason)

    def slot_path(self, i):
        return os.path.join(self.state_dir, "slot-%d.lock" % i)

    def take_slot(self):
        wait = self.budget.start_wait(self.slot_wait)  # R3: never past the job's last start
        if wait < self.slot_wait:
            log("ASTRAPRO_SLOT_WAIT=%gs clamped to %.0fs by the total deadline."
                % (self.slot_wait, wait))
        slot_end = self.clock() + wait
        while True:
            for i in range(1, self.max_parallel + 1):
                with deferred():
                    lk = FileLock(self.slot_path(i))
                    if lk.try_acquire():
                        self.slot, self.slot_index = lk, i
                        log("step 5/8: slot-%d taken." % i)
                        return
            left = slot_end - self.clock()
            if left <= 0:
                if wait < self.slot_wait:
                    why = "deadline: no free slot before the total deadline"
                    log(why + " - launching nothing.")
                    raise Exit(5, "deadline", why)
                why = "no free slot within %.0fs (max %d)" % (self.slot_wait, self.max_parallel)
                log(why + " - launching nothing.")
                raise Exit(5, "no_slot", why)
            time.sleep(min(0.5, left))

    # ---- launcher lifecycle (start path) -----------------------------------
    def active_path(self, i):
        return os.path.join(self.state_dir, "active-%d.lock" % i)

    def enter_job(self):
        try:
            self.job_handle = join_kill_job()
        except OSError as exc:
            log("cannot create the kill-on-close job object (%s) - launching nothing." % exc)
            raise Exit(2, "preflight_refused", "job object unavailable: %s" % exc)

    def start_bridge(self):
        if not self.bridge:
            log("step 5/8: dry run without a launcher command - bridge skipped.")
            return
        self.state = FileLock(os.path.join(self.state_dir, "state.lock"))
        wait = self.budget.start_wait(self.state_wait)  # R3
        if not self.state.acquire(wait):
            if wait < self.state_wait:
                why = "deadline: the state lock was not free before the total deadline"
            else:
                why = "state lock busy - not obtainable within %.0fs" % self.state_wait
            log(why + " - launching nothing.")
            raise Exit(5, "deadline" if wait < self.state_wait else "no_slot", why)
        self.state_ever_held = True
        try:
            self.resolve_marker()
            code, data = self.health()
            if code == 200:
                self.use_running(data)
            else:
                self.recover_and_spawn()
            # R1: from here until the stop path this job is ACTIVE on the bridge
            # F5: the owner field is set BEFORE the take, so a signal deferred
            # inside try_acquire can never strand a held lock without an owner
            self.active = FileLock(self.active_path(self.slot_index))
            self.active.test_sigint = self.sigint_in_active
            if not self.active.acquire(2.0):
                path, self.active = self.active.path, None
                raise Exit(2, "preflight_refused", "active lock %s held by another process" % path)
        except BaseException:
            if self.spawned and not self.spawn_stop_failed:
                self.stop_own_spawn()
            raise
        finally:
            self.state.release()
        log("step 5/8: bridge healthz 200, mode browser-only.")

    def read_marker(self):
        exists, m = read_json(self.marker_path)
        return m if exists else None

    def resolve_marker(self):
        """Under the state lock: settle an intent marker, clear a stale one.

        An intent marker (no "pid") was left by a job that died between its
        launcher Popen and the marker publication (spawning happens only
        under this lock, so it is never in progress now): the launcher it
        started is a process with the launcher image whose parent is the
        spawner and that was created after the spawner. Adopt the earliest
        such process as the marker, or clear the intent when none survives.
        A full marker whose pid is gone or reused (creation time differs) is
        cleared; nothing is ever killed here.
        """
        exists, m = read_json(self.marker_path)
        if not exists:
            return
        if m is None:
            log("launcher marker unreadable - clearing it (nothing killed).")
            remove(self.marker_path)
            return
        if "pid" not in m:
            sp, sc = m.get("spawner_pid"), m.get("spawner_created")
            if not (_is_int(sp) and _is_int(sc)):
                log("launcher intent marker malformed - clearing it.")
                remove(self.marker_path)
                return
            reused_at = None
            if pid_alive(sp):
                now_created = pid_created(sp)
                if now_created is not None and now_created != sc:
                    reused_at = now_created  # spawner pid reused: only children from before
            cands = []
            for pid, (ppid, image) in process_snapshot().items():
                if ppid != sp or image != self.launcher_image:
                    continue
                c = pid_created(pid)
                if c is None or c < sc or (reused_at is not None and c >= reused_at):
                    continue
                cands.append((c, pid))
            if cands:
                c, pid = min(cands)
                write_json_atomic(self.marker_path, {"pid": pid, "created": c,
                                                     "spawner_pid": sp, "spawner_created": sc})
                log("adopted launcher pid %d, spawned by job pid %d before it could publish "
                    "its marker." % (pid, sp))
            else:
                log("cleared an intent marker of job pid %d - no launcher of it survives." % sp)
                remove(self.marker_path)
            return
        if not same_process(m.get("pid"), m.get("created")):
            if self.daemon_alive(m):
                log("launcher pid %s is gone but its supervisor-vouched daemon pid %d lives - "
                    "keeping the marker so the daemon gets stopped." % (m.get("pid"),
                                                                        m["daemon_pid"]))
                return
            log("cleared a stale launcher marker (pid %s is gone or reused; nothing killed)."
                % m.get("pid"))
            remove(self.marker_path)

    def daemon_alive(self, m):
        """F3: is m's recorded daemon (pid + creation time + image) still that process?"""
        dp = m.get("daemon_pid")
        return (_is_int(dp) and same_process(dp, m.get("daemon_created"))
                and process_snapshot().get(dp, (0, ""))[1] == m.get("daemon_image"))

    def serves(self, m, data):
        """How the bridge answering healthz is provably marker m's launcher (G5).

        "tree" when healthz's pid is m's process or a live descendant of it,
        "supervisor" when launcher-supervisor.json (status ready) names m's pid
        as ownerPid and healthz's pid as daemonPid, "daemon" when healthz's pid
        is the daemon recorded in m and still that process, else None.
        """
        hp = data.get("pid")
        if not m or not _is_int(hp):
            return None
        if same_process(m.get("pid"), m.get("created")):
            if in_tree(m["pid"], m["created"], hp):
                return "tree"
            exists, sup = read_json(self.supervisor)
            if sup and sup.get("status") == "ready" and sup.get("ownerPid") == m["pid"] \
                    and sup.get("daemonPid") == hp:
                return "supervisor"
        if hp == m.get("daemon_pid") and self.daemon_alive(m):
            return "daemon"  # F3: the daemon recorded at verification, still that process
        return None

    def record_daemon(self, hp):
        """R5: the supervisor-vouched daemon is outside the launcher's tree; keep its
        identity in the marker so the stop can identity-check and kill it too."""
        m = self.read_marker()
        created = pid_created(hp)
        image = process_snapshot().get(hp, (0, ""))[1]
        if not m or created is None or not image:
            return
        fields = {"daemon_pid": hp, "daemon_created": created, "daemon_image": image}
        m.update(fields)
        with deferred():
            write_json_atomic(self.marker_path, m)
            if self.spawned and self.spawned.get("pid") == m.get("pid"):
                self.spawned.update(fields)  # F4: an interrupted spawn stops the daemon too
        log("ownership verified by the supervisor file; daemon pid %d (%s) recorded." % (hp, image))

    def use_running(self, data):
        m = self.read_marker()
        how = self.serves(m, data) if m else None
        if how:
            log("healthz up; the launcher astrapro started (pid %d) serves it." % m["pid"])
            if how == "supervisor":
                self.record_daemon(data["pid"])
        elif m:
            log("healthz up but not verifiably from the launcher astrapro started (pid %s) - "
                "treating the bridge as foreign; it will not be stopped." % m.get("pid"))
            remove(self.marker_path)
            remove(self.keep_path)
        else:
            log("healthz up; launcher not started by astrapro - it will be left running.")
        mode = data.get("mode")
        if mode != "browser-only":
            self.refuse_bridge("bridge mode is %r, not browser-only" % mode, record=True)
        self.write_keep_open()

    def recover_and_spawn(self):
        # R1/G4: a job already ACTIVE on the bridge (start path done, not yet in its
        # stop) means never stop, respawn or clear keep-open - marker or not. Jobs
        # that only hold a slot while waiting for the state lock have not used the
        # bridge yet, so a cold start with parallel jobs still spawns once.
        if self.other_active_held():
            self.refuse_bridge("bridge unhealthy while other jobs hold it", record=False)
        m = self.read_marker()
        if m:  # resolve_marker kept it: our launcher (or its daemon) is alive, not serving
            log("healthz is down but the launcher astrapro started (pid %d) or its daemon is "
                "alive - stopping it before a fresh start." % m["pid"])
            if not self.stop_marked(m):
                self.refuse_bridge("could not stop the unhealthy launcher pid %d" % m["pid"],
                                   record=False)
            remove(self.marker_path)
        remove(self.keep_path)  # a new launcher lifetime
        if not self.launcher_cmd and not os.path.isfile(self.launcher):
            self.refuse_bridge("launcher not found: %s" % self.launcher, record=False)
        self.spawn()
        t = self.clock()
        wait = self.budget.start_wait(self.launch_deadline)  # R3
        end = t + wait
        while True:
            code, data = self.health()
            if code == 200:
                break
            left = end - self.clock()
            if left <= 0:
                self.stop_own_spawn()
                if wait < self.launch_deadline:
                    why = ("deadline: the launcher was not healthy before the total deadline "
                           "(%.0fs of its %.0fs launch wait)" % (wait, self.launch_deadline))
                    log("step 5/8: %s - launching nothing." % why)
                    raise Exit(5, "deadline", why)
                self.refuse_bridge("launcher did not answer healthz within %.0fs"
                                   % self.launch_deadline, record=True)
            time.sleep(min(0.5, left))
        if data.get("mode") != "browser-only":
            self.stop_own_spawn()
            self.refuse_bridge("bridge mode is %r, not browser-only" % data.get("mode"),
                               record=True)
        how = self.serves(self.spawned, data)
        if not how:
            pid = self.spawned["pid"]
            self.stop_own_spawn()
            self.refuse_bridge("healthz answers, but its pid %s is not verifiably from the "
                               "launcher this job spawned (pid %d)" % (data.get("pid"), pid),
                               record=False)
        if how == "supervisor":
            self.record_daemon(data["pid"])
            if self.sigint_after_daemon:  # test hook: an interrupt right after the record
                signal.raise_signal(signal.SIGINT)
        log("launcher up after %.1fs (owned: pid %d serves healthz)."
            % (self.clock() - t, self.spawned["pid"]))
        self.spawned = None
        self.write_keep_open()

    def spawn(self):
        write_json_atomic(self.marker_path, {"spawner_pid": self.my_pid,
                                             "spawner_created": self.my_created,
                                             "spawned_at": time.time()})
        env = dict(self.env)
        env.pop("ELECTRON_RUN_AS_NODE", None)
        env["CODEX_HOME"] = self.codex_home
        kw = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                  stderr=subprocess.DEVNULL, close_fds=True, env=env)
        if WINDOWS:
            kw["creationflags"] = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        else:  # pragma: no cover - POSIX
            kw["start_new_session"] = True
        if self.job_handle is not None:
            raise RuntimeError("the launcher is never spawned from inside the job object")
        log("launcher down - starting %s (CODEX_HOME=%s)." % (self.launcher_argv[0], self.codex_home))
        with deferred():
            try:
                self.launcher_proc = subprocess.Popen(self.launcher_argv, **kw)
            except OSError as exc:
                remove(self.marker_path)
                self.refuse_bridge("launcher failed to start: %s" % exc, record=False)
            self.spawned = {"pid": self.launcher_proc.pid,
                            "created": pid_created(self.launcher_proc.pid)}
        if self.spawn_pause:  # test-only: the window between Popen and publication
            time.sleep(self.spawn_pause)
        with deferred():
            write_json_atomic(self.marker_path, {
                "pid": self.spawned["pid"], "created": self.spawned["created"],
                "spawner_pid": self.my_pid, "spawner_created": self.my_created})

    def stop_own_spawn(self):
        """Stop the launcher this job spawned and could not use. True when it is gone.

        R4: a failed stop keeps the spawn reference and (re)publishes the full
        marker, so cleanup does not lose it and a later run can still verify
        and stop that launcher; the failure is reported (stderr + JSON reason).
        """
        sp = self.spawned
        if not sp:
            return True
        log("stopping the launcher this job spawned and could not use (pid %d)." % sp["pid"])
        if self.stop_marked(sp):
            self.spawned = None
            m = self.read_marker()
            if m is not None and (m.get("pid") == sp["pid"] or
                                  ("pid" not in m and m.get("spawner_pid") == self.my_pid)):
                remove(self.marker_path)
            return True
        self.spawn_stop_failed = True
        marker = dict(sp)  # keeps any daemon_* fields (F4)
        marker.update(spawner_pid=self.my_pid, spawner_created=self.my_created)
        write_json_atomic(self.marker_path, marker)
        return False

    def stop_marked(self, m):
        """Kill marker m's launcher tree (and its supervisor-vouched daemon, R5)
        after identity checks. True when everything it targeted is gone."""
        pid, created = m.get("pid"), m.get("created")
        targets = []
        with pinned(pid):
            if same_process(pid, created):
                kill_tree(pid, self.budget.cleanup_wait(KILL_TIMEOUT))
                targets.append((pid, created))
            else:
                log("launcher pid %s is gone or not the process astrapro started - killing "
                    "nothing." % pid)
        dp, dc, di = m.get("daemon_pid"), m.get("daemon_created"), m.get("daemon_image")
        if _is_int(dp):
            with pinned(dp):
                if same_process(dp, dc) and process_snapshot().get(dp, (0, ""))[1] == di:
                    log("stopping the daemon the supervisor vouched for (pid %d, %s)." % (dp, di))
                    if _TEST["fail_daemon_kill"]:
                        log("test hook: the daemon kill is skipped (a simulated failed kill).")
                    else:
                        kill_tree(dp, self.budget.cleanup_wait(KILL_TIMEOUT))
                    targets.append((dp, dc))
        end = self.clock() + self.budget.cleanup_wait(self.kill_confirm)  # R3
        while True:
            left = [t for t in targets if same_process(*t)]
            if not left:
                return True
            if self.clock() >= end:
                break
            time.sleep(0.2)
        self.note("stopping launcher pid %s failed - %s still running; its marker is kept "
                  "for the next run" % (pid, ", ".join(str(t[0]) for t in left)))
        return False

    def refuse_bridge(self, why, record):
        log("step 5/8: bridge preflight REFUSED - %s. Nothing launched." % why)
        if record:
            try:
                e = lanew_log.record_preflight_failed(self.run, self.name, self.model,
                                                      log_path=self.usage_log)
                if not e.get("_append_ok"):
                    log("failed to write the preflight-failure record.")
            except Exception as exc:
                log("failed to write the preflight-failure record (%r)." % exc)
        raise Exit(2, "preflight_refused", why)

    def write_keep_open(self):
        if self.keep_open:
            with open(self.keep_path, "w", encoding="utf-8") as f:
                f.write(str(self.my_pid))

    def other_slots_held(self):
        for i in range(1, HARD_MAX + 1):
            if i == self.slot_index and self.slot is not None and self.slot.held:
                continue
            probe = FileLock(self.slot_path(i))
            if probe.try_acquire():
                probe.release()
            else:
                return True
        return False

    def other_active_held(self):
        """R1: is another job past its start path (active on the bridge)?"""
        for i in range(1, HARD_MAX + 1):
            if i == self.slot_index:
                continue
            probe = FileLock(self.active_path(i))
            if probe.try_acquire():
                probe.release()
            else:
                return True
        return False

    # ---- admit, job, record end -----------------------------------------------
    def admit(self):
        pend_out = fwd(os.path.join(self.out_dir, "pending-%s.out" % self.name))
        pend_rep = fwd(os.path.join(self.out_dir, "pending-%s.report.md" % self.name))
        with deferred():
            try:
                status, reason, entry = lanew_log.admit(
                    self.run, self.name, self.model, pend_out, pend_rep, owner_pid=self.my_pid,
                    log_path=self.usage_log, ceiling=self.ceiling, owner_created=self.my_created)
            except Exception as exc:
                status, reason, entry = "log_error", repr(exc), None
            if status == "admitted":
                self.job_id, self.ts_start = entry["job_id"], entry["ts_start"]
        if status == "refused":
            log("step 6/8: admit refused - %s" % reason)
            raise Exit(1, "run_refused", reason)
        if status != "admitted":
            log("step 6/8: admit failed - %s" % reason)
            raise Exit(3, "log_failure", "record start failed: %s" % reason)
        self.out = fwd(os.path.join(self.out_dir, "%s-%s.out" % (self.job_id, self.name)))
        self.report = fwd(os.path.join(self.out_dir, "%s-%s.report.md" % (self.job_id, self.name)))
        for p in (self.out, self.report):
            try:
                os.close(os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
            except FileExistsError:
                raise Exit(3, "log_failure", "output path exists: %s" % p)
        log("step 6/8: admitted job_id=%s out=%s report=%s" % (self.job_id, self.out, self.report))

    def launch_job(self, data):
        fd, self.brief_tmp = tempfile.mkstemp(prefix="astrapro-brief-", suffix=".md")
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        env = dict(self.env)
        env["CODEX_DIRECT"] = "1"
        env["CODEX_HOME"] = self.codex_home
        if self.dry:
            argv = [sys.executable, "-c", DRY_JOB, str(self.dry_sleep), self.report]
            if self.job_grandchild:
                argv.append(self.job_grandchild)
            log("step 7/8: dry run - fake job (%gs), no codex exec." % self.dry_sleep)
        else:
            argv = [self.codex, "exec", "--skip-git-repo-check", "-s", "read-only", "-m",
                    self.model, "--output-last-message", os.path.normpath(self.report)]
            log("step 7/8: %s exec -m %s -s read-only (cwd %s, CODEX_HOME=%s)."
                % (self.codex, self.model, self.empty_cwd, self.codex_home))
        launched_after = filetime_now()
        with open(self.brief_tmp, "rb") as fin, open(self.out, "wb") as fout:
            with deferred():
                self.job_proc = start_job_child(argv, pause=self.child_pause, cwd=self.empty_cwd,
                                                stdin=fin, stdout=fout, env=env)
                # its creation time (or a lower bound if it is already gone) - F2
                self.job_created = pid_created(self.job_proc.pid) or launched_after

    def wait_job(self, budget):
        end = time.monotonic() + budget
        while True:
            try:
                rc = self.job_proc.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                pass
            else:
                self.reap_job_descendants()
                return rc
            if time.monotonic() >= end:
                log("the job hit its %.0fs timeout - stopping its process tree." % budget)
                self.kill_job()
                return 124  # what `timeout` returned in the bash wrapper; classify -> timeout

    def kill_job(self):
        p = self.job_proc
        if p is None:
            return
        if p.poll() is None:
            kill_tree(p.pid, self.budget.cleanup_wait(KILL_TIMEOUT))
        wait = self.budget.cleanup_wait(KILL_CONFIRM)
        try:
            if wait > 0:
                p.wait(timeout=wait)
        except subprocess.TimeoutExpired:
            pass
        if p.poll() is None:
            log("WARNING: job pid %d still running after its tree kill (the job object ends "
                "it when this wrapper exits)." % p.pid)
        else:
            self.reap_job_descendants()

    def reap_job_descendants(self):
        """F2: once the job child is gone, stop whatever it left running (before
        record end), so nothing of the job lives on through cleanup's waits.

        Snapshot walk from the child's pid (descendants()), each one pinned and
        identity-checked (pid + creation time) right before its tree kill; this
        wrapper and the launcher (marker pid, daemon, own spawn) are never touched.
        """
        p = self.job_proc
        if p is None or p.poll() is None:
            return
        never = {self.my_pid}
        m = self.read_marker() or {}
        for key in ("pid", "daemon_pid"):
            if _is_int(m.get(key)):
                never.add(m[key])
        if self.spawned:
            never.add(self.spawned.get("pid"))
        found = [d for d in descendants(p.pid, self.job_created) if d[0] not in never]
        stopped = []
        for pid, created in found:
            with pinned(pid):
                if same_process(pid, created):
                    kill_tree(pid, self.budget.cleanup_wait(KILL_TIMEOUT))
                    stopped.append(pid)
        if stopped:
            log("stopped %d process(es) the job left running: %s"
                % (len(stopped), ", ".join(str(s) for s in stopped)))

    def record_end(self, code):
        self.job_ended = True
        return lanew_log.record_end(self.job_id, self.run, self.name, self.model, self.ts_start,
                                    code, self.out, self.report, log_path=self.usage_log)

    def end_job(self, code):
        with deferred():
            entry = self.record_end(code)
        status = entry["status"]
        log("step 8/8: codex_exit=%d status=%s report=%s" % (code, status, self.report))
        if not entry.get("_append_ok"):
            raise Exit(3, "log_failure", "record end failed (status %s) - usage unknown" % status)
        if status == "ok":
            raise Exit(0, "ok", "job ended ok")
        raise Exit(6, status, "job ran and did not end ok (codex_exit=%d)" % code)

    def on_interrupt(self, signame):
        if self.job_id and not self.job_ended:
            log("interrupted (%s) - stopping the job and recording its end." % signame)
            self.kill_job()
            try:
                status = self.record_end(130)["status"]
            except Exception as exc:
                log("record end failed (%r) - usage unknown." % exc)
                status = "interrupted"
            return Exit(130, status, "interrupted by %s after launch" % signame)
        return Exit(130, "interrupted", "interrupted by %s before launch" % signame)

    def on_error(self, exc):
        log("internal error: %r" % exc)
        traceback.print_exc(file=sys.stderr)
        if self.job_id and not self.job_ended:
            self.kill_job()
            try:
                status = self.record_end(1)["status"]
            except Exception:
                status = "internal_error"
            return Exit(6, status, "internal error after admit: %r" % exc)
        return Exit(2, "internal_error", "internal error before launch: %r" % exc)

    # ---- stop path (every exit) -------------------------------------------------
    def _drop_slot(self):
        if self.active is not None:
            self.active.release()
            self.active = None
        self.slot.release()
        log("slot-%d released." % self.slot_index)

    def release(self):
        if self.brief_tmp:
            try:
                os.remove(self.brief_tmp)
            except OSError:
                pass
        if self.slot is None or not self.slot.held:
            if self.state is not None and self.state.held:
                self.state.release()
            return
        # R6: a start path that never held the state lock touched no launcher state
        if not self.bridge or (not self.state_ever_held and not self.spawned):
            self._drop_slot()
            return
        if self.state is None:
            self.state = FileLock(os.path.join(self.state_dir, "state.lock"))
        if not self.state.held:
            wait = self.budget.cleanup_wait(self.state_wait, reserve=STOP_RESERVE)  # R3
            if not self.state.acquire(wait):
                self._drop_slot()
                log("could not take the state lock within %.0fs - launcher left as it is."
                    % wait)
                return
        try:
            if self.spawned and self.spawn_stop_failed:
                log("leaving launcher pid %d: its stop failed; the marker is kept for the next "
                    "run." % self.spawned["pid"])
            elif self.spawned:
                self.stop_own_spawn()
            else:
                self.resolve_marker()
                m = self.read_marker()
                if m is None:
                    pass
                elif self.other_slots_held():
                    log("another job holds a slot - leaving the launcher running.")
                elif os.path.exists(self.keep_path):
                    log("last job out; keep-open marker set - leaving the launcher running.")
                else:
                    log("last job out - stopping the launcher astrapro started (pid %d and its "
                        "tree)." % m["pid"])
                    if self.stop_marked(m):
                        remove(self.marker_path)
                        if self.budget.cleanup_left() > 4:
                            code, _ = self.health()
                            if code == 200:
                                log("healthz still answers at %s - that bridge is not ours."
                                    % self.health_url)
            if self.stop_pause:
                time.sleep(self.stop_pause)
        except Exception as exc:
            log("stop path error: %r" % exc)
        finally:
            self._drop_slot()            # G1: own slot BEFORE the state lock
            self.state.release()

    def emit(self, r):
        n = lambda v: v or None  # noqa: E731
        line = json.dumps({"tool": "astrapro", "exit": r.code, "status": r.status,
                           "reason": r.reason, "run": n(self.run), "name": n(self.name),
                           "model": n(self.model), "job_id": n(self.job_id),
                           "report": n(self.report), "out": n(self.out)})
        try:
            print(line, flush=True)
        except (OSError, ValueError):
            pass


def main(argv=None, env=None):
    install_signals()
    w = Wrapper(sys.argv[1:] if argv is None else argv, os.environ if env is None else env)
    result = None
    try:
        try:
            w.main()
            result = Exit(3, "internal_error", "wrapper ended without a result")
        except Exit as e:
            result = e
    except Interrupted as e:
        disarm()
        if result is None:
            result = w.on_interrupt(e.signame)
    except Exception as e:
        disarm()
        result = w.on_error(e)
    finally:
        disarm()
        try:
            w.release()
        except BaseException as exc:
            log("cleanup error: %r" % exc)
    if w.notes:
        result.reason = "%s (%s)" % (result.reason, "; ".join(w.notes))
    w.emit(result)
    return result.code


if __name__ == "__main__":
    sys.exit(main())
