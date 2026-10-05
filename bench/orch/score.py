"""Score one orchestration-eval work dir and append one row to results/results.csv.

Usage: python score.py <work> <ARM> <N>
Never crashes on a missing or partial run: absent inputs leave empty cells.
"""
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime

BENCH = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(BENCH, "results")
CSV_PATH = os.path.join(RESULTS, "results.csv")
HIDDEN = os.path.join(BENCH, "hidden", "test_hidden.py")

COLUMNS = (
    "timestamp,arm,n,lead_model,mode,hidden_pass,hidden_total,visible_pass,visible_total,"
    "exit_code,seconds,api_seconds,cost_usd,turns,opus_out_tokens,fable_out_tokens,"
    "plan_seat,plan_findings,plan_p1,plan_rejected,plan_seconds,review_seats,review_findings,"
    "review_p1,review_rounds,fix_rounds,in_session_edits,defaults_taken,unfinished,"
    "files_changed,files_outside_ledger,metrics_present,run_md_present"
).split(",")

EXCLUDE_PREFIXES = (".fabstra/", ".scratch/", ".pytest_cache/")
EXCLUDE_NAMES = ("timing.txt",)


def pytest_python():
    """A Python that can import pytest: this interpreter first, then others on PATH."""
    candidates = [[sys.executable]]
    for name in ("python", "python3"):
        found = shutil.which(name)
        if found:
            candidates.append([found])
    if shutil.which("py"):
        candidates.append(["py", "-3.12"])
    for cmd in candidates:
        try:
            if subprocess.run(cmd + ["-c", "import pytest"], capture_output=True, timeout=60).returncode == 0:
                return cmd
        except (OSError, subprocess.SubprocessError):
            continue
    return [sys.executable]


def count_static_tests(path):
    files = [path] if os.path.isfile(path) else [
        os.path.join(root, f) for root, _, names in os.walk(path)
        for f in names if f.startswith("test") and f.endswith(".py")
    ]
    total = 0
    for f in files:
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                total += len(re.findall(r"^\s*def test_", fh.read(), re.M))
        except OSError:
            pass
    return total


def run_pytest(py, work, target):
    """Return (passed, total). Collection errors count as 0 passed."""
    if not os.path.exists(target):
        return 0, 0
    env = dict(os.environ, PYTHONPATH=work, PYTHONDONTWRITEBYTECODE="1")
    try:
        r = subprocess.run(py + ["-m", "pytest", "-q", "-p", "no:cacheprovider", target],
                           cwd=work, env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=900)
        out = r.stdout
    except (OSError, subprocess.SubprocessError):
        out = ""
    lines = [l for l in out.splitlines() if l.strip()]
    last = lines[-1] if lines else ""
    counts = {k: int(v) for v, k in re.findall(r"(\d+) (passed|failed|errors?|skipped|xfailed|xpassed)", last)}
    passed = counts.get("passed", 0)
    total = passed + counts.get("failed", 0) + counts.get("skipped", 0) + counts.get("xfailed", 0) + counts.get("xpassed", 0)
    if "error" in counts or "errors" in counts:
        if total == 0:          # collection error: nothing ran
            passed = 0
        total += counts.get("error", 0) + counts.get("errors", 0)
    static = count_static_tests(target)
    if total == 0 or (passed == 0 and static > total):
        total = static
    return passed, total


def read_timing(work):
    try:
        with open(os.path.join(work, "timing.txt"), encoding="utf-8") as f:
            vals = [l.strip() for l in f if l.strip()]
    except OSError:
        return "", ""
    seconds = ""
    if len(vals) >= 2 and vals[0].isdigit() and vals[1].isdigit():
        seconds = int(vals[1]) - int(vals[0])
    exit_code = vals[2] if len(vals) >= 3 else ""
    return seconds, exit_code


def read_claude_out(work):
    path = os.path.join(work, "claude.out.json")
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return {}
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
        if isinstance(obj, list):
            dicts = [o for o in obj if isinstance(o, dict)]
            return dicts[-1] if dicts else {}
    except ValueError:
        pass
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    return obj
            except ValueError:
                continue
    return {}


def model_tokens(usage, needle):
    if not isinstance(usage, dict):
        return ""
    hits = [v.get("outputTokens", 0) for k, v in usage.items() if needle in k.lower() and isinstance(v, dict)]
    return sum(hits) if hits else ""


def cell(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (list, tuple)):
        return ";".join(str(x) for x in v)
    return v


def read_metrics(work):
    path = os.path.join(work, ".fabstra", "METRICS.json")
    try:
        with open(path, encoding="utf-8") as f:
            m = json.load(f)
        return m if isinstance(m, dict) else None
    except (OSError, ValueError):
        return None


