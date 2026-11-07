#!/usr/bin/env python3
"""Leak gate: scan a folder (or stdin) for names, emails, home paths and secrets.

The agent RUNS this script (read-only; it writes nothing).

Usage:
  python leak_scan.py <folder> --deny DENYFILE [--allow ALLOWFILE] [--ok-domain example.com ...] [--skip DIR ...]
  git log -p | python leak_scan.py - --deny DENYFILE [--allow ALLOWFILE]

DENYFILE: one term per line, UTF-8 (a BOM is fine; case-insensitive; blank
lines and # comments ignored). Keep it outside the repo you publish - it
names what it protects.
ALLOWFILE: UTF-8, tab-separated lines `relative/path<TAB>exact snippet<TAB>reason`;
the snippet is removed from that file's lines before matching, and unused
entries are reported so they can be pruned.
A deny or allow file that cannot be read or decoded is a usage error.

Every file under the folder is scanned except `.git`; --skip DIR (repeatable)
excludes more: a bare name skips that folder name at any depth, a path with a
slash skips that folder relative to the root. The skip list used is printed.
Scanned files are decoded as UTF-16 (with BOM), else UTF-8, else cp1252.
Binary files (NUL bytes) are not scanned; they are counted and listed.
Links to folders are not followed; they are listed.

On stdin, each patch's file header (git log -p: `diff --git a/X b/X`, then
`--- a/X` / `+++ b/X` before the first `@@`) sets the file that allowlist
entries match and that hits name; `+++ /dev/null` (a deletion) uses the
a-side. Lines inside a hunk never change the file. Lines before any header,
or after a `commit <sha>` line, are `<stdin>`. Git's C-style quoted paths
("caf\\303\\251.md") are decoded; `git -c core.quotePath=false log -p` avoids
the quoting for non-ASCII names.

Exit 0 = PASS, 1 = hits (printed as file:line), 2 = usage error,
3 = INCOMPLETE: a folder or file could not be read, so the scan is not a PASS
(when there are hits as well the exit is 1 and the unread paths are listed).
Every printed line masks secret-format values. Stdlib only.
"""
import argparse
import os
import re
import sys
from pathlib import Path

