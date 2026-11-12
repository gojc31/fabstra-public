#!/usr/bin/env python3
"""Set, clear and read Claude Code's advisor setting (`advisorModel`).

Usage:
  advisor-state.py status [--project <dir>]
  advisor-state.py on <fable|opus>
  advisor-state.py off

`on` / `off` write the USER settings file only (~/.claude/settings.json). They
never re-serialise it: the file's bytes are read once, the top-level
`advisorModel` member is located with a small nesting- and escape-aware
tokenizer, and only that member's value is replaced, one member is inserted
before the top-level closing brace, or that member and its adjacent comma are
removed. Every other byte stays identical (a leading UTF-8 BOM is dropped).

Write cycle: read once -> strict parse (no NaN/Infinity, no duplicate keys at
any depth, object top level, one top-level advisorModel) -> compute the new
bytes and parse them strictly too (numbers compared as exact text) -> back up
exactly the bytes that were parsed -> write a same-folder temp file -> re-read
the settings file and, only if it still equals the parsed bytes, os.replace.
If it changed, the cycle is retried (3 retries, short wait), then exit 6.
After the replace the file is re-read (a read error is retried 3 times, short
wait). Exactly the new bytes -> exit 0. Anything else - different bytes, valid
or not, or still unreadable after the retries - is never rewritten: nothing is
restored, nothing more is written, and the script exits 5 naming the settings
file and the backup ("could not confirm the write; nothing restored; run
`status` and compare with the backup"), printing
`advisorModel now: <value|unset|invalid> (intended <value|unset>)` when the
read-back succeeded. os.replace of a fully written, fsynced temp file cannot
leave a partial file, so nothing is ever rolled back automatically.
Remaining race window (narrowed, not closed):
  - re-read -> replace: another program can save in the instant between the
    final compare-and-swap re-read and os.replace; its save is then overwritten
    by ours (it stays in neither file).
  Nothing after the replace is ever rewritten, so a save landing after it is
  always kept.

Exit codes: 0 ok, 1 backup could not be written (nothing written), 2 bad model,
3 fable needs CLI >= 2.1.321, 4 settings file unreadable / not strict JSON /
not an object (nothing written), 5 the write could not be confirmed (the file
is left as it is, nothing restored - run `status` and compare with the backup),
6 settings changed by another writer before our replace (nothing written).

Test-only overrides (environment): ADVISOR_STATE_USER_SETTINGS,
ADVISOR_STATE_BACKUP_DIR, ADVISOR_STATE_CLI_VERSION. The only external command
ever run is `claude --version`, and only when ADVISOR_STATE_CLI_VERSION is absent.
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

KEY = "advisorModel"
DISABLE_KEY = "CLAUDE_CODE_DISABLE_ADVISOR_TOOL"
MODELS = ("fable", "opus")
FABLE_MIN = (2, 1, 321)


class SettingsError(Exception):
    pass


def user_settings_path():
    return os.environ.get("ADVISOR_STATE_USER_SETTINGS") or os.path.join(
        os.path.expanduser("~"), ".claude", "settings.json"
    )


def backup_dir():
    return os.environ.get("ADVISOR_STATE_BACKUP_DIR") or os.path.join(
        os.path.expanduser("~"), ".claude", "backups"
    )


# ---------- CLI version ----------

def raw_cli_version():
    if "ADVISOR_STATE_CLI_VERSION" in os.environ:
        return os.environ["ADVISOR_STATE_CLI_VERSION"]
    exe = shutil.which("claude")
    if not exe:
        return ""
    try:
        proc = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=30)
        return proc.stdout or ""
    except (OSError, subprocess.SubprocessError):
        return ""


def parse_version(text):
    m = re.search(r"(?<![\d.])(\d+)\.(\d+)\.(\d+)(?![\d])", text or "")
    return tuple(int(g) for g in m.groups()) if m else None


def fable_ok(version):
    if version is None:
        return "unknown"
    return "yes" if version >= FABLE_MIN else "no"


# ---------- reading ----------

def read_settings(path):
    """Return (raw_text, obj). Raises FileNotFoundError or SettingsError."""
    with open(path, "rb") as f:
        raw = f.read()
    try:
        text = raw.decode("utf-8-sig")
        obj = json.loads(text)
    except (UnicodeDecodeError, ValueError) as e:
        raise SettingsError(f"cannot parse {path}: {e}")
    if not isinstance(obj, dict):
        raise SettingsError(f"{path}: top level is not a JSON object")
    return text, obj


def is_true(value):
    return isinstance(value, (str, int, bool)) and str(value).strip().lower() in ("1", "true")


def fmt(value):
    if value is None:
        return "unset"
    return value if isinstance(value, str) else json.dumps(value)


# ---------- status ----------

def cmd_status(project):
    files = [("user", user_settings_path())]
    if project:
        files.append(("project", os.path.join(project, ".claude", "settings.json")))
        files.append(("local", os.path.join(project, ".claude", "settings.local.json")))

    models = {}
    disable_settings = None
    for scope, path in files:
        try:
            _, obj = read_settings(path)
        except FileNotFoundError:
            models[scope] = "unset"
            continue
        except (SettingsError, OSError):
            models[scope] = "invalid"
            continue
        models[scope] = fmt(obj.get(KEY))
        env_block = obj.get("env")
        if disable_settings is None and isinstance(env_block, dict) and is_true(env_block.get(DISABLE_KEY)):
            disable_settings = fmt(env_block.get(DISABLE_KEY))

    disable_env = os.environ.get(DISABLE_KEY)
    version = parse_version(raw_cli_version())

    # Claude Code precedence: local > project > user.
    applied = None
    for scope in ("local", "project", "user"):
        val = models.get(scope)
        if val not in (None, "unset", "invalid"):
            applied = val
            break
    disabled = is_true(disable_env) or disable_settings is not None
    effective = applied if applied and not disabled else "off"

    lines = [f"user_advisorModel={models['user']}"]
    if project:
        lines.append(f"project_advisorModel={models['project']}")
        lines.append(f"local_advisorModel={models['local']}")
    lines += [
        f"disable_env={disable_env if disable_env is not None else 'unset'}",
        f"disable_settings={disable_settings if disable_settings is not None else 'unset'}",
        f"cli_version={'.'.join(map(str, version)) if version else 'unknown'}",
        f"fable_ok={fable_ok(version)}",
        f"effective={effective}",
    ]
    print("\n".join(lines))
    return 0


# ---------- writing ----------

BOM = b"\xef\xbb\xbf"
SWAP_RETRIES = 3      # re-tries of the whole cycle when the file changed under us
SWAP_WAIT = 0.2       # seconds, multiplied by the attempt number
READ_BACK_RETRIES = 3  # re-tries of the post-replace verification read
READ_BACK_WAIT = 0.2
WS = " \t\r\n"        # JSON whitespace


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def reread_for_swap(path):
    """The compare-and-swap re-read just before os.replace (a test seam)."""
    return read_bytes(path)


def read_back(path):
    """The post-replace verification read (a test seam)."""
    return read_bytes(path)


def replace_file(src, dst):
    os.replace(src, dst)


# --- strict parsing ---

def _no_dup_pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise SettingsError(f"duplicate key {k!r}")
        out[k] = v
    return out


def _bad_constant(name):
    raise SettingsError(f"non-standard JSON constant {name}")


def _num(text):
    return ("num", text)  # exact source text; arrays parse to lists, so no clash


def strict_parse(text):
    """Parse with exact numbers, no NaN/Infinity and no duplicate keys at any depth."""
    try:
        return json.loads(
            text,
            object_pairs_hook=_no_dup_pairs,
            parse_float=_num,
            parse_int=_num,
            parse_constant=_bad_constant,
        )
    except ValueError as e:
        raise SettingsError(str(e))


# --- tokenizer for the top-level object ---

def _skip_ws(text, i):
    while i < len(text) and text[i] in WS:
        i += 1
    return i


def _end_of_string(text, i):
    """text[i] is '"'; return the index just past the closing quote."""
    i += 1
    while True:
        c = text[i]
        if c == "\\":
            i += 2
        elif c == '"':
            return i + 1
        else:
            i += 1


def _end_of_value(text, i):
    c = text[i]
    if c == '"':
        return _end_of_string(text, i)
    if c in "{[":
        depth = 0
        while True:
            c = text[i]
            if c == '"':
                i = _end_of_string(text, i)
                continue
            if c in "{[":
                depth += 1
            elif c in "}]":
                depth -= 1
                if depth == 0:
                    return i + 1
            i += 1
    while i < len(text) and text[i] not in WS + ",}]":
        i += 1
    return i


def top_level_members(text):
    """Return (open_idx, close_idx, members) for already-validated JSON text.

    Each member is a dict: key, key_start, key_end, value_start, value_end.
    Only depth-1 members are listed; nested keys are skipped inside values.
    """
    try:
        i = _skip_ws(text, 0)
        if text[i] != "{":
            raise SettingsError("top level is not a JSON object")
        open_idx = i
        members = []
        i = _skip_ws(text, i + 1)
        if text[i] == "}":
            return open_idx, i, members
        while True:
            key_start = i
            key_end = _end_of_string(text, i)
            key = json.loads(text[key_start:key_end])
            i = _skip_ws(text, key_end)
            if text[i] != ":":
                raise SettingsError("tokenizer: expected ':'")
            value_start = _skip_ws(text, i + 1)
            value_end = _end_of_value(text, value_start)
            members.append(dict(key=key, key_start=key_start, key_end=key_end,
                                value_start=value_start, value_end=value_end))
            i = _skip_ws(text, value_end)
            if text[i] == ",":
                i = _skip_ws(text, i + 1)
                continue
            if text[i] == "}":
                return open_idx, i, members
            raise SettingsError("tokenizer: expected ',' or '}'")
    except IndexError:
        raise SettingsError("tokenizer: unexpected end of text")


def _first_newline(s):
    m = re.search(r"\r\n|\n|\r", s)
    return m.group(0) if m else None


def detect_indent(text):
    for line in text.splitlines():
        if line[:1] in (" ", "\t"):
            n = len(line) - len(line.lstrip(" "))
            return n if n in (2, 4) and line[n:n + 1] != "\t" else 2
    return 2


def edit_text(text, new_value):
    """Return text with only the top-level advisorModel member changed.

    new_value None removes the member. Raises SettingsError on a second
    top-level advisorModel.
    """
    open_idx, close_idx, members = top_level_members(text)
    hits = [n for n, m in enumerate(members) if m["key"] == KEY]
    if len(hits) > 1:
        raise SettingsError(f"more than one top-level {KEY}")
    value = json.dumps(new_value, ensure_ascii=False) if new_value is not None else None

    if hits:
        n = hits[0]
        m = members[n]
        if value is not None:  # replace the value only
            return text[:m["value_start"]] + value + text[m["value_end"]:]
        if len(members) == 1:  # only member: the object becomes {}
            return text[:open_idx + 1] + text[close_idx:]
        if n == len(members) - 1:  # last: drop the comma before it through its value
            return text[:members[n - 1]["value_end"]] + text[m["value_end"]:]
        # first or middle: drop key through the whitespace before the next key
        return text[:m["key_start"]] + text[members[n + 1]["key_start"]:]

    if value is None:
        return text  # nothing to remove (caller treats as no-op)

    key = json.dumps(KEY)
    if not members:
        nl = _first_newline(text) or "\n"
        ind = " " * detect_indent(text)
        return text[:open_idx + 1] + nl + ind + key + ": " + value + nl + text[close_idx:]

    last = members[-1]
    sep = text[last["key_end"]:last["value_start"]]  # the file's own ': ' style
    inside = text[open_idx:close_idx]
    if _first_newline(inside) is None:  # single-line object
        return text[:last["value_end"]] + ", " + key + sep + value + text[last["value_end"]:]
    nl = (_first_newline(text[last["value_end"]:close_idx])
          or _first_newline(text[open_idx:last["key_start"]])
          or "\n")
    line_start = max(text.rfind("\n", 0, last["key_start"]), text.rfind("\r", 0, last["key_start"])) + 1
    ind = text[line_start:last["key_start"]]
    if line_start <= open_idx or ind.strip(" \t"):
        ind = " " * detect_indent(text)  # last member does not start its own line
    return text[:last["value_end"]] + "," + nl + ind + key + sep + value + text[last["value_end"]:]


def parse_settings_bytes(raw):
    """The strict object parse of raw bytes, or None when they do not parse."""
    body = raw[len(BOM):] if raw.startswith(BOM) else raw
    try:
        obj = strict_parse(body.decode("utf-8"))
    except (UnicodeDecodeError, SettingsError):
        return None
    return obj if isinstance(obj, dict) else None


def _shown(value):
    """fmt() for a strict-parse value (numbers arrive as ("num", text))."""
    if isinstance(value, tuple) and len(value) == 2 and value[0] == "num":
        return value[1]
    return fmt(value)


def plan_edit(raw, new_value):
    """Validate raw bytes and compute the new bytes.

    Returns (old_value, new_bytes); new_bytes is None when nothing changes.
    Raises SettingsError when the file must not be touched.
    """
    body = raw[len(BOM):] if raw.startswith(BOM) else raw
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as e:
        raise SettingsError(f"not UTF-8: {e}")
    before = strict_parse(text)
    if not isinstance(before, dict):
        raise SettingsError("top level is not a JSON object")
    old = before.get(KEY)
    if new_value is None and KEY not in before:
        return old, None
    if new_value is not None and old == new_value:
        return old, None

    new_text = edit_text(text, new_value)
    after = strict_parse(new_text)
    expected = dict(before)
    if new_value is None:
        del expected[KEY]
    else:
        expected[KEY] = new_value
    if not isinstance(after, dict) or list(after.items()) != list(expected.items()):
        raise SettingsError("internal check: the edit would change more than advisorModel")
    return old, new_text.encode("utf-8")


def make_backup(src_bytes):
    """Write src_bytes to a new settings-advisor-<stamp>[-n].json in the backup folder."""
    folder = backup_dir()
    os.makedirs(folder, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    n = 1
    while True:
        name = f"settings-advisor-{stamp}.json" if n == 1 else f"settings-advisor-{stamp}-{n}.json"
        path = os.path.join(folder, name)
        try:
            f = open(path, "xb")  # exclusive create: never overwrites
        except FileExistsError:
            n += 1
            continue
        try:
            with f:
                f.write(src_bytes)
                f.flush()
                os.fsync(f.fileno())
        except BaseException:
            _unlink_quiet(path)  # never leave a partial backup behind
            raise
        return path


def _unlink_quiet(path):
    try:
        os.unlink(path)
    except OSError:
        pass


def _write_temp(path, data):
    folder = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".settings-advisor-", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
    except BaseException:
        _unlink_quiet(tmp)
        raise
    return tmp


def swap_if_unchanged(path, expected, data):
    """Replace path with data only if it still holds expected. Returns True if replaced."""
    tmp = _write_temp(path, data)
    try:
        if reread_for_swap(path) != expected:
            _unlink_quiet(tmp)
            return False
        replace_file(tmp, path)
    except BaseException:
        _unlink_quiet(tmp)
        raise
    return True


def read_back_retrying(path):
    """Return the file's bytes, or None when still unreadable after the retries."""
    for attempt in range(1 + READ_BACK_RETRIES):
        if attempt:
            time.sleep(READ_BACK_WAIT * attempt)
        try:
            return read_back(path)
        except OSError as e:  # PermissionError included: a transient lock
            error = e
    print(f"advisor-state: cannot read {path} back after the write: {error}", file=sys.stderr)
    return None


