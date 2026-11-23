"""t3-pick-login: which Claude login (T3 provider instance) the next Claude build seat should use.

Read-only. Picks the session's own login while it is under the threshold, else the least-used of
JC's other logins: PERSONAL ones (claude_max / claude_pro) that cannot bill extra usage, and Team
seats (claude_team) whose pay-as-you-go is capped and known to be under 90% of the cap; every pick's
settings must not send prompts anywhere but Anthropic. The built-in claudeAgent is never an overflow
candidate. Usage comes from a file the lead saved from ~/bin/claude-usage.py; this script never runs
it, never touches the network and never starts a subprocess.

Never prints a token, an email, a cap / spend amount, or any value from a credentials / .claude.json /
settings / usage file: output names instance ids, files, fields and variable names only.

Exit 0 picked, 3 none usable, 2 bad input or internal error (one stderr line, never a value).
"""
import argparse
import decimal
import json
import math
import os
import re
import stat
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PERSONAL_ORGS = frozenset({"claude_max", "claude_pro"})
TEAM_ORG = "claude_team"
TEAM_SPEND_TENTHS = 9                     # a Team seat's spend must stay under 9/10 of its cap (exact)
USAGE_MAX_AGE = timedelta(minutes=30)     # Team: the --usage-json file's age limit
REMOTE_MAX_AGE = timedelta(hours=24)      # Team: remote-settings.json cache age limit
GATED_PREFIX = "OTEL_"
GATED_PREFIXES = (GATED_PREFIX, "CLAUDE_CODE_MANAGED")
GATED_ENV = frozenset({
    "CLAUDE_CODE_ENABLE_TELEMETRY", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL",
    "ANTHROPIC_BEDROCK_BASE_URL", "ANTHROPIC_VERTEX_BASE_URL", "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY", "HTTPS_PROXY", "HTTP_PROXY",
    "CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR",
    "CLAUDE_CODE_API_KEY_FILE_DESCRIPTOR", "ANTHROPIC_CUSTOM_HEADERS", "CLAUDE_CONFIG_DIR",
})
ENV_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}")
INSTANCE_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")
HELPER_KEYS = ("apiKeyHelper", "otelHeadersHelper", "awsAuthRefresh", "awsCredentialExport")
REMOTE_SETTINGS = "remote-settings.json"
PRIVACY_FILES = (REMOTE_SETTINGS, "managed-settings.json")
SETTINGS_FILES = ("settings.json", "settings.local.json")
BUILTIN = "claudeAgent"
# T3 instance fields that change how the child launches (env, binary, args).
T3_LAUNCH_FIELDS = (("environment", None), ("binaryPath", "config"), ("launchArgs", "config"))
USAGE_MAX = 1000

# T3 Code managed policy (server.asar managedPolicyPath / WINDOWS_POLICY_SUBKEY, T3 build 2026-11-20).
T3_POLICY_FILE = {"win32": r"C:\Program Files\T3Code\policy.json",
                  "darwin": "/Library/Application Support/T3Code/policy.json"}.get(sys.platform,
                                                                                  "/etc/t3code/policy.json")
T3_POLICY_REG_SUBKEY = r"SOFTWARE\Policies\T3Tools\T3Code"
T3_HOME_ENV = "T3CODE_HOME"  # supported envelope: the default T3 profile (~/.t3)
CONFIG_DIR_ENV = "CLAUDE_CONFIG_DIR"

# Claude Code machine managed settings (F3): presence, never content. The dirs cover
# managed-settings.json, managed-mcp.json and any drop-in dir; ProgramData is the legacy path.
CC_MANAGED_DIRS = (r"C:\Program Files\ClaudeCode", r"C:\ProgramData\ClaudeCode")
CC_POLICY_REG_SUBKEY = r"SOFTWARE\Policies\ClaudeCode"

MISSING = object()   # file absent / key absent
# The only errors that confirm a path is absent; any other probe error is undetermined (fail closed).
ABSENT_ERRORS = (FileNotFoundError, NotADirectoryError)
BAD = object()       # file unreadable or not valid JSON


