#!/usr/bin/env python3
"""PreToolUse guard for the /careful skill.

Reads a Claude Code PreToolUse hook payload from stdin (see
https://code.claude.com/docs/en/hooks) and denies commands that destroy data
or history. Registered on the Bash and PowerShell tools only, for the
duration of the session, via /careful's own SKILL.md frontmatter `hooks:`
block -- see that file for the matcher.

Deny form: exit code 2 with the reason on stderr (the "blocking error" form
documented for PreToolUse hooks -- it blocks unconditionally, unlike the
JSON permissionDecision form, which is only honored on other exit codes).

Everything else -- including any parse or lookup failure -- passes silently:
exit 0, no output. This script never raises; a hook that crashes must never
be the thing that blocks an unrelated command.

How a command is read (no regex over the raw string):
  1. heredoc bodies are cut out of the text and kept aside;
  2. the rest is tokenized quote-aware (shlex, posix, no backslash escapes
     so Windows paths survive); unbalanced quotes fall back to a plain
     whitespace/operator split;
  3. tokens are split into segments on && || ; | & ( ) and newlines;
  4. each segment's program is found after stripping wrappers (sudo, env,
     xargs, nohup, time, command, call, cmd /c, powershell -Command,
     bash -c ...), compared by lowercased basename without .exe;
  5. per-program checks run on that segment's tokens only. The first
     match anywhere in the command denies.

This is an opt-in seatbelt against accidents, not a sandbox: obfuscation
(base64, variable indirection, eval of computed strings) is out of scope.

stdlib only.
"""
import json
import re
import shlex
import sys

# ---------------------------------------------------------------------------
# Tokenizer + segmenter
# ---------------------------------------------------------------------------

# shlex punctuation set: its default "();<>|&" plus newline, so newlines
# outside quotes come out as operator tokens instead of being whitespace.
_PUNCT = "();<>|&\n"
_SEPARATOR_TOKENS = {"&&", "||", "|", "&", "|&", ";", ";;", "(", ")"}
_MAX_DEPTH = 5  # recursion limit for bash -c / cmd /c / heredoc scripts

_HEREDOC_RE = re.compile(r"(?<!<)<<(?!<)-?\s*(['\"]?)([A-Za-z_][\w.-]*)\1")


def _split_heredocs(cmd):
    """Cut heredoc bodies out of `cmd`. Returns (text_without_bodies, bodies).

    The `<<EOF` marker stays in the text (so the segment still shows it was
    fed a heredoc); the body lines up to the delimiter line are removed. An
    unterminated heredoc runs to the end of the text, as in bash."""
    lines = cmd.split("\n")
    out, bodies = [], []
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        i += 1
        for m in _HEREDOC_RE.finditer(line):
            strip_tabs = line[m.start():m.end()].startswith("<<-")
            delim = m.group(2)
            body = []
            while i < len(lines):
                cand = lines[i].lstrip("\t") if strip_tabs else lines[i]
                i += 1
                if cand.strip() == delim:
                    break
                body.append(lines[i - 1])
            bodies.append("\n".join(body))
    return "\n".join(out), bodies


def _tokenize(text):
    """Quote-aware tokens. Unbalanced quotes -> plain whitespace split with
    operators still separated, so the same checks still run (never a silent
    allow of something the fallback would deny)."""
    try:
        lex = shlex.shlex(text, posix=True, punctuation_chars=_PUNCT)
        lex.whitespace_split = True
        lex.escape = ""  # C:\Users\... must keep its backslashes
        lex.whitespace = " \t\r"  # newline is an operator, not whitespace
        lex.commenters = ""  # never hide text after '#' from the checks
        return list(lex)
    except ValueError:
        return re.findall(r"&&|\|\||[;|&()\n]|[<>]+&?|[^\s;|&()<>]+", text)


def _is_operator(tok):
    return bool(tok) and all(c in _PUNCT for c in tok)


def _is_separator(tok):
    if not _is_operator(tok):
        return False
    if "\n" in tok or ";" in tok:
        return True
    return tok in _SEPARATOR_TOKENS or tok.startswith(("&&", "||"))


def _is_redirect(tok):
    return _is_operator(tok) and ("<" in tok or ">" in tok)


