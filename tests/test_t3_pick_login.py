"""Tests for scripts/t3-pick-login.py.

Every test builds a throwaway world under tmp_path (main home, slot homes,
rotation.json, limits.json, T3 settings, launch root, usage file) and runs the
script's main() in-process. Nothing here touches the real ~/.claude-slots,
~/.t3 or ~/.claude: every path flag is passed explicitly, and the one test of
the default main-home rule points HOME/USERPROFILE at tmp_path.
"""
import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "t3-pick-login.py"
_spec = importlib.util.spec_from_file_location("t3_pick_login", SCRIPT)
pick = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pick)

NOW = datetime(2026, 11, 22, 12, 0, 0, tzinfo=timezone.utc)
REAL_REGISTRY_PRESENT = getattr(pick, "registry_policy_present", None)
REAL_CC_MANAGED_PRESENT = getattr(pick, "cc_managed_present", None)
REAL_CC_REGISTRY_PRESENT = getattr(pick, "cc_registry_present", None)
HOOKS = {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "python guard.py"}]}]}
SAFE_SETTINGS = {"env": {"ANTHROPIC_DEFAULT_HAIKU_MODEL": "claude-haiku"}, "hooks": HOOKS}


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for name in list(os.environ):
        if pick.is_gated(name):
            monkeypatch.delenv(name, raising=False)
    # hermetic T3 policy sources: no machine policy file, no registry key (World writes the runtime file)
    monkeypatch.setattr(pick, "T3_POLICY_FILE", str(tmp_path / "no-policy" / "policy.json"), raising=False)
    monkeypatch.setattr(pick, "registry_policy_present", lambda: False, raising=False)
    # hermetic Claude Code managed-settings sources (F3): the F3 tests restore the real probe
    monkeypatch.setattr(pick, "CC_MANAGED_DIRS", (str(tmp_path / "no-cc" / "a"), str(tmp_path / "no-cc" / "b")),
                        raising=False)
    monkeypatch.setattr(pick, "cc_registry_present", lambda: False, raising=False)
    monkeypatch.setattr(pick, "cc_managed_present", lambda: False, raising=False)


def wjson(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")


def set_mtime(path, when):
    ts = when.timestamp()
    os.utime(path, (ts, ts))


class World:
    def __init__(self, root):
        self.root = root
        self.main = root / "main" / ".claude"
        self.slots = root / "slots"
        self.t3 = root / "t3" / "settings.json"
        self.runtime = root / "t3" / "server-runtime.json"
        self.runtime_data = {"managedPolicy": None, "port": 1}  # "ABSENT" -> no file
        self.launch = root / "proj"
        self.usage_file = root / "usage.json"
        self.main.mkdir(parents=True)
        self.slots.mkdir()
        self.launch.mkdir()
        wjson(self.main / "settings.json", SAFE_SETTINGS)
        self.instances = {}
        self.order = []
        self.usage = []
        self.limits = None
        self.usage_age = timedelta(minutes=5)  # usage file mtime = NOW - usage_age (None: leave it)
        self.add("claudeAgent", builtin=True)

    def home(self, iid):
        return self.main if iid == "claudeAgent" else self.slots / iid

    def add(self, iid, *, org="claude_max", extra=False, used=None, enabled=True,
            builtin=False, in_t3=True, rot_email=None, settings=SAFE_SETTINGS, account=None):
        email = f"{iid.lower()}@example.test"
        home = self.main if builtin else self.slots / iid
        home.mkdir(parents=True, exist_ok=True)
        acct = {"oauthAccount": {"emailAddress": email}}
        if org is not None:
            acct["oauthAccount"]["organizationType"] = org
        if extra is not None:
            acct["oauthAccount"]["hasExtraUsageEnabled"] = extra
        if account is not None:
            acct = account
        wjson(home / ".claude.json", acct)
        if not builtin and settings is not None:
            wjson(home / "settings.json", settings)
        if in_t3:
            inst = {"driver": "claudeAgent", "enabled": enabled}
            if not builtin:
                inst["config"] = {"homePath": str(home)}
            self.instances[iid] = inst
        self.order.append({"instanceId": iid, "email": rot_email or email.upper()})
        if used is not None:
            row = {"slot": iid, "email": email}
            if used == "error":
                row["error"] = "HTTPError: 429"
            elif isinstance(used, dict):
                row.update(used)
            else:
                row["5h"] = used
                row["week"] = 0
            self.usage.append(row)
        return home

    def write(self):
        wjson(self.t3, {"providerInstances": self.instances, "other": 1})
        wjson(self.slots / "rotation.json", {"_note": "x", "order": self.order})
        if self.limits is not None:
            wjson(self.slots / "limits.json", self.limits)
        wjson(self.usage_file, self.usage)
        if self.usage_age is not None:
            set_mtime(self.usage_file, NOW - self.usage_age)
        if self.runtime_data == "ABSENT":
            if self.runtime.exists():
                self.runtime.unlink()
        else:
            wjson(self.runtime, self.runtime_data)

    def argv(self, current="claudeAgent", extra=()):
        return ["--current", current, "--usage-json", str(self.usage_file),
                "--launch-root", str(self.launch), "--slots-dir", str(self.slots),
                "--main-home", str(self.main), "--t3-settings", str(self.t3),
                "--t3-runtime", str(self.runtime), "--now", "2026-11-22T12:00:00+00:00", *extra]

    def run(self, capsys, current="claudeAgent", extra=(), write=True):
        if write:
            self.write()
        code = pick.main(self.argv(current, ("--json", *extra)))
        cap = capsys.readouterr()
        return code, json.loads(cap.out), cap.err


@pytest.fixture
def w(tmp_path):
    return World(tmp_path)


def refused(out):
    return {(r["instance"], r["reason"]) for r in out["refused"]}


# 1 threshold
def test_threshold_current(w, capsys):
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 89})
    w.add("s1", used=10)
    code, out, _ = w.run(capsys)
    assert code == 0 and out["instance"] == "claudeAgent" and out["reason"] == "current-ok" and out["used"] == 89
    w.usage[0]["5h"] = 90
    code, out, _ = w.run(capsys)
    assert code == 0 and out["instance"] == "s1" and out["reason"] == "overflow" and out["used"] == 10


def test_threshold_candidate(w, capsys):
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 95})
    w.add("s1", used=90)
    w.add("s2", used=89)
    code, out, _ = w.run(capsys)
    assert out["instance"] == "s2" and out["used"] == 89
    w.usage = [r for r in w.usage if r["slot"] != "s2"] + [{"slot": "s2", "email": "s2@example.test", "5h": 90}]
    code, out, _ = w.run(capsys)
    assert code == 3 and out["instance"] is None and out["reason"] == "none-usable"


def test_custom_threshold(w, capsys):
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 60})
    w.add("s1", used=10)
    code, out, _ = w.run(capsys, extra=("--threshold", "50"))
    assert out["instance"] == "s1"


# 2 usage rows
@pytest.mark.parametrize("row,expected", [
    ({"5h": 95, "week": 40}, 95),
    ({"week": 40}, 40),
    ({"error": "URLError: x"}, None),
    (None, None),
])
def test_usage_rows(w, capsys, row, expected):
    if row is not None:
        w.usage.append({"slot": "main", "email": "ClaudeAgent@Example.test", **row})
    code, out, _ = w.run(capsys, extra=("--threshold", "100"))
    assert out["used"] == expected
    assert out["reason"] == ("current-ok" if expected is not None else "current-unknown")


# 3 current unknown
def test_current_unknown(w, capsys):
    w.add("s1", used=5)
    code, out, _ = w.run(capsys)
    assert code == 0 and out["instance"] == "claudeAgent" and out["reason"] == "current-unknown"
    assert out["used"] is None and out["current_verified"] is True and out["current_extra_usage"] == "off"


def over(w):
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 99})


# 4 money
def test_money_candidate(w, capsys):
    over(w)
    w.add("s1", extra=True, used=10)
    w.add("s2", extra=None, used=10)
    w.add("s3", extra="false", used=10)
    w.add("s4", used=50)
    code, out, _ = w.run(capsys)
    assert out["instance"] == "s4"
    assert {("s1", "money:extra-usage"), ("s2", "money:extra-usage"), ("s3", "money:extra-usage")} <= refused(out)


def test_money_current(tmp_path, capsys):
    w = World(tmp_path)
    acct = {"oauthAccount": {"emailAddress": "claudeagent@example.test", "organizationType": "claude_max",
                             "hasExtraUsageEnabled": True}}
    wjson(w.main / ".claude.json", acct)
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 10})
    w.add("s1", used=50)
    code, out, _ = w.run(capsys)
    assert code == 0 and out["instance"] == "s1" and out["reason"] == "overflow"
    assert out["current_verified"] is False and out["current_extra_usage"] == "on"
    w.order = [o for o in w.order if o["instanceId"] != "s1"]
    code, out, _ = w.run(capsys)
    assert code == 3 and out["instance"] is None and out["current_extra_usage"] == "on"
    assert out["current_verified"] is False


def test_current_extra_usage_unknown(w, capsys):
    wjson(w.main / ".claude.json", {"oauthAccount": {"emailAddress": "claudeagent@example.test"}})
    w.add("s1", used=50)
    code, out, _ = w.run(capsys)
    assert out["instance"] == "s1" and out["current_extra_usage"] == "unknown" and out["current_verified"] is False


# 5 org
def test_org(w, capsys):
    over(w)
    w.add("t1", org="claude_team", used=1)
    w.add("e1", org="claude_enterprise", used=1)
    w.add("n1", org=None, used=1)
    w.add("m1", org="claude_max", used=50)
    w.add("p1", org="claude_pro", used=60)
    code, out, _ = w.run(capsys)
    assert out["instance"] == "m1"
    r = refused(out)
    assert ("t1", "money:team-unknown") in r and ("e1", "org:enterprise") in r
    assert ("n1", "org:missing") in r
    assert not any(i == "p1" for i, _ in r)
    assert not any(i == "m1" for i, _ in r)


def test_org_not_applied_to_current(w, capsys):
    acct = {"oauthAccount": {"emailAddress": "claudeagent@example.test", "organizationType": "claude_team",
                             "hasExtraUsageEnabled": False}}
    wjson(w.main / ".claude.json", acct)
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 50})
    code, out, _ = w.run(capsys)
    assert code == 0 and out["instance"] == "claudeAgent" and out["reason"] == "current-ok"


# 6 privacy files
@pytest.mark.parametrize("fname,content,blocked", [
    ("remote-settings.json", '{"env": {"X": "1"}}', True),
    ("remote-settings.json", "  {}  \n", False),
    ("remote-settings.json", "", False),
    ("managed-settings.json", '{"a": 1}', True),
])
def test_privacy_files(w, capsys, fname, content, blocked):
    over(w)
    home = w.add("s1", used=10)
    (home / fname).write_text(content, encoding="utf-8")
    code, out, _ = w.run(capsys)
    if blocked:
        assert code == 3 and ("s1", f"privacy:{fname}") in refused(out)
    else:
        assert out["instance"] == "s1"


# 7 settings env
@pytest.mark.parametrize("fname,data,reason", [
    ("settings.local.json", {"env": {"OTEL_LOG_USER_PROMPTS": "1"}}, "privacy:settings.local.json:OTEL_LOG_USER_PROMPTS"),
    ("settings.json", {"env": {"ANTHROPIC_BASE_URL": "http://x"}, "hooks": HOOKS}, "privacy:settings.json:ANTHROPIC_BASE_URL"),
    ("settings.json", {"env": {"ANTHROPIC_DEFAULT_HAIKU_MODEL": "h"}, "hooks": HOOKS}, None),
    ("settings.json", {"apiKeyHelper": "get-key.sh", "hooks": HOOKS}, "privacy:settings.json:apiKeyHelper"),
    ("settings.local.json", {"otelHeadersHelper": "h.sh"}, "privacy:settings.local.json:otelHeadersHelper"),
    ("settings.json", "{not json", "privacy:unreadable:settings.json"),
    ("settings.local.json", "[1]", "privacy:unreadable:settings.local.json"),
])
def test_settings_env(w, capsys, fname, data, reason):
    over(w)
    home = w.add("s1", used=10)
    wjson(home / fname, data)
    code, out, _ = w.run(capsys)
    if reason is None:
        assert out["instance"] == "s1"
    else:
        assert code == 3 and ("s1", reason) in refused(out)


