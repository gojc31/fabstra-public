"""Tests for scripts/advisor-state.py.

Every test runs the script as a subprocess against a temp settings file through
the ADVISOR_STATE_* overrides. ADVISOR_STATE_CLI_VERSION is always set and PATH
points at an empty folder, so `claude` is never launched. A session fixture
fails the run if the real user settings file changed.
"""
import importlib.util
import json
import os
import subprocess
import sys

import pytest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "advisor-state.py")
REAL_SETTINGS = os.path.join(os.path.expanduser("~"), ".claude", "settings.json")


def _stat(path):
    try:
        st = os.stat(path)
        return (st.st_size, st.st_mtime_ns)
    except FileNotFoundError:
        return None


@pytest.fixture(scope="module", autouse=True)
def real_settings_untouched():
    before = _stat(REAL_SETTINGS)
    yield
    assert _stat(REAL_SETTINGS) == before, "real ~/.claude/settings.json changed during tests"


@pytest.fixture
def env(tmp_path):
    empty_bin = tmp_path / "emptybin"
    empty_bin.mkdir()
    settings = tmp_path / "settings.json"
    backups = tmp_path / "backups"
    e = {
        "ADVISOR_STATE_USER_SETTINGS": str(settings),
        "ADVISOR_STATE_BACKUP_DIR": str(backups),
        "ADVISOR_STATE_CLI_VERSION": "2.1.321 (Claude Code)",
        "PATH": str(empty_bin),
    }
    for k in ("SYSTEMROOT", "SystemRoot", "TEMP", "TMP"):
        if k in os.environ:
            e[k] = os.environ[k]
    return {"env": e, "settings": settings, "backups": backups, "tmp": tmp_path}


def run(ctx, *args, version=None, extra_env=None):
    e = dict(ctx["env"])
    if version is not None:
        e["ADVISOR_STATE_CLI_VERSION"] = version
    if extra_env:
        e.update(extra_env)
    return subprocess.run(
        [sys.executable, SCRIPT, *args], env=e, capture_output=True, text=True, timeout=30
    )


def status_map(proc):
    assert proc.returncode == 0, proc.stderr
    out = {}
    for line in proc.stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k] = v
    return out


RICH = {
    "model": "opus",
    "permissions": {"allow": ["Bash(git status)", "Read"], "deny": [], "defaultMode": "auto"},
    "hooks": {
        "PreToolUse": [
            {"matcher": "Agent", "hooks": [{"type": "command", "command": "python guard.py"}]}
        ]
    },
    "env": {"FOO": "bar"},
    "enabledPlugins": {"a@b": True},
    "statusLine": {"type": "command", "command": "x"},
}


def write_json(path, obj, indent=2, newline="\n"):
    text = json.dumps(obj, indent=indent, ensure_ascii=False) + "\n"
    if newline != "\n":
        text = text.replace("\n", newline)
    path.write_bytes(text.encode("utf-8"))


def read_obj(path):
    return json.loads(path.read_bytes().decode("utf-8"))


# ---------- round trip ----------

def test_round_trip_on_status_off(env):
    write_json(env["settings"], RICH)
    s = status_map(run(env, "status"))
    assert s["user_advisorModel"] == "unset"
    assert s["effective"] == "off"

    p = run(env, "on", "fable")
    assert p.returncode == 0, p.stderr
    assert "advisorModel: unset -> fable" in p.stdout
    assert read_obj(env["settings"])["advisorModel"] == "fable"

    s = status_map(run(env, "status"))
    assert s["user_advisorModel"] == "fable"
    assert s["effective"] == "fable"
    assert s["fable_ok"] == "yes"
    assert s["cli_version"] == "2.1.321"
    assert s["disable_env"] == "unset"
    assert s["disable_settings"] == "unset"

    p = run(env, "on", "opus")
    assert p.returncode == 0
    assert "advisorModel: fable -> opus" in p.stdout

    p = run(env, "off")
    assert p.returncode == 0, p.stderr
    assert "advisorModel: opus -> unset" in p.stdout
    obj = read_obj(env["settings"])
    assert "advisorModel" not in obj
    assert obj == RICH
    assert status_map(run(env, "status"))["effective"] == "off"