# No length caps: a match runs to the end of its token. Patterns that need
# more text after a run (jwt, private key) only start where a token starts,
# so no pattern backtracks over the same text twice on a long line.
SK = "sk" + "-"  # split so this source holds no key-prefix literal
SECRETS = [
    ("anthropic key", SK + r"ant-[A-Za-z0-9_\-]{20,}"),
    ("openai key", r"\b" + SK + r"(?!ant-)(?:proj-)?[A-Za-z0-9_\-]{20,}"),
    ("github token", r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{30,}"),
    ("aws access key", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    ("slack token", r"\bxox[abprs]-[A-Za-z0-9\-]{10,}"),
    ("google api key", r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    ("stripe live key", r"\b[rs]k_live_[0-9A-Za-z]{16,}"),
    ("private key block", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ("jwt", r"eyJ(?<![A-Za-z0-9_\-.]eyJ)[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),
]
SECRETS = [(n, re.compile(p)) for n, p in SECRETS]
SECRET_ANY = re.compile("|".join(f"(?:{rx.pattern})" for _, rx in SECRETS))
TOKEN_TAIL = re.compile(r"[A-Za-z0-9_\-]*")
# Emails: only an '@' right after a local-part character is a candidate; the
# local part is walked back at most 64 characters and the domain (labels of
# 1-63 characters) is matched anchored after the '@'.
EMAIL_LOCAL = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._%+-")
EMAIL_AT = re.compile(r"[A-Za-z0-9._%+\-]@")
EMAIL_DOMAIN = re.compile(r"(?:[A-Za-z0-9\-]{1,63}\.)+[A-Za-z0-9\-]{1,63}")
OK_DOMAINS = {"example.com", "example.org", "anthropic.com", "users.noreply.github.com"}
# An absolute home path naming a real user; placeholders like <you>, {name},
# $HOME, %USERPROFILE% or ~ pass. The Windows form matches in any case and
# any username. /Users/ and /home/ match anywhere in their usual case, and in
# any case where the path starts a token (line start, whitespace, quote,
# backtick, = ( [ < > :, or file://), so web routes like /api/users/42 pass.
HOME_PATH = re.compile(
    r"(?:(?i:[a-z]:[\\/]{1,8}users[\\/]{1,8})"
    r"|/Users/|/home/"
    r"|(?:(?<![^\s\"'`=(\[<>:])|(?<=[Ff][Ii][Ll][Ee]://))(?i:/users/|/home/))"
    r"(?![<{$%~])([^\\/\s\"'`<>|:*?,;=()\[\]{}]{1,128})")
HOME_OK = {"public", "default", "shared", "runner", "user", "username", "you", "name", "me"}
ALWAYS_SKIP = ".git"
COMMIT_LINE = re.compile(r"commit [0-9a-f]{7,64}\b")


def mask(text):
    """Replace every secret-format value in text with its first 4 chars and length."""
    if not SECRET_ANY.search(text):
        return text
    out, pos = [], 0
    for m in SECRET_ANY.finditer(text):
        if m.start() < pos:
            continue
        end = TOKEN_TAIL.match(text, m.end()).end()
        out.append(text[pos:m.start()])
        out.append(f"{text[m.start():m.start() + 4]}...({end - m.start()} chars)")
        pos = end
    out.append(text[pos:])
    return "".join(out)


def say(line):
    print(mask(line))


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write(mask(f"{self.prog}: error: {message}") + "\n")
        sys.exit(2)


def read_utf8(path, what):
    """Read a deny/allow file as UTF-8 (BOM allowed); raise SystemExit(2) on failure."""
    try:
        return Path(path).read_text(encoding="utf-8-sig")
    except OSError as e:
        say(f"leak_scan: cannot read {what} {path}: {e.strerror}")
    except UnicodeDecodeError as e:
        say(f"leak_scan: cannot decode {what} {path} as UTF-8 ({e.reason} at byte {e.start}); save it as UTF-8")
    raise SystemExit(2)


def load_terms(path):
    terms = []
    for line in read_utf8(path, "deny file").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            terms.append((line, re.compile(re.escape(line), re.I)))
    return terms


def load_allow(path):
    rows = []
    if path:
        for line in read_utf8(path, "allow file").splitlines():
            parts = line.split("\t")
            if len(parts) >= 2 and not line.startswith("#"):
                rows.append((parts[0].replace("\\", "/"), parts[1]))
    return rows


def decode(data):
    """Return the text of a file's bytes, or None when the file is binary."""
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16", errors="replace")
    if data[:3] == b"\xef\xbb\xbf":
        data = data[3:]
    if b"\0" in data:
        return None
    for enc in ("utf-8", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            pass
    return data.decode("latin-1")  # never fails: bytes cp1252 leaves undefined


def emails(line):
    """Yield (address, domain) for each email-shaped run around an '@'."""
    for at in EMAIL_AT.finditer(line):
        i = at.end() - 1
        j = i
        while j > 0 and i - j < 64 and line[j - 1] in EMAIL_LOCAL:
            j -= 1
        m = EMAIL_DOMAIN.match(line, i + 1)
        if m:
            yield line[j:m.end()], m.group(0)


def scan_line(where, line, mine, terms, used, ok_domains, hits):
    """Check one line; `where` is the printed location, `mine` its allowlist rows."""
    for i, snip in mine:
        if snip in line:
            line = line.replace(snip, "")
            used.add(i)
    for term, rx in terms:
        if rx.search(line):
            hits.append(f"{where}: [deny: {term}] {mask(line.strip())[:120]}")
    for label, rx in SECRETS:
        for m in rx.finditer(line):
            end = TOKEN_TAIL.match(line, m.end()).end()
            hits.append(f"{where}: [secret: {label}] {m.group(0)[:4]}... ({end - m.start()} chars)")
    if "@" in line:
        for addr, dom in emails(line):
            dom = dom.lower()
            if not any(dom == d or dom.endswith("." + d) for d in ok_domains):
                hits.append(f"{where}: [email] {addr}")
    for m in HOME_PATH.finditer(line):
        if m.group(1).rstrip(".").lower() not in HOME_OK:
            hits.append(f"{where}: [home path] {m.group(0)}")


def scan_text(rel, text, terms, allow, used, ok_domains, hits):
    mine = [(i, s) for i, (f, s) in enumerate(allow) if f == rel]
    for ln, line in enumerate(text.splitlines(), 1):
        scan_line(f"{rel}:{ln}", line, mine, terms, used, ok_domains, hits)


GIT_ESCAPES = {"\\": "\\", '"': '"', "t": "\t", "n": "\n", "r": "\r",
               "a": "\a", "b": "\b", "f": "\f", "v": "\v"}


def read_quoted(s):
    """Decode a Git C-style quoted path at the start of s; return (path, rest after it)."""
    out, i = bytearray(), 1
    while i < len(s) and s[i] != '"':
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            octal = s[i + 1:i + 4]
            if len(octal) == 3 and all(ch in "01234567" for ch in octal):
                out.append(int(octal, 8) & 0xFF)
                i += 4
                continue
            if s[i + 1] in GIT_ESCAPES:
                out += GIT_ESCAPES[s[i + 1]].encode("utf-8")
                i += 2
                continue
        out += c.encode("utf-8")
        i += 1
    return out.decode("utf-8", errors="replace"), s[i + 1:]


def strip_side(path, side):
    return path[2:] if path.startswith(side + "/") else path


def git_path(token, side):
    """The path in a `--- ` / `+++ ` line: quotes decoded, then its a/ or b/ prefix removed."""
    if token.startswith('"'):
        return strip_side(read_quoted(token)[0], side)
    return strip_side(token.split("\t")[0].rstrip("\r\n "), side)


def diff_git_paths(rest):
    """(a-side, b-side) of the text after `diff --git `."""
    rest = rest.rstrip("\r\n")
    if rest.startswith('"'):
        a, tail = read_quoted(rest)
        tail = tail.lstrip(" ")
        b = read_quoted(tail)[0] if tail.startswith('"') else tail
        return strip_side(a, "a"), strip_side(b, "b")
    if rest.endswith('"'):
        k = rest.rfind(' "')
        if k != -1:
            return strip_side(rest[:k], "a"), strip_side(read_quoted(rest[k + 1:])[0], "b")
    n = len(rest)
    if n >= 5 and (n - 5) % 2 == 0:  # a/X b/X with the same X: split in the middle
        k = (n - 5) // 2
        if rest[:2] == "a/" and rest[2 + k:5 + k] == " b/" and rest[2:2 + k] == rest[5 + k:]:
            return rest[2:2 + k], rest[5 + k:]
    k = rest.rfind(" b/")
    if k == -1:
        return "", ""
    return strip_side(rest[:k], "a"), rest[k + 3:]


def scan_stdin(text, terms, allow, used, ok_domains, hits):
    """Scan git log -p (or any text) on stdin, tracking which file each hunk is in.

    A column-0 `diff --git` line opens a file-header zone, where `--- ` and
    `+++ ` lines name the file; the first `@@` line ends the zone. Hunk lines
    start with ' ', '+', '-' or '\\', so only a column-0 `diff --git` or
    `commit <sha>` line can end a hunk; nothing inside one changes the file.
    """
    by_file = {}
    for i, (f, s) in enumerate(allow):
        by_file.setdefault(f, []).append((i, s))
    current, a_side, in_header = "", "", False
    for ln, line in enumerate(text.splitlines(), 1):
        if line.startswith("diff --git "):
            a_side, current = diff_git_paths(line[len("diff --git "):])
            current = current or a_side
            in_header = True
        elif COMMIT_LINE.match(line):
            current, a_side, in_header = "", "", False
        elif in_header:
            if line.startswith("--- "):
                path = git_path(line[4:], "a")
                if path != "/dev/null":
                    a_side = path
            elif line.startswith("+++ "):
                path = git_path(line[4:], "b")
                current = a_side if path == "/dev/null" else path
            elif line.startswith("@@"):
                in_header = False
        where = f"<stdin>:{ln} ({current})" if current else f"<stdin>:{ln}"
        scan_line(where, line, by_file.get(current or "<stdin>", []), terms, used, ok_domains, hits)


def skipped(rel_dir, skips):
    """True when the folder at rel_dir (a/b/c) is excluded by a skip entry."""
    parts = rel_dir.split("/")
    for s in skips:
        if "/" in s:
            if rel_dir == s or rel_dir.startswith(s + "/"):
                return True
        elif s in parts:
            return True
    return False


def walk(root, skips, problems, links):
    """Yield (relative posix path, Path) for every file not under a skipped folder.

    A folder that cannot be listed, or an entry whose type cannot be read, goes
    to problems; a link to a folder, a broken link or a special file to links.
    """
    stack = [""]
    while stack:
        rel_dir = stack.pop()
        try:
            with os.scandir(root / rel_dir if rel_dir else root) as it:
                entries = sorted(it, key=lambda e: e.name)
        except OSError as e:
            problems.append(f"{rel_dir or '.'}/ (cannot list: {e.strerror or e})")
            continue
        subdirs = []
        for e in entries:
            rel = f"{rel_dir}/{e.name}" if rel_dir else e.name
            try:
                if e.is_dir(follow_symlinks=False):
                    if not skipped(rel, skips):
                        subdirs.append(rel)
                    continue
                if e.is_file():
                    yield rel, Path(e.path)
                    continue
            except OSError as ex:
                problems.append(f"{rel} (cannot stat: {ex.strerror or ex})")
                continue
            links.append(rel)
        stack.extend(reversed(subdirs))


def main():
    try:
        sys.stdout.reconfigure(errors="backslashreplace")
    except (AttributeError, ValueError):
        pass
    ap = Parser(description=__doc__.split("\n")[0])
    ap.add_argument("target", help="folder to scan, or - for stdin")
    ap.add_argument("--deny", required=True)
    ap.add_argument("--allow")
    ap.add_argument("--ok-domain", action="append", default=[])
    ap.add_argument("--skip", action="append", default=[], metavar="DIR",
                    help="folder to exclude (repeatable); .git is always excluded")
    a = ap.parse_args()
    try:
        terms, allow = load_terms(a.deny), load_allow(a.allow)
    except SystemExit as e:
        return e.code
    ok = OK_DOMAINS | {d.lower() for d in a.ok_domain}
    skips = [ALWAYS_SKIP]
    for s in a.skip:
        s = s.replace("\\", "/").strip("/")
        if s and s not in skips:
            skips.append(s)
    hits, used, scanned, binary, problems, links = [], set(), 0, [], [], []
    if a.target == "-":
        data = sys.stdin.buffer.read()
        text = decode(data)
        if text is None:
            text = data.decode("utf-8", errors="replace")
        scan_stdin(text, terms, allow, used, ok, hits)
        scanned = 1
    else:
        root = Path(a.target)
        if not root.is_dir():
            say(f"leak_scan: {root} is not a folder")
            return 2
        for rel, p in walk(root, skips, problems, links):
            for term, rx in terms:
                if rx.search(rel):
                    hits.append(f"{rel}: [path name: {term}]")
            try:
                data = p.read_bytes()
            except OSError as e:
                problems.append(f"{rel} (cannot read: {e.strerror or e})")
                continue
            text = decode(data)
            if text is None:
                binary.append(rel)
                continue
            scanned += 1
            scan_text(rel, text, terms, allow, used, ok, hits)
    say(f"leak_scan: {scanned} text input(s) scanned, {len(terms)} deny terms")
    if a.target != "-":
        say(f"  skip list: {', '.join(skips)}")
        say(f"  binary skipped: {len(binary)}")
        for rel in binary:
            say(f"    {rel}")
        if links:
            say(f"  links not followed: {len(links)}")
            for rel in links:
                say(f"    {rel}")
        if problems:
            say(f"  could not read: {len(problems)}")
            for rel in problems:
                say(f"    {rel}")
    for i, (f, s) in enumerate(allow):
        if i not in used:
            say(f"  allowlist UNUSED: {f}: {s!r}")
    if hits:
        say(f"leak_scan: FAIL - {len(hits)} hit(s)")
        for h in hits:
            say("  " + h)
        if problems:
            say(f"leak_scan: INCOMPLETE as well - {len(problems)} path(s) could not be read (listed above)")
        return 1
    if problems:
        say(f"leak_scan: INCOMPLETE - not a PASS: {len(problems)} path(s) could not be read (listed above)")
        return 3
    say("leak_scan: PASS - 0 hits")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # never a traceback that could echo a value unmasked
        say(f"leak_scan: INCOMPLETE - not a PASS: internal error {type(e).__name__}: {e}")
        sys.exit(3)
