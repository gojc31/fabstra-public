"""jev_privacy - opt-out and secret-scrub guard shared by the jev CLI and hooks.

Every caller (jev.py, jev-tag.py, jev-agent-guard.py, jev-gate.py) runs
sanitize(cwd, text) before any prompt text leaves the machine for OpenRouter /
TypeSafe. A session whose cwd is listed in assets/jev-skip-dirs.txt (or is
inside a listed folder) sends nothing at all; everything else is sent with
each secret-looking run masked to [REDACTED] per line, so a diff or a config
paste still gets a decision without the secret going out.

The decision fails CLOSED: when assets/jev-skip-dirs.txt cannot be read at
all, load_skip_dirs raises PolicyUnavailable and sanitize sends nothing,
rather than treating an unreadable denylist as an empty one.

allowed()/has_secret() are the older all-or-nothing gate, kept for callers
that want a plain yes/no.
"""
import os
import re

SKIP_DIRS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "jev-skip-dirs.txt")
MAX_SCAN = 20000  # hooks send at most this many chars, so only this much is scanned
# redact_capped() scans the WHOLE text up to this ceiling, never a window
# sized from its cap. Any fixed lookahead is guessable: a pattern whose
# closing delimiter is unbounded - the URL credential `://user:pass@`, the PEM
# block, the trailing runs on `sk-or-v1-` / `xox?-` - can end arbitrarily far
# past the cap, and a span the window could not see was emitted as plain text.
# The ceiling is a cost bound, not a correctness one: every SECRET_PATTERN is
# linear (possessive quantifiers), the hooks send at most MAX_SCAN chars, and
# a 1 MB scan finishes in well under a second, far inside the 7 s deadline.
REDACT_CEILING = 1_000_000
# The hooks only ever SEND MAX_SCAN chars, so scanning a prompt larger than
# this buys nothing but wall clock inside the 7 s deadline - a real prompt is
# never this big, a pasted log or a dumped binary is. The three hooks
# (jev-tag, jev-agent-guard, jev-gate) cut the RAW prompt to this ceiling
# BEFORE redaction; the CLI and the roster keep the full REDACT_CEILING.
# Accepted limit: a secret straddling the 200 KB mark in a hook prompt is not
# seen, exactly as one past REDACT_CEILING is not.
HOOK_REDACT_CEILING = 200_000
REDACTED = "[REDACTED]"