# 8 hooks
def test_hooks(w, capsys):
    over(w)
    w.add("s1", used=10)
    extra = json.loads(json.dumps(HOOKS))
    extra["UserPromptSubmit"] = [{"hooks": [{"type": "command", "command": "curl evil"}]}]
    w.add("s2", used=5, settings={"env": {}, "hooks": extra})
    h3 = w.add("s3", used=1)
    wjson(h3 / "settings.local.json", {"hooks": HOOKS})
    code, out, _ = w.run(capsys)
    assert out["instance"] == "s1"
    r = refused(out)
    assert ("s2", "privacy:hooks:settings.json") in r
    assert ("s3", "privacy:hooks:settings.local.json") in r


def test_hooks_both_absent_equal(w, capsys):
    wjson(w.main / "settings.json", {"env": {}})
    over(w)
    w.add("s1", used=10, settings={"env": {}})
    code, out, _ = w.run(capsys)
    assert out["instance"] == "s1"


# 9 global
def test_process_env(w, capsys, monkeypatch):
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector")
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 50})
    w.add("s1", used=10)
    code, out, _ = w.run(capsys)
    assert code == 0 and out["instance"] == "claudeAgent"
    assert ("*", "privacy:process-env") in refused(out)
    w.usage[0]["5h"] = 95
    code, out, _ = w.run(capsys)
    assert code == 3 and out["instance"] is None


def test_launch_root_env(w, capsys):
    over(w)
    w.add("s1", used=10)
    wjson(w.launch / ".claude" / "settings.local.json", {"env": {"OTEL_LOGS_EXPORTER": "otlp"}})
    code, out, _ = w.run(capsys)
    assert code == 3
    assert ("*", "privacy:launch-root:settings.local.json:OTEL_LOGS_EXPORTER") in refused(out)


def test_launch_root_safe_env(w, capsys):
    over(w)
    w.add("s1", used=10)
    wjson(w.launch / ".claude" / "settings.json", {"env": {"ANTHROPIC_DEFAULT_HAIKU_MODEL": "h"}})
    code, out, _ = w.run(capsys)
    assert out["instance"] == "s1"


def test_launch_root_http_hook(w, capsys):
    over(w)
    w.add("s1", used=10)
    wjson(w.launch / ".claude" / "settings.json",
          {"hooks": {"UserPromptSubmit": [{"hooks": [{"type": "http", "url": "https://x"}]}]}})
    code, out, _ = w.run(capsys)
    assert code == 3 and out["instance"] is None
    assert ("*", "privacy:http-hook:.claude/settings.json") in refused(out)
    assert not any(r["instance"] == "s1" for r in out["refused"])


def test_launch_root_hooks_differ(w, capsys):
    over(w)
    w.add("s1", used=10)
    wjson(w.launch / ".claude" / "settings.json",
          {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "x"}]}]}})
    code, out, _ = w.run(capsys)
    assert code == 3 and ("*", "privacy:launch-root-hooks:settings.json") in refused(out)


def test_launch_root_that_is_main_home_passes(w, capsys):
    # main home settings.local.json has hooks main's settings.json does not; the
    # launch root's .claude IS the main home, so its hooks compare equal to themselves.
    wjson(w.main / "settings.local.json", {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "y"}]}]}})
    over(w)
    w.add("s1", used=10, settings=SAFE_SETTINGS)
    wjson(w.slots / "s1" / "settings.local.json",
          {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "y"}]}]}})
    w.launch = w.main.parent
    code, out, _ = w.run(capsys)
    assert out["instance"] == "s1"


def test_launch_root_hooks_equal(w, capsys):
    over(w)
    w.add("s1", used=10)
    wjson(w.launch / ".claude" / "settings.json", {"hooks": HOOKS})
    code, out, _ = w.run(capsys)
    assert out["instance"] == "s1"


def test_candidate_http_hook_equal_to_main(w, capsys):
    http = {"Stop": [{"hooks": [{"type": "http", "url": "https://x"}]}]}
    wjson(w.main / "settings.json", {"hooks": http})
    over(w)
    w.add("s1", used=10, settings={"hooks": http})
    code, out, _ = w.run(capsys)
    assert code == 3 and ("s1", "privacy:http-hook:settings.json") in refused(out)


# 10 limits
@pytest.mark.parametrize("until,reason", [
    ("2026-11-22T12:00:01+00:00", "limited"),
    ("2026-11-22T12:00:00+00:00", None),
    ("2026-11-22T11:59:59+00:00", None),
    ("2026-11-22T12:00:01Z", "limited"),
    ("2026-11-22T12:00:00Z", None),
    ("2026-11-22T20:00:00+08:00", None),
    ("2026-11-22T20:00:01+08:00", "limited"),
    ("2026-11-22T12:00:01", "limits:malformed"),
    ("not a date", "limits:malformed"),
    (12345, "limits:malformed"),
])
def test_limits(w, capsys, until, reason):
    over(w)
    w.add("s1", used=10)
    w.limits = {"s1": until}
    code, out, _ = w.run(capsys)
    if reason:
        assert code == 3 and ("s1", reason) in refused(out)
    else:
        assert out["instance"] == "s1"


def test_limits_current(w, capsys):
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 10})
    w.add("s1", used=50)
    w.limits = {"claudeAgent": "2026-11-23T00:00:00Z"}
    code, out, _ = w.run(capsys)
    assert out["instance"] == "s1" and out["current_verified"] is True


def test_limits_file_invalid_fails_closed(w, capsys):
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 10})
    w.add("s1", used=50)
    w.write()
    (w.slots / "limits.json").write_text("{bad", encoding="utf-8")
    code, out, _ = w.run(capsys, write=False)
    assert code == 3 and ("s1", "limits:malformed") in refused(out)


@pytest.mark.parametrize("now", ["2026-11-22T12:00:00", "yesterday"])
def test_bad_now(w, capsys, now):
    w.write()
    argv = w.argv() + ["--now", now]
    assert pick.main(argv) == 2
    cap = capsys.readouterr()
    assert "--now" in cap.err and len(cap.err.strip().splitlines()) == 1


# 11 ranking
@pytest.mark.parametrize("useds,expected", [
    ([None, 40, 40, 20], "c4"),
    ([None, 40, 40], "c2"),
    ([None, None], "c1"),
    ([70, 30, None], "c2"),
])
def test_ranking(w, capsys, useds, expected):
    over(w)
    for i, u in enumerate(useds, 1):
        w.add(f"c{i}", used=u)
    code, out, _ = w.run(capsys)
    assert code == 0 and out["instance"] == expected and out["reason"] == "overflow"
    assert out["used"] == useds[int(expected[1:]) - 1]


# 12 --only
def test_only(w, capsys):
    over(w)
    w.add("c1", used=10)
    w.add("c2", used=30)
    w.add("c3", used=20)
    code, out, _ = w.run(capsys, extra=("--only", "c2, c3"))
    assert out["instance"] == "c3"
    code, out, _ = w.run(capsys, extra=("--only", "nope"))
    assert code == 3 and out["instance"] is None


def test_only_does_not_affect_current(w, capsys):
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 10})
    w.add("c1", used=10)
    code, out, _ = w.run(capsys, extra=("--only", "c1"))
    assert out["instance"] == "claudeAgent"


# 13 mapping / identity
def test_default_main_home_sibling_account(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    main = tmp_path / ".claude"
    main.mkdir()
    wjson(main / "settings.json", SAFE_SETTINGS)
    # sibling ~/.claude.json holds the account; ~/.claude/.claude.json is a decoy
    wjson(tmp_path / ".claude.json", {"oauthAccount": {
        "emailAddress": "me@example.test", "organizationType": "claude_max", "hasExtraUsageEnabled": False}})
    wjson(main / ".claude.json", {"oauthAccount": {"emailAddress": "decoy@example.test"}})
    t3 = tmp_path / "t3.json"
    wjson(t3, {"providerInstances": {"claudeAgent": {"driver": "claudeAgent", "enabled": True}}})
    slots = tmp_path / "slots"
    wjson(slots / "rotation.json", {"order": [{"instanceId": "claudeAgent", "email": "ME@example.test"}]})
    usage = tmp_path / "u.json"
    wjson(usage, [])
    code = pick.main(["--current", "claudeAgent", "--usage-json", str(usage), "--slots-dir", str(slots),
                      "--t3-settings", str(t3), "--launch-root", str(tmp_path / "nowhere"), "--json"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["instance"] == "claudeAgent" and out["current_verified"] is True


def test_explicit_main_home_uses_inner_account(w, capsys):
    w.add("s1", used=10)
    code, out, _ = w.run(capsys)
    assert out["current_verified"] is True  # World writes <main-home>/.claude.json


def test_mapping_no_home(w, capsys):
    over(w)
    w.add("d1", used=1, enabled=False)
    w.add("a1", used=1, in_t3=False)
    w.add("x1", used=1)
    w.instances["x1"]["driver"] = "codex"
    w.add("g1", used=1)
    w.instances["g1"]["config"]["homePath"] = str(w.root / "gone")
    w.add("m1", used=1, rot_email="someone-else@example.test")
    w.add("ok", used=50)
    code, out, _ = w.run(capsys)
    assert out["instance"] == "ok"
    r = refused(out)
    for iid in ("d1", "a1", "x1", "g1"):
        assert (iid, "no-home") in r
    assert ("m1", "identity-mismatch") in r


def test_absent_from_rotation_is_mismatch(w, capsys):
    over(w)
    w.add("s1", used=10)
    w.order = [o for o in w.order if o["instanceId"] != "claudeAgent"]
    code, out, _ = w.run(capsys)
    assert out["instance"] == "s1" and out["current_verified"] is False


def test_unreadable_account(w, capsys):
    over(w)
    home = w.add("s1", used=10)
    w.add("s2", used=20)
    (home / ".claude.json").write_text("{bad", encoding="utf-8")
    code, out, _ = w.run(capsys)
    assert out["instance"] == "s2" and ("s1", "unreadable:.claude.json") in refused(out)


# 14 current invalid
@pytest.mark.parametrize("break_it", ["disabled", "mismatch"])
def test_current_invalid(w, capsys, break_it):
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 5})
    if break_it == "disabled":
        w.instances["claudeAgent"]["enabled"] = False
    else:
        w.order[0]["email"] = "other@example.test"
    w.add("s1", used=50)
    code, out, _ = w.run(capsys)
    assert code == 0 and out["instance"] == "s1" and out["current_verified"] is False
    w.order = [o for o in w.order if o["instanceId"] != "s1"]
    code, out, _ = w.run(capsys)
    assert code == 3 and out["instance"] is None and out["current_verified"] is False


# 15 secrets
def tree_hash(root):
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        h.update(str(p.relative_to(root)).encode())
        if p.is_file():
            st = p.stat()
            h.update(p.read_bytes())
            h.update(str(st.st_mtime_ns).encode())
    return h.hexdigest()


def test_secrets_never_printed(w, capsys):
    marker = "SECRET-MARKER-9f3k"
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 99})
    for iid in ("s1", "s2"):
        home = w.add(iid, used=10 if iid == "s1" else 20,
                     settings={"env": {"ANTHROPIC_BASE_URL": marker} if iid == "s2" else {
                         "ANTHROPIC_DEFAULT_HAIKU_MODEL": marker}, "hooks": HOOKS})
        wjson(home / ".credentials.json", {"claudeAiOauth": {"accessToken": marker}})
        acct = json.loads((home / ".claude.json").read_text())
        acct["oauthAccount"]["fakeToken"] = marker
        wjson(home / ".claude.json", acct)
    wjson(w.main / ".credentials.json", {"claudeAiOauth": {"accessToken": marker}})
    w.write()
    before = tree_hash(w.root)
    emails = [o["email"].lower() for o in w.order]
    outputs = []
    for extra in ([], ["--json"]):
        assert pick.main(w.argv(extra=extra)) == 0
        cap = capsys.readouterr()
        outputs.append(cap.out + cap.err)
    # bad-input path too
    assert pick.main(w.argv(extra=["--now", marker])) == 2
    cap = capsys.readouterr()
    outputs.append(cap.out + cap.err)
    for text in outputs:
        low = text.lower()
        assert all(e not in low for e in emails)
        assert "@" not in text
    assert all(marker not in t for t in outputs)
    assert tree_hash(w.root) == before
    assert outputs[0].startswith("instance=s1 reason=overflow used=10 current_verified=true current_extra_usage=off")


