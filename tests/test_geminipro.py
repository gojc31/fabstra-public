"""Offline tests for scripts/geminipro.py - fakes only: no network, no Chrome. One exception,
local and Windows-only: three N1 tests start their own sleeping Python interpreters (stdlib
only) and terminate exactly those, through the creation-time-verified kill under test; every
other test sees recording doubles of the process snapshot and kill seams.

The real gemini_webapi library runs against a fake curl_cffi transport (FakeSession,
installed where get_access_token constructs its AsyncSession) and a fake
browser-harness (geminipro._run_harness). Run with the geminipro-lab venv:
  .venv/Scripts/python.exe -m pytest -q tests/test_geminipro.py
Set GEMINIPRO_SCRIPT=<path> to run the suite against another copy of the script
(used once to show the A3 negative test failing on a sabotaged identity check).
"""
import asyncio
import builtins
import contextlib
import importlib.util
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import uuid

import pytest

pytest.importorskip("gemini_webapi")

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
_spec = importlib.util.spec_from_file_location(
    "geminipro", os.environ.get("GEMINIPRO_SCRIPT") or os.path.join(SCRIPTS, "geminipro.py"))
gp = importlib.util.module_from_spec(_spec)
sys.modules["geminipro"] = gp
_spec.loader.exec_module(gp)
# the real process seams, before any fixture replaces them (only a test that starts its own
# processes calls these; every other test sees the recording doubles of the `world` fixture)
REAL = {n: getattr(gp, n, None) for n in ("_run_api", "_snapshot", "_kill_verified", "_created",
                                          "_kill_descendants")}

import lanew_log  # noqa: E402
from curl_cffi.requests import Cookies  # noqa: E402
from curl_cffi.requests.exceptions import HTTPError  # noqa: E402
from gemini_webapi.constants import GRPC, Endpoint  # noqa: E402

PSID = "FAKE1PSID" + uuid.uuid4().hex + uuid.uuid4().hex
PSIDTS = "FAKE1PSIDTS" + uuid.uuid4().hex
OTHER_PSID = "FAKEOTHER1PSID" + uuid.uuid4().hex + uuid.uuid4().hex
OTHER_PSIDTS = "FAKEOTHER1PSIDTS" + uuid.uuid4().hex
CACHED_PSIDTS = "FAKECACHED1PSIDTS" + uuid.uuid4().hex
SECRETS = (PSID, PSIDTS, OTHER_PSID, OTHER_PSIDTS, CACHED_PSIDTS)
RIGHT = "pro.user@example.com"          # the configured account (GEMINIPRO_ACCOUNT in `env`)
WRONG = "work.user@corp.example.com"    # another signed-in account
THIRD = "third.user@client.example.com"
DECOY = "staff@mail.example.com"        # an unrelated address field on the app page
CLEAN = (b"brief-check: clean - generic arithmetic question\n"
         b"What is 17*23? Reply with the number only.\n")
BASE_KEYS = {"tool", "exit", "status", "reason", "run", "name", "model", "job_id", "report",
             "account_ok", "duration_s", "submissions", "context", "via", "meter"}
TRIGGER_KEYS = {"backup", "primary_exit", "primary_reason", "requested_model"}
# a unique 40-character stand-in for GEMINI_API_KEY (never a real key)
API_KEY = ("FAKEAPIKEY" + uuid.uuid4().hex + uuid.uuid4().hex)[:40]
CARBON = ["c4rb0n1d", "Carbon", "Most capable"]
FAST = ["f4571d", "Fast", "Quick answers"]


# --------------------------------------------------------------------------
# fake Google (transport level) and fake browser-harness
# --------------------------------------------------------------------------

class World:
    def __init__(self):
        self.accounts = {PSID: RIGHT, OTHER_PSID: WRONG}
        self.status_code = 1000
        self.gen_mode = "ok"
        self.answer = "391"
        self.requests = []          # (method, url, {cookie: value})
        self.generate_calls = 0     # POSTs that reached the transport
        self.dispatched = False
        self.html_override = None
        self.batch_fail = None      # HTTP status for every batch RPC (pre-send failure)
        self.batch_fail_armed = None  # HTTP status for batch RPCs after admission, before dispatch
        self.harness_calls = 0
        self.init_status = {}       # __Secure-1PSID -> (HTTP status, body) for the /app GET
        self.kwargs = []            # (method, url, kwargs) of every transport call
        self.omit_user_status = False
        self.get_cookie = None      # (name, value) the /app GET sets in the session jar
        self.stream_cookie = None   # (name, value) the generate stream sets in the session jar
        # GetUsageInfo items (remaining, usage_level, window type, [[reset ts]]); None: no part
        self.usage = [[512, 0.1, 1, [[1893456000]]], [4096, 0.2, 2, [[1893456000]]]]
        self.rpcids = []            # every batch RPC id the transport saw, in order


WORLD = World()


def _frame(obj):
    payload = "\n" + json.dumps(obj)
    return "%d%s" % (len(payload.encode("utf-16-le")) // 2, payload)


def _answer_stream(text):
    cand = ["rc_1", [text], None, None, None, None, None, None, [2]]
    inner = [None, ["c_1", "r_1"], None, None, [cand]]
    return ")]}'\n\n" + _frame([["wrb.fr", None, json.dumps(inner)]])


def _cid_only_stream():
    inner = [None, ["c_1", "r_1"]]
    return ")]}'\n\n" + _frame([["wrb.fr", None, json.dumps(inner)]])


def _batch_body(rpcid):
    if rpcid == GRPC.GET_USER_STATUS:
        if WORLD.omit_user_status:
            return None
        return [None] * 14 + [WORLD.status_code, [CARBON, FAST], [], []]
    if rpcid == GRPC.GET_USAGE_INFO:
        return None if WORLD.usage is None else [2, WORLD.usage, False]
    if rpcid == GRPC.GET_ABUSE_STATUS:
        return [None, None]
    return None


class FakeResp:
    def __init__(self, status, text="", chunks=()):
        self.status_code = status
        self.text = text
        self.http_version = 2
        self._chunks = list(chunks)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise HTTPError("HTTP %d" % self.status_code, 0, self)

    async def aiter_content(self):
        for c in self._chunks:
            if isinstance(c, BaseException):
                raise c
            yield c


class FakeSession:
    def __init__(self, *a, **k):
        self.cookies = Cookies()
        self.timeout = None

    def _jar(self):
        return {c.name: c.value for c in self.cookies.jar}

    async def get(self, url, headers=None, **k):
        WORLD.requests.append(("GET", url, self._jar()))
        WORLD.kwargs.append(("GET", url, dict(k)))
        if url.startswith(Endpoint.INIT):
            if WORLD.get_cookie:
                self.cookies.set(WORLD.get_cookie[0], WORLD.get_cookie[1], domain=".google.com")
            forced = WORLD.init_status.get(self._jar().get("__Secure-1PSID"))
            if forced is not None:
                return FakeResp(forced[0], forced[1])
            if WORLD.html_override is not None:
                return FakeResp(200, WORLD.html_override)
            email = WORLD.accounts.get(self._jar().get("__Secure-1PSID"))
            if email is None:
                return FakeResp(200, "<html>Sign in</html>")
            return FakeResp(200, '<script>window.WIZ_global_data = {"SNlM0e":"tok","cfb2h":"bl1",'
                                 '"FdrFJe":"sid1","TuX5cc":"en","45670485":"%s",'
                                 '"nVwyhb":false,"oPEP7c":"%s"};</script>' % (DECOY, email))
        return FakeResp(404)

    async def post(self, url, params=None, headers=None, data=None, **k):
        WORLD.requests.append(("POST", url, self._jar()))
        WORLD.kwargs.append(("POST", url, dict(k)))
        if url.startswith(Endpoint.BATCH_EXEC):
            if WORLD.gen_mode == "recover_auth_loss" and WORLD.dispatched:
                return FakeResp(401)
            if WORLD.batch_fail:
                return FakeResp(WORLD.batch_fail)
            if WORLD.batch_fail_armed and gp.STATE.policy.armed and not WORLD.dispatched:
                return FakeResp(WORLD.batch_fail_armed)
            parts = []
            for rid in (params or {}).get("rpcids", "").split(","):
                WORLD.rpcids.append(rid)
                body = _batch_body(rid)
                if body is not None:
                    parts.append(["wrb.fr", rid, json.dumps(body), None, None, None, "generic"])
            return FakeResp(200, ")]}'\n\n" + json.dumps(parts))
        return FakeResp(404)

    @contextlib.asynccontextmanager
    async def stream(self, method, url, **k):
        WORLD.requests.append((method, url, self._jar()))
        WORLD.kwargs.append((method, url, dict(k)))
        if url.startswith(Endpoint.GENERATE):
            WORLD.generate_calls += 1
            WORLD.dispatched = True
        if WORLD.stream_cookie:
            self.cookies.set(WORLD.stream_cookie[0], WORLD.stream_cookie[1], domain=".google.com")
        m = WORLD.gen_mode
        if m in ("http500", "http429", "http403", "http302"):
            yield FakeResp(int(m[4:]))
        elif m == "abort":
            yield FakeResp(200, chunks=[])
        elif m == "recover_auth_loss":
            yield FakeResp(200, chunks=[_cid_only_stream().encode()])
        elif m == "cancel":
            yield FakeResp(200, chunks=[asyncio.CancelledError()])
        elif m == "kbint":
            yield FakeResp(200, chunks=[KeyboardInterrupt()])
        else:
            yield FakeResp(200, chunks=[_answer_stream(WORLD.answer).encode()])

    async def close(self):
        pass


def harness_payload(contexts=None, default="AAAA1111", errors=(), default_jar=None,
                    bc_fields=("browserContextIds", "defaultBrowserContextId")):
    """The harness child's summary (v2): per-context cookies plus the default jar read
    on the browser-target session (its ctx is defaultBrowserContextId when reported)."""
    if contexts is None:
        contexts = [{"ctx": "AAAA1111", "via": "browser_ui/Network.getCookies",
                     "psid": PSID, "psidts": PSIDTS},
                    {"ctx": "BBBB2222", "via": "browser_ui/Network.getCookies",
                     "psid": OTHER_PSID, "psidts": OTHER_PSIDTS}]
    if default_jar is None:
        for c in contexts:
            if default and c["ctx"] == default and c.get("psid"):
                default_jar = {"ctx": default, "via": "browser/Storage.getCookies",
                               "psid": c["psid"], "psidts": c["psidts"]}
    return json.dumps({"v": 2, "bc_fields": list(bc_fields), "default_jar": default_jar,
                       "contexts": contexts, "errors": list(errors)}).encode()


def api_ok(text="API-ANSWER-391", status="completed", model="gemini-4-hydrogen"):
    """What the gemini-api CLI printed on a good call (shape seen live 2026-11-15); model None
    leaves the response's model field out."""
    out = {"status": status, "usage": {}, "created": "x", "updated": "x", "object": "interaction",
           "model": model, "steps": [
               {"type": "thought", "signature": "THOUGHT-SIG"},
               {"type": "model_output", "content": [{"type": "text", "text": text}]}]}
    if model is None:
        del out["model"]
    return (0, json.dumps(out).encode(), b"")


def api_err(rc, code, etype, message="failed"):
    err = {"error": {"code": code, "message": message}, "error_type": etype, "exit_code": rc,
           "hints": []}
    return (rc, b"", json.dumps(err).encode())


class FakeApi:
    """The gp._run_api seam: records argv, cwd (and what it held), stdin, timeout, env and the
    body file; answers from `script` (a (rc, stdout, stderr) tuple or an exception to raise)."""

    def __init__(self):
        self.calls = []
        self.script = []

    def __call__(self, argv, cwd, env, timeout, stdin, holder):
        bp = os.path.join(cwd, "body.json")
        self.calls.append({"argv": list(argv), "cwd": cwd, "env": dict(env), "timeout": timeout,
                           "stdin": stdin, "listing": sorted(os.listdir(cwd)),
                           "body_raw": open(bp, "rb").read() if os.path.exists(bp) else None})
        r = self.script.pop(0) if self.script else api_ok()
        if isinstance(r, BaseException):
            raise r
        return subprocess.CompletedProcess(argv, r[0], r[1], r[2])


@pytest.fixture
def world(monkeypatch, tmp_path):
    global WORLD
    WORLD = World()
    gp._SECRETS.clear()  # each geminipro call is a fresh process in production
    gat = sys.modules.get("gemini_webapi.utils.get_access_token")
    if gat is None:
        import gemini_webapi  # noqa: F401
        gat = sys.modules["gemini_webapi.utils.get_access_token"]
    monkeypatch.setattr(gat, "AsyncSession", FakeSession)
    monkeypatch.setattr(sys.modules["gemini_webapi.utils.decorators"], "_DELAY_FACTOR", 0)
    # name-aware: browser-harness resolves to the fake; gemini-api is not on PATH unless a
    # test says so (the API backup tests point GEMINIPRO_API_CLI at a fake file instead)
    monkeypatch.setattr(gp.shutil, "which", lambda name, *a, **k: (
        "C:/fake/browser-harness.exe" if "browser-harness" in str(name) else None))
    # the API CLI seam: every test gets a recording fake, so no test ever starts a process
    WORLD.api = FakeApi()
    monkeypatch.setattr(gp, "_run_api", WORLD.api, raising=False)
    monkeypatch.setattr(gp, "API_RETRY_PAUSE", 0, raising=False)
    # the process-kill seams: recording doubles, so no test reads a real process snapshot or
    # kills a real process (a fake Popen carries an invented pid) unless it opts in through REAL
    WORLD.kills = []
    monkeypatch.setattr(gp, "_snapshot", lambda: [], raising=False)
    monkeypatch.setattr(gp, "_kill_verified",
                        lambda pid, created: WORLD.kills.append((pid, created)) or True, raising=False)
    monkeypatch.setattr(gp, "_created", lambda pid: 1000, raising=False)
    payload = {"out": harness_payload(), "rc": 0, "err": b""}

    def fake_harness(argv, script, env, timeout):
        WORLD.harness_calls += 1
        WORLD.harness_env = env
        return subprocess.CompletedProcess(argv, payload["rc"], payload["out"], payload["err"])

    monkeypatch.setattr(gp, "_run_harness", fake_harness)
    WORLD.hard_exits = []
    monkeypatch.setattr(gp, "HARD_EXIT", WORLD.hard_exits.append, raising=False)  # never kills pytest
    WORLD.payload = payload
    cache = tmp_path / "gcp"
    cache.mkdir()
    monkeypatch.setenv("GEMINI_COOKIE_PATH", str(cache))
    WORLD.cache = cache
    return WORLD


@pytest.fixture
def env(tmp_path):
    """A fresh env dict (never os.environ): GEMINI_API_KEY and the GEMINIPRO_API_* variables
    are absent unless a test sets them, so the developer's real key never enters a test."""
    cp = tmp_path / "cliproxy"
    e = {"PATH": os.environ.get("PATH", ""), "CLIPROXY_DIR": str(cp),
         "GEMINIPRO_LOG": str(cp / "geminipro-usage.jsonl"), "GEMINIPRO_TOTAL_DEADLINE": "120",
         "GEMINIPRO_SLOT_WAIT": "0", "GEMINIPRO_ACCOUNT": RIGHT}
    assert not any(k == "GEMINI_API_KEY" or k.startswith("GEMINIPRO_API_") for k in e)
    # 2026-11-18 (R8): every test written before the API primary path runs in the legacy
    # app-first mode; the API primary tests (primary_env) drop the switch
    e["GEMINIPRO_API_PRIMARY"] = "0"
    # 2026-11-19 (Neon, design-gate finding 1): every test written before Neon pins Carbon, so a
    # later DEFAULT_MODEL flip changes none of them; the Neon tests drop it or pass --model
    e["GEMINIPRO_MODEL"] = "gemini-carbon"
    return e


def run(capfd, tmp_path, env, args=("t1", "carbon"), brief=CLEAN, json_mode=True):
    bf = tmp_path / ("brief-%s.md" % uuid.uuid4().hex[:6])
    bf.write_bytes(brief)
    argv = list(args) + (["--brief-file", str(bf)] if brief is not None else []) + (
        ["--json"] if json_mode else [])
    code = gp.main(argv, env)
    out, err = capfd.readouterr()
    stream = out if json_mode else err
    line = [l for l in stream.strip().splitlines() if l.startswith("{")][-1]
    status = json.loads(line)
    assert status["exit"] == code
    return code, status, out, err


def log_entries(env):
    p = env["GEMINIPRO_LOG"]
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


# --------------------------------------------------------------------------
# A1 / A2 brief gate
# --------------------------------------------------------------------------

def test_a1_brief_without_attestation_exit7(world, env, capfd, tmp_path):
    code, st, _, _ = run(capfd, tmp_path, env, brief=b"What is 17*23?\n")
    assert code == 7 and st["status"] == "brief_refused"
    assert WORLD.harness_calls == 0 and WORLD.requests == [] and WORLD.generate_calls == 0
    assert not os.path.exists(env["GEMINIPRO_LOG"])


def test_a2_brief_with_secret_exit7(world, env, capfd, tmp_path):
    key = b"RSA " + b"PRIVATE KEY-----"  # built at run time: no key header literal in this file
    brief = CLEAN + b"-----BEGIN " + key + b"\nMIIEow\n-----END " + key + b"\n"
    code, st, _, _ = run(capfd, tmp_path, env, brief=brief)
    assert code == 7 and "secret" in st["reason"]
    assert WORLD.requests == [] and WORLD.generate_calls == 0


def test_brief_gate_bom_utf8_and_size(world, env, capfd, tmp_path):
    assert run(capfd, tmp_path, env, brief=b"\xff\xfe bad")[0] == 7
    assert run(capfd, tmp_path, env, brief=CLEAN + b"x" * 20001)[0] == 7
    code, st, _, _ = run(capfd, tmp_path, env, brief=b"\xef\xbb\xbf" + CLEAN)
    assert code == 0, st


def test_usage_errors_exit64(world, env, capfd, tmp_path):
    code, st, _, _ = run(capfd, tmp_path, env, args=("bad run", "x"))
    assert code == 64 and st["status"] == "usage_error"
    code, st, _, _ = run(capfd, tmp_path, env, args=("only",))
    assert code == 64


# --------------------------------------------------------------------------
# success path (A9 offline), output channels, report, log records
# --------------------------------------------------------------------------

def test_success_default_mode_stdout_answer_report_and_log(world, env, capfd, tmp_path):
    code, st, out, err = run(capfd, tmp_path, env, json_mode=False)
    assert code == 0 and st["status"] == "ok" and st["account_ok"] is True
    assert out.strip() == "391"
    assert st["submissions"] == 1 and WORLD.generate_calls == 1
    assert st["model"] == "gemini-carbon" and st["context"].startswith("AAAA1111")
    for k in ("tool", "exit", "status", "reason", "run", "name", "model", "job_id", "report",
              "account_ok", "duration_s"):
        assert k in st
    assert set(st) == BASE_KEYS and st["via"] == "app"  # today's keys plus `via`, nothing else
    assert "391" in open(st["report"], encoding="utf-8").read()
    recs = log_entries(env)
    assert [r["status"] for r in recs] == ["started", "ok"]
    assert recs[1]["job_id"] == st["job_id"] and recs[1]["codex_exit"] is None
    # only the supplied (right-context) cookies ever went out; the wrong context was never used
    sent = {r[2].get("__Secure-1PSID") for r in WORLD.requests}
    assert sent == {PSID}


def test_json_mode_stdout_only_status_line(world, env, capfd, tmp_path):
    WORLD.answer = "Answer-Text-Marker"
    code, st, out, err = run(capfd, tmp_path, env)
    assert code == 0
    assert out.strip().count("\n") == 0 and json.loads(out)["status"] == "ok"
    assert "Answer-Text-Marker" not in out
    assert "Answer-Text-Marker" in open(st["report"], encoding="utf-8").read()


def test_brief_on_stdin(world, env, capfd, monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(CLEAN)))
    code = gp.main(["t1", "stdin", "--json"], env)
    out, _ = capfd.readouterr()
    assert code == 0 and json.loads(out)["status"] == "ok"


# --------------------------------------------------------------------------
# A3 / A8 identity
# --------------------------------------------------------------------------

def test_a3_other_account_exit8_generate_never_called(world, env, capfd, tmp_path):
    WORLD.accounts = {PSID: WRONG, OTHER_PSID: THIRD}
    code, st, _, _ = run(capfd, tmp_path, env)
    assert code == 8 and st["status"] == "account_mismatch" and st["account_ok"] is False
    assert WORLD.generate_calls == 0 and st["submissions"] == 0
    assert not any(r[1].startswith(Endpoint.BATCH_EXEC) for r in WORLD.requests)  # no RPC either
    assert not os.path.exists(env["GEMINIPRO_LOG"])


def test_a8_forced_wrong_context_exit8(world, env, capfd, tmp_path):
    e = dict(env, GEMINIPRO_TEST="1", GEMINIPRO_TEST_CONTEXT="BBBB")
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 8 and WORLD.generate_calls == 0 and WRONG in st["reason"]
    e = dict(env, GEMINIPRO_TEST="1", GEMINIPRO_EXPECT_ACCOUNT="nobody@nowhere.example.com")
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 8 and WORLD.generate_calls == 0


def test_test_only_env_without_test_mode_refused(world, env, capfd, tmp_path):
    code, st, _, _ = run(capfd, tmp_path, dict(env, GEMINIPRO_EXPECT_ACCOUNT=WRONG))
    assert code == 2 and WORLD.harness_calls == 0


# --------------------------------------------------------------------------
# the configured account: GEMINIPRO_ACCOUNT, else the module default
# (the source tree's default account; the shareable copy ships "" and refuses)
# --------------------------------------------------------------------------

OTHER_DEFAULT = "default.user@example.com"


def _no_account(env):
    return {k: v for k, v in env.items() if k != "GEMINIPRO_ACCOUNT"}


def _configured(env):
    """config() alone: (the identity check's expected account, the production account)."""
    gp.STATE.new_run()
    w = gp.Wrapper(["t1", "carbon"], env)
    w.parse_args()
    w.config()
    return gp.STATE.expected, w.account


def test_account_env_sets_expected_account(world, env, capfd, tmp_path, monkeypatch):
    monkeypatch.setattr(gp, "EXPECTED_ACCOUNT", OTHER_DEFAULT)
    assert _configured(dict(env, GEMINIPRO_ACCOUNT=WRONG)) == (WRONG, WRONG)
    assert _configured(dict(env, GEMINIPRO_ACCOUNT=" %s \t" % WRONG)) == (WRONG, WRONG)  # stripped
    # end to end: the signed-in account must now be WRONG, so its context is the one used
    code, st, _, _ = run(capfd, tmp_path, dict(env, GEMINIPRO_ACCOUNT=WRONG))
    assert code == 0 and st["account_ok"] is True and st["context"].startswith("BBBB2222")
    assert WORLD.generate_calls == 1


def test_account_unset_uses_module_default(world, env, monkeypatch):
    monkeypatch.setattr(gp, "EXPECTED_ACCOUNT", OTHER_DEFAULT)
    assert _configured(_no_account(env)) == (OTHER_DEFAULT, OTHER_DEFAULT)


def test_shipped_default_resolution_when_unset(world, env):
    """A4: GEMINIPRO_ACCOUNT unset resolves to the module's own default, unpatched: the
    source tree keeps its default account; a copy shipped with "" refuses (exit 2)."""
    default = gp.EXPECTED_ACCOUNT.strip()
    if default:
        assert _configured(_no_account(env)) == (default, default)
    else:
        with pytest.raises(gp.Exit) as ei:
            _configured(_no_account(env))
        assert ei.value.code == 2 and "GEMINIPRO_ACCOUNT" in ei.value.reason


@pytest.mark.parametrize("mode", ["job", "status"])
@pytest.mark.parametrize("default,value", [
    ("", None),              # the shareable copy with GEMINIPRO_ACCOUNT unset
    ("", ""),
    ("", "   "),             # whitespace-only counts as empty
    ("", " \t\n"),
    (OTHER_DEFAULT, ""),     # a set-but-blank value never falls back to the default
    (OTHER_DEFAULT, "  "),
])
def test_empty_account_exit2_before_harness_or_network(world, env, capfd, tmp_path, monkeypatch,
                                                       default, value, mode):
    monkeypatch.setattr(gp, "EXPECTED_ACCOUNT", default)
    hardened = []
    real_harden = gp.harden
    monkeypatch.setattr(gp, "harden", lambda: hardened.append(1) or real_harden())
    e = _no_account(env)
    if value is not None:
        e["GEMINIPRO_ACCOUNT"] = value
    if mode == "job":
        code, st, _, _ = run(capfd, tmp_path, e)
    else:
        code = gp.main(["--status", "--json"], e)
        st = json.loads(capfd.readouterr()[0].strip().splitlines()[-1])
        assert st["exit"] == code
    assert code == 2 and st["status"] == "preflight_refused" and "GEMINIPRO_ACCOUNT" in st["reason"]
    assert WORLD.harness_calls == 0 and WORLD.requests == [] and WORLD.generate_calls == 0
    assert hardened == [] and st["submissions"] == 0 and st["account_ok"] is None
    assert not os.path.exists(env["GEMINIPRO_LOG"])


def test_test_override_wins_but_a_production_account_is_still_required(world, env, monkeypatch):
    e = dict(env, GEMINIPRO_TEST="1", GEMINIPRO_EXPECT_ACCOUNT=WRONG)
    assert _configured(e) == (WRONG, RIGHT)  # the override is what identity checks against
    monkeypatch.setattr(gp, "EXPECTED_ACCOUNT", "")
    with pytest.raises(gp.Exit) as ei:
        _configured(_no_account(e))
    assert ei.value.code == 2 and "GEMINIPRO_ACCOUNT" in ei.value.reason


def test_remember_context_follows_the_configured_account(world, env, capfd, monkeypatch):
    """The memory is written on a real run for the configured account, compared against
    the resolved production account rather than the module default."""
    monkeypatch.setattr(gp, "EXPECTED_ACCOUNT", OTHER_DEFAULT)
    assert gp.main(["--status", "--json"], env) == 0  # env: GEMINIPRO_ACCOUNT=RIGHT
    capfd.readouterr()
    assert _memory(env) == "AAAA1111"
    os.remove(os.path.join(env["CLIPROXY_DIR"], "geminipro.d", "last-context"))
    monkeypatch.setattr(gp, "EXPECTED_ACCOUNT", RIGHT)  # unset: the default path still remembers
    assert gp.main(["--status", "--json"], _no_account(env)) == 0
    capfd.readouterr()
    assert _memory(env) == "AAAA1111"


def test_signed_out_page_is_no_evidence(world, env, capfd, tmp_path):
    WORLD.accounts = {}
    code, st, _, _ = run(capfd, tmp_path, env)
    assert code == 8 and WORLD.generate_calls == 0
    # no fallback past the supplied cookies (no www.google.com preflight, no guest)
    assert not any(r[1].startswith(Endpoint.GOOGLE) for r in WORLD.requests)


def test_unauthenticated_status_exit8(world, env, capfd, tmp_path):
    WORLD.status_code = 1016
    code, st, _, _ = run(capfd, tmp_path, env)
    assert code == 8 and WORLD.generate_calls == 0


@pytest.mark.parametrize("html,expect", [
    ('{"oPEP7c":"pro.user@example.com"}', "pro.user@example.com"),
    ('{"oPEP7c":"pro.user\\u0040example.com"}', "pro.user@example.com"),
    ('{"oPEP7c":"work.user@corp.example.com"}', "work.user@corp.example.com"),
    ('{"45670485":"staff@mail.example.com"} <div>pro.user@example.com</div>', None),
    ('{"oPEP7c":"pro.user@example.com","x":{"oPEP7c":"work.user@corp.example.com"}}', None),
    ('{"oPEP7c":"pro.user@example.com","x":{"oPEP7c":"pro.user@example.com"}}', None),
    ('{"oPEP7c":""}', None),
    ("", None),
])
def test_parse_account_fixtures(html, expect):
    if expect is None:
        with pytest.raises(gp.NoEvidence):
            gp.parse_account(html)
    else:
        assert gp.parse_account(html) == expect


# --------------------------------------------------------------------------
# A4 model check
# --------------------------------------------------------------------------

def test_a4_unknown_model_exit4_lists_available(world, env, capfd, tmp_path):
    code, st, _, _ = run(capfd, tmp_path, env, args=("t1", "m", "--model", "gemini-nonesuch"))
    assert code == 4 and "gemini-carbon" in st["reason"] and "gemini-fast" in st["reason"]
    assert WORLD.generate_calls == 0 and not os.path.exists(env["GEMINIPRO_LOG"])


# --------------------------------------------------------------------------
# A5 caps
# --------------------------------------------------------------------------

def test_a5_ceiling_reached_exit1_log_unchanged(world, env, capfd, tmp_path):
    e = dict(env, GEMINIPRO_RUN_JOB_CEILING="1")
    assert run(capfd, tmp_path, e)[0] == 0
    before = open(env["GEMINIPRO_LOG"], "rb").read()
    calls = WORLD.harness_calls
    code, st, _, _ = run(capfd, tmp_path, e, args=("t1", "again"))
    assert code == 1 and st["status"] == "run_refused"
    assert open(env["GEMINIPRO_LOG"], "rb").read() == before
    assert WORLD.harness_calls == calls and WORLD.generate_calls == 1


def test_daily_cap_is_ignored(world, env, capfd, tmp_path):
    """M7: the retired GEMINIPRO_DAILY_CAP no longer refuses anything (3 jobs logged today)."""
    for r in ("r1", "r2", "r3"):
        assert run(capfd, tmp_path, env, args=(r, "a"))[0] == 0
    e = dict(env, GEMINIPRO_DAILY_CAP="1")
    code, st, _, _ = run(capfd, tmp_path, e, args=("r4", "d"))
    assert code == 0 and st["status"] == "ok", st
    assert [r["status"] for r in log_entries(env)].count("started") == 4


def test_cap_defaults(world, env):
    assert "GEMINIPRO_DAILY_CAP" not in env and "GEMINIPRO_RUN_JOB_CEILING" not in env
    assert "GEMINIPRO_MAX_5H_PCT" not in env and "GEMINIPRO_MAX_WEEKLY_PCT" not in env
    w = gp.Wrapper(["t1", "carbon", "--json"], dict(env, GEMINIPRO_DAILY_CAP="1"))
    w.config()
    assert w.max_5h == 80 and w.max_weekly == 90 and w.ceiling == 12
    assert not hasattr(w, "daily_cap") and not hasattr(gp.Wrapper, "daily_count")


# --------------------------------------------------------------------------
# Google's usage meter (M1-M10)
# --------------------------------------------------------------------------

RESET_TS = 1893456000


def set_meter(h5=None, weekly=None, h5_level=None, weekly_level=None):
    """GetUsageInfo items for the fake: percentages (or raw levels); None leaves a window out."""
    items = []
    for pct, level, kind, credits in ((h5, h5_level, 1, 512), (weekly, weekly_level, 2, 4096)):
        if level is None and pct is not None:
            level = pct / 100
        if level is not None:
            items.append([credits, level, kind, [[RESET_TS]]])
    WORLD.usage = items


def _reset_text():
    import datetime as dt
    return dt.datetime.fromtimestamp(RESET_TS, tz=dt.timezone.utc).astimezone().isoformat()


@pytest.mark.parametrize("h5,weekly", [(79, 50), (5, 89)])
def test_m1_meter_below_the_limits_runs(world, env, capfd, tmp_path, h5, weekly):
    set_meter(h5, weekly)
    code, st, _, _ = run(capfd, tmp_path, env)
    assert code == 0 and st["status"] == "ok" and WORLD.generate_calls == 1, st
    assert st["meter"] == "5h %d%%, weekly %d%%" % (h5, weekly), st
    assert "unreadable" not in st["reason"]
    # the meter comes from the usage info init already fetched: no second GetUsageInfo RPC
    assert WORLD.rpcids.count(GRPC.GET_USAGE_INFO) == 1, WORLD.rpcids