# BUMP THIS ON EVERY CHANGE TO WHAT REDACTION DOES - the patterns below, _mask,
# _spans, the ceilings, anything that changes what leaves the machine.
# Callers that PERSIST redacted text (jev_skills' roster cache) stamp this
# number and throw their cache away when it no longer matches, so text masked
# by a superseded sanitizer can never be replayed out of a cache after the
# rules were repaired.
#   1-4: the rounds before N18, none of them stamped anywhere.
#   5: N20 - anchored keyword / JWT / URL-credential patterns.
#   6: PEM spans moved out of SECRET_PATTERNS into a linear cursor pass in
#      _spans(); has_secret() checks PEM_BEGIN_RE directly. Redacted output
#      is unchanged - only how it is computed.
#   7: N22/N23 - round 5's anchors were too strict on diff and Markdown text.
#      The URL-credential lookbehind is gone (a "-"/"+" diff marker before
#      the scheme blocked it) and the JWT lookbehind no longer counts "_"
#      and "-" as identifier characters. More text is masked than under 6,
#      so persisted output from 6 must not be replayed.
#   8: N24-N27 - recall repairs. The JWT header minimum drops to 14 (a valid
#      `{"alg":"HS256"}` header encodes to 20 chars, not the 23 round 7
#      demanded) and the signature segment is masked too; the keyword value
#      may be a QUOTED string containing spaces; the keyword identifier may
#      carry Markdown decoration and the value may be a YAML block scalar or
#      carry a `!!tag`; the URL credential accepts the JSON-escaped `:\/\/`
#      spelling. Strictly more text is masked than under 7, so persisted
#      output from 7 must not be replayed.
#   9: R1/R2 - round 8 replaced the plain keyword value run with a QUOTED
#      string that needs its closing quote on the same line, instead of
#      trying the quoted form ahead of it. An unclosed quote (`password="x`)
#      and a quote that closes on the NEXT line then masked nothing at all -
#      strictly less than round 7 masked. The run is back as a fallback
#      behind an optional leading quote. The JWT segments are bounded
#      (4096/8192/2048) so a run of `_eyJ` near-matches stays linear at the
#      1 MB ceiling; no real token approaches those sizes, so nothing round 8
#      detected stops being detected. More text is masked than under 8, so
#      persisted output from 8 must not be replayed.
#   10: the closed-quote value alternative could span from one assignment's
#       opening quote to the NEXT assignment's opening quote on the same
#       line ("password=\"SSSS password=\"SSSS" masked only the first run,
#       inside one merged span, and leaked the second value). Each inner
#       character of that alternative now also excludes the start of a fresh
#       `[:=]<space>*<quote>` sequence, so it fails on the run-together case
#       and falls back to the unquoted alternative for the first value while
#       the second assignment matches on its own. Strictly more text is
#       masked than under 9, so persisted output from 9 must not be replayed.
#   11: G1 - round 10's inner `(?![:=]\s*["'])` guard rejected a value whose
#       OWN last character is "=" or ":" (a base64 password ends in "="), so
#       `password="aB3! four strong random words="` and its ":" twin matched
#       nothing at all, and an inner `='` (`password="aB3! code='demo'"`)
#       broke the branch too. The guard is gone; the CLOSING quote is defined
#       structurally instead - it must be followed by end of text,
#       whitespace, or one of ",;)]}" - which still fails the run-together
#       `password="SSSS password="SSSS` shape round 10 repaired.
#   11: G2 - round 9's JWT segment bounds (4096/8192/2048) dropped a real
#       signed token with a long `kid` header (4182 chars) outright and
#       emitted the 622-character tail of an 8814-character payload. All
#       three bounds are 16384 now: still a cost bound on a near-match run
#       (the 1 MB `_eyJ`/`-eyJ` probes measure 0.38-0.62 s, against 1.98-2.97
#       at 65536), and far above any real token. ACCEPTED LIMIT: a single
#       JWT segment longer than 16 KB is not masked - no real-world token
#       approaches it, and the 200 KB hook path is unaffected either way.
#       Strictly more text is masked than under 10, so persisted output from
#       10 must not be replayed.
#   12: round 11's closing-quote lookahead (`(?=\s|$|[,;)\]}])`) only
#       accepted a fixed set of closer characters, so a closing quote
#       immediately followed by anything else - an XML close angle-bracket
#       (`password="aB3! four strong random words"></user>`), a Markdown
#       code-span backtick (`` `DB_PASSWORD="aB3! four strong random
#       words"` ``), or a sentence-ending period - failed the branch
#       outright and fell back to the unquoted alternative, which cannot
#       start on a value containing spaces, so the whole passphrase leaked.
#       The lookahead is now the NEGATIVE `(?![A-Za-z0-9_])`: a closing
#       quote may be followed by anything except a word character. The only
#       shape this must still reject is the run-together
#       `password="SSSS password="SSSS` case, where the lone candidate
#       closer is followed by another word character (the second value) -
#       that still fails, so round 10/11's repair is untouched. Strictly
#       more text is masked than under 11, so persisted output from 11 must
#       not be replayed.
#   13: round 12's closed-quote body read one character at a time and only
#       excluded the bare quote character, with no notion of escaping. A
#       JSON-serialized value containing an escaped quote -
#       `{"password": "aB3! code=\"demo\""}`, exactly what
#       `json.dumps({"password": 'aB3! code="demo"'})` produces - stopped
#       the body one position early: the character right after the
#       backslash IS the quote, so the body's exclusion rejected it as a
#       body character, and the engine tried to close there. The character
#       after that candidate closer is "d" (from "demo"), a word character,
#       so the closer condition failed and the whole closed-quote branch
#       failed outright (the body is possessive, so it cannot backtrack to
#       try a later quote as the closer). The unquoted fallback then needs
#       6+ non-space non-quote characters and found only "aB3!" (4) before
#       the space, so NOTHING masked at all - a regression against v8/v10,
#       which at least masked the "aB3! code=" prefix. The body is now
#       escape-aware: a body character is either a backslash followed by
#       any non-newline character, or a non-backslash, non-newline
#       character that is not the quote. A backslash now consumes the
#       following character as content instead of leaving it to be
#       misread as a candidate closer, so the branch runs past every
#       escaped quote and closes only at the real one - masking the JSON
#       case whole, which is MORE than v8/v10 masked. Still possessive and
#       still one alternation per character, so the linear-time guarantee
#       (test_keyword_quoted_run_linear) is unchanged. Strictly more text
#       is masked than under 12, so persisted output from 12 must not be
#       replayed.
#   14: round 13's escape-aware closed-quote body treats a literal
#       backslash right before what would otherwise be the closer as an
#       ESCAPE of that quote, even when the backslash is not an escape at
#       all - it is the value's own last character. XML from
#       `xml.dom.minidom` (`<user name="demo" password="aB3! four strong
#       random words\"/>`) and a shlex-quoted shell export
#       (`export DB_PASSWORD='aB3! four strong random words\'`) both end
#       their value in one literal backslash immediately before the real
#       closing quote: the escape-aware body reads that backslash-quote
#       pair as an escaped quote, consumes it as content, and then finds
#       no closer left on the line at all - the branch fails outright, and
#       the unquoted fallback cannot start on a value containing spaces,
#       so NOTHING masked - a regression against v8/v10/v12, which at
#       least masked the whole value. The escape-aware closed form stays
#       as the FIRST alternative (it is still needed for a JSON-serialized
#       value with a genuinely escaped quote, `{"password": "aB3!
#       code=\"demo\""}`), but a second, LITERAL closed form - no escape
#       handling, the body just excludes the quote character, exactly
#       round 12's body - now sits behind it as the SECOND alternative,
#       ahead of the unquoted fallback. On the XML and shell shapes,
#       alternative 1 fails for the reason above, alternative 2's body
#       treats the backslash as an ordinary character and finds the real
#       closer right after it, so the whole value masks. On the JSON case,
#       alternative 1 still succeeds first (the closer right after `\"` is
#       followed by `}`), so that repair is untouched. Both closed bodies
#       are possessive, so the linear-time guarantee is unchanged. Strictly
#       more text is masked than under 13, so persisted output from 13
#       must not be replayed.
SANITIZER_VERSION = 14

