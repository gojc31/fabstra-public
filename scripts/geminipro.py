"""geminipro - send ONE brief to the consumer Gemini web app (gemini.google.com) on
the configured Google AI Pro account (GEMINIPRO_ACCOUNT, else EXPECTED_ACCOUNT below)
through the gemini_webapi library; the answer goes to stdout and to a report file.
A consult seat like astrapro, for Gemini (default model gemini-carbon).

Usage: geminipro <run> <name> [--model <m>] [--json] [--brief-file <path>] < brief.md
       geminipro --status [--json]
(bin/geminipro and bin/geminipro.cmd are thin shims that run this file with the
geminipro-lab venv interpreter, overridable by GEMINIPRO_PYTHON.)

The brief must carry a line `brief-check: clean - <why it is clean>`, be valid
UTF-8 of at most 20,000 characters (a leading BOM is stripped) and pass the
jev_privacy secret scan (astrapro's gate). Only the brief leaves the machine: one
fresh single-turn temporary chat, no files, no Gem, no tools, no history reuse.

Exit codes:
  0    ok
  1    logger refused (cap reached)
  2    preflight refused (no account configured, browser-harness / Chrome unreachable, no
       context with Google cookies)
  3    logging failure
  4    model not available
  5    no free slot within the wait / deadline
  6    the request ran and did not end ok (Gemini error, empty answer, blocked, quota)
  7    brief gate
  8    account mismatch
  64   usage error (run/name must match [A-Za-z0-9._-]{1,80}; a run/name argument holding the
       GEMINI_API_KEY value, in any mode, or a job-mode CLIPROXY_DIR or GEMINIPRO_LOG holding
       it - the value is never echoed, nothing is read, admitted or written)
  130  interrupted
Every exit path emits one JSON status line (keys tool, exit, status, reason, run,
name, model, job_id, report, account_ok, duration_s, submissions, context, via; --status
adds account, tier, models, credits_5h, credits_weekly, abuse; the API backup trigger
adds backup, primary_exit, primary_reason, requested_model - see "API backup"). Default: the
answer (or the --status summary) on stdout, the status line on stderr. --json
(honoured on every exit, usage errors included): stdout carries only the status
line. Steps log to stderr. The status line is written in its own step: a failed
or interrupted answer / summary write never costs it. An answer in hand is never
dropped: once Gemini's own completion marker was seen, a later stream error,
deadline, close failure, interrupt or report failure still records the job ok
and prints the answer (exit 0, or 3 when the report or terminal record could
not be confirmed; stdout, stderr under --json). Partial chunks are never taken.

Env: GEMINIPRO_ACCOUNT (the Google account the signed-in Gemini session must be; when
  unset, EXPECTED_ACCOUNT below. Surrounding whitespace is stripped; an empty or
  whitespace-only value - set, or the default - is exit 2 preflight_refused before
  any browser, cookie or network step, and a set value never falls back to the default),
  GEMINIPRO_MODEL (default gemini-carbon; --model wins), GEMINIPRO_RUN_JOB_CEILING
  (default 12), GEMINIPRO_DAILY_CAP (default 80 admitted jobs per local calendar day,
  all runs), GEMINIPRO_TOTAL_DEADLINE (s, default 900: one monotonic deadline over
  stdin, slot wait, harness, network, checked again inside the transport guard just
  before the prompt POST - expired there: exit 5, nothing sent; finalization gets
  BACKSTOP_GRACE = 60 s more, then a hard exit), GEMINIPRO_SLOT_WAIT (s, default 300), GEMINIPRO_LOG (default
  ~/.cli-proxy-api/geminipro-usage.jsonl), CLIPROXY_DIR (default ~/.cli-proxy-api:
  geminipro-out/ reports and the geminipro.d/ state dir live under it).
  API backup: GEMINIPRO_API_BACKUP (`0` turns it off; default on), GEMINI_API_KEY (read by
  the gemini-api CLI itself; 16+ characters, else not a key), GEMINIPRO_API_CLI (an explicit
  CLI path; default `gemini-api` on PATH), GEMINIPRO_API_MODEL (default gemini-4-hydrogen),
  GEMINIPRO_API_TIMEOUT (s per attempt, default 300; a non-number is exit 64).
Test-only, honoured ONLY with GEMINIPRO_TEST=1 (exit 2 otherwise):
  GEMINIPRO_EXPECT_ACCOUNT (replaces the expected account for the identity check;
  GEMINIPRO_ACCOUNT must still resolve non-empty), GEMINIPRO_TEST_CONTEXT
  (only browser contexts whose id starts with this are tried; "default" names the
  default jar).

Design (T1, 2026-11-13; fix round 1 the same day):
- Cookies: read at call time by a browser-harness child (BH_REQUIRE_EXISTING_DAEMON=1,
  telemetry/update check/recording off) that never opens, switches, navigates or
  activates a tab: per Chrome profile (CDP browser context) it attaches a CDP
  session to a frame-backed NON-tab target of that profile (browser_ui, then an
  extension background_page), calls Network.getCookies for the Gemini URL and
  detaches; the default jar is read explicitly with Storage.getCookies (no context
  id) on a browser-target session, labelled with defaultBrowserContextId only when
  Chrome reports one. Values come back over the child's stdout pipe, are held in
  memory only and are scrubbed from every string this wrapper emits; the child's
  stderr is never echoed.
- Secrets: every cookie value of 16+ characters the HTTP session ever holds
  (supplied, or set by any response: bootstrap, RPCs, stream) is registered at the
  transport boundary before anything is formatted, with its backslash / JSON
  escaped spellings (the library wraps stream errors with repr()); shorter values
  are not secrets (Google's auth cookies are long). Each string leaf is scrubbed
  exactly once before JSON serialization (the serialized line is never scrubbed);
  the answer is held raw and scrubbed once per sink; exceptions are formatted as
  type name + scrubbed str(), never repr().
- Identity: the gemini.google.com/app page fetched by the SAME HTTP session that
  will send must carry exactly one `"oPEP7c":"<email>"` field equal to the
  expected account (fail closed on missing / multiple / ambiguous), the init must
  come from the supplied cookies ("Base Cookies", no guest or preflight fallback)
  with an access token, before any RPC. Any transport error on that GET is a plain
  preflight error (exit 2, no other context, no library fallback request). Then
  GetUserStatus must be positively parsed from EVERY part the server sent (counted
  before the library's early-returning consumer sees them): exactly one part,
  field 14 null (Google's live AVAILABLE shape) or 1000, and a non-empty model
  registry. A part naming another status exits by that status (UNAUTHENTICATED or
  reject code 7: exit 8; others: exit 2); a missing, extra or malformed part is exit 2.
  The proven browserContextId (not a secret) is kept in geminipro.d/last-context
  and tried first next time; other contexts are scanned only if it fails (never
  written under GEMINIPRO_TEST=1, nor - the memory is simply not updated - when the
  context id or the state dir path contains the GEMINI_API_KEY value, in either mode).
- Blocks: a challenge page, HTTP 403 or 429 at ANY stage (bootstrap GET, init RPCs,
  generate) ends the whole run - no other context is tried: exit 6, "no brief
  submitted" before dispatch, outcome_unknown after. No request follows redirects
  (allow_redirects=False on every call); a redirect is a block, never followed or
  forwarded.
- Library hardening (process-local patches of the bindings each module imported;
  gemini_webapi must be exactly 2.1.1, else exit 2): save_cookies /
  clear_cookies_cache are no-ops, rotate_1psidts refuses, the cookie cache path
  resolves to nothing and local-browser cookie loading returns nothing, so the
  cache is neither read nor written; library logging is disabled.
- One submission: the generate stream is called without the library's retry
  decorator; a transport guard counts POSTs to the generate endpoint and refuses a
  second one, refuses rotate / upload URLs, and init is refused once identity is
  proven (no re-init on an unverified session). No RPC runs after dispatch on the
  job path (the library's post-answer usage refresh is skipped). Any error after
  dispatch is exit 6 outcome_unknown unless Gemini's own stream error code shows
  the request was refused.
- Caps: one job at once (OS lock geminipro.d/job.lock), the per-run ceiling via
  lanew_log.admit on geminipro's own log, a daily cap counted from that log. The
  terminal record is written here (lanew_log.record_end classifies Codex
  transcripts) with status ok / failed / outcome_unknown and Codex fields null.

API backup (2026-11-15). When the app path cannot run for a Chrome or account reason, the
same gate-passed brief goes ONCE to the Gemini API through the `gemini-api` CLI (on this
machine a guard wrapper; never the HTTP API directly). It is never the primary path.
- Trigger: job mode only (never --status). An exit 2 (preflight_refused) or 8
  (account_mismatch) raised after the brief gate, the slot and the precheck passed and
  before admission (no job_id, 0 submissions, no answer held): harden(), candidates(),
  open_verified(). Exits from argument parsing / config (no account configured, a
  test-only variable without GEMINIPRO_TEST=1) and every other code (1, 3, 4, 5, 6, 7, 64,
  130) never trigger.
- Preconditions, in order (a miss = "not run"): GEMINIPRO_API_BACKUP is not 0;
  GEMINI_API_KEY is non-blank and 16+ characters; GEMINIPRO_API_MODEL does not contain the
  key ("GEMINIPRO_API_MODEL contains the API key"); the CLI resolves (GEMINIPRO_API_CLI, else
  gemini-api on PATH) and its path does not contain the key ("the CLI path contains the API
  key"); JOB_MIN seconds remain; the brief does not contain the key (such a brief is never
  written to a body file or sent, and not silently scrubbed). Not run: the original exit
  code and status, reason + "; API backup not run: <why>", nothing admitted or logged, no
  report, the CLI never started. Metadata carrying the key is refused, never scrubbed into a
  file or argv - one check (key_in) at every persistence and process boundary: run/name, and
  in job mode CLIPROXY_DIR and GEMINIPRO_LOG (the report, state, lock, log and log-lock paths
  all derive from them), are exit 64 (see the exit codes); a string of the usage record (run,
  name, model - on the app path a name from the app's registry -, report path, log path) is
  exit 3 log_failure, nothing admitted; a context id or a state dir holding it is never
  remembered; a browser-harness path holding the key is exit 2 preflight_refused before the
  harness child starts (in job mode that is the backup trigger); the requested --model only
  reaches the scrubbed status line. Report text is scrubbed field by field; the body file
  holds only the checked brief and API model.
- Call: admit() first (same per-run ceiling and daily cap; the record's model is the API
  model), then body.json - {"input": <brief>, "model": <API model>, "stream": false,
  "store": false}, UTF-8 JSON - in a new empty directory under geminipro.d/, and
  `<cli> generate --output-format json --body @body.json` with no shell, stdin DEVNULL,
  cwd that directory, the environment inherited (the CLI reads the key; the key is never
  in argv or the body). Never --stdin or @- (the guard refuses them). The directory is
  removed on every path. The --model / GEMINIPRO_MODEL choice is ignored on this path.
- Timing: per attempt min(GEMINIPRO_API_TIMEOUT, time left - API_MARGIN); at most 2
  attempts, the 2nd only after a non-zero exit whose stderr JSON says error_type
  server_error or error.code service_unavailable, after API_RETRY_PAUSE, while JOB_MIN
  seconds remain. A timed-out or interrupted child is killed with its children, never by
  taskkill: on Windows one process snapshot while the child is still alive gives its
  verified descendants (below), then the child is killed through its own handle, then each
  verified descendant through its own (POSIX: the process group, then the child); the child
  is killed again in a finally - even when the descendant step is interrupted or fails -
  and, if that step did not finish, the verified tree step runs on the dead child. With the
  child's creation time unknown only the child itself is killed. Every
  path out of the CLI call (return, timeout, interrupt, cancellation, any exception) kills a
  child still running; the child stays tracked until it is confirmed dead, and finish()
  kills one still tracked (with its verified descendants). The verified tree step: the
  child's creation time is recorded at start while it is alive; a process counts as a
  descendant only when its recorded parent is the child (or a verified descendant) and it
  was created at or after that parent - from one process snapshot that carries parent ids
  and creation times; a process whose creation time cannot be read is never killed, and each
  kill goes through the process's own handle after its creation time is re-checked (never
  by pid alone). The backstop, before its hard exit, kills a live child synchronously
  (proc.kill() first), then runs the verified tree step, waiting KILL_WAIT = 12 s for it (the
  kill step is bounded by about 12 s), and only then removes the body directory.
- Answer: stdout is one JSON object with status "completed"; the answer is the text items
  of the model_output steps in order (thought steps ignored), then the usual hold()
  validation - the answer is held BEFORE any interruptible cleanup, so an interrupt, a
  deadline or an error while the body directory is removed keeps it (report written,
  terminal ok, answer printed). Housekeeping never changes the result: whatever a cleanup
  step raises (an interrupt included) - the body-directory removal on the success, failure
  and not-run paths, finish()'s retry of it, its reap of a tracked child, its no-cache
  existence check and removal and its library-spy log line, the backstop's kill step - is
  contained, and the original exit code, status and reason (with its suffix)
  stand. A removal that failed or was interrupted is tried once more on the way out; a
  directory that still exists after that is the status-line note "the API body directory
  could not be removed" (no note when the retry removed it). Success: report written
  (account line "n/a (API key)", plus
  "- via: api (backup; app path exit <2|8>)"), terminal record ok with via "api" and
  primary_exit, exit 0.
- Failure after admission (non-zero exit - the guard's 9 and the CLI's auth exit 3
  included -, timeout, unexpected stdout, status not completed, empty or error-card
  answer): terminal record failed with via "api", primary_exit and stop_latch false (an
  API failure never latches the run); the ORIGINAL exit code (2 or 8) and status; reason +
  "; API backup failed: <scrubbed text, at most 300 characters>". The child's stdout and
  stderr are never echoed raw.
- Backup terminal records never carry a latch. The policy is chosen before admission (via
  "api", backup "failed", the API model are set before admit() is called). Once admit() has
  handed the wrapper a job id, every terminal record of that job is unlatched whatever ends
  it - success, failure, timeout, interrupt, cancellation, any exception, the backstop - and
  the status line says via "api". The job id is taken from the entry lanew_log.admit returns
  in the very next statement. When admission ends without a job id (refused, failed, or
  interrupted) via returns to "app", backup to "not_run", model and report to the app path's;
  a refusal or an admission error is the original exit (2 or 8) with "; API backup not run:
  admission refused (...)" / "admission failed (...)", an interrupt stays exit 130. The
  wrapper never searches the log for a record to adopt and never writes a terminal record
  for a job id it was not handed. With a job id, an interrupt stays exit 130; the backstop
  with no answer held exits with the ORIGINAL code (2 or 8) and status, reason + "; API
  backup failed: hard backstop: ..."; with an answer held it keeps the kept-answer exit. No
  new exit code.
- Known limit (accepted): inside admission - from the call into lanew_log.admit until the
  wrapper holds the job id - the wrapper fails closed exactly like the app path. If an
  interrupt, or an error in lanew_log's verification read, lands just after lanew_log wrote
  the started record, that record stays without a terminal record. Nothing was sent (the CLI
  had not started). The effect: once this process has ended, later launches of that run are
  refused as "usage unknown" until the log is looked at by hand.
- Status line: `via` is "app" or "api" ("api" from the start of the API admission, back to
  "app" when it ends with no job id) on every exit. Only when the trigger fired: `backup` ok |
  failed | not_run, `primary_exit` 2 | 8,
  `primary_reason` (the app path's reason), `requested_model` (the model asked for). On
  an API run `model` is the API model, `context` null, `account_ok` as the app path left
  it (false after exit 8, else null); `submissions` counts app-path POSTs only (0).
- Secrets: a GEMINI_API_KEY of 16+ characters is registered with remember_secret() when
  the wrapper starts - before argument parsing and any output, in every mode - so any
  text carrying it (a usage error, an app answer, a reason, CLI output) is scrubbed like
  the cookie values; a shorter value is never registered and never used.
"""
import asyncio
import contextlib
import datetime as _dt
import io
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import traceback

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

