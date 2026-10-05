"""Weekly Sol-on-Codex usage report: speed, tokens, reliability, quality, and account rotation.

Sources (all already written by the tools in normal use; nothing to remember to run):
  1. Codex companion job records  ~/.claude/plugins/data/codex-openai-codex/state/*/jobs/*.json
     -> one row per Sol task: project, role (review/build), created/completed, status, output.
  2. Codex session logs            ~/.codex/sessions/YYYY/MM/DD/rollout-*-<threadId>.jsonl
     -> model, reasoning effort, token usage, tool calls, joined by threadId.
  3. Proxy account snapshots       ~/model-router/bench/account-usage.csv
     -> per-account success/failed counts, appended every 30 min by codex-credit-check.py.
  4. Quality lines                 ~/model-router/bench/usage-log.csv
     -> appended by fabsol / fable-mode after each report: findings accepted vs rejected.

Usage: python usage-report.py [--since 2026-09-04] [--until 2026-09-11]
Writes usage-week.csv (one row per task) and prints a markdown summary.
"""
import csv
import glob
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta

HOME = os.path.expanduser("~")
JOBS = os.path.join(HOME, ".claude", "plugins", "data", "codex-openai-codex", "state", "*", "jobs", "*.json")
SESSIONS = os.path.join(HOME, ".codex", "sessions")
BENCH = os.path.dirname(os.path.abspath(__file__))
ACCOUNTS = os.path.join(BENCH, "account-usage.csv")
QUALITY = os.path.join(BENCH, "usage-log.csv")
OUT = os.path.join(BENCH, "usage-week.csv")


def arg(name, default):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


def parse_ts(s):
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def role_of(job):
    s = (job.get("summary") or "").lower()
    if job.get("write"):
        return "build"
    if "review" in s or "red team" in s:
        return "review"
    return "task"


def findings_in(text):
    """Count findings in either layout: inline P1/P2/P3 lines or numbered items under a P-heading."""
    n = 0
    in_sev = False
    for ln in (text or "").splitlines():
        if re.match(r"^\s*(#{1,6}\s*|\*\*)?\s*P[123]\b[^\n]{0,40}$", ln) and not re.match(r"^\s*\d+[.)]\s", ln):
            in_sev = True
            continue
        if re.match(r"^\s*#{1,6}\s", ln):
            in_sev = False
        if re.search(r"\bP[123]\b", ln) and (re.search(r"\w+\.\w+:\d+", ln) or "—" in ln or " - " in ln):
            n += 1
        elif in_sev and re.match(r"^\s*\d+[.)]\s+\S", ln):
            n += 1
    return n


def session_info(thread_id):
    """model, effort, tokens, tool calls, turns for a Codex thread; {} when the log is missing."""
    if not thread_id:
        return {}
    files = glob.glob(os.path.join(SESSIONS, "*", "*", "*", f"*{thread_id}*.jsonl"))
    if not files:
        return {}
    info = {"model": None, "effort": None, "tool_calls": 0, "turns": 0, "in": 0, "cached": 0, "out": 0, "reasoning": 0}
    for ln in open(files[0], encoding="utf-8", errors="replace"):
        try:
            o = json.loads(ln)
        except ValueError:
            continue
        p = o.get("payload") if isinstance(o.get("payload"), dict) else {}
        t = o.get("type")
        if t == "turn_context":
            info["turns"] += 1
            info["model"] = info["model"] or p.get("model")
            cm = p.get("collaboration_mode") or {}
            st = cm.get("settings") or {}
            info["effort"] = info["effort"] or st.get("reasoning_effort") or p.get("reasoning_effort") or p.get("effort")
        elif t == "response_item" and p.get("type") in ("function_call", "custom_tool_call", "local_shell_call"):
            info["tool_calls"] += 1
        elif t == "event_msg" and p.get("type") == "token_count":
            tu = ((p.get("info") or {}).get("total_token_usage")) or {}
            info["in"] = tu.get("input_tokens", info["in"])
            info["cached"] = tu.get("cached_input_tokens", info["cached"])
            info["out"] = tu.get("output_tokens", info["out"])
            info["reasoning"] = tu.get("reasoning_output_tokens", info["reasoning"])
    return info