def test_other_keys_and_order_unchanged(env):
    write_json(env["settings"], RICH)
    assert run(env, "on", "opus").returncode == 0
    obj = read_obj(env["settings"])
    assert list(obj.keys())[:-1] == list(RICH.keys())
    for k, v in RICH.items():
        assert obj[k] == v


def test_existing_value_replaced_in_place_keeps_order(env):
    data = {"a": 1, "advisorModel": "opus", "b": {"c": [1, 2]}}
    write_json(env["settings"], data)
    assert run(env, "on", "fable").returncode == 0
    obj = read_obj(env["settings"])
    assert list(obj.keys()) == ["a", "advisorModel", "b"]
    assert obj["advisorModel"] == "fable"


# ---------- formatting ----------

@pytest.mark.parametrize("indent", [2, 4])
def test_indentation_kept(env, indent):
    write_json(env["settings"], RICH, indent=indent)
    assert run(env, "on", "opus").returncode == 0
    lines = env["settings"].read_bytes().decode("utf-8").splitlines()
    first_indented = next(l for l in lines if l.startswith(" "))
    assert len(first_indented) - len(first_indented.lstrip(" ")) == indent
    assert run(env, "off").returncode == 0
    assert env["settings"].read_bytes() == (json.dumps(RICH, indent=indent) + "\n").encode("utf-8")


def test_odd_indentation_matched_and_kept(env):
    write_json(env["settings"], RICH, indent=3)
    before = env["settings"].read_bytes()
    assert run(env, "on", "opus").returncode == 0
    lines = env["settings"].read_bytes().decode("utf-8").splitlines()
    assert '   "advisorModel": "opus"' in lines
    assert run(env, "off").returncode == 0
    assert env["settings"].read_bytes() == before


def test_crlf_kept_no_bom(env):
    write_json(env["settings"], RICH, newline="\r\n")
    assert run(env, "on", "opus").returncode == 0
    raw = env["settings"].read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" in raw
    assert raw.count(b"\n") == raw.count(b"\r\n")


def test_lf_kept(env):
    write_json(env["settings"], RICH)
    assert run(env, "on", "opus").returncode == 0
    assert b"\r\n" not in env["settings"].read_bytes()


def test_non_ascii_kept_utf8(env):
    data = {"note": "Angono café — ok"}
    write_json(env["settings"], data)
    assert run(env, "on", "opus").returncode == 0
    raw = env["settings"].read_bytes()
    assert "café —".encode("utf-8") in raw


# ---------- refusals ----------

def test_unparseable_refused_nothing_written(env):
    env["settings"].write_bytes(b'{"a": 1,,}')
    before = env["settings"].read_bytes()
    for args in (("on", "opus"), ("off",)):
        p = run(env, *args)
        assert p.returncode == 4
        assert env["settings"].read_bytes() == before
    assert not env["backups"].exists() or not list(env["backups"].iterdir())


def test_non_object_top_level_refused(env):
    env["settings"].write_bytes(b"[1, 2]\n")
    p = run(env, "on", "opus")
    assert p.returncode == 4
    assert env["settings"].read_bytes() == b"[1, 2]\n"


def test_unknown_model_refused(env):
    write_json(env["settings"], RICH)
    before = env["settings"].read_bytes()
    p = run(env, "on", "sonnet")
    assert p.returncode == 2
    assert env["settings"].read_bytes() == before


@pytest.mark.parametrize("version", ["2.1.318", "2.1.320 (Claude Code)", "2.0.999", "1.9.400"])
def test_fable_refused_on_old_cli(env, version):
    write_json(env["settings"], RICH)
    before = env["settings"].read_bytes()
    p = run(env, "on", "fable", version=version)
    assert p.returncode == 3
    assert env["settings"].read_bytes() == before
    assert not env["backups"].exists() or not list(env["backups"].iterdir())