TOOL = "geminipro"
USAGE = ("usage: geminipro <run> <name> [--model <m>] [--json] [--brief-file <path>] < brief.md"
         " | geminipro --status [--json]")
EXPECTED_ACCOUNT = ""  # default when GEMINIPRO_ACCOUNT is unset; "" refuses (exit 2)
DEFAULT_MODEL = "gemini-carbon"
LIB_VERSION = "2.1.1"  # the hardening patches are keyed on this release's private names
NAME_RE = re.compile(r"[A-Za-z0-9._-]{1,80}")
ATTEST_RE = re.compile(r"(?m)^brief-check: clean - (\S[^\r\n]*)")
MAX_BRIEF = 20000
GEMINI_APP_URL = "https://gemini.google.com/app"
TELEMETRY_DISABLE_ENVS = ("BH_TELEMETRY", "BROWSER_HARNESS_TELEMETRY", "ANONYMIZED_TELEMETRY")
TEST_ONLY = ("GEMINIPRO_EXPECT_ACCOUNT", "GEMINIPRO_TEST_CONTEXT")
ACCOUNT_ENV = "GEMINIPRO_ACCOUNT"
HARNESS_TIMEOUT = 90
INIT_TIMEOUT = 300
CLOSE_TIMEOUT = 10    # a client close never holds the run longer than this
JOB_MIN = 60          # less than this left for the request -> exit 5 "deadline"
BACKSTOP_GRACE = 60   # hard exit this long past the total deadline
SECRET_MIN = 16      # shortest cookie value registered as a secret (live: shortest 72 chars)
STALE_RE = re.compile(r"session with given id not found|no session with given id", re.IGNORECASE)
MEMORY_FILE = "last-context"
MEMORY_RE = re.compile(r"[A-Za-z0-9._:-]{1,128}")
OEPEP_RE = re.compile(r'"oPEP7c"\s*:\s*"((?:[^"\\]|\\.)*)"')
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ERROR_CARD_RE = re.compile(
    r"^\s*(something went wrong|sorry, something went wrong|an internal error has occurred"
    r"|i'?m having a hard time fulfilling your request|there was a problem)", re.IGNORECASE)
# Google's interstitials: the /sorry/ unusual-traffic page, reCAPTCHA, "verify it's you".
# Only consulted on pages that lack the app's bootstrap values or RPC framing.
CHALLENGE_RE = re.compile(
    r"unusual traffic|not a robot|/sorry/|captcha|verify (?:that )?you(?:'|&#39;|’| a)re "
    r"(?:a )?human|verify it(?:'|&#39;|’)?s you", re.IGNORECASE)

# the API backup (module docstring, "API backup")
API_CLI_NAME = "gemini-api"   # resolved on PATH (may be a guard wrapper) unless GEMINIPRO_API_CLI is set
API_MODEL = "gemini-4-hydrogen"
API_TIMEOUT = 300     # per-attempt timeout default (s), GEMINIPRO_API_TIMEOUT
API_MARGIN = 10       # seconds kept back from the total deadline for an attempt's timeout
API_RETRY_PAUSE = 5   # pause before the one retry after a server error; tests set 0
API_REASON_MAX = 300  # longest API failure text in a reason (scrubbed first)
API_BODY = "body.json"
KILL_WAIT = 12        # the backstop waits this long for its verified tree step; the whole kill
#                       step - direct kill + tree step - is bounded by about 12 s (<= 15)

HARD_EXIT = os._exit  # the backstop's exit; tests replace it
_ABSENT = object()    # "no such field" (distinct from a JSON null)


# --------------------------------------------------------------------------
# exits, secrets, logging
# --------------------------------------------------------------------------

class Exit(Exception):
    """Ends the run with one exit code, status and reason (the JSON line)."""

    def __init__(self, code, status, reason):
        super().__init__(reason)
        self.code, self.status, self.reason = code, status, reason


class PolicyAbort(BaseException):
    """A refused library action (second submission, re-init, rotation, upload).
    BaseException so no library `except Exception` can turn it into a retry."""


class Blocked(PolicyAbort):
    """A challenge page, HTTP 403 / 429 or a redirect from Google: the whole run ends
    (exit 6), no other context is tried, nothing is retried or followed."""


class DeadlineAbort(PolicyAbort):
    """The total deadline passed before the prompt POST: refused inside the transport
    guard (exit 5, nothing sent)."""


class AccountMismatch(Exception):
    def __init__(self, seen, why):
        super().__init__(why)
        self.seen, self.why = seen, why


class NoEvidence(AccountMismatch):
    def __init__(self, why):
        super().__init__(None, why)


class BootstrapError(Exception):
    """A transport failure on the Gemini app page GET. Deliberately neither an HTTPError
    (the library would swallow it and open its google.com preflight / guest fallback)
    nor an AccountMismatch (the next context would be tried): exit 2."""


_SECRETS = set()


def remember_secret(value):
    """Register a cookie value of SECRET_MIN+ chars, with the spellings a repr() or JSON
    encoding of it takes (backslash, quote, control-character escapes)."""
    if not (isinstance(value, str) and len(value) >= SECRET_MIN):
        return
    _SECRETS.add(value)
    escaped = value.encode("unicode_escape").decode("ascii")
    _SECRETS.update((escaped, escaped.replace("'", "\\'"), json.dumps(value)[1:-1]))


def remember_jar(cookies):
    """Register every value in a curl_cffi cookie jar (or anything iterable of cookies)."""
    if cookies is None:
        return
    try:
        for c in list(getattr(cookies, "jar", cookies)):
            remember_secret(getattr(c, "value", None))
    except Exception:  # registration is best effort; the scrub still covers what is known
        pass


def scrub(text):
    """Remove every cookie value this process holds from text (longest first)."""
    if not isinstance(text, str):
        text = str(text)
    for v in sorted(_SECRETS, key=len, reverse=True):
        if v in text:
            text = text.replace(v, "[redacted]")
    return text


def fmt_exc(exc):
    """An exception for a message: type name + scrubbed str(), never repr()."""
    try:
        text = str(exc)
    except Exception:
        text = "<unprintable>"
    return "%s: %s" % (type(exc).__name__, scrub(text))


def _frames(exc):
    """Where an exception came from (file:line in function), without any message text."""
    with contextlib.suppress(Exception):
        tb = traceback.extract_tb(exc.__traceback__)[-6:]
        return " at " + " < ".join("%s:%d in %s" % (os.path.basename(f.filename), f.lineno, f.name)
                                   for f in reversed(tb))
    return ""