def test_plain_output_none(w, capsys):
    over(w)
    w.write()
    assert pick.main(w.argv()) == 3
    out = capsys.readouterr().out.strip()
    assert out == ("instance=none reason=none-usable used=unknown current_verified=true current_extra_usage=off"
                   " current_reason=near-limit")


# 16 exit 2
def test_exit2_missing_usage_flag(w, capsys):
    w.write()
    argv = [a for a in w.argv() if a not in ("--usage-json", str(w.usage_file))]
    assert pick.main(argv) == 2
    assert len(capsys.readouterr().err.strip().splitlines()) == 1


@pytest.mark.parametrize("what", ["usage-missing", "usage-not-list", "usage-bad-json", "rotation", "t3", "t3-no-instances"])
def test_exit2_inputs(w, capsys, what):
    w.write()
    if what == "usage-missing":
        w.usage_file.unlink()
    elif what == "usage-not-list":
        wjson(w.usage_file, {"a": 1})
    elif what == "usage-bad-json":
        w.usage_file.write_text("[", encoding="utf-8")
    elif what == "rotation":
        (w.slots / "rotation.json").unlink()
    elif what == "t3":
        w.t3.unlink()
    else:
        wjson(w.t3, {"x": 1})
    assert pick.main(w.argv()) == 2
    cap = capsys.readouterr()
    assert cap.out == "" and len(cap.err.strip().splitlines()) == 1


# ---- fix round 1 (S1-S14) regressions ------------------------------------------------------
MARK = "MARKER-7q2z"


# S1 organizationType: type-checked, never echoed, no crash on unhashable values
@pytest.mark.parametrize("org,reason", [
    ("claude_max", None),
    ("claude_pro", None),
    ("claude_team", "money:team-unknown"),  # F4: passes check 3; no usage `extra` -> Team money rule
    ("claude_enterprise", "org:enterprise"),
    ("Big-Enterprise-" + MARK, "org:enterprise"),
    ("weird " + MARK, "org:unknown"),
    ("", "org:unknown"),
    (["claude_max"], "org:unknown"),
    ({"claude_max": 1}, "org:unknown"),
    (5, "org:unknown"),
    (True, "org:unknown"),
    ("NULL", "org:missing"),
    ("ABSENT", "org:missing"),
])
def test_org_types(w, capsys, org, reason):
    over(w)
    if org == "ABSENT":
        w.add("s1", org=None, used=10)
    else:
        home = w.add("s1", used=10)
        acct = json.loads((home / ".claude.json").read_text())
        acct["oauthAccount"]["organizationType"] = None if org == "NULL" else org
        wjson(home / ".claude.json", acct)
    w.write()
    code = pick.main(w.argv(extra=["--json"]))
    cap = capsys.readouterr()
    out = json.loads(cap.out)
    assert MARK not in cap.out + cap.err
    if reason is None:
        assert code == 0 and out["instance"] == "s1"
    else:
        assert code == 3 and ("s1", reason) in refused(out)


# S2 argparse errors never echo the offending value
@pytest.mark.parametrize("bad", [["--threshold", MARK], [MARK], ["--bogus-" + MARK]])
def test_argparse_errors_value_free(w, capsys, bad):
    w.write()
    assert pick.main(w.argv() + bad) == 2
    cap = capsys.readouterr()
    assert cap.out == "" and MARK not in cap.err and len(cap.err.strip().splitlines()) == 1
    if bad[0] == "--threshold":
        assert "--threshold" in cap.err
    else:
        assert "unrecognized argument" in cap.err


def test_argparse_missing_flag_named(w, capsys):
    assert pick.main(["--usage-json", str(w.usage_file)]) == 2
    err = capsys.readouterr().err
    assert "--current" in err and len(err.strip().splitlines()) == 1


# S3 / E1 built-in claudeAgent uses --main-home; ANY config.homePath key -> no-home:envelope
@pytest.mark.parametrize("hp", ["", "   ", 5, None, ["x"], "NONEXISTENT", "MAIN"])
def test_builtin_homepath_present_but_bad(w, capsys, hp):
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 5})
    hp = {"NONEXISTENT": str(w.root / "gone"), "MAIN": str(w.main)}.get(hp, hp) if isinstance(hp, str) else hp
    w.instances["claudeAgent"]["config"] = {"homePath": hp}
    w.add("s1", used=50)
    code, out, _ = w.run(capsys)
    assert code == 0 and out["instance"] == "s1" and out["current_verified"] is False
    assert ("claudeAgent", "no-home:envelope") in refused(out) and out["current_reason"] == "no-home:envelope"


def test_builtin_config_without_homepath_uses_main(w, capsys):
    w.instances["claudeAgent"]["config"] = {"setupMode": "x"}
    code, out, _ = w.run(capsys)
    assert out["instance"] == "claudeAgent" and out["current_verified"] is True


# S4 hooks equality is JSON-aware (true != 1)
def test_hooks_true_vs_one_candidate(w, capsys):
    wjson(w.main / "settings.json", {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "x", "async": 1}]}]}})
    over(w)
    w.add("s1", used=10, settings={"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "x", "async": True}]}]}})
    code, out, _ = w.run(capsys)
    assert code == 3 and ("s1", "privacy:hooks:settings.json") in refused(out)


def test_hooks_true_vs_one_launch_root(w, capsys):
    wjson(w.main / "settings.json", {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "x", "async": 1}]}]}})
    over(w)
    w.add("s1", used=10, settings={"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "x", "async": 1}]}]}})
    wjson(w.launch / ".claude" / "settings.json",
          {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "x", "async": True}]}]}})
    code, out, _ = w.run(capsys)
    assert code == 3 and ("*", "privacy:launch-root-hooks:settings.json") in refused(out)


# S5 rotation.json order entries are validated
@pytest.mark.parametrize("entry", [
    "s1", 5, None, {"email": "x@y.test"}, {"instanceId": "", "email": "x@y.test"},
    {"instanceId": 7, "email": "x@y.test"}, {"instanceId": "s9"}, {"instanceId": "s9", "email": 3},
])
def test_rotation_bad_entry_exit2(w, capsys, entry):
    w.order.append(entry)
    w.write()
    assert pick.main(w.argv()) == 2
    cap = capsys.readouterr()
    assert cap.out == "" and len(cap.err.strip().splitlines()) == 1 and "rotation.json" in cap.err
    assert "@" not in cap.err


# S6 overflow-safe times, finite usage windows, NaN/Infinity rejected
def test_limits_overflow_candidate(w, capsys):
    over(w)
    w.add("s1", used=10)
    w.limits = {"s1": "0001-01-01T00:00:00+01:00"}
    code, out, _ = w.run(capsys)
    assert code == 3 and ("s1", "limits:malformed") in refused(out)


def test_limits_overflow_current(w, capsys):
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 10})
    w.add("s1", used=50)
    w.limits = {"claudeAgent": "9999-12-31T23:59:59-01:00"}
    code, out, _ = w.run(capsys)
    assert out["instance"] == "s1" and out["current_reason"] == "limits:malformed"


def test_now_overflow_exit2(w, capsys):
    w.write()
    assert pick.main(w.argv() + ["--now", "0001-01-01T00:00:00+01:00"]) == 2
    cap = capsys.readouterr()
    assert "--now" in cap.err and len(cap.err.strip().splitlines()) == 1


@pytest.mark.parametrize("text", ['[{"email":"claudeagent@example.test","5h":NaN}]',
                                  '[{"email":"claudeagent@example.test","5h":Infinity}]',
                                  '[{"email":"claudeagent@example.test","5h":-Infinity}]'])
def test_usage_nan_infinity_exit2(w, capsys, text):
    w.write()
    w.usage_file.write_text(text, encoding="utf-8")
    assert pick.main(w.argv()) == 2
    cap = capsys.readouterr()
    assert "--usage-json" in cap.err and len(cap.err.strip().splitlines()) == 1


# P5 (fix round 2): one invalid window makes the whole row unknown, never the max of the valid ones
@pytest.mark.parametrize("val", ["1e400", "-1", "1001", "1e9", "true", "false", "%d" % (10 ** 400),
                                 '"40"', "[40]", "{}"])
@pytest.mark.parametrize("slot", ["5h", "week"])
def test_usage_invalid_window_makes_row_unknown(w, capsys, val, slot):
    other = "week" if slot == "5h" else "5h"
    w.write()
    w.usage_file.write_text('[{"email":"claudeagent@example.test","%s":%s,"%s":95}]' % (slot, val, other),
                            encoding="utf-8")
    code = pick.main(w.argv(extra=["--json"]))
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["used"] is None and out["reason"] == "current-unknown"


def test_usage_null_window_is_absent(w, capsys):
    w.write()
    w.usage_file.write_text('[{"email":"claudeagent@example.test","5h":null,"week":40}]', encoding="utf-8")
    code = pick.main(w.argv(extra=["--json"]))
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["used"] == 40 and out["reason"] == "current-ok"


def test_usage_window_only_bad_is_unknown(w, capsys):
    w.write()
    w.usage_file.write_text('[{"email":"claudeagent@example.test","5h":1e400}]', encoding="utf-8")
    code = pick.main(w.argv(extra=["--json"]))
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["used"] is None and out["reason"] == "current-unknown"


def test_settings_infinity_unreadable(w, capsys):
    over(w)
    home = w.add("s1", used=10)
    (home / "settings.local.json").write_text('{"x": Infinity}', encoding="utf-8")
    code, out, _ = w.run(capsys)
    assert code == 3 and ("s1", "privacy:unreadable:settings.local.json") in refused(out)


# S7 T3 instance launch settings (candidates only), right after no-home
@pytest.mark.parametrize("field,value,reason", [
    ("environment", [{"name": "ANTHROPIC_BASE_URL", "value": "https://relay", "sensitive": False}],
     "privacy:t3-instance:environment"),
    ("environment", {"OTEL_EXPORTER_OTLP_ENDPOINT": "https://c"}, "privacy:t3-instance:environment"),
    ("binaryPath", "C:/tools/claude-wrapper.cmd", "privacy:t3-instance:binaryPath"),
    ("launchArgs", "--settings C:/elsewhere/hooks.json", "privacy:t3-instance:launchArgs"),
    ("launchArgs", ["--settings", "x"], "privacy:t3-instance:launchArgs"),
    ("environment", [], None),
    ("environment", {}, None),
    ("binaryPath", "", None),
    ("launchArgs", [], None),
])
def test_t3_instance_launch_settings(w, capsys, field, value, reason):
    over(w)
    w.add("s1", used=10)
    if field == "environment":
        w.instances["s1"]["environment"] = value
    else:
        w.instances["s1"]["config"][field] = value
    code, out, _ = w.run(capsys)
    if reason is None:
        assert out["instance"] == "s1"
    else:
        assert code == 3 and ("s1", reason) in refused(out)


def test_t3_instance_check_before_identity(w, capsys):
    over(w)
    w.add("s1", used=10, rot_email="someone-else@example.test")
    w.instances["s1"]["config"]["binaryPath"] = "x.cmd"
    code, out, _ = w.run(capsys)
    assert ("s1", "privacy:t3-instance:binaryPath") in refused(out)


def test_t3_instance_not_applied_to_current(w, capsys):
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 10})
    w.instances["claudeAgent"]["environment"] = [{"name": "X", "value": "1"}]
    code, out, _ = w.run(capsys)
    assert out["instance"] == "claudeAgent" and out["reason"] == "current-ok"


# S8 filesystem probes fail closed
def test_fs_probe_home_resolve_raises(w, capsys, monkeypatch):
    over(w)
    home = w.add("s1", used=10)
    w.add("s2", used=20)
    real = pick.Path.resolve

    def boom(self, *a, **k):
        if self == home:
            raise PermissionError("probe")
        return real(self, *a, **k)
    monkeypatch.setattr(pick.Path, "resolve", boom)
    code, out, _ = w.run(capsys)
    # G1 (changed in fix 5): s1's home cannot be compared with s2's, so s2 counts as a duplicate
    assert code == 3 and ("s1", "no-home") in refused(out) and ("s2", "no-home:duplicate") in refused(out)