_PIPE_TOKENS = {"|", "|&"}
# Block braces ({ ... } in bash and PowerShell script blocks) end a segment.
_BRACE_TOKENS = {"{", "}"}
# Shell keywords stripped from the front of a segment so the command after
# them (`then rm -rf x`, `do git push --force`) is the segment's program.
_SHELL_KEYWORDS = {
    "if", "then", "elif", "else", "fi", "for", "foreach", "while", "until",
    "do", "done", "case", "esac", "function", "!",
}


def _segments(tokens):
    """Split tokens into command segments on separator operators and block
    braces. Returns a list of (pipeline_index, segment_tokens): segments
    joined by `|` share a pipeline index; any other separator starts a new
    pipeline."""
    segs, cur = [], []
    pipeline = 0
    for tok in tokens:
        if _is_separator(tok) or tok in _BRACE_TOKENS:
            if cur:
                segs.append((pipeline, cur))
            cur = []
            if tok not in _PIPE_TOKENS:
                pipeline += 1
        else:
            cur.append(tok)
    if cur:
        segs.append((pipeline, cur))
    return segs


def _heredoc_markers(seg):
    """Count heredoc markers (`<<`, not the `<<<` here-string) in a segment."""
    return sum(1 for t in seg if _is_redirect(t) and t.startswith("<<") and not t.startswith("<<<"))


def _herestrings(seg):
    """Operands of `<<<` here-strings in a segment."""
    return [seg[i + 1] for i, t in enumerate(seg[:-1]) if t.startswith("<<<")]


def _strip_redirects(tokens):
    """Drop redirect operators, their targets, and a bare fd number right
    before them (`2>&1`, `> /dev/null`, `<<EOF`)."""
    out = []
    skip_next = False
    for tok in tokens:
        if skip_next:
            skip_next = False
            continue
        if _is_redirect(tok):
            if out and out[-1].isdigit():
                out.pop()
            skip_next = True
            continue
        out.append(tok)
    return out


def _basename(tok):
    """Lowercased basename with .exe stripped: /usr/bin/git, git.exe and
    C:\\Program Files\\Git\\cmd\\git.exe all give 'git'."""
    base = re.split(r"[\\/]", tok)[-1].lower()
    if base.endswith(".exe"):
        base = base[:-4]
    return base


_ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_XARGS_VALUE_FLAGS = {"-n", "-i", "-l", "-p", "-d", "-e", "-s", "-a", "-I", "-L", "-P", "-E"}
_SUDO_VALUE_FLAGS = {"-u", "-g", "-h", "-p", "-c", "-r", "-t", "-U", "-C", "-D"}
_SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
_POWERSHELLS = {"powershell", "pwsh"}
# Package runners: npx / bunx <pkg>, pnpm [dlx|exec] <pkg>, yarn [dlx|exec]
# <pkg>, npm exec|x <pkg>. Value-taking flags are skipped with their value.
_RUNNER_VALUE_FLAGS = {"-p", "--package", "-C", "--dir", "-F", "--filter", "--cwd", "-w", "--workspace"}
_RUNNER_SUBCOMMANDS = {
    "npx": set(), "bunx": set(), "pnpx": set(),
    "pnpm": {"dlx", "exec"}, "yarn": {"dlx", "exec"}, "npm": {"exec", "x"},
}
_DOCKERS = {"docker", "podman"}
_DOCKER_EXEC_VALUE_FLAGS = {
    "-e", "--env", "--env-file", "-u", "--user", "-w", "--workdir",
    "--detach-keys", "--index", "-H", "--host", "--context", "-f", "--file",
    "-p", "--project-name", "--profile",
}
_SSH_VALUE_FLAGS = {
    "-b", "-B", "-c", "-D", "-E", "-e", "-F", "-I", "-i", "-J", "-L", "-l",
    "-m", "-O", "-o", "-p", "-P", "-Q", "-R", "-S", "-W", "-w",
}
_KUBECTL_VALUE_OPTS = {
    "-n", "--namespace", "--context", "--kubeconfig", "-s", "--server",
    "--cluster", "--user", "--token", "--as", "--as-group", "-l",
}


def _skip_opts(toks, value_flags):
    """Skip leading option tokens; a flag in `value_flags` (compared
    lowercased) also skips its value token. `--flag=value` is one token."""
    lowered = {f.lower() for f in value_flags}
    i = 0
    while i < len(toks) and toks[i].startswith("-") and toks[i] != "--":
        i += 2 if toks[i].lower() in lowered else 1
    return toks[i:]