@pytest.mark.parametrize("version", ["2.1.321 (Claude Code)", "2.2.0", "2.1.1000", "3.0.0"])
def test_fable_allowed_on_new_cli(env, version):
    write_json(env["settings"], RICH)
    p = run(env, "on", "fable", version=version)
    assert p.returncode == 0, p.stderr
    assert read_obj(env["settings"])["advisorModel"] == "fable"
    assert status_map(run(env, "status", version=version))["fable_ok"] == "yes"


@pytest.mark.parametrize("version", ["not a version", "", "2.1"])
def test_unknown_version_refuses_fable(env, version):
    write_json(env["settings"], RICH)
    before = env["settings"].read_bytes()
    p = run(env, "on", "fable", version=version)
    assert p.returncode == 3
    assert env["settings"].read_bytes() == before
    s = status_map(run(env, "status", version=version))
    assert s["fable_ok"] == "unknown"
    assert s["cli_version"] == "unknown"


@pytest.mark.parametrize("version", ["2.1.318", "garbage"])
def test_opus_allowed_regardless(env, version):
    write_json(env["settings"], RICH)
    p = run(env, "on", "opus", version=version)
    assert p.returncode == 0, p.stderr
    assert read_obj(env["settings"])["advisorModel"] == "opus"


def test_status_old_cli_fable_ok_no(env):
    write_json(env["settings"], RICH)
    assert status_map(run(env, "status", version="2.1.318"))["fable_ok"] == "no"


# ---------- backups ----------

def test_backups_created_and_never_overwritten(env):
    write_json(env["settings"], RICH)
    originals = []
    for model in ("opus", "fable", "opus", "fable"):
        originals.append(env["settings"].read_bytes())
        assert run(env, "on", model).returncode == 0
    files = sorted(env["backups"].iterdir())
    assert len(files) == 4
    for f in files:
        assert f.name.startswith("settings-advisor-") and f.suffix == ".json"
    contents = sorted(f.read_bytes() for f in files)
    assert contents == sorted(originals)


def test_backup_suffix_when_name_taken(env):
    write_json(env["settings"], RICH)
    env["backups"].mkdir()
    # Pre-create backups for every second in a wide window so the run collides.
    import datetime as dt
    now = dt.datetime.now()
    sentinel = b"SENTINEL"
    for delta in range(-2, 30):
        stamp = (now + dt.timedelta(seconds=delta)).strftime("%Y%m%d-%H%M%S")
        (env["backups"] / f"settings-advisor-{stamp}.json").write_bytes(sentinel)
    assert run(env, "on", "opus").returncode == 0
    suffixed = [f for f in env["backups"].iterdir() if f.name.endswith("-2.json")]
    assert len(suffixed) == 1
    for f in env["backups"].iterdir():
        if f not in suffixed:
            assert f.read_bytes() == sentinel


# ---------- disable values ----------

@pytest.mark.parametrize("val", ["1", "true", "TRUE", "True"])
def test_disable_env_makes_effective_off(env, val):
    write_json(env["settings"], dict(RICH, advisorModel="opus"))
    s = status_map(run(env, "status", extra_env={"CLAUDE_CODE_DISABLE_ADVISOR_TOOL": val}))
    assert s["disable_env"] == val
    assert s["effective"] == "off"


def test_disable_env_false_keeps_effective(env):
    write_json(env["settings"], dict(RICH, advisorModel="opus"))
    s = status_map(run(env, "status", extra_env={"CLAUDE_CODE_DISABLE_ADVISOR_TOOL": "0"}))
    assert s["disable_env"] == "0"
    assert s["effective"] == "opus"


def test_disable_settings_env_block_makes_effective_off(env):
    data = dict(RICH, advisorModel="opus", env={"CLAUDE_CODE_DISABLE_ADVISOR_TOOL": "1"})
    write_json(env["settings"], data)
    s = status_map(run(env, "status"))
    assert s["disable_settings"] == "1"
    assert s["effective"] == "off"