# Git Bash renders "C:\x" as "/c/x"; a cwd in that form must still match a
# listed Windows folder. POSIX has real "/c/..." paths, so this rewrite runs
# on Windows only.
GIT_BASH_DRIVE_RE = re.compile(r"^/([A-Za-z])/")


class PolicyUnavailable(Exception):
    """The opt-out policy file could not be read.

    Raised by load_skip_dirs() so callers FAIL CLOSED: an unreadable denylist
    must never be treated as an empty one. An existing file with zero entries
    is a valid empty policy and does not raise.
    """

# Used by has_secret() and _spans() to find a PEM block's BEGIN/END markers.
# PEM spans are NOT found via SECRET_PATTERNS below - a pattern with an
# optional END half (`(?:[\s\S]*?-----END...-----)?`) is a lazy rescan to EOF
# every time the END is not found immediately, and on a run of unterminated
# BEGIN headers that rescan repeats per header: O(n*m) on m repeats (4.57s at
# the 200KB hook ceiling, unbounded at the 1MB REDACT_CEILING). _spans() below
# instead walks PEM_BEGIN_RE matches in source order with a cursor and stops
# at the first BEGIN with no END, so the whole pass is one O(n) scan
# regardless of how many BEGINs precede the unterminated one.
PEM_BEGIN_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
PEM_END_RE = re.compile(r"-----END [A-Z ]*PRIVATE KEY-----")

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    # The three patterns below carry a trailing run so redact() masks the whole
    # token, not just the marker. The run is optional, so has_secret() still
    # matches a bare marker exactly as it did before.
    re.compile(r"sk-or-v1-[A-Za-z0-9_-]*"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"xox[abp]-[A-Za-z0-9-]*"),
    # A JWT never starts in the middle of a WORD, so the lookbehind ends the
    # rescan that a run of "eyJaaaa..." near-matches used to start at every
    # repeat: each inner "eyJ" there is preceded by a letter, so only the
    # first repeat is ever a candidate start. It counts letters and digits
    # only - "_" and "-" are punctuation in the text a reviewer pastes (a
    # removed diff line "-eyJ...", Markdown emphasis "_eyJ..._"), and
    # treating them as identifier characters hid a complete signed token.
    # The segment runs are possessive; "." is outside their class, so the dot
    # that ends the first segment is still found.
    # The HEADER minimum is 14 characters after "eyJ", not 20: the shortest
    # real protected header is `{"alg":"HS256"}` ("typ" is optional), which
    # encodes to the 20-character "eyJhbGciOiJIUzI1NiJ9" - three short of the
    # 23 the old run demanded, so a complete signed token with ordinary
    # indented claims was invisible. `{"alg":"none"}` encodes to 18, so 14 is
    # the safe floor.
    # The THIRD segment is masked as well: a signature alone is useless, but
    # there is no reason to send it. It stays OPTIONAL rather than mandatory
    # because a two-segment "eyJ<header>.<payload>" blob is still
    # secret-shaped and has been detected since round 1; making the dot
    # mandatory would DROP that detection.
    # Each segment run is BOUNDED as well as possessive (16384 per
    # segment). The lookbehind counts letters and
    # digits only, so every repeat of a "_eyJaaa..." near-match is a fresh
    # candidate start, and with an unbounded run each start consumed the
    # whole remaining input: 15.1 s on the 1 MB CLI ceiling, measured (the
    # 200 KB hook ceiling stayed at 0.5 s, so only the CLI was exposed).
    # The bounds cap the per-start work instead. Round 9 set them at
    # 4096/8192/2048, which looked far above any real token and was not: a
    # signed token with a long `kid` header (4182 characters) stopped
    # matching altogether, and an 8814-character payload matched only its
    # first 8192, leaking the 622-character tail and the signature as plain
    # text. 16384 per segment keeps the per-start work bounded - a 1 MB run
    # of `_eyJ`/`-eyJ` near-matches measures 0.38 s sparse and 0.62 s dense,
    # against 1.98 s / 2.97 s at 65536 - while sitting far past any token a
    # real system issues (a long-`kid` header is ~4 KB, a fat claim set ~9
    # KB). ACCEPTED LIMIT, documented rather than silently missing: a single
    # segment longer than 16 KB is not masked. Cost is linear in the bound,
    # so raising it to cover such a segment costs the 1 MB CLI scan
    # proportionally; the 200 KB hook path stays well inside the 7 s
    # deadline at either value.
    re.compile(
        r"(?<![A-Za-z0-9])eyJ[A-Za-z0-9_-]{14,16384}+\.[A-Za-z0-9_-]{20,16384}+"
        r"(?:\.[A-Za-z0-9_-]{10,16384}+)?"
    ),
    re.compile(r"sk_(?:live|test)_[A-Za-z0-9]{10,}"),
    re.compile(r"rk_(?:live|test)_[A-Za-z0-9]{10,}"),
    re.compile(r"(?i)\bBearer\s++[A-Za-z0-9._~+/=-]{16,}"),
    # A URL credential, matched from the SCHEME rather than from a bare "://"
    # so a scheme cannot restart inside a longer identifier run. There is NO
    # lookbehind: one that forbade "+", "-" and "." before the scheme also
    # forbade the "-"/"+" markers of a unified diff, and a connection-string
    # diff - the most ordinary way a database password is pasted - then made
    # zero substitutions.
    # Two bounds replace it, because the lookbehind was also carrying the
    # linear-time property. (1) The scheme run is CAPPED at 32 characters: a
    # real scheme is a few bytes, while an unbounded run made every letter of
    # a long alphanumeric blob a candidate start that scanned to the blob's
    # end - 15.5 s on 200 KB of letters, measured, i.e. past the 7 s hook
    # deadline well inside the hook ceiling. (2) The possessive password run
    # excludes "/" as well as "@" (RFC 3986 userinfo cannot hold a literal
    # "/" - it would end the authority), so a repeated "https://u:bbbbbbbbbb"
    # near-match fails at each candidate start instead of rescanning the tail
    # - 78 s on a 1 MB input before that exclusion. With both, 1 MB of
    # letters is 0.04 s and the 1 MB near-match probe 0.09 s.
    # The separator is written `:(?:\\?/){2}` so the JSON-escaped spelling
    # `postgres:\/\/alice:...@host` - what a serialized config looks like
    # when it is pasted as prose - matches as well as the literal "://". For
    # the same reason "\\" joins the excluded set of both userinfo runs: the
    # password must stop at the "\/" that opens the path, not swallow it.
    re.compile(r"[A-Za-z][A-Za-z0-9+.-]{0,31}+:(?:\\?/){2}[^/\s:@\\]++:[^@\s/\\]{3,}+@"),
    # Possessive quantifiers (Python 3.11+) around the identifier/whitespace
    # runs keep this linear-time: without them, a long run of keyword-charset
    # bytes with no ":"/"=" (e.g. has_secret("password" * 2500)) backtracks
    # catastrophically. The anchoring is the other half of that bound. The
    # match now starts at the IDENTIFIER, not at the keyword inside it: the
    # lookbehind allows only one candidate start per identifier run, and the
    # LAZY lookahead ("does a keyword appear anywhere in this run?") commits
    # once instead of retrying the possessive tail at every keyword repeat -
    # "password" * 40000 used to be 40000 rescans of the whole run.
    # Behaviour is unchanged on real assignments: the identifier before the
    # keyword ("DB_PASSWORD=", "my-token:") was already emitted as plain text
    # ahead of the span, and _mask still preserves everything up to `val`.
    # "-" joins the identifier class so "api-key: x" is still one run, and
    # the lookbehind excludes "-" for the same reason: a leading "-"/"+" on a
    # diff line is already a legal start (the character before it is a
    # newline), so "-DB_PASSWORD=x", "+api-key: x" and "_password_: x" all
    # match as they are - while allowing a start after a "-" would make every
    # dash of a "-----" separator line a fresh candidate whose LAZY keyword
    # lookahead rescans the rest of the run: 8.6 s on a 20 KB run of dashes,
    # measured, i.e. past the 7 s hook deadline on an everyday input.
    #
    # The VALUE is an alternation, because a real secret is not always a run
    # of non-space characters:
    #   * a QUOTED string may contain spaces - `DB_PASSWORD='aB3! four words'`
    #     leaked whole under the old run, and `password="Tr0ub4dor & more"`
    #     kept everything after its first word. The quoted branch is tried
    #     FIRST (an optional leading quote tried greedily would let the
    #     unquoted branch win on the first word again) and the quotes are
    #     inside `val`, so the whole literal goes. That branch needs its
    #     CLOSING quote on the SAME line, so it is only an ADDITION to the
    #     plain run, never a replacement for it: an unclosed quote
    #     (`password="secret`, a truncated paste) and a quote that closes on
    #     the NEXT line both fail it, and round 8 - which had dropped the run
    #     - then masked nothing at all, less than round 7 did. The run is
    #     back as the SECOND alternative behind an optional leading quote,
    #     so those shapes mask exactly as they did before round 8;
    #     round 10: the closed-quote branch's inner class only excluded the
    #     quote character itself, so on `password="SSSS password="SSSS` it
    #     ran straight past the first value's unclosed-looking opening quote,
    #     through the space, and adopted the SECOND assignment's opening
    #     quote as its own closer - one span covering both assignments, and
    #     the second value's content never got its own match. Round 10
    #     excluded any inner character about to start a fresh
    #     `[:=]<space>*<quote>` sequence, which also rejected a value's OWN
    #     trailing "=" or ":" - a base64 password ends in "=" - and an inner
    #     `='`, so `password="aB3! four strong random words="` and
    #     `password="aB3! code='demo'"` went out whole (round 11 / G1).
    #     Round 11 defines the CLOSING quote structurally instead: it must be
    #     followed by end of text, whitespace, or one of ",;)]}"
    #     (`(?=\s|$|[,;)\]}])`). The body is possessive and cannot hold the
    #     quote character, so on `password="SSSS password="SSSS` the only
    #     candidate closer is the second assignment's quote, which is
    #     followed by "S": the branch fails outright, the unquoted fallback
    #     masks the first run, and the second assignment matches fresh on its
    #     own. An "=" inside an otherwise normal quoted value
    #     (`password="ab=cd ef gh"`) is just content and masks whole;
    #   * a YAML BLOCK SCALAR puts the value on the next line behind a `|`/`>`
    #     indicator. The indicator plus its indentation is matched by `blk`
    #     and kept, and a CONDITIONAL - `(?(blk)...|...)` - lets only that
    #     branch take a whole line (`[^\r\n]{3,}+`); an inline value must
    #     still be quoted or a 6-character non-space run, so ordinary prose
    #     after a colon is not swallowed.
    # An optional `!!tag ` before the value covers YAML's explicit tags.
    # The IDENTIFIER may carry up to three Markdown decoration characters on
    # each side (`**password**:`, `` `api_key`: ``, `*password*:`); "_" is in
    # the identifier class already. Those characters are outside the
    # lookbehind's class, so each one is a fresh candidate start - the
    # lookahead is bounded (it may skip at most 3 of them before it needs
    # keyword characters), which keeps a 200 KB run of "*", "`" or "~" linear
    # exactly as the dash run is.
    # Accepted ceilings, documented rather than silently missing:
    #   * only the FIRST content line of a block scalar is masked;
    #   * a Markdown TABLE cell (`| password | hunter2 |`) is NOT masked -
    #     there is no separator between key and value, and anchoring on the
    #     pipe would treat every table row as an assignment;
    #   * a YAML ANCHOR (`password: &name value`) masks the anchor, not the
    #     value after it.
    # bench/jev-privacy-cases.py carries all three as xfail cases.
    re.compile(
        r"(?i)(?<![A-Za-z0-9_-])"
        r"(?=[*_`~]{0,3}[A-Za-z0-9_-]*?(?:password|passwd|secret|api[_-]?key|"
        r"access[_-]?key|private[_-]?key|service[_-]?role|token))"
        r"[*_`~]{0,3}+[A-Za-z0-9_-]++[*_`~]{0,3}+[\"']?\s*+[:=]\s*+"
        r"(?:!![A-Za-z0-9_.+-]*+[ \t]++)?"
        r"(?P<blk>[|>][+-]?[ \t]*\r?\n[ \t]++)?"
        r"(?P<val>(?(blk)[^\r\n]{3,}+|"
        r"(?:(?P<q>[\"'])(?:\\[^\r\n]|(?!(?P=q))[^\r\n\\]){6,}+(?P=q)(?![A-Za-z0-9_])"
        r"|(?P<q2>[\"'])(?:(?!(?P=q2))[^\r\n]){6,}+(?P=q2)(?![A-Za-z0-9_])"
        r"|[\"']?+[^\s\"']{6,}+)))"
    ),
]