def _resolve(tokens, depth):
    """Strip wrappers from a segment's tokens.

    Returns ("program", name, args) for a plain segment, ("script", text)
    when a wrapper hands a whole script string to a shell (bash -c "...",
    cmd /c "...", powershell -Command "...", ssh host "..."), or None if
    empty."""
    toks = list(tokens)
    while toks:
        if toks[0] in _SHELL_KEYWORDS:
            toks = toks[1:]
            continue
        prog = _basename(toks[0])
        rest = toks[1:]
        if prog in ("sudo", "doas"):
            toks = _skip_opts(rest, _SUDO_VALUE_FLAGS)
        elif prog == "env":
            i = 0
            while i < len(rest) and (rest[i].startswith("-") or _ENV_ASSIGN_RE.match(rest[i])):
                i += 2 if rest[i] in ("-u", "-C", "-S") else 1
            toks = rest[i:]
        elif prog == "xargs":
            toks = _skip_opts(rest, _XARGS_VALUE_FLAGS)
        elif prog in ("nohup", "call", "exec", "winpty", "&"):
            toks = rest
        elif prog in ("time", "command", "nice"):
            toks = _skip_opts(rest, {"-n"} if prog == "nice" else set())
        elif prog in _RUNNER_SUBCOMMANDS:
            nxt = _skip_opts(rest, _RUNNER_VALUE_FLAGS)
            if nxt and nxt[0].lower() in _RUNNER_SUBCOMMANDS[prog]:
                nxt = _skip_opts(nxt[1:], _RUNNER_VALUE_FLAGS)
            elif prog == "npm":
                return ("program", prog, rest)  # npm run / install: not a wrapper
            toks = nxt
        elif prog in _DOCKERS or prog == "docker-compose":
            nxt = _skip_opts(rest, _DOCKER_EXEC_VALUE_FLAGS)
            if prog != "docker-compose" and nxt and nxt[0].lower() == "compose":
                nxt = _skip_opts(nxt[1:], _DOCKER_EXEC_VALUE_FLAGS)
            if not nxt or nxt[0].lower() != "exec":
                return ("program", prog, rest)
            nxt = _skip_opts(nxt[1:], _DOCKER_EXEC_VALUE_FLAGS)
            toks = nxt[1:]  # drop the container / service name
        elif prog == "ssh":
            nxt = _skip_opts(rest, _SSH_VALUE_FLAGS)
            if len(nxt) < 2:
                return ("program", prog, rest)
            return _script_or_tokens(nxt[1:])  # the remote command
        elif prog == "kubectl":
            nxt = _skip_opts(rest, _KUBECTL_VALUE_OPTS)
            if nxt and nxt[0].lower() == "exec" and "--" in nxt:
                toks = nxt[nxt.index("--") + 1:]
            else:
                return ("program", prog, rest)
        elif _ENV_ASSIGN_RE.match(toks[0]) and not toks[0].startswith("-"):
            toks = rest  # FOO=1 cmd ...
        elif prog == "cmd":
            idx = next((i for i, t in enumerate(rest) if t.lower() in ("/c", "/k")), None)
            if idx is None:
                return ("program", prog, rest)
            return _script_or_tokens(rest[idx + 1:])
        elif prog in _POWERSHELLS:
            idx = next(
                (i for i, t in enumerate(rest)
                 if t.lower() in ("-c", "-command", "/c", "/command", "-com", "-comm", "-comma", "-comman")),
                None,
            )
            if idx is None:
                return ("program", prog, rest)
            return _script_or_tokens(rest[idx + 1:])
        elif prog in _SHELLS:
            for i, t in enumerate(rest):
                if not t.startswith("-"):
                    break
                if not t.startswith("--") and "c" in t[1:]:
                    if i + 1 < len(rest):
                        return ("script", rest[i + 1])
                    return None
            return ("program", prog, rest)
        else:
            return ("program", prog, rest)
    return None


def _script_or_tokens(rest):
    """After cmd /c or powershell -Command: one token is a script string to
    re-parse; several tokens are the command itself."""
    if not rest:
        return None
    if len(rest) == 1:
        return ("script", rest[0])
    return ("script", " ".join(shlex.quote(t) if re.search(r"\s", t) else t for t in rest))


# ---------------------------------------------------------------------------
# Per-program checks. Each takes the segment's args (tokens after the
# program, redirects removed) and returns a matched-pattern name or None.
# ---------------------------------------------------------------------------

def _short_letters(tok):
    """Letters of a bundled short-flag token (`-rf` -> 'rf'), else ''."""
    if tok.startswith("-") and not tok.startswith("--") and len(tok) > 1:
        return tok[1:]
    return ""