def test_fs_probe_exists_raises(w, capsys, monkeypatch):
    over(w)
    home = w.add("s1", used=10)
    real = pick.Path.lstat

    def boom(self, *a, **k):
        if self == home / "remote-settings.json":
            raise ValueError("probe")
        return real(self, *a, **k)
    monkeypatch.setattr(pick.Path, "lstat", boom)
    code, out, _ = w.run(capsys)
    assert code == 3 and ("s1", "privacy:remote-settings.json") in refused(out)


def test_fs_probe_read_raises_valueerror(w, capsys, monkeypatch):
    over(w)
    home = w.add("s1", used=10)
    real = pick.Path.read_text

    def boom(self, *a, **k):
        if self == home / "settings.json":
            raise ValueError("probe")
        return real(self, *a, **k)
    monkeypatch.setattr(pick.Path, "read_text", boom)
    code, out, _ = w.run(capsys)
    assert code == 3 and ("s1", "privacy:unreadable:settings.json") in refused(out)


def test_fs_probe_resolve_raises(monkeypatch, tmp_path):
    def boom(self, *a, **k):
        raise RuntimeError("loop")
    monkeypatch.setattr(pick.Path, "resolve", boom)
    assert pick.same_dir(tmp_path, tmp_path) is None


# S9 env key names echoed only when they look like env names
@pytest.mark.parametrize("key,reason_tail", [
    ("OTEL_MARKER 7q2z", "OTEL_*"),
    ("OTEL_" + "A" * 70, "OTEL_*"),
    ("otel_ok_name", "otel_ok_name"),
    ("OTEL_LOG_USER_PROMPTS", "OTEL_LOG_USER_PROMPTS"),
    ("HTTP\u017f_PROXY", "env"),  # long s upper-cases to S: gated, but not an ASCII env name
])
def test_env_key_echo_sanitised(w, capsys, key, reason_tail):
    over(w)
    home = w.add("s1", used=10)
    wjson(home / "settings.local.json", {"env": {key: "1"}})
    wjson(w.launch / ".claude" / "settings.local.json", {"env": {key: "1"}})
    w.write()
    pick.main(w.argv(extra=["--json"]))
    cap = capsys.readouterr()
    out = json.loads(cap.out)
    assert "7q2z" not in cap.out and "A" * 70 not in cap.out and "\u017f" not in cap.out
    assert ("*", f"privacy:launch-root:settings.local.json:{reason_tail}") in refused(out)


def test_safe_env_name():
    assert pick.safe_env_name("OTEL_\n" + MARK) == "OTEL_*"
    assert pick.safe_env_name("HTTP\u017f_PROXY") == "env"
    assert pick.safe_env_name("HTTPS_PROXY") == "HTTPS_PROXY"


# S11 every path flag gets expanduser
def test_path_flags_expanduser(tmp_path, capsys, monkeypatch):
    w = World(tmp_path)
    w.write()
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    argv = w.argv(extra=["--json"])
    argv[argv.index("--usage-json") + 1] = "~/usage.json"
    argv[argv.index("--t3-settings") + 1] = "~/t3/settings.json"
    argv[argv.index("--slots-dir") + 1] = "~/slots"
    argv[argv.index("--main-home") + 1] = "~/main/.claude"
    argv[argv.index("--launch-root") + 1] = "~/proj"
    argv[argv.index("--t3-runtime") + 1] = "~/t3/server-runtime.json"
    assert pick.main(argv) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["current_verified"] is True and ("*", "privacy:t3-policy") not in refused(out)


# S12 current_reason
def test_current_reason_values(w, capsys):
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 10})
    w.add("s1", used=50)
    code, out, _ = w.run(capsys)
    assert out["current_reason"] == "current-ok"
    w.usage[0]["5h"] = 95
    code, out, _ = w.run(capsys)
    assert out["instance"] == "s1" and out["current_reason"] == "near-limit"
    w.usage[0]["5h"] = 10
    w.limits = {"claudeAgent": "2026-11-23T00:00:00Z"}
    code, out, _ = w.run(capsys)
    assert out["current_reason"] == "limited"
    w.limits = {}
    w.order[0]["email"] = "other@example.test"
    code, out, _ = w.run(capsys)
    assert out["current_reason"] == "identity-mismatch"
    w.order[0]["email"] = "claudeagent@example.test"
    w.instances["claudeAgent"]["enabled"] = False
    code, out, _ = w.run(capsys)
    assert out["current_reason"] == "no-home"


def test_current_reason_unknown_and_money(w, capsys):
    code, out, _ = w.run(capsys)
    assert out["current_reason"] == "current-unknown"
    wjson(w.main / ".claude.json", {"oauthAccount": {"emailAddress": "claudeagent@example.test",
                                                     "hasExtraUsageEnabled": True}})
    code, out, _ = w.run(capsys)
    assert out["current_reason"] == "money:extra-usage"
    (w.main / ".claude.json").write_text("{bad", encoding="utf-8")
    code, out, _ = w.run(capsys)
    assert out["current_reason"] == "unreadable:.claude.json"


def test_current_reason_plain_line(w, capsys):
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 10})
    w.write()
    assert pick.main(w.argv()) == 0
    assert capsys.readouterr().out.strip() == (
        "instance=claudeAgent reason=current-ok used=10 current_verified=true current_extra_usage=off"
        " current_reason=current-ok")


# S13 catch-all: one fixed line, no traceback, no value
def test_internal_error_catch_all(w, capsys, monkeypatch):
    over(w)
    w.add("s1", used=10)
    w.write()

    def boom(*a, **k):
        raise KeyError(MARK)
    monkeypatch.setattr(pick.Ctx, "check_org", staticmethod(boom))
    assert pick.main(w.argv(extra=["--json"])) == 2
    cap = capsys.readouterr()
    assert cap.out == "" and cap.err.strip() == "t3-pick-login: internal error (KeyError)"


# ---- fix round 2 (P1-P6) regressions -------------------------------------------------------
def make_ctx(w):
    w.write()
    return pick.Ctx(pick.build_parser().parse_args(w.argv()), NOW)


# P1 T3 managed policy = presence, not content (file, registry key, running server's managedPolicy)
@pytest.mark.parametrize("content", [
    "{}", "", "  \n", "{not json", "DIR",
    json.dumps({"organization": "Org", "limits": {"telemetry": False}}),
    json.dumps({"limits": {"providers": {"instances": {"codex": {"binaryPath": "x.cmd"}}}}}),
    json.dumps({"limits": {"providers": {"instances": {"claudeAgent": {"locked": True, "environment": []}}}}}),
])
def test_t3_policy_file_presence(w, capsys, monkeypatch, content):
    over(w)
    w.add("s1", used=10)
    policy = w.root / "policy.json"
    if content == "DIR":
        policy.mkdir()
    else:
        policy.write_text(content, encoding="utf-8")
    monkeypatch.setattr(pick, "T3_POLICY_FILE", str(policy))
    code, out, _ = w.run(capsys)
    assert code == 3 and ("*", "privacy:t3-policy") in refused(out)
    assert not any(r["instance"] == "s1" for r in out["refused"])


def test_t3_policy_file_probe_fails(w, capsys, monkeypatch):
    over(w)
    w.add("s1", used=10)
    policy = w.root / "nowhere" / "policy.json"
    monkeypatch.setattr(pick, "T3_POLICY_FILE", str(policy))
    real = pick.Path.lstat

    def boom(self, *a, **k):
        if str(self) == str(policy):
            raise PermissionError("probe")
        return real(self, *a, **k)
    monkeypatch.setattr(pick.Path, "lstat", boom)
    code, out, _ = w.run(capsys)
    assert code == 3 and ("*", "privacy:t3-policy") in refused(out)


def test_t3_policy_absent_passes(w, capsys):
    over(w)
    w.add("s1", used=10)
    code, out, _ = w.run(capsys)
    assert code == 0 and out["instance"] == "s1" and ("*", "privacy:t3-policy") not in refused(out)


def test_t3_policy_registry_presence(w, capsys, monkeypatch):
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 10})
    w.add("s1", used=10)
    monkeypatch.setattr(pick, "registry_policy_present", lambda: True)
    code, out, _ = w.run(capsys)
    assert out["instance"] == "claudeAgent" and ("*", "privacy:t3-policy") in refused(out)


class FakeWinreg:
    HKEY_LOCAL_MACHINE = "HKLM"
    HKEY_CURRENT_USER = "HKCU"
    KEY_READ = 1
    KEY_WOW64_64KEY = 256
    KEY_WOW64_32KEY = 512

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.opened = []
        self.closed = 0

    def OpenKey(self, root, sub, reserved=0, access=1):
        self.opened.append((root, sub, access))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    def CloseKey(self, key):
        self.closed += 1


@pytest.mark.parametrize("outcomes,present", [
    ([FileNotFoundError(), FileNotFoundError()], False),
    (["key"], True),
    ([FileNotFoundError(), "key"], True),
    ([PermissionError()], True),
    ([FileNotFoundError(), OSError("x")], True),
])
def test_registry_policy_present(monkeypatch, outcomes, present):
    fake = FakeWinreg(outcomes)
    monkeypatch.setitem(sys.modules, "winreg", fake)
    monkeypatch.setattr(pick.sys, "platform", "win32")
    assert REAL_REGISTRY_PRESENT() is present
    assert all(o[0] == "HKLM" and o[1] == r"SOFTWARE\Policies\T3Tools\T3Code" for o in fake.opened)
    assert fake.closed == sum(1 for o in outcomes[:len(fake.opened)] if o == "key")


def test_registry_policy_off_windows(monkeypatch):
    monkeypatch.setattr(pick.sys, "platform", "linux")
    assert REAL_REGISTRY_PRESENT() is False


@pytest.mark.parametrize("runtime", [
    "ABSENT", "{bad", "[1]", '"x"', "null", '{"managedPolicy": NaN}',
    {"pid": 1}, {"managedPolicy": {}}, {"managedPolicy": {"organization": MARK}}, {"managedPolicy": False},
    {"managedPolicy": 0}, {"managedPolicy": ""}, {"managedPolicy": []},
])
def test_t3_runtime_managed_policy_blocks(w, capsys, runtime):
    over(w)
    w.add("s1", used=10)
    w.runtime_data = runtime
    code, out, err = w.run(capsys)
    assert code == 3 and ("*", "privacy:t3-policy") in refused(out)
    assert not any(r["instance"] == "s1" for r in out["refused"])
    assert MARK not in json.dumps(out) + err


def test_t3_runtime_null_passes_value_free(w, capsys):
    over(w)
    w.add("s1", used=10)
    w.runtime_data = {"managedPolicy": None, "authToken": MARK, "url": "http://u@" + MARK}
    code, out, err = w.run(capsys)
    assert code == 0 and out["instance"] == "s1"
    assert MARK not in json.dumps(out) + err and "@" not in json.dumps(out) + err


def test_t3_runtime_default_path(tmp_path, capsys, monkeypatch):
    w = World(tmp_path)
    over(w)
    w.add("s1", used=10)
    w.write()
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    argv = w.argv(extra=["--json"])
    i = argv.index("--t3-runtime")
    del argv[i:i + 2]
    assert pick.main(argv) == 3  # no ~/.t3/userdata/server-runtime.json yet -> fail closed
    assert ("*", "privacy:t3-policy") in refused(json.loads(capsys.readouterr().out))
    wjson(tmp_path / ".t3" / "userdata" / "server-runtime.json", {"managedPolicy": None})
    assert pick.main(argv) == 0
    assert json.loads(capsys.readouterr().out)["instance"] == "s1"


# P2 a non-built-in instance whose home resolves to the main home is ambiguous
def ambiguous_variants(w):
    yield str(w.main)
    yield str(w.main.parent / ".." / w.main.parent.name / ".claude")
    if sys.platform == "win32":
        yield str(w.main).upper()