def test_m2_5h_at_the_limit_refuses_and_latches_nothing(world, env, capfd, tmp_path):
    set_meter(80, 10)
    e = api_env(env, tmp_path)  # a ready API backup: exit 1 must never trigger it
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 1 and st["status"] == "run_refused", st
    assert WORLD.api.calls == [] and set(st) == BASE_KEYS and st["via"] == "app", st
    assert "Google usage limit: 5h 80% used (stop at 80%)" in st["reason"], st["reason"]
    assert _reset_text() in st["reason"] and "weekly" not in st["reason"], st["reason"]
    assert st["meter"] == "5h 80%, weekly 10%" and st["job_id"] is None, st
    assert WORLD.generate_calls == 0 and st["submissions"] == 0
    assert not any(r[1].startswith(Endpoint.GENERATE) for r in WORLD.requests)
    assert log_entries(env) == []
    ok, why = lanew_log.check("t1", log_path=env["GEMINIPRO_LOG"], ceiling=12)
    assert ok, why
    set_meter(10, 10)
    code, st, _, _ = run(capfd, tmp_path, env, args=("t1", "again"))
    assert code == 0 and WORLD.generate_calls == 1, st


def test_m3_weekly_at_the_limit_and_both_over(world, env, capfd, tmp_path):
    set_meter(10, 90)
    code, st, _, _ = run(capfd, tmp_path, env)
    assert code == 1 and "weekly 90% used (stop at 90%)" in st["reason"], st
    assert "5h" not in st["reason"].split("Google usage limit:")[1]
    set_meter(95, 99)
    code, st, _, _ = run(capfd, tmp_path, env, args=("t1", "both"))
    assert code == 1 and "5h 95% used (stop at 80%)" in st["reason"], st
    assert "weekly 99% used (stop at 90%)" in st["reason"], st
    assert WORLD.generate_calls == 0 and log_entries(env) == []


@pytest.mark.parametrize("extra,h5,weekly,want", [
    ({"GEMINIPRO_MAX_5H_PCT": "50"}, 55, 10, 1),
    ({"GEMINIPRO_MAX_5H_PCT": "50"}, 49, 10, 0),
    ({"GEMINIPRO_MAX_WEEKLY_PCT": "100"}, 10, 99, 0),
    ({"GEMINIPRO_MAX_WEEKLY_PCT": "100"}, 10, 100, 1),
    ({"GEMINIPRO_MAX_5H_PCT": "0"}, 0, 0, 1),
])
def test_m4_custom_limits(world, env, capfd, tmp_path, extra, h5, weekly, want):
    set_meter(h5, weekly)
    code, st, _, _ = run(capfd, tmp_path, dict(env, **extra))
    assert code == want, st
    assert WORLD.generate_calls == (1 if want == 0 else 0)


@pytest.mark.parametrize("var", ["GEMINIPRO_MAX_5H_PCT", "GEMINIPRO_MAX_WEEKLY_PCT"])
@pytest.mark.parametrize("value", ["abc", "120", "-1", "nan"])
def test_m5_bad_limit_is_usage_error_before_any_browser_step(world, env, capfd, tmp_path, var,
                                                             value):
    code, st, _, _ = run(capfd, tmp_path, dict(env, **{var: value}))
    assert code == 64 and st["status"] == "usage_error" and var in st["reason"], st
    assert WORLD.harness_calls == 0 and WORLD.requests == [] and st["meter"] is None


@pytest.mark.parametrize("variant", ["no_usage_info", "weekly_missing", "not_a_number"])
def test_m6_unreadable_meter_does_not_block(world, env, capfd, tmp_path, variant):
    if variant == "no_usage_info":
        WORLD.usage = None
    elif variant == "weekly_missing":
        set_meter(10, None)
    else:
        set_meter(h5_level="high", weekly_level="high")
    e = dict(env, GEMINIPRO_MAX_5H_PCT="0", GEMINIPRO_MAX_WEEKLY_PCT="0")
    if variant == "weekly_missing":
        e = env  # the 5h window was read (10% < 80%); only the weekly one is unreadable
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 0 and WORLD.generate_calls == 1, st
    note = ("Google usage meter: weekly unreadable - not checked" if variant == "weekly_missing"
            else "Google usage meter unreadable - not checked")
    assert note in st["reason"], st["reason"]
    assert st["meter"] == ("5h 10%" if variant == "weekly_missing" else None), st


@pytest.mark.parametrize("h5,weekly,h5_level,weekly_level,over,unread", [
    (95, None, None, None, "5h 95% used (stop at 80%)", "weekly"),
    (None, 95, None, None, "weekly 95% used (stop at 90%)", "5h"),
    (95, None, None, "high", "5h 95% used (stop at 80%)", "weekly"),
    (None, 95, "high", None, "weekly 95% used (stop at 90%)", "5h"),
])
def test_r1_readable_window_over_limit_refuses_when_the_other_is_unreadable(
        world, env, capfd, tmp_path, h5, weekly, h5_level, weekly_level, over, unread):
    set_meter(h5, weekly, h5_level=h5_level, weekly_level=weekly_level)
    code, st, _, _ = run(capfd, tmp_path, env)
    assert code == 1 and st["status"] == "run_refused", st
    assert ("Google usage limit: " + over) in st["reason"], st["reason"]
    assert ("Google usage meter: %s unreadable - not checked" % unread) in st["reason"], st
    assert "Google usage meter unreadable" not in st["reason"], st["reason"]
    assert WORLD.generate_calls == 0 and st["submissions"] == 0 and log_entries(env) == []


def test_r1_both_windows_unreadable_runs_with_the_whole_meter_note(world, env, capfd, tmp_path):
    set_meter(h5_level="high", weekly_level=None)  # 5h not a number, weekly missing
    code, st, _, _ = run(capfd, tmp_path, dict(env, GEMINIPRO_MAX_5H_PCT="0",
                                               GEMINIPRO_MAX_WEEKLY_PCT="0"))
    assert code == 0 and WORLD.generate_calls == 1 and st["meter"] is None, st
    assert "Google usage meter unreadable - not checked" in st["reason"], st["reason"]
    assert "5h unreadable" not in st["reason"] and "weekly unreadable" not in st["reason"]


def test_g2_negative_zero_limit_prints_0(world, env, capfd, tmp_path):
    set_meter(0, 0)
    e = dict(env, GEMINIPRO_MAX_5H_PCT="-0", GEMINIPRO_MAX_WEEKLY_PCT="-0.0")
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 1 and "5h 0% used (stop at 0%)" in st["reason"], st["reason"]
    assert "weekly 0% used (stop at 0%)" in st["reason"] and "-0%" not in st["reason"], st
    code = gp.main(["--status"], e)
    out, _ = capfd.readouterr()
    assert "consults stop at 5h 0% / weekly 0%" in out.splitlines()[0], out


def test_m8_one_job_at_a_time_still_holds(world, env, capfd, tmp_path):
    sd = os.path.join(env["CLIPROXY_DIR"], "geminipro.d")
    os.makedirs(sd, exist_ok=True)
    holder = gp.FileLock(os.path.join(sd, "job.lock"))
    assert holder.try_acquire()
    try:
        code, st, _, _ = run(capfd, tmp_path, env)
    finally:
        holder.release()
    assert code == 5 and st["status"] == "no_slot" and WORLD.generate_calls == 0, st


def test_m9_api_backup_is_not_gated_by_the_meter(world, env, capfd, tmp_path):
    _harness_down()
    set_meter(99, 99)
    e = api_env(env, tmp_path, GEMINIPRO_MAX_5H_PCT="0", GEMINIPRO_MAX_WEEKLY_PCT="0")
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 0 and st["via"] == "api" and st["backup"] == "ok", st
    assert st["meter"] is None and len(WORLD.api.calls) == 1, st
    # an account mismatch (exit 8, after init read the meter) still sends meter null on the API path
    _harness_up()
    WORLD.accounts = {PSID: WRONG, OTHER_PSID: THIRD}
    code, st, _, _ = run(capfd, tmp_path, e, args=("t1", "again"))
    assert code == 0 and st["via"] == "api" and st["meter"] is None, st


def test_m10_status_summary_and_json_meter(world, env, capfd, tmp_path):
    set_meter(23, 8)
    code = gp.main(["--status", "--json"], env)
    out, _ = capfd.readouterr()
    st = json.loads(out)
    assert code == 0 and st["meter"] == "5h 23%, weekly 8%", st
    code = gp.main(["--status"], dict(env, GEMINIPRO_MAX_5H_PCT="70"))
    out, err = capfd.readouterr()
    r = _reset_text()
    assert code == 0, err
    assert out.splitlines()[0] == (
        "Gemini usage: 5h 23%% used (resets %s), weekly 8%% used (resets %s); consults stop at "
        "5h 70%% / weekly 90%%" % (r, r)), out
    assert "tier: PRO" in out and json.loads(err.strip().splitlines()[-1])["meter"] == (
        "5h 23%, weekly 8%")
    assert WORLD.generate_calls == 0


def test_slot_held_exit5(world, env, capfd, tmp_path):
    sd = os.path.join(env["CLIPROXY_DIR"], "geminipro.d")
    os.makedirs(sd, exist_ok=True)
    holder = gp.FileLock(os.path.join(sd, "job.lock"))
    assert holder.try_acquire()
    try:
        code, st, _, _ = run(capfd, tmp_path, env)
    finally:
        holder.release()
    assert code == 5 and WORLD.harness_calls == 0


# --------------------------------------------------------------------------
# R5 one submission, no resend, no re-init
# --------------------------------------------------------------------------

@pytest.mark.parametrize("mode", ["http500", "http429", "http403", "http302", "abort"])
def test_post_dispatch_failure_exit6_single_submission(world, env, capfd, tmp_path, mode):
    """G7/G1/G3: any non-200, block or redirect after dispatch is outcome_unknown, never resent."""
    WORLD.gen_mode = mode
    code, st, _, _ = run(capfd, tmp_path, env)
    assert code == 6 and WORLD.generate_calls == 1 and st["submissions"] == 1
    assert st["status"] == "outcome_unknown", st
    recs = log_entries(env)
    assert recs[-1]["status"] == "outcome_unknown" and recs[-1]["stop_latch"] is True
    if mode != "abort":
        assert mode[4:] in st["reason"]  # the HTTP status is named


def test_auth_loss_during_recovery_no_reinit_no_resend(world, env, capfd, tmp_path):
    WORLD.gen_mode = "recover_auth_loss"
    code, st, _, _ = run(capfd, tmp_path, env)
    assert code == 6 and st["status"] == "outcome_unknown"
    assert WORLD.generate_calls == 1
    inits = [r for r in WORLD.requests if r[1].startswith(Endpoint.INIT)]
    assert len(inits) == 1  # identity-proven session was never re-initialised
    urls = [r[1] for r in WORLD.requests]
    gen_at = max(i for i, u in enumerate(urls) if u.startswith(Endpoint.GENERATE))
    assert any(u.startswith(Endpoint.BATCH_EXEC) for u in urls[gen_at + 1:])  # recovery read ran
    assert "reinit" in gp.STATE.policy.refused and "401" in st["reason"]


@pytest.mark.parametrize("status", [429, 403, 500])
def test_init_rpc_failure_ends_at_once_naming_status(world, env, capfd, tmp_path, status):
    """G1: 403/429 at the init RPCs end the run with exit 6 (no brief submitted); a 500 is a
    preflight failure (exit 2) and the library's re-init is refused."""
    import time as _t
    WORLD.batch_fail = status
    t0 = _t.monotonic()
    code = gp.main(["--status", "--json"], dict(env, GEMINIPRO_TOTAL_DEADLINE="30"))
    st = json.loads(capfd.readouterr()[0])
    assert str(status) in st["reason"] and _t.monotonic() - t0 < 10
    if status in (403, 429):
        assert code == 6 and st["status"] == "blocked" and "no brief submitted" in st["reason"]
        assert len([r for r in WORLD.requests if r[1].startswith(Endpoint.BATCH_EXEC)]) == 1
    else:
        assert code == 2 and "nested-init" in gp.STATE.policy.refused
    WORLD.batch_fail = None
    code, st, _, _ = run(capfd, tmp_path, env)  # and a job: nothing sent, nothing logged
    assert code == 0


def test_library_retry_path_is_capped_at_one_submission(world):
    """The decorated generate_content retries; both guards keep it at one POST."""
    gp.STATE.new_run()
    gp.STATE.expected = RIGHT
    cand = gp.Candidate("AAAA1111", "test", PSID, PSIDTS, True)

    async def go(drop_verified):
        client = await gp.open_verified([cand], 30, {})
        model = gp.pick_model(client, "gemini-carbon")
        if drop_verified:  # let re-init through so the transport guard is what stops it
            gp.STATE.verified.discard(client)
            gp.STATE.reset_attempt()
        gp.STATE.policy.armed = True
        WORLD.gen_mode = "http500"
        try:
            await client.generate_content("x", model=model)
        finally:
            await gp.safe_close(client)

    for drop in (False, True):
        gp.STATE.new_run()
        gp.STATE.expected = RIGHT  # new_run() resets it to the module default
        WORLD.generate_calls = 0
        with pytest.raises(gp.PolicyAbort):
            asyncio.run(go(drop))
        assert WORLD.generate_calls == 1 and gp.STATE.policy.submissions == 1


def test_policy_refuses_rotate_upload_and_unarmed_generate():
    p = gp.Policy()
    for url in (Endpoint.ROTATE_COOKIES, Endpoint.UPLOAD, Endpoint.GENERATE):
        with pytest.raises(gp.PolicyAbort):
            p.check("POST", url)
    p.armed = True
    p.check("POST", Endpoint.GENERATE)
    with pytest.raises(gp.PolicyAbort):
        p.check("POST", Endpoint.GENERATE)
    assert p.submissions == 1


def test_empty_answer_and_error_card_exit6(world, env, capfd, tmp_path):
    WORLD.answer = "Something went wrong. Please try again."
    code, st, _, _ = run(capfd, tmp_path, env, args=("e1", "card"))
    assert code == 6 and "error card" in st["reason"]


def test_interrupts_exit130(world, env, capfd, tmp_path):
    for mode, run_name in (("cancel", "c1"), ("kbint", "c2")):
        WORLD.gen_mode = mode
        code, st, _, _ = run(capfd, tmp_path, env, args=(run_name, "x"))
        assert code == 130, (mode, st)
        assert log_entries(env)[-1]["status"] == "outcome_unknown"


# --------------------------------------------------------------------------
# R7 terminal record shape
# --------------------------------------------------------------------------

def test_r7_codex_and_openai_phrase_answers_record_ok(world, env, capfd, tmp_path):
    for i, ans in enumerate(("codex", "Quote: Your request was blocked by OpenAI's safety checks.")):
        WORLD.answer = ans
        code, st, _, _ = run(capfd, tmp_path, env, args=("r7", "n%d" % i))
        assert code == 0, st
        assert log_entries(env)[-1]["status"] == "ok"
    ok, reason = lanew_log.check("r7", log_path=env["GEMINIPRO_LOG"], ceiling=4)
    assert ok, reason
    status, _, entry = lanew_log.admit("r7", "probe", "m", None, None, log_path=env["GEMINIPRO_LOG"],
                                       ceiling=4)
    assert status == "admitted"


# --------------------------------------------------------------------------
# R1 / R4 harness child
# --------------------------------------------------------------------------

def _disable_envs_from_source():
    src = pathlib.Path(os.path.expanduser("~/Desktop/browser-harness/src/browser_harness/telemetry.py"))
    if not src.exists():
        return gp.TELEMETRY_DISABLE_ENVS
    m = re.search(r"DISABLE_ENVS\s*=\s*\(([^)]*)\)", src.read_text(encoding="utf-8"))
    return tuple(re.findall(r'"([A-Z_]+)"', m.group(1)))


def test_r1_harness_env_disables_telemetry_and_update(world, env, capfd, tmp_path):
    e = dict(env, BH_TELEMETRY="1", BH_UPDATE_CHECK="1", BU_AUTOSPAWN="1")
    assert run(capfd, tmp_path, e)[0] == 0
    he = WORLD.harness_env
    names = _disable_envs_from_source()
    assert names and all(he.get(n) == "0" for n in names)
    assert set(names) <= set(gp.TELEMETRY_DISABLE_ENVS)
    assert he["BH_UPDATE_CHECK"] == "0" and he["BH_REQUIRE_EXISTING_DAEMON"] == "1"
    assert "BU_AUTOSPAWN" not in he


def test_harness_script_reads_only():
    s = gp.HARNESS_SCRIPT
    for banned in ("new_tab", "switch_tab", "goto", "activate", "Target.activateTarget",
                   "Page.navigate", "Target.createTarget", "Target.closeTarget", "setCookie",
                   "Storage.setCookies", "type_text", "click"):
        assert banned not in s
    assert "Storage.getCookies" in s and "session_id=_bs" in s


@pytest.mark.parametrize("rc,out,errors", [
    (1, b"", ()),
    (0, b"not json " + PSID.encode(), ()),
    (0, None, ("cookies browser_ui: Session with given id not found",)),
])
def test_harness_failures_exit2_without_echo(world, env, capfd, tmp_path, rc, out, errors):
    WORLD.payload["rc"] = rc
    WORLD.payload["out"] = out if out is not None else harness_payload(errors=errors)
    WORLD.payload["err"] = b"browser-harness: required daemon 'default' is not running"
    code, st, o, e = run(capfd, tmp_path, env)
    assert code == 2 and WORLD.requests == []
    assert PSID not in o + e


def test_no_google_session_exit2(world, env, capfd, tmp_path):
    WORLD.payload["out"] = harness_payload(contexts=[{"ctx": "AAAA", "via": None, "psid": None,
                                                      "psidts": None}])
    assert run(capfd, tmp_path, env)[0] == 2


# --------------------------------------------------------------------------
# --status
# --------------------------------------------------------------------------

def test_status_reports_tier_models_credits(world, env, capfd, tmp_path):
    code = gp.main(["--status", "--json"], env)
    out, _ = capfd.readouterr()
    st = json.loads(out)
    assert code == 0 and st["account_ok"] is True and st["tier"] == "PRO"
    assert "gemini-carbon" in st["models"]
    assert st["credits_5h"]["remaining_credits"] == 512
    assert st["credits_weekly"]["remaining_credits"] == 4096
    assert st["abuse"]["is_clean"] is True
    assert WORLD.generate_calls == 0 and not os.path.exists(env["GEMINIPRO_LOG"])
    code = gp.main(["--status"], env)
    out, err = capfd.readouterr()
    assert code == 0 and "tier: PRO" in out and json.loads(err.strip().splitlines()[-1])["exit"] == 0


# --------------------------------------------------------------------------
# A6 cookies never on disk, never printed (success, failure, cancellation)
# --------------------------------------------------------------------------

class WriteSpy:
    def __init__(self, monkeypatch):
        self.paths = []
        real_open, real_io_open, real_os_open = builtins.open, io.open, os.open
        real_wt, real_wb = pathlib.Path.write_text, pathlib.Path.write_bytes
        real_mkdir = pathlib.Path.mkdir

        def rec(path):
            self.paths.append(os.fspath(path) if not isinstance(path, int) else "<fd>")

        def spy_open(file, mode="r", *a, **k):
            if any(c in mode for c in "wax+"):
                rec(file)
            return real_open(file, mode, *a, **k)

        def spy_io_open(file, mode="r", *a, **k):
            if any(c in mode for c in "wax+"):
                rec(file)
            return real_io_open(file, mode, *a, **k)

        def spy_os_open(path, flags, *a, **k):
            if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND):
                rec(path)
            return real_os_open(path, flags, *a, **k)

        def spy_wt(self_, *a, **k):
            rec(self_)
            return real_wt(self_, *a, **k)

        def spy_wb(self_, *a, **k):
            rec(self_)
            return real_wb(self_, *a, **k)

        def spy_mkdir(self_, *a, **k):
            rec(self_)
            return real_mkdir(self_, *a, **k)

        monkeypatch.setattr(builtins, "open", spy_open)
        monkeypatch.setattr(io, "open", spy_io_open)
        monkeypatch.setattr(os, "open", spy_os_open)
        monkeypatch.setattr(pathlib.Path, "write_text", spy_wt)
        monkeypatch.setattr(pathlib.Path, "write_bytes", spy_wb)
        monkeypatch.setattr(pathlib.Path, "mkdir", spy_mkdir)


def _scan(roots):
    hits = []
    for root in roots:
        root = str(root)
        if not os.path.exists(root):
            continue
        for dirpath, dirnames, files in os.walk(root):
            for n in dirnames + files:
                if any(s in n for s in SECRETS):
                    hits.append(os.path.join(dirpath, n))
            for n in files:
                p = os.path.join(dirpath, n)
                try:
                    data = open(p, "rb").read().decode("utf-8", "replace")
                except OSError:
                    continue
                if any(s in data for s in SECRETS):
                    hits.append(p)
    return hits


@pytest.mark.parametrize("mode", ["ok", "http500", "cancel"])
def test_a6_no_cookie_on_disk_or_output(world, env, capfd, tmp_path, monkeypatch, mode):
    import tempfile
    WORLD.gen_mode = mode
    # a planted cache entry for the right session with another PSIDTS: must never be read
    planted = WORLD.cache / (".cached_cookies_%s.json" % PSID)
    planted.write_text(json.dumps([{"name": "__Secure-1PSID", "value": PSID, "domain": ".google.com"},
                                   {"name": "__Secure-1PSIDTS", "value": CACHED_PSIDTS,
                                    "domain": ".google.com"}]))
    run(capfd, tmp_path, env)  # warm-up: lazy imports done before the spy
    capfd.readouterr()
    planted_bytes = planted.read_bytes()
    spy = WriteSpy(monkeypatch)
    code, st, out, err = run(capfd, tmp_path, env, args=("a6", mode), json_mode=False)
    monkeypatch.undo()
    assert code == {"ok": 0, "http500": 6, "cancel": 130}[mode]
    assert not any(s in out + err for s in SECRETS)
    # the real close() reached the save binding (neutralized), nothing was written
    assert gp.STATE.spy["save_cookies"] >= 1 and gp.STATE.spy["rotate"] == 0
    for p in spy.paths:
        assert not any(s in p for s in SECRETS), p
        inside = os.path.normcase(os.path.abspath(p)).startswith(
            os.path.normcase(os.path.abspath(str(tmp_path))))
        assert p.endswith(".pyc") or inside or "<fd>" in p, "write outside the test dirs: %s" % p
    roots = [tmp_path, os.path.join(tempfile.gettempdir(), "gemini_webapi"), gp._HARDENED["nocache"]]
    hits = [h for h in _scan(roots) if os.path.abspath(h) != os.path.abspath(str(planted))]
    assert hits == []
    assert planted.read_bytes() == planted_bytes          # cache untouched
    assert not os.path.exists(str(gp._HARDENED["nocache"]))
    sent_ts = {r[2].get("__Secure-1PSIDTS") for r in WORLD.requests}
    assert CACHED_PSIDTS not in sent_ts                     # cache never read


def test_a6_real_save_bindings_write_nothing(world, tmp_path):
    gp.harden()
    jar = Cookies()
    jar.set("__Secure-1PSID", PSID, domain=".google.com")
    jar.set("__Secure-1PSIDTS", PSIDTS, domain=".google.com")
    gp.STATE.new_run()
    for mod in ("gemini_webapi.client", "gemini_webapi.utils.rotate_1psidts", "gemini_webapi.utils"):
        sys.modules[mod].save_cookies(jar)
        sys.modules[mod].clear_cookies_cache(jar)
    assert gp.STATE.spy["save_cookies"] == 3
    assert list(WORLD.cache.iterdir()) == []
    assert sys.modules["gemini_webapi.utils.get_access_token"]._get_cookies_cache_path(jar) is None
    with pytest.raises(gp.PolicyAbort):
        asyncio.run(sys.modules["gemini_webapi.client"].rotate_1psidts(None))


# --------------------------------------------------------------------------
# fix round 1 (2026-11-13): G1-G12
# --------------------------------------------------------------------------

def _wrong_first():
    return harness_payload(contexts=[
        {"ctx": "BBBB2222", "via": "browser_ui/Network.getCookies", "psid": OTHER_PSID,
         "psidts": OTHER_PSIDTS},
        {"ctx": "AAAA1111", "via": "browser_ui/Network.getCookies", "psid": PSID, "psidts": PSIDTS}],
        default="BBBB2222")


def _init_gets():
    return [r for r in WORLD.requests if r[1].startswith(Endpoint.INIT)]


@pytest.mark.parametrize("status,body", [
    (403, "blocked"), (429, "Too many requests"), (200, "<html>Verify you are human</html>"),
    (200, "<html>Our systems have detected unusual traffic from your network</html>"),
    (401, "<form id=captcha-form></form>"), (302, ""), (301, "")])
def test_g1_g3_bootstrap_block_or_redirect_ends_whole_run(world, env, capfd, tmp_path, status, body):
    """The first context is challenged / blocked / redirected; the next (right) one is never tried."""
    WORLD.payload["out"] = _wrong_first()
    WORLD.init_status = {OTHER_PSID: (status, body)}
    code, st, _, _ = run(capfd, tmp_path, env)
    assert code == 6 and st["status"] == "blocked", st
    assert "no brief submitted" in st["reason"] and st["account_ok"] is None
    assert len(_init_gets()) == 1 and WORLD.generate_calls == 0 and st["submissions"] == 0
    assert not any(r[1].startswith(Endpoint.BATCH_EXEC) for r in WORLD.requests)
    assert not os.path.exists(env["GEMINIPRO_LOG"])
    if status != 200:
        assert str(status) in st["reason"]


def test_g1_block_on_every_context_is_not_account_mismatch(world, env, capfd, tmp_path):
    WORLD.init_status = {PSID: (403, "blocked"), OTHER_PSID: (403, "blocked")}
    code, st, _, _ = run(capfd, tmp_path, dict(env))
    assert code == 6 and st["status"] == "blocked" and len(_init_gets()) == 1


def test_g1_signed_out_page_still_moves_to_next_context(world, env, capfd, tmp_path):
    """Negative: an ordinary signed-out page (no challenge) is identity evidence, not a block."""
    WORLD.payload["out"] = _wrong_first()
    WORLD.init_status = {OTHER_PSID: (200, "<html>Sign in to continue</html>")}
    code, st, _, _ = run(capfd, tmp_path, env)
    assert code == 0 and len(_init_gets()) == 2 and WORLD.generate_calls == 1


def test_g1_block_after_admission_before_dispatch(world, env, capfd, tmp_path):
    WORLD.batch_fail_armed = 403
    code, st, _, _ = run(capfd, tmp_path, env)
    assert code == 6 and st["status"] == "blocked" and "no brief submitted" in st["reason"]
    assert WORLD.generate_calls == 0 and st["submissions"] == 0
    recs = log_entries(env)
    assert [r["status"] for r in recs] == ["started", "failed"] and recs[-1]["submissions"] == 0


def test_g3_every_guarded_request_disables_redirects(world, env, capfd, tmp_path):
    assert run(capfd, tmp_path, env)[0] == 0
    assert WORLD.kwargs and all(k.get("allow_redirects") is False for _, _, k in WORLD.kwargs), \
        [(m, u[:40], k.get("allow_redirects")) for m, u, k in WORLD.kwargs]


SHORT = "Qz9Qz9Qz9Qz9Qz9Q"  # 16 chars: the shortest value registered as a secret (H4)


@pytest.mark.parametrize("where", ["get", "stream"])
def test_g2_response_cookies_never_printed_or_saved(world, env, capfd, tmp_path, where):
    new = "NEWRESPONSECOOKIE" + uuid.uuid4().hex
    if where == "get":
        WORLD.get_cookie = ("__Secure-1PSIDTS", new)
    else:
        WORLD.stream_cookie = ("NID", new)
    WORLD.answer = "echo %s and %s" % (new, PSIDTS)
    code, st, out, err = run(capfd, tmp_path, env, json_mode=False)
    assert code == 0, st
    report = open(st["report"], encoding="utf-8").read()
    for s in (new, PSIDTS):
        assert s not in out + err and s not in report
    assert "[redacted]" in out


def test_g2_short_and_json_escaped_cookie_values_scrubbed_in_errors(world, env, capfd, tmp_path,
                                                                   monkeypatch):
    weird = "W\\E\"IRD\x07" + uuid.uuid4().hex[:12]   # 20 chars, escapes under repr and JSON
    WORLD.get_cookie = ("SIDCC", weird)

    async def post(self, url, *a, **k):
        self.cookies.set("OTZ", SHORT, domain=".google.com")
        raise ValueError("transport failure %s %s %s" % (weird, SHORT, PSID))

    monkeypatch.setattr(FakeSession, "post", post)
    code, st, out, err = run(capfd, tmp_path, env)
    assert code == 2, st
    for s in (weird, json.dumps(weird)[1:-1], repr(weird)[1:-1], SHORT, PSID):
        assert s not in out + err and s not in st["reason"], s   # decoded reason too (H5)
    assert "ValueError" in st["reason"]  # H5: type name + scrubbed str(), never repr()


def test_g2_harness_stderr_never_echoed(world, env, capfd, tmp_path):
    gp._SECRETS.clear()  # a fresh process: nothing registered yet
    WORLD.payload["rc"] = 1
    WORLD.payload["out"] = b""
    WORLD.payload["err"] = b"Traceback:\nRuntimeError: bad value " + PSID.encode()
    code, st, out, err = run(capfd, tmp_path, env)
    assert code == 2 and PSID not in out + err


def test_g4_harness_script_reads_default_jar_without_context_id(capfd):
    """Documented CDP responses (no defaultBrowserContextId): the default jar is still read,
    on the browser-target session, with no invented context id."""
    calls = []
    jar = [{"name": "__Secure-1PSID", "value": "DEFPSID", "domain": ".google.com"},
           {"name": "__Secure-1PSIDTS", "value": "DEFTS", "domain": ".google.com"}]

    def cdp(method, **kw):
        calls.append((method, kw))
        if method == "Target.getTargets":
            return {"targetInfos": [{"type": "page", "targetId": "p", "browserContextId": "prof"}]}
        if method == "Target.getBrowserContexts":
            return {"browserContextIds": []}
        if method == "Target.attachToBrowserTarget":
            return {"sessionId": "bs"}
        if method == "Storage.getCookies":
            return {"cookies": jar}
        if method == "Target.detachFromTarget":
            return {}
        raise AssertionError("unexpected CDP call %s" % method)

    exec(gp.HARNESS_SCRIPT, {"cdp": cdp})
    out = json.loads(capfd.readouterr()[0].strip().splitlines()[-1])
    assert out["default_jar"]["psid"] == "DEFPSID" and out["default_jar"]["ctx"] is None
    assert out["bc_fields"] == ["browserContextIds"]
    st = [kw for m, kw in calls if m == "Storage.getCookies"]
    assert st == [{"session_id": "bs"}]
    assert not any(m == "Target.attachToTarget" for m, _ in calls)  # no page target attached


def test_g4_default_only_candidate_is_used(world, env, capfd, tmp_path):
    WORLD.payload["out"] = harness_payload(
        contexts=[{"ctx": "BBBB2222", "via": "browser_ui/Network.getCookies", "psid": OTHER_PSID,
                   "psidts": OTHER_PSIDTS}],
        default=None, default_jar={"ctx": None, "via": "browser/Storage.getCookies", "psid": PSID,
                                   "psidts": PSIDTS}, bc_fields=("browserContextIds",))
    code, st, _, _ = run(capfd, tmp_path, env)
    assert code == 0 and st["context"].startswith("default")


def _memory(env):
    p = os.path.join(env["CLIPROXY_DIR"], "geminipro.d", "last-context")
    return open(p, encoding="utf-8").read().strip() if os.path.exists(p) else None


def _wrong_hits():
    return [r for r in WORLD.requests if r[2].get("__Secure-1PSID") == OTHER_PSID]