def test_project_and_local_settings(env):
    write_json(env["settings"], RICH)
    proj = env["tmp"] / "proj"
    (proj / ".claude").mkdir(parents=True)
    write_json(proj / ".claude" / "settings.json", {"advisorModel": "opus"})
    write_json(
        proj / ".claude" / "settings.local.json",
        {"advisorModel": "fable", "env": {"CLAUDE_CODE_DISABLE_ADVISOR_TOOL": "true"}},
    )
    s = status_map(run(env, "status", "--project", str(proj)))
    assert s["user_advisorModel"] == "unset"
    assert s["project_advisorModel"] == "opus"
    assert s["local_advisorModel"] == "fable"
    assert s["disable_settings"] == "true"
    assert s["effective"] == "off"


def test_project_model_applies_without_user(env):
    write_json(env["settings"], RICH)
    proj = env["tmp"] / "proj"
    (proj / ".claude").mkdir(parents=True)
    write_json(proj / ".claude" / "settings.json", {"advisorModel": "opus"})
    s = status_map(run(env, "status", "--project", str(proj)))
    assert s["local_advisorModel"] == "unset"
    assert s["effective"] == "opus"


# ---------- off when absent ----------

def test_off_when_absent_is_noop(env):
    write_json(env["settings"], RICH, indent=4)
    before = env["settings"].read_bytes()
    p = run(env, "off")
    assert p.returncode == 0
    assert p.stdout.strip()
    assert env["settings"].read_bytes() == before
    assert not env["backups"].exists() or not list(env["backups"].iterdir())


# ========== byte-preserving edits (fix round 1) ==========

def put(ctx, text):
    raw = text.encode("utf-8") if isinstance(text, str) else text
    ctx["settings"].write_bytes(raw)
    return raw


def no_backups(ctx):
    return not ctx["backups"].exists() or not list(ctx["backups"].iterdir())


NUMS = (
    '{\n'
    '  "ratio": 0.12345678901234567890123456789,\n'
    '  "huge": 1e400,\n'
    '  "tiny": 1e-400,\n'
    '  "exp": 6.02E+23,\n'
    '  "neg0": -0,\n'
    '  "negf": -0.0,\n'
    '  "dec": 1.00,\n'
    '  "big": 1234567890123456789012345678901234567890\n'
    '}\n'
)


def test_numbers_kept_byte_identical(env):
    raw = put(env, NUMS)
    assert run(env, "on", "opus").returncode == 0
    after_on = env["settings"].read_bytes().decode("utf-8")
    assert after_on == NUMS[:-3] + ',\n  "advisorModel": "opus"\n}\n'
    assert run(env, "on", "fable").returncode == 0
    assert env["settings"].read_bytes().decode("utf-8") == after_on.replace('"opus"', '"fable"')
    assert run(env, "off").returncode == 0
    assert env["settings"].read_bytes() == raw


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_nonstandard_constants_refused(env, token):
    raw = put(env, '{\n  "other": %s\n}\n' % token)
    for args in (("on", "opus"), ("off",)):
        p = run(env, *args)
        assert p.returncode == 4, p.stdout + p.stderr
        assert env["settings"].read_bytes() == raw
    assert no_backups(env)


def test_constant_in_nested_value_refused_on_off_with_key(env):
    raw = put(env, '{"advisorModel": "opus", "x": [1, NaN]}')
    assert run(env, "off").returncode == 4
    assert env["settings"].read_bytes() == raw
    assert no_backups(env)


@pytest.mark.parametrize(
    "text",
    [
        '{"env": {"FIRST": "keep"}, "env": {"SECOND": "keep"}}\n',
        '{"a": {"b": {"FIRST": 1, "FIRST": 2}}}\n',
        '{"a": [{"k": 1, "k": 1}]}\n',
        '{"advisorModel": "opus", "x": 1, "advisorModel": "fable"}\n',
    ],
)
def test_duplicate_keys_refused(env, text):
    raw = put(env, text)
    for args in (("on", "opus"), ("off",)):
        p = run(env, *args)
        assert p.returncode == 4, p.stdout + p.stderr
        assert env["settings"].read_bytes() == raw
    assert no_backups(env)