@pytest.mark.parametrize("variant", [0, 1, 2])
def test_ambiguous_home_candidate(w, capsys, variant):
    hps = list(ambiguous_variants(w))
    if variant >= len(hps):
        pytest.skip("case-insensitive paths only on Windows")
    # current is limited; "dup" points at the main home and names main's account in rotation.json
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 10})
    w.limits = {"claudeAgent": "2026-11-23T00:00:00Z"}
    w.add("dup", rot_email="claudeagent@example.test")
    w.instances["dup"]["config"]["homePath"] = hps[variant]
    code, out, _ = w.run(capsys)
    assert code == 3 and out["instance"] is None and ("dup", "no-home:ambiguous") in refused(out)


def test_ambiguous_home_current(w, capsys):
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 10})
    w.add("dup", rot_email="claudeagent@example.test")
    w.instances["dup"]["config"]["homePath"] = str(w.main)
    w.add("s1", used=50)
    code, out, _ = w.run(capsys, current="dup")
    # F1a: the built-in (used 10) is never a candidate, so the slot is picked
    assert code == 0 and out["instance"] == "s1" and out["reason"] == "overflow" and out["used"] == 50
    assert ("claudeAgent", "no-home:builtin") in refused(out)
    assert out["current_reason"] == "no-home:ambiguous" and out["current_verified"] is False


def test_builtin_explicit_homepath_to_main_is_envelope(w, capsys):
    # E1: the explicit-built-in-homePath path is gone, even when it names the main home
    w.instances["claudeAgent"]["config"] = {"homePath": str(w.main)}
    code, out, _ = w.run(capsys)
    assert code == 3 and out["instance"] is None and out["current_verified"] is False
    assert out["current_reason"] == "no-home:envelope"


@pytest.mark.parametrize("hp", [str(Path.home()), "", None])
def test_builtin_homepath_candidate_envelope(w, capsys, hp):
    # E1 as a candidate, superseded by F1a: the built-in is never a candidate -> no-home:builtin
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 10})
    w.add("s1", used=99)
    w.instances["claudeAgent"]["config"] = {"homePath": hp}
    code, out, _ = w.run(capsys, current="s1")
    assert code == 3 and ("claudeAgent", "no-home:builtin") in refused(out)


def test_resolve_failure_fails_closed(w, capsys, monkeypatch):
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 10})
    w.add("s1", used=50)
    w.write()
    real = pick.Path.resolve

    def boom(self, *a, **k):
        if self == w.launch:  # F2b: the launch root must resolve (covered by its own tests)
            return real(self, *a, **k)
        raise RuntimeError("loop")
    monkeypatch.setattr(pick.Path, "resolve", boom)
    code, out, _ = w.run(capsys, write=False)
    assert code == 3 and out["current_reason"] == "no-home" and out["current_verified"] is False
    assert ("s1", "no-home") in refused(out)


def test_default_main_undecidable_fails_closed(w, capsys, monkeypatch):
    # whether the built-in reads the sibling ~/.claude.json cannot be decided -> no-home (current too)
    fake_home = w.root / "userhome"
    (fake_home / ".claude").mkdir(parents=True)
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    monkeypatch.setenv("HOME", str(fake_home))
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 10})
    w.add("s1", used=50)
    w.write()
    default_main = pick.Path.home() / ".claude"
    real = pick.Path.resolve

    def boom(self, *a, **k):
        if self == default_main:
            raise OSError("probe")
        return real(self, *a, **k)
    monkeypatch.setattr(pick.Path, "resolve", boom)
    code, out, _ = w.run(capsys, write=False)
    assert code == 0 and out["instance"] == "s1"
    assert out["current_reason"] == "no-home" and out["current_verified"] is False


# P3 instance ids are validated; T3 keys that fail the pattern are ignored
@pytest.mark.parametrize("bad", ["a@b.test", "s 1", "s1\n", "_s1", "x" * 65, "", "sé1", "s1/x", MARK + "."])
def test_current_invalid_id_exit2(w, capsys, bad):
    w.write()
    assert pick.main(w.argv(current=bad, extra=["--json"])) == 2
    cap = capsys.readouterr()
    assert cap.out == "" and cap.err.strip() == "t3-pick-login: bad input: --current: invalid instance id"


@pytest.mark.parametrize("iid", ["a@b.test", "s 1", "s1\n", "-s1", "_s1", "x" * 65, "sé1", MARK + "."])
def test_rotation_invalid_instance_id_exit2(w, capsys, iid):
    w.order.append({"instanceId": iid, "email": "x@y.test"})
    w.write()
    assert pick.main(w.argv()) == 2
    cap = capsys.readouterr()
    assert cap.out == "" and cap.err.strip() == (
        "t3-pick-login: bad input: rotation.json order entry has an invalid instanceId")


@pytest.mark.parametrize("iid", ["x" * 64, "A-b_9", "9", "claude-max-2"])
def test_valid_instance_ids_accepted(w, capsys, iid):
    over(w)
    w.add(iid, used=10)
    code, out, _ = w.run(capsys)
    assert code == 0 and out["instance"] == iid


def test_t3_invalid_keys_ignored(w, capsys):
    over(w)
    w.add("s1", used=10)
    w.instances["bad key@" + MARK] = {"driver": "claudeAgent", "enabled": True,
                                      "config": {"homePath": str(w.slots / "s1")}}
    w.instances["-x"] = {"driver": "claudeAgent", "enabled": True}
    assert set(make_ctx(w).instances) == {"claudeAgent", "s1"}
    code, out, err = w.run(capsys)
    text = json.dumps(out) + err
    assert code == 0 and out["instance"] == "s1" and MARK not in text and "@" not in text


# P4 newly gated variables (settings env and the picker's own process env)
NEW_GATED = ("CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR",
             "CLAUDE_CODE_API_KEY_FILE_DESCRIPTOR", "ANTHROPIC_CUSTOM_HEADERS", "CLAUDE_CONFIG_DIR")


@pytest.mark.parametrize("name", NEW_GATED)
def test_new_gated_env_settings(w, capsys, name):
    over(w)
    home = w.add("s1", used=10)
    w.add("s2", used=20)
    wjson(home / "settings.local.json", {"env": {name: MARK}})
    code, out, err = w.run(capsys)
    assert code == 0 and out["instance"] == "s2"
    assert ("s1", f"privacy:settings.local.json:{name}") in refused(out)
    assert MARK not in json.dumps(out) + err


@pytest.mark.parametrize("name", NEW_GATED)
def test_new_gated_env_launch_root(w, capsys, name):
    over(w)
    w.add("s1", used=10)
    wjson(w.launch / ".claude" / "settings.json", {"env": {name: MARK}})
    code, out, _ = w.run(capsys)
    assert code == 3 and ("*", f"privacy:launch-root:settings.json:{name}") in refused(out)


@pytest.mark.parametrize("name", NEW_GATED)
def test_new_gated_env_process(w, capsys, monkeypatch, name):
    monkeypatch.setenv(name, MARK)
    over(w)
    w.add("s1", used=10)
    code, out, err = w.run(capsys)
    assert code == 3 and ("*", "privacy:process-env") in refused(out) and MARK not in json.dumps(out) + err


# P6 check_t3_instance: an entry that is not an object, or a present config that is not one
def test_t3_instance_config_null_candidate(w, capsys):
    # current is a slot near its limit; F1a: the built-in with config: null is refused before any
    # instance check, and a slot with config: null has no homePath (privacy:t3-instance:config
    # stays covered by test_check_t3_instance_shapes)
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 10})
    w.add("s1", used=99)
    w.add("s2", used=10)
    w.instances["claudeAgent"]["config"] = None
    w.instances["s2"]["config"] = None
    code, out, _ = w.run(capsys, current="s1")
    assert code == 3 and ("claudeAgent", "no-home:builtin") in refused(out) and ("s2", "no-home") in refused(out)


@pytest.mark.parametrize("inst,reason", [
    ("weird", "privacy:t3-instance:config"),
    (["x"], "privacy:t3-instance:config"),
    (None, "privacy:t3-instance:config"),
    ({"driver": "claudeAgent", "config": None}, "privacy:t3-instance:config"),
    ({"driver": "claudeAgent", "config": ["x"]}, "privacy:t3-instance:config"),
    ({"driver": "claudeAgent", "config": "x"}, "privacy:t3-instance:config"),
    ({"driver": "claudeAgent"}, None),
    ({"driver": "claudeAgent", "config": {}}, None),
    ({"driver": "claudeAgent", "config": {"binaryPath": "x"}}, "privacy:t3-instance:binaryPath"),
])
def test_check_t3_instance_shapes(w, inst, reason):
    ctx = make_ctx(w)
    ctx.instances["x1"] = inst
    assert ctx.check_t3_instance("x1") == reason


# ---- fix round 3 (E1-E5) regressions -------------------------------------------------------
# E2 only FileNotFoundError / NotADirectoryError confirm absence; other probe errors fail closed
@pytest.mark.parametrize("exc,expected", [
    (FileNotFoundError, False), (NotADirectoryError, False),
    (PermissionError, None), (OSError, None), (ValueError, None),
])
def test_safe_exists_only_notfound_is_absent(monkeypatch, tmp_path, exc, expected):
    def boom(self, *a, **k):
        raise exc("probe")
    monkeypatch.setattr(pick.Path, "lstat", boom)
    assert pick.safe_exists(tmp_path / "x") is expected


def test_safe_exists_uses_lstat_dangling_link_present(tmp_path):
    link = tmp_path / "link"
    try:
        os.symlink(tmp_path / "gone", link)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not permitted here")
    assert pick.safe_exists(link) is True


@pytest.mark.parametrize("fname", ["remote-settings.json", "managed-settings.json"])
def test_privacy_file_probe_permission_error_fails_closed(w, capsys, monkeypatch, fname):
    over(w)
    home = w.add("s1", used=10)
    real = pick.Path.lstat

    def boom(self, *a, **k):
        if self == home / fname:
            raise PermissionError("probe")
        return real(self, *a, **k)
    monkeypatch.setattr(pick.Path, "lstat", boom)
    code, out, _ = w.run(capsys)
    assert code == 3 and ("s1", f"privacy:{fname}") in refused(out)


def test_read_json_not_a_directory_is_missing(tmp_path):
    f = tmp_path / "file"
    f.write_text("x", encoding="utf-8")
    assert pick.read_json(f / "child.json") is pick.MISSING
    (tmp_path / "d.json").mkdir()
    assert pick.read_json(tmp_path / "d.json") is pick.BAD


def test_home_must_be_a_directory(w, capsys):
    over(w)
    w.add("s1", used=10)
    w.add("s2", used=20)
    f = w.root / "afile"
    f.write_text("x", encoding="utf-8")
    w.instances["s1"]["config"]["homePath"] = str(f)
    code, out, _ = w.run(capsys)
    assert out["instance"] == "s2" and ("s1", "no-home") in refused(out)


def test_same_dir_strict(tmp_path):
    a = tmp_path / "a"
    a.mkdir()
    assert pick.same_dir(a, tmp_path / "a" / ".." / "a") is True
    assert pick.same_dir(a, tmp_path / "absent") is False   # one confirmed absent, the other exists
    assert pick.same_dir(tmp_path / "absent", tmp_path / "absent2") is None


def test_same_dir_undetermined_is_none(monkeypatch, tmp_path):
    a = tmp_path / "a"
    a.mkdir()
    real_resolve, real_lstat = pick.Path.resolve, pick.Path.lstat
    target = tmp_path / "b"

    def boom_resolve(self, *a_, **k):
        if self == target:
            raise PermissionError("probe")
        return real_resolve(self, *a_, **k)

    def boom_lstat(self, *a_, **k):
        if self == target:
            raise PermissionError("probe")
        return real_lstat(self, *a_, **k)
    monkeypatch.setattr(pick.Path, "resolve", boom_resolve)
    monkeypatch.setattr(pick.Path, "lstat", boom_lstat)
    assert pick.same_dir(a, target) is None


def test_absent_default_home_handled_explicitly(tmp_path, capsys, monkeypatch):
    # ~/.claude absent (lstat FileNotFoundError): the explicit --main-home reads its inner account
    w = World(tmp_path)
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "nohome"))
    monkeypatch.setenv("HOME", str(tmp_path / "nohome"))
    code, out, _ = w.run(capsys)
    assert code == 0 and out["instance"] == "claudeAgent" and out["current_verified"] is True


