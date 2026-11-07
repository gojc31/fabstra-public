"""Tests for leak_scan.py. Run from the skill folder:

  python -m unittest discover -s scripts/tests -q

Key-, email- and path-shaped fixtures are built by concatenation at run time,
so this file holds no value the leak gate itself would flag.
"""
import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "leak_scan.py"
SKILL = HERE.parent.parent

ANT = "sk-" + "ant-" + "A" * 30
OPENAI = "sk-" + "proj-" + "B" * 30
GITHUB = "gh" + "p_" + "c" * 36
AWS = "AK" + "IA" + "D" * 16
AWS_TEMP = "AS" + "IA" + "E" * 16
SLACK = "xo" + "xb-" + "1" * 12
WIN = "C:" + "\\"
USERS = "Users" + "\\"
AT = "@"


def run(args, stdin=None, timeout=60):
    p = subprocess.run([sys.executable, str(SCRIPT), *args], input=stdin,
                       capture_output=True, timeout=timeout)
    out = p.stdout.decode("utf-8", "replace") + p.stderr.decode("utf-8", "replace")
    return p.returncode, out


def load_module():
    """Import a fresh copy of leak_scan for in-process tests (no bytecode written)."""
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("leak_scan_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_inproc(args):
    """Run leak_scan.main() in this process; return (exit code, stdout + stderr)."""
    mod = load_module()
    out, err = io.StringIO(), io.StringIO()
    with mock.patch.object(sys, "argv", ["leak_scan.py", *args]), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = mod.main()
        except SystemExit as e:
            code = e.code
    return code, out.getvalue() + err.getvalue()


def failing_read_bytes(bad_name):
    real = Path.read_bytes

    def fake(self):
        if self.name == bad_name:
            raise PermissionError(13, "Permission denied", str(self))
        return real(self)
    return fake


def failing_scandir(bad_name):
    real = os.scandir

    def fake(path="."):
        if os.path.basename(os.fspath(path).rstrip("\\/")) == bad_name:
            raise PermissionError(13, "Permission denied", os.fspath(path))
        return real(path)
    return fake


def remove_tree(path):
    """Delete a temp tree; Windows may hold a folder a moment after a subprocess exits."""
    for _ in range(10):
        shutil.rmtree(path, ignore_errors=True)
        if not os.path.exists(path):
            return
        time.sleep(0.2)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "repo"
        self.root.mkdir()
        self.deny = self.tmp / "deny.txt"
        self.deny.write_text("", encoding="utf-8")

    def tearDown(self):
        remove_tree(self.tmp)

    def put(self, rel, data):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, str):
            data = data.encode("utf-8")
        p.write_bytes(data)
        return p

    def deny_terms(self, *terms):
        self.deny.write_text("\n".join(terms) + "\n", encoding="utf-8")

    def scan(self, *extra):
        return run([str(self.root), "--deny", str(self.deny), *extra])


class TestMasking(Base):
    """Finding 1: no printed line may carry a full secret-format value."""

    def test_deny_hit_line_context_masks_secret(self):
        self.deny_terms("Alice")
        self.put("a.txt", "Alice token " + ANT + "\n")
        code, out = self.scan()
        self.assertEqual(code, 1)
        self.assertIn("[deny: Alice]", out)
        self.assertNotIn(ANT, out)

    def test_unused_allowlist_entry_masks_secret(self):
        self.put("a.txt", "clean\n")
        allow = self.tmp / "allow.txt"
        allow.write_text("a.txt\t" + ANT + "\tfake fixture\n", encoding="utf-8")
        code, out = self.scan("--allow", str(allow))
        self.assertEqual(code, 0)
        self.assertIn("allowlist UNUSED", out)
        self.assertNotIn(ANT, out)

    def test_email_context_masks_secret(self):
        self.put("a.txt", "mail " + OPENAI + AT + "corp.test\n")
        code, out = self.scan()
        self.assertEqual(code, 1)
        self.assertIn("[email]", out)
        self.assertNotIn(OPENAI, out)

    def test_home_path_context_masks_secret(self):
        self.put("a.txt", "see " + WIN + USERS + ANT + "\\x\n")
        code, out = self.scan()
        self.assertEqual(code, 1)
        self.assertIn("[home path]", out)
        self.assertNotIn(ANT, out)