def scrub_obj(obj):
    """Scrub every string leaf of a JSON-able structure exactly once, before
    serialization (the serialized text is never scrubbed: typed fields stay intact)."""
    if isinstance(obj, str):
        return scrub(obj)
    if isinstance(obj, dict):
        return {(scrub(k) if isinstance(k, str) else k): scrub_obj(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [scrub_obj(v) for v in obj]
    return obj


def log(msg):
    try:
        print(scrub("geminipro: " + msg), file=sys.stderr, flush=True)
    except (OSError, ValueError):
        pass


def _now_iso():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _parse_iso(value):
    try:
        return _dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _where(url):
    return str(url).split("?")[0][-60:]


def _shape(body):
    """A secret-free description of an RPC body: list length, and per index 14-17 the
    type (ints and None shown as values, lists by length, strings never shown)."""
    if not isinstance(body, list):
        return type(body).__name__
    parts = []
    for i in range(14, 18):
        v = body[i] if len(body) > i else "<absent>"
        if v is None or (isinstance(v, int) and not isinstance(v, bool)):
            parts.append("[%d]=%s" % (i, v))
        elif isinstance(v, list):
            parts.append("[%d]=list(%d)" % (i, len(v)))
        else:
            parts.append("[%d]=%s" % (i, "<absent>" if v == "<absent>" else type(v).__name__))
    return "list(%d) %s" % (len(body), " ".join(parts))


def _side(fn, timeout):
    """Run fn in a daemon thread; wait at most timeout seconds (never blocks the caller)."""
    th = threading.Thread(target=fn, daemon=True)
    th.start()
    th.join(timeout)


# --------------------------------------------------------------------------
# OS lock (astrapro.py FileLock pattern): freed by the OS when the holder dies
# --------------------------------------------------------------------------

class FileLock:
    def __init__(self, path):
        self.path = path
        self.fd = None

    def try_acquire(self):
        if self.fd is not None:
            return True
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
        return True

    def acquire(self, timeout, poll=0.2):
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
# cookies from Chrome through browser-harness (read only)
# --------------------------------------------------------------------------

HARNESS_SCRIPT = r'''
import json as _gp_json
_GP_URL = "https://gemini.google.com/app"
_GP_NAMES = ("__Secure-1PSID", "__Secure-1PSIDTS")
def _gp_pick(_cookies):
    _v = {}
    for _k in _cookies or []:
        if _k.get("domain") == ".google.com" and _k.get("name") in _GP_NAMES and _k.get("value"):
            _v[_k["name"]] = _k["value"]
    return _v
_gp_out = {"v": 2, "bc_fields": [], "default_jar": None, "contexts": [], "errors": []}
_gp_infos = cdp("Target.getTargets").get("targetInfos", [])
_gp_default = None
try:
    _gp_bc = cdp("Target.getBrowserContexts") or {}
    _gp_out["bc_fields"] = sorted(str(_k) for _k in _gp_bc)
    _gp_default = _gp_bc.get("defaultBrowserContextId") or None
except Exception as _e:
    _gp_out["errors"].append("contexts: %s" % str(_e)[:160])
_gp_order = []
for _ti in _gp_infos:
    _c = _ti.get("browserContextId")
    if _c and _c not in _gp_order:
        _gp_order.append(_c)
for _c in _gp_order:
    _rec = {"ctx": _c, "via": None, "psid": None, "psidts": None}
    _tg = [_t for _t in _gp_infos if _t.get("browserContextId") == _c
           and _t.get("type") in ("browser_ui", "background_page")]
    _tg.sort(key=lambda _t: 0 if _t.get("type") == "browser_ui" else 1)
    for _t in _tg[:4]:
        try:
            _sid = cdp("Target.attachToTarget", targetId=_t["targetId"], flatten=True)["sessionId"]
        except Exception as _e:
            _gp_out["errors"].append("attach %s: %s" % (_t.get("type"), str(_e)[:160]))
            continue
        try:
            _v = _gp_pick(cdp("Network.getCookies", session_id=_sid, urls=[_GP_URL]).get("cookies"))
        except Exception as _e:
            _v = {}
            _gp_out["errors"].append("cookies %s: %s" % (_t.get("type"), str(_e)[:160]))
        finally:
            try:
                cdp("Target.detachFromTarget", sessionId=_sid)
            except Exception as _e:
                _gp_out["errors"].append("detach: %s" % str(_e)[:160])
        if _v.get("__Secure-1PSID"):
            _rec.update(via=_t.get("type") + "/Network.getCookies", psid=_v.get("__Secure-1PSID"),
                        psidts=_v.get("__Secure-1PSIDTS"))
            break
    _gp_out["contexts"].append(_rec)
_bs = None
try:
    _bs = cdp("Target.attachToBrowserTarget")["sessionId"]
except Exception as _e:
    _gp_out["errors"].append("browser attach: %s" % str(_e)[:160])
if _bs:
    try:
        _v = _gp_pick(cdp("Storage.getCookies", session_id=_bs).get("cookies"))
        _gp_out["default_jar"] = {"ctx": _gp_default, "via": "browser/Storage.getCookies",
                                  "psid": _v.get("__Secure-1PSID"),
                                  "psidts": _v.get("__Secure-1PSIDTS")}
    except Exception as _e:
        _gp_out["errors"].append("browser storage: %s" % str(_e)[:160])
    finally:
        try:
            cdp("Target.detachFromTarget", sessionId=_bs)
        except Exception as _e:
            _gp_out["errors"].append("detach: %s" % str(_e)[:160])
print(_gp_json.dumps(_gp_out))
'''


def harness_env(base):
    """The child env: telemetry, update check and recording off, existing daemon only."""
    env = dict(base)
    for name in TELEMETRY_DISABLE_ENVS:
        env[name] = "0"
    env["BH_UPDATE_CHECK"] = "0"
    env["BH_RECORD"] = "0"
    env["BH_REQUIRE_EXISTING_DAEMON"] = "1"
    env.pop("BU_AUTOSPAWN", None)
    return env


class Candidate:
    def __init__(self, ctx, via, psid, psidts, is_default):
        self.ctx, self.via, self.psid, self.psidts, self.is_default = (
            ctx, via, psid, psidts, is_default)

    @property
    def key(self):
        """What geminipro.d/last-context stores: the browserContextId, or "default" for the
        default jar when Chrome reports no id for it."""
        return self.ctx or "default"

    @property
    def label(self):
        return "%s%s" % (self.key[:8], " (default)" if self.is_default and self.ctx else "")


def _run_harness(argv, script, env, timeout):
    return subprocess.run(argv, input=script.encode("utf-8"), capture_output=True, env=env,
                          timeout=timeout)


def read_candidates(env, timeout, test_context=None):
    """Read the Google session cookies of every Chrome profile. Exit 2 on any failure."""
    exe = shutil.which("browser-harness", path=env.get("PATH"))
    if not exe:
        raise Exit(2, "preflight_refused", "browser-harness is not on PATH")
    try:
        proc = _run_harness([exe], HARNESS_SCRIPT, harness_env(env), timeout)
    except subprocess.TimeoutExpired:
        raise Exit(2, "preflight_refused", "browser-harness did not answer within %ds" % timeout)
    data = None
    for line in reversed(proc.stdout.decode("utf-8", "replace").splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                data = json.loads(line)
            except ValueError:
                data = None
            break
    # register every value BEFORE any message is built (G2)
    if isinstance(data, dict):
        for rec in list(data.get("contexts") or []) + [data.get("default_jar")]:
            if isinstance(rec, dict):
                remember_secret(rec.get("psid"))
                remember_secret(rec.get("psidts"))
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", "replace")
        hint = ("its daemon is not running" if re.search(r"not running|no daemon|connection refused",
                                                          err, re.IGNORECASE)
                else "its output is not echoed")
        raise Exit(2, "preflight_refused",
                   "browser-harness refused (exit %d: %s) - start the browser-harness daemon "
                   "yourself against your running Chrome (run `browser-harness` once), then retry"
                   % (proc.returncode, hint))
    if not isinstance(data, dict) or data.get("v") != 2 or not isinstance(data.get("contexts"), list):
        raise Exit(2, "preflight_refused", "browser-harness output was not the expected cookie "
                   "summary (not echoed)")
    # both stale-session spellings browser-harness knows (helpers.py), any case, matched on
    # the raw text before any redaction could hide the signature (the text is never echoed)
    if any(STALE_RE.search(str(e)) for e in data.get("errors") or []):
        raise Exit(2, "preflight_refused", "browser-harness reported a stale CDP session - restart "
                   "the browser-harness daemon yourself, then retry")
    recs = [dict(c) for c in data["contexts"] if isinstance(c, dict)]
    dj = data.get("default_jar") if isinstance(data.get("default_jar"), dict) else None
    if dj and dj.get("psid"):
        home = None
        for c in recs:
            if (dj.get("ctx") and c.get("ctx") == dj.get("ctx")) or c.get("psid") == dj["psid"]:
                home = c
                break
        if home is None:
            recs.append({"ctx": dj.get("ctx"), "via": dj.get("via"), "psid": dj["psid"],
                         "psidts": dj.get("psidts"), "is_default": True})
        else:
            home["is_default"] = True
            if not home.get("psid"):
                home.update(via=dj.get("via"), psid=dj["psid"], psidts=dj.get("psidts"))
    seen, out = set(), []
    for c in recs:
        psid = c.get("psid")
        if not psid or psid in seen:
            continue
        cand = Candidate(c.get("ctx"), c.get("via"), psid, c.get("psidts"), bool(c.get("is_default")))
        if test_context and not cand.key.startswith(test_context):
            continue
        seen.add(psid)
        out.append(cand)
    if not out:
        raise Exit(2, "preflight_refused", "no Chrome context with Google session cookies%s"
                   % (" matching GEMINIPRO_TEST_CONTEXT" if test_context else ""))
    fields = [f for f in data.get("bc_fields") or [] if isinstance(f, str) and f.isalnum()]
    log("cookies: %d context(s) with a Google session (%s); Target.getBrowserContexts fields: %s."
        % (len(out), ", ".join("%s via %s" % (c.label, c.via) for c in out),
           ", ".join(fields) or "none"))
    return out


def load_remembered(state_dir):
    try:
        with open(os.path.join(state_dir, MEMORY_FILE), "r", encoding="utf-8") as f:
            value = f.read(256).strip()
    except OSError:
        return None
    return value if MEMORY_RE.fullmatch(value) else None


def save_remembered(state_dir, key):
    """Store the proven browserContextId (not a secret) for the next run."""
    if not MEMORY_RE.fullmatch(key or ""):
        return
    path = os.path.join(state_dir, MEMORY_FILE)
    try:
        if load_remembered(state_dir) == key:
            return
        os.makedirs(state_dir, exist_ok=True)
        tmp = "%s.%d.tmp" % (path, os.getpid())
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(key + "\n")
        os.replace(tmp, path)
    except OSError as exc:
        log("could not remember the proven context (%s) - the next run scans again."
            % type(exc).__name__)


def order_candidates(cands, remembered):
    """The remembered context first; the others keep their order behind it."""
    first = [c for c in cands if remembered and c.key == remembered]
    return first + [c for c in cands if c not in first], bool(first)


# --------------------------------------------------------------------------
# identity evidence
# --------------------------------------------------------------------------

def parse_account(html):
    """The signed-in account from the Gemini app page: exactly one oPEP7c field."""
    if not isinstance(html, str) or not html:
        raise NoEvidence("no Gemini app page to read the account from")
    found = OEPEP_RE.findall(html)
    if not found:
        raise NoEvidence("the Gemini app page names no signed-in account")
    values = set()
    for raw in found:
        try:
            values.add(json.loads('"%s"' % raw).strip().lower())
        except ValueError:
            raise NoEvidence("the account field on the Gemini app page is unreadable")
    if len(found) != 1 or len(values) != 1:
        raise NoEvidence("the Gemini app page names %d accounts - ambiguous" % len(found))
    email = values.pop()
    if not EMAIL_RE.fullmatch(email):
        raise NoEvidence("the account field on the Gemini app page is not an email")
    return email


# --------------------------------------------------------------------------
# gemini_webapi hardening (process-local patches; see the docstring)
# --------------------------------------------------------------------------

class Policy:
    """Transport rules for a verified session: one generate POST at most, only once
    armed; never rotate or upload; never follow a redirect; a block ends the run."""

    def __init__(self):
        self.armed = False
        self.deadline = None     # the run's monotonic deadline, set when armed
        self.submissions = 0
        self.refused = []
        self.http_errors = []

    def saw(self, url, resp, body=True):
        from gemini_webapi.constants import Endpoint
        status = getattr(resp, "status_code", None)
        where = _where(url)
        if status is not None and status != 200:
            self.http_errors.append("%s answered HTTP %s" % (where, status))
        if isinstance(status, int) and 300 <= status < 400:
            raise Blocked("%s answered a redirect (HTTP %s) - not followed" % (where, status))
        if status in (403, 429):
            raise Blocked("%s answered HTTP %s" % (where, status))
        if body and str(url).startswith(Endpoint.BATCH_EXEC):
            text = getattr(resp, "text", "") or ""
            if not text.lstrip().startswith(")]}'") and CHALLENGE_RE.search(text[:200000]):
                raise Blocked("%s returned a challenge page (HTTP %s)" % (where, status))
        return resp

    def last_error(self):
        return (" (after: %s)" % self.http_errors[-1]) if self.http_errors else ""

    def check(self, method, url):
        from gemini_webapi.constants import Endpoint
        url = str(url)
        if url.startswith(Endpoint.ROTATE_COOKIES) or url.startswith(Endpoint.UPLOAD):
            self.refused.append("rotate/upload")
            raise PolicyAbort("refused a cookie-rotation or upload request")
        if url.startswith(Endpoint.GENERATE):
            if not self.armed:
                self.refused.append("generate-unarmed")
                raise PolicyAbort("refused a prompt submission before admission")
            if self.submissions >= 1:
                self.refused.append("generate-second")
                raise PolicyAbort("refused a second prompt submission (no resend)")
            if self.deadline is not None and time.monotonic() >= self.deadline:
                self.refused.append("generate-deadline")
                raise DeadlineAbort("total deadline reached just before dispatch - nothing sent")
            self.submissions += 1


class GuardedSession:
    """Wraps the verified curl_cffi session; every request passes the Policy, never
    follows a redirect, and registers the session's cookies as they change."""

    def __init__(self, inner, policy):
        object.__setattr__(self, "_inner", inner)
        object.__setattr__(self, "_policy", policy)

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def __setattr__(self, name, value):
        setattr(self._inner, name, value)

    def _jar(self):
        remember_jar(getattr(self._inner, "cookies", None))

    async def get(self, url, *a, **k):
        self._policy.check("GET", url)
        k["allow_redirects"] = False
        try:
            resp = await self._inner.get(url, *a, **k)
        finally:
            self._jar()
        return self._policy.saw(url, resp)

    async def post(self, url, *a, **k):
        self._policy.check("POST", url)
        k["allow_redirects"] = False
        try:
            resp = await self._inner.post(url, *a, **k)
        finally:
            self._jar()
        return self._policy.saw(url, resp)

    async def request(self, method, url, *a, **k):
        self._policy.check(method, url)
        k["allow_redirects"] = False
        try:
            resp = await self._inner.request(method, url, *a, **k)
        finally:
            self._jar()
        return self._policy.saw(url, resp)

    def stream(self, method, url, *a, **k):
        self._policy.check(method, url)
        k["allow_redirects"] = False
        return self._stream(method, url, a, k)

    @contextlib.asynccontextmanager
    async def _stream(self, method, url, a, k):
        try:
            async with self._inner.stream(method, url, *a, **k) as resp:
                self._jar()
                self._policy.saw(url, resp, body=False)
                try:
                    yield resp
                finally:
                    self._jar()
        finally:
            self._jar()


class Held:
    """Identity set holding strong references (no id() reuse after garbage collection)."""

    def __init__(self):
        self.items = []

    def add(self, obj):
        if obj not in self:
            self.items.append(obj)

    def discard(self, obj):
        self.items = [o for o in self.items if o is not obj]

    def __contains__(self, obj):
        return any(o is obj for o in self.items)


class _State:
    def __init__(self):
        self.new_run()

    def reset_attempt(self):
        self.calls = 0
        self.html = None
        self.seen = None
        self.user_status = []   # per GetUserStatus part SENT: raw [14] (or _ABSENT), reject, models
        self.user_status_shape = []  # their shapes (types / lengths / ints only) for reasons
        self.completed = {}     # rcid -> the latest frame carried the completion marker

    def new_run(self):
        """Fresh per-invocation state (main() may run more than once in a process)."""
        self.expected = EXPECTED_ACCOUNT
        self.policy = Policy()
        self.reset_attempt()
        self.verified = Held()       # clients whose identity is proven
        self.initializing = Held()   # clients inside init() (a nested init would deadlock)
        self.after_dispatch = Held()  # clients past the generate POST
        self.spy = {"save_cookies": 0, "clear_cookies_cache": 0, "rotate": 0}
        self.notes = []


STATE = _State()
_HARDENED = {}


def _library_version():
    from importlib import metadata
    try:
        return metadata.version("gemini_webapi")
    except metadata.PackageNotFoundError:
        return None


def harden():
    """Check the library release, then patch the gemini_webapi bindings each module
    imported (idempotent)."""
    found = _library_version()
    if found != LIB_VERSION:
        raise Exit(2, "preflight_refused", "gemini_webapi %s is installed; geminipro's no-write "
                   "hardening is written for exactly %s - nothing read or sent" % (found, LIB_VERSION))
    if _HARDENED:
        return _HARDENED
    from pathlib import Path
    from loguru import logger as _loguru
    import gemini_webapi.client as gc
    from curl_cffi.requests import Cookies
    from gemini_webapi.constants import GRPC, Endpoint, Headers
    gat = sys.modules["gemini_webapi.utils.get_access_token"]
    rot = sys.modules["gemini_webapi.utils.rotate_1psidts"]
    upkg = sys.modules["gemini_webapi.utils"]
    _loguru.disable("gemini_webapi")
    nocache = Path(tempfile.gettempdir()) / ("geminipro-nocache-%d" % os.getpid())

    def no_save(*_a, **_k):
        STATE.spy["save_cookies"] += 1      # never writes

    def no_clear(*_a, **_k):
        STATE.spy["clear_cookies_cache"] += 1

    async def no_rotate(*_a, **_k):
        STATE.spy["rotate"] += 1
        raise PolicyAbort("cookie rotation refused")

    for mod in (gc, rot, upkg):
        mod.save_cookies = no_save
        mod.clear_cookies_cache = no_clear
        mod.rotate_1psidts = no_rotate
    for mod in (gat, rot):
        mod._get_cookies_cache_path = lambda *_a, **_k: None
        mod._get_cookie_cache_dir = lambda: nocache
    gat.load_browser_cookies = lambda *_a, **_k: {}

    extract = gat._extract_payload
    cookie_domain = gat._COOKIE_DOMAIN

    async def send_capture(client, cookies, verbose=False):
        """The library's _send_request, with redirects off, the jar registered, and the
        answer classified: block -> Blocked (run ends), signed out -> NoEvidence."""
        if STATE.calls >= 1:
            raise NoEvidence("init fell back past the supplied cookies")
        STATE.calls += 1
        client.cookies.clear()
        if isinstance(cookies, Cookies):
            client.cookies.update(cookies)
        else:
            for k, v in cookies.items():
                client.cookies.set(k, v, domain=cookie_domain, secure=True)
        remember_jar(client.cookies)
        with contextlib.suppress(Exception):
            client.allow_redirects = False
        page = "the Gemini app page"
        try:
            resp = await client.get(Endpoint.INIT, headers=Headers.GEMINI.value,
                                    allow_redirects=False)
        except Exception as exc:  # cancellation passes through untouched
            remember_jar(client.cookies)  # registered before the message is built
            raise BootstrapError("%s request failed (%s)" % (page, fmt_exc(exc)[:300])) from None
        finally:
            remember_jar(client.cookies)
        status = resp.status_code
        if isinstance(status, int) and 300 <= status < 400:
            raise Blocked("%s answered a redirect (HTTP %s) - not followed" % (page, status))
        if status in (403, 429):
            raise Blocked("%s answered HTTP %s" % (page, status))
        if isinstance(status, int) and status >= 500:
            resp.raise_for_status()   # the library re-raises 5xx: preflight failure, exit 2
        text = resp.text or ""
        payload = extract(resp) if status == 200 else None
        if payload is None:
            if CHALLENGE_RE.search(text):
                raise Blocked("%s is a challenge page (HTTP %s)" % (page, status))
            if status != 200:
                raise NoEvidence("%s answered HTTP %s" % (page, status))
            raise NoEvidence("%s carried no session values (signed out?)" % page)
        STATE.html = text
        return resp

    gat._send_request = send_capture
    orig_gat = gat.get_access_token

    async def verified_get_access_token(*a, **k):
        sess = await orig_gat(*a, **k)
        try:
            remember_jar(getattr(sess.client, "cookies", None))
            if sess.cookie_source != "Base Cookies":
                raise NoEvidence("init used '%s', not the supplied cookies" % sess.cookie_source)
            if not sess.access_token:
                raise NoEvidence("no access token (guest session)")
            seen = parse_account(STATE.html)
            STATE.seen = seen
            if seen != STATE.expected.strip().lower():
                raise AccountMismatch(seen, "signed-in account is %s, not %s" % (seen, STATE.expected))
        except BaseException:
            STATE.html = None
            await safe_close(sess.client)
            raise
        STATE.html = None
        return sess._replace(client=GuardedSession(sess.client, STATE.policy))

    gc.get_access_token = verified_get_access_token
    orig_init = gc.GeminiClient.init

    async def guarded_init(self, *a, **k):
        if self in STATE.verified:
            STATE.policy.refused.append("reinit")
            raise PolicyAbort("refused a re-init after the identity proof%s"
                              % STATE.policy.last_error())
        if self in STATE.initializing:  # the retry decorator re-entering a failed init
            STATE.policy.refused.append("nested-init")
            raise PolicyAbort("an init RPC failed and the library tried to re-init - refused%s"
                              % STATE.policy.last_error())
        STATE.initializing.add(self)
        try:
            return await orig_init(self, *a, **k)
        finally:
            STATE.initializing.discard(self)

    gc.GeminiClient.init = guarded_init
    orig_parse = gc.GeminiClient._parse_rpc_results

    from gemini_webapi.utils.parsing import extract_json_from_response, get_nested_value

    def count_status_parts(response_text, target_id):
        """Every GetUserStatus part the server sent, read from the raw response (the
        library skips malformed / empty bodies and stops at a reject code)."""
        try:
            raw_parts = extract_json_from_response(response_text)
        except Exception:
            raw_parts = None
        if not isinstance(raw_parts, list):
            STATE.user_status.append({"code": _ABSENT, "reject": None, "models": False})
            STATE.user_status_shape.append("unreadable response")
            return
        for part in raw_parts:
            if get_nested_value(part, [1]) != target_id:
                continue
            rec = {"code": _ABSENT, "reject": get_nested_value(part, [5, 0]), "models": False}
            raw = get_nested_value(part, [2])
            if rec["reject"] is not None:
                r = rec["reject"]
                shape = "reject code %s" % (r if type(r) is int else type(r).__name__)
            elif not isinstance(raw, str) or not raw:
                shape = "empty body"
            else:
                try:
                    body = json.loads(raw)
                except ValueError:
                    body = _ABSENT
                if body is _ABSENT:
                    shape = "malformed body"
                else:
                    long_list = isinstance(body, list) and len(body) > 14
                    rec["code"] = body[14] if long_list else _ABSENT
                    rec["models"] = bool(long_list and len(body) > 15 and isinstance(body[15], list)
                                         and len(body[15]) > 0)
                    shape = _shape(body)
            STATE.user_status.append(rec)
            STATE.user_status_shape.append(shape)

    def parse_capture(self, response_text, target_id):
        if target_id != GRPC.GET_USER_STATUS:
            yield from orig_parse(self, response_text, target_id)
            return
        count_status_parts(response_text, target_id)
        # drained before the library's early-returning consumer sees the first body
        yield from list(orig_parse(self, response_text, target_id))

    gc.GeminiClient._parse_rpc_results = parse_capture
    orig_candidate = gc.GeminiClient._parse_candidate

    def candidate_capture(self, candidate_data, *a, **k):
        """Records the library's own completion marker per candidate ([8][0] == 2,
        client.py:1707-1709) for the frame about to be yielded."""
        out = orig_candidate(self, candidate_data, *a, **k)
        rcid = get_nested_value(candidate_data, [0])
        if rcid:
            STATE.completed[rcid] = get_nested_value(candidate_data, [8, 0]) == 2
        return out

    gc.GeminiClient._parse_candidate = candidate_capture
    orig_usage = gc.GeminiClient._fetch_usage_info

    async def usage_before_dispatch_only(self):
        if self in STATE.after_dispatch:
            return None  # the job path sends no RPC after the prompt (the answer stays ours)
        return await orig_usage(self)

    gc.GeminiClient._fetch_usage_info = usage_before_dispatch_only
    _HARDENED.update(gc=gc, gat=gat, rot=rot, upkg=upkg, raw_generate=gc.GeminiClient._generate.__wrapped__,
                     nocache=nocache)
    return _HARDENED


async def safe_close(client):
    """Close a client or session; bounded, never raises an ordinary error."""
    if client is None:
        return
    with contextlib.suppress(Exception):
        await asyncio.wait_for(client.close(), CLOSE_TIMEOUT)


async def open_verified(cands, init_timeout, context_out):
    """Init a client per candidate until one is proven to be the expected account.
    A block (challenge / 403 / 429 / redirect) on any candidate ends the search."""
    h = harden()
    from gemini_webapi.exceptions import TemporarilyBlockedError
    from gemini_webapi.constants import AccountStatus
    tried = []
    for cand in cands:
        STATE.reset_attempt()
        client = h["gc"].GeminiClient(cand.psid, cand.psidts or None)
        try:
            await client.init(timeout=init_timeout, auto_close=False, auto_refresh=False,
                              verbose=False)
        except AccountMismatch as exc:
            await safe_close(client)
            tried.append("%s: %s" % (cand.label, exc.why))
            log("identity: context %s is not the expected account (%s)." % (cand.label, exc.why))
            continue
        except Blocked:
            await safe_close(client)
            raise
        except TemporarilyBlockedError:
            await safe_close(client)
            raise Blocked("Google answered HTTP 429 (temporarily blocked) at init")
        except PolicyAbort as exc:
            await safe_close(client)
            raise Exit(2, "preflight_refused", "Gemini init failed for context %s: %s - nothing "
                       "sent; stop, do not retry around it" % (cand.label, scrub(str(exc))[:300]))
        except Exception as exc:  # BootstrapError (H1) included: no other context is tried
            await safe_close(client)
            raise Exit(2, "preflight_refused", "Gemini init failed for context %s: %s%s - nothing "
                       "sent" % (cand.label, fmt_exc(exc)[:300], STATE.policy.last_error()))
        except BaseException:  # cancellation / interrupt: the live session is closed too
            await safe_close(client)
            raise
        try:
            STATE.verified.add(client)
            context_out.update(context=cand.label, key=cand.key, account=STATE.seen)
            if client.account_status == AccountStatus.UNAUTHENTICATED:
                raise Exit(8, "account_mismatch", "Gemini reports the session UNAUTHENTICATED")
            parts = list(STATE.user_status)
            # Every part the server sent is judged as if it had come alone (H2): a part
            # naming another status exits by that status, wherever it sits.
            for i, p in enumerate(parts, 1):
                rej, c = p.get("reject"), p.get("code")
                if rej == 7 or c == AccountStatus.UNAUTHENTICATED.value:
                    raise Exit(8, "account_mismatch", "GetUserStatus part %d of %d: %s - nothing "
                               "sent" % (i, len(parts), "reject code 7 (permission denied / "
                                         "unauthenticated)" if rej == 7 else "1016 UNAUTHENTICATED"))
            for i, p in enumerate(parts, 1):
                c = p.get("code")
                if type(c) is int and c != AccountStatus.AVAILABLE.value:
                    st = AccountStatus.from_status_code(c)
                    raise Exit(2, "preflight_refused", "GetUserStatus %s: %s - %s (part %d of %d) - "
                               "nothing sent" % (c, st.name, st.description, i, len(parts)))
            # Positive evidence: exactly one GetUserStatus part sent for this session, a
            # list body with field 14 present; 14 is null (live AVAILABLE shape, 2026-11-13:
            # list(25), [14] null, [15] the model registry) or the int 1000; a non-empty
            # model registry that the library registered. The constructor default and
            # from_status_code(None) both say AVAILABLE, so neither is trusted alone.
            code = parts[0]["code"] if len(parts) == 1 else _ABSENT
            readable = code is None or (type(code) is int)
            if len(parts) != 1 or not readable:
                raise Exit(2, "preflight_refused", "GetUserStatus returned no readable account "
                           "status (%d part(s): %s) - not treated as AVAILABLE; nothing sent"
                           % (len(parts), "; ".join(STATE.user_status_shape) or "none"))
            if (code is not None and code != 1000) or client.account_status != AccountStatus.AVAILABLE:
                st = AccountStatus.from_status_code(code) if code is not None else client.account_status
                raise Exit(2, "preflight_refused", "GetUserStatus %s: %s - %s"
                           % (code, st.name, st.description))
            if not parts[0]["models"] or not (client.list_models() or []):
                raise Exit(2, "preflight_refused", "GetUserStatus carried no model registry (%s) "
                           "- not treated as AVAILABLE; nothing sent"
                           % "; ".join(STATE.user_status_shape))
        except BaseException:
            await safe_close(client)
            raise
        log("identity: %s proven from the Gemini app page (context %s via %s); GetUserStatus "
            "AVAILABLE (%s)." % (STATE.seen, cand.label, cand.via, STATE.user_status_shape[0]))
        return client
    raise Exit(8, "account_mismatch", "no Chrome context is signed in to Gemini as %s (%s) - "
               "nothing sent" % (STATE.expected, "; ".join(tried) or "nothing tried"))


def model_names(client):
    return [m.model_name for m in client.list_models() or []]


def pick_model(client, wanted):
    w = wanted.strip().lower()
    for m in client.list_models() or []:
        if m.model_name.lower() == w or w in [str(a).lower() for a in (m.aliases or [])]:
            return m
    raise Exit(4, "model_not_available", "model '%s' is not offered to this account; available: %s"
               % (wanted, ", ".join(model_names(client)) or "none"))


# --------------------------------------------------------------------------
# the API backup: one child process of the gemini-api CLI (never the HTTP API directly)
# --------------------------------------------------------------------------

class ApiFailure(Exception):
    """The API backup ran and did not answer (the run keeps the app path's exit)."""


def api_body(text, model):
    """The request body file's bytes: UTF-8 JSON of exactly the gate-passed text."""
    return json.dumps({"input": text, "model": model, "stream": False, "store": False},
                      ensure_ascii=False).encode("utf-8")


def api_argv(cli):
    return [cli, "generate", "--output-format", "json", "--body", "@" + API_BODY]


_created = lanew_log.pid_created  # a live process's creation time (FILETIME ticks) or None; tests replace


def _kill_direct(proc):
    """The direct CLI child, through its own Popen handle (never by pid)."""
    with contextlib.suppress(Exception):
        proc.kill()


def _dead(proc):
    try:
        return proc.poll() is not None
    except Exception:
        return False


def _kill_tree(proc, created=None):
    """Timeout / interrupt path. Windows (no taskkill): ONE process snapshot while the root is
    still alive, the verified descendants from it (_descendants, `created` = the root's
    creation time recorded at start), then the root through its own handle (proc.kill, so it
    starts nothing new), then each descendant through its own handle after its creation time
    is re-checked (_kill_verified). With the root's creation time unknown only the root is
    killed. POSIX: the process group, then the root. The root is killed again in a finally,
    so an interrupted or failed descendant step never leaves it running; when that step did
    not finish, the verified walk (_kill_descendants) on the now dead root takes the rest."""
    done = False
    try:
        try:
            if os.name == "nt":
                kids = _descendants(proc.pid, created, _snapshot()) if created else []
                _kill_direct(proc)
                for pid, c in kids:
                    _kill_verified(pid, c)
            else:
                os.killpg(proc.pid, signal.SIGKILL)
            done = True
        except Exception:
            pass
    finally:
        _kill_direct(proc)
        if not done:
            with contextlib.suppress(Exception):
                _kill_descendants(proc, created)


def _snapshot():
    """Windows: every process as (pid, recorded parent pid, creation time) from ONE
    NtQuerySystemInformation(SystemProcessInformation) call - the parent ids and creation
    times come from the same instant, so a reused pid is told apart. [] on any error."""
    if os.name != "nt":
        return []
    import ctypes
    from ctypes import wintypes as wt

    class Entry(ctypes.Structure):  # SYSTEM_PROCESS_INFORMATION, the fields up to the parent id
        _fields_ = [("NextEntryOffset", wt.ULONG), ("NumberOfThreads", wt.ULONG),
                    ("WorkingSetPrivateSize", ctypes.c_int64), ("HardFaultCount", wt.ULONG),
                    ("NumberOfThreadsHighWatermark", wt.ULONG), ("CycleTime", ctypes.c_uint64),
                    ("CreateTime", ctypes.c_int64), ("UserTime", ctypes.c_int64),
                    ("KernelTime", ctypes.c_int64), ("NameLength", wt.USHORT),
                    ("NameMaximumLength", wt.USHORT), ("NameBuffer", ctypes.c_void_p),
                    ("BasePriority", wt.LONG), ("UniqueProcessId", ctypes.c_void_p),
                    ("InheritedFromUniqueProcessId", ctypes.c_void_p)]

    try:
        nt = ctypes.WinDLL("ntdll")
        nt.NtQuerySystemInformation.restype = ctypes.c_long
        nt.NtQuerySystemInformation.argtypes = [wt.ULONG, ctypes.c_void_p, wt.ULONG,
                                                ctypes.POINTER(wt.ULONG)]
        size = 1 << 20
        for _ in range(6):
            buf = ctypes.create_string_buffer(size)
            need = wt.ULONG(0)
            status = nt.NtQuerySystemInformation(5, buf, size, ctypes.byref(need)) & 0xFFFFFFFF
            if status == 0:
                break
            if status != 0xC0000004:  # STATUS_INFO_LENGTH_MISMATCH: retry with a bigger buffer
                return []
            size = max(size * 2, need.value + (1 << 16))
        else:
            return []
        out, off = [], 0
        while off + ctypes.sizeof(Entry) <= size:
            e = Entry.from_buffer(buf, off)
            out.append((int(e.UniqueProcessId or 0), int(e.InheritedFromUniqueProcessId or 0),
                        int(e.CreateTime)))
            if not e.NextEntryOffset:
                break
            off += e.NextEntryOffset
        return out
    except Exception:
        return []


def _descendants(root_pid, root_created, snapshot):
    """The verified tree under the root, parents first, as (pid, creation time): a process
    counts only when its recorded parent is the root or a verified descendant AND it was
    created at or after that parent (so at or after the root). An older process whose
    recorded parent pid is a reused pid is never in it, nor one whose creation time is
    unknown; with the root's own time unknown nothing is verifiable (empty)."""
    if not root_created:
        return []
    out, frontier, seen = [], [(root_pid, root_created)], {root_pid}
    while frontier:
        parent, parent_created = frontier.pop(0)
        for pid, ppid, created in snapshot:
            if ppid == parent and pid not in seen and created and created >= parent_created:
                seen.add(pid)
                out.append((pid, created))
                frontier.append((pid, created))
    return out


def _kill_verified(pid, created):
    """Windows: force-kill pid only through a handle whose own creation time equals created
    (never by pid alone: a reused pid has another creation time). True when terminated."""
    import ctypes
    from ctypes import wintypes as wt
    try:
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        k.OpenProcess.restype = wt.HANDLE
        k.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
        k.GetProcessTimes.argtypes = [wt.HANDLE] + [ctypes.POINTER(ctypes.c_uint64)] * 4
        k.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]
        k.CloseHandle.argtypes = [wt.HANDLE]
        h = k.OpenProcess(0x0001 | 0x1000, False, int(pid))  # TERMINATE | QUERY_LIMITED_INFORMATION
        if not h:
            return False
        try:
            t = [ctypes.c_uint64() for _ in range(4)]
            if not k.GetProcessTimes(h, *[ctypes.byref(x) for x in t]) or not t[0].value:
                return False
            if int(t[0].value) != int(created):
                return False
            return bool(k.TerminateProcess(h, 1))
        finally:
            k.CloseHandle(h)
    except Exception:
        return False


def _kill_descendants(proc, created):
    """The verified tree step, run after the direct child was killed (the backstop; the
    timeout path when its tree step did not finish; finish()): on Windows every verified
    descendant of the root (_descendants over one _snapshot, `created` = the root's creation
    time recorded at start) is killed through its own handle (_kill_verified), parents first;
    on POSIX the child's process group."""
    if os.name == "nt":
        for pid, c in _descendants(proc.pid, created, _snapshot()):
            _kill_verified(pid, c)
    else:
        with contextlib.suppress(Exception):
            os.killpg(proc.pid, signal.SIGKILL)


def _reap(proc, holder):
    """Every path out of _run_api: a child still running is killed (its own handle); it leaves
    the holder only once it is confirmed dead, so the backstop and finish() can still reach it."""
    try:
        if not _dead(proc):
            _kill_direct(proc)
            with contextlib.suppress(Exception):
                proc.wait(timeout=5)
    finally:
        if _dead(proc) and holder.get("proc") is proc:
            holder.pop("proc", None)
            holder.pop("created", None)


def _run_api(argv, cwd, env, timeout, stdin, holder):
    """Run the CLI once (no shell); the live child sits in holder["proc"] and its creation
    time, read at start while it is alive, in holder["created"] (for the backstop's verified
    tree step). A timeout or interrupt kills the child tree before re-raising; every path out
    kills a child still running and drops it from holder only when it is dead. Tests replace this."""
    extra = {} if os.name == "nt" else {"start_new_session": True}
    holder["proc"] = proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=stdin,
                                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                             shell=False, **extra)
    try:
        holder["created"] = _created(proc.pid)
        try:
            out, err = proc.communicate(timeout=timeout)
        except BaseException:
            _kill_tree(proc, holder.get("created"))
            with contextlib.suppress(Exception):
                proc.communicate(timeout=5)
            raise
    finally:
        _reap(proc, holder)
    return subprocess.CompletedProcess(argv, proc.returncode, out, err)


def _json_tail(data):
    """The CLI's JSON object: the whole text, else the last line that starts with '{'."""
    text = data.decode("utf-8", "replace") if isinstance(data, bytes) else str(data or "")
    with contextlib.suppress(ValueError):
        obj = json.loads(text.strip())
        if isinstance(obj, dict):
            return obj
    for line in reversed(text.splitlines()):
        if line.strip().startswith("{"):
            with contextlib.suppress(ValueError):
                obj = json.loads(line.strip())
                if isinstance(obj, dict):
                    return obj
    return None


def api_server_error(obj):
    """A retryable CLI error: error_type server_error or error.code service_unavailable."""
    if not isinstance(obj, dict):
        return False
    err = obj.get("error")
    return obj.get("error_type") == "server_error" or (
        isinstance(err, dict) and err.get("code") == "service_unavailable")


def api_error_text(rc, stderr):
    """A short description of a failed CLI call (the caller scrubs and truncates it)."""
    obj = _json_tail(stderr)
    if isinstance(obj, dict) and (obj.get("error") or obj.get("error_type")):
        err = obj.get("error") if isinstance(obj.get("error"), dict) else {}
        kinds = ", ".join(str(x) for x in (err.get("code"), obj.get("error_type")) if x)
        return "CLI exit %d (%s): %s" % (rc, scrub(kinds)[:80] or "error",
                                         scrub(str(err.get("message") or ""))[:400])
    text = scrub(" ".join((stderr or b"").decode("utf-8", "replace").split()))[:400]
    return "CLI exit %d%s" % (rc, (": " + text) if text else " with no error text")


def api_answer(stdout):
    """The answer text from the CLI's JSON: status completed; the text items of the
    model_output steps, in order (thought steps ignored)."""
    try:
        obj = json.loads((stdout or b"").decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        obj = None
    if not isinstance(obj, dict):
        raise ApiFailure("the CLI output was not the expected JSON (not echoed)")
    if obj.get("status") != "completed":
        raise ApiFailure("the interaction status is %s, not completed"
                         % scrub(str(obj.get("status")))[:40])
    texts = []
    for step in obj.get("steps") or []:
        if isinstance(step, dict) and step.get("type") == "model_output":
            for item in step.get("content") or []:
                if isinstance(item, dict) and item.get("type") == "text" and isinstance(
                        item.get("text"), str):
                    texts.append(item["text"])
    return "".join(texts)


def credits(usage, key):
    w = (usage or {}).get(key) or {}
    if not w:
        return None
    return {"remaining_credits": w.get("remaining_credits"), "usage_percentage":
            w.get("usage_percentage"), "reset_at": w.get("reset_at")}


# --------------------------------------------------------------------------
# the wrapper
# --------------------------------------------------------------------------

class Wrapper:
    def __init__(self, argv, env):
        # the API key is a secret from the first line on: before argument parsing and before
        # any output, in every mode (a value under SECRET_MIN is not a key: not registered)
        key = env.get("GEMINI_API_KEY")
        self.api_keys = ()          # the registered key spellings (raw, stripped)
        if isinstance(key, str) and len(key) >= SECRET_MIN:
            remember_secret(key)
            remember_secret(key.strip())
            self.api_keys = tuple(v for v in {key, key.strip()} if len(v) >= SECRET_MIN)
        self.argv, self.env = list(argv), env
        self.t0 = time.monotonic()
        try:  # the one deadline; config() validates the value (exit 64 if malformed)
            self.total = max(1.0, float(env.get("GEMINIPRO_TOTAL_DEADLINE") or 900))
        except ValueError:
            self.total = 900.0
        self.deadline = self.t0 + self.total
        self.run = self.name = self.job_id = self.report = None
        self.model = None
        self.json_mode = "--json" in self.argv   # decided before anything can fail
        self.status_mode = False
        self.brief_file = None
        self.test = False
        self.account = None         # the resolved production account (config)
        self.account_ok = None
        self.ctx = {}
        self.extra = {}
        self.answer = None          # raw; each sink scrubs it once
        self.report_written = False
        self.term_ok = None         # the terminal record's verified append (None: not written)
        self.body_done = False      # the answer / summary output step has run
        self.ts_start = None
        self.job_ended = False
        self.term_lock = threading.Lock()
        self.lock = None
        self.notes = []
        self.emitted = False
        self.emit_lock = threading.Lock()
        self.via = "app"            # "api" from the start of the API admission (back to "app" if no job id)
        self.trigger = None         # the status-line keys when the backup trigger fired
        self.primary = None         # the app path's Exit that fired the trigger
        self.api_model = API_MODEL
        self.api_timeout = float(API_TIMEOUT)
        self.api_holder = {}        # the live CLI child ("proc"), for the backstop
        self.api_dir = None         # the body file's directory while it exists
        self.api_started = False    # a CLI child was started (the brief may have gone out)

    # ---- config -----------------------------------------------------------------
    def parse_args(self):
        def usage(why):
            raise Exit(64, "usage_error", "%s - %s" % (why, USAGE))

        pos, a = [], list(self.argv)
        while a:
            t = a.pop(0)
            if t in ("-h", "--help"):
                usage("help")
            elif t == "--json":
                self.json_mode = True
            elif t == "--status":
                self.status_mode = True
            elif t in ("--model", "--brief-file"):
                if not a or a[0].startswith("--"):
                    usage("%s needs a value" % t)
                v = a.pop(0)
                if t == "--model":
                    self.model = v
                else:
                    self.brief_file = v
            elif t.startswith("--model="):
                self.model = t.split("=", 1)[1]
            elif t.startswith("--brief-file="):
                self.brief_file = t.split("=", 1)[1]
            elif t.startswith("-"):
                usage("unknown option %s" % t)
            else:
                pos.append(t)
        if any(self.key_in(v) for v in pos):  # every mode; the value is never echoed
            usage("run/name contains the API key")
        self.model = self.model or self.env.get("GEMINIPRO_MODEL") or DEFAULT_MODEL
        if self.status_mode:
            if pos or self.brief_file:
                usage("--status takes no run, name or brief")
            return
        if len(pos) != 2:
            usage("expected <run> <name>")
        self.run, self.name = pos
        for v in pos:
            if not NAME_RE.fullmatch(v):
                usage("run/name must match [A-Za-z0-9._-]{1,80}")

    def config(self):
        e = self.env
        self.test = e.get("GEMINIPRO_TEST") == "1"
        for k in TEST_ONLY:
            if e.get(k) and not self.test:
                raise Exit(2, "preflight_refused", "%s is test-only (needs GEMINIPRO_TEST=1)" % k)
        # the production account: a set GEMINIPRO_ACCOUNT (even blank) wins over the default
        raw = e.get(ACCOUNT_ENV)
        self.account = (EXPECTED_ACCOUNT if raw is None else raw).strip()
        if not self.account:
            raise Exit(2, "preflight_refused", "no Google account configured: set %s to the "
                       "account Chrome is signed in to on gemini.google.com - nothing read or "
                       "sent" % ACCOUNT_ENV)
        override = (e.get("GEMINIPRO_EXPECT_ACCOUNT") or "").strip() if self.test else ""
        STATE.expected = override or self.account
        self.test_context = e.get("GEMINIPRO_TEST_CONTEXT") if self.test else None

        def num(key, default, lo):
            try:
                return max(lo, float(e.get(key) or default))
            except ValueError:
                raise Exit(64, "usage_error", "%s must be a number" % key)

        num("GEMINIPRO_TOTAL_DEADLINE", 900, 1)  # validated; the value is self.total
        self.slot_wait = num("GEMINIPRO_SLOT_WAIT", 300, 0)
        self.ceiling = int(num("GEMINIPRO_RUN_JOB_CEILING", 12, 1))
        self.daily_cap = int(num("GEMINIPRO_DAILY_CAP", 80, 1))
        self.api_timeout = num("GEMINIPRO_API_TIMEOUT", API_TIMEOUT, 1)
        self.api_model = (e.get("GEMINIPRO_API_MODEL") or "").strip() or API_MODEL
        home = os.path.expanduser("~")
        self.cliproxy = e.get("CLIPROXY_DIR") or os.path.join(home, ".cli-proxy-api")
        self.usage_log = e.get("GEMINIPRO_LOG") or os.path.join(self.cliproxy, "geminipro-usage.jsonl")
        if not self.status_mode:  # job mode creates files under both roots (names persisted)
            for var, root in (("CLIPROXY_DIR", self.cliproxy), ("GEMINIPRO_LOG", self.usage_log)):
                if self.key_in(root):
                    raise Exit(64, "usage_error", "%s contains the API key" % var)
        self.out_dir = os.path.join(self.cliproxy, "geminipro-out")
        self.state_dir = os.path.join(self.cliproxy, "geminipro.d")

    def key_in(self, *texts):
        """The registered API key occurs in any of texts: the one check every persistence and
        process boundary uses (metadata carrying the key is refused, never scrubbed)."""
        return any(isinstance(t, str) and any(k in t for k in self.api_keys) for t in texts)

    def left(self):
        return self.deadline - time.monotonic()

    def bounded(self, fn, what):
        """Run a blocking read under the total deadline (exit 5 when it runs out)."""
        box = {}

        def work():
            try:
                box["v"] = fn()
            except BaseException as exc:  # handed back to the caller's thread
                box["e"] = exc

        th = threading.Thread(target=work, name="geminipro-read", daemon=True)
        th.start()
        th.join(max(0.0, self.left()))
        if th.is_alive():
            raise Exit(5, "deadline", "total deadline reached while %s - nothing sent" % what)
        if "e" in box:
            raise box["e"]
        return box["v"]

    # ---- brief gate (astrapro.py brief_gate) ------------------------------------
    def read_brief(self):
        if self.brief_file:
            path = self.brief_file

            def read_file():
                with open(path, "rb") as f:
                    return f.read()

            try:
                return self.bounded(read_file, "reading --brief-file")
            except OSError as exc:
                raise Exit(64, "usage_error", "cannot read --brief-file: %s" % fmt_exc(exc))
        stdin = sys.stdin
        if stdin is None or (hasattr(stdin, "isatty") and stdin.isatty()):
            raise Exit(64, "usage_error", "brief on stdin or --brief-file - %s" % USAGE)
        try:
            fd = stdin.fileno()
        except (AttributeError, OSError, ValueError, io.UnsupportedOperation):
            fd = None
        if fd is not None:
            def read_stdin():  # raw fd reads: no buffered-IO lock left held at shutdown
                chunks = []
                while True:
                    chunk = os.read(fd, 65536)
                    if not chunk:
                        return b"".join(chunks)
                    chunks.append(chunk)
        else:
            def read_stdin():
                return stdin.buffer.read() if hasattr(stdin, "buffer") else stdin.read().encode("utf-8")
        return self.bounded(read_stdin, "reading the brief from stdin")

    def brief_gate(self, data):
        def refuse(why):
            log("brief gate REFUSED - %s. Nothing sent, nothing logged." % why)
            raise Exit(7, "brief_refused", why)

        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            refuse("brief is not valid UTF-8")
        if text.startswith("﻿"):
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
        return text

    # ---- caps -------------------------------------------------------------------
    def take_slot(self):
        os.makedirs(self.state_dir, exist_ok=True)
        os.makedirs(self.out_dir, exist_ok=True)
        self.lock = FileLock(os.path.join(self.state_dir, "job.lock"))
        wait = max(0.0, min(self.slot_wait, self.left() - JOB_MIN))
        if not self.lock.acquire(wait):
            self.lock = None
            raise Exit(5, "no_slot", "another geminipro job holds the slot (waited %.0fs)" % wait)
        log("slot taken (one job at a time).")

    def daily_count(self):
        try:
            with open(self.usage_log, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            return 0
        today, n = _dt.datetime.now().date(), 0
        for raw in lines:
            if not raw.strip():
                continue
            try:
                e = json.loads(raw)
            except ValueError:
                raise Exit(1, "run_refused", "usage log is corrupt - refusing")
            if isinstance(e, dict) and e.get("status") == "started":
                ts = _parse_iso(e.get("ts_start"))
                if ts is not None and ts.astimezone().date() == today:
                    n += 1
        return n

    def precheck(self):
        ok, reason = lanew_log.check(self.run, log_path=self.usage_log, ceiling=self.ceiling)
        if not ok:
            raise Exit(1, "run_refused", reason)
        n = self.daily_count()
        if n >= self.daily_cap:
            raise Exit(1, "run_refused", "daily cap reached: %d job(s) admitted today (cap %d)"
                       % (n, self.daily_cap))

    def admit(self):
        n = self.daily_count()
        if n >= self.daily_cap:
            raise Exit(1, "run_refused", "daily cap reached: %d job(s) admitted today (cap %d)"
                       % (n, self.daily_cap))
        stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.report = os.path.join(self.out_dir, "%s-%s-%s-%d.md"
                                   % (stamp, self.run, self.name, os.getpid())).replace("\\", "/")
        # every string the started and terminal records carry (the report path is also the
        # report's file name); the model may be a name from the app's own registry
        if self.key_in(self.run, self.name, self.model, self.report, self.usage_log):
            self.report = None
            raise Exit(3, "log_failure", "the usage record would carry the API key - nothing admitted")
        args = (self.run, self.name, self.model, None, self.report)
        kw = {"owner_pid": os.getpid(), "log_path": self.usage_log, "ceiling": self.ceiling,
              "owner_created": lanew_log.pid_created(os.getpid())}
        try:  # the handoff: job_id is taken from the returned entry in the very next statement
            status, reason, entry = lanew_log.admit(*args, **kw)
            if status == "admitted":
                self.job_id, self.ts_start = entry["job_id"], entry["ts_start"]
        except Exception as exc:
            status, reason, entry = "log_error", fmt_exc(exc), None
        if status == "refused":
            raise Exit(1, "run_refused", reason)
        if status != "admitted":
            raise Exit(3, "log_failure", "record start failed: %s" % reason)
        log("admitted job_id=%s (run %s)." % (self.job_id, self.run))

    def record_terminal(self, status, code, latch=None):
        """The terminal record, shaped like lanew_log's (check() counts it), Codex
        diagnostics null; written with lanew_log's own lock + verified append. At most
        once per job (the backstop thread may race the main thread here). latch: the
        stop_latch value (default: any non-ok status latches). An API-backup job's record
        carries via "api" and primary_exit and NEVER latches, whatever ended it (failure,
        interrupt, cancellation, any exception, the backstop): this is the one choke point."""
        with self.term_lock:
            if not self.job_id or self.job_ended:
                return True
            self.job_ended = True
        if self.via == "api":
            latch = False
        ts_end = _now_iso()
        a, b = _parse_iso(self.ts_start), _parse_iso(ts_end)
        entry = {
            "job_id": self.job_id, "run": self.run, "name": self.name, "model": self.model,
            "ts_start": self.ts_start, "ts_end": ts_end, "codex_exit": None,
            "duration_s": round((b - a).total_seconds(), 3) if a and b else None,
            "assistant_message_markers": None, "tokens_used": None, "web_messages": None,
            "usage_complete": True, "status": status, "out_path": None,
            "report_path": self.report, "stop_latch": (status != "ok") if latch is None else latch,
            "tool": TOOL, "exit": code, "submissions": STATE.policy.submissions,
        }
        if self.via == "api":
            entry.update(via="api", primary_exit=self.primary.code)
        ok = lanew_log.append_line_verified(self.usage_log, json.dumps(entry, sort_keys=True) + "\n")
        self.term_ok = bool(ok)
        if not ok:
            log("terminal record could not be verified - usage unknown for job %s." % self.job_id)
        return ok

    # ---- candidates and context memory ------------------------------------------
    def candidates(self):
        exe = shutil.which("browser-harness", path=self.env.get("PATH"))
        if self.key_in(exe):  # it would be the harness child's argv[0]
            raise Exit(2, "preflight_refused", "the browser-harness path contains the API key - "
                       "nothing read")
        cands = read_candidates(self.env, min(HARNESS_TIMEOUT, max(1, int(self.left()))),
                                self.test_context)
        remembered = load_remembered(self.state_dir)
        cands, hit = order_candidates(cands, remembered)
        if hit:
            log("context: trying the remembered context %s first; others only if it fails."
                % cands[0].label)
        return cands

    def remember_context(self):
        if self.test or STATE.expected != self.account or not self.ctx.get("key"):
            return  # test runs never write (or clear) the memory
        if self.key_in(self.state_dir, self.ctx["key"]):  # the memory's path or its content
            log("context memory not updated: the context id or the state dir contains the API key.")
            return
        save_remembered(self.state_dir, self.ctx["key"])

    # ---- the job ----------------------------------------------------------------
    async def status_async(self, cands):
        client = None
        try:
            client = await open_verified(cands, min(INIT_TIMEOUT, max(5.0, self.left())), self.ctx)
            self.account_ok = True
            self.remember_context()
            usage = client.usage_info or {}
            tier = (usage.get("tier") or {}).get("label")
            self.extra = {"account": self.ctx.get("account"), "tier": tier,
                          "models": model_names(client), "credits_5h": credits(usage, "current_5h"),
                          "credits_weekly": credits(usage, "weekly"), "abuse": client.abuse_status}
            log("secrets held in memory for scrubbing: %d value(s), shortest %d chars."
                % (len(_SECRETS), min((len(s) for s in _SECRETS), default=0)))
        finally:
            await safe_close(client)

    def hold(self, text, quiet=False):
        """Validate a completed answer and hold it (raw; each sink scrubs it once).
        quiet: an invalid answer is simply not held (no Exit raised)."""
        text = text or ""
        if not text.strip():
            why = "empty answer"
        elif len(text) < 300 and ERROR_CARD_RE.match(text):
            why = "Gemini returned an error card as text: %s" % scrub(text)[:120]
        else:
            self.answer = text
            return
        if not quiet:
            raise Exit(6, "failed", why)

    async def job_async(self, cands, prompt):
        h = harden()
        from gemini_webapi.exceptions import (ModelInvalidError, TemporarilyBlockedError,
                                              UsageLimitExceededError)
        client = None
        try:
            client = await open_verified(cands, min(INIT_TIMEOUT, max(5.0, self.left())), self.ctx)
            self.account_ok = True
            self.remember_context()
            model = pick_model(client, self.model)
            self.model = model.model_name
            if self.left() < JOB_MIN:
                raise Exit(5, "deadline", "total deadline too close to send (%.0fs left)" % self.left())
            self.admit()
            STATE.policy.deadline = self.deadline  # re-checked inside the guard right before the POST
            STATE.policy.armed = True
            log("sending the brief (%d chars) to %s in a temporary chat." % (len(prompt), self.model))
            output = completed = None
            try:
                await client._sync_activity()
                STATE.after_dispatch.add(client)
                session_state = {"last_texts": {}, "last_thoughts": {}}
                async for chunk in h["raw_generate"](client, prompt=prompt, model=model,
                                                     temporary=True, session_state=session_state):
                    output = chunk
                    # Gemini's own marker on the LATEST frame (the library's is_completed): a
                    # later frame without it un-completes the answer
                    completed = chunk if STATE.completed.get(chunk.rcid) else None
            except (UsageLimitExceededError, TemporarilyBlockedError, ModelInvalidError) as exc:
                # Gemini's own stream error code: positive evidence the request was refused
                raise Exit(6, "failed", "Gemini refused the request (%s) - stop, do not retry"
                           % fmt_exc(exc)[:300])
            except Exception as exc:
                if completed is None or not STATE.policy.submissions:
                    if STATE.policy.submissions:
                        raise Exit(6, "outcome_unknown", "error after dispatch (%s)%s - outcome "
                                   "unknown, not resent" % (fmt_exc(exc)[:300],
                                                            STATE.policy.last_error()))
                    raise Exit(6, "failed", "error before dispatch, no brief submitted: %s"
                               % fmt_exc(exc)[:300])
                # a read / stream-exit error after the completed frame: the answer is whole
                self.notes.append("the stream ended with %s after Gemini marked the answer "
                                  "complete - answer kept" % type(exc).__name__)
                output = completed
            except BaseException:
                if completed is not None:  # a deadline / interrupt / abort after completion
                    self.hold(completed.text, quiet=True)
                raise
            self.hold(output.text if output is not None else "")
        finally:
            await safe_close(client)

    # ---- the API backup (module docstring, "API backup") --------------------------
    def sent(self):
        """Something may have left with the brief: an app-path POST or a started CLI child."""
        return bool(STATE.policy.submissions or self.api_started)

    def backup_applies(self, exc):
        """The trigger: exit 2 / 8 in job mode before admission, nothing dispatched, no answer."""
        return (exc.code in (2, 8) and not self.status_mode and self.job_id is None
                and not STATE.policy.submissions and self.answer is None)

    def api_ready(self, prompt):
        """The preconditions in contract order: (cli, None) or (None, why not)."""
        e = self.env
        if (e.get("GEMINIPRO_API_BACKUP") or "").strip() == "0":
            return None, "GEMINIPRO_API_BACKUP=0"
        key = e.get("GEMINI_API_KEY")
        if key is None:
            return None, "GEMINI_API_KEY is not set"
        if not key.strip():
            return None, "GEMINI_API_KEY is blank"
        if len(key) < SECRET_MIN:
            return None, "GEMINI_API_KEY is too short to be a key"
        if self.key_in(self.api_model):
            return None, "GEMINIPRO_API_MODEL contains the API key"
        explicit = (e.get("GEMINIPRO_API_CLI") or "").strip()
        if explicit:
            if self.key_in(explicit):
                return None, "the CLI path contains the API key"
            if not os.path.isfile(explicit):
                return None, "GEMINIPRO_API_CLI (%s) was not found" % explicit
            cli = explicit
        else:
            cli = shutil.which(API_CLI_NAME, path=e.get("PATH"))
            if not cli:
                return None, "%s is not on PATH" % API_CLI_NAME
            if self.key_in(cli):
                return None, "the CLI path contains the API key"
        if self.left() < JOB_MIN:
            return None, "only %.0fs left before the total deadline (needs %ds)" % (
                max(0.0, self.left()), JOB_MIN)
        if key in prompt or key.strip() in prompt:
            return None, "the brief contains the API key"
        return cli, None

    def api_backup(self, prompt, primary):
        """The app path ended with exit 2 / 8 before admission: send the same gate-passed
        brief once through the CLI. Returns with the answer held, or raises the app path's
        own exit (code and status) with the reason extended."""
        self.primary = primary
        self.trigger = {"backup": "not_run", "primary_exit": primary.code,
                        "primary_reason": primary.reason, "requested_model": self.model}
        if primary.code == 8:
            self.account_ok = False

        def not_run(why):
            log("API backup not run: %s." % why)
            raise Exit(primary.code, primary.status, "%s; API backup not run: %s"
                       % (primary.reason, why))

        cli, why = self.api_ready(prompt)
        if why:
            not_run(why)
        requested = self.model
        try:
            # the policy is chosen before admission: once admit() hands over a job id, every
            # terminal record of this job is unlatched and the status line says api (backup
            # failed until an answer is held)
            self.via, self.trigger["backup"], self.model = "api", "failed", self.api_model
            self.admit()   # the same per-run ceiling and daily cap; the record names the API model
        except BaseException as exc:
            # no job id handed over: fail closed like the app path - no terminal record is
            # written (never for a job id this wrapper was not handed); back to the app path's state
            if self.job_id is None:
                self.via, self.trigger["backup"] = "app", "not_run"
                self.model, self.report = requested, None
                if isinstance(exc, Exit):
                    not_run("admission %s (%s)" % ("refused" if exc.code == 1 else "failed",
                                                  exc.reason))
                if isinstance(exc, Exception):  # any other admission error (interrupts stay)
                    not_run("admission failed (%s)" % fmt_exc(exc)[:200])
            raise
        try:
            try:
                self.api_call(cli, prompt)  # holds a valid answer before any cleanup
            except Exit as exc:      # hold(): an empty answer or an error card
                self.api_fail(exc.reason)
            except ApiFailure as exc:
                self.api_fail(str(exc))
            except Exception as exc:  # anything else after admission is an API failure too
                self.api_fail(fmt_exc(exc))
        finally:
            # housekeeping, after the answer is held, contained: it never changes the result
            # (a failed or interrupted removal leaves api_dir set; finish() tries once more)
            self.housekeeping(self.remove_api_dir)
        log("API backup answered (%d chars) with %s." % (len(self.answer), self.model))

    def housekeeping(self, fn):
        """One cleanup step: whatever it raises - an interrupt included - is contained, so
        housekeeping never changes the result (the original exit code, status and reason
        stand; what is left is noted by the caller). Returns fn()'s value, None if it raised."""
        try:
            return fn()
        except BaseException as exc:  # noqa: B902 - containment is the point
            with contextlib.suppress(BaseException):
                log("cleanup step raised %s - contained; the result stands." % type(exc).__name__)
            return None

    def api_fail(self, text):
        """An API failure after admission: terminal record failed, never latched; the run
        keeps the app path's exit code and status."""
        p = self.primary
        msg = scrub(text)[:API_REASON_MAX]
        self.record_terminal("failed", p.code, latch=False)
        log("API backup failed: %s" % msg)
        raise Exit(p.code, p.status, "%s; API backup failed: %s" % (p.reason, msg))

    def api_call(self, cli, prompt):
        """Write body.json into a new empty directory under the state dir, run the CLI there
        (at most 2 attempts) and hold the answer (hold(): Exit 6 when empty or an error card)
        and set backup ok - all before any cleanup; the caller removes the directory."""
        argv = api_argv(cli)
        self.api_dir = tempfile.mkdtemp(prefix="api-", dir=self.state_dir)
        with open(os.path.join(self.api_dir, API_BODY), "wb") as f:
            f.write(api_body(prompt, self.model))
        log("API backup: the app path ended with exit %d; sending the brief (%d chars) to %s "
            "through %s." % (self.primary.code, len(prompt), self.model, API_CLI_NAME))
        attempt = 0
        while True:
            attempt += 1
            timeout = min(self.api_timeout, self.left() - API_MARGIN)
            if timeout <= 0:
                raise ApiFailure("the total deadline left no time for attempt %d" % attempt)
            self.api_started = True
            try:
                proc = _run_api(argv, cwd=self.api_dir, env=dict(self.env), timeout=timeout,
                                stdin=subprocess.DEVNULL, holder=self.api_holder)
            except subprocess.TimeoutExpired:
                raise ApiFailure("the CLI did not answer within %.0fs (killed)" % timeout)
            except OSError as exc:
                raise ApiFailure("the CLI could not be started (%s)" % fmt_exc(exc))
            if proc.returncode == 0:
                self.hold(api_answer(proc.stdout))
                self.trigger["backup"] = "ok"
                return
            text = api_error_text(proc.returncode, proc.stderr)
            if (attempt < 2 and api_server_error(_json_tail(proc.stderr))
                    and self.left() - API_RETRY_PAUSE >= JOB_MIN):
                log("API backup: attempt 1 hit a server error (%s); one retry in %ds."
                    % (scrub(text)[:200], API_RETRY_PAUSE))
                time.sleep(API_RETRY_PAUSE)
                continue
            raise ApiFailure(text if attempt == 1 else "attempt %d: %s" % (attempt, text))

    def remove_api_dir(self):
        """Remove the body directory (3 tries). api_dir stays set until it is gone, so an
        interrupted or failed attempt is retried on the way out (finish)."""
        d = self.api_dir
        if not d:
            return True
        for i in range(3):  # a just-killed grandchild may hold the directory for a moment
            shutil.rmtree(d, ignore_errors=True)
            if not os.path.exists(d):
                self.api_dir = None
                return True
            if i < 2:
                time.sleep(0.2)
        return False

    def abort_exit(self, exc):
        """Exit for a refused or blocked library action (PolicyAbort / Blocked)."""
        sent = STATE.policy.submissions
        msg = scrub(str(exc))
        if isinstance(exc, DeadlineAbort):
            return Exit(5, "deadline", msg)
        if isinstance(exc, Blocked):
            if sent:
                return Exit(6, "outcome_unknown", "%s after dispatch - outcome unknown, not resent; "
                            "stop, do not retry around it" % msg)
            return Exit(6, "blocked", "%s - no brief submitted; stop, do not retry around it" % msg)
        if sent:
            return Exit(6, "outcome_unknown", "%s - outcome unknown, not resent" % msg)
        return Exit(6, "failed", "%s - no brief submitted" % msg)

    def run_async(self, coro):
        budget = self.left()
        if budget <= 0:
            coro.close()
            raise Exit(5, "deadline", "total deadline reached")
        try:
            return asyncio.run(asyncio.wait_for(coro, timeout=budget))
        except (asyncio.TimeoutError, TimeoutError):
            if self.answer is not None:  # the deadline hit while closing: the answer is kept
                self.notes.append("the total deadline passed while the client closed - answer kept")
                return None
            if STATE.policy.submissions:
                raise Exit(6, "outcome_unknown", "total deadline reached after dispatch - outcome "
                           "unknown, not resent")
            raise Exit(5, "deadline", "total deadline reached before anything was sent")
        except PolicyAbort as exc:
            raise self.abort_exit(exc)

    def write_report(self):
        fields = [scrub(str(v)) for v in (self.run, self.name, self.model, self.job_id)]
        if self.via == "api":
            who = "- account: n/a (API key)\n- via: api (backup; app path exit %d)\n" % self.primary.code
        else:
            who = "- account: %s (context %s)\n" % tuple(
                scrub(str(v)) for v in (self.ctx.get("account"), self.ctx.get("context")))
        body = ("# geminipro report\n\n- run: %s\n- name: %s\n- model: %s\n- job_id: %s\n"
                "%s- written: %s\n\n---\n\n%s\n"
                % tuple(fields + [who, _now_iso(), scrub(self.answer)]))  # each value scrubbed once
        fd = os.open(self.report, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0),
                     0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(body.encode("utf-8"))
        self.report_written = True

    def held_exit(self, what):
        """The exit when something fails after the answer arrived: the answer is kept
        (printed, terminal record ok) - exit 0 when the report and record are safe."""
        if not self.report_written:
            return Exit(3, "log_failure", "answer received (printed here) but %s before the "
                        "report was written" % what)
        if self.job_ended and self.term_ok is not True:
            return Exit(3, "log_failure", "answer received (report %s) but %s before the terminal "
                        "record was confirmed" % (self.report, what))
        return Exit(0, "ok", "answer received (report %s); %s during finalization"
                    % (self.report, what))

    def interrupted(self, during=""):
        if self.answer is not None:
            return self.held_exit("interrupted%s" % during)
        return Exit(130, "interrupted", "interrupted%s%s" % (
            during, " after dispatch - outcome unknown" if self.sent() else " - nothing sent"))

    def main(self):
        self.parse_args()
        self.config()
        if self.status_mode:
            harden()  # library release check before any cookie is read
            cands = self.candidates()
            self.run_async(self.status_async(cands))
            raise Exit(0, "ok", "status read; nothing sent")
        prompt = self.brief_gate(self.read_brief())
        log("brief gate passed (%d chars)." % len(prompt))
        self.take_slot()
        self.precheck()
        try:
            harden()
            cands = self.candidates()
            try:
                self.run_async(self.job_async(cands, prompt))
            except BaseException as exc:  # an Exit / abort / interrupt after the answer arrived
                if self.answer is None:
                    raise
                self.notes.append("%s after the answer arrived - answer kept" % (
                    exc.status if isinstance(exc, Exit) else type(exc).__name__))
        except Exit as exc:
            if not self.backup_applies(exc):
                raise
            try:
                self.api_backup(prompt, exc)  # returns with the answer held, or raises
            except BaseException as late:  # an interrupt / error in cleanup after the answer
                if self.answer is None:
                    raise
                self.notes.append("%s after the API answer arrived - answer kept" % (
                    late.status if isinstance(late, Exit) else type(late).__name__))
        try:
            self.write_report()
        except OSError as exc:
            self.record_terminal("ok", 3)
            raise Exit(3, "log_failure", "answer received (printed here) but the report could not "
                       "be written (%s)" % fmt_exc(exc))
        if not self.record_terminal("ok", 0):
            raise Exit(3, "log_failure", "answer received (report %s) but the terminal record "
                       "could not be verified" % self.report)
        if self.via == "api":
            raise Exit(0, "ok", "answer received through the API backup (app path exit %d: %s)"
                       % (self.primary.code, self.primary.reason))
        raise Exit(0, "ok", "answer received")

    # ---- every exit -------------------------------------------------------------
    def reap_api_child(self):
        """A CLI child still in the holder (its _run_api exit was interrupted before the child
        was confirmed dead) is killed here with its verified descendants: no child outlives
        the wrapper (main() cancels the backstop on the way out)."""
        proc = self.api_holder.get("proc")
        if proc is None:
            return
        _kill_direct(proc)
        _kill_descendants(proc, self.api_holder.get("created"))
        if not _dead(proc):
            with contextlib.suppress(Exception):
                proc.wait(timeout=5)
        if _dead(proc):
            self.api_holder.pop("proc", None)
            self.api_holder.pop("created", None)

    def finish(self, r):
        if r.code == 8:
            self.account_ok = False
        self.housekeeping(self.reap_api_child)
        if self.job_id and not self.job_ended:
            if self.answer is not None:  # an answer in hand is an ok job, whatever came after
                status = "ok"
            elif r.status in ("ok", "failed", "outcome_unknown"):
                status = r.status
            else:
                status = "outcome_unknown" if self.sent() else "failed"
            if not self.record_terminal(status, r.code) and r.code == 0:
                r = Exit(3, "log_failure", "terminal record could not be verified")
        if self.api_dir:  # an earlier removal was interrupted or failed: one more try, contained
            gone = self.housekeeping(self.remove_api_dir)
            if not gone and self.housekeeping(lambda: os.path.exists(self.api_dir)) is not False:
                self.notes.append("the API body directory could not be removed")
        leftover = _HARDENED.get("nocache")  # the check itself is housekeeping too (R3-2)
        if leftover is not None and self.housekeeping(lambda: os.path.exists(str(leftover))):
            self.notes.append("INVARIANT: the no-cache dir was created")
            self.housekeeping(lambda: shutil.rmtree(str(leftover), ignore_errors=True))
        if any(STATE.spy.values()):
            self.housekeeping(lambda: log("library cache/rotation calls neutralized: %s" % STATE.spy))
        return r

    def status_line(self, r):
        notes = self.notes + STATE.notes
        reason = r.reason + (" (%s)" % "; ".join(notes) if notes else "")
        n = lambda v: v or None  # noqa: E731
        d = {"tool": TOOL, "exit": r.code, "status": r.status, "reason": reason,
             "run": n(self.run), "name": n(self.name), "model": n(self.model),
             "job_id": n(self.job_id), "report": n(self.report), "account_ok": self.account_ok,
             "duration_s": round(time.monotonic() - self.t0, 3),
             "submissions": STATE.policy.submissions,
             "context": None if self.via == "api" else self.ctx.get("context"), "via": self.via}
        if self.trigger:
            d.update(self.trigger)
        if self.status_mode:
            d.update({"account": self.ctx.get("account")})
            d.update(self.extra)
        return json.dumps(scrub_obj(d))  # leaves scrubbed once; the JSON text is never scrubbed

    def emit(self, r, hard=False):
        """The answer / status summary, then the one status line in its own step: a
        failed or interrupted body write never costs the line. hard=True (the backstop,
        or the retry after an interrupt mid-emission) never waits on a lock and writes
        straight to the fds. `emitted` is set only after the line write was attempted."""
        if hard:
            if not self.emit_lock.acquire(blocking=False):
                return  # the main thread is emitting
        else:
            self.emit_lock.acquire()
        try:
            if self.emitted:
                return
            show_answer = self.answer is not None and not (self.json_mode and r.code == 0)
            if hard:
                if show_answer and not self.body_done:
                    self.body_done = True
                    with contextlib.suppress(OSError, ValueError):
                        os.write(2 if self.json_mode else 1, self._answer_bytes())
                line = self.status_line(r)
                with contextlib.suppress(OSError, ValueError):
                    os.write(1 if self.json_mode else 2, (line + "\n").encode("utf-8"))
                self.emitted = True
                return
            if not self.body_done:
                what = "the answer" if show_answer else "the status summary"
                try:
                    if self.status_mode and r.code == 0 and not self.json_mode:
                        self.print_status_summary()
                    elif show_answer:
                        # an answer in hand is never dropped: stdout, or stderr under --json
                        self.print_answer(sys.stderr if self.json_mode else sys.stdout)
                except (OSError, ValueError, KeyboardInterrupt) as exc:
                    self.notes.append("%s could not be printed (%s)" % (what, type(exc).__name__))
                finally:
                    self.body_done = True
            line = self.status_line(r)
            with contextlib.suppress(OSError, ValueError):
                print(line, file=sys.stdout if self.json_mode else sys.stderr, flush=True)
            self.emitted = True
        finally:
            self.emit_lock.release()

    def _answer_bytes(self):
        text = scrub(self.answer)  # the answer is held raw: scrubbed once, here, per sink
        return (text if text.endswith("\n") else text + "\n").encode("utf-8")

    def print_answer(self, stream):
        text = scrub(self.answer)  # the answer is held raw: scrubbed once, here, per sink
        text = text if text.endswith("\n") else text + "\n"
        out = getattr(stream, "buffer", None)
        stream.flush()
        if out is not None:
            out.write(text.encode("utf-8"))
            out.flush()
        else:
            stream.write(text)
            stream.flush()

    def print_status_summary(self):
        x = scrub_obj(self.extra)  # every leaf scrubbed once; the text below is not re-scrubbed
        def cr(c):
            if not c:
                return "unknown"
            return "%s (used %s%%, resets %s)" % (c.get("remaining_credits"), c.get("usage_percentage"),
                                                  c.get("reset_at"))
        ab = x.get("abuse") or {}
        lines = ["account: %s (verified from gemini.google.com/app, context %s)"
                 % (x.get("account"), scrub_obj(self.ctx.get("context"))),
                 "tier: %s" % x.get("tier"),
                 "models: %s" % ", ".join(str(m) for m in x.get("models") or []),
                 "5h remaining credits: %s" % cr(x.get("credits_5h")),
                 "weekly remaining credits: %s" % cr(x.get("credits_weekly")),
                 "abuse status: %s" % ("clean" if ab.get("is_clean") else json.dumps(ab))]
        print("\n".join(lines), flush=True)

    def backstop(self):
        """Fires at deadline + BACKSTOP_GRACE: terminal record and status line on side
        threads (bounded waits, no lock held), then a hard exit. A live API child is killed
        first - the direct child synchronously, then its verified descendants (_kill_descendants
        with the creation time recorded at start, waited KILL_WAIT; the kill step is bounded by
        about KILL_WAIT) -
        and only then the body directory is removed: no child outlives the wrapper. An
        admitted API job with no answer exits with the app path's code and status, unlatched."""
        proc, created = self.api_holder.get("proc"), self.api_holder.get("created")
        if proc is not None:
            with contextlib.suppress(Exception):
                proc.kill()  # the direct child, synchronously, before anything else
            with contextlib.suppress(Exception):  # cleanup: never skips the line or the hard exit
                _side(lambda: _kill_descendants(proc, created), KILL_WAIT)
        if self.api_dir:
            with contextlib.suppress(Exception):
                shutil.rmtree(self.api_dir, ignore_errors=True)
        sent = self.sent()
        if self.answer is not None:  # an answer in hand is printed and recorded ok
            code, status, term = 3, "log_failure", "ok"
            why = ("hard backstop: answer received (printed here) but finalization overran the "
                   "total deadline")
        elif self.via == "api":  # never latched (record_terminal), the app path's own exit
            p = self.primary
            code, status, term = p.code, p.status, "failed"
            why = "%s; API backup failed: hard backstop: the process overran the total deadline" % (
                p.reason)
        else:
            code = 6 if sent else 5
            status = "outcome_unknown" if sent else "deadline"
            term = "outcome_unknown" if sent else "failed"
            why = "hard backstop: the process overran the total deadline"
        if self.job_id and not self.job_ended:
            _side(lambda: self.record_terminal(term, code), 5)
        _side(lambda: self.emit(Exit(code, status, why), hard=True), 5)
        HARD_EXIT(code)


def _sigbreak(_signum, _frame):
    raise KeyboardInterrupt


def main(argv=None, env=None):
    STATE.new_run()
    w = Wrapper(sys.argv[1:] if argv is None else argv, os.environ if env is None else env)
    if hasattr(signal, "SIGBREAK") and threading.current_thread() is threading.main_thread():
        with contextlib.suppress(ValueError, OSError):
            signal.signal(signal.SIGBREAK, _sigbreak)
    timer = None
    result = final = None
    try:
        try:
            timer = threading.Timer(max(0.0, w.deadline + BACKSTOP_GRACE - time.monotonic()),
                                    w.backstop)
            timer.daemon = True
            timer.start()
            try:
                w.main()
                result = Exit(3, "internal_error", "wrapper ended without a result")
            except Exit as e:
                result = e
            except (KeyboardInterrupt, asyncio.CancelledError):
                result = w.interrupted()
            except PolicyAbort as e:
                result = (w.held_exit(type(e).__name__) if w.answer is not None
                          else w.abort_exit(e))
            except Exception as e:
                log("internal error: %s%s" % (fmt_exc(e)[:300], _frames(e)))
                if w.answer is not None:
                    result = w.held_exit("an internal error (%s)" % fmt_exc(e)[:300])
                else:
                    result = Exit(6 if w.job_id else 2, "outcome_unknown" if STATE.policy.submissions
                                  else "internal_error", "internal error: %s" % fmt_exc(e)[:300])
            # finalization inside the same cancellation-aware boundary, watchdog still armed
            try:
                result = w.finish(result)
            except (KeyboardInterrupt, asyncio.CancelledError):
                result = w.interrupted(" during finalization")
            except Exception as e:
                result = Exit(3, "log_failure", "finalization failed: %s" % fmt_exc(e)[:300])
        except (KeyboardInterrupt, asyncio.CancelledError):  # a second interrupt mid-handling
            result = w.interrupted()
            with contextlib.suppress(BaseException):
                result = w.finish(result)
    finally:
        final = result if result is not None else w.interrupted()
        try:
            with contextlib.suppress(BaseException):  # the OS frees the lock at exit anyway
                if w.lock is not None:
                    w.lock.release()
            # the status line in its own protected step, inside the interrupt-aware boundary
            try:
                w.emit(final)
            except BaseException:  # interrupted mid-emission: one lock-free retry of the line
                with contextlib.suppress(BaseException):
                    w.emit(final, hard=True)
        finally:
            if timer is not None:
                timer.cancel()
    return final.code


if __name__ == "__main__":
    sys.exit(main())