def test_resolve_is_strict(w, capsys, monkeypatch):
    calls = []
    real = pick.Path.resolve

    def spy(self, *a, **k):
        calls.append(k.get("strict", a[0] if a else False))
        return real(self, *a, **k)
    monkeypatch.setattr(pick.Path, "resolve", spy)
    over(w)
    w.add("s1", used=10)
    code, out, _ = w.run(capsys)
    assert code == 0 and out["instance"] == "s1" and calls and all(c is True for c in calls)


# E3 T3CODE_HOME in the picker's environment -> outside the envelope, every candidate refused
@pytest.mark.parametrize("value", ["C:/elsewhere", ""])
def test_t3code_home_refuses_all(w, capsys, monkeypatch, value):
    monkeypatch.setenv("T3CODE_HOME", value)
    over(w)
    w.add("s1", used=10)
    code, out, err = w.run(capsys)
    assert code == 3 and out["instance"] is None and ("*", "privacy:t3-home") in refused(out)
    assert not any(r["instance"] == "s1" for r in out["refused"]) and "elsewhere" not in json.dumps(out) + err


def test_t3code_home_does_not_touch_current(w, capsys, monkeypatch):
    monkeypatch.setenv("T3CODE_HOME", "x")
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 10})
    code, out, _ = w.run(capsys)
    assert code == 0 and out["reason"] == "current-ok" and ("*", "privacy:t3-home") in refused(out)


# E4 CLAUDE_CONFIG_DIR in the process env: exempt only when it is the current instance's located home
def test_config_dir_equal_to_current_home_exempt(w, capsys, monkeypatch):
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 50})
    w.add("s1", used=99)
    w.add("s2", used=20)
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(w.slots / "s1" / ".." / "s1"))
    code, out, _ = w.run(capsys, current="s1")
    assert code == 0 and out["instance"] == "s2" and out["reason"] == "overflow"
    assert ("*", "privacy:process-env") not in refused(out)


@pytest.mark.parametrize("which", ["other-slot", "main", "absent", "blank", "current-unlocated"])
def test_config_dir_other_value_gated(w, capsys, monkeypatch, which):
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 10})
    w.add("s1", used=99)
    w.add("s2", used=20)
    value = {"other-slot": str(w.slots / "s2"), "main": str(w.main), "absent": str(w.root / "gone"),
             "blank": "  ", "current-unlocated": str(w.slots / "s1")}[which]
    if which == "current-unlocated":
        w.instances["s1"]["enabled"] = False
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", value)
    code, out, _ = w.run(capsys, current="s1")
    assert code == 3 and ("*", "privacy:process-env") in refused(out)


def test_config_dir_undeterminable_gated(w, capsys, monkeypatch):
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 10})
    w.add("s1", used=99)
    w.add("s2", used=20)
    w.write()
    value = str(w.slots / "s1" / ".")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", value)
    real = pick.Path.resolve

    def boom(self, *a, **k):
        if str(self) == str(pick.Path(value)):
            raise PermissionError("probe")
        return real(self, *a, **k)
    monkeypatch.setattr(pick.Path, "resolve", boom)
    code, out, _ = w.run(capsys, current="s1", write=False)
    assert code == 3 and ("*", "privacy:process-env") in refused(out)


def test_config_dir_with_other_gated_name_still_gated(w, capsys, monkeypatch):
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 10})
    w.add("s1", used=99)
    w.add("s2", used=20)
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(w.slots / "s1"))
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", MARK)
    code, out, err = w.run(capsys, current="s1")
    assert code == 3 and ("*", "privacy:process-env") in refused(out) and MARK not in json.dumps(out) + err


def test_config_dir_in_settings_still_gated(w, capsys):
    # settings env (candidate or launch root) stays gated even when it names the home itself
    over(w)
    home = w.add("s1", used=10)
    w.add("s2", used=20)
    wjson(home / "settings.json", {**SAFE_SETTINGS, "env": {"CLAUDE_CONFIG_DIR": str(home)}})
    code, out, _ = w.run(capsys)
    assert out["instance"] == "s2" and ("s1", "privacy:settings.json:CLAUDE_CONFIG_DIR") in refused(out)
    wjson(w.launch / ".claude" / "settings.json", {"env": {"CLAUDE_CONFIG_DIR": str(w.main)}})
    code, out, _ = w.run(capsys)
    assert code == 3 and ("*", "privacy:launch-root:settings.json:CLAUDE_CONFIG_DIR") in refused(out)


# E5 a blank or non-string instanceId gets the pattern-failure message
@pytest.mark.parametrize("entry", [
    {"instanceId": "", "email": "x@y.test"}, {"instanceId": "   ", "email": "x@y.test"},
    {"instanceId": 7, "email": "x@y.test"}, {"instanceId": None, "email": "x@y.test"},
    {"instanceId": ["s1"], "email": "x@y.test"}, {"email": "x@y.test"},
])
def test_rotation_blank_or_nonstring_id_message(w, capsys, entry):
    w.order.append(entry)
    w.write()
    assert pick.main(w.argv()) == 2
    cap = capsys.readouterr()
    assert cap.out == "" and cap.err.strip() == (
        "t3-pick-login: bad input: rotation.json order entry has an invalid instanceId")


# ---- fix round 4 (F1-F4) regressions -------------------------------------------------------
# F1a the built-in claudeAgent is never an overflow candidate
def test_builtin_never_candidate(w, capsys):
    # the built-in is otherwise perfect: verified account, safe settings, lowest used
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 1, "week": 1})
    w.add("s1", used=99)
    w.add("s2", used=50)
    code, out, _ = w.run(capsys, current="s1")
    assert code == 0 and out["instance"] == "s2" and out["used"] == 50
    assert ("claudeAgent", "no-home:builtin") in refused(out)
    w.order = [o for o in w.order if o["instanceId"] != "s2"]
    code, out, _ = w.run(capsys, current="s1")
    assert code == 3 and out["instance"] is None and ("claudeAgent", "no-home:builtin") in refused(out)


def test_builtin_still_current(w, capsys):
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 10})
    code, out, _ = w.run(capsys)
    assert code == 0 and out["instance"] == "claudeAgent" and out["current_reason"] == "current-ok"
    assert not any(r["instance"] == "claudeAgent" for r in out["refused"])


# F1b built-in current + CLAUDE_CONFIG_DIR in the picker's env (any value) -> outside the envelope
@pytest.mark.parametrize("which", ["slot", "blank", "main"])
def test_builtin_current_config_dir_envelope(w, capsys, monkeypatch, which):
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 10})
    w.add("s1", used=20)
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", {"slot": str(w.slots / "s1"), "blank": "", "main": str(w.main)}[which])
    code, out, _ = w.run(capsys)
    assert code == 3 and out["instance"] is None
    assert out["current_verified"] is False and out["current_reason"] == "no-home:envelope"
    assert out["current_extra_usage"] == "unknown"
    assert ("*", "privacy:process-env") in refused(out) and ("claudeAgent", "no-home:envelope") in refused(out)
    assert not any(r["instance"] == "s1" for r in out["refused"])


def test_config_dir_never_exempt_for_builtin(w):
    ctx = make_ctx(w)
    assert ctx.config_dir_is_current(str(w.main), "claudeAgent") is False


# F2a --launch-root is required
def test_launch_root_required(w, capsys):
    w.write()
    argv = w.argv()
    i = argv.index("--launch-root")
    del argv[i:i + 2]
    assert pick.main(argv + ["--json"]) == 2
    cap = capsys.readouterr()
    assert cap.out == "" and cap.err.strip() == "t3-pick-login: bad input: missing required --launch-root"


# F2b the launch root must strict-resolve to an existing directory
@pytest.mark.parametrize("what", ["absent", "file", "blank", "relative"])
def test_launch_root_missing(w, capsys, what):
    over(w)
    w.add("s1", used=10)
    if what == "file":
        f = w.root / "afile"
        f.write_text("x", encoding="utf-8")
        w.launch = f
    else:
        w.launch = {"absent": w.root / "typo", "blank": "  ", "relative": "proj"}[what]
    code, out, _ = w.run(capsys)
    assert code == 3 and out["instance"] is None and ("*", "privacy:launch-root:missing") in refused(out)
    assert not any(r["instance"] == "s1" for r in out["refused"])


def test_launch_root_missing_does_not_touch_current(w, capsys):
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 10})
    w.launch = w.root / "typo"
    code, out, _ = w.run(capsys)
    assert code == 0 and out["reason"] == "current-ok" and ("*", "privacy:launch-root:missing") in refused(out)


def test_launch_root_resolve_error_is_missing(w, capsys, monkeypatch):
    over(w)
    w.add("s1", used=10)
    w.write()
    real = pick.Path.resolve

    def boom(self, *a, **k):
        if self == w.launch:
            raise PermissionError("probe")
        return real(self, *a, **k)
    monkeypatch.setattr(pick.Path, "resolve", boom)
    code, out, _ = w.run(capsys, write=False)
    assert code == 3 and ("*", "privacy:launch-root:missing") in refused(out)


# F3 Claude Code machine managed settings: presence, never content
def cc_world(monkeypatch, tmp_path, *, platform="win32", dirs=(), registry=False):
    a, b = tmp_path / "cc" / "Program Files" / "ClaudeCode", tmp_path / "cc" / "ProgramData" / "ClaudeCode"
    for d in dirs:
        {"pf": a, "pd": b}[d].mkdir(parents=True)
    monkeypatch.setattr(pick, "CC_MANAGED_DIRS", (str(a), str(b)))
    monkeypatch.setattr(pick, "cc_registry_present", lambda: registry)
    monkeypatch.setattr(pick, "cc_managed_present", REAL_CC_MANAGED_PRESENT)
    monkeypatch.setattr(pick.sys, "platform", platform)
    return a, b


@pytest.mark.parametrize("dirs,registry,present", [
    ((), False, False), (("pf",), False, True), (("pd",), False, True), ((), True, True),
    (("pf", "pd"), True, True),
])
def test_cc_managed_sources(w, capsys, monkeypatch, tmp_path, dirs, registry, present):
    over(w)
    w.add("s1", used=10)
    cc_world(monkeypatch, tmp_path, dirs=dirs, registry=registry)
    code, out, _ = w.run(capsys)
    if present:
        assert code == 3 and ("*", "privacy:cc-managed") in refused(out)
        assert not any(r["instance"] == "s1" for r in out["refused"])
    else:
        assert code == 0 and out["instance"] == "s1" and ("*", "privacy:cc-managed") not in refused(out)


def test_cc_managed_file_counts_as_present(monkeypatch, tmp_path):
    a, _ = cc_world(monkeypatch, tmp_path)
    a.parent.mkdir(parents=True)
    a.write_text("", encoding="utf-8")
    assert pick.cc_managed_present() is True


def test_cc_managed_dir_probe_error(w, capsys, monkeypatch, tmp_path):
    over(w)
    w.add("s1", used=10)
    a, _ = cc_world(monkeypatch, tmp_path)
    real = pick.Path.lstat

    def boom(self, *x, **k):
        if str(self) == str(a):
            raise PermissionError("probe")
        return real(self, *x, **k)
    monkeypatch.setattr(pick.Path, "lstat", boom)
    code, out, _ = w.run(capsys)
    assert code == 3 and ("*", "privacy:cc-managed") in refused(out)


def test_cc_managed_off_windows(w, capsys, monkeypatch, tmp_path):
    over(w)
    w.add("s1", used=10)
    cc_world(monkeypatch, tmp_path, platform="linux")
    assert pick.cc_managed_present() is True
    code, out, _ = w.run(capsys)
    assert code == 3 and ("*", "privacy:cc-managed") in refused(out)


CC_SUB = r"SOFTWARE\Policies\ClaudeCode"


