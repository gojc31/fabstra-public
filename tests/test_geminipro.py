"""Offline tests for scripts/geminipro.py - fakes only: no network, no Chrome.

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
        return [2, [[512, 0.1, 1, [[1893456000]]], [4096, 0.2, 2, [[1893456000]]]], False]
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
    monkeypatch.setattr(gp.shutil, "which", lambda *a, **k: "C:/fake/browser-harness.exe")
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
    cp = tmp_path / "cliproxy"
    return {"PATH": os.environ.get("PATH", ""), "CLIPROXY_DIR": str(cp),
            "GEMINIPRO_LOG": str(cp / "geminipro-usage.jsonl"), "GEMINIPRO_TOTAL_DEADLINE": "120",
            "GEMINIPRO_SLOT_WAIT": "0", "GEMINIPRO_ACCOUNT": RIGHT}


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


def test_daily_cap_counts_all_runs(world, env, capfd, tmp_path):
    e = dict(env, GEMINIPRO_DAILY_CAP="2")
    assert run(capfd, tmp_path, e, args=("r1", "a"))[0] == 0
    assert run(capfd, tmp_path, e, args=("r2", "b"))[0] == 0
    before = open(env["GEMINIPRO_LOG"], "rb").read()
    code, st, _, _ = run(capfd, tmp_path, e, args=("r3", "c"))
    assert code == 1 and "daily cap" in st["reason"]
    assert open(env["GEMINIPRO_LOG"], "rb").read() == before


def test_cap_defaults(world, env):
    assert "GEMINIPRO_DAILY_CAP" not in env and "GEMINIPRO_RUN_JOB_CEILING" not in env
    w = gp.Wrapper(["t1", "carbon", "--json"], dict(env))
    w.config()
    assert w.daily_cap == 80 and w.ceiling == 12


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