def test_g5_remembered_context_first_no_wrong_cookies_sent(world, env, capfd, tmp_path):
    WORLD.payload["out"] = _wrong_first()
    assert gp.main(["--status", "--json"], env) == 0
    capfd.readouterr()
    assert len(_wrong_hits()) == 1          # negative: without memory the wrong one is tried
    assert _memory(env) == "AAAA1111"       # only the proven context id is stored
    WORLD.requests.clear()
    for _ in range(2):
        assert gp.main(["--status", "--json"], env) == 0
        capfd.readouterr()
    code, st, _, err = run(capfd, tmp_path, env)
    assert code == 0 and _wrong_hits() == []
    assert "remembered context AAAA1111" in err
    data = open(os.path.join(env["CLIPROXY_DIR"], "geminipro.d", "last-context"), "rb").read()
    assert PSID.encode() not in data and PSIDTS.encode() not in data


def test_g5_remembered_context_now_wrong_falls_back_to_scan(world, env, capfd, tmp_path):
    os.makedirs(os.path.join(env["CLIPROXY_DIR"], "geminipro.d"))
    with open(os.path.join(env["CLIPROXY_DIR"], "geminipro.d", "last-context"), "w") as f:
        f.write("BBBB2222")
    code, st, _, _ = run(capfd, tmp_path, env)
    assert code == 0 and len(_wrong_hits()) == 1 and _memory(env) == "AAAA1111"


def test_g5_test_mode_never_writes_memory(world, env, capfd, tmp_path):
    e = dict(env, GEMINIPRO_TEST="1", GEMINIPRO_EXPECT_ACCOUNT=WRONG)
    assert gp.main(["--status", "--json"], e) == 0
    capfd.readouterr()
    assert _memory(env) is None


def test_g5_block_on_remembered_context_does_not_scan(world, env, capfd, tmp_path):
    WORLD.payload["out"] = _wrong_first()
    assert gp.main(["--status", "--json"], env) == 0
    capfd.readouterr()
    WORLD.requests.clear()
    WORLD.init_status = {PSID: (429, "slow down")}
    code, st, _, _ = run(capfd, tmp_path, env)
    assert code == 6 and _wrong_hits() == [] and len(_init_gets()) == 1


def test_g6_usage_refresh_after_answer_never_runs_answer_kept(world, env, capfd, tmp_path,
                                                            monkeypatch):
    real_post = FakeSession.post

    async def post(self, url, *a, **k):
        if WORLD.dispatched and url.startswith(Endpoint.BATCH_EXEC):
            WORLD.requests.append(("POST", url, self._jar()))
            return FakeResp(500)
        return await real_post(self, url, *a, **k)

    monkeypatch.setattr(FakeSession, "post", post)
    WORLD.answer = "ANSWER-391"
    code, st, out, _ = run(capfd, tmp_path, env, json_mode=False)
    assert code == 0 and out.strip() == "ANSWER-391", st
    assert "ANSWER-391" in open(st["report"], encoding="utf-8").read()
    urls = [r[1] for r in WORLD.requests]
    gen_at = max(i for i, u in enumerate(urls) if u.startswith(Endpoint.GENERATE))
    assert not any(u.startswith(Endpoint.BATCH_EXEC) for u in urls[gen_at + 1:])
    assert log_entries(env)[-1]["status"] == "ok"


@pytest.mark.parametrize("json_mode", [False, True])
def test_g6_report_write_failure_still_prints_answer(world, env, capfd, tmp_path, monkeypatch,
                                                   json_mode):
    WORLD.answer = "ANSWER-MARKER-391"

    def boom(self):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(gp.Wrapper, "write_report", boom)
    code, st, out, err = run(capfd, tmp_path, env, json_mode=json_mode)
    assert code == 3 and st["status"] == "log_failure"
    if json_mode:
        assert out.strip().count("\n") == 0 and "ANSWER-MARKER-391" in err
    else:
        assert "ANSWER-MARKER-391" in out


def _live_shape_user_status(code=None, models=True, length=25):
    """The live GetUserStatus shape seen 2026-11-13 on the PRO account: list(25), [14] null
    (no restriction code), [15] the model registry, [16] tier flags, [17] capability flags."""
    body = [None] * length
    if length > 17:
        body[14] = code
        body[15] = [CARBON, FAST, ["x1", "X", "x"], ["x2", "Y", "y"]] if models else None
        body[16], body[17] = [], []
    return body


@pytest.mark.parametrize("variant", ["missing", "null_no_models", "string", "short", "two_parts"])
def test_g8_user_status_must_be_positively_available(world, env, capfd, tmp_path, monkeypatch,
                                                    variant):
    real = _batch_body
    if variant == "missing":
        WORLD.omit_user_status = True
    elif variant == "string":
        WORLD.status_code = "1000"
    else:
        body = {"null_no_models": _live_shape_user_status(None, models=False),
                "short": _live_shape_user_status(None, length=10),
                "two_parts": None}[variant]

        def fake_body(rid):
            if rid == GRPC.GET_USER_STATUS and variant != "two_parts":
                return body
            return real(rid)

        monkeypatch.setattr(sys.modules[__name__], "_batch_body", fake_body)
        if variant == "two_parts":  # a hard-block part first (library skips it), then models
            real_post = FakeSession.post

            async def post(self, url, params=None, headers=None, data=None, **k):
                rids = (params or {}).get("rpcids", "")
                if rids == GRPC.GET_USER_STATUS:
                    WORLD.requests.append(("POST", url, self._jar()))
                    parts = [["wrb.fr", rids, json.dumps(_live_shape_user_status(1060, False)), None,
                              None, None, "generic"],
                             ["wrb.fr", rids, json.dumps(_live_shape_user_status(None)), None, None,
                              None, "generic"]]
                    return FakeResp(200, ")]}'\n\n" + json.dumps(parts))
                return await real_post(self, url, params=params, headers=headers, data=data, **k)

            monkeypatch.setattr(FakeSession, "post", post)
    code = gp.main(["--status", "--json"], env)
    st = json.loads(capfd.readouterr()[0])
    assert code == 2 and st["account_ok"] is not True and "GetUserStatus" in st["reason"], st
    code, st, _, _ = run(capfd, tmp_path, env)
    assert code == 2 and WORLD.generate_calls == 0 and not os.path.exists(env["GEMINIPRO_LOG"])


@pytest.mark.parametrize("code14", [None, 1000])
def test_g8_live_shape_null_code_with_models_is_available(world, env, capfd, tmp_path, monkeypatch,
                                                         code14):
    real = _batch_body
    monkeypatch.setattr(sys.modules[__name__], "_batch_body",
                        lambda rid: _live_shape_user_status(code14) if rid == GRPC.GET_USER_STATUS
                        else real(rid))
    code = gp.main(["--status", "--json"], env)
    st = json.loads(capfd.readouterr()[0])
    assert code == 0 and st["account_ok"] is True and "gemini-carbon" in st["models"], st


def test_g9_cancel_during_init_closes_client_and_emits(world, env, capfd, tmp_path, monkeypatch):
    closed = []
    real_close = FakeSession.close

    async def close(self):
        closed.append(self)
        await real_close(self)

    async def cancel(self, *a, **k):
        raise asyncio.CancelledError()

    monkeypatch.setattr(FakeSession, "close", close)
    monkeypatch.setattr(FakeSession, "post", cancel)
    code, st, _, _ = run(capfd, tmp_path, env)
    assert code == 130 and st["status"] == "interrupted" and closed
    lock = gp.FileLock(os.path.join(env["CLIPROXY_DIR"], "geminipro.d", "job.lock"))
    assert lock.try_acquire()
    lock.release()


def test_g9_interrupt_during_finalization_still_emits_and_releases(world, env, capfd, tmp_path,
                                                                  monkeypatch):
    WORLD.gen_mode = "http500"

    def interrupt(*a, **k):
        raise KeyboardInterrupt()

    monkeypatch.setattr(gp.lanew_log, "append_line_verified", interrupt)
    code, st, _, _ = run(capfd, tmp_path, env)
    assert code == 130 and st["status"] == "interrupted" and "outcome unknown" in st["reason"]
    lock = gp.FileLock(os.path.join(env["CLIPROXY_DIR"], "geminipro.d", "job.lock"))
    assert lock.try_acquire()
    lock.release()


def test_g10_slow_stdin_bounded_by_total_deadline(world, env, capfd, monkeypatch):
    import time as _t

    class SlowInput:
        def isatty(self):
            return False

        def read(self):
            _t.sleep(3)
            return "brief-check: clean - x\nhello\n"

    monkeypatch.setattr(sys, "stdin", SlowInput())
    t0 = _t.monotonic()
    code = gp.main(["r", "n", "--json"], dict(env, GEMINIPRO_TOTAL_DEADLINE="1"))
    took = _t.monotonic() - t0
    st = json.loads(capfd.readouterr()[0])
    assert code == 5 and st["status"] == "deadline" and took < 2.0
    assert WORLD.harness_calls == 0


def test_g10_backstop_armed_through_finalization(world, env, capfd, tmp_path, monkeypatch):
    import time as _t
    monkeypatch.setattr(gp, "JOB_MIN", 0)
    monkeypatch.setattr(gp, "BACKSTOP_GRACE", 1)
    WORLD.gen_mode = "http500"
    real_append = gp.lanew_log.append_line_verified

    def slow_append(path, line):
        if '"status": "started"' not in line:
            _t.sleep(4)  # the terminal record hangs past deadline + grace
        return real_append(path, line)

    monkeypatch.setattr(gp.lanew_log, "append_line_verified", slow_append)
    code, st, out, err = run(capfd, tmp_path, dict(env, GEMINIPRO_TOTAL_DEADLINE="2"))
    lines = [l for l in out.splitlines() if l.startswith("{")]
    assert WORLD.hard_exits == [6] and len(lines) == 1
    assert "hard backstop" in json.loads(lines[0])["reason"]


def test_g11_json_mode_honoured_on_early_usage_errors(world, env, capfd):
    for argv in (["--bad", "--json"], ["--help", "--json"], ["--model", "--json"]):
        code = gp.main(argv, env)
        out, err = capfd.readouterr()
        assert code == 64 and json.loads(out)["exit"] == 64, argv


def test_g12_library_version_pinned(world, env, capfd, tmp_path, monkeypatch):
    monkeypatch.setattr(gp, "_library_version", lambda: "2.2.0", raising=False)
    code, st, _, _ = run(capfd, tmp_path, env)
    assert code == 2 and "2.2.0" in st["reason"] and WORLD.harness_calls == 0
    code = gp.main(["--status", "--json"], env)
    assert code == 2 and WORLD.harness_calls == 0
    capfd.readouterr()


# --------------------------------------------------------------------------
# fix round 2 (2026-11-13): H1-H8
# --------------------------------------------------------------------------

def _remember_right(env):
    d = os.path.join(env["CLIPROXY_DIR"], "geminipro.d")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "last-context"), "w") as f:
        f.write("AAAA1111")


def _google_gets():
    return [r for r in WORLD.requests if r[1].startswith(Endpoint.GOOGLE)]


@pytest.mark.parametrize("ecode", ["HTTP2_STREAM", "PARTIAL_FILE", "RECV_ERROR"])
@pytest.mark.parametrize("mode", ["status", "job"])
def test_h1_bootstrap_transport_error_is_preflight_exit2(world, env, capfd, tmp_path, monkeypatch,
                                                         ecode, mode):
    """Reviewer probe P15: the remembered right context's /app GET dies with a curl error
    raised exactly as curl_cffi raises it. Exit 2; no google.com preflight, no other context."""
    from curl_cffi.const import CurlECode
    from curl_cffi.requests.exceptions import code2error
    real_get = FakeSession.get
    ec = getattr(CurlECode, ecode)
    msg = "curl: (%d) simulated transport failure %s" % (int(ec), ecode)
    err = code2error(ec, msg)(msg, ec, FakeResp(200 if ecode != "RECV_ERROR" else 0))

    async def get(self, url, headers=None, **k):
        if url.startswith(Endpoint.GOOGLE):
            WORLD.requests.append(("GET", url, self._jar()))
            self.cookies.set("AEC", "ANONCOOKIE" + uuid.uuid4().hex, domain=".google.com")
            return FakeResp(200, "<html>google</html>")
        if url.startswith(Endpoint.INIT) and self._jar().get("__Secure-1PSID") == PSID:
            WORLD.requests.append(("GET", url, self._jar()))
            raise err
        return await real_get(self, url, headers=headers, **k)

    monkeypatch.setattr(FakeSession, "get", get)
    _remember_right(env)
    if mode == "status":
        code = gp.main(["--status", "--json"], env)
        st = json.loads(capfd.readouterr()[0])
    else:
        code, st, _, _ = run(capfd, tmp_path, env)
    assert code == 2 and st["status"] == "preflight_refused" and st["account_ok"] is None, st
    assert _google_gets() == [] and _wrong_hits() == [] and len(_init_gets()) == 1
    assert WORLD.generate_calls == 0 and st["submissions"] == 0
    assert not os.path.exists(env["GEMINIPRO_LOG"])


def _status_post(monkeypatch, second):
    real_post = FakeSession.post

    async def post(self, url, params=None, headers=None, data=None, **k):
        rids = (params or {}).get("rpcids", "")
        if rids == GRPC.GET_USER_STATUS:
            WORLD.requests.append(("POST", url, self._jar()))
            good = json.dumps(_live_shape_user_status(None))
            body2 = {"blocked_1060": json.dumps(_live_shape_user_status(1060, False)),
                     "unauth_1016": json.dumps(_live_shape_user_status(1016)),
                     "duplicate": good, "malformed": "{broken", "reject_7": None}[second]
            parts = [["wrb.fr", rids, good, None, None, None, "generic"],
                     ["wrb.fr", rids, body2, None, None, [7] if second == "reject_7" else None,
                      "generic"]]
            return FakeResp(200, ")]}'\n\n" + json.dumps(parts))
        return await real_post(self, url, params=params, headers=headers, data=data, **k)

    monkeypatch.setattr(FakeSession, "post", post)


@pytest.mark.parametrize("second,expect", [("blocked_1060", 2), ("duplicate", 2), ("malformed", 2),
                                           ("unauth_1016", 8), ("reject_7", 8)])
def test_h2_every_user_status_part_the_server_sent_is_counted(world, env, capfd, tmp_path,
                                                              monkeypatch, second, expect):
    """A good part FIRST hides nothing: the library's early-returning consumer sees only the
    first part, but every part of the response is counted."""
    _status_post(monkeypatch, second)
    code = gp.main(["--status", "--json"], env)
    st = json.loads(capfd.readouterr()[0])
    assert code == expect and st["account_ok"] is not True and "GetUserStatus" in st["reason"], st
    if second == "blocked_1060":
        assert "LOCATION_REJECTED" in st["reason"]
    code, st, _, _ = run(capfd, tmp_path, env)
    assert code == expect and WORLD.generate_calls == 0 and st["submissions"] == 0
    assert not os.path.exists(env["GEMINIPRO_LOG"])


def _partial_stream(text, prefix=True):
    cand = ["rc_1", [text], None, None, None, None, None, None, [1]]  # [8][0] != 2: not complete
    inner = [None, ["c_1", "r_1"], None, None, [cand]]
    return (")]}'\n\n" if prefix else "") + _frame([["wrb.fr", None, json.dumps(inner)]])


def _gen_stream(monkeypatch, chunks, exit_error=None):
    @contextlib.asynccontextmanager
    async def stream(self, method, url, **k):
        WORLD.requests.append((method, url, self._jar()))
        WORLD.kwargs.append((method, url, dict(k)))
        WORLD.generate_calls += 1
        WORLD.dispatched = True
        yield FakeResp(200, chunks=list(chunks))
        if exit_error is not None:
            raise exit_error

    monkeypatch.setattr(FakeSession, "stream", stream)


@pytest.mark.parametrize("failure", ["read_error", "reset_error", "stream_exit_error"])
def test_h3_completed_frame_then_stream_error_keeps_answer(world, env, capfd, tmp_path, monkeypatch,
                                                           failure):
    done = _answer_stream("ANSWER-MARKER-391").encode()
    if failure == "read_error":
        _gen_stream(monkeypatch, [done, OSError("read failed after the completed frame")])
    elif failure == "reset_error":
        _gen_stream(monkeypatch, [done, ConnectionResetError("reset at end")])
    else:
        _gen_stream(monkeypatch, [done], exit_error=OSError("stream exit failed"))
    code, st, out, err = run(capfd, tmp_path, env, json_mode=False)
    assert code == 0 and st["status"] == "ok" and out.strip() == "ANSWER-MARKER-391", st
    assert "ANSWER-MARKER-391" in open(st["report"], encoding="utf-8").read()
    assert WORLD.generate_calls == 1 and st["submissions"] == 1
    assert log_entries(env)[-1]["status"] == "ok"


@pytest.mark.parametrize("frames", ["partial", "done_then_partial"])
def test_h3_partial_frame_then_stream_error_is_never_promoted(world, env, capfd, tmp_path,
                                                             monkeypatch, frames):
    """Negative: without Gemini's completion marker on the latest frame a chunk is never
    taken as the answer (a marked frame followed by an unmarked one is not complete)."""
    chunks = [_partial_stream("PARTIAL-391").encode(), OSError("read failed")]
    if frames == "done_then_partial":  # the later frame continues the same stream (no prefix)
        chunks = [_answer_stream("ANSWER-MARKER-391").encode(),
                  _partial_stream("PARTIAL-391", prefix=False).encode(), OSError("read failed")]
    _gen_stream(monkeypatch, chunks)
    code, st, out, err = run(capfd, tmp_path, env, json_mode=False)
    assert code == 6 and st["status"] == "outcome_unknown", st
    assert "PARTIAL" not in out + err and "ANSWER-MARKER" not in out + err
    assert not os.path.exists(st["report"])
    assert WORLD.generate_calls == 1 and log_entries(env)[-1]["status"] == "outcome_unknown"


@pytest.mark.parametrize("stop", ["cancel", "kbint"])
def test_h3_interrupt_in_stream_after_completed_frame_keeps_answer(world, env, capfd, tmp_path,
                                                                   monkeypatch, stop):
    done = _answer_stream("ANSWER-MARKER-391").encode()
    _gen_stream(monkeypatch, [done, asyncio.CancelledError() if stop == "cancel"
                              else KeyboardInterrupt()])
    code, st, out, err = run(capfd, tmp_path, env, json_mode=False)
    _answer_kept(env, st, out)
    assert "ANSWER-MARKER-391" in open(st["report"], encoding="utf-8").read()


def test_h5_library_repr_wrapped_stream_error_is_scrubbed(world, env, capfd, tmp_path, monkeypatch):
    """gemini_webapi wraps a stream error as APIError('...({type}: {e!r})') (client.py:2063):
    the repr-escaped spelling of a registered value is scrubbed too."""
    weird = "W\\E\"IRD'Q\x07" + uuid.uuid4().hex[:12]
    WORLD.get_cookie = ("SIDCC", weird)
    _gen_stream(monkeypatch, [ValueError("stream died near " + weird)])
    code, st, out, err = run(capfd, tmp_path, env)
    assert code == 6 and st["status"] == "outcome_unknown", st
    assert "APIError" in st["reason"] and "[redacted]" in st["reason"], st["reason"]
    for s in (weird, repr(weird)[1:-1], json.dumps(weird)[1:-1],
              weird.encode("unicode_escape").decode("ascii")):
        assert s not in st["reason"] and s not in out + err, s


def _answer_kept(env, st, out, code=0):
    assert st["exit"] == code and "ANSWER-MARKER-391" in out, st
    assert log_entries(env)[-1]["status"] == "ok" and WORLD.generate_calls == 1


def test_h3_cancel_during_close_after_answer_keeps_it(world, env, capfd, tmp_path, monkeypatch):
    async def close(self):
        if WORLD.dispatched:
            raise asyncio.CancelledError()

    monkeypatch.setattr(FakeSession, "close", close)
    WORLD.answer = "ANSWER-MARKER-391"
    code, st, out, err = run(capfd, tmp_path, env, json_mode=False)
    _answer_kept(env, st, out)
    assert "ANSWER-MARKER-391" in open(st["report"], encoding="utf-8").read()


def test_h3_deadline_during_close_after_answer_keeps_it(world, env, capfd, tmp_path, monkeypatch):
    monkeypatch.setattr(gp, "JOB_MIN", 0)

    async def slow_close(self):
        if WORLD.dispatched:
            await asyncio.sleep(5)

    monkeypatch.setattr(FakeSession, "close", slow_close)
    WORLD.answer = "ANSWER-MARKER-391"
    code, st, out, err = run(capfd, tmp_path, dict(env, GEMINIPRO_TOTAL_DEADLINE="3"),
                             json_mode=False)
    _answer_kept(env, st, out)
    assert os.path.exists(st["report"])


def test_h3_interrupt_while_writing_report_keeps_answer(world, env, capfd, tmp_path, monkeypatch):
    def boom(self):
        raise KeyboardInterrupt()

    monkeypatch.setattr(gp.Wrapper, "write_report", boom)
    WORLD.answer = "ANSWER-MARKER-391"
    code, st, out, err = run(capfd, tmp_path, env, json_mode=False)
    _answer_kept(env, st, out, code=3)
    assert st["status"] == "log_failure" and "interrupted" in st["reason"]


def test_h3_internal_error_while_writing_report_keeps_answer(world, env, capfd, tmp_path,
                                                            monkeypatch):
    def boom(self):
        raise ValueError("offline failure " + PSID)

    monkeypatch.setattr(gp.Wrapper, "write_report", boom)
    WORLD.answer = "ANSWER-MARKER-391"
    code, st, out, err = run(capfd, tmp_path, env, json_mode=False)
    _answer_kept(env, st, out, code=3)
    assert PSID not in out + err and "ValueError" in st["reason"]


def test_h3_backstop_with_answer_in_hand_prints_it(world, env, capfd, tmp_path, monkeypatch):
    import time as _t
    monkeypatch.setattr(gp, "JOB_MIN", 0)
    monkeypatch.setattr(gp, "BACKSTOP_GRACE", 1)
    WORLD.answer = "ANSWER-MARKER-391"
    real_append = gp.lanew_log.append_line_verified

    def slow_append(path, line):
        if '"status": "started"' not in line:
            _t.sleep(4)  # the terminal record hangs past deadline + grace
        return real_append(path, line)

    monkeypatch.setattr(gp.lanew_log, "append_line_verified", slow_append)
    bf = tmp_path / "b.md"
    bf.write_bytes(CLEAN)
    # HARD_EXIT is a no-op here, so main() goes on after the backstop (in production the
    # process is gone): only the backstop's line and exit code are checked
    gp.main(["t1", "carbon", "--brief-file", str(bf), "--json"], dict(env, GEMINIPRO_TOTAL_DEADLINE="2"))
    out, err = capfd.readouterr()
    lines = [l for l in out.splitlines() if l.startswith("{")]
    assert WORLD.hard_exits == [3] and len(lines) == 1, (WORLD.hard_exits, lines)
    hard = json.loads(lines[0])
    assert hard["exit"] == 3 and "hard backstop" in hard["reason"]
    assert "ANSWER-MARKER-391" in err  # --json: the answer goes to stderr


@pytest.mark.parametrize("val", ["0", "1", "e", "39", "r2tag", "A" * 15])
def test_h4_short_cookie_values_are_not_secrets_json_stays_valid(world, env, capfd, tmp_path, val):
    WORLD.get_cookie = ("X_SHORT", val)
    code, st, out, err = run(capfd, tmp_path, env, json_mode=False)  # run() json-parses the line
    assert code == 0 and st["exit"] == 0 and out.strip() == "391", st
    assert val not in gp._SECRETS and "redacted" not in out + err
    code = gp.main(["--status", "--json"], env)
    out, _ = capfd.readouterr()
    st = json.loads(out)
    assert code == 0 and st["exit"] == 0 and st["credits_5h"]["remaining_credits"] == 512
    assert st["tool"] == "geminipro" and st["submissions"] == 0


def test_h4_sixteen_char_value_is_scrubbed_exactly_once(world, env, capfd, tmp_path):
    secret = "S" * 15 + "T"
    WORLD.get_cookie = ("NID", secret)
    WORLD.answer = "x %s y" % secret
    code, st, out, err = run(capfd, tmp_path, env, json_mode=False)
    assert code == 0 and out.strip() == "x [redacted] y", out
    report = open(st["report"], encoding="utf-8").read()
    assert "x [redacted] y" in report and secret not in report


def test_h5_no_repr_formatting_in_the_script():
    src = open(gp.__file__, encoding="utf-8").read()
    bad = r"\brepr\((?!\))|%r|!r\}"  # a call with an argument (the docstring names "repr()")
    assert not re.search(bad, src), re.findall(r".*(?:%s).*" % bad, src)
    assert "format_exc" not in src


def test_h6_deadline_checked_right_before_dispatch(world, env, capfd, tmp_path, monkeypatch):
    """Reviewer probe P122 (admission): the clock passes the deadline after admission; the
    transport guard refuses the prompt POST - exit 5, nothing sent."""
    real_monotonic = gp.time.monotonic
    offset = [0.0]
    monkeypatch.setattr(gp.time, "monotonic", lambda: real_monotonic() + offset[0])
    original = gp.Wrapper.admit

    def late_admit(self):
        original(self)
        offset[0] = self.deadline - real_monotonic() + 1.0

    monkeypatch.setattr(gp.Wrapper, "admit", late_admit)
    code, st, out, err = run(capfd, tmp_path, env)
    assert code == 5 and st["status"] == "deadline" and "nothing sent" in st["reason"], st
    assert WORLD.generate_calls == 0 and st["submissions"] == 0
    assert log_entries(env)[-1]["status"] == "failed"


def test_h6_policy_refuses_generate_after_deadline():
    import time as _t
    p = gp.Policy()
    p.armed = True
    p.deadline = _t.monotonic() - 1
    with pytest.raises(gp.PolicyAbort):
        p.check("POST", Endpoint.GENERATE)
    assert p.submissions == 0
    p.deadline = _t.monotonic() + 60   # negative: before the deadline it goes through
    p.check("POST", Endpoint.GENERATE)
    assert p.submissions == 1


@pytest.mark.parametrize("error", ["cookies browser_ui: No session with given id",
                                   "detach: no session with given id 7",
                                   "attach browser_ui: SESSION WITH GIVEN ID NOT FOUND"])
def test_h7_stale_session_variants_exit2(world, env, capfd, tmp_path, error):
    WORLD.payload["out"] = harness_payload(errors=[error])
    code, st, _, _ = run(capfd, tmp_path, env)
    assert code == 2 and "stale CDP session" in st["reason"] and WORLD.requests == []


@pytest.mark.parametrize("exc", [BrokenPipeError(32, "Broken pipe"), OSError(22, "Invalid argument"),
                                 KeyboardInterrupt()])
def test_h8_answer_write_failure_still_emits_status_line(world, env, capfd, tmp_path, monkeypatch,
                                                         exc):
    timers = []
    real_timer = gp.threading.Timer

    def timer(*a, **k):
        t = real_timer(*a, **k)
        timers.append(t)
        return t

    def boom(self, stream):
        raise exc

    monkeypatch.setattr(gp.threading, "Timer", timer)
    monkeypatch.setattr(gp.Wrapper, "print_answer", boom)
    bf = tmp_path / "b.md"
    bf.write_bytes(CLEAN)
    try:
        code = gp.main(["t1", "carbon", "--brief-file", str(bf)], env)
    except KeyboardInterrupt:
        code = "escaped"  # never let it abort the pytest session
    finally:
        escaped = [t for t in timers if not t.finished.is_set()]
        for t in timers:
            t.cancel()
    out, err = capfd.readouterr()
    lines = [l for l in err.splitlines() if l.startswith("{")]
    assert code == 0 and len(lines) == 1 and json.loads(lines[0])["exit"] == 0, (code, lines)
    assert timers and escaped == []  # watchdog cancelled by main itself


def test_h8_status_summary_write_failure_still_emits_status_line(world, env, capfd, monkeypatch):
    def boom(self):
        raise OSError(22, "Invalid argument")

    monkeypatch.setattr(gp.Wrapper, "print_status_summary", boom)
    code = gp.main(["--status"], env)
    out, err = capfd.readouterr()
    lines = [l for l in err.splitlines() if l.startswith("{")]
    assert code == 0 and len(lines) == 1 and json.loads(lines[0])["exit"] == 0


def test_h8_interrupt_while_building_status_line_retries_once(world, env, capfd, tmp_path,
                                                              monkeypatch):
    real_line = gp.Wrapper.status_line
    calls = []

    def flaky(self, r):
        calls.append(r.code)
        if len(calls) == 1:
            raise KeyboardInterrupt()
        return real_line(self, r)

    monkeypatch.setattr(gp.Wrapper, "status_line", flaky)
    bf = tmp_path / "b.md"
    bf.write_bytes(CLEAN)
    try:
        code = gp.main(["t1", "carbon", "--brief-file", str(bf), "--json"], env)
    except KeyboardInterrupt:
        code = "escaped"
    out, err = capfd.readouterr()
    lines = [l for l in out.splitlines() if l.startswith("{")]
    assert code == 0 and len(lines) == 1 and json.loads(lines[0])["exit"] == 0, (code, out)


# --------------------------------------------------------------------------
# API backup (2026-11-15): exit 2 / 8 before admission -> the same brief, once, through
# the gemini-api CLI seam (gp._run_api); offline, the seam is always FakeApi
# --------------------------------------------------------------------------

SERVER_ERR = api_err(1, "service_unavailable", "server_error", "high demand")


def api_env(env, tmp_path, **extra):
    """env with a key and an explicit fake CLI path (a plain file: the seam never runs it)."""
    cli = tmp_path / "fake-gemini-api.exe"
    cli.write_bytes(b"")
    return dict(env, GEMINI_API_KEY=API_KEY, GEMINIPRO_API_CLI=str(cli), **extra)


def _harness_down():
    WORLD.payload["rc"] = 1
    WORLD.payload["out"] = b""
    WORLD.payload["err"] = b"browser-harness: required daemon 'default' is not running"


def _harness_up():
    WORLD.payload.update(rc=0, out=harness_payload(), err=b"")


def _api_dirs(env):
    sd = os.path.join(env["CLIPROXY_DIR"], "geminipro.d")
    return [n for n in os.listdir(sd) if os.path.isdir(os.path.join(sd, n))] if os.path.isdir(sd) else []


def test_api_a1_exit2_backup_answers(world, env, capfd, tmp_path):
    e = api_env(env, tmp_path)
    _harness_down()
    WORLD.api.script = [api_ok("API-ANSWER-391")]
    code, st, out, err = run(capfd, tmp_path, e)
    assert code == 0 and st["status"] == "ok" and st["via"] == "api" and st["backup"] == "ok", st
    assert st["primary_exit"] == 2 and "browser-harness" in st["primary_reason"]
    assert st["model"] == "gemini-4-hydrogen" and st["requested_model"] == "gemini-carbon"
    assert st["submissions"] == 0 and st["context"] is None and st["account_ok"] is None
    assert set(st) == BASE_KEYS | TRIGGER_KEYS
    report = open(st["report"], encoding="utf-8").read()
    assert "API-ANSWER-391" in report and "- via: api (backup; app path exit 2)" in report
    assert "- account: n/a (API key)" in report
    recs = log_entries(env)
    assert [r["status"] for r in recs] == ["started", "ok"]
    assert recs[0]["model"] == "gemini-4-hydrogen" and recs[1]["job_id"] == st["job_id"]
    assert recs[1]["via"] == "api" and recs[1]["primary_exit"] == 2
    assert len(WORLD.api.calls) == 1 and WORLD.generate_calls == 0
    assert _api_dirs(env) == []


def test_api_a2_exit8_backup_answers(world, env, capfd, tmp_path):
    WORLD.accounts = {PSID: WRONG, OTHER_PSID: THIRD}
    WORLD.api.script = [api_ok("API-ANSWER-391")]
    code, st, out, err = run(capfd, tmp_path, api_env(env, tmp_path), json_mode=False)
    assert code == 0 and st["status"] == "ok" and st["via"] == "api" and st["backup"] == "ok", st
    assert st["primary_exit"] == 8 and st["account_ok"] is False and st["context"] is None
    assert st["model"] == "gemini-4-hydrogen" and st["requested_model"] == "gemini-carbon"
    assert out.strip() == "API-ANSWER-391" and WORLD.generate_calls == 0 and st["submissions"] == 0
    recs = log_entries(env)
    assert [r["status"] for r in recs] == ["started", "ok"] and recs[1]["primary_exit"] == 8
    assert "app path exit 8" in open(st["report"], encoding="utf-8").read()


