"""Tests for the /triage PreToolUse guard.

Pure-function tests exercise guard.check() directly; subprocess tests exercise
guard.py's stdin/exit-code contract exactly as Claude Code's PreToolUse hook
invokes it. A last group parses SKILL.md's frontmatter. All local, no network.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import guard  # noqa: E402

SKILL_DIR = Path(__file__).resolve().parent.parent
GUARD_PATH = SKILL_DIR / "guard.py"
SKILL_MD = SKILL_DIR / "SKILL.md"
_PLACEHOLDER = "{{" + "SKILLS_DIR" + "}}"  # split so the installer leaves it alone
PREFIX = "mcp__n8n-mcp__"


def payload(tool_name, tool_input=None):
    p = {
        "session_id": "test",
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
    }
    if tool_input is not None:
        p["tool_input"] = tool_input
    return p


def run_raw(stdin_text):
    """Invoke guard.py as a subprocess with raw text on stdin."""
    return subprocess.run(
        [sys.executable, str(GUARD_PATH)],
        input=stdin_text,
        capture_output=True,
        text=True,
        timeout=10,
    )


def run_guard(tool_name, tool_input=None):
    """Invoke guard.py with a PreToolUse JSON payload on stdin."""
    if tool_input is None:
        tool_input = {}
    return run_raw(json.dumps(payload(tool_name, tool_input)))


def assert_allowed(result):
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""
    assert result.stderr.strip() == ""


def assert_denied(result, tool_name=None):
    assert result.returncode == 2
    assert result.stdout.strip() == ""
    assert result.stderr.strip() != ""
    if tool_name:
        assert tool_name in result.stderr


# ---------------------------------------------------------------------------
# Allowlist
# ---------------------------------------------------------------------------

READ_TOOLS = [
    "search_workflow_executions",
    "get_workflow_execution",
    "search_workflows",
    "get_workflow_details",
    "get_node_types",
    "search_nodes",
]

# Allowed before fix round 2b (N3) or the structure-only redesign
# (validate_node_config: no parameters are visible, nothing to validate).
NO_LONGER_ALLOWED = [
    "validate_node_config",
    "search_data_tables",
    "search_projects",
    "search_folders",
    "list_workflow_tags",
    "validate_workflow",
    "get_workflow_sdk_reference",
    "get_workflow_best_practices",
]

WRITE_OR_UNLISTED_TOOLS = [
    "update_workflow",
    "publish_workflow",
    "execute_workflow",
    "archive_workflow",
    "create_workflow_from_code",
    "add_data_table_rows",
    "list_credentials",
    "explore_node_resources",
    # builder extras: every other tool the deployed server exposes
    "unpublish_workflow",
    "restore_workflow_version",
    "test_workflow",
    "prepare_workflow_pin_data",
    "create_data_table",
    "add_data_table_column",
    "delete_data_table_column",
    "rename_data_table",
    "rename_data_table_column",
    "list_n8n_connect_services",
    "some_future_tool",
    "get_workflow_history",
    "get_workflow_version",
] + NO_LONGER_ALLOWED


def test_subprocess_search_workflow_executions_allowed_silently():
    result = run_guard(PREFIX + "search_workflow_executions",
                       {"status": ["error", "crashed"], "limit": 200})
    assert_allowed(result)


@pytest.mark.parametrize("short", READ_TOOLS)
def test_every_read_tool_allowed(short):
    assert guard.check(payload(PREFIX + short, {})) is None


@pytest.mark.parametrize("short", WRITE_OR_UNLISTED_TOOLS)
def test_unlisted_tool_denied_and_named(short):
    reason = guard.check(payload(PREFIX + short, {}))
    assert reason is not None
    assert PREFIX + short in reason
    assert "read-only" in reason
    assert "/model-router:fabstra" in reason
    assert "fresh session" in reason


@pytest.mark.parametrize("short", WRITE_OR_UNLISTED_TOOLS[:8])
def test_subprocess_unlisted_tool_exit_2_names_tool(short):
    assert_denied(run_guard(PREFIX + short, {"workflowId": "1"}), PREFIX + short)


@pytest.mark.parametrize("short", ["get_workflow_history", "get_workflow_version"])
def test_subprocess_history_and_version_tools_exit_2(short):
    assert_denied(run_guard(PREFIX + short, {"workflowId": "1"}), PREFIX + short)


def test_allowlist_is_exactly_the_procedure_tools():
    assert guard.READ_ALLOWLIST == frozenset(READ_TOOLS)


@pytest.mark.parametrize("short", NO_LONGER_ALLOWED)
def test_subprocess_shrunken_allowlist_denies(short):
    assert_denied(run_guard(PREFIX + short, {}), PREFIX + short)
    assert_denied(run_guard("mcp__n8n-clientx__" + short, {}),
                  "mcp__n8n-clientx__" + short)


def test_allowlist_is_exact_not_prefix_or_case_insensitive():
    for name in ["search_workflow_executions_and_delete",
                 "Search_Workflows", "get_workflow_details ", ""]:
        assert guard.check(payload(PREFIX + name, {})) is not None, name


# ---------------------------------------------------------------------------
# get_workflow_execution payload minimisation
# ---------------------------------------------------------------------------

GWE = PREFIX + "get_workflow_execution"
BASE = {"workflowId": "w1", "executionId": "e1"}

GWE_ALLOW = [
    {},
    {"includeData": False},
    {"includeData": None},
    {"includeData": True, "nodeNames": ["X"], "truncateData": 1},
    {"includeData": True, "nodeNames": ["A", "B", "C"], "truncateData": 2},
    # extra args are only honoured with includeData true; harmless otherwise
    {"includeData": False, "nodeNames": ["A", "B", "C", "D"], "truncateData": 50},
]

GWE_DENY = [
    {"includeData": True},
    {"includeData": True, "truncateData": 1},
    {"includeData": True, "nodeNames": [], "truncateData": 1},
    {"includeData": True, "nodeNames": ["A", "B", "C", "D"], "truncateData": 1},
    {"includeData": True, "nodeNames": ["X"], "truncateData": 5},
    {"includeData": True, "nodeNames": ["X"]},
    {"includeData": True, "nodeNames": ["X"], "truncateData": 0},
    {"includeData": True, "nodeNames": ["X"], "truncateData": 3},
    {"includeData": True, "nodeNames": ["X"], "truncateData": True},
    {"includeData": True, "nodeNames": ["X"], "truncateData": 1.0},
    {"includeData": True, "nodeNames": ["X"], "truncateData": "1"},
    {"includeData": True, "nodeNames": "X", "truncateData": 1},
    {"includeData": True, "nodeNames": [""], "truncateData": 1},
    {"includeData": True, "nodeNames": [None], "truncateData": 1},
    # anything that is not exactly false/absent counts as "include data"
    {"includeData": "true", "truncateData": 1},
    {"includeData": 1},
]


@pytest.mark.parametrize("extra", GWE_ALLOW)
def test_get_execution_allowed(extra):
    assert guard.check(payload(GWE, {**BASE, **extra})) is None


@pytest.mark.parametrize("extra", GWE_DENY)
def test_get_execution_denied(extra):
    reason = guard.check(payload(GWE, {**BASE, **extra}))
    assert reason is not None
    assert GWE in reason


def test_subprocess_get_execution_acceptance_rows():
    assert_allowed(run_guard(GWE, {**BASE, "includeData": False}))
    assert_allowed(run_guard(GWE, {**BASE, "includeData": True,
                                   "nodeNames": ["X"], "truncateData": 1}))
    assert_denied(run_guard(GWE, {**BASE, "includeData": True}), GWE)
    assert_denied(run_guard(GWE, {**BASE, "includeData": True,
                                  "nodeNames": ["A", "B", "C", "D"],
                                  "truncateData": 1}), GWE)
    assert_denied(run_guard(GWE, {**BASE, "includeData": True,
                                  "nodeNames": ["X"], "truncateData": 5}), GWE)
    assert_denied(run_guard(GWE, {**BASE, "includeData": True,
                                  "nodeNames": ["X"]}), GWE)


# ---------------------------------------------------------------------------
# Fail closed for n8n, pass for everything else
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("stdin_text", ["", "not json", "{", "[1, 2]", "null", '"str"'])
def test_subprocess_malformed_stdin_denied(stdin_text):
    assert_denied(run_raw(stdin_text))


def test_subprocess_missing_tool_name_denied():
    assert_denied(run_raw(json.dumps({"tool_input": {}})))
    assert_denied(run_raw(json.dumps({"tool_name": None, "tool_input": {}})))
    assert_denied(run_raw(json.dumps({"tool_name": 7, "tool_input": {}})))


@pytest.mark.parametrize("bad_input", [None, "x", ["a"], 3])
def test_n8n_tool_with_unreadable_input_denied(bad_input):
    p = {"tool_name": PREFIX + "search_workflows", "tool_input": bad_input}
    assert guard.check(p) is not None
    assert_denied(run_raw(json.dumps(p)), PREFIX + "search_workflows")


def test_n8n_tool_missing_tool_input_denied():
    p = {"tool_name": PREFIX + "search_workflows"}
    assert guard.check(p) is not None


def test_subprocess_unrelated_tool_passes():
    assert_allowed(run_raw(json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": "ls"}})))
    assert_allowed(run_raw(json.dumps({"tool_name": "Read"})))
    assert_allowed(run_raw(json.dumps(
        {"tool_name": "mcp__other__update_workflow", "tool_input": {}})))


# ---------------------------------------------------------------------------
# Every n8n server (R2): server segment starts with n8n, case-insensitive
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tool", [
    "mcp__n8n__n8n_update_full_workflow",       # community stdio server
    "mcp__n8n__n8n_list_executions",            # community names: unsupported
    "mcp__n8n-clientx__update_workflow",   # client cloud instance
    "mcp__N8N-Prod__execute_workflow",
    "mcp__n8n_staging__publish_workflow",
])
def test_other_n8n_servers_write_or_unlisted_denied(tool):
    reason = guard.check(payload(tool, {}))
    assert reason is not None and tool in reason
    assert_denied(run_guard(tool, {}), tool)


@pytest.mark.parametrize("tool", [
    "mcp__n8n-clientx__search_workflows",
    "mcp__N8n-Prod__get_workflow_details",
])
def test_other_n8n_servers_read_allowed(tool):
    assert guard.check(payload(tool, {})) is None
    assert_allowed(run_guard(tool, {}))


def test_other_n8n_server_execution_minimisation_applies():
    tool = "mcp__n8n-clientx__get_workflow_execution"
    assert guard.check(payload(tool, {**BASE, "includeData": True})) is not None
    assert guard.check(payload(tool, {**BASE, "includeData": True,
                                      "nodeNames": ["X"], "truncateData": 1})) is None


@pytest.mark.parametrize("tool", [
    "mcp__n8n", "mcp__n8n-mcp", "mcp__n8n__", "mcp____n8n_tool", "mcp__N8N",
])
def test_unparsable_mcp_name_with_n8n_denied(tool):
    assert guard.check(payload(tool, {})) is not None
    assert_denied(run_guard(tool, {}))


@pytest.mark.parametrize("tool", [
    "mcp__other__update_workflow", "mcp__xn8n__update_workflow",
    "mcp__plugin_x_n8n__update_workflow", "mcp__other", "n8n_update_workflow",
])
def test_non_n8n_server_passes(tool):
    assert guard.check(payload(tool, {})) is None


def test_matcher_regexes_select_every_n8n_server():
    import re
    fm = _frontmatter_yaml()
    pre = fm["hooks"]["PreToolUse"][0]["matcher"]
    post = fm["hooks"]["PostToolUse"][0]["matcher"]
    for name in ["mcp__n8n-mcp__update_workflow", "mcp__n8n__n8n_list_executions",
                 "mcp__n8n-clientx__search_workflows",
                 "mcp__N8N-Prod__get_workflow_execution", "mcp__n8n-stub__x",
                 "mcp__n8n"]:
        assert re.search(pre, name), name
    for name in ["mcp__other__update_workflow", "Bash", "mcp__xn8n__a"]:
        assert not re.search(pre, name), name
    for name in ["mcp__n8n-mcp__get_workflow_execution",
                 "mcp__n8n-clientx__get_workflow_details",
                 "mcp__N8N-Prod__get_workflow_execution",
                 "mcp__n8n_staging__get_workflow_execution",
                 "mcp__n8n-stub__get_workflow_execution",
                 "mcp__n8n-mcp__search_workflows",
                 "mcp__n8n-mcp__search_workflow_executions",
                 "mcp__n8n-clientx__search_workflows",
                 "mcp__n8n-stub__search_workflows"]:
        assert re.search(post, name), name
    for name in ["mcp__n8n-mcp__get_node_types",
                 "mcp__n8n-mcp__search_nodes",
                 "mcp__n8n-mcp__validate_node_config",
                 "mcp__n8n-mcp__search_workflows_x",
                 "mcp__n8n-mcp__get_workflow_execution_x",
                 "mcp__other__get_workflow_execution",
                 "mcp__other__search_workflows",
                 "mcp__n8n-mcp__get_workflow_details2"]:
        assert not re.search(post, name), name


def test_internal_error_denies_n8n_and_passes_other(monkeypatch):
    def boom(_payload):
        raise RuntimeError("boom")

    monkeypatch.setattr(guard, "check", boom)
    assert guard.decide(json.dumps(payload(PREFIX + "search_workflows", {}))) is not None
    assert guard.decide(json.dumps(payload("Bash", {"command": "ls"}))) is None


# ---------------------------------------------------------------------------
# SKILL.md frontmatter
# ---------------------------------------------------------------------------

def _frontmatter():
    text = SKILL_MD.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    end = text.index("\n---\n", 4)
    return text[4:end]


def _frontmatter_yaml():
    yaml = pytest.importorskip("yaml")
    return yaml.safe_load(_frontmatter())


def test_skill_frontmatter_parses_and_registers_guard():
    fm = _frontmatter_yaml()
    assert fm["name"] == "triage"
    assert fm["disable-model-invocation"] is True
    desc = fm["description"]
    assert "read-only" in desc and "n8n" in desc and "session" in desc
    entries = fm["hooks"]["PreToolUse"]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["matcher"] == "^mcp__[nN]8[nN]"
    hook = entry["hooks"][0]
    assert hook["type"] == "command"
    assert hook["command"] == "python"
    assert len(hook["args"]) == 1
    if _PLACEHOLDER in hook["args"][0]:
        pytest.skip("repo copy: run the installed copy (scripts/install-user-skills.*)")
    assert Path(hook["args"][0]).resolve() == GUARD_PATH.resolve()


def test_skill_frontmatter_registers_scrubber():
    fm = _frontmatter_yaml()
    entries = fm["hooks"]["PostToolUse"]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["matcher"] == (
        "^mcp__[nN]8[nN][^_]*(_[^_]+)*__(search_workflow_executions"
        "|get_workflow_execution|search_workflows|get_workflow_details)$")
    hook = entry["hooks"][0]
    assert hook["type"] == "command" and hook["command"] == "python"
    assert len(hook["args"]) == 1
    if _PLACEHOLDER in hook["args"][0]:
        pytest.skip("repo copy: run the installed copy (scripts/install-user-skills.*)")
    assert Path(hook["args"][0]).resolve() == (SKILL_DIR / "scrub.py").resolve()


def test_skill_md_size_and_handoff():
    body = SKILL_MD.read_text(encoding="utf-8")
    # Budget measured with the installed skills dir folded back to the
    # placeholder, so a long install path does not fail it. The export's
    # generic wording adds bytes, so the source budget (5300) gets +60.
    import re as _re
    sized = _re.sub(_re.escape(str(SKILL_DIR.parent)), lambda m: _PLACEHOLDER, body, flags=_re.I)
    assert len(sized.encode("utf-8")) < 5360
    assert "\r\n" not in body
    assert "/model-router:fabstra fix triage group <N> from .fabstra/TRIAGE-<stamp>.md" in body
    assert "redaction gate" in body
    assert "starts with n8n" in body
    assert "check-ignore" in body
    assert "at least" in body and "window total unknown" in body
    assert "lasts until the session ends" in body and "seatbelt" in body
    assert "confirm in n8n: open execution <id>" in body
    assert "[LABEL-n]" in body and "UNDIAGNOSED" in body
    assert "never reach Claude by design" in body
    assert "error class + HTTP code" in body
    assert "[NAME]" not in body and "Redact" not in body


def _step(body, n):
    start = body.index("\n%d. **" % n)
    end = body.find("\n%d. **" % (n + 1), start + 1)
    return body[start:end if end != -1 else len(body)]


def test_skill_md_round3_paging_draft_and_plugin_servers():
    body = SKILL_MD.read_text(encoding="utf-8")
    step2 = _step(body, 2)
    for s in ("`cursor`", "`nextCursor`", "`lastId`", "no next cursor",
              "no new ids", "partial"):
        assert s in step2, s
    step5 = _step(body, 5)
    assert "`sameAsDraft`" in step5 and "false or absent" in step5
    assert "may differ from what ran" in step5 and "ASSUMED" in step5
    assert "`mcp__plugin_*`" in body and "outside the lock" in body
    assert "disable them before running /triage" in body


def test_guard_docstring_names_plugin_servers():
    doc = guard.__doc__
    assert "`mcp__plugin_*`" in doc and "outside the lock" in doc
    assert "disable them before running /triage" in doc


def test_skill_files_use_lf():
    for p in (SKILL_MD, GUARD_PATH, SKILL_DIR / "scrub.py",
              SKILL_DIR / "tests" / "test_guard.py", SKILL_DIR / "tests" / "test_scrub.py"):
        assert b"\r\n" not in p.read_bytes(), p


def test_skill_md_uses_only_allowlisted_tools():
    body = SKILL_MD.read_text(encoding="utf-8")
    for short in NO_LONGER_ALLOWED + ["get_workflow_history", "get_workflow_version"]:
        assert short not in body, short
    for short in ("search_workflow_executions", "get_workflow_execution",
                  "search_workflows", "get_workflow_details"):
        assert short in body, short


def test_skill_md_round4_paging_stop_rule_per_parameter():
    step2 = _step(SKILL_MD.read_text(encoding="utf-8"), 2)
    cur, last = step2.index("`cursor`"), step2.index("`lastId`")
    assert cur < last
    cursor_rule = step2[cur:last]
    lastid_rule = step2[last:step2.index("Per-workflow")]
    assert "no next cursor" in cursor_rule
    assert "next cursor" not in lastid_rule and "nextCursor" not in lastid_rule
    for s in ("last execution id", "fewer than `limit`", "no new ids", "600"):
        assert s in lastid_rule, s
    assert "stop at no next cursor or no new ids" not in step2
    # coverage-partial wording unchanged
    assert ("Else (capped, no new ids, cursor missing, `count` above what you "
            "fetched) say coverage is partial") in step2