def test_nested_advisor_model_untouched(env):
    text = '{\n  "x": {\n    "advisorModel": "opus"\n  },\n  "y": [{"advisorModel": "fable"}]\n}\n'
    raw = put(env, text)
    p = run(env, "off")
    assert p.returncode == 0
    assert "already unset" in p.stdout
    assert env["settings"].read_bytes() == raw
    assert run(env, "on", "fable").returncode == 0
    after = env["settings"].read_bytes().decode("utf-8")
    assert after == text[:-3] + ',\n  "advisorModel": "fable"\n}\n'
    assert run(env, "off").returncode == 0
    assert env["settings"].read_bytes() == raw


def test_nested_key_untouched_when_top_level_first(env):
    text = '{"advisorModel": "opus", "x": {"advisorModel": "opus"}}'
    put(env, text)
    assert run(env, "on", "fable").returncode == 0
    assert env["settings"].read_bytes().decode() == '{"advisorModel": "fable", "x": {"advisorModel": "opus"}}'
    assert run(env, "off").returncode == 0
    assert env["settings"].read_bytes().decode() == '{"x": {"advisorModel": "opus"}}'


@pytest.mark.parametrize("nl", ["\n", "\r\n"])
@pytest.mark.parametrize("trailing", [False, True])
def test_insert_into_empty_object(env, nl, trailing):
    tail = nl * 2 if trailing else ""  # two trailing line endings must survive
    raw = put(env, "{}" + tail)
    if not trailing:
        nl = "\n"  # no line ending in the file: LF default
    assert run(env, "on", "fable").returncode == 0
    after = env["settings"].read_bytes().decode("utf-8")
    assert after == "{" + nl + '  "advisorModel": "fable"' + nl + "}" + tail
    assert json.loads(after) == {"advisorModel": "fable"}
    assert run(env, "off").returncode == 0
    assert env["settings"].read_bytes() == raw


@pytest.mark.parametrize("nl", ["\n", "\r\n"])
@pytest.mark.parametrize("indent", [2, 4])
def test_insert_into_one_member_object(env, nl, indent):
    ind = " " * indent
    text = "{" + nl + ind + '"n": 1.50' + nl + "}" + nl
    raw = put(env, text)
    assert run(env, "on", "fable").returncode == 0
    after = env["settings"].read_bytes().decode("utf-8")
    assert after == "{" + nl + ind + '"n": 1.50,' + nl + ind + '"advisorModel": "fable"' + nl + "}" + nl
    assert json.loads(after) == {"n": 1.5, "advisorModel": "fable"}
    assert run(env, "off").returncode == 0
    assert env["settings"].read_bytes() == raw


def test_insert_into_single_line_object(env):
    raw = put(env, '{"a": 1}')
    assert run(env, "on", "opus").returncode == 0
    assert env["settings"].read_bytes() == b'{"a": 1, "advisorModel": "opus"}'
    assert run(env, "off").returncode == 0
    assert env["settings"].read_bytes() == raw


def test_remove_only_member(env):
    put(env, '{\n  "advisorModel": "opus"\n}\n\n')
    assert run(env, "off").returncode == 0
    assert env["settings"].read_bytes() == b"{}\n\n"


@pytest.mark.parametrize(
    "text, expected",
    [
        (
            '{\n  "a": 1.0e2,\n  "advisorModel": "opus",\n  "b": 2\n}\n',
            '{\n  "a": 1.0e2,\n  "b": 2\n}\n',
        ),
        (
            '{\r\n    "a": 1,\r\n    "b": [1,\r\n 2],\r\n    "advisorModel": "opus"\r\n}\r\n',
            '{\r\n    "a": 1,\r\n    "b": [1,\r\n 2]\r\n}\r\n',
        ),
        (
            '{\n  "advisorModel": "opus",\n  "a": {"b": 1}\n}\n',
            '{\n  "a": {"b": 1}\n}\n',
        ),
        ('{"a":1,"advisorModel":"opus","b":2}', '{"a":1,"b":2}'),
    ],
)
def test_remove_member_middle_last_first(env, text, expected):
    put(env, text)
    assert run(env, "off").returncode == 0
    assert env["settings"].read_bytes().decode("utf-8") == expected