def test_api_a2_unauthenticated_after_context_proven_keeps_context_null(world, env, capfd, tmp_path):
    WORLD.status_code = 1016  # open_verified fills the context, then exits 8
    code, st, _, _ = run(capfd, tmp_path, api_env(env, tmp_path))
    assert code == 0 and st["via"] == "api" and st["primary_exit"] == 8, st
    assert st["context"] is None and st["account_ok"] is False


def _a3_cap(env, tmp_path, capfd):
    e = dict(env, GEMINIPRO_RUN_JOB_CEILING="1")
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 0 and st["via"] == "app" and set(st) == BASE_KEYS  # app path, no trigger
    return run(capfd, tmp_path, e, args=("t1", "again"))


def _a3_slot(env, tmp_path, capfd):
    sd = os.path.join(env["CLIPROXY_DIR"], "geminipro.d")
    os.makedirs(sd, exist_ok=True)
    holder = gp.FileLock(os.path.join(sd, "job.lock"))
    assert holder.try_acquire()
    try:
        return run(capfd, tmp_path, env)
    finally:
        holder.release()


def _a3_block(env, tmp_path, capfd):
    WORLD.init_status = {PSID: (403, "blocked"), OTHER_PSID: (403, "blocked")}
    return run(capfd, tmp_path, env)


A3_CASES = {
    "cap_1": (1, _a3_cap),
    "model_4": (4, lambda e, t, c: run(c, t, e, args=("t1", "m", "--model", "gemini-nonesuch"))),
    "slot_5": (5, _a3_slot),
    "block_6": (6, _a3_block),
    "gate_7": (7, lambda e, t, c: run(c, t, e, brief=b"What is 17*23?\n")),
    "blank_account_2": (2, lambda e, t, c: run(c, t, dict(e, GEMINIPRO_ACCOUNT="  "))),
    "test_only_2": (2, lambda e, t, c: run(c, t, dict(e, GEMINIPRO_EXPECT_ACCOUNT=WRONG))),
    "usage_64": (64, lambda e, t, c: run(c, t, e, args=("bad run", "x"))),
}


@pytest.mark.parametrize("case", sorted(A3_CASES))
def test_api_a3_other_exits_never_trigger(world, env, capfd, tmp_path, case):
    expect, fn = A3_CASES[case]
    code, st, _, _ = fn(api_env(env, tmp_path), tmp_path, capfd)
    assert code == expect, st
    assert WORLD.api.calls == [] and st["via"] == "app" and set(st) == BASE_KEYS, st
    assert "API backup" not in st["reason"]


def test_api_a3_deadline_5_never_triggers(world, env, capfd, tmp_path, monkeypatch):
    monkeypatch.setattr(gp, "JOB_MIN", 200)  # > the 120 s deadline: job_async's own exit 5
    code, st, _, _ = run(capfd, tmp_path, api_env(env, tmp_path))
    assert code == 5 and st["status"] == "deadline", st
    assert WORLD.api.calls == [] and set(st) == BASE_KEYS and st["via"] == "app"


A4_CASES = {
    "backup_off": ({"GEMINIPRO_API_BACKUP": "0"}, "GEMINIPRO_API_BACKUP"),
    "key_unset": ({"GEMINI_API_KEY": None}, "GEMINI_API_KEY"),
    "key_blank": ({"GEMINI_API_KEY": "   "}, "GEMINI_API_KEY"),
    "key_short": ({"GEMINI_API_KEY": "Ab3" * 5}, "GEMINI_API_KEY is too short to be a key"),
    "cli_missing": ({"GEMINIPRO_API_CLI": "MISSING"}, "not found"),
    "cli_not_on_path": ({"GEMINIPRO_API_CLI": None}, "gemini-api is not on PATH"),
    "time_left": ({}, "left before the total deadline"),
    "key_in_brief": ({}, "the brief contains the API key"),
}


@pytest.mark.parametrize("case", sorted(A4_CASES))
def test_api_a4_backup_not_run(world, env, capfd, tmp_path, monkeypatch, case):
    change, why = A4_CASES[case]
    e = api_env(env, tmp_path)
    for k, v in change.items():
        if v is None:
            e.pop(k, None)
        else:
            e[k] = str(tmp_path / "no-such-cli.exe") if v == "MISSING" else v
    if case == "time_left":
        monkeypatch.setattr(gp, "JOB_MIN", 200)  # over the 120 s deadline: the backup cannot fit
    made = []
    real_mkdtemp = gp.tempfile.mkdtemp
    monkeypatch.setattr(gp.tempfile, "mkdtemp",
                        lambda *a, **k: made.append(1) or real_mkdtemp(*a, **k))
    brief = CLEAN + (b"note " + API_KEY.encode() + b"\n" if case == "key_in_brief" else b"")
    _harness_down()
    code, st, out, err = run(capfd, tmp_path, e, brief=brief)
    assert code == 2 and st["status"] == "preflight_refused", st
    assert st["reason"].startswith(st["primary_reason"]), st
    assert "; API backup not run: " in st["reason"] and why in st["reason"], st["reason"]
    assert st["backup"] == "not_run" and st["via"] == "app" and st["primary_exit"] == 2
    assert st["model"] == "gemini-carbon" and st["requested_model"] == "gemini-carbon"
    assert set(st) == BASE_KEYS | TRIGGER_KEYS and st["job_id"] is None and st["report"] is None
    assert WORLD.api.calls == [] and made == [] and not os.path.exists(env["GEMINIPRO_LOG"])
    assert not list(tmp_path.rglob("body.json"))
    assert API_KEY not in out + err


A5_CASES = {
    "guard_exit9": (9, b"", b"gemini-api guard: refused (stdin)"),
    "auth_exit3": api_err(3, "unauthenticated", "auth_error", "API key not valid"),
    "runtime_exit1": api_err(1, "invalid_argument", "invalid_request", "bad request"),
    "timeout": subprocess.TimeoutExpired(["gemini-api"], 5),
    "not_json": (0, b"hello, not json", b""),
    "not_completed": api_ok("partial", status="in_progress"),
    "empty_answer": api_ok(""),
    "error_card": api_ok("Something went wrong. Please try again."),
    "long_error": api_err(1, "invalid_argument", "invalid_request", "x" * 2000),
}


@pytest.mark.parametrize("case", sorted(A5_CASES))
def test_api_a5_backup_failed_keeps_original_exit_and_never_latches(world, env, capfd, tmp_path,
                                                                    case):
    e = api_env(env, tmp_path)
    _harness_down()
    WORLD.api.script = [A5_CASES[case]]
    code, st, out, err = run(capfd, tmp_path, e)
    assert code == 2 and st["status"] == "preflight_refused", st
    prefix = st["primary_reason"] + "; API backup failed: "
    assert st["reason"].startswith(prefix), st["reason"]
    assert len(st["reason"]) - len(prefix) <= 300
    assert st["backup"] == "failed" and st["via"] == "api" and st["primary_exit"] == 2
    assert len(WORLD.api.calls) == 1 and _api_dirs(env) == []
    recs = log_entries(env)
    assert [r["status"] for r in recs] == ["started", "failed"], recs
    assert recs[1]["stop_latch"] is False and recs[1]["via"] == "api" and recs[1]["primary_exit"] == 2
    ok, reason = lanew_log.check("t1", log_path=env["GEMINIPRO_LOG"], ceiling=12)
    assert ok, reason
    _harness_up()  # a second launch in the same run slug is admitted (app path this time)
    code, st, _, _ = run(capfd, tmp_path, e, args=("t1", "again"))
    assert code == 0 and st["via"] == "app" and len(WORLD.api.calls) == 1, st


def test_api_a5_exit8_failure_keeps_exit8(world, env, capfd, tmp_path):
    WORLD.accounts = {PSID: WRONG, OTHER_PSID: THIRD}
    WORLD.api.script = [api_err(3, "unauthenticated", "auth_error")]
    code, st, _, _ = run(capfd, tmp_path, api_env(env, tmp_path))
    assert code == 8 and st["status"] == "account_mismatch" and st["backup"] == "failed", st
    assert st["account_ok"] is False and log_entries(env)[-1]["stop_latch"] is False


@pytest.mark.parametrize("first", [SERVER_ERR, api_err(1, "overloaded", "server_error"),
                                   api_err(1, "service_unavailable", "other")])
def test_api_a6_server_error_retried_once(world, env, capfd, tmp_path, first):
    _harness_down()
    WORLD.api.script = [first, api_ok("SECOND-TRY-391")]
    code, st, _, _ = run(capfd, tmp_path, api_env(env, tmp_path))
    assert code == 0 and st["backup"] == "ok" and len(WORLD.api.calls) == 2, st
    assert "SECOND-TRY-391" in open(st["report"], encoding="utf-8").read()


def test_api_a6_non_server_error_not_retried_and_two_server_errors_fail(world, env, capfd, tmp_path):
    e = api_env(env, tmp_path)
    _harness_down()
    WORLD.api.script = [api_err(1, "invalid_argument", "invalid_request"), api_ok()]
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 2 and st["backup"] == "failed" and len(WORLD.api.calls) == 1, st
    WORLD.api.calls.clear()
    WORLD.api.script = [SERVER_ERR, SERVER_ERR, api_ok()]
    code, st, _, _ = run(capfd, tmp_path, e, args=("t1", "again"))
    assert code == 2 and st["backup"] == "failed" and len(WORLD.api.calls) == 2, st
    assert "high demand" in st["reason"]


def test_api_a7_backup_job_counts_toward_ceiling_daily_cap_ignored(world, env, capfd, tmp_path):
    _harness_down()
    e = api_env(env, tmp_path, GEMINIPRO_RUN_JOB_CEILING="1")
    assert run(capfd, tmp_path, e)[1]["via"] == "api"
    code, st, _, _ = run(capfd, tmp_path, e, args=("t1", "again"))
    assert code == 1 and st["status"] == "run_refused" and len(WORLD.api.calls) == 1, st
    # the retired GEMINIPRO_DAILY_CAP refuses nothing (one backup job already logged today)
    e = api_env(env, tmp_path, GEMINIPRO_DAILY_CAP="1")
    code, st, _, _ = run(capfd, tmp_path, e, args=("other", "x"))
    assert code == 0 and st["via"] == "api" and len(WORLD.api.calls) == 2, st


def test_api_a8_key_never_in_any_output(world, env, capfd, tmp_path):
    e = api_env(env, tmp_path)
    _harness_down()
    leaky_err = (b"debug key=" + API_KEY.encode() + b"\n" + json.dumps(
        {"error": {"code": "invalid_argument", "message": "bad key " + API_KEY},
         "error_type": "invalid_request", "exit_code": 1}).encode())
    WORLD.api.script = [(1, b"", leaky_err), api_ok("the key is %s, ok" % API_KEY)]
    seen = []
    for args, mode in ((("t1", "fail"), True), (("t1", "ok"), False)):
        code, st, out, err = run(capfd, tmp_path, e, args=args, json_mode=mode)
        seen.append(out + err)
        assert API_KEY not in json.dumps(st)
        if st.get("report") and os.path.exists(st["report"]):
            assert API_KEY not in open(st["report"], encoding="utf-8").read()
    assert code == 0 and "[redacted]" in seen[1], seen[1]
    assert not any(API_KEY in s for s in seen)
    assert API_KEY not in open(env["GEMINIPRO_LOG"], encoding="utf-8").read()
    assert all(API_KEY.encode() not in c["body_raw"] and API_KEY not in " ".join(c["argv"])
               for c in WORLD.api.calls)
    # registered before argument parsing: a usage error echoing the key as its argument
    code = gp.main(["--" + API_KEY, "--json"], e)
    out, err = capfd.readouterr()
    assert code == 64 and API_KEY not in out + err and "[redacted]" in out
    # an app-path answer carrying the key, and a --status run
    _harness_up()
    WORLD.answer = "app says " + API_KEY
    code, st, out, err = run(capfd, tmp_path, e, args=("t1", "app"), json_mode=False)
    assert code == 0 and st["via"] == "app" and API_KEY not in out + err
    assert API_KEY not in open(st["report"], encoding="utf-8").read()
    code = gp.main(["--status", "--json"], e)
    out, err = capfd.readouterr()
    assert code == 0 and API_KEY not in out + err


def test_api_a8_short_key_is_not_registered_and_never_used(world, env, capfd, tmp_path):
    short = "Q7w2E9r4T1"  # 10 characters: not a key
    e = dict(api_env(env, tmp_path), GEMINI_API_KEY=short)
    WORLD.answer = "short " + short
    code, st, out, err = run(capfd, tmp_path, e, json_mode=False)
    assert code == 0 and short in out and short not in gp._SECRETS  # not scrubbed
    _harness_down()
    code, st, _, _ = run(capfd, tmp_path, e, args=("t1", "down"))
    assert code == 2 and st["backup"] == "not_run" and "too short" in st["reason"]
    assert WORLD.api.calls == []


TRICKY = ('---\nbrief-check: clean - generic quoting test\nShe said "hi" and \'bye\'; '
          'a\\b\\\\c \\n is literal\r\nnon-ASCII: café – 東京 ✓\n\t"end"\n')


@pytest.mark.parametrize("outcome", ["ok", "failed"])
def test_api_a9_call_shape_body_and_cleanup(world, env, capfd, tmp_path, outcome):
    e = api_env(env, tmp_path)
    _harness_down()
    WORLD.api.script = [api_ok() if outcome == "ok" else api_err(1, "bad", "invalid_request")]
    code, st, _, _ = run(capfd, tmp_path, e, brief=TRICKY.encode("utf-8"))
    assert code == (0 if outcome == "ok" else 2), st
    (c,) = WORLD.api.calls
    assert c["argv"] == [e["GEMINIPRO_API_CLI"], "generate", "--output-format", "json",
                         "--body", "@body.json"]
    assert c["listing"] == ["body.json"] and c["stdin"] is subprocess.DEVNULL
    body = json.loads(c["body_raw"].decode("utf-8"))
    assert body == {"input": TRICKY, "model": "gemini-4-hydrogen", "stream": False, "store": False}
    assert API_KEY.encode() not in c["body_raw"]
    assert c["env"].get("GEMINI_API_KEY") == API_KEY  # the child inherits the env; the CLI reads it
    sd = os.path.normcase(os.path.join(env["CLIPROXY_DIR"], "geminipro.d"))
    assert os.path.normcase(os.path.dirname(os.path.abspath(c["cwd"]))) == sd
    assert not os.path.exists(c["cwd"]) and _api_dirs(env) == []


def test_api_a10_status_mode_never_triggers(world, env, capfd, tmp_path):
    _harness_down()
    code = gp.main(["--status", "--json"], api_env(env, tmp_path))
    st = json.loads(capfd.readouterr()[0])
    assert code == 2 and st["status"] == "preflight_refused" and st["via"] == "app", st
    assert WORLD.api.calls == [] and not (set(st) & TRIGGER_KEYS)


def test_api_a11_model_and_timeout_env(world, env, capfd, tmp_path):
    e = api_env(env, tmp_path, GEMINIPRO_API_MODEL="gemini-test-model", GEMINIPRO_API_TIMEOUT="7")
    _harness_down()
    code, st, _, _ = run(capfd, tmp_path, e, args=("t1", "carbon", "--model", "gemini-fast"))
    assert code == 0 and st["model"] == "gemini-test-model" and st["requested_model"] == "gemini-fast"
    (c,) = WORLD.api.calls
    assert json.loads(c["body_raw"])["model"] == "gemini-test-model" and c["timeout"] == 7
    assert log_entries(env)[0]["model"] == "gemini-test-model"
    code, st, _, _ = run(capfd, tmp_path, dict(e, GEMINIPRO_API_TIMEOUT="soon"), args=("t1", "x"))
    assert code == 64 and "GEMINIPRO_API_TIMEOUT" in st["reason"] and len(WORLD.api.calls) == 1


def test_api_timeout_bounded_by_total_deadline(world, env, capfd, tmp_path):
    _harness_down()
    code, st, _, _ = run(capfd, tmp_path, api_env(env, tmp_path))  # default 300 s, deadline 120 s
    assert code == 0 and 60 <= WORLD.api.calls[0]["timeout"] < 120


def test_api_exit2_after_admission_never_triggers(world, env, capfd, tmp_path, monkeypatch):
    """Negative: an exit 2 raised once the app job was admitted (job_id set) is not the trigger."""
    original = gp.Wrapper.admit

    def admit_then_fail(self):
        original(self)
        raise gp.Exit(2, "preflight_refused", "forced after admission")

    monkeypatch.setattr(gp.Wrapper, "admit", admit_then_fail)
    code, st, _, _ = run(capfd, tmp_path, api_env(env, tmp_path))
    assert code == 2 and st["via"] == "app" and set(st) == BASE_KEYS, st
    assert WORLD.api.calls == [] and log_entries(env)[-1]["status"] == "failed"


def test_api_admission_refused_is_not_run(world, env, capfd, tmp_path, monkeypatch):
    def refuse(self):
        self.report = "would-be-report.md"
        raise gp.Exit(1, "run_refused", "daily cap reached: 80 job(s) admitted today (cap 80)")

    monkeypatch.setattr(gp.Wrapper, "admit", refuse)
    _harness_down()
    code, st, _, _ = run(capfd, tmp_path, api_env(env, tmp_path))
    assert code == 2 and st["backup"] == "not_run" and "admission refused" in st["reason"], st
    assert st["via"] == "app" and st["report"] is None and st["model"] == "gemini-carbon"
    assert WORLD.api.calls == [] and not os.path.exists(env["GEMINIPRO_LOG"])



# --------------------------------------------------------------------------
# fix round 1 (2026-11-15): F1 key in metadata, F2 no latch on any API ending, F3 the
# backstop's kill order, F4 an answer held before interruptible cleanup
# --------------------------------------------------------------------------

def _key_leaks(*roots):
    """Every place under roots where the API key shows up (a file name or file content),
    plus any recorded CLI argv or body file that carries it."""
    hits = []
    for root in roots:
        for p in (pathlib.Path(root).rglob("*") if os.path.isdir(root) else []):
            if API_KEY in p.name:
                hits.append(str(p))
            elif p.is_file() and API_KEY.encode() in p.read_bytes():
                hits.append(str(p))
    for c in WORLD.api.calls:
        if API_KEY in " ".join(c["argv"]) or (c["body_raw"] and API_KEY.encode() in c["body_raw"]):
            hits.append("api call")
    return hits


@pytest.mark.parametrize("where", ["run", "name", "inside_name"])
def test_f1_key_in_run_or_name_is_usage_error_before_the_brief(world, env, capfd, tmp_path,
                                                               monkeypatch, where):
    reads = []
    real_read = gp.Wrapper.read_brief
    monkeypatch.setattr(gp.Wrapper, "read_brief", lambda self: reads.append(1) or real_read(self))
    _harness_down()  # the backup would otherwise fire
    args = {"run": (API_KEY, "x"), "name": ("t1", API_KEY), "inside_name": ("t1", "n-" + API_KEY)}
    code, st, out, err = run(capfd, tmp_path, api_env(env, tmp_path), args=args[where])
    assert code == 64 and st["status"] == "usage_error" and "API key" in st["reason"], st
    assert reads == [] and WORLD.api.calls == [] and WORLD.harness_calls == 0
    assert not os.path.exists(env["GEMINIPRO_LOG"]) and st["job_id"] is None
    assert API_KEY not in out + err and _key_leaks(env["CLIPROXY_DIR"]) == []


def test_f1_key_as_status_mode_argument_is_usage_error(world, env, capfd, tmp_path):
    code = gp.main(["--status", API_KEY, "--json"], api_env(env, tmp_path))
    out, err = capfd.readouterr()
    assert code == 64 and "API key" in json.loads(out)["reason"] and API_KEY not in out + err
    assert WORLD.harness_calls == 0


def test_f1_negative_run_without_the_key_is_admitted(world, env, capfd, tmp_path):
    """Negative: a run/name that only resembles the key (one character short) is a normal job."""
    code, st, _, _ = run(capfd, tmp_path, api_env(env, tmp_path), args=(API_KEY[:-1], "x"))
    assert code == 0 and st["via"] == "app", st


@pytest.mark.parametrize("where", ["api_model", "cli_path"])
def test_f1_key_in_api_model_or_cli_path_backup_not_run(world, env, capfd, tmp_path, where):
    e = api_env(env, tmp_path)
    if where == "api_model":
        e["GEMINIPRO_API_MODEL"] = "gemini-" + API_KEY
        why = "GEMINIPRO_API_MODEL contains the API key"
    else:
        d = tmp_path / ("bin-" + API_KEY)
        d.mkdir()
        cli = d / "gemini-api.exe"
        cli.write_bytes(b"")
        e["GEMINIPRO_API_CLI"] = str(cli)
        why = "the CLI path contains the API key"
    _harness_down()
    code, st, out, err = run(capfd, tmp_path, e)
    assert code == 2 and st["backup"] == "not_run" and st["via"] == "app", st
    assert st["reason"].endswith("; API backup not run: " + why), st["reason"]
    assert WORLD.api.calls == [] and not os.path.exists(env["GEMINIPRO_LOG"])
    assert API_KEY not in out + err and _key_leaks(env["CLIPROXY_DIR"]) == []


def test_f1_key_in_cli_path_found_on_path_backup_not_run(world, env, capfd, tmp_path, monkeypatch):
    e = api_env(env, tmp_path)
    e.pop("GEMINIPRO_API_CLI")
    monkeypatch.setattr(gp.shutil, "which", lambda name, *a, **k: (
        "C:/fake/browser-harness.exe" if "browser-harness" in str(name)
        else "C:/k-%s/gemini-api.exe" % API_KEY))
    _harness_down()
    code, st, out, err = run(capfd, tmp_path, e)
    assert code == 2 and st["backup"] == "not_run", st
    assert "the CLI path contains the API key" in st["reason"]
    assert WORLD.api.calls == [] and API_KEY not in out + err


def test_f1_key_as_requested_model_never_leaves_scrubbed_sinks(world, env, capfd, tmp_path):
    _harness_down()
    code, st, out, err = run(capfd, tmp_path, api_env(env, tmp_path),
                             args=("t1", "x", "--model", API_KEY), json_mode=False)
    assert code == 0 and st["via"] == "api" and st["model"] == "gemini-4-hydrogen", st
    assert st["requested_model"] == "[redacted]" and API_KEY not in out + err
    assert _key_leaks(env["CLIPROXY_DIR"]) == []


def test_f1_key_in_cliproxy_dir_is_usage_error(world, env, capfd, tmp_path):
    cp = tmp_path / ("cp-" + API_KEY)
    e = dict(api_env(env, tmp_path), CLIPROXY_DIR=str(cp))
    _harness_down()
    code, st, out, err = run(capfd, tmp_path, e)
    assert code == 64 and "CLIPROXY_DIR contains the API key" in st["reason"], st
    assert not cp.exists() and WORLD.api.calls == [] and API_KEY not in out + err


@pytest.mark.parametrize("exc", [KeyboardInterrupt, asyncio.CancelledError])
def test_f2_interrupt_from_the_cli_never_latches(world, env, capfd, tmp_path, exc):
    e = api_env(env, tmp_path)
    _harness_down()
    WORLD.api.script = [exc()]
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 130 and st["status"] == "interrupted" and st["via"] == "api", st
    recs = log_entries(env)
    assert len(recs) == 2 and recs[0]["status"] == "started", recs
    assert recs[1]["stop_latch"] is False and recs[1]["via"] == "api"
    ok, reason = lanew_log.check("t1", log_path=env["GEMINIPRO_LOG"], ceiling=12)
    assert ok, reason
    assert _api_dirs(env) == []


def test_f2_any_terminal_record_on_the_api_path_is_unlatched(world, env, tmp_path):
    """The choke point: once via is api, even a default-latch caller writes stop_latch false."""
    w = gp.Wrapper(["t1", "x"], env)
    w.parse_args()
    w.config()
    os.makedirs(w.out_dir, exist_ok=True)
    w.admit()
    w.via, w.primary = "api", gp.Exit(2, "preflight_refused", "down")
    assert w.record_terminal("outcome_unknown", 6)
    assert log_entries(env)[-1]["stop_latch"] is False


@pytest.mark.parametrize("primary", [2, 8])
def test_f2_backstop_on_an_admitted_api_job_keeps_the_original_exit(world, env, capfd, tmp_path,
                                                                    monkeypatch, primary):
    seen = []
    real_backup = gp.Wrapper.api_backup
    monkeypatch.setattr(gp.Wrapper, "api_backup",
                        lambda self, p, exc: seen.append(self) or real_backup(self, p, exc))
    fake = WORLD.api

    def overrun(*a, **k):
        fake(*a, **k)
        seen[0].backstop()  # HARD_EXIT is a no-op here: main goes on afterwards
        raise subprocess.TimeoutExpired(["gemini-api"], 5)

    monkeypatch.setattr(gp, "_run_api", overrun)
    if primary == 2:
        _harness_down()
    else:
        WORLD.accounts = {PSID: WRONG, OTHER_PSID: THIRD}
    bf = tmp_path / "b.md"
    bf.write_bytes(CLEAN)
    gp.main(["t1", "carbon", "--brief-file", str(bf), "--json"], api_env(env, tmp_path))
    out, _ = capfd.readouterr()
    lines = [l for l in out.splitlines() if l.startswith("{")]
    assert WORLD.hard_exits == [primary] and len(lines) == 1, (WORLD.hard_exits, lines)
    hard = json.loads(lines[0])
    status = "preflight_refused" if primary == 2 else "account_mismatch"
    assert hard["exit"] == primary and hard["status"] == status and hard["via"] == "api", hard
    assert hard["reason"].startswith(hard["primary_reason"] + "; API backup failed: hard backstop")
    recs = log_entries(env)
    assert [r["status"] for r in recs] == ["started", "failed"] and recs[1]["stop_latch"] is False
    assert lanew_log.check("t1", log_path=env["GEMINIPRO_LOG"], ceiling=12)[0]


class _Proc:
    def __init__(self, events):
        self.events, self.pid = events, 4242

    def kill(self):
        self.events.append("direct-kill")


def _backstop_world(env, tmp_path, monkeypatch, tree_sleep=None, release=None):
    import time as _t
    events = []

    def slow_tree(proc, created=None):  # fix round 2: the tree step also takes the creation time
        events.append("tree-start")
        if release is not None:
            release.wait(10)  # blocks until the test releases it (past the backstop's bound)
        else:
            _t.sleep(tree_sleep)
        events.append("tree-done")

    monkeypatch.setattr(gp, "_kill_descendants", slow_tree, raising=False)
    w = gp.Wrapper(["t1", "x", "--json"], env)
    d = tmp_path / "api-dir"
    d.mkdir()
    (d / "body.json").write_text("{}")
    w.api_holder["proc"] = _Proc(events)
    w.api_dir = str(d)
    monkeypatch.setattr(gp, "HARD_EXIT", lambda code: events.append(("hard-exit", d.exists())))
    return w, events, d


def test_api_backstop_kills_the_child_and_removes_the_body_dir(world, env, tmp_path, monkeypatch,
                                                               capfd):
    """Rewritten in fix round 1 (F3): the old instant list.append double proved the call, not
    the termination order; this one uses a slow tree-kill double and checks the order."""
    w, events, d = _backstop_world(env, tmp_path, monkeypatch, tree_sleep=0.6)
    w.backstop()
    assert events == ["direct-kill", "tree-start", "tree-done", ("hard-exit", False)], events
    assert not d.exists()
    assert gp.KILL_WAIT <= 15  # fix round 2 follow-on: KILL_TREE_TIMEOUT (taskkill's) is gone


def test_f3_backstop_tree_kill_wait_is_bounded(world, env, tmp_path, monkeypatch, capfd):
    import threading
    import time as _t
    monkeypatch.setattr(gp, "KILL_WAIT", 0.3, raising=False)
    release = threading.Event()
    w, events, d = _backstop_world(env, tmp_path, monkeypatch, release=release)
    t = _t.monotonic()
    try:
        w.backstop()
    finally:
        took = _t.monotonic() - t
        release.set()  # let the blocked double finish before the fixture tears down
    assert events[:3] == ["direct-kill", "tree-start", ("hard-exit", False)], events
    assert took >= 0.25, took  # waited for the bound (Windows timers run ~15 ms coarse)


@pytest.mark.skipif(os.name != "nt", reason="Windows tree kill")
def test_f3_tree_kill_targets_the_children_of_the_dead_root(world, monkeypatch):
    """Rewritten in fix round 2 (N1): the dead root's tree is walked from the process snapshot
    and each VERIFIED descendant is killed through its own handle - no taskkill by pid."""
    runs = []
    monkeypatch.setattr(gp, "_snapshot", lambda: [(11, 4242, 2000), (12, 4242, 2001),
                                                  (13, 11, 2002), (14, 99, 2003)], raising=False)
    monkeypatch.setattr(gp.subprocess, "run", lambda argv, **k: runs.append(argv))
    gp._kill_descendants(_Proc([]), 1500)
    assert WORLD.kills == [(11, 2000), (12, 2001), (13, 2002)] and runs == []
    WORLD.kills.clear()
    monkeypatch.setattr(gp, "_snapshot", lambda: [])
    gp._kill_descendants(_Proc([]), 1500)
    assert WORLD.kills == [] and runs == []


@pytest.mark.skipif(os.name != "nt", reason="Windows process snapshot")
def test_f3_child_pids_reads_the_process_snapshot():
    """Rewritten in fix round 2 (N1): the real snapshot carries each process's recorded parent
    AND its creation time (the old _child_pids returned parent-matched pids only)."""
    me = [r for r in REAL["_snapshot"]() if r[0] == os.getpid()]
    assert me == [(os.getpid(), os.getppid(), lanew_log.pid_created(os.getpid()))], me


@pytest.mark.parametrize("dir_state", ["recovers", "stuck"])
def test_f4_interrupt_during_cleanup_keeps_the_answer(world, env, capfd, tmp_path, monkeypatch,
                                                      dir_state):
    real_rmtree, real_sleep = gp.shutil.rmtree, gp.time.sleep
    state = {"fails": 0, "armed": False}

    def rmtree(path, *a, **k):
        if os.path.basename(str(path)).startswith("api-") and (
                dir_state == "stuck" or state["fails"] == 0):
            state["fails"] += 1
            state["armed"] = state["fails"] == 1
            return None  # the removal did not happen
        return real_rmtree(path, *a, **k)

    def sleep(s):
        if state["armed"]:
            state["armed"] = False
            raise KeyboardInterrupt
        return real_sleep(s)

    monkeypatch.setattr(gp.shutil, "rmtree", rmtree)
    monkeypatch.setattr(gp.time, "sleep", sleep)
    _harness_down()
    WORLD.api.script = [api_ok("KEPT-ANSWER-391")]
    code, st, out, err = run(capfd, tmp_path, api_env(env, tmp_path), json_mode=False)
    assert code == 0 and st["status"] == "ok" and st["backup"] == "ok", st
    assert out.strip() == "KEPT-ANSWER-391"
    assert "KEPT-ANSWER-391" in open(st["report"], encoding="utf-8").read()
    recs = log_entries(env)
    assert [r["status"] for r in recs] == ["started", "ok"] and recs[1]["stop_latch"] is False
    if dir_state == "recovers":
        assert _api_dirs(env) == [] and "could not be removed" not in st["reason"]
    else:
        assert len(_api_dirs(env)) == 1
        assert "the API body directory could not be removed" in st["reason"]