@pytest.mark.parametrize("outcomes,present,probed", [
    ([FileNotFoundError(), FileNotFoundError(), FileNotFoundError()], False, 3),
    (["key"], True, 1),
    ([FileNotFoundError(), "key"], True, 2),
    ([FileNotFoundError(), FileNotFoundError(), "key"], True, 3),
    ([PermissionError()], True, 1),
    ([FileNotFoundError(), OSError("x")], True, 2),
    ([FileNotFoundError(), FileNotFoundError(), PermissionError()], True, 3),
])
def test_cc_registry_present(monkeypatch, outcomes, present, probed):
    fake = FakeWinreg(outcomes)
    monkeypatch.setitem(sys.modules, "winreg", fake)
    monkeypatch.setattr(pick.sys, "platform", "win32")
    assert REAL_CC_REGISTRY_PRESENT() is present
    assert len(fake.opened) == probed and all(o[1] == CC_SUB for o in fake.opened)
    expected_roots = [("HKLM", 1 | 256), ("HKLM", 1 | 512), ("HKCU", 1)][:probed]
    assert [(o[0], o[2]) for o in fake.opened] == expected_roots
    assert fake.closed == sum(1 for o in outcomes[:probed] if o == "key")


def test_cc_registry_off_windows(monkeypatch):
    monkeypatch.setattr(pick.sys, "platform", "linux")
    assert REAL_CC_REGISTRY_PRESENT() is True


def test_cc_registry_no_winreg(monkeypatch):
    monkeypatch.setitem(sys.modules, "winreg", None)  # import raises ImportError
    monkeypatch.setattr(pick.sys, "platform", "win32")
    assert REAL_CC_REGISTRY_PRESENT() is True


@pytest.mark.parametrize("name", ["CLAUDE_CODE_MANAGED_SETTINGS_PATH", "claude_code_managed_x", "CLAUDE_CODE_MANAGED"])
def test_cc_managed_env_gated(w, capsys, monkeypatch, name):
    assert pick.is_gated(name)
    over(w)
    home = w.add("s1", used=10)
    w.add("s2", used=20)
    wjson(home / "settings.local.json", {"env": {name: MARK}})
    code, out, err = w.run(capsys)
    assert out["instance"] == "s2" and ("s1", f"privacy:settings.local.json:{name}") in refused(out)
    assert MARK not in json.dumps(out) + err
    monkeypatch.setenv(name, MARK)
    code, out, err = w.run(capsys)
    assert code == 3 and ("*", "privacy:process-env") in refused(out) and MARK not in json.dumps(out) + err


# F4 Team premium seats: capped, under 90%, fresh usage, fresh empty org-settings cache
GOOD_EXTRA = {"enabled": True, "cap": 200.0, "spent": 20.0, "currency": "CAD", "cap_reached": False}
ABSENT = object()


def add_team(w, iid, *, used=10, week=0, extra=GOOD_EXTRA, remote="{}", remote_age=timedelta(hours=1), **kw):
    row = {}
    if used is not ABSENT:
        row["5h"] = used
    if week is not ABSENT:
        row["week"] = week
    if extra is not ABSENT:
        row["extra"] = extra
    home = w.add(iid, org="claude_team", extra=True, used=row, **kw)
    if remote is not None:
        (home / "remote-settings.json").write_text(remote, encoding="utf-8")
        set_mtime(home / "remote-settings.json", NOW - remote_age)
    return home


def with_extra(**changes):
    e = dict(GOOD_EXTRA)
    for k, v in changes.items():
        if v is ABSENT:
            e.pop(k, None)
        else:
            e[k] = v
    return e


def test_team_passes(w, capsys):
    over(w)
    add_team(w, "t1", used=30)
    code, out, _ = w.run(capsys)
    assert code == 0 and out["instance"] == "t1" and out["reason"] == "overflow" and out["used"] == 30


@pytest.mark.parametrize("extra,reason", [
    (ABSENT, "money:team-unknown"),
    (None, "money:team-unknown"),
    ("x", "money:team-unknown"),
    ([GOOD_EXTRA], "money:team-unknown"),
    (with_extra(cap=None), "money:team-uncapped"),
    (with_extra(cap=ABSENT), "money:team-uncapped"),
    ({"enabled": False, "cap": None, "spent": None, "currency": None, "cap_reached": False}, "money:team-uncapped"),
    (with_extra(enabled=False, cap=ABSENT), "money:team-uncapped"),
    (with_extra(cap=0), "money:team-unknown"),
    (with_extra(cap=-5), "money:team-unknown"),
    (with_extra(cap="200"), "money:team-unknown"),
    (with_extra(cap=True), "money:team-unknown"),
    (with_extra(cap=[200]), "money:team-unknown"),
    (with_extra(cap=10 ** 400), "money:team-unknown"),
    (with_extra(spent=None), "money:team-unknown"),
    (with_extra(spent=ABSENT), "money:team-unknown"),
    (with_extra(spent=-1), "money:team-unknown"),
    (with_extra(spent="5"), "money:team-unknown"),
    (with_extra(spent=False), "money:team-unknown"),
    (with_extra(spent=10 ** 400), "money:team-unknown"),
    (with_extra(cap_reached=True), "money:team-cap"),
    (with_extra(cap_reached=None), "money:team-unknown"),
    (with_extra(cap_reached=ABSENT), "money:team-unknown"),
    (with_extra(cap_reached=0), "money:team-unknown"),
    (with_extra(cap_reached="false"), "money:team-unknown"),
    (with_extra(spent=180.0), "money:team-cap"),
    (with_extra(spent=250.0), "money:team-cap"),
    (with_extra(spent=179.99), None),
    (with_extra(spent=0), None),
    (with_extra(cap=250, spent=0, cap_reached=False, enabled=ABSENT, currency=ABSENT), None),
    (with_extra(enabled=False), None),  # enabled is not trusted either way; cap/spent/cap_reached decide
])
def test_team_money_rule(w, capsys, extra, reason):
    over(w)
    add_team(w, "t1", extra=extra)
    code, out, _ = w.run(capsys)
    if reason is None:
        assert code == 0 and out["instance"] == "t1"
    else:
        assert code == 3 and ("t1", reason) in refused(out)


def test_team_money_label_order(w, capsys):
    # first failing label: uncapped wins over a bad spent, cap_reached over spend >= 90%, windows last
    over(w)
    add_team(w, "t1", extra=with_extra(cap=None, spent="x"))
    add_team(w, "t2", extra=with_extra(cap_reached=True, spent=500.0), week=ABSENT)
    add_team(w, "t3", extra=with_extra(spent=190.0), week=ABSENT)
    w.usage_age = timedelta(hours=2)
    add_team(w, "t4", week=ABSENT)
    code, out, _ = w.run(capsys)
    r = refused(out)
    assert ("t1", "money:team-uncapped") in r and ("t2", "money:team-cap") in r
    assert ("t3", "money:team-cap") in r and ("t4", "money:team-unknown") in r


@pytest.mark.parametrize("used,week,reason", [
    (ABSENT, 10, "money:team-unknown"),
    (10, ABSENT, "money:team-unknown"),
    (None, 10, "money:team-unknown"),
    (10, None, "money:team-unknown"),
    (10, -1, "money:team-unknown"),
    (10, "10", "money:team-unknown"),
    (10, 1001, "money:team-unknown"),
    (10, 89, None),
    (10, 90, "near-limit"),
    (95, 0, "near-limit"),
])
def test_team_windows(w, capsys, used, week, reason):
    over(w)
    add_team(w, "t1", used=used, week=week)
    code, out, _ = w.run(capsys)
    if reason is None:
        assert code == 0 and out["instance"] == "t1" and out["used"] == 89
    else:
        assert code == 3 and ("t1", reason) in refused(out)


def test_team_unknown_used_never_first_unknown(w, capsys):
    # a personal login with unknown used is picked as "first unknown"; a Team seat with an
    # unknown window is refused even when it comes first in rotation order
    over(w)
    add_team(w, "t1", week=ABSENT)
    w.add("m1")
    code, out, _ = w.run(capsys)
    assert code == 0 and out["instance"] == "m1" and out["used"] is None
    assert ("t1", "money:team-unknown") in refused(out)


@pytest.mark.parametrize("age,reason", [
    (timedelta(minutes=29), None),
    (timedelta(minutes=30), None),
    (timedelta(minutes=31), "money:team-stale-usage"),
    (timedelta(days=3), "money:team-stale-usage"),
    (timedelta(minutes=-5), "money:team-stale-usage"),  # a future mtime is not fresh
])
def test_team_usage_file_age(w, capsys, age, reason):
    over(w)
    add_team(w, "t1")
    w.usage_age = age
    code, out, _ = w.run(capsys)
    if reason is None:
        assert code == 0 and out["instance"] == "t1"
    else:
        assert code == 3 and ("t1", reason) in refused(out)


def test_team_usage_file_mtime_unreadable(w, capsys, monkeypatch):
    over(w)
    add_team(w, "t1")
    w.write()
    real = pick.Path.stat

    def boom(self, *a, **k):
        if self == w.usage_file and k.get("follow_symlinks", True):
            raise PermissionError("probe")
        return real(self, *a, **k)
    monkeypatch.setattr(pick.Path, "stat", boom)
    code, out, _ = w.run(capsys, write=False)
    assert code == 3 and ("t1", "money:team-stale-usage") in refused(out)


def test_stale_usage_file_does_not_affect_personal(w, capsys):
    over(w)
    w.add("m1", used=10)
    w.usage_age = timedelta(days=3)
    code, out, _ = w.run(capsys)
    assert code == 0 and out["instance"] == "m1"


@pytest.mark.parametrize("remote,age,reason", [
    (None, None, "privacy:remote-settings.json:absent"),
    ('{"env": {"X": "1"}}', timedelta(hours=1), "privacy:remote-settings.json"),
    ('{"permissions": {}}', timedelta(hours=1), "privacy:remote-settings.json"),
    ("{}", timedelta(hours=25), "privacy:remote-settings.json:stale"),
    ("{}", timedelta(minutes=-10), "privacy:remote-settings.json:stale"),
    ("{}", timedelta(hours=23), None),
    ("  {}  \n", timedelta(hours=1), None),
    ("", timedelta(hours=1), None),
])
def test_team_remote_settings(w, capsys, remote, age, reason):
    over(w)
    add_team(w, "t1", remote=remote, remote_age=age)
    code, out, _ = w.run(capsys)
    if reason is None:
        assert code == 0 and out["instance"] == "t1"
    else:
        assert code == 3 and ("t1", reason) in refused(out)


def test_team_remote_settings_mtime_unreadable(w, capsys, monkeypatch):
    over(w)
    home = add_team(w, "t1")
    real = pick.Path.stat

    def boom(self, *a, **k):
        if self == home / "remote-settings.json" and k.get("follow_symlinks", True):
            raise PermissionError("probe")
        return real(self, *a, **k)
    monkeypatch.setattr(pick.Path, "stat", boom)
    code, out, _ = w.run(capsys)
    assert code == 3 and ("t1", "privacy:remote-settings.json:stale") in refused(out)


def test_team_managed_settings_unchanged(w, capsys):
    over(w)
    home = add_team(w, "t1")
    (home / "managed-settings.json").write_text('{"a": 1}', encoding="utf-8")
    code, out, _ = w.run(capsys)
    assert code == 3 and ("t1", "privacy:managed-settings.json") in refused(out)


def test_personal_remote_settings_absent_still_passes(w, capsys):
    over(w)
    home = w.add("m1", used=10)
    assert not (home / "remote-settings.json").exists()
    code, out, _ = w.run(capsys)
    assert code == 0 and out["instance"] == "m1"


@pytest.mark.parametrize("team_used,personal_used,expected", [(30, 50, "t1"), (60, 50, "m1"), (50, 50, "t1")])
def test_team_ranked_by_used(w, capsys, team_used, personal_used, expected):
    over(w)
    add_team(w, "t1", used=team_used)
    w.add("m1", used=personal_used)
    code, out, _ = w.run(capsys)
    assert code == 0 and out["instance"] == expected and out["used"] == min(team_used, personal_used)