def main():
    since = parse_ts(arg("--since", "2026-09-04") + "T00:00:00+08:00")
    until = parse_ts(arg("--until", "2026-09-11") + "T23:59:59+08:00")
    rows = []
    for path in glob.glob(JOBS):
        try:
            job = json.load(open(path, encoding="utf-8"))
        except ValueError:
            continue
        created = parse_ts(job.get("createdAt"))
        if not created or not (since <= created.astimezone(since.tzinfo) <= until):
            continue
        done = parse_ts(job.get("completedAt"))
        secs = round((done - created).total_seconds()) if done else None
        s = session_info(job.get("threadId"))
        result = job.get("result") or {}
        text = job.get("rendered") or result.get("rawOutput") or ""
        rows.append({
            "date": created.astimezone(since.tzinfo).strftime("%Y-%m-%d %H:%M"),
            "project": os.path.basename((job.get("workspaceRoot") or "").rstrip("/\\")),
            "role": role_of(job),
            "model": s.get("model") or "",
            "effort": s.get("effort") or "",
            "seconds": secs if secs is not None else "",
            "status": job.get("status"),
            "exit": result.get("status", ""),
            "turns": s.get("turns", ""),
            "tool_calls": s.get("tool_calls", ""),
            "tokens_in": s.get("in", ""),
            "tokens_cached": s.get("cached", ""),
            "tokens_out": s.get("out", ""),
            "tokens_reasoning": s.get("reasoning", ""),
            "findings": findings_in(text) if role_of(job) == "review" else "",
            "job": job.get("id"),
        })
    rows.sort(key=lambda r: r["date"])
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["date"])
        w.writeheader()
        w.writerows(rows)

    # ---- summary ----
    def med(xs):
        xs = sorted(x for x in xs if isinstance(x, (int, float)))
        return xs[len(xs) // 2] if xs else "-"

    print(f"# Sol on Codex, {arg('--since', '2026-09-04')} to {arg('--until', '2026-09-11')}\n")
    print(f"Tasks: {len(rows)}  |  reviews: {sum(r['role']=='review' for r in rows)}  |  builds: {sum(r['role']=='build' for r in rows)}\n")
    print("| role | n | completed | failed | median s | median tool calls | median tokens in (cached) | median findings |")
    print("|---|---|---|---|---|---|---|---|")
    for role in ("review", "build", "task"):
        rs = [r for r in rows if r["role"] == role]
        if not rs:
            continue
        comp = sum(r["status"] == "completed" for r in rs)
        fail = sum(r["status"] == "failed" for r in rs)
        print(f"| {role} | {len(rs)} | {comp} | {fail} | {med([r['seconds'] for r in rs])} | {med([r['tool_calls'] for r in rs])} | "
              f"{med([r['tokens_in'] for r in rs])} ({med([r['tokens_cached'] for r in rs])}) | {med([r['findings'] for r in rs if r['findings']!=''])} |")

    # by model/effort
    by = defaultdict(list)
    for r in rows:
        by[(r["model"], r["effort"])].append(r)
    print("\n| model | effort | n | median s | failed |\n|---|---|---|---|---|")
    for (m, e), rs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        print(f"| {m or '?'} | {e or '?'} | {len(rs)} | {med([r['seconds'] for r in rs])} | {sum(r['status']=='failed' for r in rs)} |")

    # accounts
    if os.path.isfile(ACCOUNTS):
        acc = defaultdict(lambda: {"success": 0, "failed": 0, "snapshots": 0})
        seen = {}
        for r in csv.DictReader(open(ACCOUNTS, encoding="utf-8")):
            ts = parse_ts(r["timestamp"])
            if ts and since <= ts <= until:
                key = (r["account"], r["bucket"])
                if key in seen:
                    continue  # buckets repeat across snapshots; count each once
                seen[key] = 1
                acc[r["account"]]["success"] += int(r["success"] or 0)
                acc[r["account"]]["failed"] += int(r["failed"] or 0)
        print("\n| account | requests ok | failed |\n|---|---|---|")
        for a, v in acc.items():
            print(f"| {a} | {v['success']} | {v['failed']} |")

    # quality lines
    if os.path.isfile(QUALITY):
        q = [r for r in csv.DictReader(open(QUALITY, encoding="utf-8")) if r.get("date")]
        if q:
            acc_n = sum(int(r.get("accepted") or 0) for r in q)
            rej_n = sum(int(r.get("rejected") or 0) for r in q)
            tot = acc_n + rej_n
            print(f"\nQuality (from {len(q)} logged reviews): findings accepted {acc_n}, rejected {rej_n}"
                  f"{f', precision {100*acc_n//tot}%' if tot else ''}; median fix rounds "
                  f"{med([int(r.get('fix_rounds') or 0) for r in q])}")
    print(f"\nDetail: {OUT}")


if __name__ == "__main__":
    main()