def canonical_dir(path: "str | None") -> str:
    """One comparable form for a folder: Git-Bash drive rewrite, realpath, normcase.

    realpath resolves the aliases a lexical abspath misses - an 8.3 short name
    ("C:\\CLIENT~1") and the "\\\\?\\" extended prefix both collapse onto the real
    path. A path that does not exist (or a realpath that raises) falls back to
    the lexical form, which is what the old comparison used.
    """
    if not path:
        return ""
    text = str(path).strip()
    if os.sep == "\\":
        m = GIT_BASH_DRIVE_RE.match(text)
        if m:
            text = m.group(1).upper() + ":\\" + text[3:]
        # realpath keeps the extended-length prefix, so strip it first.
        if text.startswith("\\\\?\\UNC\\"):
            text = "\\\\" + text[8:]
        elif text.startswith("\\\\?\\"):
            text = text[4:]
    try:
        canon = os.path.realpath(os.path.abspath(text))
    except (OSError, ValueError):
        canon = os.path.abspath(text)
    return os.path.normcase(canon)


def load_skip_dirs(path=SKIP_DIRS_FILE) -> "list[str]":
    """The listed opt-out folders, canonicalised. Raises PolicyUnavailable when unreadable."""
    try:
        with open(path, encoding="utf-8-sig") as f:
            lines = f.readlines()
    except UnicodeError:
        # Not a missing file - it opened, but wasn't valid UTF-8 (e.g. a
        # UTF-16 file from PowerShell's `>` redirect). Retry once with
        # utf-16; if that also fails the policy is unavailable.
        try:
            with open(path, encoding="utf-16") as e2:
                lines = e2.readlines()
        except Exception as e:
            raise PolicyUnavailable("%s: %s" % (path, type(e).__name__)) from e
    except OSError as e:
        raise PolicyUnavailable("%s: %s" % (path, type(e).__name__)) from e
    except Exception as e:
        raise PolicyUnavailable("%s: %s" % (path, type(e).__name__)) from e
    dirs = []
    for line in lines:
        line = line.strip().strip('"').strip("'").strip()
        if not line or line.startswith("#"):
            continue
        dirs.append(canonical_dir(line))
    return dirs