def _is_temp_path(path):
    """Path-boundary match against the temp roots: /tmp/, .../AppData/Local/
    Temp/ (and %TEMP%-style variables), or a `scratchpad` path segment.
    `/tmp2/...` is not temp; any `..` segment disqualifies."""
    p = path.replace("\\", "/").lower()
    parts = p.split("/")
    if ".." in parts:
        return False
    if p.startswith("/tmp/"):
        return True
    if p.startswith(("%temp%/", "%tmp%/", "$env:temp/", "$env:tmp/", "$tmpdir/", "${tmpdir}/")):
        return True
    if re.search(r"(^|/)appdata/local/temp/", p):
        return True
    return "scratchpad" in parts


_FALSE_VALUES = ("$false", "false", "0")


def _ps_switch(tok, full, min_len):
    """True if `tok` sets PowerShell switch `full` (e.g. '-recurse'): an
    unambiguous prefix at least `min_len` long, optionally `:value`, where
    an explicit `:$false` turns the switch off."""
    name, _, value = tok.lower().partition(":")
    if len(name) < min_len or not full.startswith(name):
        return False
    return value not in _FALSE_VALUES


def _check_remove_item(args):
    # -r is Remove-Item's only R parameter; -f alone is ambiguous (-Filter),
    # so -Force needs at least -fo.
    has_recurse = any(_ps_switch(t, "-recurse", 2) for t in args)
    has_force = any(_ps_switch(t, "-force", 3) for t in args)
    if has_recurse and has_force:
        return "Remove-Item -Recurse -Force"
    return None


def _check_rd(args):
    # cmd.exe rd / rmdir: /s deletes the whole tree.
    if any(t.lower() == "/s" for t in args):
        return "rd /s / rmdir /s (recursive delete)"
    return _check_remove_item(args)


def _check_rm(args):
    # PowerShell alias form (rm -Recurse -Force) first.
    ps = _check_remove_item(args)
    if ps:
        return ps
    recursive = force = False
    paths = []
    end_of_opts = False
    for tok in args:
        if end_of_opts or not tok.startswith("-") or tok == "-":
            paths.append(tok)
            continue
        if tok == "--":
            end_of_opts = True
            continue
        low = tok.lower()
        if low.partition(":")[0] in ("-recurse", "-force"):
            continue  # PowerShell parameter, handled above
        if low.startswith("--"):
            recursive |= low == "--recursive"
            force |= low == "--force"
            continue
        letters = _short_letters(low)
        recursive |= "r" in letters
        force |= "f" in letters
    if not recursive:
        return None
    if force:
        return "rm -rf / -fr (recursive + force delete)"
    if paths and all(_is_temp_path(p) for p in paths):
        return None
    return "rm -r on a non-temp path (recursive delete)"


def _check_find(args):
    for i, tok in enumerate(args):
        low = tok.lower()
        if low == "-delete":
            return "find -delete"
        if low in ("-exec", "-execdir", "-ok", "-okdir") and i + 1 < len(args):
            if _basename(args[i + 1]) == "rm":
                return "find -exec rm"
    return None


_GIT_VALUE_OPTS = {"-c", "-C", "--git-dir", "--work-tree", "--namespace", "--super-prefix", "--config-env"}


def _git_subcommand(args):
    """Skip git global options; return (subcommand_lowercased, sub_args)."""
    i = 0
    while i < len(args):
        t = args[i]
        if t in _GIT_VALUE_OPTS:
            i += 2
            continue
        if t.startswith("-"):
            i += 1  # --opt=value, or a bare option (--no-pager, -P, --bare, -p)
            continue
        return t.lower(), args[i + 1:]
    return None, []