class BadInput(Exception):
    """Exit 2; the message is fixed text naming the bad input only (never a value read from it)."""


def is_gated(name):
    n = str(name).upper()
    return n.startswith(GATED_PREFIXES) or n in GATED_ENV


def config_dir_in_env():
    """True when CLAUDE_CONFIG_DIR is in the picker's own environment, with any value."""
    return any(str(name).upper() == CONFIG_DIR_ENV for name in os.environ)


def safe_env_name(name):
    """The key itself when it looks like an env name, else a fixed placeholder."""
    if isinstance(name, str) and ENV_NAME_RE.fullmatch(name):
        return name
    return "OTEL_*" if str(name).upper().startswith(GATED_PREFIX) else "env"


def _reject_constant(name):
    raise ValueError("non-finite JSON constant")


def loads_strict(text):
    """json.loads that rejects NaN / Infinity / -Infinity (raises ValueError)."""
    return json.loads(text, parse_constant=_reject_constant)


def read_json(path):
    """Parsed JSON, MISSING only on confirmed absence, BAD when unreadable or invalid."""
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except ABSENT_ERRORS:
        return MISSING
    except (OSError, ValueError):
        return BAD
    try:
        return loads_strict(text)
    except (ValueError, RecursionError):
        return BAD


def safe_exists(path):
    """lstat probe: True present (a dangling link counts), False only on confirmed absence,
    None when undetermined."""
    try:
        Path(path).lstat()
        return True
    except ABSENT_ERRORS:
        return False
    except (OSError, ValueError):
        return None


def mtime_of(path):
    """Aware UTC mtime (follows links), or None when it cannot be read."""
    try:
        return datetime.fromtimestamp(Path(path).stat().st_mtime, timezone.utc)
    except (OSError, ValueError, OverflowError):
        return None


def finite_number(v):
    """v as a finite float when it is a JSON number (not a bool), else None."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    try:
        f = float(v)
    except OverflowError:
        return None
    return f if math.isfinite(f) else None


def exact(v):
    """A finite JSON number as an exact Decimal of its shortest repr (G2: no float rounding)."""
    return decimal.Decimal(repr(v))


def resolve_home(path):
    """A home that must exist: its strict-resolved Path when it is a directory, else None."""
    try:
        real = Path(path).resolve(strict=True)
        return real if stat.S_ISDIR(real.lstat().st_mode) else None
    except (OSError, ValueError, RuntimeError):
        return None


def valid_id(value):
    return isinstance(value, str) and INSTANCE_ID_RE.fullmatch(value) is not None


def _resolve_strict(path):
    """(resolved Path, None), (None, 'absent') on confirmed absence (lstat), (None, None) otherwise."""
    try:
        return Path(path).resolve(strict=True), None
    except (OSError, ValueError, RuntimeError):
        pass
    return None, ("absent" if safe_exists(path) is False else None)


def same_dir(a, b):
    """True / False, or None when undetermined (callers fail closed). Both paths are resolved
    strictly; one confirmed absent while the other exists -> False; anything else unresolvable -> None."""
    ra, why_a = _resolve_strict(a)
    rb, why_b = _resolve_strict(b)
    if ra is not None and rb is not None:
        return os.path.normcase(str(ra)) == os.path.normcase(str(rb))
    if (ra is not None and why_b == "absent") or (rb is not None and why_a == "absent"):
        return False
    return None


def parse_aware(value):
    """Aware UTC datetime, or None for naive / malformed / out-of-range / non-string."""
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.strip())
        if dt.tzinfo is None or dt.utcoffset() is None:
            return None
        return dt.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return None


def window_value(v):
    """A usage window value when it is a finite number in 0..USAGE_MAX, else None."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v if 0 <= v <= USAGE_MAX else None


def is_set(v):
    """A launch field counts as set unless it is absent, null or empty."""
    if v is None or v is MISSING:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (list, dict)):
        return bool(v)
    return True