@pytest.mark.parametrize("mode", ["job", "status"])
def test_f1_key_in_the_browser_harness_path_never_reaches_its_argv(world, env, capfd, tmp_path,
                                                                   monkeypatch, mode):
    monkeypatch.setattr(gp.shutil, "which", lambda name, *a, **k: (
        "C:/h-%s/browser-harness.exe" % API_KEY if "browser-harness" in str(name) else None))
    e = api_env(env, tmp_path)
    if mode == "job":
        code, st, out, err = run(capfd, tmp_path, e)
        assert code == 0 and st["via"] == "api" and st["primary_exit"] == 2, st  # the trigger
    else:
        code = gp.main(["--status", "--json"], e)
        out, err = capfd.readouterr()
        st = json.loads(out)
        assert code == 2 and st["status"] == "preflight_refused", st
    assert "browser-harness path contains the API key" in (st.get("primary_reason") or st["reason"])
    assert WORLD.harness_calls == 0 and API_KEY not in out + err


def test_r2_app_path_failure_with_the_key_set_still_latches(world, env, capfd, tmp_path):
    """Negative for the no-latch choke point: it covers the API path only."""
    WORLD.gen_mode = "http500"
    code, st, _, _ = run(capfd, tmp_path, api_env(env, tmp_path))
    assert code == 6 and st["via"] == "app" and log_entries(env)[-1]["stop_latch"] is True, st


# --------------------------------------------------------------------------
# fix round 2 (2026-11-15): F2 no window between admission and via "api", F6 the key at every
# persistence boundary, F7 cancellation-safe child termination, F8 cleanup never changes the
# result, N1 descendants verified by creation time
# --------------------------------------------------------------------------

def _interrupted_api_launch(e, st, code):
    """Rewritten in fix round 3 (the re-specced F2 rule): an API-path launch interrupted in the
    admission window exits 130. Once admit() handed the wrapper a job id (status line job_id
    set): exactly one terminal record, unlatched, via api, and the run is not latched. Before
    that the wrapper fails closed like the app path: it writes no terminal record, the status
    line is back at via app, and a started record lanew_log may already have appended stays
    alone (the documented limit). Returns "job", "none" (nothing on disk) or "orphan"."""
    recs = log_entries(e)
    assert code == 130 and st["status"] == "interrupted", st
    started = [r for r in recs if r["status"] == "started"]
    terminal = [r for r in recs if r["status"] != "started"]
    assert len(started) <= 1, recs
    if st["job_id"]:
        assert started and started[0]["job_id"] == st["job_id"], (recs, st)
        assert len(terminal) == 1 and terminal[0]["job_id"] == st["job_id"], recs
        assert terminal[0]["stop_latch"] is False and terminal[0]["via"] == "api", recs
        assert terminal[0]["primary_exit"] == 2, recs
        assert st["via"] == "api" and st["backup"] == "failed", st
        assert st["model"] == "gemini-4-hydrogen", st
        ok, reason = lanew_log.check("t1", log_path=e["GEMINIPRO_LOG"], ceiling=12)
        assert ok, reason
        kind = "job"
    else:
        assert terminal == [], recs  # the wrapper never writes a record for a job it was not handed
        assert st["via"] == "app" and st["report"] is None and st["model"] == "gemini-carbon", st
        assert st.get("backup") in (None, "not_run"), st
        kind = "orphan" if started else "none"
    assert _api_dirs(e) == []
    return kind


def _f2_after_reservation_append(monkeypatch):
    real = gp.lanew_log.admit

    def admit(*a, **k):
        real(*a, **k)  # the started record is on disk; admit() has not set job_id yet
        raise KeyboardInterrupt

    monkeypatch.setattr(gp.lanew_log, "admit", admit)


def _f2_at_log(prefix):
    def inject(monkeypatch):
        real = gp.log

        def log(msg):
            if msg.startswith(prefix):
                raise KeyboardInterrupt
            return real(msg)

        monkeypatch.setattr(gp, "log", log)
    return inject


def _f2_after_admit_returns(monkeypatch):
    real = gp.Wrapper.admit

    def admit(self):
        real(self)
        raise KeyboardInterrupt

    monkeypatch.setattr(gp.Wrapper, "admit", admit)


def _in_admit_step(monkeypatch, exc):
    """Raise exc from Wrapper.admit's own lanew_log.pid_created call: a step inside admission
    before the started record is appended (lanew_log's internal calls pass through)."""
    real = gp.lanew_log.pid_created

    def pid_created(pid):
        if sys._getframe(1).f_code is gp.Wrapper.admit.__code__:
            raise exc
        return real(pid)

    monkeypatch.setattr(gp.lanew_log, "pid_created", pid_created)


def _f2_before_the_reservation(monkeypatch):
    _in_admit_step(monkeypatch, KeyboardInterrupt())


# fix round 3: the expectation per point follows the re-specced rule - "job" once the wrapper
# holds the job id; before that it fails closed ("orphan": lanew_log's started record alone)
F2_POINTS = {
    "inside_admit_after_the_record_is_appended": (_f2_after_reservation_append, "orphan"),
    "inside_admit_at_the_admitted_log_line": (_f2_at_log("admitted job_id="), "job"),
    "right_after_admit_returns": (_f2_after_admit_returns, "job"),
    "right_before_the_first_cli_call": (_f2_at_log("API backup: the app path ended"), "job"),
    "inside_admit_before_the_record": (_f2_before_the_reservation, "none"),
}


@pytest.mark.parametrize("point", sorted(F2_POINTS))
def test_f2_interrupt_between_admission_and_the_cli_never_latches(world, env, capfd, tmp_path,
                                                                  monkeypatch, point):
    inject, kind = F2_POINTS[point]
    e = api_env(env, tmp_path)
    _harness_down()
    inject(monkeypatch)
    code, st, _, _ = run(capfd, tmp_path, e)
    assert _interrupted_api_launch(e, st, code) == kind
    assert WORLD.api.calls == []


def test_f2_interrupt_at_every_line_from_admission_to_the_cli_never_latches(world, env, capfd,
                                                                            tmp_path, monkeypatch):
    """The sweep: a KeyboardInterrupt raised at the Nth executed line of geminipro.py and
    lanew_log.py code, from the entry of api_backup up to the CLI start, for every N."""
    ours = {os.path.normcase(os.path.abspath(f)) for f in (gp.__file__, lanew_log.__file__)}
    st8 = {"n": 0, "seen": 0, "fired": False, "done": False}

    def local(frame, event, arg):
        if event == "line" and not st8["done"]:
            st8["seen"] += 1
            if st8["seen"] == st8["n"]:
                st8["fired"] = True
                raise KeyboardInterrupt
        return local

    def tracer(frame, event, arg):
        if st8["done"] or os.path.normcase(os.path.abspath(frame.f_code.co_filename)) not in ours:
            return None
        return local

    real_backup, fake = gp.Wrapper.api_backup, WORLD.api

    def traced(self, prompt, primary):
        sys.settrace(tracer)
        try:
            return real_backup(self, prompt, primary)
        finally:
            sys.settrace(None)

    def cli(*a, **k):
        st8["done"] = True  # the CLI start ends the window
        return fake(*a, **k)

    monkeypatch.setattr(gp.Wrapper, "api_backup", traced)
    monkeypatch.setattr(gp, "_run_api", cli)
    _harness_down()
    kinds = {"job": 0, "none": 0, "orphan": 0}
    for n in range(1, 3000):
        st8.update(n=n, seen=0, fired=False, done=False)
        e = api_env(env, tmp_path, GEMINIPRO_LOG=str(tmp_path / ("usage-%d.jsonl" % n)))
        code, st, _, _ = run(capfd, tmp_path, e)
        if not st8["fired"]:  # past the last line of the window: an ordinary API answer
            assert code == 0 and st["via"] == "api", st
            break
        kinds[_interrupted_api_launch(e, st, code)] += 1
    else:
        pytest.fail("the window never closed")
    print("F2 sweep: %(job)d boundaries with the job id held, %(none)d before any record, "
          "%(orphan)d with lanew_log's record but no job id yet" % kinds)
    # rewritten in fix round 3: the orphan boundaries are the accepted fail-closed limit
    assert kinds["job"] >= 10 and kinds["none"] >= 10 and kinds["orphan"] >= 1, kinds


# ---- fix round 3 (2026-11-16): F2 re-specced, R3-1, R3-2 ------------------------------------

def test_r3_reservation_appended_but_unverified_is_not_run_and_fails_closed(world, env, capfd,
                                                                            tmp_path, monkeypatch):
    """lanew_log appends the started record, then its verification read raises: admission
    failed, the original exit, not run - and the wrapper writes nothing more (no terminal, no
    second record of any kind). The documented limit: the run is refused once we are gone."""
    import builtins
    e = api_env(env, tmp_path)
    _harness_down()
    real_open, failed = builtins.open, []

    def flaky_open(path, mode="r", *a, **k):
        if str(path) == e["GEMINIPRO_LOG"] and mode == "r" and os.path.exists(path) and not failed:
            failed.append(path)  # the first read of an existing log: the verification read
            raise OSError("synthetic verification read error")
        return real_open(path, mode, *a, **k)

    monkeypatch.setattr(builtins, "open", flaky_open)
    code, st, _, _ = run(capfd, tmp_path, e)
    monkeypatch.setattr(builtins, "open", real_open)
    assert failed and code == 2 and st["status"] == "preflight_refused", st
    assert "; API backup not run: admission failed (" in st["reason"], st["reason"]
    assert st["via"] == "app" and st["backup"] == "not_run" and st["job_id"] is None, st
    assert st["report"] is None and WORLD.api.calls == [] and _api_dirs(e) == []
    recs = log_entries(e)
    assert [r["status"] for r in recs] == ["started"], recs
    monkeypatch.setattr(gp.lanew_log, "pid_alive", lambda pid: False)  # this process has ended
    ok, reason = lanew_log.check("t1", log_path=e["GEMINIPRO_LOG"], ceiling=12)
    assert not ok and "usage unknown" in reason, reason


def test_r3_second_launch_interrupted_before_its_reservation_writes_nothing(world, env, capfd,
                                                                            tmp_path, monkeypatch):
    """R3-1: two launches in one process, same run/name, the clock frozen (same report path);
    the first fails normally, the second is interrupted before its reservation - it must not
    take the first job as its own: the first has exactly one terminal record, the second
    wrote nothing."""
    e = api_env(env, tmp_path)
    _harness_down()
    real_dt = gp._dt.datetime
    stamp = real_dt.now()

    class Frozen(real_dt):
        @classmethod
        def now(cls, tz=None):
            return stamp if tz is None else stamp.astimezone(tz)

    monkeypatch.setattr(gp._dt, "datetime", Frozen)
    WORLD.api.script = [api_err(3, "unauthenticated", "auth_error")]
    code1, st1, _, _ = run(capfd, tmp_path, e)
    assert code1 == 2 and st1["job_id"] and st1["backup"] == "failed", st1

    def never_reserved(*a, **k):
        raise KeyboardInterrupt

    monkeypatch.setattr(gp.lanew_log, "admit", never_reserved)
    code2, st2, _, _ = run(capfd, tmp_path, e)
    assert code2 == 130 and st2["job_id"] is None and st2["via"] == "app", st2
    recs = log_entries(e)
    assert [(r["job_id"], r["status"]) for r in recs] == [
        (st1["job_id"], "started"), (st1["job_id"], "failed")], recs


def test_r3_an_admission_error_is_not_run_with_the_original_exit(world, env, capfd, tmp_path,
                                                                 monkeypatch):
    """An ordinary error inside admission (here the owner-creation read before the started
    record) is an admission failure: the original exit (8 here) with "not run", no job,
    nothing recorded."""
    _in_admit_step(monkeypatch, PermissionError(13, "synthetic log read error"))
    WORLD.accounts = {PSID: WRONG, OTHER_PSID: THIRD}
    e = api_env(env, tmp_path)
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 8 and st["status"] == "account_mismatch", st
    assert "; API backup not run: admission failed (PermissionError" in st["reason"], st["reason"]
    assert st["via"] == "app" and st["backup"] == "not_run" and st["job_id"] is None, st
    assert WORLD.api.calls == [] and log_entries(e) == []


def test_r3_the_job_id_handoff_follows_the_reservation_at_once(world, env, capfd, tmp_path,
                                                               monkeypatch):
    """The handoff, explicitly: a KeyboardInterrupt at every line event of Wrapper.admit's own
    frame. The only lines where lanew_log's started record is on disk while the wrapper holds
    no job id lie between the lanew_log.admit call and the job_id assignment, at most 3."""
    import inspect
    code_obj = gp.Wrapper.admit.__code__
    st8 = {"n": 0, "seen": 0, "fired": False, "line": None}

    def local(frame, event, arg):
        if event == "line":
            st8["seen"] += 1
            if st8["seen"] == st8["n"]:
                st8["fired"], st8["line"] = True, frame.f_lineno
                raise KeyboardInterrupt
        return local

    def tracer(frame, event, arg):
        return local if frame.f_code is code_obj else None

    real_backup = gp.Wrapper.api_backup

    def traced(self, prompt, primary):
        sys.settrace(tracer)
        try:
            return real_backup(self, prompt, primary)
        finally:
            sys.settrace(None)

    monkeypatch.setattr(gp.Wrapper, "api_backup", traced)
    _harness_down()
    orphan_lines, kinds = [], set()
    for n in range(1, 500):
        st8.update(n=n, seen=0, fired=False, line=None)
        e = api_env(env, tmp_path, GEMINIPRO_LOG=str(tmp_path / ("h-%d.jsonl" % n)))
        code, st, _, _ = run(capfd, tmp_path, e)
        if not st8["fired"]:
            assert code == 0 and st["via"] == "api", st
            break
        kind = _interrupted_api_launch(e, st, code)
        kinds.add(kind)
        if kind == "orphan":
            orphan_lines.append(st8["line"])
    lines, first = inspect.getsourcelines(gp.Wrapper.admit)
    call = first + next(i for i, l in enumerate(lines) if "lanew_log.admit(" in l)
    assign = first + next(i for i, l in enumerate(lines) if "self.job_id, self.ts_start = entry" in l)
    print("handoff: orphan lines %s (call line %d, assignment line %d)" % (orphan_lines, call,
                                                                          assign))
    assert kinds == {"none", "orphan", "job"}, kinds
    assert orphan_lines and all(call <= ln <= assign for ln in orphan_lines), (orphan_lines, call,
                                                                               assign)
    assert len(orphan_lines) <= 3, orphan_lines


def test_r3_interrupt_in_the_no_cache_check_keeps_the_exit(world, env, capfd, tmp_path,
                                                           monkeypatch):
    """R3-2: finish()'s no-cache existence check is housekeeping too (the directory need not
    exist: the check itself is interrupted)."""
    left = tmp_path / "nocache"
    monkeypatch.setitem(gp._HARDENED, "nocache", left)
    real = gp.os.path.exists

    def exists(path):
        if str(path) == str(left):
            raise KeyboardInterrupt
        return real(path)

    monkeypatch.setattr(gp.os.path, "exists", exists)
    _harness_down()
    code, st, _, _ = run(capfd, tmp_path, dict(api_env(env, tmp_path), GEMINIPRO_API_BACKUP="0"))
    assert code == 2 and st["status"] == "preflight_refused", st
    assert st["reason"].endswith("; API backup not run: GEMINIPRO_API_BACKUP=0"), st["reason"]


def test_r3_interrupt_in_finish_diagnostics_keeps_the_exit(world, env, capfd, tmp_path,
                                                           monkeypatch):
    """R3-2 grep pass: finish()'s library-spy log line is housekeeping as well."""
    real_finish, real_log = gp.Wrapper.finish, gp.log

    def finish(self, r):
        gp.STATE.spy["rotate"] = 1  # a neutralized library call to report
        return real_finish(self, r)

    def log(msg):
        if msg.startswith("library cache/rotation calls neutralized"):
            raise KeyboardInterrupt
        return real_log(msg)

    monkeypatch.setattr(gp.Wrapper, "finish", finish)
    monkeypatch.setattr(gp, "log", log)
    _harness_down()
    code, st, _, _ = run(capfd, tmp_path, dict(api_env(env, tmp_path), GEMINIPRO_API_BACKUP="0"))
    assert code == 2 and st["status"] == "preflight_refused", st


def test_r3_backstop_kill_step_failure_still_reaches_the_hard_exit(world, env, tmp_path,
                                                                   monkeypatch, capfd):
    """R3-2 grep pass: the backstop's kill step (a side thread) is contained - a failure to
    start it never skips the status line or the hard exit."""
    w, events, d = _backstop_world(env, tmp_path, monkeypatch, tree_sleep=0)
    real_side, calls = gp._side, []

    def side(fn, timeout):
        calls.append(fn)
        if len(calls) == 1:
            raise RuntimeError("can't start new thread")
        return real_side(fn, timeout)

    monkeypatch.setattr(gp, "_side", side)
    w.backstop()
    assert events[0] == "direct-kill" and events[-1] == ("hard-exit", False), events


# ---- F6 ---------------------------------------------------------------------------------

def test_f6_key_in_the_usage_log_path_is_usage_error(world, env, capfd, tmp_path):
    logs = tmp_path / "logs"
    e = dict(api_env(env, tmp_path), GEMINIPRO_LOG=str(logs / ("usage-" + API_KEY + ".jsonl")))
    _harness_down()
    code, st, out, err = run(capfd, tmp_path, e)
    assert code == 64 and st["status"] == "usage_error", st
    assert "GEMINIPRO_LOG contains the API key" in st["reason"], st
    assert WORLD.api.calls == [] and WORLD.harness_calls == 0 and not logs.exists()
    assert API_KEY not in out + err and _key_leaks(tmp_path) == []
    # negative: --status never reads or writes the usage log, so the variable is no refusal there
    _harness_up()
    code = gp.main(["--status", "--json"], e)
    out, err = capfd.readouterr()
    assert code == 0 and API_KEY not in out + err and not logs.exists()


@pytest.mark.parametrize("mode", ["job", "status"])
def test_f6_a_context_id_carrying_the_key_is_never_remembered(world, env, capfd, tmp_path, mode):
    WORLD.payload["out"] = harness_payload(contexts=[
        {"ctx": API_KEY, "via": "browser_ui/Network.getCookies", "psid": PSID, "psidts": PSIDTS}],
        default=API_KEY)
    e = api_env(env, tmp_path)
    if mode == "job":
        code, st, out, err = run(capfd, tmp_path, e)
        assert st["via"] == "app", st
    else:
        code = gp.main(["--status", "--json"], e)
        out, err = capfd.readouterr()
    assert code == 0 and API_KEY not in out + err
    assert not (pathlib.Path(env["CLIPROXY_DIR"]) / "geminipro.d" / gp.MEMORY_FILE).exists()
    assert _key_leaks(env["CLIPROXY_DIR"]) == []


def test_f6_status_mode_never_creates_a_state_dir_named_with_the_key(world, env, capfd, tmp_path):
    cp = tmp_path / ("cp-" + API_KEY)
    code = gp.main(["--status", "--json"], dict(api_env(env, tmp_path), CLIPROXY_DIR=str(cp)))
    out, err = capfd.readouterr()
    assert code == 0 and API_KEY not in out + err and not cp.exists()


def test_f6_usage_record_fields_carrying_the_key_are_never_written(world, env, tmp_path):
    """The shared check at the usage-record boundary (here: a model name from the app's registry)."""
    w = gp.Wrapper(["t1", "x"], api_env(env, tmp_path))
    w.parse_args()
    w.config()
    os.makedirs(w.out_dir, exist_ok=True)
    w.model = "registry-" + API_KEY
    with pytest.raises(gp.Exit) as ei:
        w.admit()
    assert ei.value.code == 3 and API_KEY not in ei.value.reason and w.job_id is None
    assert not os.path.exists(env["GEMINIPRO_LOG"])


# ---- F7 ---------------------------------------------------------------------------------

class FakePopen:
    """A stand-in CLI child for the REAL gp._run_api - never a real process. communicate()
    follows `steps` ("timeout", an exception to raise, or (rc, stdout, stderr)); kill() takes
    effect only while `mortal`."""

    def __init__(self, steps, mortal=True, spy=None):
        self.pid, self.returncode = 4243, None
        self.steps, self.events, self.mortal, self.spy = list(steps), [], mortal, spy

    def communicate(self, timeout=None):
        self.events.append("communicate")
        if self.spy:
            self.spy(self)
        step = self.steps.pop(0) if self.steps else (None, b"", b"")
        if step == "timeout":
            raise subprocess.TimeoutExpired(["fake-cli"], timeout)
        if isinstance(step, BaseException):
            raise step
        if self.returncode is None and step[0] is not None:
            self.returncode = step[0]
        return step[1], step[2]

    def kill(self):
        self.events.append("direct-kill")
        if self.mortal:
            self.returncode = -9

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        if self.returncode is None:
            raise subprocess.TimeoutExpired(["fake-cli"], timeout)
        return self.returncode


def _fake_child(monkeypatch, proc, tree_error=None, where="snapshot"):
    """The real _run_api with a fake Popen. tree_error: raised inside the timeout path's
    descendant step - by the process snapshot or by the first verified kill (`where`). Any
    subprocess.run (taskkill) call is recorded: the timeout path must make none."""
    runs = []
    monkeypatch.setattr(gp.subprocess, "Popen", lambda *a, **k: proc)
    monkeypatch.setattr(gp.subprocess, "run", lambda argv, **k: runs.append(argv))
    if tree_error is not None and where == "snapshot":
        def snapshot():
            raise tree_error
        monkeypatch.setattr(gp, "_snapshot", snapshot, raising=False)
    elif tree_error is not None:
        monkeypatch.setattr(gp, "_snapshot", lambda: [(4300, proc.pid, 2000)], raising=False)

        def kill_verified(pid, created):
            raise tree_error
        monkeypatch.setattr(gp, "_kill_verified", kill_verified, raising=False)
    return runs


@pytest.mark.skipif(os.name != "nt", reason="Windows tree kill")
@pytest.mark.parametrize("where", ["snapshot", "verified_kill"])
@pytest.mark.parametrize("stop", ["kbint", "cancel"])
def test_f7_interrupted_tree_kill_still_kills_the_direct_child(world, monkeypatch, tmp_path, stop,
                                                               where):
    """Adapted in the round-2 follow-on: the interrupt now lands in the verified descendant
    step (the snapshot, or a verified kill) - the timeout path has no taskkill any more."""
    proc = FakePopen(["timeout"])
    exc = KeyboardInterrupt() if stop == "kbint" else asyncio.CancelledError()
    runs = _fake_child(monkeypatch, proc, tree_error=exc, where=where)
    walks = []
    monkeypatch.setattr(gp, "_kill_descendants", lambda p, c: walks.append((p.pid, c)),
                        raising=False)
    holder = {}
    with pytest.raises(type(exc)):
        REAL["_run_api"](["fake-cli"], str(tmp_path), {}, 1, subprocess.DEVNULL, holder)
    assert runs == []
    assert proc.returncode is not None and "direct-kill" in proc.events, proc.events
    assert walks == [(4243, 1000)]  # the step did not finish: the verified walk took over
    assert holder == {}


def test_f7_the_child_stays_in_the_holder_until_it_is_confirmed_dead(world, monkeypatch, tmp_path):
    proc = FakePopen([KeyboardInterrupt()], mortal=False)
    _fake_child(monkeypatch, proc)
    holder = {}
    with pytest.raises(KeyboardInterrupt):
        REAL["_run_api"](["fake-cli"], str(tmp_path), {}, 1, subprocess.DEVNULL, holder)
    assert "direct-kill" in proc.events
    assert holder.get("proc") is proc and holder.get("created") == 1000  # the backstop still has it


@pytest.mark.parametrize("ending", ["return", "timeout", "kbint", "cancel", "oserror"])
def test_f7_every_path_out_of_run_api_leaves_no_live_child(world, monkeypatch, tmp_path, ending):
    step = {"return": (0, b"{}", b""), "timeout": "timeout", "kbint": KeyboardInterrupt(),
            "cancel": asyncio.CancelledError(), "oserror": OSError("pipe broke")}[ending]
    holder, seen = {}, {}
    proc = FakePopen([step], spy=lambda p: seen.update(holder))
    _fake_child(monkeypatch, proc)
    try:
        r = REAL["_run_api"](["fake-cli"], str(tmp_path), {}, 1, subprocess.DEVNULL, holder)
        assert ending == "return" and r.returncode == 0 and r.stdout == b"{}"
        assert "direct-kill" not in proc.events
    except BaseException as exc:  # noqa: B902 - every ending is raised on purpose here
        assert ending != "return", exc
        assert ending != "timeout" or isinstance(exc, subprocess.TimeoutExpired)
    assert proc.returncode is not None and holder == {}
    # N1: the child's creation time is recorded at start, while it is alive
    assert seen["proc"] is proc and seen["created"] == 1000, seen


@pytest.mark.skipif(os.name != "nt", reason="Windows tree kill")
def test_f7_wrapper_interrupted_in_timeout_cleanup_leaves_no_live_child(world, env, capfd,
                                                                        tmp_path, monkeypatch):
    proc = FakePopen(["timeout"])
    runs = _fake_child(monkeypatch, proc, tree_error=KeyboardInterrupt())  # adapted: no taskkill
    monkeypatch.setattr(gp, "_run_api", REAL["_run_api"])
    e = api_env(env, tmp_path)
    _harness_down()
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 130 and st["via"] == "api", st
    assert proc.returncode is not None and "direct-kill" in proc.events, proc.events
    assert runs == []
    recs = log_entries(e)
    assert recs[-1]["stop_latch"] is False and _api_dirs(e) == []


def test_f7_finish_reaps_a_child_left_in_the_holder(world, env, capfd, tmp_path, monkeypatch):
    proc = FakePopen([KeyboardInterrupt()], mortal=False)  # survives every kill inside _run_api
    _fake_child(monkeypatch, proc)
    monkeypatch.setattr(gp, "_run_api", REAL["_run_api"])
    walks, seen = [], {}
    monkeypatch.setattr(gp, "_kill_descendants", lambda p, c: walks.append((p.pid, c)),
                        raising=False)
    real_finish = gp.Wrapper.finish

    def finish(self, r):
        seen["w"], proc.mortal = self, True
        return real_finish(self, r)

    monkeypatch.setattr(gp.Wrapper, "finish", finish)
    _harness_down()
    code, st, _, _ = run(capfd, tmp_path, api_env(env, tmp_path))
    assert code == 130 and st["via"] == "api", st
    assert proc.returncode is not None and seen["w"].api_holder == {}
    assert (4243, 1000) in walks  # its verified descendants too


# ---- F8 ---------------------------------------------------------------------------------

def _api_rmtree(monkeypatch, what):
    """shutil.rmtree for the API body directories: what(i) for the i-th call - "raise" an
    OSError, "skip" (the directory stays) or None (really removed)."""
    real, calls = gp.shutil.rmtree, []

    def rmtree(path, *a, **k):
        if os.path.basename(str(path)).startswith("api-"):
            calls.append(path)
            w = what(len(calls))
            if w == "raise":
                raise OSError("synthetic cleanup error")
            if w == "skip":
                return None
        return real(path, *a, **k)

    monkeypatch.setattr(gp.shutil, "rmtree", rmtree)
    return calls


def _interrupting_sleep(monkeypatch, on_call):
    """time.sleep for remove_api_dir's 0.2 s pauses: a KeyboardInterrupt on call number on_call."""
    real, calls = gp.time.sleep, []

    def sleep(s):
        if s == 0.2:
            calls.append(s)
            if len(calls) == on_call:
                raise KeyboardInterrupt
        return real(s)

    monkeypatch.setattr(gp.time, "sleep", sleep)


F8_FAILURE_CASES = {
    "oserror_once": (lambda m: _api_rmtree(m, lambda i: "raise" if i == 1 else None), 0),
    "oserror_always": (lambda m: _api_rmtree(m, lambda i: "raise"), 1),
    "interrupt_in_the_cleanup": (lambda m: (_api_rmtree(m, lambda i: "skip" if i == 1 else None),
                                            _interrupting_sleep(m, 1)), 0),
    "interrupt_in_the_finish_retry": (lambda m: (_api_rmtree(m, lambda i: "skip"),
                                                 _interrupting_sleep(m, 3)), 1),
}


@pytest.mark.parametrize("case", sorted(F8_FAILURE_CASES))
def test_f8_cleanup_never_changes_the_api_failure_exit(world, env, capfd, tmp_path, monkeypatch,
                                                       case):
    setup, left = F8_FAILURE_CASES[case]
    setup(monkeypatch)
    e = api_env(env, tmp_path)
    _harness_down()
    WORLD.api.script = [api_err(3, "unauthenticated", "auth_error", "API key not valid")]
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 2 and st["status"] == "preflight_refused", st
    assert st["reason"].startswith(st["primary_reason"] + "; API backup failed: CLI exit 3"), st
    assert st["backup"] == "failed" and st["via"] == "api"
    assert len(_api_dirs(e)) == left
    assert ("the API body directory could not be removed" in st["reason"]) is bool(left), st
    recs = log_entries(e)
    assert [r["status"] for r in recs] == ["started", "failed"] and recs[1]["stop_latch"] is False


def test_f8_cleanup_error_never_replaces_a_pending_interrupt(world, env, capfd, tmp_path,
                                                             monkeypatch):
    _api_rmtree(monkeypatch, lambda i: "raise")
    _harness_down()
    WORLD.api.script = [KeyboardInterrupt()]
    code, st, _, _ = run(capfd, tmp_path, api_env(env, tmp_path))
    assert code == 130 and st["status"] == "interrupted" and st["via"] == "api", st
    assert "the API body directory could not be removed" in st["reason"]
    assert log_entries(env)[-1]["stop_latch"] is False


def test_f8_cleanup_error_on_the_success_path_is_only_a_note(world, env, capfd, tmp_path,
                                                             monkeypatch):
    _api_rmtree(monkeypatch, lambda i: "raise")
    _harness_down()
    WORLD.api.script = [api_ok("KEPT-391")]
    code, st, out, _ = run(capfd, tmp_path, api_env(env, tmp_path), json_mode=False)
    assert code == 0 and st["backup"] == "ok" and out.strip() == "KEPT-391", st
    assert st["reason"].startswith("answer received through the API backup"), st
    assert "the API body directory could not be removed" in st["reason"]
    assert "OSError" not in st["reason"], st  # contained in the cleanup step, not a late error


def test_f8_finish_cleanup_error_keeps_the_not_run_exit(world, env, capfd, tmp_path, monkeypatch):
    left = tmp_path / "nocache-left"
    left.mkdir()
    monkeypatch.setitem(gp._HARDENED, "nocache", left)
    real = gp.shutil.rmtree

    def rmtree(path, *a, **k):
        if str(path) == str(left):
            raise OSError("synthetic cleanup error")
        return real(path, *a, **k)

    monkeypatch.setattr(gp.shutil, "rmtree", rmtree)
    _harness_down()
    code, st, _, _ = run(capfd, tmp_path, dict(api_env(env, tmp_path), GEMINIPRO_API_BACKUP="0"))
    assert code == 2 and st["status"] == "preflight_refused" and st["backup"] == "not_run", st
    assert "; API backup not run: GEMINIPRO_API_BACKUP=0" in st["reason"]
    assert "INVARIANT: the no-cache dir was created" in st["reason"]


# ---- N1 ---------------------------------------------------------------------------------

N1_SNAPSHOT = [
    (100, 50, 5000),   # the CLI child (the root)
    (200, 100, 4000),  # OLDER than the root, recorded parent 100: a reused pid, unrelated
    (206, 200, 9000),  # a child of that unrelated process
    (201, 100, 6000),  # a real child
    (202, 201, 7000),  # a real grandchild
    (203, 201, 5500),  # older than its recorded parent 201: unrelated
    (204, 100, None),  # creation time unreadable
    (205, 100, 0),     # creation time unreadable
]


def test_n1_an_older_process_with_the_same_recorded_parent_is_never_killed(world, monkeypatch):
    assert gp._descendants(100, 5000, N1_SNAPSHOT) == [(201, 6000), (202, 7000)]
    assert gp._descendants(100, None, N1_SNAPSHOT) == []  # the root's own time unknown
    monkeypatch.setattr(gp, "_snapshot", lambda: list(N1_SNAPSHOT), raising=False)
    proc = _Proc([])
    proc.pid = 100
    if os.name == "nt":
        gp._kill_descendants(proc, 5000)
        assert WORLD.kills == [(201, 6000), (202, 7000)], WORLD.kills
        WORLD.kills.clear()
        gp._kill_descendants(proc, None)
        assert WORLD.kills == []


