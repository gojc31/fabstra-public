"""Tests for the /careful PreToolUse guard.

Pure-function tests exercise guard.check() directly; subprocess tests exercise
guard.py's stdin/exit-code contract exactly as Claude Code's PreToolUse hook
invokes it. All local, no network.
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import guard  # noqa: E402

GUARD_PATH = Path(__file__).resolve().parent.parent / "guard.py"


def run_guard(tool_input_command, tool_name="Bash"):
    """Invoke guard.py as a subprocess with a PreToolUse JSON payload on stdin."""
    payload = {
        "session_id": "test",
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": {"command": tool_input_command},
    }
    return subprocess.run(
        [sys.executable, str(GUARD_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
    )


# ---------------------------------------------------------------------------
# Pure function tests: guard.check() -> reason string, or None to allow.
# ---------------------------------------------------------------------------

BLOCKED_COMMANDS = [
    r"rm -rf C:\Users\you\project",
    r"rm -fr C:\Users\you\project",
    r"rm -r C:\Users\you\project",
    r"Remove-Item -Recurse -Force C:\Users\you\project",
    r"Remove-Item -Force -Recurse C:\Users\you\project",
    "git push --force",
    "git push -f",
    "git push --force-with-lease",
    "git push origin main --force",
    "git reset --hard",
    "git reset --hard HEAD~1",
    "git clean -f",
    "git clean -fd",
    "DROP TABLE users",
    "drop database prod",
    "DROP SCHEMA public",
    "TRUNCATE users",
    "TRUNCATE TABLE users",
    "DELETE FROM users",
    "delete from users;",
    "supabase db reset",
    "kubectl delete pod my-pod",
    "terraform destroy",
]


def test_each_blocked_pattern_is_denied():
    for cmd in BLOCKED_COMMANDS:
        reason = guard.check(cmd)
        assert reason is not None, f"expected deny for: {cmd!r}"
        assert isinstance(reason, str) and reason.strip()


def test_blocked_patterns_case_insensitive():
    for cmd in BLOCKED_COMMANDS:
        reason = guard.check(cmd.upper())
        assert reason is not None, f"expected deny (upper) for: {cmd!r}"
        reason = guard.check(cmd.lower())
        assert reason is not None, f"expected deny (lower) for: {cmd!r}"


NEGATIVE_COMMANDS = [
    "rm file.txt",
    "git push",
    "git push origin main",
    "SELECT * FROM x",
    "DELETE FROM t WHERE id=1",
    "ls -rf-notes",
    "git branch -d feature",
]


def test_negatives_pass():
    for cmd in NEGATIVE_COMMANDS:
        reason = guard.check(cmd)
        assert reason is None, f"expected allow for: {cmd!r}, got {reason!r}"


def test_rm_recursive_on_temp_path_passes():
    # Plain -r (no force) on an obvious temp/scratchpad path is allowed;
    # -rf/-fr stay blocked everywhere (see BLOCKED_COMMANDS above).
    cmd = r"rm -r C:\Users\you\AppData\Local\Temp\claude\scratchpad\old-run"
    assert guard.check(cmd) is None


# git's -d/-D case carries meaning: -d only deletes an already-merged
# branch (safe), -D force-deletes regardless (destroys history). The
# blanket case-insensitive rule does not apply to this one flag.

def test_git_branch_uppercase_D_is_denied():
    assert guard.check("git branch -D feature/old") is not None


def test_git_branch_lowercase_d_alone_passes():
    # This is the fix: the previous guard matched -d case-insensitively
    # and denied this safe, already-merged-branch delete. Confirmed
    # reproduced against the pre-fix regex before patching (session log).
    assert guard.check("git branch -d feature") is None


def test_git_branch_lowercase_d_with_force_flag_is_denied():
    # -d plus an explicit -f/--force is force-equivalent to -D.
    assert guard.check("git branch -d -f feature") is not None
    assert guard.check("git branch --delete --force feature") is not None


def test_git_branch_bundled_df_is_denied():
    assert guard.check("git branch -df feature") is not None


def test_reason_names_the_matched_pattern():
    reason = guard.check("git reset --hard")
    assert "git reset --hard" in reason.lower() or "reset" in reason.lower()


def test_reason_says_how_to_proceed():
    reason = guard.check("terraform destroy")
    assert "/careful" in reason or "the user" in reason.lower()


# ---------------------------------------------------------------------------
# Fix round 2 - adversarial review findings (R1-R4).
# ---------------------------------------------------------------------------

def test_rm_recursive_denied_if_any_path_argument_is_non_temp():
    # R1: the temp exemption must hold only when EVERY path argument is a
    # temp path; a mixed non-temp + temp target list must still deny.
    cmd = r"rm -r C:/prod/clients /tmp/cache"
    assert guard.check(cmd) is not None


def test_delete_from_checked_per_sql_statement():
    # R2: a later statement's stray "where" (even as a string literal) must
    # not excuse an earlier DELETE FROM with no WHERE in its own statement.
    cmd = "psql -c \"DELETE FROM users; SELECT 'where';\""
    assert guard.check(cmd) is not None


def test_git_global_options_do_not_bypass_push_force():
    # R3: git global options between `git` and the subcommand (-C <path>,
    # -c k=v, --git-dir=..., --work-tree=...) must not hide the subcommand.
    assert guard.check("git -C C:/repo push --force") is not None


def test_git_global_options_do_not_bypass_reset_hard():
    assert guard.check("git -C C:/repo reset --hard") is not None


def test_git_global_options_do_not_bypass_clean_and_branch():
    assert guard.check("git -c user.name=x clean -f") is not None
    assert guard.check("git --git-dir=/repo/.git branch -D feature") is not None


def test_rm_does_not_misread_hyphenated_path_as_a_flag():
    # R4: a hyphen inside a path token (not its own whitespace-separated
    # token) is not a flag - "rm C:/work/client-report-final" is not
    # "rm -rf ...".
    assert guard.check("rm C:/work/client-report-final") is None


# ---------------------------------------------------------------------------
# Fix round 3 - follow-up finding: git clean's long-form --force was never
# checked (the flag loop explicitly skipped any token starting with "--").
# ---------------------------------------------------------------------------

def test_git_clean_long_form_force_is_denied():
    assert guard.check("git clean --force") is not None


def test_git_clean_long_form_force_with_global_options_is_denied():
    assert guard.check("git -C C:/repo clean --force") is not None


def test_git_clean_dash_d_with_long_force_is_denied():
    assert guard.check("git clean -d --force") is not None


def test_reason_never_claims_a_careful_off_toggle():
    # There is no "/careful off" - hooks registered from a skill's
    # frontmatter persist for the rest of the session. The reason must not
    # claim otherwise.
    for cmd in ("terraform destroy", "git reset --hard", "git push -f"):
        reason = guard.check(cmd)
        assert "off" not in reason.lower(), reason
        assert "rest of the session" in reason.lower() or "session" in reason.lower()


# ---------------------------------------------------------------------------
# Subprocess tests: guard.py's stdin/exit-code contract.
# ---------------------------------------------------------------------------

def test_subprocess_denies_with_exit_2_and_stderr():
    result = run_guard("git push --force")
    assert result.returncode == 2
    assert result.stderr.strip() != ""
    assert result.stdout.strip() == ""


def test_subprocess_powershell_tool_denies():
    result = run_guard("Remove-Item -Recurse -Force .\\build", tool_name="PowerShell")
    assert result.returncode == 2
    assert result.stderr.strip() != ""


def test_subprocess_allows_silently():
    result = run_guard("git push origin main")
    assert result.returncode == 0
    assert result.stdout.strip() == ""
    assert result.stderr.strip() == ""


def test_subprocess_malformed_stdin_exits_zero_silently():
    result = subprocess.run(
        [sys.executable, str(GUARD_PATH)],
        input="not valid json {{{",
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""
    assert result.stderr.strip() == ""


def test_subprocess_missing_command_field_exits_zero_silently():
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {}}
    result = subprocess.run(
        [sys.executable, str(GUARD_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""
    assert result.stderr.strip() == ""


def test_subprocess_empty_stdin_exits_zero_silently():
    result = subprocess.run(
        [sys.executable, str(GUARD_PATH)],
        input="",
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""
    assert result.stderr.strip() == ""


# ---------------------------------------------------------------------------
# T3b - tokenizer/segmenter rewrite. Table-driven acceptance rows.
# ---------------------------------------------------------------------------
import pytest  # noqa: E402

T3B_MUST_DENY = [
    "rm file.txt && rm -rf C:/prod",
    "git push origin main && git push --force origin main",
    "rm -r /tmp/cache /tmp2/client-data",
    "rm -r C:/prod/clients /tmp/cache",
    'git -C "C:/Users/you/My Project" push --force',
    'git --git-dir="C:/my repo/.git" reset --hard',
    'git -C "C:/Users/you/My Project" branch -D x',
    "/usr/bin/git push --force origin main",
    "git.exe push --force",
    "git push origin +main",
    "git push -fu origin main",
    "git clean --force",
    "git -C x clean -fd",
    "find C:/prod -delete",
    'find . -name "*.log" -exec rm -rf {} +',
    "kubectl -n prod delete pod x",
    "kubectl --context prod delete deploy x",
    "terraform apply -destroy",
    "supabase db reset",
    'psql -c "DELETE FROM users -- WHERE id=1"',
    "psql -c \"DELETE FROM users RETURNING 'where'\"",
    "psql -c \"DELETE FROM users; SELECT 'where';\"",
    "psql <<EOF\nDELETE FROM users;\nEOF",
    'psql -c "TRUNCATE users"',
    'mysql -e "DROP TABLE t"',
    "Remove-Item -Recurse -Force C:/x",
    'bash -c "rm -rf /c/prod"',
    "sudo rm -rf /var/x",
    "ls | xargs rm -rf",
    "rm -rf /tmp/x",
    # extra rows (builder): wrappers and forms the spec names
    r'& "C:\Program Files\Git\cmd\git.exe" push --force',
    'cmd /c "rm -rf C:/prod"',
    'powershell -Command "Remove-Item -Recurse -Force C:/x"',
    "env FOO=1 rm -rf /x",
    "git push origin --delete feature",
    "git push --force-with-lease=main origin main",
    "git push --mirror",
    "git branch -Dr origin/x",
    "git branch --delete --force x",
    "echo hi\nrm -rf C:/prod",
    'rm -rf C:/x "unbalanced',
    "cat <<'SQL' | psql\nDROP TABLE t;\nSQL",
    "sqlite3 app.db \"DELETE FROM t\"",
    "Remove-Item -Recurse:$true -Force C:/x",
    "rm -r C:/Users/you/AppData/Local/Temp/../../prod",
]

T3B_MUST_PASS = [
    "rm file.txt",
    'rm "C:/work/my file.txt"',
    "rm C:/work/client-report-final",
    'rm -r "C:/Users/you/AppData/Local/Temp/my dir"',
    "rm -r C:/Users/you/AppData/Local/Temp/claude/x/scratchpad/old",
    "git push",
    "git push origin main",
    "git push origin feature--force",
    "git reset feature--hard",
    "git reset --soft HEAD~1",
    'git -C "C:/my repo" status',
    "git -C C:/repo log --oneline",
    "git branch -d feature",
    "git rm -r --cached node_modules",
    'git commit -m "truncate long titles"',
    "git log --grep='drop table'",
    'grep -rn "DELETE FROM" src/',
    "truncate -s 0 app.log",
    'python -c "f.truncate()"',
    "npm run rm-artifacts",
    'psql -c "DELETE FROM users WHERE id=1"',
    "psql -c \"DELETE FROM users WHERE name = 'a;b'\"",
    'psql -c "SELECT * FROM x"',
    "kubectl get pods -n prod",
    "terraform apply",
    "Remove-Item foo.txt",
    "Remove-Item -Recurse C:/x/build",
    "ls -rf-notes",
    "echo \"it's fine",
    # extra rows (builder)
    'git commit -m "rm -rf everything; git push --force"',
    'echo "DROP TABLE users"',
    "rm -r /tmp/cache > /dev/null 2>&1",
    "npm test 2>&1 | tail -5",
    'git -C "C:/Users/you/My Project" push origin main',
]


@pytest.mark.parametrize("cmd", T3B_MUST_DENY)
def test_t3b_must_deny(cmd):
    assert guard.check(cmd) is not None, f"expected deny for: {cmd!r}"


@pytest.mark.parametrize("cmd", T3B_MUST_PASS)
def test_t3b_must_pass(cmd):
    reason = guard.check(cmd)
    assert reason is None, f"expected allow for: {cmd!r}, got {reason!r}"


def test_t3b_subprocess_chain_deny():
    result = run_guard("rm file.txt && rm -rf C:/prod")
    assert result.returncode == 2
    assert "rest of the session" in result.stderr
    assert result.stdout == ""


# ---------------------------------------------------------------------------
# T3b fix round 1 - review findings (Sol xhigh + fresh Fable).
# ---------------------------------------------------------------------------

R1_MUST_DENY = [
    # 1 inline conditionals and blocks
    "if [ -d /c/prod ]; then rm -rf /c/prod; fi",
    'for d in a b; do rm -rf "$d"; done',
    "while true; do git push --force; done",
    "if (Test-Path C:/prod) { Remove-Item -Recurse -Force C:/prod }",
    "Get-ChildItem C:/x | ForEach-Object { Remove-Item $_.FullName -Recurse -Force }",
    'powershell -Command "& { Remove-Item -Recurse -Force C:/x }"',
    # 2 package-runner wrappers
    "npx supabase db reset",
    "pnpm supabase db reset",
    "pnpm dlx supabase db reset",
    "pnpm exec supabase db reset",
    "bunx supabase db reset",
    "npx supabase db reset --linked",
    "yarn supabase db reset",
    # 3 here-strings
    'psql <<< "DROP TABLE users"',
    'mysql <<< "TRUNCATE TABLE users"',
    'psql "$DB" <<< "DELETE FROM users"',
    # 4 container / remote / pty wrappers
    'docker compose exec db psql -U postgres -c "DELETE FROM users"',
    'docker exec -it pg psql -c "DROP TABLE x"',
    'winpty psql -c "DROP TABLE x"',
    'ssh prod "rm -rf /var/www"',
    'kubectl exec -it pod -- psql -c "DROP TABLE x"',
    # 5 colon refspec delete
    "git push origin :main",
    "git push origin :refs/heads/x",
    # 6 PowerShell parameter prefixes
    "Remove-Item -r -Force C:/x",
    "Remove-Item -Rec -Fo C:/x",
    # 7 supabase global options with values
    "supabase --workdir ./app db reset",
    # 8 cmd.exe recursive delete
    r'cmd /c "rd /s /q C:\x"',
    "rmdir /s /q node_modules",
]

R1_MUST_PASS = [
    # 9 feeder over-deny
    'echo "DROP TABLE users" && psql -c "SELECT 1"',
    # 10
    "Remove-Item -Recurse:$false -Force C:/x",
    'docker compose exec db psql -c "SELECT 1"',
    "npx supabase status",
    "git push origin main:main",
    r"rd C:\empty-dir",
    'echo "if then"',
    # builder extras
    'echo "DROP TABLE users"; psql -c "SELECT 1"',
    "cat <<EOF > notes.sql\nDROP TABLE t;\nEOF\npsql -c 'select 1'",
]


@pytest.mark.parametrize("cmd", R1_MUST_DENY)
def test_r1_must_deny(cmd):
    assert guard.check(cmd) is not None, f"expected deny for: {cmd!r}"


@pytest.mark.parametrize("cmd", R1_MUST_PASS)
def test_r1_must_pass(cmd):
    reason = guard.check(cmd)
    assert reason is None, f"expected allow for: {cmd!r}, got {reason!r}"