def canon(x):
    """JSON-aware form for equality (true != 1)."""
    return "<missing>" if x is MISSING else json.dumps(x, sort_keys=True)


def hooks_of(data):
    return data.get("hooks", MISSING) if isinstance(data, dict) else MISSING


def hooks_differ(mine, ref_data):
    if ref_data is BAD or (ref_data is not MISSING and not isinstance(ref_data, dict)):
        return True
    return canon(mine) != canon(hooks_of(ref_data))


def has_http_hook(obj):
    if isinstance(obj, dict):
        if str(obj.get("type", "")).lower() == "http":
            return True
        return any(has_http_hook(v) for v in obj.values())
    if isinstance(obj, list):
        return any(has_http_hook(v) for v in obj)
    return False


def settings_reason(data, fname):
    """Check 6 on one parsed settings file. Returns 'privacy:...' or None."""
    if data is MISSING:
        return None
    if not isinstance(data, dict):
        return f"privacy:unreadable:{fname}"
    env = data.get("env", {})
    if env is None:
        env = {}
    if not isinstance(env, dict):
        return f"privacy:{fname}:env"
    for name in sorted(env, key=str):
        if is_gated(name):
            return f"privacy:{fname}:{safe_env_name(name)}"
    for key in HELPER_KEYS:
        if key in data:
            return f"privacy:{fname}:{key}"
    return None


