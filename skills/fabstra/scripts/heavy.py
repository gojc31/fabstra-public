"""Run a heavy check (full build, typecheck, full test suite) in one of a few
shared slots, so cooperating sessions across client projects take turns.

Usage: python heavy.py [--slots N] [--dir PATH] -- <command...>
       python heavy.py --tree-id    (print the working-tree fingerprint only)

One heavy command per call. A gate of several commands (build && test) either
calls heavy.py once per command or puts them in a script file run as one
command (`heavy.py -- python gate.py`, `heavy.py -- sh gate.sh`). The command
runs as argv, never through a shell, so `&`, `|` and `%VAR%` in an argument
stay literal. A Windows .cmd/.bat shim (npm, pnpm, npx) runs only when no
argument holds a cmd.exe metacharacter; otherwise call the tool's .exe or a
script file.

Before and after the command it prints `tree=<id>`: a fingerprint of HEAD,
the staged diff, the unstaged diff and untracked files, repo-wide, leaving out
`.fabstra/` (the logbook) and ignored files. A logged result names exactly
what it tested only when both ids match; a changed id prints a warning.

Slots (default 2, env HEAVY_SLOTS) and the slot folder (default
~/.fabstra/heavy-slots, env HEAVY_DIR) must be the same for every session.
A slot is an OS file lock, released by the OS when its holder dies, so no
slot is ever reclaimed by guessing. Two jobs in the same worktree also take
turns (a per-worktree lock), since they share generated files. When the
wrapper dies its command dies with it (a Windows job object; on POSIX the
command inherits the lock, so the slot stays held while it runs). The
command's exit code is passed through. Standard library only.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import time

WAIT_SECONDS = 30
EXCLUDE = ":(exclude).fabstra"
CMD_META = set('&|<>^%!"()\r\n')


def try_lock(path):
    """Open path and take a non-blocking exclusive lock. Returns the fd, or
    None when another process holds it."""
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return None
    return fd


def wait_lock(paths, what):
    """Lock the first free path in paths, waiting while all are held."""
    while True:
        for i, path in enumerate(paths, 1):
            fd = try_lock(path)
            if fd is not None:
                return i, fd
        print(f"heavy.py: {what} busy, waiting ({time.strftime('%H:%M:%S')})",
              file=sys.stderr, flush=True)
        time.sleep(WAIT_SECONDS)


def kill_children_on_exit():
    """Windows: put this process in a job that kills every member when the
    last handle closes, i.e. when this wrapper exits or is killed. Children
    join the job at creation, so none can escape before assignment."""
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    class BASIC(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong),
                    ("PerJobUserTimeLimit", ctypes.c_longlong),
                    ("LimitFlags", wintypes.DWORD),
                    ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t),
                    ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t),
                    ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD)]

    class IO(ctypes.Structure):
        _fields_ = [(n, ctypes.c_ulonglong) for n in (
            "Read", "Write", "Other", "ReadBytes", "WriteBytes", "OtherBytes")]

    class EXTENDED(ctypes.Structure):
        _fields_ = [("Basic", BASIC), ("Io", IO),
                    ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t)]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateJobObjectW.restype = wintypes.HANDLE
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    job = k32.CreateJobObjectW(None, None)
    info = EXTENDED()
    info.Basic.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    ok = job and k32.SetInformationJobObject(
        wintypes.HANDLE(job), 9, ctypes.byref(info), ctypes.sizeof(info))
    ok = ok and k32.AssignProcessToJobObject(
        wintypes.HANDLE(job), wintypes.HANDLE(k32.GetCurrentProcess()))
    if not ok:
        print("heavy.py: warning: no job object; the command may outlive a killed wrapper",
              file=sys.stderr)
        return None
    return job  # never closed: the OS closes it when this process ends


def resolve(command):
    """argv to run without a shell. Returns (argv, error)."""
    exe = shutil.which(command[0])
    if not exe:
        return None, f"command not found: {command[0]!r}"
    if os.name == "nt" and exe.lower().endswith((".cmd", ".bat")):
        bad = [a for a in command[1:] if CMD_META & set(a)]
        if bad:
            return None, (f"{os.path.basename(exe)} is a cmd.exe script and argument {bad[0]!r} "
                          "holds a cmd metacharacter; run the tool's .exe or a script file instead")
    return [exe, *command[1:]], None


def git(*a, cwd=None):
    return subprocess.run(["git", *a], capture_output=True, cwd=cwd)


def tree_id():
    """Fingerprint of the code under test: HEAD, staged diff, unstaged diff
    and untracked files, repo-wide, without .fabstra/ and ignored files.
    None outside a git repo."""
    top = git("rev-parse", "--show-toplevel")
    if top.returncode != 0:
        return None
    top = top.stdout.decode("utf-8", "surrogateescape").strip()
    head = git("rev-parse", "HEAD", cwd=top)
    h = hashlib.sha256(b"head\0" + (head.stdout if head.returncode == 0 else b"unborn"))
    diff = ("--no-ext-diff", "--no-textconv", "--no-color", "--binary")
    for label, extra in ((b"staged", ("--cached",)), (b"unstaged", ())):
        out = git("diff", *extra, *diff, "--", ".", EXCLUDE, cwd=top)
        h.update(b"\0" + label + b"\0" + out.stdout)
    others = git("ls-files", "--others", "--exclude-standard", "-z", "--", ".", EXCLUDE,
                 cwd=top).stdout.split(b"\0")
    h.update(b"\0untracked\0")
    for path in sorted(p for p in others if p):
        h.update(path + b"\0")
        try:
            with open(os.path.join(top, path.decode("utf-8", "surrogateescape")), "rb") as f:
                h.update(f.read())
        except OSError:
            h.update(b"<unreadable>")
    return h.hexdigest()[:16]


def worktree_key():
    top = git("rev-parse", "--show-toplevel")
    where = top.stdout.strip() if top.returncode == 0 else os.getcwd().encode()
    return hashlib.sha256(os.path.normcase(where.decode("utf-8", "surrogateescape")).encode()).hexdigest()[:12]


def main(argv):
    slots = int(os.environ.get("HEAVY_SLOTS", "2"))
    base = os.environ.get("HEAVY_DIR") or os.path.join(os.path.expanduser("~"), ".fabstra", "heavy-slots")
    args = list(argv)
    if args == ["--tree-id"]:
        tid = tree_id()
        print(tid or "none (not git)")
        return 0 if tid else 1
    while args and args[0] != "--":
        flag = args.pop(0)
        if flag == "--slots" and args:
            slots = int(args.pop(0))
        elif flag == "--dir" and args:
            base = args.pop(0)
        else:
            print(f"heavy.py: unknown argument {flag!r}; usage: heavy.py [--slots N] [--dir PATH] -- <command...>", file=sys.stderr)
            return 2
    command = args[1:]
    if not command or slots < 1:
        print("heavy.py: no command given (put it after --), or --slots below 1", file=sys.stderr)
        return 2
    run, err = resolve(command)
    if err:
        print(f"heavy.py: {err}", file=sys.stderr)
        return 2
    os.makedirs(base, exist_ok=True)
    _, wt_fd = wait_lock([os.path.join(base, f"worktree-{worktree_key()}.lock")], "this worktree's heavy lock")
    num, slot_fd = wait_lock([os.path.join(base, f"slot-{i}.lock") for i in range(1, slots + 1)],
                             f"all {slots} slots in {base}")
    kill_children_on_exit()
    before = tree_id()
    print(f"heavy.py: slot {num}: tree={before or 'none (not git)'}: {' '.join(command)}", file=sys.stderr, flush=True)
    try:
        kw = {} if os.name == "nt" else {"pass_fds": (wt_fd, slot_fd)}
        code = subprocess.call(run, **kw)
    finally:
        os.close(slot_fd)
        os.close(wt_fd)
    after = tree_id()
    note = "" if after == before else "  WARNING: the tree changed during the run; this result is evidence for neither id"
    print(f"heavy.py: exit={code} tree-after={after or 'none (not git)'}{note}", file=sys.stderr, flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
