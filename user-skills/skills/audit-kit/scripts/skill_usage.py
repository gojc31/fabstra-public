#!/usr/bin/env python3
"""Count skill use in Claude Code transcripts and list installed skills never used.

The agent RUNS this script (read-only; it writes nothing).

Counts two kinds of use in ~/.claude/projects/**/*.jsonl:
  - model calls: Skill tool_use blocks in assistant messages (input.skill)
  - typed slash commands: user messages that open with Claude Code's command
    wrapper (optional <command-message>...</command-message>, then
    <command-name>/name</command-name>): a string content opens with it, or
    the first content block is a text block that does; the tag in a later
    block, user prose, assistant text or tool output is not counted
Each event counts by its own timestamp, so an old event in a recently
modified transcript stays out of the window. A file last modified before the
window is not opened: Claude Code appends to transcripts, so a file last
written before the window holds no event inside it; a copied or restored file
with an old mtime would be missed. A tool_use id or message uuid seen twice
(a transcript copied into another) counts once.

Then lists every skill found in ~/.claude/skills/*/SKILL.md and in the skills/
folder of each plugin in ~/.claude/plugins/installed_plugins.json that
~/.claude/settings.json enables, marking the ones with zero uses in the window
and whether each is model-invoked. Names compare exactly: plugin skills as
plugin:skill, user skills bare. A typed bare command counts for a plugin skill
only when exactly one installed skill has that short name.

Not read, so the inventory can miss or over-list skills: project- and
managed-scope plugin enables (~/.claude/settings.local.json is the home
folder's project-local file, not a global one, and is not read either), skill
paths a plugin manifest declares outside skills/, and project .claude/skills
folders. Where this Claude Code has /skill-doctor, its inventory is the
authoritative one; use this script for the usage counts.

Usage:
  python skill_usage.py [--days 30] [--home PATH]

Stdlib only. The window is limited by whatever transcripts still exist: the
script prints the oldest event date it counted.

Exit 0 = done, 3 = INCOMPLETE: a transcript or project folder could not be
read (each is listed), so the zero-use list is not definitive.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

# Transcripts run to many GB, so lines are pre-filtered by byte substring
# (bytes.find, far faster here than a regex alternation) and only those lines
# are parsed as JSON and walked block by block.
NEEDLES = (b'"Skill"', b"<command-name>")
# A typed command: the user text opens with the wrapper Claude Code writes.
CMD = re.compile(r"\s*(?:<command-message>[^<]*</command-message>\s*)?<command-name>/?([^<\s\\]+)</command-name>")
YAML_TRUE = {"true", "yes", "on", "1"}
INLINE_COMMENT = re.compile(r"\s#")


def yaml_scalar(v):
    """A one-line YAML value without its surrounding quotes or unquoted # comment."""
    v = v.strip()
    if v[:1] in ("'", '"'):
        q, i = v[0], 1
        while i < len(v):
            if q == '"' and v[i] == "\\":
                i += 2
                continue
            if v[i] == q:
                if q == "'" and v[i + 1:i + 2] == "'":
                    i += 2
                    continue
                break
            i += 1
        inner = v[1:i]
        return inner.replace("''", "'") if q == "'" else inner.replace('\\"', '"')
    if v.startswith("#"):
        return ""
    m = INLINE_COMMENT.search(v)
    return (v[:m.start()] if m else v).strip()


def frontmatter(path):
    """Return (name, model_invoked) from a SKILL.md frontmatter block (top-level keys only)."""
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return path.parent.name, True
    name, model_invoked = None, True
    lines = text.splitlines()
    if lines and lines[0].rstrip() == "---":
        end = next((i for i in range(1, len(lines)) if lines[i].rstrip() == "---"), None)
        for line in lines[1:end] if end else []:
            if not line.strip() or line[0] in " \t" or line.startswith("#"):
                continue  # blank, nested under a parent key, or a comment
            k, sep, v = line.partition(":")
            if not sep:
                continue
            k, v = k.strip(), yaml_scalar(v)
            if k == "name":
                name = v
            elif k == "disable-model-invocation":
                model_invoked = v.lower() not in YAML_TRUE
    return name or path.parent.name, model_invoked


def installed_skills(claude):
    rows = []  # (qualified name, source, model_invoked)
    for p in sorted((claude / "skills").glob("*/SKILL.md")):
        n, mi = frontmatter(p)
        rows.append((n, "user", mi))
    rec = claude / "plugins" / "installed_plugins.json"
    if rec.is_file():
        try:
            plugins = json.loads(rec.read_text(encoding="utf-8")).get("plugins", {})
        except (OSError, ValueError):
            plugins = {}
        try:
            enabled = json.loads((claude / "settings.json").read_text(encoding="utf-8-sig")).get("enabledPlugins", {})
        except (OSError, ValueError, AttributeError):
            enabled = {}
        seen = set()
        for key, entries in plugins.items():
            if not isinstance(enabled, dict) or enabled.get(key) is not True:
                continue  # disabled or never enabled at user level: its skills do not load
            plugin = key.split("@")[0]
            for e in entries if isinstance(entries, list) else [entries]:
                root = Path(e.get("installPath", ""))
                if not root.is_dir() or (plugin, str(root)) in seen:
                    continue
                seen.add((plugin, str(root)))
                for p in sorted(root.glob("skills/*/SKILL.md")):
                    n, mi = frontmatter(p)
                    rows.append((f"{plugin}:{n}", f"plugin {key} ({e.get('scope', '?')})", mi))
    uniq = {}
    for n, src, mi in rows:
        uniq.setdefault(n, (src, mi))
    return uniq