class TestEncoding(Base):
    """Finding 2: decode what can be decoded, fail loudly on the rest."""

    def test_utf16_bom_file_is_scanned(self):
        self.deny_terms("Alice")
        text = "Alice was here\r\n" + WIN + USERS + "bob\\docs\r\n"
        self.put("notes.txt", text.encode("utf-16"))
        code, out = self.scan()
        self.assertEqual(code, 1)
        self.assertIn("1 text input(s) scanned", out)
        self.assertIn("notes.txt:1: [deny: Alice]", out)
        self.assertIn("notes.txt:2: [home path]", out)

    def test_utf8_bom_denylist_matches_first_term(self):
        self.deny.write_bytes(b"\xef\xbb\xbfAlice\nBob\n")
        self.put("a.txt", "Alice\n")
        code, out = self.scan()
        self.assertEqual(code, 1)
        self.assertIn("[deny: Alice]", out)

    def test_cp1252_text_keeps_non_ascii_term(self):
        self.deny_terms("Zo\u00eb")
        self.put("a.txt", "hello Zo\u00eb\n".encode("cp1252"))
        code, out = self.scan()
        self.assertEqual(code, 1)
        self.assertIn("a.txt:1: [deny:", out)

    def test_undecodable_denylist_exits_2_naming_file(self):
        self.deny.write_bytes(b"Zo\xeb\n")
        self.put("a.txt", "clean\n")
        code, out = self.scan()
        self.assertEqual(code, 2)
        self.assertIn("deny.txt", out)
        self.assertNotIn("Traceback", out)

    def test_undecodable_allowlist_exits_2_naming_file(self):
        allow = self.tmp / "allow.txt"
        allow.write_bytes(b"a.txt\tZo\xeb\treason\n")
        self.put("a.txt", "clean\n")
        code, out = self.scan("--allow", str(allow))
        self.assertEqual(code, 2)
        self.assertIn("allow.txt", out)
        self.assertNotIn("Traceback", out)

    def test_binary_file_is_counted_and_listed(self):
        self.put("img/logo.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
        self.put("a.txt", "clean\n")
        code, out = self.scan()
        self.assertEqual(code, 0)
        self.assertIn("binary skipped: 1", out)
        self.assertIn("img/logo.png", out)

    def test_stdin_non_utf8_bytes_are_decoded(self):
        self.deny_terms("Zo\u00eb")
        code, out = run(["-", "--deny", str(self.deny)], stdin="diff Zo\u00eb\n".encode("cp1252"))
        self.assertEqual(code, 1)
        self.assertIn("<stdin>:1: [deny:", out)


class TestSkipDirs(Base):
    """Finding 3: every file but .git is scanned unless --skip names it."""

    def test_node_modules_scanned_by_default(self):
        self.deny_terms("Alice")
        self.put("node_modules/accidental-secret.txt", "Alice\n")
        code, out = self.scan()
        self.assertEqual(code, 1)
        self.assertIn("node_modules/accidental-secret.txt:1: [deny: Alice]", out)
        self.assertIn("skip list: .git", out)

    def test_skip_flag_excludes_and_is_printed(self):
        self.deny_terms("Alice")
        self.put("node_modules/accidental-secret.txt", "Alice\n")
        self.put("build/out/x.txt", "Alice\n")
        self.put(".git/config", "Alice\n")
        self.put("a.txt", "clean\n")
        code, out = self.scan("--skip", "node_modules", "--skip", "build/out")
        self.assertEqual(code, 0, out)
        self.assertIn("skip list: .git, node_modules, build/out", out)
        self.assertIn("1 text input(s) scanned", out)


class TestPatterns(Base):
    """Finding 10: home paths in any case and any username; AWS ASIA keys."""

    def test_lowercase_users_dir_is_a_hit(self):
        self.put("a.txt", "open " + WIN + "users\\" + "Alice\\private.txt\n")
        code, out = self.scan()
        self.assertEqual(code, 1)
        self.assertIn("[home path]", out)

    def test_non_ascii_username_is_a_hit(self):
        self.put("a.txt", "open " + WIN + USERS + "\u5f20\u4f1f\\docs\n")
        code, out = self.scan()
        self.assertEqual(code, 1)
        self.assertIn("[home path]", out)

    def test_placeholders_pass(self):
        lines = [
            WIN + USERS + "<you>\\x",
            WIN + USERS + "{name}\\x",
            WIN + USERS + "%USERNAME%\\x",
            WIN + USERS + "Public\\x",
            "%USERPROFILE%\\x",
            "/home/" + "$USER/x",
            "/Users/" + "~/x",
            "$HOME/x",
            "~/x",
        ]
        self.put("a.txt", "\n".join(lines) + "\n")
        code, out = self.scan()
        self.assertEqual(code, 0, out)

    def test_aws_temporary_key_is_a_hit(self):
        self.put("a.txt", "key " + AWS_TEMP + "\n")
        code, out = self.scan()
        self.assertEqual(code, 1)
        self.assertIn("[secret: aws access key]", out)
        self.assertNotIn(AWS_TEMP, out)


class TestLongLines(unittest.TestCase):
    """Finding 12: a 1,000,000-char line scans in well under a second."""

    CODE = (
        "import importlib.util, sys, time\n"
        "spec = importlib.util.spec_from_file_location('ls', sys.argv[1])\n"
        "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
        "lines = {'plain': 'a' * 1000000, 'at': 'a' * 500000 + '@' + 'a' * 499999,\n"
        "         'jwt': '-eyJ' * 250000, 'ats': '@' * 1000000}\n"
        "line = lines[sys.argv[2]]\n"
        "hits = []\n"
        "t = time.perf_counter()\n"
        "m.scan_text('x', line, [], [], set(), m.OK_DOMAINS, hits)\n"
        "print(time.perf_counter() - t)\n"
    )

    def elapsed(self, mode):
        try:
            p = subprocess.run([sys.executable, "-B", "-c", self.CODE, str(SCRIPT), mode],
                               capture_output=True, text=True, timeout=20)
        except subprocess.TimeoutExpired:
            self.fail(f"{mode} line: scan did not finish in 20 s")
        self.assertEqual(p.returncode, 0, p.stderr)
        return float(p.stdout.strip())

    def test_long_line_without_at(self):
        self.assertLess(self.elapsed("plain"), 0.5)

    def test_long_line_with_one_at(self):
        self.assertLess(self.elapsed("at"), 0.5)

    def test_long_line_of_token_fragments(self):
        self.assertLess(self.elapsed("jwt"), 0.5)
        self.assertLess(self.elapsed("ats"), 0.5)

    def test_jwt_still_detected_and_masked(self):
        seg = "A" * 12
        jwt = "ey" + "J" + seg + ".ey" + "J" + seg + "." + seg
        code = ("import importlib.util, sys\n"
                "spec = importlib.util.spec_from_file_location('ls', sys.argv[1])\n"
                "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
                "hits = []\n"
                "m.scan_text('x', 'Bearer ' + sys.argv[2], [], [], set(), m.OK_DOMAINS, hits)\n"
                "print(hits)\n")
        p = subprocess.run([sys.executable, "-B", "-c", code, str(SCRIPT), jwt],
                           capture_output=True, text=True, timeout=20)
        self.assertIn("[secret: jwt]", p.stdout)
        self.assertNotIn(jwt, p.stdout)


class TestKeptBehaviour(Base):
    """Behaviour that predates the fixes and must hold."""

    def test_planted_fixture_with_crlf_gives_eleven_hits(self):
        self.deny_terms("zephyrcorp")
        lines = [
            "Project ZephyrCorp notes",                       # 1 deny (any case)
            "mail bob" + AT + "corp.test",                    # 2 email
            "path " + WIN + USERS + "bob\\proj",              # 3 windows home
            "path /Users/" + "carol/x",                       # 4 mac home
            "path /home/" + "dave/x",                         # 5 linux home
            "k1 " + ANT,                                      # 6 anthropic
            "k2 " + OPENAI,                                   # 7 openai
            "k3 " + GITHUB,                                   # 8 github
            "k4 " + AWS,                                      # 9 aws
            "k5 " + SLACK,                                    # 10 slack
            "ok " + "x" + AT + "example.com",
            "ok " + WIN + USERS + "<you>\\x",
            "ok /home/" + "$USER",
        ]
        self.put("doc.txt", "\r\n".join(lines).encode("utf-8") + b"\r\n")
        self.put("zephyrcorp.txt", "clean\r\n")                # 11 deny in path name
        code, out = self.scan()
        self.assertEqual(code, 1)
        self.assertIn("FAIL - 11 hit(s)", out)
        for s in (ANT, OPENAI, GITHUB, AWS, SLACK):
            self.assertNotIn(s, out)
        self.assertIn("doc.txt:3: [home path]", out)
        self.assertIn("zephyrcorp.txt: [path name: zephyrcorp]", out)

    def test_skill_folder_passes_with_empty_denylist(self):
        code, out = run([str(SKILL), "--deny", str(self.deny)])
        self.assertEqual(code, 0, out)
        self.assertIn("PASS - 0 hits", out)

    def test_stdin_mode(self):
        self.deny_terms("Alice")
        code, out = run(["-", "--deny", str(self.deny)], stdin=b"+ Alice\n")
        self.assertEqual(code, 1)
        self.assertIn("<stdin>:1: [deny: Alice]", out)
        code, out = run(["-", "--deny", str(self.deny)], stdin=b"+ clean\n")
        self.assertEqual(code, 0)

    def test_usage_errors_exit_2(self):
        code, _ = run([str(self.root), "--deny", str(self.tmp / "missing.txt")])
        self.assertEqual(code, 2)
        code, _ = run([str(self.tmp / "nope"), "--deny", str(self.deny)])
        self.assertEqual(code, 2)


class TestErrorPathsMasked(Base):
    """Round 2, still open 1: error messages that echo a path mask secrets too."""

    def test_missing_deny_file_path_is_masked(self):
        code, out = run([str(self.root), "--deny", str(self.tmp / ("x" + ANT) / "deny.txt")])
        self.assertEqual(code, 2)
        self.assertNotIn(ANT, out)

    def test_missing_allow_file_path_is_masked(self):
        code, out = self.scan("--allow", str(self.tmp / ("x" + ANT) / "allow.txt"))
        self.assertEqual(code, 2)
        self.assertNotIn(ANT, out)

    def test_invalid_target_path_is_masked(self):
        code, out = run([str(self.tmp / ("x" + ANT)), "--deny", str(self.deny)])
        self.assertEqual(code, 2)
        self.assertNotIn(ANT, out)

    def test_unknown_argument_is_masked(self):
        code, out = run([str(self.root), "--deny", str(self.deny), "--bogus", ANT])
        self.assertEqual(code, 2)
        self.assertNotIn(ANT, out)

    def test_unreadable_list_is_masked(self):
        name = "k" + ANT + ".txt"
        self.put(name, "clean\n")
        with mock.patch.object(Path, "read_bytes", failing_read_bytes(name)):
            code, out = run_inproc([str(self.root), "--deny", str(self.deny)])
        self.assertEqual(code, 3)
        self.assertNotIn(ANT, out)


class TestFailClosed(Base):
    """Round 2, N1: an incomplete scan exits 3, never 0."""

    def test_unreadable_file_exits_3_and_is_listed(self):
        self.put("a.txt", "clean\n")
        self.put("locked.txt", "clean\n")
        with mock.patch.object(Path, "read_bytes", failing_read_bytes("locked.txt")):
            code, out = run_inproc([str(self.root), "--deny", str(self.deny)])
        self.assertEqual(code, 3, out)
        self.assertIn("INCOMPLETE - not a PASS", out)
        self.assertIn("locked.txt", out)
        self.assertNotIn("PASS - 0 hits", out)

    def test_unlistable_folder_exits_3_and_is_listed(self):
        self.put("a.txt", "clean\n")
        self.put("sealed/inner.txt", "clean\n")
        with mock.patch("os.scandir", failing_scandir("sealed")):
            code, out = run_inproc([str(self.root), "--deny", str(self.deny)])
        self.assertEqual(code, 3, out)
        self.assertIn("INCOMPLETE - not a PASS", out)
        self.assertIn("sealed", out)

    def test_hits_and_unreadable_exit_1_with_incomplete_note(self):
        self.deny_terms("Alice")
        self.put("a.txt", "Alice\n")
        self.put("locked.txt", "clean\n")
        with mock.patch.object(Path, "read_bytes", failing_read_bytes("locked.txt")):
            code, out = run_inproc([str(self.root), "--deny", str(self.deny)])
        self.assertEqual(code, 1, out)
        self.assertIn("INCOMPLETE", out)
        self.assertIn("locked.txt", out)

    def test_docstring_documents_exit_3(self):
        self.assertIn("3 = INCOMPLETE", load_module().__doc__)


class TestLongTokens(Base):
    """Round 2, N2: no length cap lets a long token through, and it is masked whole."""

    def test_jwt_with_8244_char_payload_is_detected_and_masked(self):
        payload = "B" * 8244
        jwt = "ey" + "J" + "A" * 20 + ".ey" + "J" + payload + "." + "C" * 43
        self.deny_terms("Alice")
        self.put("a.txt", "Alice Bearer " + jwt + "\n")
        code, out = self.scan()
        self.assertEqual(code, 1)
        self.assertIn("[secret: jwt]", out)
        self.assertNotIn("B" * 40, out)

    def test_jwt_with_long_header_on_stdin(self):
        jwt = "ey" + "J" + "H" * 9000 + ".ey" + "J" + "P" * 30 + "." + "S" * 43
        code, out = run(["-", "--deny", str(self.deny)], stdin=("x " + jwt + "\n").encode())
        self.assertEqual(code, 1)
        self.assertIn("[secret: jwt]", out)
        self.assertNotIn("H" * 40, out)

    def test_long_key_is_masked_whole(self):
        key = "sk-" + "ant-" + "A" * 900
        self.deny_terms("Alice")
        self.put("a.txt", "Alice " + key + " end\n")
        code, out = self.scan()
        self.assertEqual(code, 1)
        self.assertIn("(907 chars)", out)
        self.assertNotIn("A" * 40, out)


class TestPosixHomeAnyCase(Base):
    """Round 2, still open 10: /users/ and /home/ in any case where a path starts."""

    def test_token_start_paths_are_hits(self):
        lines = [
            "/users/" + "alice/x",
            "cd /HOME/" + "bob",
            'open "/Users/' + 'carol/x"',
            "url file:///users/" + "dave/x",
            "p=/home/" + "erin",
            "(/users/" + "fay)",
        ]
        for line in lines:
            with self.subTest(line=line):
                self.put("a.txt", line + "\n")
                code, out = self.scan()
                self.assertEqual(code, 1, out)
                self.assertIn("[home path]", out)

    def test_web_routes_stay_clean(self):
        self.put("a.txt", "GET /api/users/42\nsee https://example.com/users/42/edit\n")
        code, out = self.scan()
        self.assertEqual(code, 0, out)

    def test_exact_case_inside_a_path_still_hits(self):
        self.put("a.txt", "/c/Users/" + "gina/x\n")
        code, out = self.scan()
        self.assertEqual(code, 1, out)
        self.assertIn("[home path]", out)


class TestHistoryAllowlist(Base):
    """Round 2, N7: in stdin mode allowlist entries match the file a git log -p hunk is in."""

    EMAIL = "help" + AT + "corp.test"

    def diff(self, path, added):
        return (f"diff --git a/{path} b/{path}\n"
                f"--- a/{path}\n+++ b/{path}\n@@ -0,0 +1 @@\n+{added}\n")

    def scan_stdin(self, text):
        allow = self.tmp / "allow.txt"
        allow.write_text("doc.txt\t" + self.EMAIL + "\tpublic support address\n", encoding="utf-8")
        return run(["-", "--deny", str(self.deny), "--allow", str(allow)], stdin=text.encode())

    def test_allowlisted_file_in_history_passes(self):
        code, out = self.scan_stdin("commit 1234567\n\n    msg\n\n" + self.diff("doc.txt", "mail " + self.EMAIL))
        self.assertEqual(code, 0, out)
        self.assertNotIn("UNUSED", out)

    def test_other_file_in_history_still_hits(self):
        code, out = self.scan_stdin(self.diff("other.txt", "mail " + self.EMAIL))
        self.assertEqual(code, 1, out)
        self.assertIn("other.txt", out)
        self.assertIn("[email]", out)

    def test_lines_before_any_header_stay_stdin(self):
        code, out = self.scan_stdin("mail " + self.EMAIL + "\n" + self.diff("doc.txt", "fine"))
        self.assertEqual(code, 1, out)
        self.assertIn("<stdin>:1: [email]", out)


class TestHistoryPatchState(Base):
    """Round 3: only the file-header zone of a patch changes the current file."""

    EMAIL = "help" + AT + "corp.test"

    def scan_stdin(self, text, allow_path="doc.txt"):
        allow = self.tmp / "allow.txt"
        allow.write_text(allow_path + "\t" + self.EMAIL + "\treason\n", encoding="utf-8")
        return run(["-", "--deny", str(self.deny), "--allow", str(allow)], stdin=text.encode("utf-8"))

    def test_header_shaped_hunk_lines_do_not_switch_file(self):
        text = ("diff --git a/other.txt b/other.txt\n"
                "--- a/other.txt\n"
                "+++ b/other.txt\n"
                "@@ -1 +1,2 @@\n"
                "--- a/fake\n"
                "+++ b/doc.txt\n"
                "+" + self.EMAIL + "\n")
        code, out = self.scan_stdin(text)
        self.assertEqual(code, 1, out)
        self.assertIn("(other.txt): [email]", out)
        self.assertIn("allowlist UNUSED", out)

    def test_git_quoted_octal_path_matches_allowlist(self):
        q = r'"b/caf\303\251.md"'
        text = (r'diff --git "a/caf\303\251.md" ' + q + "\n"
                r'--- "a/caf\303\251.md"' + "\n"
                "+++ " + q + "\n"
                "@@ -0,0 +1 @@\n"
                "+mail " + self.EMAIL + "\n")
        code, out = self.scan_stdin(text, allow_path="caf\u00e9.md")
        self.assertEqual(code, 0, out)
        self.assertNotIn("UNUSED", out)

    def test_git_quoted_escaped_quote_matches_allowlist(self):
        text = ('diff --git "a/say \\"hi\\".md" "b/say \\"hi\\".md"\n'
                '--- "a/say \\"hi\\".md"\n'
                '+++ "b/say \\"hi\\".md"\n'
                "@@ -0,0 +1 @@\n"
                "+mail " + self.EMAIL + "\n")
        code, out = self.scan_stdin(text, allow_path='say "hi".md')
        self.assertEqual(code, 0, out)
        self.assertNotIn("UNUSED", out)

    def test_deletion_uses_the_a_side(self):
        text = ("diff --git a/doc.txt b/doc.txt\n"
                "deleted file mode 100644\n"
                "--- a/doc.txt\n"
                "+++ /dev/null\n"
                "@@ -1 +0,0 @@\n"
                "-mail " + self.EMAIL + "\n")
        code, out = self.scan_stdin(text)
        self.assertEqual(code, 0, out)

    def test_commit_line_after_hunk_resets_to_stdin(self):
        text = ("diff --git a/doc.txt b/doc.txt\n--- a/doc.txt\n+++ b/doc.txt\n@@ -0,0 +1 @@\n+fine\n"
                "commit 89abcdef0123\n"
                "    mail " + self.EMAIL + "\n")
        code, out = self.scan_stdin(text)
        self.assertEqual(code, 1, out)
        self.assertIn("<stdin>:7: [email]", out)

    def test_docstring_mentions_quote_path_option(self):
        self.assertIn("core.quotePath=false", load_module().__doc__)


if __name__ == "__main__":
    unittest.main()