def cwd_is_skipped(cwd: "str | None", skip_dirs=None) -> bool:
    """True when cwd is, or sits inside, a listed folder. Propagates PolicyUnavailable."""
    if not cwd:
        return False
    if skip_dirs is None:
        # Reference the module global by name (not a bound default arg) so
        # monkeypatching SKIP_DIRS_FILE at test time takes effect.
        skip_dirs = load_skip_dirs(SKIP_DIRS_FILE)
    norm_cwd = canonical_dir(cwd)
    for d in skip_dirs:
        # Canonicalise here too: a caller may hand in a plain lexical list.
        d = canonical_dir(d)
        if not d:
            continue
        if norm_cwd == d:
            return True
        if norm_cwd.startswith(d.rstrip(os.sep) + os.sep):
            return True
    return False


def has_secret(text: str) -> bool:
    if not text:
        return False
    text = text[:MAX_SCAN]
    # Checked directly, not via SECRET_PATTERNS: PEM detection here only needs
    # the BEGIN marker's presence, and PEM_BEGIN_RE alone has no optional
    # lazy-to-EOF half, so it stays linear even on a run of bare headers.
    if PEM_BEGIN_RE.search(text):
        return True
    return any(p.search(text) for p in SECRET_PATTERNS)


def allowed(cwd, text) -> bool:
    return not cwd_is_skipped(cwd) and not has_secret(text)