# ---- T3 managed policy: presence, never content ----------------------------------------------
def registry_policy_present():
    """True when the T3 policy key exists in HKLM (64- or 32-bit view) or cannot be ruled out;
    False only when every view answers "not found". Always False off Windows."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
    except ImportError:
        return True
    for view in (getattr(winreg, "KEY_WOW64_64KEY", 0), getattr(winreg, "KEY_WOW64_32KEY", 0)):
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, T3_POLICY_REG_SUBKEY, 0, winreg.KEY_READ | view)
        except FileNotFoundError:
            continue
        except OSError:
            return True
        winreg.CloseKey(key)
        return True
    return False


def t3_policy_present(runtime_path):
    """Any T3 managed policy (file, registry key, or the running server's managedPolicy), or a
    source that cannot be checked -> True. Reads only the runtime file's managedPolicy field."""
    if safe_exists(T3_POLICY_FILE) is not False or registry_policy_present():
        return True
    runtime = read_json(runtime_path)
    return not isinstance(runtime, dict) or runtime.get("managedPolicy", MISSING) is not None


# ---- Claude Code machine managed settings: presence, never content (F3) -------------------
def cc_registry_present():
    """True when the Claude Code policy key exists in HKLM (64- or 32-bit view) or HKCU, or cannot
    be ruled out; False only when every probe answers "not found". Off Windows: True."""
    if sys.platform != "win32":
        return True
    try:
        import winreg
    except ImportError:
        return True
    probes = ((winreg.HKEY_LOCAL_MACHINE, getattr(winreg, "KEY_WOW64_64KEY", 0)),
              (winreg.HKEY_LOCAL_MACHINE, getattr(winreg, "KEY_WOW64_32KEY", 0)),
              (winreg.HKEY_CURRENT_USER, 0))
    for root, view in probes:
        try:
            key = winreg.OpenKey(root, CC_POLICY_REG_SUBKEY, 0, winreg.KEY_READ | view)
        except FileNotFoundError:
            continue
        except OSError:
            return True
        winreg.CloseKey(key)
        return True
    return False


def cc_managed_present():
    """Any Claude Code managed-settings source present or not ruled out -> True. Off Windows
    always True (MDM / plist / system sources are outside the envelope)."""
    if sys.platform != "win32":
        return True
    return any(safe_exists(p) is not False for p in CC_MANAGED_DIRS) or cc_registry_present()


class Ctx:
    def __init__(self, args, now):
        self.now = now
        self.threshold = args.threshold
        home = Path.home()
        self.default_main = home / ".claude"
        self.main_home = Path(args.main_home).expanduser() if args.main_home else self.default_main
        # an absent default home (confirmed by lstat) is never the main home; else strict compare
        self.main_is_default = (False if safe_exists(self.default_main) is False
                                else same_dir(self.main_home, self.default_main))
        self.slots_dir = Path(args.slots_dir).expanduser() if args.slots_dir else home / ".claude-slots"
        self.t3_path = Path(args.t3_settings).expanduser() if args.t3_settings else home / ".t3" / "userdata" / "settings.json"
        self.t3_runtime = (Path(args.t3_runtime).expanduser() if args.t3_runtime
                           else home / ".t3" / "userdata" / "server-runtime.json")
        lr = args.launch_root.strip()
        self.launch_root = Path(lr).expanduser() if lr else None

        t3 = read_json(self.t3_path)
        if not isinstance(t3, dict) or not isinstance(t3.get("providerInstances"), dict):
            raise BadInput("--t3-settings: missing, unreadable or without a providerInstances object")
        # keys that are not valid instance ids are ignored (and so never echoed)
        self.instances = {k: v for k, v in t3["providerInstances"].items() if valid_id(k)}

        rot = read_json(self.slots_dir / "rotation.json")
        if not isinstance(rot, dict) or not isinstance(rot.get("order"), list):
            raise BadInput("--slots-dir: rotation.json missing, unreadable or without an order list")
        self.order, self.rot_email = [], {}
        for entry in rot["order"]:
            if not isinstance(entry, dict):
                raise BadInput("--slots-dir: rotation.json order entry is not an object")
            iid = entry.get("instanceId")
            if not valid_id(iid):  # blank, non-string, absent or off-pattern: one message
                raise BadInput("rotation.json order entry has an invalid instanceId")
            if not isinstance(entry.get("email"), str):
                raise BadInput("--slots-dir: rotation.json order entry has no string email")
            if iid in self.rot_email:
                continue
            self.order.append(iid)
            email = entry["email"]
            self.rot_email[iid] = email.strip().lower() if email.strip() else None

        limits = read_json(self.slots_dir / "limits.json")
        # A limits.json that exists but cannot be read fails closed: every login counts as limited.
        self.limits = {} if limits is MISSING else (limits if isinstance(limits, dict) else None)

        usage_path = Path(args.usage_json).expanduser()
        usage = read_json(usage_path)
        if not isinstance(usage, list):
            raise BadInput("--usage-json: missing, unreadable or not a JSON list")
        self.usage_mtime = mtime_of(usage_path)
        self.used_by_email, self.rows_by_email = {}, {}
        for row in usage:
            if not isinstance(row, dict) or not isinstance(row.get("email"), str):
                continue
            self.rows_by_email.setdefault(row["email"].strip().lower(), []).append(row)
            present = [row[k] for k in ("5h", "week") if row.get(k) is not None]
            vals = [window_value(v) for v in present]
            # one invalid window makes the whole row unknown (never the max of the valid ones)
            if not vals or any(v is None for v in vals):
                continue
            key = row["email"].strip().lower()
            used = int(round(max(vals)))
            self.used_by_email[key] = max(used, self.used_by_email.get(key, used))

        self.main_settings = {f: read_json(self.main_home / f) for f in SETTINGS_FILES}
        self.dup_ids = self.duplicate_home_ids()
        self.team_used = {}

    def raw_home(self, iid):
        """The unresolved home path an id would launch with (built-in: --main-home), or None when
        the id has no launchable claudeAgent instance with a home path."""
        if iid == BUILTIN:
            return self.main_home
        inst = self.instances.get(iid)
        if not isinstance(inst, dict) or inst.get("driver") != "claudeAgent" or inst.get("enabled") is not True:
            return None
        cfg = inst.get("config")
        hp = cfg.get("homePath") if isinstance(cfg, dict) else None
        if not isinstance(hp, str) or not hp.strip():
            return None
        try:
            return Path(hp).expanduser()
        except (RuntimeError, ValueError, OSError):
            return MISSING  # undeterminable

    def duplicate_home_ids(self):
        """G1: rotation ids whose homes are the same directory as another rotation id's home;
        an undeterminable comparison counts as the same directory (fail closed)."""
        homes = [(iid, self.raw_home(iid)) for iid in self.order]
        homes = [(iid, h) for iid, h in homes if h is not None]
        dups = set()
        for i, (a, ha) in enumerate(homes):
            for b, hb in homes[i + 1:]:
                same = None if ha is MISSING or hb is MISSING else same_dir(ha, hb)
                if same is not False:
                    dups.update((a, b))
        return dups

    # ---- per-login facts -------------------------------------------------------------------
    def home_of(self, iid):
        """(home directory, None) of an enabled claudeAgent instance, or (None, reason).
        Envelope: the built-in uses --main-home and must not carry any config.homePath key."""
        inst = self.instances.get(iid)
        if not isinstance(inst, dict) or inst.get("driver") != "claudeAgent" or inst.get("enabled") is not True:
            return None, "no-home"
        cfg = inst.get("config", MISSING)
        if cfg is MISSING or cfg is None:
            cfg = {}
        if not isinstance(cfg, dict):
            return None, "no-home"
        if iid == BUILTIN:
            if "homePath" in cfg:
                return None, "no-home:envelope"
            home = self.main_home
        else:
            hp = cfg.get("homePath")
            if not isinstance(hp, str) or not hp.strip():
                return None, "no-home"
            try:
                home = Path(hp).expanduser()
            except (RuntimeError, ValueError, OSError):
                return None, "no-home"
        real = resolve_home(home)
        return (real, None) if real is not None else (None, "no-home")

    def locate(self, iid):
        """((home, account file, is_main), None), or (None, 'no-home' / 'no-home:ambiguous' /
        'no-home:envelope')."""
        home, reason = self.home_of(iid)
        if home is None:
            return None, reason
        is_main = same_dir(home, self.main_home)
        if is_main is None:
            return None, "no-home"
        if is_main and iid != BUILTIN:
            return None, "no-home:ambiguous"
        if is_main and self.main_is_default is None:
            return None, "no-home"
        if is_main and self.main_is_default:
            return (home, self.default_main.parent / ".claude.json", True), None
        return (home, home / ".claude.json", is_main), None

    @staticmethod
    def account_of(account_file):
        data = read_json(account_file)
        if not isinstance(data, dict):
            return None
        acct = data.get("oauthAccount")
        return acct if isinstance(acct, dict) else {}

    def used_of(self, iid):
        email = self.rot_email.get(iid)
        return self.used_by_email.get(email) if email else None

    def fresh(self, mtime, max_age):
        """mtime known and not older than max_age before now (a future mtime is not fresh)."""
        return mtime is not None and timedelta(0) <= self.now - mtime <= max_age

    # ---- checks (one function each) --------------------------------------------------------
    def check_t3_instance(self, iid):
        """S7: a candidate's T3 instance must not set launch env / binary / args; an entry that
        is not an object, or a present config that is not an object, fails closed."""
        inst = self.instances.get(iid)
        if not isinstance(inst, dict) or ("config" in inst and not isinstance(inst["config"], dict)):
            return "privacy:t3-instance:config"
        cfg = inst.get("config")
        for field, where in T3_LAUNCH_FIELDS:
            src = inst if where is None else cfg
            if isinstance(src, dict) and is_set(src.get(field)):
                return f"privacy:t3-instance:{field}"
        return None

    def check_identity(self, iid, acct):
        if acct is None:
            return "unreadable:.claude.json"
        email = acct.get("emailAddress")
        want = self.rot_email.get(iid)
        if iid not in self.rot_email or not want or not isinstance(email, str) or email.strip().lower() != want:
            return "identity-mismatch"
        return None

    @staticmethod
    def check_org(acct):
        org = acct.get("organizationType")
        if org is None:
            return "org:missing"
        if not isinstance(org, str):
            return "org:unknown"
        if org in PERSONAL_ORGS or org == TEAM_ORG:
            return None
        if "enterprise" in org.lower():
            return "org:enterprise"
        return "org:unknown"

    @staticmethod
    def check_money(acct):
        return None if acct.get("hasExtraUsageEnabled") is False else "money:extra-usage"

    def team_rows(self, iid, home):
        """G3: the usage rows of this Team slot - slot field equal to the home's directory name
        (home a direct child of --slots-dir) and email equal to rotation's; None when unbound."""
        email = self.rot_email.get(iid)
        if not email or same_dir(home.parent, self.slots_dir) is not True:
            return None
        return [r for r in self.rows_by_email.get(email, []) if r.get("slot") == home.name]

    def check_team_money(self, iid, home):
        """F4b (replaces check 4 for a claude_team candidate): passes only on a known, capped,
        under-90% pay-as-you-go state from a fresh usage file; else the first failing label.
        On a pass, records the slot-bound row's used value in team_used (G3)."""
        rows = self.team_rows(iid, home)
        if not rows:
            return "money:team-unknown"
        # two slot-bound rows that disagree (extra or either window) -> invalid
        sigs = {(canon(r.get("extra", MISSING)), canon(r.get("5h", MISSING)), canon(r.get("week", MISSING)))
                for r in rows}
        if len(sigs) != 1 or not isinstance(rows[0].get("extra"), dict):
            return "money:team-unknown"
        row, extra = rows[0], rows[0]["extra"]
        if extra.get("cap") is None:
            return "money:team-uncapped"
        cap = finite_number(extra["cap"])
        if cap is None or cap <= 0:
            return "money:team-unknown"
        spent = finite_number(extra.get("spent"))
        if spent is None or spent < 0:
            return "money:team-unknown"
        reached = extra.get("cap_reached", MISSING)
        if reached is True:
            return "money:team-cap"
        if reached is not False:
            return "money:team-unknown"
        if exact(extra["spent"]) * 10 >= exact(extra["cap"]) * TEAM_SPEND_TENTHS:  # G2: exact
            return "money:team-cap"
        windows = (window_value(row.get("5h")), window_value(row.get("week")))
        if any(v is None for v in windows):
            return "money:team-unknown"
        if not self.fresh(self.usage_mtime, USAGE_MAX_AGE):
            return "money:team-stale-usage"
        self.team_used[iid] = int(round(max(windows)))
        return None

    def check_privacy_files(self, home, team=False):
        """Check 5. A Team candidate's remote-settings.json must also be present (never fetched =
        unknown) and written within REMOTE_MAX_AGE (F4c)."""
        for fname in PRIVACY_FILES:
            path = home / fname
            exists = safe_exists(path)
            if exists is None:
                return f"privacy:{fname}"
            if not exists:
                if team and fname == REMOTE_SETTINGS:
                    return "privacy:remote-settings.json:absent"
                continue
            try:
                text = path.read_text(encoding="utf-8-sig").strip()
            except (OSError, ValueError):
                return f"privacy:{fname}"
            if text not in ("", "{}"):
                return f"privacy:{fname}"
            if team and fname == REMOTE_SETTINGS and not self.fresh(mtime_of(path), REMOTE_MAX_AGE):
                return "privacy:remote-settings.json:stale"
        return None

    @staticmethod
    def check_settings(home):
        for fname in SETTINGS_FILES:
            reason = settings_reason(read_json(home / fname), fname)
            if reason:
                return reason
        return None

    def check_hooks(self, home, is_main):
        for fname in SETTINGS_FILES:
            mine = hooks_of(read_json(home / fname))
            if has_http_hook(mine):
                return f"privacy:http-hook:{fname}"
            if is_main:
                continue
            if hooks_differ(mine, self.main_settings[fname]):
                return f"privacy:hooks:{fname}"
        return None

    def check_limited(self, iid):
        if self.limits is None:
            return "limits:malformed"
        if iid not in self.limits:
            return None
        until = parse_aware(self.limits[iid])
        if until is None:
            return "limits:malformed"
        return "limited" if self.now < until else None

    def candidate_reason(self, iid):
        """First failing check for an overflow candidate, or None."""
        if iid == BUILTIN:  # F1a: the built-in may inherit the T3 server's env, invisible here
            return "no-home:builtin"
        loc, reason = self.locate(iid)
        if loc is None:
            return reason
        if iid in self.dup_ids:  # G1
            return "no-home:duplicate"
        home, account_file, is_main = loc
        t3_reason = self.check_t3_instance(iid)
        if t3_reason:
            return t3_reason
        acct = self.account_of(account_file)
        reason = self.check_identity(iid, acct) or self.check_org(acct)
        if reason:
            return reason
        team = acct.get("organizationType") == TEAM_ORG
        return ((self.check_team_money(iid, home) if team else self.check_money(acct))
                or self.check_privacy_files(home, team) or self.check_settings(home)
                or self.check_hooks(home, is_main) or self.check_limited(iid))

    def current_state(self, iid):
        """(first failing of checks 1, 2, 4 or None, extra-usage state)."""
        if iid == BUILTIN and config_dir_in_env():  # F1b: outside the envelope
            return "no-home:envelope", "unknown"
        loc, reason = self.locate(iid)
        if loc is None:
            return reason, "unknown"
        if iid in self.dup_ids:  # G1
            return "no-home:duplicate", "unknown"
        acct = self.account_of(loc[1])
        extra = "unknown"
        if acct is not None:
            flag = acct.get("hasExtraUsageEnabled")
            extra = "off" if flag is False else ("on" if flag is True else "unknown")
        return (self.check_identity(iid, acct) or self.check_money(acct)), extra

    def config_dir_is_current(self, value, current):
        """E4: CLAUDE_CONFIG_DIR names the current instance's located home (strict resolve).
        Never for a built-in current (F1b)."""
        if current == BUILTIN or not isinstance(value, str) or not value.strip():
            return False
        loc, _ = self.locate(current)
        return loc is not None and same_dir(value, loc[0]) is True

    def process_env_gated(self, current):
        for name, value in os.environ.items():
            if not is_gated(name):
                continue
            if str(name).upper() == CONFIG_DIR_ENV and self.config_dir_is_current(value, current):
                continue
            return True
        return False

    def global_reasons(self, current):
        reasons = []
        if self.process_env_gated(current):
            reasons.append("privacy:process-env")
        # E3: a T3 run from a non-default profile is outside the supported envelope
        if any(str(name).upper() == T3_HOME_ENV for name in os.environ):
            reasons.append("privacy:t3-home")
        if t3_policy_present(self.t3_runtime):
            reasons.append("privacy:t3-policy")
        if cc_managed_present():
            reasons.append("privacy:cc-managed")
        # F2b: the launch root must be an absolute path that strict-resolves to an existing directory
        if (self.launch_root is None or not self.launch_root.is_absolute()
                or resolve_home(self.launch_root) is None):
            reasons.append("privacy:launch-root:missing")
            return reasons
        lr_claude = self.launch_root / ".claude"
        for fname in SETTINGS_FILES:
            data = read_json(lr_claude / fname)
            r = settings_reason(data, fname)
            if r:
                reasons.append("privacy:launch-root:" + r[len("privacy:"):])
            hooks = hooks_of(data)
            if has_http_hook(hooks):
                reasons.append(f"privacy:http-hook:.claude/{fname}")
            if hooks is MISSING:
                continue
            if hooks_differ(hooks, self.main_settings[fname]):
                reasons.append(f"privacy:launch-root-hooks:{fname}")
        return reasons


def pick(ctx, current, only):
    refused = []
    cur_fail, cur_extra = ctx.current_state(current)
    verified = cur_fail is None
    cur_used = ctx.used_of(current)
    cur_reason = cur_fail or ctx.check_limited(current)
    if cur_reason is None and cur_used is not None and cur_used >= ctx.threshold:
        cur_reason = "near-limit"
    result = {"current_verified": verified, "current_extra_usage": cur_extra}
    if cur_reason is None:
        picked = "current-ok" if cur_used is not None else "current-unknown"
        result.update(instance=current, reason=picked, used=cur_used, current_reason=picked)
    else:
        result["current_reason"] = cur_reason
        refused.append({"instance": current, "reason": cur_reason})

    globals_ = ctx.global_reasons(current)
    refused.extend({"instance": "*", "reason": r} for r in globals_)
    eligible = []
    if not globals_:
        for iid in ctx.order:
            if iid == current or (only is not None and iid not in only):
                continue
            reason = ctx.candidate_reason(iid)
            used = ctx.team_used[iid] if iid in ctx.team_used else ctx.used_of(iid)
            if reason is None and used is not None and used >= ctx.threshold:
                reason = "near-limit"
            if reason:
                refused.append({"instance": iid, "reason": reason})
            else:
                eligible.append((iid, used))

    if "instance" not in result:
        known = [(u, i, iid) for i, (iid, u) in enumerate(eligible) if u is not None]
        if known:
            used, _, iid = min(known)
            result.update(instance=iid, reason="overflow", used=used)
        elif eligible:
            result.update(instance=eligible[0][0], reason="overflow", used=None)
        else:
            result.update(instance=None, reason="none-usable", used=None)
    result["refused"] = refused
    return result


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        """Fixed text only: the flag name argparse names, never the offending value."""
        flags = {s for a in self._actions for s in a.option_strings}
        m = re.match(r"argument (\S+?):", message)
        if m:
            named = [f for f in m.group(1).split("/") if f in flags]
            raise BadInput(f"{named[0]}: invalid or missing value" if named else "arguments")
        if message.startswith("the following arguments are required:"):
            named = [f for f in re.split(r"[,\s]+", message.split(":", 1)[1]) if f in flags]
            raise BadInput("missing required " + (", ".join(named) if named else "arguments"))
        if message.startswith("unrecognized arguments"):
            raise BadInput("unrecognized argument")
        if message.startswith("ambiguous option"):
            raise BadInput("ambiguous option")
        raise BadInput("arguments")


def build_parser():
    p = _Parser(prog="t3-pick-login.py", description=__doc__.splitlines()[0])
    p.add_argument("--current", required=True)
    p.add_argument("--usage-json", required=True)
    p.add_argument("--threshold", type=int, default=90)
    p.add_argument("--only")
    p.add_argument("--launch-root", required=True)
    p.add_argument("--slots-dir")
    p.add_argument("--main-home")
    p.add_argument("--t3-settings")
    p.add_argument("--t3-runtime")
    p.add_argument("--now")
    p.add_argument("--json", action="store_true")
    return p


OUT_FIELDS = ("instance", "reason", "used", "current_verified", "current_extra_usage", "current_reason", "refused")


def run(argv):
    try:
        args = build_parser().parse_args(argv)
        if not valid_id(args.current):
            raise BadInput("--current: invalid instance id")
        if args.now is not None:
            now = parse_aware(args.now)
            if now is None:
                raise BadInput("--now: not a timezone-aware ISO8601 time")
        else:
            now = datetime.now(timezone.utc)
        only = None
        if args.only is not None:
            only = {x.strip() for x in args.only.split(",") if x.strip()}
        ctx = Ctx(args, now)
    except BadInput as e:
        print(f"t3-pick-login: bad input: {str(e).splitlines()[0] if str(e) else 'arguments'}", file=sys.stderr)
        return 2

    res = pick(ctx, args.current, only)
    if args.json:
        text = json.dumps({k: res[k] for k in OUT_FIELDS})
    else:
        text = (f"instance={res['instance'] or 'none'} reason={res['reason']} "
                f"used={res['used'] if res['used'] is not None else 'unknown'} "
                f"current_verified={'true' if res['current_verified'] else 'false'} "
                f"current_extra_usage={res['current_extra_usage']} "
                f"current_reason={res['current_reason']}")
    print(text)
    return 0 if res["instance"] else 3


def main(argv=None):
    try:
        return run(argv)
    except Exception as e:  # S13: never a traceback, never a value
        print(f"t3-pick-login: internal error ({type(e).__name__})", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