def parse_ts(value):
    """Parse a transcript ISO timestamp to an aware UTC datetime, or None."""
    if not isinstance(value, str):
        return None
    try:
        t = dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def line_events(obj):
    """Yield (kind, name, dedupe key or None) for each skill use in one transcript line."""
    msg = obj.get("message")
    if not isinstance(msg, dict):
        return
    role, content = msg.get("role"), msg.get("content")
    if role == "assistant" and isinstance(content, list):
        for b in content:
            if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "Skill":
                inp = b.get("input")
                name = inp.get("skill") if isinstance(inp, dict) else None
                if isinstance(name, str) and name.strip().lstrip("/"):
                    tid = b.get("id")
                    yield "call", name.strip().lstrip("/"), ("call", tid) if isinstance(tid, str) else None
    elif role == "user":
        # The wrapper must open the whole message: the string itself, or the
        # first content block when that block is text. Later blocks never count.
        text = content if isinstance(content, str) else None
        if isinstance(content, list) and content and isinstance(content[0], dict) \
                and content[0].get("type") == "text":
            text = content[0].get("text")
        m = CMD.match(text) if isinstance(text, str) and "<command-name>" in text else None
        if m:
            uid = obj.get("uuid")
            yield "typed", m.group(1), ("typed", uid) if isinstance(uid, str) else None


def candidate_lines(data):
    """Yield each line of data (bytes) holding a needle, once."""
    starts = set()
    for needle in NEEDLES:
        pos = data.find(needle)
        while pos != -1:
            start = data.rfind(b"\n", 0, pos) + 1
            end = data.find(b"\n", pos)
            if end == -1:
                end = len(data)
            if start not in starts:
                starts.add(start)
                yield data[start:end]
            pos = data.find(needle, end)


def transcripts(projects, problems):
    """Yield every *.jsonl under projects; folders that cannot be listed go to problems."""
    def onerror(e):
        problems.append(f"{shown(projects, e.filename)}/ (cannot list: {e.strerror or e})")
    for dirpath, _dirs, names in os.walk(projects, onerror=onerror):
        for name in sorted(names):
            if name.endswith(".jsonl"):
                yield Path(dirpath) / name


def shown(projects, path):
    try:
        return Path(path).relative_to(projects).as_posix()
    except (TypeError, ValueError):
        return str(path)


def main():
    try:
        sys.stdout.reconfigure(errors="backslashreplace")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--home", default=str(Path.home()))
    a = ap.parse_args()
    claude = Path(a.home) / ".claude"
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=a.days)
    since_ts = since.timestamp()
    calls, typed = Counter(), Counter()
    seen_keys = set()
    oldest = oldest_before = None
    before = files = 0
    projects = claude / "projects"
    problems = []
    for f in transcripts(projects, problems) if projects.is_dir() else ():
        try:
            if f.stat().st_mtime < since_ts:
                continue
            data = f.read_bytes()
        except OSError as e:
            problems.append(f"{shown(projects, f)} (cannot read: {e.strerror or e})")
            continue
        files += 1
        for line in candidate_lines(data):
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if not isinstance(obj, dict):
                continue
            events = list(line_events(obj))
            if not events:
                continue
            ts = parse_ts(obj.get("timestamp"))
            if ts is None:
                continue  # no time of its own (e.g. a request copy): cannot place it in the window
            for kind, name, key in events:
                if key is not None:
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                if ts < since:
                    before += 1
                    oldest_before = ts if oldest_before is None or ts < oldest_before else oldest_before
                    continue
                oldest = ts if oldest is None or ts < oldest else oldest
                (calls if kind == "call" else typed)[name] += 1
    print(f"transcripts read: {files} (modified in the last {a.days} days); "
          f"events counted from {since.date()}; oldest event counted: {oldest.date() if oldest else 'none'}")
    if before:
        print(f"older events in those files, not counted: {before} (oldest {oldest_before.date()})")
    if problems:
        print(f"unreadable transcripts: {len(problems)}")
        for p in problems:
            print(f"  {p}")
    print("\nUsed (model calls / typed):")
    used = set(calls) | set(typed)
    for n in sorted(used, key=lambda k: (-(calls[k] + typed[k]), k)):
        print(f"  {calls[n]:5d} / {typed[n]:<5d} {n}")
    skills = installed_skills(claude)
    owners = {}
    for n in skills:
        owners.setdefault(n.split(":")[-1], []).append(n)
    hit = set(calls)
    for n in typed:
        if n in skills:
            hit.add(n)
        elif ":" not in n and len(owners.get(n, [])) == 1:
            hit.add(owners[n][0])
        else:
            hit.add(n)
    print("\nInstalled, zero uses in window (model-invoked ones cost context every turn):")
    for n, (src, mi) in sorted(skills.items()):
        if n in hit:
            continue
        print(f"  {'MODEL-INVOKED' if mi else 'user-invoked '}  {n}  [{src}]")
    if problems:
        print(f"\nINCOMPLETE: {len(problems)} transcripts unreadable - the zero-use list is not definitive")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