def _mask(m) -> str:
    """Replace a matched secret with REDACTED.

    The keyword pattern (the last one in SECRET_PATTERNS) carries a named
    group `val` around the value only, so `password: hunter2` keeps the
    identifier and the separator and loses just the value. Every other
    pattern matches the secret itself, so the whole match goes.
    """
    try:
        val_start = m.start("val")
    except (IndexError, re.error):
        return REDACTED
    if val_start < 0:
        return REDACTED
    return m.group(0)[: val_start - m.start(0)] + REDACTED


def _spans(window: str) -> "list[tuple[int, int, str]]":
    """Every detected secret as (start, end, replacement) in SOURCE coordinates.

    Overlapping or adjacent spans are merged into their UNION, and a merged
    span is always replaced by [REDACTED] whole. The identifier-preserving
    replacement of the keyword pattern (`password: [REDACTED]`) therefore
    survives only on a keyword span that overlaps nothing: when another
    pattern matched INSIDE the identifier - "token_ghp_QQQ...=hunter2" - that
    identifier is itself a secret, and keeping it copied the whole token into
    the output.

    Every pattern is matched against the ORIGINAL window, never against a
    partly-masked copy, so a position in a span is a position in the caller's
    own text.
    """
    found: "list[tuple[int, int, str]]" = []

    # PEM private-key blocks, one linear left-to-right pass with a cursor -
    # not via SECRET_PATTERNS (see the comment above PEM_BEGIN_RE for why).
    # Each BEGIN at or after the cursor is paired with the nearest END that
    # follows it: found -> span (b, e_end), cursor moves to e_end so a BEGIN
    # inside an already-emitted span is skipped. A BEGIN with no END anywhere
    # after it in the window swallows the rest of the window as one span and
    # stops the scan outright - the body cannot ride along past the window's
    # end, and no later BEGIN needs walking once the scan has given up.
    cursor = 0
    for begin_match in PEM_BEGIN_RE.finditer(window):
        b = begin_match.start()
        if b < cursor:
            continue
        end_match = PEM_END_RE.search(window, begin_match.end())
        if end_match:
            e = end_match.end()
            found.append((b, e, REDACTED))
            cursor = e
        else:
            found.append((b, len(window), REDACTED))
            break

    for pattern in SECRET_PATTERNS:
        for m in pattern.finditer(window):
            if m.end() > m.start():
                found.append((m.start(), m.end(), _mask(m)))

    found.sort(key=lambda s: (s[0], -s[1]))
    merged: "list[tuple[int, int, str]]" = []
    for start, end, replacement in found:
        if merged and start <= merged[-1][1]:
            prev_start, prev_end, _prev_replacement = merged[-1]
            # UNION, and the merged span loses any identifier-preserving
            # replacement: a span built from two raw spans is masked whole.
            merged[-1] = (prev_start, max(prev_end, end), REDACTED)
            continue
        merged.append((start, end, replacement))
    return merged