def _check_git(args):
    sub, rest = _git_subcommand(args)
    if sub is None:
        return None
    low = [t.lower() for t in rest]
    if sub == "push":
        positionals = [t for t in rest if not t.startswith("-")]
        delete = False
        for t in low:
            if t in ("--force", "--force-if-includes", "--mirror") or t.startswith("--force-with-lease"):
                return f"git push {t.split('=')[0]}"
            letters = _short_letters(t)
            if "f" in letters:
                return "git push -f"
            if t == "--delete" or "d" in letters:
                delete = True
        if delete and positionals:
            return "git push --delete / -d (remote ref delete)"
        if any(p.startswith(":") for p in positionals):
            return "git push :ref (remote ref delete)"
        if any(p.startswith("+") for p in positionals):
            return "git push +refspec (force push)"
        return None
    if sub == "reset":
        if "--hard" in low:
            return "git reset --hard"
        return None
    if sub == "clean":
        for t in low:
            if t == "--force":
                return "git clean --force"
            if "f" in _short_letters(t):
                return "git clean -f"
        return None
    if sub == "branch":
        # Case-sensitive on purpose: -d deletes only a merged branch (safe);
        # -D force-deletes regardless (destroys unmerged history).
        delete = force = False
        for t in rest:
            if t == "--delete":
                delete = True
            elif t == "--force":
                force = True
            else:
                letters = _short_letters(t)
                if "D" in letters:
                    return "git branch -D"
                delete |= "d" in letters
                force |= "f" in letters
        if delete and force:
            return "git branch -d/--delete with -f/--force"
        return None
    return None


def _check_kubectl(args):
    i = 0
    while i < len(args):
        t = args[i]
        if t.lower() in _KUBECTL_VALUE_OPTS:
            i += 2
            continue
        if t.startswith("-"):
            i += 1
            continue
        if t.lower() == "delete":
            return "kubectl delete"
        return None
    return None


def _check_terraform(args):
    words = [t.lower() for t in args if not t.startswith("-")]
    flags = [t.lower() for t in args if t.startswith("-")]
    if not words:
        return None
    if words[0] == "destroy":
        return "terraform destroy"
    if words[0] == "apply" and "-destroy" in flags:
        return "terraform apply -destroy"
    return None


_SUPABASE_VALUE_OPTS = {
    "--workdir", "--profile", "-o", "--output", "--dns-resolver", "--network-id",
    "--project-ref", "--db-url",
}


def _supabase_words(args):
    """Positional words of a supabase command, global options skipped."""
    words, i = [], 0
    while i < len(args):
        t = args[i]
        if t.startswith("-"):
            i += 2 if t.lower() in _SUPABASE_VALUE_OPTS else 1
            continue
        words.append(t.lower())
        i += 1
    return words


def _check_supabase(args):
    if _supabase_words(args)[:2] == ["db", "reset"]:
        return "supabase db reset"
    return None


_PROGRAM_CHECKS = {
    "rm": _check_rm,
    "remove-item": _check_remove_item,
    "del": _check_remove_item,
    "ri": _check_remove_item,
    "rd": _check_rd,
    "rmdir": _check_rd,
    "erase": _check_remove_item,
    "find": _check_find,
    "git": _check_git,
    "kubectl": _check_kubectl,
    "terraform": _check_terraform,
    "supabase": _check_supabase,
}


# ---------------------------------------------------------------------------
# SQL: only for SQL clients (or text a command feeds into one).
# ---------------------------------------------------------------------------

_SQL_CLIENTS = {"psql", "mysql", "mariadb", "sqlite3", "sqlite", "sqlcmd", "invoke-sqlcmd", "duckdb"}
_SUPABASE_SQL_WORDS = {"execute", "sql", "query"}
# Programs whose arguments are text that can be piped into a SQL client.
_SQL_FEEDERS = {"echo", "printf", "cat", "write-output", "write-host", "type"}
# A bare SQL statement typed as a command (kept denying from the old guard).
_SQL_KEYWORD_PROGRAMS = {"drop", "truncate", "delete"}


def _clean_sql(sql):
    """Remove -- line comments, /* */ block comments and single-quoted
    string literals ('' escapes included); keep everything else."""
    out = []
    i, n = 0, len(sql)
    while i < n:
        c = sql[i]
        if c == "'":
            i += 1
            while i < n:
                if sql[i] == "'":
                    if i + 1 < n and sql[i + 1] == "'":
                        i += 2
                        continue
                    break
                i += 1
            i += 1
            out.append(" '' ")
        elif sql.startswith("--", i):
            j = sql.find("\n", i)
            i = n if j < 0 else j
        elif sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            i = n if j < 0 else j + 2
            out.append(" ")
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _check_sql_text(sql):
    for stmt in _clean_sql(sql).split(";"):
        words = [w.upper() for w in re.findall(r"[A-Za-z_][A-Za-z0-9_$]*", stmt)]
        if not words:
            continue
        for a, b in zip(words, words[1:]):
            if a == "DROP" and b in ("TABLE", "DATABASE", "SCHEMA"):
                return f"SQL DROP {b}"
        if words[0] == "TRUNCATE":
            return "SQL TRUNCATE"
        has_delete_from = any(a == "DELETE" and b == "FROM" for a, b in zip(words, words[1:]))
        if has_delete_from and "WHERE" not in words:
            return "SQL DELETE FROM without WHERE"
    return None