@pytest.mark.skipif(os.name != "nt", reason="Windows tree kill")
@pytest.mark.parametrize("root_created", [5000, None])
def test_n1_timeout_path_tree_kill_is_verified_and_never_uses_taskkill(world, monkeypatch,
                                                                       root_created):
    """The timeout / interrupt path (_kill_tree): one snapshot while the root is alive, the
    root through its own handle, then only VERIFIED descendants through theirs - an older
    process carrying the root's pid as its recorded parent is never killed; no taskkill."""
    events, runs = [], []
    proc = FakePopen([])
    proc.pid = 100

    def snapshot():
        events.append(("snapshot", "root alive" if proc.returncode is None else "root dead"))
        return list(N1_SNAPSHOT)

    real_kill = proc.kill
    monkeypatch.setattr(proc, "kill", lambda: (events.append("root-kill"), real_kill()))
    monkeypatch.setattr(gp, "_snapshot", snapshot, raising=False)
    monkeypatch.setattr(gp.subprocess, "run", lambda argv, **k: runs.append(argv))
    gp._kill_tree(proc, root_created)
    assert runs == [] and proc.returncode is not None, (runs, events)
    if root_created:
        assert events[:2] == [("snapshot", "root alive"), "root-kill"], events
        assert WORLD.kills == [(201, 6000), (202, 7000)], WORLD.kills  # never (200, 4000)
    else:  # the root's creation time unknown: only the root, never descendants by pid alone
        assert WORLD.kills == [] and "root-kill" in events, (WORLD.kills, events)


def test_n1_the_backstop_passes_the_recorded_creation_time(world, env, tmp_path, monkeypatch):
    w, events, d = _backstop_world(env, tmp_path, monkeypatch, tree_sleep=0)
    seen = []
    monkeypatch.setattr(gp, "_kill_descendants", lambda p, c: seen.append((p.pid, c)),
                        raising=False)
    w.api_holder["created"] = 777
    w.backstop()
    assert seen == [(4242, 777)] and events[0] == "direct-kill"


def _own_python():
    return getattr(sys, "_base_executable", None) or sys.executable  # no venv launcher in between