def test_replace_value_in_place_only(env):
    text = '{\n\t"a" :  1.50,\n\t"advisorModel"  :  "opus" ,\n\t"b": 2\n}'
    put(env, text)
    assert run(env, "on", "fable").returncode == 0
    assert env["settings"].read_bytes().decode() == text.replace('"opus"', '"fable"')


def test_mixed_line_endings_and_two_trailing_newlines_kept(env):
    text = '{\n  "model": "opus",\n  "env": {"FOO":"bar"}\r\n}\n\n'
    raw = put(env, text)
    assert run(env, "on", "opus").returncode == 0
    after = env["settings"].read_bytes().decode("utf-8")
    assert after == '{\n  "model": "opus",\n  "env": {"FOO":"bar"},\r\n  "advisorModel": "opus"\r\n}\n\n'
    assert run(env, "off").returncode == 0
    assert env["settings"].read_bytes() == raw


def test_bom_dropped_rest_identical(env):
    put(env, b'\xef\xbb\xbf{\r\n    "env": {"note":"ok"}\r\n}\r\n')
    assert run(env, "on", "opus").returncode == 0
    assert env["settings"].read_bytes() == b'{\r\n    "env": {"note":"ok"},\r\n    "advisorModel": "opus"\r\n}\r\n'
    assert run(env, "off").returncode == 0
    assert env["settings"].read_bytes() == b'{\r\n    "env": {"note":"ok"}\r\n}\r\n'


def test_escaped_strings_kept_byte_identical(env):
    text = '{"note": "caf\\u00e9 \\/ \\u0061 \\"q\\" \\\\", "path": "C:\\\\tmp\\tfoo\\nbar"}'
    raw = put(env, text)
    assert run(env, "on", "opus").returncode == 0
    assert run(env, "off").returncode == 0
    assert env["settings"].read_bytes() == raw


# ---------- in-process fault injection ----------