def redact_capped(text: str, cap: int) -> "tuple[str, int]":
    """Mask every secret-looking run and return at most `cap` chars.

    Returns (masked_text, spans_emitted). The one place a cap and a redaction
    meet: cutting redacted text to a length is unsafe, because a replacement
    is shorter than the secret it replaces, so an earlier substitution slides
    a later, incompletely-masked token back under the cap. The cap is
    therefore applied in SOURCE coordinates while the output is built:

      (a) the cap is reached inside plain text -> cut there;
      (b) the cap falls inside a span -> the span's replacement is emitted
          WHOLE and nothing after it is emitted (the tail beyond a straddling
          secret is dropped);
      (c) the output itself would pass `cap` (replacements can be longer than
          what they replace) -> plain text is cut to fit, and a replacement
          that would not fit is dropped along with everything after it.

    Spans are collected over text[:REDACT_CEILING] - the whole input, not a
    window sized from the cap - so a secret whose closing delimiter lies far
    past the cap is still detected, and rule (b) then drops it and its tail.

    Invariants: len(output) <= cap, and no source character belonging to a
    detected span ever appears in the output.
    """
    if not text or cap <= 0:
        return ("" if cap <= 0 else text), 0
    window = text[:REDACT_CEILING]
    out: "list[str]" = []
    out_len = 0
    pos = 0
    emitted = 0

    for start, end, replacement in _spans(window):
        if end <= pos:
            continue
        if start > pos:
            plain = window[pos:start]
            take = min(len(plain), cap - pos, cap - out_len)
            if take > 0:
                out.append(plain[:take])
                out_len += take
                pos += take
            if take < len(plain):
                return "".join(out), emitted  # (a) / (c) in plain text
        if start >= cap or out_len + len(replacement) > cap:
            return "".join(out), emitted  # (c) no room for the replacement
        out.append(replacement)
        out_len += len(replacement)
        emitted += 1
        pos = end
        if end > cap:
            return "".join(out), emitted  # (b) straddling secret: drop the tail

    tail = window[pos:cap]
    if tail:
        out.append(tail[:max(0, cap - out_len)])
    return "".join(out), emitted