@pytest.mark.skipif(os.name != "nt", reason="Windows process handles")
def test_n1_kill_verified_never_kills_by_pid_alone():
    """Only a process this test starts (a sleeping interpreter) is ever touched."""
    p = subprocess.Popen([_own_python(), "-c", "import time; time.sleep(30)"],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    try:
        created = lanew_log.pid_created(p.pid)
        assert created
        assert REAL["_kill_verified"](p.pid, created + 1) is False  # same pid, other process
        assert p.poll() is None
        assert REAL["_kill_verified"](p.pid, created) is True
        p.wait(timeout=10)
    finally:
        if p.poll() is None:
            p.kill()
            p.wait(timeout=10)


TREE_PARENT = ("import subprocess, sys, time\n"
               "c = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
               "print(c.pid, flush=True)\n"
               "time.sleep(60)\n")


TREE_PARENT_TO_FILE = ("import subprocess, sys, time\n"
                       "c = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
                       "open(sys.argv[1] + '.tmp', 'w').write(str(c.pid))\n"
                       "import os; os.replace(sys.argv[1] + '.tmp', sys.argv[1])\n"
                       "time.sleep(60)\n")


@pytest.mark.skipif(os.name != "nt", reason="Windows process snapshot")
def test_n1_real_timeout_path_kills_the_root_and_its_child(world, monkeypatch, tmp_path):
    """The real _run_api timeout path against processes this test starts: a root interpreter
    and the sleeper it starts -> both dead, with no taskkill. Nothing else is ever touched."""
    import threading
    import time as _t
    for n in ("_snapshot", "_kill_verified", "_created"):
        monkeypatch.setattr(gp, n, REAL[n])
    runs = []
    real_run = gp.subprocess.run
    monkeypatch.setattr(gp.subprocess, "run", lambda argv, *a, **k: (
        runs.append(argv), real_run(argv, *a, **k))[1])
    pidfile = str(tmp_path / "kid.pid")
    holder, seen, stop = {}, {}, threading.Event()

    def watch():  # the kid's identity (pid + creation time) while it is alive, and the root
        while not stop.is_set():
            if "root" not in seen and holder.get("proc") is not None:
                seen["root"] = holder["proc"]
            if "kid" not in seen:
                try:  # fix round 3 (P3-1): the root may be renaming the file right now
                    with open(pidfile) as f:
                        kid = int(f.read())
                except (OSError, ValueError):
                    pass  # not there yet, mid-rename or partly written: the next poll retries
                else:
                    seen["kid"], seen["kid_created"] = kid, lanew_log.pid_created(kid)
            _t.sleep(0.02)

    th = threading.Thread(target=watch, daemon=True)
    th.start()
    try:
        with pytest.raises(subprocess.TimeoutExpired):
            REAL["_run_api"]([_own_python(), "-c", TREE_PARENT_TO_FILE, pidfile], str(tmp_path),
                             dict(os.environ), 4, subprocess.DEVNULL, holder)
        stop.set()
        th.join(5)
        assert seen.get("kid_created"), seen  # the kid had started before the timeout
        assert seen["root"].poll() is not None and holder == {}
        end = _t.monotonic() + 10
        while lanew_log.pid_created(seen["kid"]) == seen["kid_created"] and _t.monotonic() < end:
            _t.sleep(0.05)
        assert lanew_log.pid_created(seen["kid"]) != seen["kid_created"]  # the child is dead too
        assert not any("taskkill" in str(a) for a in runs), runs
    finally:
        stop.set()
        root = seen.get("root")
        if root is not None and root.poll() is None:
            root.kill()
        if seen.get("kid_created") and lanew_log.pid_created(seen["kid"]) == seen["kid_created"]:
            REAL["_kill_verified"](seen["kid"], seen["kid_created"])


@pytest.mark.skipif(os.name != "nt", reason="Windows process snapshot")
def test_n1_real_tree_step_kills_the_child_of_a_dead_root(world, monkeypatch):
    """Only processes this test starts: a root interpreter and the sleeper it starts."""
    import time as _t
    for n in ("_snapshot", "_kill_verified"):
        monkeypatch.setattr(gp, n, REAL[n])
    root = subprocess.Popen([_own_python(), "-c", TREE_PARENT], stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    kid = kid_created = None
    try:
        created = lanew_log.pid_created(root.pid)
        kid = int(root.stdout.readline())
        kid_created = lanew_log.pid_created(kid)
        assert created and kid_created and kid_created >= created
        root.kill()
        root.wait(timeout=10)
        gp._kill_descendants(root, created)  # the root's pid stays ours: its handle is open
        end = _t.monotonic() + 10
        while lanew_log.pid_created(kid) == kid_created and _t.monotonic() < end:
            _t.sleep(0.05)
        assert lanew_log.pid_created(kid) != kid_created
    finally:
        if root.poll() is None:
            root.kill()
        if (REAL["_kill_verified"] and kid and kid_created
                and lanew_log.pid_created(kid) == kid_created):
            REAL["_kill_verified"](kid, kid_created)
        root.stdout.close()


# --------------------------------------------------------------------------
# API primary (2026-11-18): the paid API key first, the Gemini app as the fallback.
# The CLI error shape below is gemini-api v0.4.4's classified JSON error envelope
# (internal/output/output.go classifiedErrorEnvelope, MarshalIndent on stderr): the API's own
# body ({"error": {...}}) plus error_type, exit_code, message, hints, error_reason (when a
# reason was found) and status_code (the HTTP status, when there was one).
# --------------------------------------------------------------------------

PRIMARY_KEYS = BASE_KEYS | {"api_attempt", "api_reason", "requested_model"}


def primary_env(env, tmp_path, **extra):
    """api_env without the legacy pin: the default API primary mode (extra applied last)."""
    e = api_env(env, tmp_path)
    e.pop("GEMINIPRO_API_PRIMARY", None)
    e.update(extra)
    return e


def cli_error(rc=1, status_code=None, etype="api_error", reason=None, message="failed",
              google=None, noise=b"", stdout=b""):
    """The CLI's classified error envelope on stderr (indented, as the CLI prints it)."""
    env_ = {"error": google if google is not None else {"message": message},
            "error_type": etype, "exit_code": rc, "message": message, "hints": ["a hint"]}
    if reason:
        env_["error_reason"] = reason
    if status_code:
        env_["status_code"] = status_code
    return (rc, stdout, noise + json.dumps(env_, indent=2).encode())


def google_err(code, status, message="failed"):
    return {"code": code, "message": message, "status": status}


QUOTA_MSG = "You exceeded your current quota, please check your plan and billing details."
Q429 = cli_error(1, 429, "rate_limit_error", "RESOURCE_EXHAUSTED", QUOTA_MSG,
                 google_err(429, "RESOURCE_EXHAUSTED", QUOTA_MSG))


def _ledger(e):
    return os.path.splitext(e["GEMINIPRO_LOG"])[0] + "-api-day.jsonl"


def _ledger_count(e):
    return lanew_log.count_reservations(_ledger(e))[0]


def _app_untouched():
    return WORLD.harness_calls == 0 and WORLD.generate_calls == 0 and WORLD.requests == []


def test_p1_carbon_api_answers_and_the_app_is_never_touched(world, env, capfd, tmp_path):
    e = primary_env(env, tmp_path)
    WORLD.api.script = [api_ok("API-ANSWER-391", model="gemini-4-carbon")]
    code, st, out, err = run(capfd, tmp_path, e)
    assert code == 0 and st["status"] == "ok" and st["via"] == "api", st
    assert st["model"] == "gemini-4-carbon" and st["requested_model"] == "gemini-carbon", st
    assert st["api_attempt"] == "ok" and st["api_reason"] is None and st["model_mismatch"] is False
    assert set(st) == PRIMARY_KEYS | {"model_mismatch"}, st
    assert st["context"] is None and st["meter"] is None and st["submissions"] == 0
    assert _app_untouched()
    (c,) = WORLD.api.calls
    # FIX-1 A-F2: primary disables the CLI's own retries (one admitted attempt = at most one
    # upstream request)
    assert c["argv"] == [e["GEMINIPRO_API_CLI"], "generate", "--output-format", "json",
                         "--body", "@body.json", "--no-retries"] and c["stdin"] is subprocess.DEVNULL
    assert json.loads(c["body_raw"]) == {"input": CLEAN.decode(), "model": "gemini-4-carbon",
                                         "stream": False, "store": False}
    recs = log_entries(e)
    assert [r["status"] for r in recs] == ["started", "ok"], recs
    assert recs[0]["model"] == "gemini-4-carbon" and recs[1]["via"] == "api"
    assert recs[1]["stop_latch"] is False and "primary_exit" not in recs[1]
    report = open(st["report"], encoding="utf-8").read()
    assert "API-ANSWER-391" in report and "- via: api (primary" in report
    assert "- account: n/a (API key)" in report
    assert _ledger_count(e) == 1 and _api_dirs(e) == []
    assert out.strip().count("\n") == 0  # --json: the status line alone on stdout


def test_p1_hydrogen_maps_to_itself_and_default_mode_prints_the_answer(world, env, capfd, tmp_path):
    e = primary_env(env, tmp_path)
    code, st, out, err = run(capfd, tmp_path, e, args=("t1", "h", "--model", "gemini-4-hydrogen"),
                             json_mode=False)
    assert code == 0 and st["via"] == "api" and st["model"] == "gemini-4-hydrogen", st
    assert st["model_mismatch"] is False and out.strip() == "API-ANSWER-391"
    assert json.loads(WORLD.api.calls[0]["body_raw"])["model"] == "gemini-4-hydrogen"


LIVE_429_MSG = ("Rate limit exceeded for model gemini-4-carbon (limit: 0 input tokens per minute "
                "on Free Tier). Please upgrade your tier at https://ai.dev/rate-limit.")
REJECTIONS = {
    "429_quota": Q429,
    # the shape the live smoke got on 2026-11-18 (interactions API: a string error.code)
    "429_live_shape_2026_11_18": cli_error(1, 429, "rate_limit_error", None, LIVE_429_MSG,
                                           {"code": "too_many_requests", "message": LIVE_429_MSG}),
    # FIX-4 N1: only the CLI's own progress text (progress.go's spinner) may precede the
    # envelope ("429_after_cli_retry_lines", invented retry lines, moved to UNKNOWN)
    "429_after_the_cli_spinner": cli_error(
        1, 429, "rate_limit_error", "RESOURCE_EXHAUSTED", QUOTA_MSG,
        google_err(429, "RESOURCE_EXHAUSTED", QUOTA_MSG),
        noise=b"\r\x1b[2K| gemini-api generate\r\x1b[2K/ gemini-api generate\r\x1b[2K"),
    # FIX-4 N1 condition 5: "resource_exhausted_reason_without_status" moved to UNKNOWN
    "400": cli_error(2, 400, "validation_error", None, "bad", google_err(400, "INVALID_ARGUMENT")),
    "401": cli_error(3, 401, "authentication_error", "API_KEY_INVALID", "API key not valid",
                     google_err(401, "UNAUTHENTICATED")),
    "403": cli_error(3, 403, "authorization_error", None, "denied",
                     google_err(403, "PERMISSION_DENIED")),
    "404": cli_error(1, 404, "not_found", None, "no model", google_err(404, "NOT_FOUND")),
    # FIX-1 A-F3: "429_envelope_on_stdout_with_exit_0" moved to UNKNOWN (a proven rejection
    # needs a non-zero CLI exit and an empty stdout)
}


@pytest.mark.parametrize("case", sorted(REJECTIONS))
def test_p2_a_proven_rejection_falls_back_to_the_app(world, env, capfd, tmp_path, case):
    e = primary_env(env, tmp_path)
    WORLD.api.script = [REJECTIONS[case]]
    code, st, out, err = run(capfd, tmp_path, e)
    assert code == 0 and st["status"] == "ok" and st["via"] == "app", st
    assert st["api_attempt"] == "failed" and st["api_reason"] and len(st["api_reason"]) <= 300, st
    assert set(st) == PRIMARY_KEYS and st["model"] == "gemini-carbon", st
    assert st["requested_model"] == "gemini-carbon" and st["account_ok"] is True
    assert len(WORLD.api.calls) == 1 and WORLD.generate_calls == 1 and WORLD.harness_calls >= 1
    if case.startswith("429"):
        assert "429" in st["api_reason"] or "RESOURCE_EXHAUSTED" in st["api_reason"], st
    recs = log_entries(e)
    assert [r["status"] for r in recs] == ["started", "ok"], recs  # one admission per launch
    assert recs[1]["via"] == "app" and recs[1]["stop_latch"] is False
    assert _ledger_count(e) == 1 and _api_dirs(e) == []


SERVER = {n: cli_error(1, n, "server_error", None, "upstream", google_err(n, "UNAVAILABLE"))
          for n in (500, 502, 503, 504)}
UNKNOWN = {
    "timeout": subprocess.TimeoutExpired(["gemini-api"], 5),
    "oserror_after_spawn": OSError(32, "Broken pipe"),
    "http500": SERVER[500], "http502": SERVER[502], "http503": SERVER[503], "http504": SERVER[504],
    "live_server_error_shape": SERVER_ERR,  # never retried in primary mode
    "connection_error": cli_error(1, None, "connection_error", "CLI_CONNECTION",
                                  "error sending request: dial tcp: no such host"),
    "cli_validation_without_status": cli_error(2, None, "validation_error", "CLI_VALIDATION"),
    "cli_auth_without_status": cli_error(3, None, "authentication_error", "CLI_AUTHENTICATION"),
    "partial_stdout_then_429": (Q429[0], b'{"status": "in_progress", "steps": [{"type": "model_o',
                                Q429[2]),
    "guard_internal_error": (9, b"", b"gemini-guard: error: cannot start the real CLI: busy\n"),
    "stderr_not_json": (1, b"", b"panic: runtime error\n"),
    "not_json": (0, b"hello, not json", b""),
    "not_completed": api_ok("partial", status="in_progress", model="gemini-4-carbon"),
    "empty_answer": api_ok("", model="gemini-4-carbon"),
    "error_card": api_ok("Something went wrong. Please try again.", model="gemini-4-carbon"),
    "server_envelope_on_stdout_with_exit_0": (0, SERVER[503][2], b""),
    # FIX-1 A-F3 (was a REJECTIONS case under G1): exit 0 is never a proven rejection
    "429_envelope_on_stdout_with_exit_0": (0, Q429[2], b""),
    # FIX-4 N1 (were REJECTIONS cases): stderr lines that are not the CLI's own progress text
    # before the envelope, and a quota reason without the required outer status_code
    "429_after_cli_retry_lines": cli_error(
        1, 429, "rate_limit_error", "RESOURCE_EXHAUSTED", QUOTA_MSG,
        google_err(429, "RESOURCE_EXHAUSTED", QUOTA_MSG),
        noise=b"retrying in 2s (HTTP 429)\nretrying in 4s (HTTP 429)\n"),
    "resource_exhausted_reason_without_status": cli_error(
        1, None, "rate_limit_error", "QUOTA_EXCEEDED", QUOTA_MSG),
}


@pytest.mark.parametrize("case", sorted(UNKNOWN))
def test_p3_anything_else_after_dispatch_is_outcome_unknown_never_the_app(world, env, capfd,
                                                                          tmp_path, case):
    e = primary_env(env, tmp_path)
    WORLD.api.script = [UNKNOWN[case], api_ok(model="gemini-4-carbon")]
    code, st, out, err = run(capfd, tmp_path, e)
    assert code == 6 and st["status"] == "outcome_unknown", st
    assert st["via"] == "api" and st["api_attempt"] == "failed" and st["api_reason"], st
    assert len(WORLD.api.calls) == 1 and _app_untouched()  # no retry on either transport
    recs = log_entries(e)
    assert [r["status"] for r in recs] == ["started", "outcome_unknown"], recs
    assert recs[1]["stop_latch"] is False and recs[1]["via"] == "api"
    ok, why = lanew_log.check("t1", log_path=e["GEMINIPRO_LOG"], ceiling=12)
    assert ok, why  # an API ending never latches the run
    assert _api_dirs(e) == []


NOT_RUN = {
    "key_unset": ({"GEMINI_API_KEY": None}, "GEMINI_API_KEY is not set"),
    "key_blank": ({"GEMINI_API_KEY": "   "}, "GEMINI_API_KEY is blank"),
    "key_short": ({"GEMINI_API_KEY": "Ab3" * 5}, "too short"),
    # FIX-6 item 5: "cli_missing" (an explicit GEMINIPRO_API_CLI path that does not exist) moved
    # to test_fix6_an_explicit_cli_path_that_cannot_be_inspected_refuses_the_launch (exit 2)
    "cli_not_on_path": ({"GEMINIPRO_API_CLI": None}, "gemini-api is not on PATH"),
}


@pytest.mark.parametrize("case", sorted(NOT_RUN))
def test_p4_a_missing_precondition_is_not_run_and_the_app_answers(world, env, capfd, tmp_path,
                                                                  case):
    change, why = NOT_RUN[case]
    e = primary_env(env, tmp_path)
    for k, v in change.items():
        if v is None:
            e.pop(k, None)
        else:
            e[k] = str(tmp_path / "no-such-cli.exe") if v == "MISSING" else v
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 0 and st["via"] == "app" and st["api_attempt"] == "not_run", st
    assert why in st["api_reason"] and set(st) == PRIMARY_KEYS, st
    assert WORLD.api.calls == [] and WORLD.generate_calls == 1
    assert [r["status"] for r in log_entries(e)] == ["started", "ok"]
    assert not os.path.exists(_ledger(e))


def _reserve_today(e, n=1, run_="other", ts=None):
    for i in range(n):
        assert lanew_log.reserve(_ledger(e), {"ts": ts or lanew_log._now_iso(), "run": run_,
                                              "job_id": "pre%d" % i}, 1000)[0] == "reserved"


def test_p5_daily_api_ceiling_reached_skips_the_api(world, env, capfd, tmp_path):
    e = primary_env(env, tmp_path, GEMINIPRO_API_DAY_CEILING="2")
    _reserve_today(e, 2)
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 0 and st["via"] == "app" and st["api_attempt"] == "skipped", st
    assert "2/2" in st["api_reason"] and "local date" in st["api_reason"], st
    assert WORLD.api.calls == [] and WORLD.generate_calls == 1 and _ledger_count(e) == 2


def test_p5_ceiling_zero_is_api_off_in_both_modes(world, env, capfd, tmp_path):
    e = primary_env(env, tmp_path, GEMINIPRO_API_DAY_CEILING="0")
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 0 and st["via"] == "app" and st["api_attempt"] == "skipped", st
    assert "GEMINIPRO_API_DAY_CEILING=0" in st["api_reason"] and WORLD.api.calls == []
    _harness_down()  # legacy mode: the backup trigger fires but the paid CLI never runs
    code, st, _, _ = run(capfd, tmp_path, dict(e, GEMINIPRO_API_PRIMARY="0"), args=("t2", "x"))
    assert code == 2 and st["backup"] == "not_run" and "GEMINIPRO_API_DAY_CEILING=0" in st["reason"]
    assert WORLD.api.calls == [] and not os.path.exists(_ledger(e))


@pytest.mark.parametrize("bad", ["abc", "-1", "1.5", "4 0", "+3", "nan"])
def test_p5_a_bad_ceiling_is_usage_error_before_anything(world, env, capfd, tmp_path, bad):
    e = primary_env(env, tmp_path, GEMINIPRO_API_DAY_CEILING=bad)
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 64 and "GEMINIPRO_API_DAY_CEILING" in st["reason"], st
    assert WORLD.api.calls == [] and _app_untouched() and log_entries(e) == []
    code = gp.main(["--status", "--json"], e)  # --status validates it too (it reports api_day)
    assert code == 64 and WORLD.harness_calls == 0
    capfd.readouterr()


def test_p6_switch_off_is_the_old_order_and_the_backup_obeys_the_ceiling(world, env, capfd,
                                                                         tmp_path):
    e = primary_env(env, tmp_path, GEMINIPRO_API_PRIMARY="0")
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 0 and st["via"] == "app" and set(st) == BASE_KEYS, st  # app first, no API keys
    assert WORLD.api.calls == [] and WORLD.generate_calls == 1
    _harness_down()  # the legacy backup still runs - and reserves a day slot first
    code, st, _, _ = run(capfd, tmp_path, e, args=("t1", "b"))
    assert code == 0 and st["via"] == "api" and st["backup"] == "ok", st
    assert _ledger_count(e) == 1
    code, st, _, _ = run(capfd, tmp_path, dict(e, GEMINIPRO_API_DAY_CEILING="1"), args=("t1", "c"))
    assert code == 2 and st["backup"] == "not_run" and "daily API ceiling" in st["reason"], st
    assert len(WORLD.api.calls) == 1


def test_p7_a_model_with_no_api_id_is_app_only(world, env, capfd, tmp_path):
    e = primary_env(env, tmp_path)
    code, st, _, _ = run(capfd, tmp_path, e, args=("t1", "m", "--model", "gemini-flash-lite"))
    assert WORLD.api.calls == [] and WORLD.harness_calls >= 1, st  # the app path ran, alone
    assert st["api_attempt"] == "not_run" and "gemini-flash-lite" in st["api_reason"], st
    assert code == 4 and st["status"] == "model_not_available" and st["via"] == "app", st
    assert not os.path.exists(_ledger(e))


def _p8_launches(e, capfd, tmp_path):
    """Cases 1-3 with a CLI that echoes the key on every channel it has."""
    leak = API_KEY.encode()
    WORLD.api.script = [
        (0, api_ok("answer " + API_KEY, model="gemini-4-carbon")[1], b"debug: key=" + leak + b"\n"),
        cli_error(1, 429, "rate_limit_error", "RESOURCE_EXHAUSTED", "quota for key " + API_KEY,
                  google_err(429, "RESOURCE_EXHAUSTED", "quota for key " + API_KEY),
                  noise=b"\r\x1b[2K| gemini-api generate\r\x1b[2K/ gemini-api generate\r\x1b[2K"),  # FIX-4 N1 (key on an unknown line: test_fix4_n1_a_key_...)
        OSError(32, "broken pipe for " + API_KEY),
        subprocess.TimeoutExpired(["gemini-api", API_KEY], 5),
    ]
    seen = []
    for name, mode in (("ok", False), ("rej", False), ("err", True), ("tmo", False)):
        code, st, out, err = run(capfd, tmp_path, e, args=("t1", name), json_mode=mode)
        seen.append((code, st, out + err))
    return seen


def test_p8_the_key_never_reaches_any_output_or_file(world, env, capfd, tmp_path):
    e = primary_env(env, tmp_path)
    seen = _p8_launches(e, capfd, tmp_path)
    assert [c for c, _, _ in seen] == [0, 0, 6, 6], [s for _, s, _ in seen]
    assert seen[0][1]["via"] == "api" and seen[1][1]["via"] == "app"
    assert "answer [redacted]" in seen[0][2] and "[redacted]" in seen[1][1]["api_reason"]
    assert "[redacted]" in seen[2][1]["reason"]
    for _, st, text in seen:
        assert API_KEY not in text and API_KEY not in json.dumps(st)
    assert _key_leaks(str(tmp_path)) == []


def test_p8_negative_without_scrubbing_the_same_launches_leak(world, env, capfd, tmp_path,
                                                             monkeypatch):
    """The check above is live: with scrub() disabled the very same launches print the key."""
    monkeypatch.setattr(gp, "scrub", lambda text: text if isinstance(text, str) else str(text))
    seen = _p8_launches(primary_env(env, tmp_path), capfd, tmp_path)
    assert any(API_KEY in text for _, _, text in seen)


def test_p9_api_failure_plus_app_answer_counts_once_toward_the_run_ceiling(world, env, capfd,
                                                                          tmp_path):
    e = primary_env(env, tmp_path, GEMINIPRO_RUN_JOB_CEILING="2")
    WORLD.api.script = [Q429, Q429, api_ok(model="gemini-4-carbon")]
    for name in ("a", "b"):
        code, st, _, _ = run(capfd, tmp_path, e, args=("t1", name))
        assert code == 0 and st["via"] == "app" and st["api_attempt"] == "failed", st
    assert [r["status"] for r in log_entries(e)] == ["started", "ok", "started", "ok"]
    code, st, _, _ = run(capfd, tmp_path, e, args=("t1", "c"))
    assert code == 1 and st["status"] == "run_refused" and len(WORLD.api.calls) == 2, st


def test_g4_a_torn_ledger_line_is_skipped_with_a_note(world, env, capfd, tmp_path):
    e = primary_env(env, tmp_path)
    os.makedirs(os.path.dirname(_ledger(e)), exist_ok=True)
    with open(_ledger(e), "w", encoding="utf-8") as f:
        f.write('{"kind": "api_reservation", "ts": "2026-11-1')  # a crash mid-append
    WORLD.api.script = [api_ok(model="gemini-4-carbon")]
    code, st, out, err = run(capfd, tmp_path, e)
    assert code == 0 and st["via"] == "api", st
    assert "unreadable line" in err, err
    assert lanew_log.count_reservations(_ledger(e)) == (1, 1)


def test_r1_a_guard_content_denial_is_terminal_never_the_app(world, env, capfd, tmp_path):
    e = primary_env(env, tmp_path)
    WORLD.api.script = [(9, b"", b"gemini-guard: denied: --body: a signed link (sig=) in the "
                         b"request body\ngemini-guard: client content is not sent to Gemini "
                         b"while the key tier is unconfirmed (see the gemini-api skill).\n")]
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 7 and st["status"] == "brief_refused", st
    assert "signed link" in st["reason"] and "guard" in st["reason"], st
    assert st["via"] == "api" and st["api_attempt"] == "failed"
    assert _app_untouched() and len(WORLD.api.calls) == 1
    recs = log_entries(e)
    assert [r["status"] for r in recs] == ["started", "failed"] and recs[1]["stop_latch"] is False
    assert lanew_log.check("t1", log_path=e["GEMINIPRO_LOG"], ceiling=12)[0]


R2_ROUTES = {
    "default": ({}, ()),
    "api_off": ({"GEMINIPRO_API_DAY_CEILING": "0"}, ()),
    "cli_missing": ({"GEMINIPRO_API_CLI": None}, ()),
    "unmapped_model": ({}, ("--model", "gemini-flash-lite")),
}


@pytest.mark.parametrize("route", sorted(R2_ROUTES))
def test_r2_a_brief_carrying_the_key_is_refused_before_any_transport(world, env, capfd, tmp_path,
                                                                     route):
    change, extra = R2_ROUTES[route]
    e = primary_env(env, tmp_path)
    for k, v in change.items():
        if v is None:
            e.pop(k, None)
        else:
            e[k] = v
    brief = CLEAN + b"note " + API_KEY.encode() + b"\n"
    code, st, out, err = run(capfd, tmp_path, e, args=("t1", "k") + extra, brief=brief)
    assert code == 7 and st["status"] == "brief_refused" and "API key" in st["reason"], st
    assert WORLD.api.calls == [] and _app_untouched() and log_entries(e) == []
    assert API_KEY not in out + err


def test_r5_cap_reached_by_an_api_rejection_then_another_run_skips_the_api(world, env, capfd,
                                                                         tmp_path):
    e = primary_env(env, tmp_path, GEMINIPRO_API_DAY_CEILING="1")
    WORLD.api.script = [Q429]
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 0 and st["via"] == "app" and st["api_attempt"] == "failed", st
    code, st, _, _ = run(capfd, tmp_path, e, args=("t2", "next"))  # a different run slug
    assert code == 0 and st["via"] == "app" and st["api_attempt"] == "skipped", st
    assert len(WORLD.api.calls) == 1


def test_r5_an_unterminated_reservation_counts_and_yesterday_does_not(world, env, capfd, tmp_path):
    import datetime as dt
    e = primary_env(env, tmp_path, GEMINIPRO_API_DAY_CEILING="1")
    midnight = dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    late = (midnight - dt.timedelta(minutes=1)).astimezone(dt.timezone.utc)
    _reserve_today(e, 1, ts=late.strftime("%Y-%m-%dT%H:%M:%S.000Z"))  # yesterday 23:59 local
    WORLD.api.script = [api_ok(model="gemini-4-carbon")]
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 0 and st["via"] == "api", st
    e2 = primary_env(env, tmp_path, GEMINIPRO_API_DAY_CEILING="1",
                     GEMINIPRO_LOG=str(tmp_path / "other" / "geminipro-usage.jsonl"))
    os.makedirs(os.path.dirname(_ledger(e2)), exist_ok=True)
    _reserve_today(e2, 1)  # a reservation whose job never got a terminal record (a crash)
    code, st, _, _ = run(capfd, tmp_path, e2, args=("t3", "x"))
    assert code == 0 and st["api_attempt"] == "skipped", st
    assert len(WORLD.api.calls) == 1


def _r6_meter(e, capfd, tmp_path):
    set_meter(90, 10)
    return run(capfd, tmp_path, e), (1, "run_refused", False)


def _r6_model(e, capfd, tmp_path):
    return (run(capfd, tmp_path, e, args=("t1", "carbon", "--model", "gemini-4-hydrogen")),
            (4, "model_not_available", False))


def _r6_identity(e, capfd, tmp_path):
    WORLD.accounts = {PSID: WRONG, OTHER_PSID: THIRD}
    return run(capfd, tmp_path, e), (8, "account_mismatch", False)


def _r6_post(e, capfd, tmp_path):
    WORLD.gen_mode = "http500"
    return run(capfd, tmp_path, e), (6, "outcome_unknown", True)


R6_CASES = {"meter_refusal": _r6_meter, "model_unavailable": _r6_model,
            "identity_mismatch": _r6_identity, "app_post_failure": _r6_post}


@pytest.mark.parametrize("case", sorted(R6_CASES))
def test_r6_after_an_api_rejection_app_refusals_keep_their_exit_and_latch_only_on_post(
        world, env, capfd, tmp_path, case):
    e = primary_env(env, tmp_path)
    WORLD.api.script = [Q429, Q429]
    (code, st, _, _), (want, status, latched) = R6_CASES[case](e, capfd, tmp_path)
    assert code == want and st["status"] == status and st["api_attempt"] == "failed", st
    assert st["via"] == "app", st
    if not latched:
        assert "outcome unknown" not in st["reason"], st
    recs = log_entries(e)
    assert [r["status"] for r in recs][0] == "started" and len(recs) == 2, recs
    assert recs[1]["stop_latch"] is latched and recs[1]["exit"] == want, recs
    assert WORLD.generate_calls == (1 if latched else 0)
    # the next launch on the same slug
    WORLD.accounts = {PSID: RIGHT, OTHER_PSID: WRONG}
    WORLD.gen_mode = "ok"
    set_meter(10, 10)
    code, st, _, _ = run(capfd, tmp_path, e, args=("t1", "next"))
    if latched:
        assert code == 1 and st["status"] == "run_refused" and "latched" in st["reason"], st
    else:
        assert code == 0 and st["via"] == "app" and st["api_attempt"] == "failed", st


R7_CASES = {"other_model": ("gemini-4-hydrogen", "gemini-4-hydrogen", True),
            "no_model": (None, None, True),
            "models_prefix": ("models/gemini-4-carbon", "gemini-4-carbon", False)}


@pytest.mark.parametrize("case", sorted(R7_CASES))
def test_r7_the_answering_model_comes_from_the_response(world, env, capfd, tmp_path, case):
    returned, shown, mismatch = R7_CASES[case]
    e = primary_env(env, tmp_path)
    WORLD.api.script = [api_ok("KEPT-391", model=returned)]
    code, st, out, err = run(capfd, tmp_path, e)
    assert code == 0 and st["via"] == "api" and st["model"] == shown, st
    assert st["model_mismatch"] is mismatch and st["requested_model"] == "gemini-carbon", st
    assert json.loads(WORLD.api.calls[0]["body_raw"])["model"] == "gemini-4-carbon"
    assert len(WORLD.api.calls) == 1  # kept, never resent
    assert "KEPT-391" in open(st["report"], encoding="utf-8").read()
    term = log_entries(e)[-1]
    assert term["model"] == shown and term.get("model_mismatch", False) is mismatch, term


def test_r9_report_failure_on_the_api_path_keeps_the_answer(world, env, capfd, tmp_path,
                                                           monkeypatch):
    def boom(self):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(gp.Wrapper, "write_report", boom)
    WORLD.api.script = [api_ok("KEPT-ANSWER-391", model="gemini-4-carbon")]
    code, st, out, err = run(capfd, tmp_path, primary_env(env, tmp_path))
    assert code == 3 and st["status"] == "log_failure" and st["via"] == "api", st
    assert "KEPT-ANSWER-391" in err and out.strip().count("\n") == 0


def test_r9_terminal_append_failure_on_the_api_path_keeps_the_answer(world, env, capfd, tmp_path,
                                                                    monkeypatch):
    real = gp.lanew_log.append_line_verified
    monkeypatch.setattr(gp.lanew_log, "append_line_verified",
                        lambda path, line: False if '"status": "ok"' in line else real(path, line))
    WORLD.api.script = [api_ok("KEPT-ANSWER-391", model="gemini-4-carbon")]
    code, st, out, err = run(capfd, tmp_path, primary_env(env, tmp_path))
    assert code == 3 and st["status"] == "log_failure" and st["via"] == "api", st
    assert "KEPT-ANSWER-391" in err and os.path.exists(st["report"])


def test_r9_hard_backstop_on_the_api_primary_path(world, env, capfd, tmp_path, monkeypatch):
    seen = []
    real_primary = gp.Wrapper.api_primary
    monkeypatch.setattr(gp.Wrapper, "api_primary",
                        lambda self, p: seen.append(self) or real_primary(self, p))
    fake = WORLD.api

    def overrun(*a, **k):
        fake(*a, **k)
        seen[0].backstop()  # HARD_EXIT is a no-op here: main goes on afterwards
        raise subprocess.TimeoutExpired(["gemini-api"], 5)

    monkeypatch.setattr(gp, "_run_api", overrun)
    bf = tmp_path / "b.md"
    bf.write_bytes(CLEAN)
    gp.main(["t1", "carbon", "--brief-file", str(bf), "--json"], primary_env(env, tmp_path))
    out, _ = capfd.readouterr()
    lines = [l for l in out.splitlines() if l.startswith("{")]
    assert WORLD.hard_exits == [6] and len(lines) == 1, (WORLD.hard_exits, lines)
    hard = json.loads(lines[0])
    assert hard["status"] == "outcome_unknown" and hard["via"] == "api", hard
    assert "hard backstop" in hard["reason"]
    recs = log_entries(env)
    assert [r["status"] for r in recs] == ["started", "outcome_unknown"], recs
    assert recs[1]["stop_latch"] is False and _app_untouched()


def test_r10_a_blank_account_never_blocks_an_api_answer(world, env, capfd, tmp_path):
    e = primary_env(env, tmp_path, GEMINIPRO_ACCOUNT="  ")
    WORLD.api.script = [api_ok(model="gemini-4-carbon")]
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 0 and st["via"] == "api" and _app_untouched(), st


def test_r10_a_blank_account_after_an_api_rejection_refuses_before_any_app_step(world, env, capfd,
                                                                               tmp_path):
    e = primary_env(env, tmp_path, GEMINIPRO_ACCOUNT="  ")
    WORLD.api.script = [Q429]
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 2 and st["status"] == "preflight_refused" and st["api_attempt"] == "failed", st
    assert "GEMINIPRO_ACCOUNT" in st["reason"] and "app fallback" in st["reason"], st
    assert _app_untouched()
    recs = log_entries(e)
    assert [r["status"] for r in recs] == ["started", "failed"] and recs[1]["stop_latch"] is False


def test_status_reports_the_api_day_count(world, env, capfd, tmp_path):
    for e in (primary_env(env, tmp_path), env):
        os.makedirs(os.path.dirname(_ledger(e)), exist_ok=True)
        if not os.path.exists(_ledger(e)):
            _reserve_today(e, 3)
        code = gp.main(["--status", "--json"], dict(e, GEMINIPRO_API_DAY_CEILING="40"))
        st = json.loads(capfd.readouterr()[0])
        assert code == 0 and st["api_day"] == "3/40", st
        code = gp.main(["--status"], e)
        out, err = capfd.readouterr()
        assert code == 0 and "api_day: 3/40" in out.splitlines(), out
        assert out.splitlines()[0].startswith("Gemini usage:")
    assert WORLD.api.calls == []


# --------------------------------------------------------------------------
# FIX-1 (review round 1, 2026-11-18): dispatch safety of the API primary path.
# A-F2 child retries, A-F3/C-5 rejection evidence, A-F8 post-dispatch classification,
# A-F9 local faults, A-F10 the reservation's clock.
# --------------------------------------------------------------------------

def _fix1_env_fields(**over):
    """The CLI's classified 429 envelope as a dict (fields overridable; None-valued kept)."""
    env_ = {"error": google_err(429, "RESOURCE_EXHAUSTED", QUOTA_MSG),
            "error_type": "rate_limit_error", "exit_code": 1, "message": QUOTA_MSG,
            "hints": ["a hint"], "error_reason": "RESOURCE_EXHAUSTED", "status_code": 429}
    env_.update(over)
    return env_


def _fix1_err(obj, rc=1, stdout=b"", indent=2, before=b"", after=b""):
    return (rc, stdout, before + json.dumps(obj, indent=indent).encode() + after)


def _fix1_no(key, obj):
    obj = dict(obj)
    obj.pop(key)
    return obj


_COMPACT_429 = json.dumps(_fix1_env_fields()).encode()
_COMPLETED = json.loads(api_ok("PARTIAL-391", model="gemini-4-carbon")[1])


def test_fix1_f2_primary_disables_the_cli_retries_and_legacy_does_not(world, env, capfd,
                                                                      tmp_path):
    WORLD.api.script = [api_ok(model="gemini-4-carbon")]
    code, st, _, _ = run(capfd, tmp_path, primary_env(env, tmp_path))
    assert code == 0 and st["via"] == "api", st
    (c,) = WORLD.api.calls
    assert c["argv"].count("--no-retries") == 1 and c["argv"][-1] == "--no-retries", c["argv"]
    WORLD.api.calls.clear()
    _harness_down()  # the legacy backup: its argv (and its own one retry) are unchanged
    code, st, _, _ = run(capfd, tmp_path, api_env(env, tmp_path), args=("t2", "legacy"))
    assert code == 0 and st["backup"] == "ok", st
    (c,) = WORLD.api.calls
    assert "--no-retries" not in c["argv"], c["argv"]


def test_fix1_f2_the_legacy_retry_predicate_is_the_base_one(world, env, capfd, tmp_path):
    """Progress text, then a pretty-printed server error: the base parser found no JSON object
    there, so the legacy backup never retried it - the primary parser must not widen that."""
    pretty = json.dumps({"error": {"code": "service_unavailable", "message": "high demand"},
                         "error_type": "server_error", "exit_code": 1, "hints": []}, indent=2)
    stderr = b"retrying in 2s (HTTP 503)\n" + pretty.encode()
    assert gp._json_tail(stderr) is None
    _harness_down()
    WORLD.api.script = [(1, b"", stderr), api_ok("SECOND-TRY-391")]
    code, st, _, _ = run(capfd, tmp_path, api_env(env, tmp_path))
    assert code == 2 and st["backup"] == "failed" and len(WORLD.api.calls) == 1, st


FIX1_UNKNOWN = {
    # C-5: a one-line envelope that is not the end of stderr
    "c5_one_line_429_then_trailing_text": (1, b"", _COMPACT_429 + b"\nfatal: context deadline "
                                           b"exceeded while reading the response body\n"),
    "indented_429_then_trailing_text": _fix1_err(_fix1_env_fields(), after=b"\nfatal: closed\n"),
    "429_then_another_json_line": (1, b"", _COMPACT_429 + b'\n{"note": "trailing"}\n'),
    # (d) a malformed outer status is never discarded in favour of a nested quota reason
    "outer_status_string": _fix1_err(_fix1_env_fields(status_code="429")),
    "outer_status_null": _fix1_err(_fix1_env_fields(status_code=None)),
    "outer_status_float": _fix1_err(_fix1_env_fields(status_code=429.0)),
    "outer_status_bool": _fix1_err(_fix1_env_fields(status_code=True)),
    "outer_429_but_nested_503": _fix1_err(_fix1_env_fields(
        error=google_err(503, "UNAVAILABLE"))),
    "no_outer_status_nested_403_only": _fix1_err(_fix1_no("status_code", _fix1_env_fields(
        error=google_err(403, "PERMISSION_DENIED"), error_reason=None))),
    "no_outer_status_quota_reason_nested_500": _fix1_err(_fix1_no("status_code", _fix1_env_fields(
        error=google_err(500, "RESOURCE_EXHAUSTED")))),
    # rejection and generation evidence mixed
    "envelope_with_generation_fields": _fix1_err(_fix1_env_fields(
        status="completed", steps=_COMPLETED["steps"])),
    "429_with_whitespace_on_stdout": _fix1_err(_fix1_env_fields(), stdout=b"\n"),
    "429_exit_0_with_completed_output": (0, json.dumps(dict(
        _COMPLETED, error_type="rate_limit_error", status_code=429)).encode(), b""),
    # FIX-4 N1 (were FIX1_REJECTIONS cases): an unknown stderr line before the envelope; no
    # outer status_code (condition 5 requires it)
    "one_line_429_as_the_last_line": (1, b"", b"progress\n" + _COMPACT_429 + b"\n\n"),
    "no_outer_status_quota_reason_nested_429": _fix1_err(_fix1_no("status_code",
                                                                  _fix1_env_fields())),
}


@pytest.mark.parametrize("case", sorted(FIX1_UNKNOWN))
def test_fix1_f3_ambiguous_rejection_evidence_is_outcome_unknown(world, env, capfd, tmp_path,
                                                                case):
    e = primary_env(env, tmp_path)
    WORLD.api.script = [FIX1_UNKNOWN[case], api_ok(model="gemini-4-carbon")]
    code, st, out, err = run(capfd, tmp_path, e)
    assert code == 6 and st["status"] == "outcome_unknown", st
    assert st["via"] == "api" and st["api_attempt"] == "failed" and st["api_reason"], st
    assert len(WORLD.api.calls) == 1 and _app_untouched()
    recs = log_entries(e)
    assert [r["status"] for r in recs] == ["started", "outcome_unknown"], recs
    assert recs[1]["stop_latch"] is False


FIX1_REJECTIONS = {
    # FIX-4 N1: "one_line_429_as_the_last_line" (after an unknown "progress" line) and
    # "no_outer_status_quota_reason_nested_429" (no outer status_code) moved to FIX1_UNKNOWN
    "one_line_429_as_the_last_line_after_the_spinner": (1, b"", b"\r\x1b[2K| gemini-api generate\r\x1b[2K/ gemini-api generate\r\x1b[2K" + _COMPACT_429 + b"\n\n"),
    "outer_429_live_string_code": _fix1_err(_fix1_env_fields(
        error={"code": "too_many_requests", "message": "slow down"}, error_reason=None)),
}


@pytest.mark.parametrize("case", sorted(FIX1_REJECTIONS))
def test_fix1_f3_a_final_unambiguous_rejection_still_falls_back(world, env, capfd, tmp_path,
                                                              case):
    e = primary_env(env, tmp_path)
    WORLD.api.script = [FIX1_REJECTIONS[case]]
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 0 and st["via"] == "app" and st["api_attempt"] == "failed", st
    assert len(WORLD.api.calls) == 1 and WORLD.generate_calls == 1


@pytest.mark.parametrize("exc", [KeyboardInterrupt, asyncio.CancelledError])
def test_fix1_f8_an_interrupt_after_the_api_spawn_is_outcome_unknown(world, env, capfd, tmp_path,
                                                                    exc):
    e = primary_env(env, tmp_path)
    WORLD.api.script = [exc()]
    code, st, _, _ = run(capfd, tmp_path, e)
    # the interrupt contract keeps exit 130; the status and the record say outcome_unknown
    assert code == 130 and st["status"] == "outcome_unknown" and st["via"] == "api", st
    assert "outcome unknown" in st["reason"] and _app_untouched() and len(WORLD.api.calls) == 1
    recs = log_entries(e)
    assert [r["status"] for r in recs] == ["started", "outcome_unknown"], recs
    assert recs[1]["stop_latch"] is False and recs[1]["exit"] == 130
    assert lanew_log.check("t1", log_path=e["GEMINIPRO_LOG"], ceiling=12)[0]


FIX1_BAD_COMPLETED = {
    "steps_not_a_list": {"status": "completed", "model": "gemini-4-carbon", "steps": 5},
    "content_not_a_list": {"status": "completed", "model": "gemini-4-carbon",
                           "steps": [{"type": "model_output", "content": 7}]},
}


@pytest.mark.parametrize("case", sorted(FIX1_BAD_COMPLETED))
def test_fix1_f8_a_completed_shape_that_fails_to_parse_is_outcome_unknown(world, env, capfd,
                                                                         tmp_path, case):
    e = primary_env(env, tmp_path)
    WORLD.api.script = [(0, json.dumps(FIX1_BAD_COMPLETED[case]).encode(), b""),
                        api_ok(model="gemini-4-carbon")]
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 6 and st["status"] == "outcome_unknown" and st["via"] == "api", st
    assert len(WORLD.api.calls) == 1 and _app_untouched()
    assert [r["status"] for r in log_entries(e)] == ["started", "outcome_unknown"]


def test_fix1_f8_an_unexpected_error_after_the_api_spawn_is_outcome_unknown(world, env, capfd,
                                                                           tmp_path, monkeypatch):
    def boom(self, proc, api_model):
        raise RuntimeError("the judge broke")

    monkeypatch.setattr(gp.Wrapper, "api_judge", boom)
    e = primary_env(env, tmp_path)
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 6 and st["status"] == "outcome_unknown", st
    assert len(WORLD.api.calls) == 1 and _app_untouched()


@pytest.mark.parametrize("where", ["before_publish", "after_publish"])
def test_fix1_f8_an_interrupt_never_keeps_an_answer_labelled_with_the_requested_model(
        world, env, capfd, tmp_path, monkeypatch, where):
    if where == "before_publish":
        def interrupt(model):
            raise KeyboardInterrupt
        monkeypatch.setattr(gp, "api_model_name", interrupt)
    else:
        real_log = gp.log

        def log(msg):
            if str(msg).startswith("API answered"):
                raise KeyboardInterrupt
            real_log(msg)
        monkeypatch.setattr(gp, "log", log)
    e = primary_env(env, tmp_path)
    WORLD.api.script = [api_ok("KEPT-391", model="gemini-4-hydrogen")]
    code, st, out, err = run(capfd, tmp_path, e)
    report = st.get("report")
    kept = "KEPT-391" in out + err or bool(report and os.path.exists(report) and "KEPT-391" in
                                          open(report, encoding="utf-8").read())
    assert not kept or (st["model"] == "gemini-4-hydrogen" and st["model_mismatch"] is True), st
    if where == "before_publish":
        assert code == 130 and st["status"] == "outcome_unknown" and not kept, st
    else:
        assert code == 0 and kept, st
    assert len(WORLD.api.calls) == 1 and _app_untouched()


@pytest.mark.parametrize("how", ["explicit", "path"])
def test_fix1_f9_a_key_bearing_cli_path_refuses_the_launch(world, env, capfd, tmp_path,
                                                           monkeypatch, how):
    e = primary_env(env, tmp_path)
    cli = tmp_path / ("gemini-api-%s.exe" % API_KEY)
    cli.write_bytes(b"")
    if how == "explicit":
        e["GEMINIPRO_API_CLI"] = str(cli)
    else:
        e.pop("GEMINIPRO_API_CLI")
        monkeypatch.setattr(gp.shutil, "which", lambda name, *a, **k: (
            str(cli) if name == gp.API_CLI_NAME else "C:/fake/browser-harness.exe"))
    code, st, out, err = run(capfd, tmp_path, e)
    assert code == 2 and st["status"] == "preflight_refused", st
    assert "CLI path contains the API key" in st["reason"] and st["api_attempt"] == "not_run", st
    assert WORLD.api.calls == [] and _app_untouched() and log_entries(e) == []
    assert API_KEY not in out + err


def test_fix1_f9_too_little_time_refuses_before_the_app(world, env, capfd, tmp_path, monkeypatch):
    monkeypatch.setattr(gp, "JOB_MIN", 200)  # over the 120 s total deadline
    e = primary_env(env, tmp_path)
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 5 and st["status"] == "deadline" and st["api_attempt"] == "not_run", st
    assert WORLD.api.calls == [] and _app_untouched() and log_entries(e) == []


def test_fix1_f9_no_time_left_for_the_attempt_refuses_after_admission(world, env, capfd, tmp_path,
                                                                      monkeypatch):
    monkeypatch.setattr(gp, "API_MARGIN", 1000)  # the attempt's timeout comes out <= 0
    e = primary_env(env, tmp_path)
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 5 and st["status"] == "deadline" and st["api_attempt"] == "not_run", st
    assert WORLD.api.calls == [] and _app_untouched() and _api_dirs(e) == []
    recs = log_entries(e)
    assert [r["status"] for r in recs] == ["started", "failed"] and recs[1]["stop_latch"] is False


def test_fix1_f9_an_unreadable_ledger_refuses_the_launch(world, env, capfd, tmp_path):
    e = primary_env(env, tmp_path)
    os.makedirs(_ledger(e))  # a directory where the ledger file belongs: it cannot be read
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 3 and st["status"] == "log_failure" and "ledger" in st["reason"], st
    assert st["api_attempt"] == "skipped" and WORLD.api.calls == [] and _app_untouched()
    assert log_entries(e) == []


@pytest.mark.parametrize("fault", ["log_error", "raises"])
def test_fix1_f9_a_reservation_write_or_lock_failure_refuses_the_launch(world, env, capfd, tmp_path,
                                                                        monkeypatch, fault):
    def reserve(*a, **k):
        if fault == "raises":
            raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")
        return ("log_error", None, 0)

    monkeypatch.setattr(gp.lanew_log, "reserve", reserve)
    e = primary_env(env, tmp_path)
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 3 and st["status"] == "log_failure" and "reservation" in st["reason"], st
    assert st["api_attempt"] == "skipped" and WORLD.api.calls == [] and _app_untouched()
    recs = log_entries(e)
    assert [r["status"] for r in recs] == ["started", "failed"] and recs[1]["stop_latch"] is False
    assert lanew_log.check("t1", log_path=e["GEMINIPRO_LOG"], ceiling=12)[0]


def test_fix1_f9_a_ceiling_refusal_at_reservation_still_falls_back(world, env, capfd, tmp_path,
                                                                    monkeypatch):
    monkeypatch.setattr(gp.lanew_log, "reserve", lambda *a, **k: ("refused", 40, 0))
    e = primary_env(env, tmp_path)
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 0 and st["via"] == "app" and st["api_attempt"] == "skipped", st
    assert WORLD.api.calls == [] and WORLD.generate_calls == 1
    assert [r["status"] for r in log_entries(e)] == ["started", "ok"]


def test_fix1_f9_the_cli_vanishing_at_spawn_falls_back_to_the_app(world, env, capfd, tmp_path):
    e = primary_env(env, tmp_path)
    WORLD.api.script = [gp._mark_unspawned(FileNotFoundError(2, "The system cannot find the file"))]
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 0 and st["via"] == "app" and st["api_attempt"] == "not_run", st
    assert "not found" in st["api_reason"] or "cannot find" in st["api_reason"], st
    assert len(WORLD.api.calls) == 1 and WORLD.generate_calls == 1
    recs = log_entries(e)
    assert [r["status"] for r in recs] == ["started", "ok"] and recs[1]["via"] == "app", recs


def test_fix1_f9_a_file_not_found_after_the_spawn_stays_outcome_unknown(world, env, capfd,
                                                                        tmp_path):
    e = primary_env(env, tmp_path)
    WORLD.api.script = [FileNotFoundError(2, "gone after the spawn")]  # not Popen's own
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 6 and st["status"] == "outcome_unknown" and _app_untouched(), st


@pytest.mark.parametrize("raised,tagged", [(FileNotFoundError, True), (PermissionError, False)])
def test_fix1_f9_run_api_tags_only_popens_own_file_not_found(monkeypatch, tmp_path, raised,
                                                             tagged):
    def popen(*a, **k):
        raise raised(2, "refused by the test")

    monkeypatch.setattr(gp.subprocess, "Popen", popen)
    holder = {}
    with pytest.raises(raised) as ei:
        REAL["_run_api"](["no-such-cli"], str(tmp_path), {}, 1, subprocess.DEVNULL, holder)
    assert gp._unspawned(ei.value) is tagged and holder == {}


def test_fix1_f10_the_reservation_row_is_stamped_under_the_ledger_lock(world, env, capfd, tmp_path,
                                                                       monkeypatch):
    rows, real = [], gp.lanew_log.reserve

    def spy(path, row, ceiling, *a, **k):
        rows.append(dict(row))
        return real(path, row, ceiling, *a, **k)

    monkeypatch.setattr(gp.lanew_log, "reserve", spy)
    e = primary_env(env, tmp_path)
    WORLD.api.script = [api_ok(model="gemini-4-carbon")]
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 0 and len(rows) == 1 and "ts" not in rows[0], rows
    with open(_ledger(e), encoding="utf-8") as f:
        (row,) = [json.loads(line) for line in f if line.strip()]
    assert row["ts"] and lanew_log.count_reservations(_ledger(e)) == (1, 0)


# --------------------------------------------------------------------------
# FIX-4 (2026-11-18, review round 2): N1 a proven rejection is an allowlist over BOTH channels;
# N5 a CLI path that exists but is not a regular file is a local fault; N6 a damaged API-day
# ledger refuses; N7 an answer that is not encodable UTF-8 is outcome unknown
# --------------------------------------------------------------------------

# gemini-api v0.4.4 internal/output/progress.go: the request spinner (the CLI's only non-result
# stderr text; never printed in machine mode or to a pipe): frames "\r\x1b[2K%c %s" (%c from
# "|/-\\", %s the command path cut to the terminal width), then the clear "\r\x1b[2K"
_SPIN = (b"\r\x1b[2K| gemini-api generate\r\x1b[2K/ gemini-api generate"
         b"\r\x1b[2K- gemini-api generate\r\x1b[2K\\ gemini-api generate\r\x1b[2K")
_SERVER_503_PRETTY = SERVER[503][2]
_COMPLETED_LINE = json.dumps(_COMPLETED).encode()

FIX4_UNKNOWN = {
    # contrary dispatch evidence BEFORE a final 429 envelope
    "n1_5xx_envelope_then_429": (1, b"", _SERVER_503_PRETTY + b"\n" + Q429[2]),
    "n1_5xx_line_then_429": (1, b"", SERVER_ERR[2] + b"\n" + Q429[2]),
    "n1_completed_interaction_then_429": (1, b"", _COMPLETED_LINE + b"\n" + Q429[2]),
    "n1_completed_pretty_then_429": (1, b"", json.dumps(_COMPLETED, indent=2).encode() + b"\n"
                                     + Q429[2]),
    # error_type outside the rejection allowlist, with an accepted outer status
    "n1_server_error_type_429_no_nested_code": _fix1_err(_fix1_env_fields(
        error_type="server_error", error={"code": "too_many_requests", "message": "x"})),
    "n1_server_error_type_429_nested_429": _fix1_err(_fix1_env_fields(error_type="server_error")),
    "n1_api_error_type_429": _fix1_err(_fix1_env_fields(error_type="api_error")),
    "n1_connection_error_type_400": _fix1_err(_fix1_env_fields(
        error_type="connection_error", status_code=400, error=google_err(400, "INVALID_ARGUMENT"))),
    "n1_unknown_type_403": _fix1_err(_fix1_env_fields(
        error_type="quota_teapot", status_code=403, error=google_err(403, "PERMISSION_DENIED"))),
    "n1_no_error_type": _fix1_err(_fix1_no("error_type", _fix1_env_fields())),
    # stderr text that is not a known CLI progress shape before the envelope
    "n1_spinner_with_a_foreign_label": (1, b"", b"\r\x1b[2K| HTTP 503 upstream\r\x1b[2K" + Q429[2]),
    "n1_spinner_after_the_envelope": (1, b"", Q429[2] + b"\r\x1b[2K| gemini-api generate"),
    "n1_bare_escape_before_429": (1, b"", b"\x1b[31m" + Q429[2]),
    "n1_two_envelopes": (1, b"", Q429[2] + b"\n" + Q429[2]),
    "n1_duplicate_status_code_key": (1, b"", b'{"error_type": "rate_limit_error", "exit_code": 1, '
                                     b'"status_code": 503, "status_code": 429}'),
    "n1_stderr_not_utf8": (1, b"", b"\xff\xfe" + Q429[2]),
    "n1_nested_code_float_mismatch": _fix1_err(_fix1_env_fields(
        error={"code": 503.0, "message": "x", "status": "UNAVAILABLE"})),
    # condition 5 (the outer status is required) and unknown stderr lines: see the cases moved
    # to UNKNOWN / FIX1_UNKNOWN ("429_after_cli_retry_lines", "one_line_429_as_the_last_line", ...)
    # the guard's exit 9: a content denial only with an empty stdout; anything else is unknown
    "n1_exit_9_with_a_clean_429_envelope": (9, b"", Q429[2]),
    "n1_guard_denial_with_stdout": (9, b"partial", b"gemini-guard: denied: a signed link\n"),
}


@pytest.mark.parametrize("case", sorted(FIX4_UNKNOWN))
def test_fix4_n1_anything_but_an_allowlisted_rejection_is_outcome_unknown(world, env, capfd,
                                                                         tmp_path, case):
    e = primary_env(env, tmp_path)
    WORLD.api.script = [FIX4_UNKNOWN[case], api_ok(model="gemini-4-carbon")]
    code, st, out, err = run(capfd, tmp_path, e)
    assert code == 6 and st["status"] == "outcome_unknown", st
    assert st["via"] == "api" and st["api_attempt"] == "failed" and st["api_reason"], st
    assert len(WORLD.api.calls) == 1 and _app_untouched()
    recs = log_entries(e)
    assert [r["status"] for r in recs] == ["started", "outcome_unknown"], recs
    assert recs[1]["stop_latch"] is False and _ledger_count(e) == 1


FIX4_REJECTIONS = {
    "n1_known_spinner_then_429": (1, b"", _SPIN + Q429[2]),
    "n1_spinner_cut_to_the_terminal_width_then_429": (
        1, b"", b"\r\x1b[2K| gemi\r\x1b[2K/ gemi\r\x1b[2K" + Q429[2]),
    "n1_spinner_then_one_line_429_and_blank_lines": (1, b"", _SPIN + _COMPACT_429 + b"\n\n"),
    "n1_blank_lines_then_429": (1, b"", b"\n\r\n" + Q429[2] + b"\n"),
    "n1_service_disabled_403": _fix1_err(_fix1_env_fields(
        error_type="service_disabled", status_code=403, error_reason="SERVICE_DISABLED",
        error=google_err(403, "PERMISSION_DENIED"))),
    "n1_billing_disabled_403": _fix1_err(_fix1_env_fields(
        error_type="billing_disabled", status_code=403, error_reason="BILLING_DISABLED",
        error=google_err(403, "PERMISSION_DENIED"))),
    # FIX-6 item 1: "n1_nested_code_float_equal" (error.code 429.0) moved to FIX6_UNKNOWN as
    # "nested_code_429_float" - numeric codes compare as exact ints only
}


@pytest.mark.parametrize("case", sorted(FIX4_REJECTIONS))
def test_fix4_n1_known_progress_then_an_allowlisted_rejection_falls_back(world, env, capfd,
                                                                         tmp_path, case):
    e = primary_env(env, tmp_path)
    WORLD.api.script = [FIX4_REJECTIONS[case]]
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 0 and st["via"] == "app" and st["api_attempt"] == "failed", st
    assert len(WORLD.api.calls) == 1 and WORLD.generate_calls == 1
    assert [r["status"] for r in log_entries(e)] == ["started", "ok"]


def test_fix4_n1_a_key_on_an_unknown_stderr_line_is_unknown_and_never_echoed(world, env, capfd,
                                                                            tmp_path):
    e = primary_env(env, tmp_path)
    WORLD.api.script = [cli_error(1, 429, "rate_limit_error", "RESOURCE_EXHAUSTED",
                                  "quota for key " + API_KEY,
                                  google_err(429, "RESOURCE_EXHAUSTED", "quota for key " + API_KEY),
                                  noise=b"retry with key " + API_KEY.encode() + b"\n")]
    code, st, out, err = run(capfd, tmp_path, e, json_mode=False)
    assert code == 6 and st["status"] == "outcome_unknown" and _app_untouched(), st
    assert "[redacted]" in st["api_reason"] and API_KEY not in out + err
    assert API_KEY not in json.dumps(st) and _key_leaks(str(tmp_path)) == []  # files, records


@pytest.mark.parametrize("stderr", [Q429[2], SERVER[503][2], b"warning: something odd\n",
                                    b"\xff not utf-8"])
def test_fix4_n1_exit_0_with_an_answer_and_stderr_keeps_the_answer_with_a_warning(
        world, env, capfd, tmp_path, stderr):
    e = primary_env(env, tmp_path)
    WORLD.api.script = [(0, api_ok("KEPT-391", model="gemini-4-carbon")[1], stderr)]
    code, st, out, err = run(capfd, tmp_path, e, json_mode=False)
    assert code == 0 and st["status"] == "ok" and st["via"] == "api", st
    assert out.strip() == "KEPT-391" and st["api_stderr_warning"] is True, st
    assert set(st) == PRIMARY_KEYS | {"model_mismatch", "api_stderr_warning"}, st
    assert len(WORLD.api.calls) == 1 and _app_untouched()
    assert "something odd" not in err and "rate_limit_error" not in err


def test_fix4_n1_exit_0_with_only_spinner_text_on_stderr_has_no_warning(world, env, capfd,
                                                                        tmp_path):
    e = primary_env(env, tmp_path)
    WORLD.api.script = [(0, api_ok("KEPT-391", model="gemini-4-carbon")[1], _SPIN)]
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 0 and st["via"] == "api" and "api_stderr_warning" not in st, st


def test_fix4_n1_the_progress_shapes_are_a_named_constant(world):
    assert gp.API_PROGRESS_LABEL == "gemini-api generate"
    assert len(gp.API_PROGRESS_SHAPES) == 2
    assert gp.api_envelope(_SPIN + Q429[2]) == json.loads(Q429[2])
    assert gp.api_envelope(b"x" + Q429[2]) is None
    assert gp.API_REJECT_TYPES == frozenset((
        "authentication_error", "authorization_error", "service_disabled", "billing_disabled",
        "not_found", "validation_error", "rate_limit_error"))


@pytest.mark.parametrize("kind", ["directory", "stat_raises"])
def test_fix4_n5_a_cli_path_that_is_not_a_regular_file_refuses_the_launch(world, env, capfd,
                                                                          tmp_path, monkeypatch,
                                                                          kind):
    e = primary_env(env, tmp_path)
    if kind == "directory":
        d = tmp_path / "gemini-api-dir"
        d.mkdir()
        e["GEMINIPRO_API_CLI"] = str(d)
    else:
        target, real = e["GEMINIPRO_API_CLI"], os.stat

        def stat(p, *a, **k):
            if str(p) == target:
                raise PermissionError(13, "Access is denied", target)
            return real(p, *a, **k)
        monkeypatch.setattr(gp.os, "stat", stat)
    code, st, out, err = run(capfd, tmp_path, e)
    assert code == 2 and st["status"] == "preflight_refused", st
    assert st["api_attempt"] == "not_run" and "GEMINIPRO_API_CLI" in st["api_reason"], st
    assert WORLD.api.calls == [] and _app_untouched() and log_entries(e) == []
    assert not os.path.exists(_ledger(e))


def test_fix4_n5_legacy_keeps_a_not_a_file_cli_as_backup_not_run(world, env, capfd, tmp_path):
    d = tmp_path / "gemini-api-dir"
    d.mkdir()
    e = dict(api_env(env, tmp_path), GEMINIPRO_API_CLI=str(d))
    _harness_down()
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 2 and st["backup"] == "not_run" and "not a regular file" in st["reason"], st
    assert WORLD.api.calls == []


def _damage_ledger(e):
    os.makedirs(os.path.dirname(_ledger(e)), exist_ok=True)
    row = json.dumps({"kind": "api_reservation", "ts": lanew_log._now_iso(), "run": "x"})
    with open(_ledger(e), "w", encoding="utf-8") as f:
        f.write(row + "\n" + "{not json\n" + row + "\n")


def test_fix4_n6_a_damaged_middle_ledger_line_refuses_the_launch(world, env, capfd, tmp_path):
    e = primary_env(env, tmp_path)
    _damage_ledger(e)
    before = open(_ledger(e), "rb").read()
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 3 and st["status"] == "log_failure", st
    assert "API-day ledger damaged at line 2" in st["reason"] and st["api_attempt"] == "skipped", st
    assert WORLD.api.calls == [] and _app_untouched() and log_entries(e) == []
    assert open(_ledger(e), "rb").read() == before  # never repaired or appended to


def test_fix4_n6_legacy_a_damaged_ledger_refuses_the_backup_with_exit_3(world, env, capfd,
                                                                        tmp_path):
    e = api_env(env, tmp_path)
    _damage_ledger(e)
    _harness_down()
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 3 and st["status"] == "log_failure", st
    assert "API-day ledger damaged at line 2" in st["reason"] and st["backup"] == "not_run", st
    assert WORLD.api.calls == [] and log_entries(e) == []


def test_fix4_n6_a_torn_tail_healed_by_one_launch_never_blocks_the_next(world, env, capfd,
                                                                        tmp_path):
    e = primary_env(env, tmp_path)
    os.makedirs(os.path.dirname(_ledger(e)), exist_ok=True)
    with open(_ledger(e), "w", encoding="utf-8") as f:
        f.write('{"kind": "api_reservation", "ts": "2026-11-1')  # a crash mid-append
    WORLD.api.script = [api_ok(model="gemini-4-carbon"), api_ok(model="gemini-4-carbon")]
    for name in ("a", "b"):
        code, st, _, err = run(capfd, tmp_path, e, args=("t1", name))
        assert code == 0 and st["via"] == "api", st
        assert "unreadable line" in err, err
    assert lanew_log.count_reservations(_ledger(e)) == (2, 1)


def test_fix4_n7_an_answer_with_a_lone_surrogate_is_outcome_unknown(world, env, capfd, tmp_path):
    e = primary_env(env, tmp_path)
    WORLD.api.script = [api_ok("KEPT\ud800391", model="gemini-4-carbon"),
                        api_ok(model="gemini-4-carbon")]
    code, st, out, err = run(capfd, tmp_path, e)
    assert code == 6 and st["status"] == "outcome_unknown" and st["via"] == "api", st
    assert "UTF-8" in st["api_reason"], st
    assert st["report"] is None or not os.path.exists(st["report"]), st
    assert "KEPT" not in out + err and len(WORLD.api.calls) == 1 and _app_untouched()
    assert [r["status"] for r in log_entries(e)] == ["started", "outcome_unknown"]


# --------------------------------------------------------------------------
# FIX-6 (2026-11-19, review round 3): rejection evidence hardening (items 1-4), an explicit
# CLI path that cannot be inspected is a local fault (item 5), the API-day ledger is read
# strictly (items 6-7) and damage first seen under the reservation lock keeps its reason (8).
# Principle: when in doubt, NO app fallback.
# --------------------------------------------------------------------------

def _q429_with(**over):
    """Q429's envelope (stderr) with fields replaced."""
    obj = json.loads(Q429[2])
    obj.update(over)
    return obj


_GUARD_FOOTER = (b"gemini-guard: client content is not sent to Gemini while the key tier is "
                 b"unconfirmed (see the gemini-api skill).")

FIX6_UNKNOWN = {
    # item 2: `error` must be an object when present; a `body` key; generation keys at any depth
    "error_array_503": (1, b"", json.dumps(_q429_with(
        error=[{"code": 503, "message": "unavailable"}])).encode()),
    "error_array_429": (1, b"", json.dumps(_q429_with(
        error=[google_err(429, "RESOURCE_EXHAUSTED", QUOTA_MSG)])).encode()),
    "error_string": (1, b"", json.dumps(_q429_with(error="quota exceeded")).encode()),
    "nested_completed_under_body": (1, b"", json.dumps(_q429_with(body=[_COMPLETED])).encode()),
    "body_key_only": (1, b"", json.dumps(_q429_with(body="upstream text")).encode()),
    "nested_completed_in_error_details": (1, b"", json.dumps(_q429_with(error=dict(
        google_err(429, "RESOURCE_EXHAUSTED", QUOTA_MSG),
        details=[{"status": "completed", "id": "x"}]))).encode()),
    "nested_steps_key": (1, b"", json.dumps(_q429_with(error=dict(
        google_err(429, "RESOURCE_EXHAUSTED", QUOTA_MSG), details=[{"steps": []}]))).encode()),
    "nested_object_key": (1, b"", json.dumps(_q429_with(
        hints=[{"object": "interaction"}])).encode()),
    # item 1: NaN / Infinity are not JSON; numeric codes compare as exact ints only
    "nan_constant": (1, b"", json.dumps(_q429_with(extra=float("nan"))).encode()),
    "infinity_constant": (1, b"", json.dumps(_q429_with(extra=float("inf"))).encode()),
    "nested_code_429_00000000000001": (1, b"", Q429[2].replace(
        b'"code": 429,', b'"code": 429.00000000000001,')),
    "nested_code_429_float": _fix1_err(_fix1_env_fields(
        error={"code": 429.0, "message": "x", "status": "RESOURCE_EXHAUSTED"})),
    "nested_code_bool": _fix1_err(_fix1_env_fields(
        error={"code": True, "message": "x", "status": "RESOURCE_EXHAUSTED"})),
    # item 3: the envelope's exit_code must be the child's real exit code (an exact int)
    "exit_code_mismatch": (1, b"", json.dumps(_q429_with(exit_code=0)).encode()),
    "exit_code_float": (1, b"", json.dumps(_q429_with(exit_code=1.0)).encode()),
    "exit_code_bool": (1, b"", json.dumps(_q429_with(exit_code=True)).encode()),
    # item 4: a guard denial counts only as EXACTLY the guard's pre-spawn shape
    "guard_completed_then_denial_line": (9, b"", _COMPLETED_LINE
                                         + b"\ngemini-guard: denied: content\n"),
    "guard_denial_without_footer": (9, b"", b"gemini-guard: denied: a signed link\n"),
    "guard_denial_footer_then_more": (9, b"", b"gemini-guard: denied: a signed link\n"
                                      + _GUARD_FOOTER + b"\nextra\n"),
    "guard_text_before_denial": (9, b"", b"note\ngemini-guard: denied: a signed link\n"
                                 + _GUARD_FOOTER + b"\n"),
}


@pytest.mark.parametrize("case", sorted(FIX6_UNKNOWN))
def test_fix6_doubtful_rejection_evidence_is_outcome_unknown_never_the_app(world, env, capfd,
                                                                           tmp_path, case):
    e = primary_env(env, tmp_path)
    WORLD.api.script = [FIX6_UNKNOWN[case], api_ok(model="gemini-4-carbon")]
    code, st, out, err = run(capfd, tmp_path, e)
    assert code == 6 and st["status"] == "outcome_unknown", st
    assert st["via"] == "api" and st["api_attempt"] == "failed" and st["api_reason"], st
    assert len(WORLD.api.calls) == 1 and _app_untouched()
    recs = log_entries(e)
    assert [r["status"] for r in recs] == ["started", "outcome_unknown"], recs
    assert recs[1]["stop_latch"] is False and _ledger_count(e) == 1


def test_fix6_clean_rejections_and_the_exact_guard_shape_still_classify(world):
    # a string error.code (the live 2026-11-18 shape) and a matching exit_code stay evidence
    live = json.loads(REJECTIONS["429_live_shape_2026_11_18"][2])
    assert gp.api_rejection(live, 1) == "HTTP 429"
    assert gp.api_rejection(json.loads(Q429[2]), 1) == "HTTP 429"
    assert gp.api_rejection(json.loads(Q429[2]), 2) is None  # exit_code 1 vs the child's 2
    no_exit = json.loads(Q429[2])
    del no_exit["exit_code"]
    assert gp.api_rejection(no_exit, 1) == "HTTP 429"  # no exit_code key: nothing to contradict
    assert gp.api_envelope(b'{"error_type": "rate_limit_error", "x": NaN}') is None
    shape = b"gemini-guard: denied: a signed link\n" + _GUARD_FOOTER + b"\n"
    assert gp.guard_denial(9, shape) == "a signed link"
    assert gp.guard_denial(9, shape.replace(b"\n", b"\r\n")) is None
    assert gp.guard_denial(1, shape) is None


@pytest.mark.parametrize("kind", ["missing", "dangling_symlink", "winerror_53"])
def test_fix6_an_explicit_cli_path_that_cannot_be_inspected_refuses_the_launch(
        world, env, capfd, tmp_path, monkeypatch, kind):
    e = primary_env(env, tmp_path)
    target = tmp_path / "explicit-cli.exe"
    e["GEMINIPRO_API_CLI"] = str(target)
    if kind == "dangling_symlink":
        try:
            target.symlink_to(tmp_path / "removed.exe")
        except (OSError, NotImplementedError) as exc:  # no symlink privilege on this host
            pytest.skip("symlinks unavailable: %s" % exc)
        assert os.path.lexists(target) and not os.path.exists(target)
    elif kind == "winerror_53":
        import ctypes
        real = os.stat
        made = getattr(ctypes, "WinError", None)
        boom = made(53) if made else FileNotFoundError(2, "The network path was not found")
        assert isinstance(boom, FileNotFoundError)

        def stat(p, *a, **k):
            if str(p) == str(target):
                raise boom
            return real(p, *a, **k)
        monkeypatch.setattr(gp.os, "stat", stat)
    code, st, out, err = run(capfd, tmp_path, e)
    assert code == 2 and st["status"] == "preflight_refused", st
    assert st["api_attempt"] == "not_run" and "GEMINIPRO_API_CLI" in st["api_reason"], st
    assert WORLD.api.calls == [] and _app_untouched() and log_entries(e) == []
    assert not os.path.exists(_ledger(e))


def test_fix6_only_gemini_api_missing_from_path_is_not_found_and_falls_back(world, env, capfd,
                                                                            tmp_path):
    e = primary_env(env, tmp_path)
    e.pop("GEMINIPRO_API_CLI")
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 0 and st["via"] == "app" and st["api_attempt"] == "not_run", st
    assert "not on PATH" in st["api_reason"] and WORLD.generate_calls == 1


def _history_row():
    return json.dumps({"kind": "api_reservation", "ts": lanew_log._now_iso()}).encode() + b"\n"


@pytest.mark.parametrize("case", ["non_utf8_kind", "blank_row", "valid_pre_marker"])
def test_fix6_ledger_damage_refuses_at_the_ceiling(world, env, capfd, tmp_path, case):
    e = primary_env(env, tmp_path, GEMINIPRO_API_DAY_CEILING="40")
    p = pathlib.Path(_ledger(e))
    p.parent.mkdir(parents=True, exist_ok=True)
    row = _history_row()
    if case == "valid_pre_marker":
        p.write_bytes((row * 39).rstrip(b"\n"))  # a valid last row missing only its newline
        assert lanew_log.reserve(str(p), {}, 40)[:2] == ("reserved", 40)
        data = p.read_bytes().splitlines(keepends=True)
        data[38] = b"{damaged}\n"  # the counted row whose newline was restored
        p.write_bytes(b"".join(data))
    else:
        data = [row] * 40
        data[5] = {"non_utf8_kind": row.replace(b"api_reservation", b"api_reservatio\xff"),
                   "blank_row": b" \n"}[case]
        p.write_bytes(b"".join(data))
    before = p.read_bytes()
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 3 and st["status"] == "log_failure", st
    assert "API-day ledger damaged at line" in st["reason"], st
    assert WORLD.api.calls == [] and _app_untouched() and p.read_bytes() == before


@pytest.mark.parametrize("mode", ["primary", "legacy"])
def test_fix6_damage_first_seen_under_the_reservation_lock_keeps_its_reason(
        world, env, capfd, tmp_path, monkeypatch, mode):
    e = (primary_env if mode == "primary" else api_env)(env, tmp_path)
    if mode == "legacy":
        _harness_down()
    p = pathlib.Path(_ledger(e))
    p.parent.mkdir(parents=True, exist_ok=True)
    row = _history_row()
    p.write_bytes(row * 2)
    orig = gp.Wrapper.api_reserve

    def reserve(self, *a):
        p.write_bytes(b"not json\n" + row)  # damage lands after the precheck read
        return orig(self, *a)

    monkeypatch.setattr(gp.Wrapper, "api_reserve", reserve)
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 3 and st["status"] == "log_failure", st
    assert "API-day ledger damaged at line 1" in st["reason"], st
    assert WORLD.api.calls == [] and WORLD.generate_calls == 0
    recs = log_entries(e)
    assert [r["status"] for r in recs] == ["started", "failed"], recs
    assert recs[1]["stop_latch"] is False and recs[1]["exit"] == 3
    assert lanew_log.check("t1", log_path=e["GEMINIPRO_LOG"], ceiling=12)[0]


# --------------------------------------------------------------------------
# Gemini 4 Neon (2026-11-19): gemini-neon -> gemini-4-neon on the API only, with
# generation_config.thinking_level (GEMINIPRO_NEON_THINKING, default medium); every route that
# would enter the app is exit 4 model_not_available instead, never latching the run
# --------------------------------------------------------------------------

NEON_ARGS = ("t1", "neon", "--model", "gemini-neon")
RELAUNCH = "relaunch with --model gemini-carbon"


def _neon_body(level="medium"):
    return {"input": CLEAN.decode(), "model": "gemini-4-neon", "stream": False, "store": False,
            "generation_config": {"thinking_level": level}}


NEON_SPELLINGS = ("gemini-neon", "gemini-4-neon")


def _neon_refused(st, state, spelling="gemini-neon"):
    """The Neon exit 4: model_not_available, naming the API state, the spelling the launch used
    (never the other one) and the Carbon relaunch."""
    assert st["exit"] == 4 and st["status"] == "model_not_available", st
    assert st["api_attempt"] == state and state in st["reason"], st
    assert RELAUNCH in st["reason"] and _app_untouched(), st
    other, = [s for s in NEON_SPELLINGS if s != spelling]
    assert "%s is API-only" % spelling in st["reason"], st
    assert "%s is API-only" % other not in st["reason"], st


def test_neon_api_models_table(world):
    # DEFAULT_MODEL (gemini-neon since the 2026-11-19 flip) is pinned by test_default_is_neon
    assert gp.API_MODELS == {"gemini-carbon": "gemini-4-carbon", "gemini-neon": "gemini-4-neon",
                             "gemini-4-neon": "gemini-4-neon",
                             "gemini-4-hydrogen": "gemini-4-hydrogen"}


def _neon_api_id_checks(capfd, tmp_path, e, args):
    """The API id spelling gets every Neon rule: the Neon body, then on a proven rejection the
    API-only exit 4 with the Carbon relaunch hint, the harness never called."""
    WORLD.api.script = [api_ok("NEON-391", model="gemini-4-neon")]
    code, st, _, _ = run(capfd, tmp_path, e, args=args)
    assert code == 0 and st["model"] == "gemini-4-neon" and _app_untouched(), st
    body = json.loads(WORLD.api.calls[0]["body_raw"])
    assert body == _neon_body() and list(body) == list(_neon_body()), body
    WORLD.api.script = [cli_error(1, 404, "not_found", None, "models/gemini-4-neon not found",
                                  google_err(404, "NOT_FOUND", "models/gemini-4-neon not found"))]
    code, st, _, _ = run(capfd, tmp_path, e, args=args)
    _neon_refused(st, "failed", "gemini-4-neon")
    assert WORLD.harness_calls == 0 and log_entries(e)[-1]["stop_latch"] is False


@pytest.mark.parametrize("spelling", ["gemini-4-neon", " GEMINI-4-Neon "])
def test_neon_api_id_is_neon(world, env, capfd, tmp_path, spelling):
    e = primary_env(env, tmp_path)
    _neon_api_id_checks(capfd, tmp_path, e, ("t1", "neon", "--model", spelling))


def test_neon_api_id_env(world, env, capfd, tmp_path):
    e = primary_env(env, tmp_path, GEMINIPRO_MODEL="GEMINI-4-NEON")
    _neon_api_id_checks(capfd, tmp_path, e, ("t1", "neon"))


def test_neon_bare_name_stays_unmapped(world, env, capfd, tmp_path):
    assert "neon" not in gp.API_MODELS  # not a documented name: no Neon rules, no API id


@pytest.mark.parametrize("api_model", ["gemini-4-neon", "gemini-neon", " Gemini-4-NEON "])
def test_legacy_backup_never_neon(world, env, capfd, tmp_path, api_model):
    e = api_env(env, tmp_path, GEMINIPRO_API_MODEL=api_model)  # GEMINIPRO_API_PRIMARY=0
    _harness_down()  # the app path would end exit 2 and hand over to the backup
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 64 and st["status"] == "usage_error", st
    assert "GEMINIPRO_API_MODEL" in st["reason"] and api_model.strip() not in st["reason"], st
    assert WORLD.api.calls == [] and _app_untouched() and log_entries(e) == []
    assert not os.path.exists(_ledger(e)) and _api_dirs(e) == []


def test_legacy_backup_refusal_is_legacy_only(world, env, capfd, tmp_path):
    # API primary ignores GEMINIPRO_API_MODEL (it uses API_MODELS): a Carbon launch still answers
    e = primary_env(env, tmp_path, GEMINIPRO_API_MODEL="gemini-4-neon")
    WORLD.api.script = [api_ok(model="gemini-4-carbon")]
    code, st, _, _ = run(capfd, tmp_path, e, args=("t1", "c", "--model", "gemini-carbon"))
    assert code == 0 and st["model"] == "gemini-4-carbon", st


@pytest.mark.parametrize("spelling", ["gemini-neon", "Gemini-Neon"])
def test_neon_body(world, env, capfd, tmp_path, spelling):
    e = primary_env(env, tmp_path)
    WORLD.api.script = [api_ok("NEON-391", model="gemini-4-neon")]
    code, st, _, _ = run(capfd, tmp_path, e, args=("t1", "neon", "--model", spelling))
    assert code == 0, st
    (c,) = WORLD.api.calls
    body = json.loads(c["body_raw"])
    assert body == _neon_body() and list(body) == list(_neon_body()), body


def test_neon_answer(world, env, capfd, tmp_path):
    e = primary_env(env, tmp_path)
    WORLD.api.script = [api_ok("NEON-391", model="gemini-4-neon")]
    code, st, out, _ = run(capfd, tmp_path, e, args=NEON_ARGS, json_mode=False)
    assert code == 0 and st["status"] == "ok" and st["via"] == "api", st
    assert st["model"] == "gemini-4-neon" and st["requested_model"] == "gemini-neon", st
    assert st["api_attempt"] == "ok" and st["model_mismatch"] is False, st
    assert out.strip() == "NEON-391" and _app_untouched()
    assert WORLD.api.calls[0]["argv"][-1] == "--no-retries"
    recs = log_entries(e)
    assert [r["status"] for r in recs] == ["started", "ok"] and recs[0]["model"] == "gemini-4-neon"
    assert _ledger_count(e) == 1


@pytest.mark.parametrize("raw,level", [("XHigh", "xhigh"), ("low", "low"), (" HIGH ", "high"),
                                       ("", "medium")])
def test_neon_thinking_env(world, env, capfd, tmp_path, raw, level):
    e = primary_env(env, tmp_path, GEMINIPRO_NEON_THINKING=raw)
    WORLD.api.script = [api_ok(model="gemini-4-neon")]
    code, st, _, _ = run(capfd, tmp_path, e, args=NEON_ARGS)
    assert code == 0, st
    assert json.loads(WORLD.api.calls[0]["body_raw"])["generation_config"] == {
        "thinking_level": level}


def test_neon_thinking_env_invalid_is_a_usage_error_before_admission(world, env, capfd,
                                                                     tmp_path):
    e = primary_env(env, tmp_path, GEMINIPRO_NEON_THINKING="turbo")
    code, st, _, _ = run(capfd, tmp_path, e, args=NEON_ARGS)
    assert code == 64 and st["status"] == "usage_error", st
    assert "GEMINIPRO_NEON_THINKING" in st["reason"], st
    assert WORLD.api.calls == [] and _app_untouched() and log_entries(e) == []
    assert not os.path.exists(_ledger(e)) and _api_dirs(e) == []


def test_neon_thinking_env_never_changes_a_carbon_launch(world, env, capfd, tmp_path):
    e = primary_env(env, tmp_path, GEMINIPRO_NEON_THINKING="turbo")
    WORLD.api.script = [api_ok(model="gemini-4-carbon")]
    code, st, _, _ = run(capfd, tmp_path, e, args=("t1", "c", "--model", "gemini-carbon"))
    assert code == 0 and st["model"] == "gemini-4-carbon", st
    assert "generation_config" not in json.loads(WORLD.api.calls[0]["body_raw"])


def test_carbon_body_unchanged(world, env, capfd, tmp_path):
    e = primary_env(env, tmp_path)
    WORLD.api.script = [api_ok(model="gemini-4-carbon")]
    code, st, _, _ = run(capfd, tmp_path, e, args=("t1", "c", "--model", "gemini-carbon"))
    assert code == 0, st
    assert WORLD.api.calls[0]["body_raw"] == json.dumps(
        {"input": CLEAN.decode(), "model": "gemini-4-carbon", "stream": False, "store": False},
        ensure_ascii=False).encode("utf-8")


def test_neon_rejection_no_app(world, env, capfd, tmp_path):
    e = primary_env(env, tmp_path)
    long_msg = "models/gemini-4-neon is not found for API version v1beta. " * 12  # > 300 chars
    WORLD.api.script = [cli_error(1, 404, "not_found", None, long_msg,
                                  google_err(404, "NOT_FOUND", long_msg))]
    code, st, _, _ = run(capfd, tmp_path, e, args=NEON_ARGS)
    _neon_refused(st, "failed")
    assert len(WORLD.api.calls) == 1 and "HTTP 404" in st["reason"], st
    recs = log_entries(e)
    assert [r["status"] for r in recs] == ["started", "failed"], recs
    assert recs[1]["stop_latch"] is False
    # never latched: the lead's Carbon relaunch under the same run is admitted and answers
    WORLD.api.script = [api_ok("CARBON-391", model="gemini-4-carbon")]
    code, st, _, _ = run(capfd, tmp_path, e, args=("t1", "neon", "--model", "gemini-carbon"))
    assert code == 0 and st["via"] == "api" and st["model"] == "gemini-4-carbon", st
    assert [r["status"] for r in log_entries(e)] == ["started", "failed", "started", "ok"]


def test_neon_ceiling_no_app(world, env, capfd, tmp_path):
    e = primary_env(env, tmp_path, GEMINIPRO_API_DAY_CEILING="2")
    _reserve_today(e, 2)
    code, st, _, _ = run(capfd, tmp_path, e, args=NEON_ARGS)
    _neon_refused(st, "skipped")
    assert "2/2" in st["reason"] and WORLD.api.calls == [] and log_entries(e) == []


def test_neon_api_switched_off_no_app(world, env, capfd, tmp_path):
    e = primary_env(env, tmp_path, GEMINIPRO_API_DAY_CEILING="0")
    code, st, _, _ = run(capfd, tmp_path, e, args=NEON_ARGS)
    _neon_refused(st, "skipped")
    assert "GEMINIPRO_API_DAY_CEILING=0" in st["reason"] and WORLD.api.calls == []


def test_neon_reservation_refused_after_admission_no_app(world, env, capfd, tmp_path,
                                                         monkeypatch):
    monkeypatch.setattr(gp.lanew_log, "reserve", lambda *a, **k: ("refused", 40, 0))
    e = primary_env(env, tmp_path)
    code, st, _, _ = run(capfd, tmp_path, e, args=NEON_ARGS)
    _neon_refused(st, "skipped")
    assert WORLD.api.calls == []
    recs = log_entries(e)
    assert [r["status"] for r in recs] == ["started", "failed"] and recs[1]["stop_latch"] is False


def test_neon_cli_gone_at_spawn_no_app(world, env, capfd, tmp_path):
    e = primary_env(env, tmp_path)
    WORLD.api.script = [gp._mark_unspawned(FileNotFoundError(2, "The system cannot find the file"))]
    code, st, _, _ = run(capfd, tmp_path, e, args=NEON_ARGS)
    _neon_refused(st, "not_run")
    recs = log_entries(e)
    assert [r["status"] for r in recs] == ["started", "failed"] and recs[1]["stop_latch"] is False


def test_neon_missing_key(world, env, capfd, tmp_path):
    e = primary_env(env, tmp_path)
    e.pop("GEMINI_API_KEY")
    code, st, _, _ = run(capfd, tmp_path, e, args=NEON_ARGS)
    _neon_refused(st, "not_run")
    assert "GEMINI_API_KEY" in st["reason"] and log_entries(e) == []


def test_neon_cli_not_found(world, env, capfd, tmp_path):
    e = primary_env(env, tmp_path)
    e.pop("GEMINIPRO_API_CLI")  # gemini-api not on PATH (an explicit missing path is exit 2)
    code, st, _, _ = run(capfd, tmp_path, e, args=NEON_ARGS)
    _neon_refused(st, "not_run")
    assert "not on PATH" in st["reason"] and log_entries(e) == []


def test_neon_no_account_still_exit_4_not_the_account_refusal(world, env, capfd, tmp_path):
    e = primary_env(env, tmp_path, GEMINIPRO_ACCOUNT="", GEMINIPRO_API_DAY_CEILING="0")
    code, st, _, _ = run(capfd, tmp_path, e, args=NEON_ARGS)
    _neon_refused(st, "skipped")


@pytest.mark.parametrize("case", ["http_503", "timeout"])
def test_neon_outcome_unknown(world, env, capfd, tmp_path, case):
    e = primary_env(env, tmp_path)
    WORLD.api.script = [SERVER[503] if case == "http_503" else
                        subprocess.TimeoutExpired(["gemini-api"], 5)]
    code, st, _, _ = run(capfd, tmp_path, e, args=NEON_ARGS)
    assert code == 6 and st["status"] == "outcome_unknown" and code != 4, st
    assert RELAUNCH not in st["reason"] and _app_untouched() and len(WORLD.api.calls) == 1


def test_neon_guard_denial_and_local_fault_keep_their_exits(world, env, capfd, tmp_path):
    e = primary_env(env, tmp_path)
    WORLD.api.script = [(9, b"", b"gemini-guard: denied: a signed link\n" + _GUARD_FOOTER + b"\n")]
    code, st, _, _ = run(capfd, tmp_path, e, args=NEON_ARGS)
    assert code == 7 and st["status"] == "brief_refused" and _app_untouched(), st
    e2 = primary_env(env, tmp_path, GEMINIPRO_API_CLI=str(tmp_path / "no-such-cli.exe"))
    code, st, _, _ = run(capfd, tmp_path, e2, args=("t2", "neon", "--model", "gemini-neon"))
    assert code == 2 and st["status"] == "preflight_refused" and _app_untouched(), st


@pytest.mark.parametrize("model,spelling", [("gemini-neon", "gemini-neon"),
                                            (" GEMINI-4-Neon ", "gemini-4-neon")])
def test_neon_legacy_mode(world, env, capfd, tmp_path, model, spelling):
    e = api_env(env, tmp_path)  # GEMINIPRO_API_PRIMARY=0: the app-first order
    code, st, _, _ = run(capfd, tmp_path, e, args=("t1", "neon", "--model", model))
    assert code == 4 and st["status"] == "model_not_available", st
    assert RELAUNCH in st["reason"] and "GEMINIPRO_API_PRIMARY=0" in st["reason"], st
    other, = [s for s in NEON_SPELLINGS if s != spelling]
    assert "%s is API-only" % spelling in st["reason"], st
    assert "%s is API-only" % other not in st["reason"], st
    assert _app_untouched() and WORLD.api.calls == [] and log_entries(e) == []


def test_default_flip_ready(world, env, capfd, tmp_path, monkeypatch):
    monkeypatch.setattr(gp, "DEFAULT_MODEL", "gemini-neon")
    e = primary_env(env, tmp_path)
    e.pop("GEMINIPRO_MODEL")
    WORLD.api.script = [api_ok(model="gemini-4-neon")]
    code, st, _, _ = run(capfd, tmp_path, e)  # no --model, no GEMINIPRO_MODEL
    assert code == 0 and st["model"] == "gemini-4-neon", st
    assert json.loads(WORLD.api.calls[0]["body_raw"]) == _neon_body()
    capfd.readouterr()
    assert gp.main(["--status", "--json"], e) == 0  # --status still works after the flip


def test_default_is_neon(world, env, capfd, tmp_path):
    # the release flip (2026-11-19): no --model and no GEMINIPRO_MODEL sends the Neon body
    e = primary_env(env, tmp_path)
    e.pop("GEMINIPRO_MODEL")
    WORLD.api.script = [api_ok(model="gemini-4-neon")]
    code, st, _, _ = run(capfd, tmp_path, e)
    assert code == 0 and st["model"] == "gemini-4-neon", st
    assert st["requested_model"] == "gemini-neon", st
    body = json.loads(WORLD.api.calls[0]["body_raw"])
    assert body == _neon_body() and list(body) == list(_neon_body()), body