def metrics_cells(m):
    plan = m.get("plan_gate") if isinstance(m.get("plan_gate"), dict) else {}
    review = m.get("review") if isinstance(m.get("review"), dict) else {}
    return {
        "lead_model": cell(m.get("lead_model")),
        "mode": cell(m.get("mode")),
        "plan_seat": cell(plan.get("seat")),
        "plan_findings": cell(plan.get("findings")),
        "plan_p1": cell(plan.get("p1")),
        "plan_rejected": cell(plan.get("rejected")),
        "plan_seconds": cell(plan.get("seconds")),
        "review_seats": cell(review.get("seats")),
        "review_findings": cell(review.get("findings")),
        "review_p1": cell(review.get("p1")),
        "review_rounds": cell(review.get("rounds")),
        "fix_rounds": cell(m.get("fix_rounds")),
        "in_session_edits": cell(m.get("in_session_code_edits")),
        "defaults_taken": cell(m.get("defaults_taken")),
        "unfinished": cell(m.get("unfinished")),
    }


def run_md_cells(text):
    """Heuristic fallback when METRICS.json is absent."""
    accepted = len(re.findall(r"\bACCEPTED\b", text))
    rejected = len(re.findall(r"\bREJECTED\b", text))
    return {
        "review_findings": accepted + rejected,
        "review_p1": len(re.findall(r"\bP1\b", text)),
        "review_rounds": sum(1 for l in text.splitlines() if re.search(r"re-review", l, re.I)),
        "fix_rounds": sum(1 for l in text.splitlines() if re.search(r"fix round", l, re.I)),
        "defaults_taken": len(re.findall(r"default taken", text, re.I)),
    }


def git_lines(work, *args):
    try:
        r = subprocess.run(["git", "-C", work, *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.splitlines() if r.returncode == 0 else None


def changed_files(work):
    """Files changed since the fixture commit (committed or not) plus untracked files."""
    roots = git_lines(work, "rev-list", "--max-parents=0", "HEAD")
    if not roots:
        return None
    names = set(git_lines(work, "diff", "--name-only", roots[-1]) or [])
    for line in git_lines(work, "status", "--porcelain", "--untracked-files=all") or []:
        if line.startswith("??"):
            names.add(line[3:].strip().strip('"'))
    keep = []
    for name in names:
        n = name.replace("\\", "/")
        base = n.rsplit("/", 1)[-1]
        if n.startswith(EXCLUDE_PREFIXES) or "__pycache__" in n.split("/"):
            continue
        if base in EXCLUDE_NAMES or ("/" not in n and base.startswith("claude.")):
            continue
        keep.append(n)
    return sorted(keep)


def main():
    if len(sys.argv) != 4:
        print("usage: python score.py <work> <ARM> <N>", file=sys.stderr)
        return 2
    work, arm, n = os.path.abspath(sys.argv[1]), sys.argv[2], sys.argv[3]
    row = dict.fromkeys(COLUMNS, "")
    row.update(timestamp=datetime.now().astimezone().isoformat(timespec="seconds"), arm=arm, n=n)

    py = pytest_python()
    row["hidden_pass"], row["hidden_total"] = run_pytest(py, work, HIDDEN)
    row["visible_pass"], row["visible_total"] = run_pytest(py, work, os.path.join(work, "tests"))

    row["seconds"], row["exit_code"] = read_timing(work)

    out = read_claude_out(work)
    if isinstance(out.get("duration_api_ms"), (int, float)):
        row["api_seconds"] = round(out["duration_api_ms"] / 1000, 1)
    row["cost_usd"] = cell(out.get("total_cost_usd"))
    row["turns"] = cell(out.get("num_turns"))
    row["opus_out_tokens"] = model_tokens(out.get("modelUsage"), "opus")
    row["fable_out_tokens"] = model_tokens(out.get("modelUsage"), "fable")

    metrics = read_metrics(work)
    run_md = os.path.join(work, ".fabstra", "RUN.md")
    row["metrics_present"] = 1 if metrics is not None else 0
    row["run_md_present"] = 1 if os.path.isfile(run_md) else 0
    if metrics is not None:
        row.update(metrics_cells(metrics))
    elif row["run_md_present"]:
        with open(run_md, encoding="utf-8", errors="replace") as f:
            row.update(run_md_cells(f.read()))

    files = changed_files(work)
    if files is not None:
        row["files_changed"] = len(files)
        row["files_outside_ledger"] = sum(1 for f in files if not f.startswith(("ledger/", "tests/")))

    os.makedirs(RESULTS, exist_ok=True)
    new = not os.path.isfile(CSV_PATH) or os.path.getsize(CSV_PATH) == 0
    with open(CSV_PATH, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        if new:
            w.writeheader()
        w.writerow(row)
    print(" ".join(f"{k}={row[k]}" for k in COLUMNS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
