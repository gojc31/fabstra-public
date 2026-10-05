"""Keep the proxy's Codex credentials in step with their credit state.

For every `codex-*.json` in the CLIProxyAPI auth dir, send one tiny request straight to the
ChatGPT Codex backend with that credential's own token (the same call the proxy makes) and:

  - "out of credits" / insufficient quota  -> set "disabled": true   (proxy skips it)
  - 200 OK on a credential this script disabled -> set "disabled": false (back in rotation)
  - 429 rate limit / anything else             -> leave alone (the proxy's own cooldown handles 429)

Credentials the USER disabled by hand are never re-enabled: the script only touches files it
disabled itself, tracked in .codex-credit-check.json next to the auth files. The proxy watches
the auth dir, so edits take effect without a restart.

Usage: python codex-credit-check.py [--dry-run] [--verbose]
Schedule it every 30 minutes (see register-credit-check.ps1).

Each run also snapshots the proxy's per-account request counters (management API, key in
$CLIPROXY_DIR/.management-key) to bench/account-usage.csv, one row per
account per 10-minute bucket, so usage-report.py can show how the two accounts were cycled.
"""
import glob
import json
import os
import sys
import time
import urllib.error
import urllib.request

AUTH_DIR = os.path.expanduser(r"~\.cli-proxy-api")
STATE = os.path.join(AUTH_DIR, ".codex-credit-check.json")
ENDPOINT = "https://chatgpt.com/backend-api/codex/responses"
PROBE_MODEL = "gpt-5.4"
CREDIT_MARKERS = ("out of credits", "insufficient_quota", "insufficient quota", "refill")

DRY = "--dry-run" in sys.argv
VERBOSE = "--verbose" in sys.argv or DRY


def log(msg):
    print(time.strftime("%Y-%m-%d %H:%M:%S"), msg)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def probe(cred):
    """Return ("ok"|"credits"|"ratelimit"|"auth"|"other", detail)."""
    body = json.dumps({
        "model": PROBE_MODEL,
        "instructions": "Reply with the single word OK.",
        "input": [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": "OK?"}]}],
        "store": False,
        "stream": True,
        "reasoning": {"effort": "low"},
    }).encode()
    req = urllib.request.Request(ENDPOINT, data=body, method="POST", headers={
        "Authorization": f"Bearer {cred.get('access_token', '')}",
        "chatgpt-account-id": cred.get("account_id", ""),
        "Content-Type": "application/json",
        "OpenAI-Beta": "responses=experimental",
        "originator": "codex_cli_rs",
        "User-Agent": "codex_cli_rs/0.153.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            body = r.read(200_000).decode("utf-8", "replace")   # SSE: the error can arrive after response.created
            low = body.lower()
            if any(m in low for m in CREDIT_MARKERS):
                return "credits", f"HTTP {r.status} stream error: {body[-200:]!r}"
            if '"type":"error"' in low or "event: error" in low:
                if "rate limit" in low or "429" in low or "usage_limit" in low:
                    return "ratelimit", f"HTTP {r.status} stream error: {body[-200:]!r}"
                return "other", f"HTTP {r.status} stream error: {body[-200:]!r}"
            return "ok", f"HTTP {r.status} events={body.count('event: ')} completed={'response.completed' in body}"
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", "replace")
        low = text.lower()
        if any(m in low for m in CREDIT_MARKERS):
            return "credits", f"HTTP {e.code} {text[:160]}"
        if e.code == 429:
            return "ratelimit", f"HTTP {e.code} {text[:160]}"
        if e.code in (401, 403):
            return "auth", f"HTTP {e.code} {text[:160]}"
        return "other", f"HTTP {e.code} {text[:160]}"
    except Exception as e:  # network etc.
        return "other", repr(e)


MGMT_KEY_FILE = os.path.join(os.environ.get("CLIPROXY_DIR", os.path.expanduser("~/cli-proxy-api")), ".management-key")
ACCOUNT_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bench", "account-usage.csv")


def snapshot_accounts():
    """Append per-account success/failed counts per 10-minute bucket from the proxy management API."""
    import csv
    if not os.path.isfile(MGMT_KEY_FILE):
        return
    key = open(MGMT_KEY_FILE, encoding="utf-8").read().strip()
    req = urllib.request.Request("http://127.0.0.1:8317/v0/management/auth-files",
                                 headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.load(r)
    today = time.strftime("%Y-%m-%d")
    new = os.path.isfile(ACCOUNT_CSV) is False
    with open(ACCOUNT_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp", "account", "provider", "disabled", "failed_total", "bucket", "success", "failed"])
        for cred in data.get("files", []):
            if cred.get("provider") != "codex":
                continue
            for b in cred.get("recent_requests", []):
                if not (b.get("success") or b.get("failed")):
                    continue
                w.writerow([time.strftime("%Y-%m-%dT%H:%M:%S+08:00"), cred.get("email") or cred.get("account"),
                            cred.get("provider"), cred.get("disabled"), cred.get("failed"),
                            f"{today} {b.get('time')}", b.get("success", 0), b.get("failed", 0)])


def main():
    state = load_json(STATE) if os.path.isfile(STATE) else {"disabled_by_check": []}
    ours = set(state.get("disabled_by_check", []))
    changed = False
    for path in sorted(glob.glob(os.path.join(AUTH_DIR, "codex-*.json"))):
        name = os.path.basename(path)
        cred = load_json(path)
        if cred.get("type") not in (None, "codex"):
            continue
        status, detail = probe(cred)
        disabled = bool(cred.get("disabled"))
        if VERBOSE:
            log(f"{name}: {status} | disabled={disabled} | {detail}")
        if status == "credits" and not disabled:
            log(f"{name}: out of credits -> disabling")
            if not DRY:
                cred["disabled"] = True
                save_json(path, cred)
                ours.add(name)
                changed = True
        elif status == "ok" and disabled and name in ours:
            log(f"{name}: credits back -> re-enabling")
            if not DRY:
                cred["disabled"] = False
                save_json(path, cred)
                ours.discard(name)
                changed = True
        elif status == "ok" and disabled and name not in ours:
            log(f"{name}: has credit but was disabled by hand; leaving it (add it to {os.path.basename(STATE)} to manage)")
    if changed and not DRY:
        save_json(STATE, {"disabled_by_check": sorted(ours), "updated": time.strftime("%Y-%m-%dT%H:%M:%S")})
    if not changed and VERBOSE:
        log("no changes")
    try:
        snapshot_accounts()
    except Exception as e:
        log(f"account snapshot skipped: {e!r}")


if __name__ == "__main__":
    main()