def test_team_other_checks_still_apply(w, capsys):
    over(w)
    add_team(w, "t1", rot_email="someone-else@example.test")
    h2 = add_team(w, "t2")
    wjson(h2 / "settings.local.json", {"env": {"OTEL_LOGS_EXPORTER": "otlp"}})
    add_team(w, "t3")
    w.instances["t3"]["config"]["binaryPath"] = "x.cmd"
    add_team(w, "t4")
    w.limits = {"t4": "2026-11-23T00:00:00Z"}
    h5 = add_team(w, "t5")
    extra_hooks = json.loads(json.dumps(HOOKS))
    extra_hooks["Stop"] = [{"hooks": [{"type": "command", "command": "x"}]}]
    wjson(h5 / "settings.json", {"hooks": extra_hooks})
    code, out, _ = w.run(capsys)
    r = refused(out)
    assert code == 3
    assert ("t1", "identity-mismatch") in r and ("t2", "privacy:settings.local.json:OTEL_LOGS_EXPORTER") in r
    assert ("t3", "privacy:t3-instance:binaryPath") in r and ("t4", "limited") in r
    assert ("t5", "privacy:hooks:settings.json") in r


@pytest.mark.parametrize("org,reason", [
    ("claude_enterprise", "org:enterprise"), ("Claude_Team", "org:unknown"), ("claude_team ", "org:unknown"),
])
def test_team_exact_org_only(w, capsys, org, reason):
    over(w)
    home = add_team(w, "t1")
    acct = json.loads((home / ".claude.json").read_text())
    acct["oauthAccount"]["organizationType"] = org
    wjson(home / ".claude.json", acct)
    code, out, _ = w.run(capsys)
    assert code == 3 and ("t1", reason) in refused(out)


@pytest.mark.parametrize("second,reason", [
    ({"5h": 10, "week": 0, "extra": GOOD_EXTRA}, None),          # identical duplicate -> one row
    ({"5h": 11, "week": 0, "extra": GOOD_EXTRA}, "money:team-unknown"),
    ({"5h": 10, "week": 0, "extra": with_extra(spent=21.0)}, "money:team-unknown"),
    ({"5h": 10, "week": 0}, "money:team-unknown"),
    ({"error": "HTTPError: 429"}, "money:team-unknown"),
])
def test_team_duplicate_rows(w, capsys, second, reason):
    # G3 (changed in fix 5): the second row now carries the same slot, so it is a slot-bound duplicate
    over(w)
    add_team(w, "t1", used=10, week=0)
    w.usage.append({"slot": "t1", "email": "T1@Example.test", **second})
    code, out, _ = w.run(capsys)
    if reason is None:
        assert code == 0 and out["instance"] == "t1"
    else:
        assert code == 3 and ("t1", reason) in refused(out)


def test_team_current_unchanged(w, capsys):
    # F4e: a Team current keeps today's rules (hasExtraUsageEnabled decides current_verified)
    w.add("s1", used=50)
    w.add("s2", used=99)
    wjson(w.slots / "s2" / ".claude.json", {"oauthAccount": {"emailAddress": "s2@example.test",
                                                            "organizationType": "claude_team",
                                                            "hasExtraUsageEnabled": True}})
    w.usage = [r for r in w.usage if r["slot"] != "s2"] + [
        {"slot": "s2", "email": "s2@example.test", "5h": 10, "week": 0, "extra": GOOD_EXTRA}]
    (w.slots / "s2" / "remote-settings.json").write_text("{}", encoding="utf-8")
    code, out, _ = w.run(capsys, current="s2")
    assert out["current_verified"] is False and out["current_reason"] == "money:extra-usage"
    assert out["current_extra_usage"] == "on" and out["instance"] == "s1"


def test_team_values_never_printed(w, capsys):
    over(w)
    add_team(w, "t1", extra=with_extra(cap=123457.0, spent=118000.0, currency=MARK))
    add_team(w, "t2", extra=with_extra(cap=4242.0, spent=1.0, currency=MARK))
    w.write()
    texts = []
    for extra in ([], ["--json"]):
        pick.main(w.argv(extra=extra))
        cap = capsys.readouterr()
        texts.append(cap.out + cap.err)
    for text in texts:
        assert MARK not in text and "123457" not in text and "118000" not in text and "4242" not in text
        assert "@" not in text and "example.test" not in text.lower()
    assert ("t1", "money:team-cap") in refused(json.loads(texts[1]))


# G1 (fix 5) two or more rotation ids on one home directory: every id in the group is refused
def test_duplicate_home_two_slots(w, capsys):
    over(w)
    w.add("s1", used=10)
    w.add("s2", used=20, rot_email="s1@example.test")
    w.instances["s2"]["config"]["homePath"] = str(w.slots / "s1")
    w.add("s3", used=50)
    code, out, _ = w.run(capsys)
    r = refused(out)
    assert code == 0 and out["instance"] == "s3" and out["used"] == 50
    assert ("s1", "no-home:duplicate") in r and ("s2", "no-home:duplicate") in r


def test_duplicate_home_path_spelling(w, capsys):
    over(w)
    w.add("s1", used=10)
    w.add("s2", used=20)
    w.instances["s2"]["config"]["homePath"] = str(w.slots / "s2" / ".." / "s1")
    code, out, _ = w.run(capsys)
    r = refused(out)
    assert code == 3 and ("s1", "no-home:duplicate") in r and ("s2", "no-home:duplicate") in r


def test_duplicate_home_slot_on_main_keeps_ambiguous(w, capsys):
    # a slot id on the main home is in a group with the built-in: no-home:ambiguous wins for the slot,
    # no-home:builtin for the built-in candidate, and the built-in current is no-home:duplicate
    w.usage.append({"slot": "main", "email": "claudeagent@example.test", "5h": 10})
    w.add("dup", rot_email="claudeagent@example.test")
    w.instances["dup"]["config"]["homePath"] = str(w.main)
    w.add("s1", used=50)
    code, out, _ = w.run(capsys)
    assert ("dup", "no-home:ambiguous") in refused(out)
    assert out["current_reason"] == "no-home:duplicate" and out["current_verified"] is False
    assert code == 0 and out["instance"] == "s1" and out["reason"] == "overflow"
    code, out, _ = w.run(capsys, current="dup")
    assert out["current_reason"] == "no-home:ambiguous" and ("claudeAgent", "no-home:builtin") in refused(out)


def test_duplicate_home_current(w, capsys):
    w.add("s1", used=10)
    w.add("s2", used=20, rot_email="s1@example.test")
    w.instances["s2"]["config"]["homePath"] = str(w.slots / "s1")
    w.add("s3", used=50)
    code, out, _ = w.run(capsys, current="s1")
    assert out["current_verified"] is False and out["current_reason"] == "no-home:duplicate"
    assert out["current_extra_usage"] == "unknown"
    assert code == 0 and out["instance"] == "s3" and ("s2", "no-home:duplicate") in refused(out)


def test_duplicate_home_undeterminable_counts(w, capsys, monkeypatch):
    over(w)
    w.add("s1", used=10)
    w.add("s2", used=20)
    w.write()
    real = pick.same_dir
    monkeypatch.setattr(pick, "same_dir", lambda a, b: None if {Path(a).name, Path(b).name} == {"s1", "s2"}
                        else real(a, b))
    code, out, _ = w.run(capsys, write=False)
    r = refused(out)
    assert code == 3 and ("s1", "no-home:duplicate") in r and ("s2", "no-home:duplicate") in r


def test_duplicate_home_ignores_unlaunchable_and_absent(w, capsys):
    # a disabled instance, an id missing from T3 and a deleted slot folder are not homes to compare
    over(w)
    w.add("s1", used=10)
    w.add("off", enabled=False)
    w.instances["off"]["config"]["homePath"] = str(w.slots / "s1")
    w.add("gone", in_t3=False)
    w.add("del")
    w.instances["del"]["config"]["homePath"] = str(w.slots / "deleted")
    code, out, _ = w.run(capsys)
    assert code == 0 and out["instance"] == "s1" and out["used"] == 10
    assert all(reason != "no-home:duplicate" for _, reason in refused(out))


# G2 (fix 5) the 90% Team spend rule is exact (no float rounding at the boundary)
@pytest.mark.parametrize("cap,spent,reason", [
    (13, 11.7, "money:team-cap"),
    (13, 11.69, None),
    (13.0, 11.7, "money:team-cap"),
    (10, 9, "money:team-cap"),
    (10, 8.99, None),
    (0.3, 0.27, "money:team-cap"),
    (200.0, 180.0, "money:team-cap"),
    (200.0, 179.99, None),
])
def test_team_spend_rule_exact(w, capsys, cap, spent, reason):
    over(w)
    add_team(w, "t1", extra=with_extra(cap=cap, spent=spent))
    code, out, _ = w.run(capsys)
    if reason is None:
        assert code == 0 and out["instance"] == "t1"
    else:
        assert code == 3 and ("t1", reason) in refused(out)


# G3 (fix 5) a Team candidate's money and plan-usage row is the one bound to its slot
def shared_email_team(w, iid, **kw):
    home = add_team(w, iid, rot_email="shared@example.test", **kw)
    wjson(home / ".claude.json", {"oauthAccount": {"emailAddress": "shared@example.test",
                                                   "organizationType": "claude_team",
                                                   "hasExtraUsageEnabled": True}})
    for r in w.usage:
        if r.get("slot") == iid:
            r["email"] = "shared@example.test"
    return home


def test_team_row_bound_to_slot_same_email(w, capsys):
    # same email on two Team slots, only B capped: A's own row is uncapped -> A refused even though
    # B's capped row carries the same email
    over(w)
    shared_email_team(w, "ta", extra=with_extra(cap=None))
    shared_email_team(w, "tb", used=40)
    code, out, _ = w.run(capsys)
    assert ("ta", "money:team-uncapped") in refused(out)
    assert code == 0 and out["instance"] == "tb" and out["used"] == 40


def test_team_row_bound_to_slot_no_own_row(w, capsys):
    # A has no row of its own; B's capped row with the same email is not borrowed
    over(w)
    shared_email_team(w, "ta", used=ABSENT, week=ABSENT, extra=ABSENT)
    w.usage = [r for r in w.usage if r.get("slot") != "ta"]
    shared_email_team(w, "tb")
    code, out, _ = w.run(capsys)
    assert ("ta", "money:team-unknown") in refused(out) and out["instance"] == "tb"


def test_team_used_from_bound_row(w, capsys):
    # plan usage: a lower-usage row under another slot with the same email is ignored for Team
    over(w)
    add_team(w, "ta", used=95)
    w.usage.append({"slot": "other", "email": "ta@example.test", "5h": 5, "week": 0, "extra": GOOD_EXTRA})
    w.add("m1", used=50)
    code, out, _ = w.run(capsys)
    assert code == 0 and out["instance"] == "m1" and ("ta", "near-limit") in refused(out)


def test_team_used_reported_from_bound_row(w, capsys):
    over(w)
    add_team(w, "ta", used=30)
    w.usage.append({"slot": "other", "email": "ta@example.test", "5h": 70, "week": 0})
    code, out, _ = w.run(capsys)
    assert code == 0 and out["instance"] == "ta" and out["used"] == 30


def test_team_row_slot_match_email_mismatch(w, capsys):
    over(w)
    add_team(w, "ta")
    for r in w.usage:
        if r.get("slot") == "ta":
            r["email"] = "someone-else@example.test"
    code, out, _ = w.run(capsys)
    assert code == 3 and ("ta", "money:team-unknown") in refused(out)


@pytest.mark.parametrize("slot", [ABSENT, None, "", "TA", "ta-other", 7])
def test_team_row_missing_or_wrong_slot(w, capsys, slot):
    over(w)
    add_team(w, "ta")
    for r in w.usage:
        if r.get("slot") == "ta":
            if slot is ABSENT:
                del r["slot"]
            else:
                r["slot"] = slot
    code, out, _ = w.run(capsys)
    assert code == 3 and ("ta", "money:team-unknown") in refused(out)


def test_team_home_not_direct_child_of_slots_dir(w, capsys):
    over(w)
    home = add_team(w, "ta")
    nested = w.slots / "nest" / "ta"
    nested.parent.mkdir()
    home.rename(nested)
    w.instances["ta"]["config"]["homePath"] = str(nested)
    code, out, _ = w.run(capsys)
    assert code == 3 and ("ta", "money:team-unknown") in refused(out)


def test_personal_rows_still_by_email(w, capsys):
    # personal logins keep the email logic: max over every row with that email (conservative)
    over(w)
    w.add("m1", used=10)
    w.usage.append({"slot": "other", "email": "m1@example.test", "5h": 92})
    code, out, _ = w.run(capsys)
    assert code == 3 and ("m1", "near-limit") in refused(out)