def change(new_value):
    """Set advisorModel to new_value (None removes it) in the user settings file."""
    path = user_settings_path()
    for attempt in range(1 + SWAP_RETRIES):
        if attempt:
            time.sleep(SWAP_WAIT * attempt)
        try:
            raw = read_bytes(path)
        except FileNotFoundError:
            print(f"advisor-state: {path} not found; nothing written", file=sys.stderr)
            return 4
        except OSError as e:
            print(f"advisor-state: cannot read {path}: {e}; nothing written", file=sys.stderr)
            return 4
        try:
            old, new_bytes = plan_edit(raw, new_value)
        except SettingsError as e:
            print(f"advisor-state: {path}: {e}; nothing written", file=sys.stderr)
            return 4
        if new_bytes is None:
            if new_value is None:
                print("advisorModel: already unset; nothing changed")
            else:
                print(f"advisorModel: already {new_value}; nothing changed")
            return 0

        try:
            backup = make_backup(raw)  # exactly the bytes that were parsed
        except OSError as e:
            print(f"advisor-state: cannot write the backup ({e}); nothing written", file=sys.stderr)
            return 1

        if not swap_if_unchanged(path, raw, new_bytes):
            _unlink_quiet(backup)  # nothing was written in this cycle
            continue

        got = read_back_retrying(path)
        if got == new_bytes:
            print(f"advisorModel: {fmt(old)} -> {fmt(new_value)}")
            return 0
        # Never rewrite after the replace: whatever is there now stays as it is.
        if got is not None:
            now = parse_settings_bytes(got)
            shown = "invalid" if now is None else _shown(now.get(KEY))
            print(f"advisorModel now: {shown} (intended {fmt(new_value)})", file=sys.stderr)
        print(
            f"advisor-state: could not confirm the write; nothing restored; run `status`"
            f" and compare with the backup.\n"
            f"  settings file: {path}\n"
            f"  backup:        {backup}",
            file=sys.stderr,
        )
        return 5

    print("advisor-state: settings changed during the write; nothing written", file=sys.stderr)
    return 6



def cmd_on(model):
    if model not in MODELS:
        print(f"advisor-state: model must be one of {', '.join(MODELS)} (got {model!r})", file=sys.stderr)
        return 2
    if model == "fable":
        ok = fable_ok(parse_version(raw_cli_version()))
        if ok != "yes":
            print(
                f"advisor-state: fable advisor needs Claude Code 2.1.321 or later (fable_ok={ok}); nothing written",
                file=sys.stderr,
            )
            return 3
    return change(model)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="advisor-state.py", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_status = sub.add_parser("status")
    p_status.add_argument("--project")
    p_on = sub.add_parser("on")
    p_on.add_argument("model")
    sub.add_parser("off")
    args = parser.parse_args(argv)

    if args.cmd == "status":
        return cmd_status(args.project)
    if args.cmd == "on":
        return cmd_on(args.model)
    return change(None)


if __name__ == "__main__":
    sys.exit(main())