@pytest.fixture
def mod(env, monkeypatch):
    for k, v in env["env"].items():
        if k.startswith("ADVISOR_STATE_"):
            monkeypatch.setenv(k, v)
    monkeypatch.delenv("CLAUDE_CODE_DISABLE_ADVISOR_TOOL", raising=False)
    spec = importlib.util.spec_from_file_location("advisor_state_under_test", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    monkeypatch.setattr(m.time, "sleep", lambda s: None)
    return m


ORIG = b'{\n  "env": {"TOKEN": "old"},\n  "permissions": {"deny": ["Read(secret)"]}\n}\n'


def test_concurrent_save_never_overwritten_exit_6(env, mod, monkeypatch, capsys):
    put(env, ORIG)
    real = mod.reread_for_swap
    calls = [0]

    def competing(path):
        calls[0] += 1
        env["settings"].write_bytes(b'{"env": {"TOKEN": "new%d"}}\n' % calls[0])
        return real(path)

    monkeypatch.setattr(mod, "reread_for_swap", competing)
    assert mod.main(["on", "opus"]) == 6
    assert "settings changed during the write; nothing written" in capsys.readouterr().err
    assert calls[0] == 4  # first attempt + 3 retries
    assert env["settings"].read_bytes() == b'{"env": {"TOKEN": "new4"}}\n'
    assert no_backups(env)
    assert not list(env["tmp"].glob("*.tmp")) and not list(env["tmp"].glob(".*.tmp"))


def test_concurrent_save_once_then_retry_keeps_their_change(env, mod, monkeypatch):
    put(env, ORIG)
    real = mod.reread_for_swap
    calls = [0]
    theirs = b'{\n  "env": {"TOKEN": "new"},\n  "newUserKey": true\n}\n'

    def competing_once(path):
        calls[0] += 1
        if calls[0] == 1:
            env["settings"].write_bytes(theirs)
        return real(path)

    monkeypatch.setattr(mod, "reread_for_swap", competing_once)
    assert mod.main(["on", "opus"]) == 0
    assert env["settings"].read_bytes() == theirs[:-3] + b',\n  "advisorModel": "opus"\n}\n'
    backups = list(env["backups"].iterdir())
    assert [b.read_bytes() for b in backups] == [theirs]


def test_backup_is_exactly_parsed_bytes(env, mod, monkeypatch):
    put(env, ORIG)
    seen = []
    real = mod.read_bytes

    def spy(path):
        data = real(path)
        seen.append(data)
        return data

    monkeypatch.setattr(mod, "read_bytes", spy)
    assert mod.main(["on", "opus"]) == 0
    (backup,) = env["backups"].iterdir()
    assert backup.read_bytes() == seen[0] == ORIG


def split_backups(ctx):
    """(backups, conflict files) in the backup folder."""
    files = sorted(ctx["backups"].iterdir()) if ctx["backups"].exists() else []
    conflicts = [f for f in files if "conflict" in f.name]
    return [f for f in files if f not in conflicts], conflicts


ORIG_ON = b'{\n  "env": {"TOKEN": "old"},\n  "advisorModel": "fable",\n  "permissions": {"deny": []}\n}\n'
CMDS = [["on", "opus"], ["off"]]
UNCONFIRMED = "could not confirm the write; nothing restored; run `status` and compare with the backup"


def _external_replace(mod, monkeypatch, env, theirs):
    """After the script's own os.replace, another program saves `theirs` (atomically)."""
    real = mod.replace_file
    calls = []

    def commit(src, dst):
        real(src, dst)
        calls.append("replace")
        if len(calls) == 1 and theirs is not None:
            other = env["tmp"] / "editor-save.tmp"
            other.write_bytes(theirs)
            os.replace(other, dst)

    monkeypatch.setattr(mod, "replace_file", commit)
    return calls


def _assert_unconfirmed(env, msg, calls):
    assert UNCONFIRMED in msg
    backups, conflicts = split_backups(env)
    assert [b.read_bytes() for b in backups] == [ORIG_ON] and conflicts == []
    assert str(env["settings"]) in msg and str(backups[0]) in msg
    assert calls == ["replace"]  # never a second replace: nothing is rewritten
    assert not list(env["tmp"].glob(".*.tmp"))


@pytest.mark.parametrize(
    "cmd, theirs, now, intended",
    [
        (["on", "opus"], b'{"env":{"TOKEN":"new"},"newUserKey":true,"advisorModel":"opus"}\n', "opus", "opus"),
        (["on", "opus"], b'{"env":{"TOKEN":"new"},"advisorModel":"fable"}', "fable", "opus"),
        (["on", "opus"], b'{\r\n  "env": {"TOKEN": "new"}\r\n}', "unset", "opus"),
        (["off"], b'{"env":{"TOKEN":"new"},"permissions":{"deny":["Bash(*)"]}}\n', "unset", "unset"),
        (["off"], b'{"env":{"TOKEN":"new"},"advisorModel":"opus"}', "opus", "unset"),
    ],
)
def test_external_valid_save_after_replace_kept_exit_5(env, mod, monkeypatch, capsys, cmd, theirs, now, intended):
    put(env, ORIG_ON)
    calls = _external_replace(mod, monkeypatch, env, theirs)
    assert mod.main(cmd) == 5
    out = capsys.readouterr()
    msg = out.out + out.err
    assert env["settings"].read_bytes() == theirs  # byte-for-byte
    assert f"advisorModel now: {now} (intended {intended})" in msg
    _assert_unconfirmed(env, msg, calls)


@pytest.mark.parametrize("cmd", CMDS)
@pytest.mark.parametrize("garbage", [b"{", b'{"a": 1, "a": 2}', b"[1, 2]", b"", b"\xff\xfe"])
def test_invalid_read_back_kept_exit_5(env, mod, monkeypatch, capsys, cmd, garbage):
    put(env, ORIG_ON)
    calls = _external_replace(mod, monkeypatch, env, garbage)
    assert mod.main(cmd) == 5
    out = capsys.readouterr()
    msg = out.out + out.err
    assert env["settings"].read_bytes() == garbage  # left exactly as it is
    intended = "opus" if cmd[0] == "on" else "unset"
    assert f"advisorModel now: invalid (intended {intended})" in msg
    _assert_unconfirmed(env, msg, calls)


def _locked_read_back(mod, monkeypatch, fails):
    """The verification read raises PermissionError `fails` times, then reads for real."""
    real = mod.read_back
    tries = [0]

    def locked(path):
        tries[0] += 1
        if tries[0] <= fails:
            raise PermissionError(13, "injected sharing violation")
        return real(path)

    monkeypatch.setattr(mod, "read_back", locked)
    return tries


@pytest.mark.parametrize("cmd", CMDS)
def test_read_back_locked_for_all_retries_kept_exit_5(env, mod, monkeypatch, capsys, cmd):
    put(env, ORIG_ON)
    calls = _external_replace(mod, monkeypatch, env, None)
    tries = _locked_read_back(mod, monkeypatch, fails=99)
    assert mod.main(cmd) == 5
    out = capsys.readouterr()
    msg = out.out + out.err
    assert tries[0] == 1 + 3  # first read + 3 retries
    assert "advisorModel now:" not in msg  # nothing was read back
    after = env["settings"].read_bytes()
    assert after != ORIG_ON  # our write stays; no rollback
    assert (b'"opus"' in after) if cmd[0] == "on" else (b"advisorModel" not in after)
    _assert_unconfirmed(env, msg, calls)


@pytest.mark.parametrize("cmd", CMDS)
def test_read_back_locked_once_then_equal_exit_0(env, mod, monkeypatch, capsys, cmd):
    put(env, ORIG_ON)
    calls = _external_replace(mod, monkeypatch, env, None)
    tries = _locked_read_back(mod, monkeypatch, fails=1)
    assert mod.main(cmd) == 0
    assert tries[0] == 2
    assert calls == ["replace"]
    assert UNCONFIRMED not in capsys.readouterr().err
    after = env["settings"].read_bytes()
    assert (b'"opus"' in after) if cmd[0] == "on" else (b"advisorModel" not in after)


@pytest.mark.parametrize("cmd", CMDS)
def test_locked_read_back_then_newer_save_survives(env, mod, monkeypatch, capsys, cmd):
    """Review r3 N1: the lock clears during the retry wait; the newer save must survive."""
    put(env, ORIG_ON)
    newer = b'{"env":{"TOKEN":"new"},"permissions":{"deny":["Bash(*)"]},"newUserKey":true,"advisorModel":"opus"}\n'
    calls = _external_replace(mod, monkeypatch, env, newer)
    tries = _locked_read_back(mod, monkeypatch, fails=1)
    assert mod.main(cmd) == 5
    out = capsys.readouterr()
    msg = out.out + out.err
    assert tries[0] == 2
    assert env["settings"].read_bytes() == newer
    assert "advisorModel now: opus (intended " in msg
    _assert_unconfirmed(env, msg, calls)


def test_no_restore_path_left(mod):
    assert not hasattr(mod, "restore") and not hasattr(mod, "RESTORE_RETRIES")
    assert "exit 7" not in mod.__doc__ and "7 verification" not in mod.__doc__
    assert "advisor-conflict" not in mod.__doc__ and ".bin" not in mod.__doc__


def test_partial_backup_removed_nothing_written(env, mod, monkeypatch):
    put(env, ORIG)
    import builtins

    real_open = builtins.open

    class Partial:
        def __init__(self, f):
            self.f = f

        def __enter__(self):
            return self

        def __exit__(self, *a):
            self.f.close()

        def write(self, data):
            self.f.write(data[:5])
            raise OSError(28, "injected disk full")

    def fake_open(path, mode="r", *a, **k):
        f = real_open(path, mode, *a, **k)
        return Partial(f) if mode == "xb" else f

    monkeypatch.setattr(builtins, "open", fake_open)
    try:
        rc = mod.main(["on", "opus"])
    except OSError:
        rc = None  # the unfixed script lets the error escape
    finally:
        monkeypatch.setattr(builtins, "open", real_open)
    assert rc not in (0, 5)
    assert env["settings"].read_bytes() == ORIG
    assert no_backups(env)
    assert not list(env["tmp"].glob(".*.tmp"))