def redact(text: str) -> "tuple[str, int]":
    """Mask every secret-looking run, then return at most MAX_SCAN chars."""
    return redact_capped(text, MAX_SCAN)


def skip_reason(cwds: "list[str | None]") -> "str | None":
    """Why this send is blocked: "policy" (denylist unreadable), "optout", or None.

    "policy" is the fail-closed case: the denylist could not be read at all, so
    we cannot know whether these folders are opted out and send nothing.
    """
    try:
        skip_dirs = load_skip_dirs(SKIP_DIRS_FILE)
    except Exception:
        return "policy"
    try:
        for cwd in cwds:
            if cwd_is_skipped(cwd, skip_dirs):
                return "optout"
    except Exception:
        return "policy"
    return None


def sanitize_many(cwds: "list[str | None]", text: str) -> "tuple[str | None, int]":
    """sanitize() over several folders at once: any one of them listed blocks the send."""
    try:
        checked = [c for c in cwds if c] or [os.getcwd()]
        if skip_reason(checked) is not None:
            return None, 0
        return redact(text)
    except Exception:
        return None, 0


def sanitize(cwd: "str | None", text: str) -> "tuple[str | None, int]":
    """Privacy gate for one outbound request.

    Returns (None, 0) when nothing may be sent - the cwd is opted out, the
    policy file is unreadable, or the check itself failed - and
    (masked_text, substitutions) otherwise, with len(masked_text) <= MAX_SCAN.
    A caller that passes no cwd is checked against the process cwd.
    """
    return sanitize_many([cwd], text)