def _is_sql_client(prog, args):
    if prog in _SQL_CLIENTS:
        return True
    if prog == "supabase":
        return bool(_SUPABASE_SQL_WORDS.intersection(_supabase_words(args)[:3]))
    return False


def _sql_client_texts(args):
    """Every argument of a SQL client is a candidate SQL text (the -c / -e /
    -Q / --command value, a sqlite3 positional script, ...). A `--opt=value`
    token contributes its value. Each is checked on its own."""
    texts = []
    for t in args:
        if t.startswith("-") and "=" in t:
            texts.append(t.split("=", 1)[1])
        elif not t.startswith("-"):
            texts.append(t)
    return texts


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def _check_command(cmd, depth=0):
    if depth > _MAX_DEPTH or not cmd.strip():
        return None
    text, bodies = _split_heredocs(cmd)
    segs = _segments(_tokenize(text))

    # Hand each heredoc body to the segment whose `<<` marker it belongs to.
    # If markers and bodies do not line up, the unassigned bodies go to
    # every pipeline (conservative).
    seg_bodies = []
    k = 0
    for _p, seg in segs:
        n = _heredoc_markers(seg)
        seg_bodies.append(bodies[k:k + n])
        k += n
    orphan_bodies = bodies[k:]

    pipelines = {}  # pipeline index -> [(prog, args, raw_seg, bodies)]
    for (pidx, seg), own_bodies in zip(segs, seg_bodies):
        r = _resolve(_strip_redirects(seg), depth)
        if r is None:
            continue
        if r[0] == "script":
            hit = _check_command(r[1], depth + 1)
            if hit:
                return hit
            continue
        _, prog, args = r
        pipelines.setdefault(pidx, []).append((prog, args, seg, own_bodies))
        fn = _PROGRAM_CHECKS.get(prog)
        if fn:
            hit = fn(args)
            if hit:
                return hit
        if prog in _SQL_KEYWORD_PROGRAMS and not any(a.startswith("-") for a in args):
            hit = _check_sql_text(" ".join([prog] + args))
            if hit:
                return hit

    for records in pipelines.values():
        pipe_bodies = [b for rec in records for b in rec[3]] + orphan_bodies
        pipe_herestrings = [h for rec in records for h in _herestrings(rec[2])]
        has_sql_client = False
        for prog, args, seg, _b in records:
            if _is_sql_client(prog, args):
                has_sql_client = True
                for t in _sql_client_texts(args):
                    hit = _check_sql_text(t)
                    if hit:
                        return hit
        if has_sql_client:
            # Only text fed into the client within this pipeline: feeder
            # arguments, a bare PowerShell string, here-strings, heredocs.
            feeds = pipe_herestrings + pipe_bodies
            for prog, args, seg, _b in records:
                if prog in _SQL_FEEDERS:
                    feeds += [a for a in args if not a.startswith("-")]
                elif seg and re.search(r"\s", seg[0]):
                    feeds.append(seg[0])  # PowerShell: "DROP TABLE t" | psql
            for t in feeds:
                hit = _check_sql_text(t)
                if hit:
                    return hit
        # A heredoc or here-string fed to a shell is a script.
        if any(p in _SHELLS or p in _POWERSHELLS or p == "cmd" for p, _a, _s, _b in records):
            for body in pipe_bodies + pipe_herestrings:
                hit = _check_command(body, depth + 1)
                if hit:
                    return hit
    return None


def check(command):
    """Return a deny reason (str) for `command`, or None to allow it.

    `command` is the shell/PowerShell command text from tool_input.command.
    Program names, flags and SQL keywords compare case-insensitively, except
    git branch's -d/-D, where case carries meaning.
    """
    if not isinstance(command, str) or not command.strip():
        return None
    try:
        matched = _check_command(command)
    except Exception:
        matched = None
    if matched:
        return (
            f"[careful] blocked: matched '{matched}'. This guard stays on "
            "for the rest of the session. Ask the user to run this command "
            "themselves (their own terminal, or the `!` prefix), or start a "
            "fresh session without /careful."
        )
    return None


def main():
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw)
        command = payload.get("tool_input", {}).get("command")
        reason = check(command)
    except Exception:
        reason = None

    if reason:
        sys.stderr.write(reason + "\n")
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
