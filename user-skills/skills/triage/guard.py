#!/usr/bin/env python3
"""PreToolUse guard for the /triage skill.

Reads a Claude Code PreToolUse hook payload from stdin (see
https://code.claude.com/docs/en/hooks) and keeps every n8n MCP server -- any
server whose name starts with n8n, case-insensitive (`n8n-mcp`, `n8n`,
`n8n-clientx`, ...) -- read-only. Registered on the matcher
`^mcp__[nN]8[nN]` for the duration of the session, via /triage's own
SKILL.md frontmatter `hooks:` block -- see that file.

Deny form: exit code 2 with the reason on stderr (the "blocking error" form
documented for PreToolUse hooks -- it blocks unconditionally, unlike the
JSON permissionDecision form, which is only honored on other exit codes).
Allow form: exit 0, no output.

Rules, in order:
  1. stdin that is not a JSON object, or has no string `tool_name` -> deny
     (fail closed: the matcher only sends n8n tools here).
  2. `tool_name` is split as `mcp__<server>__<tool>` (server = text up to the
     next `__`). A name that does not split that way (empty server or tool)
     and contains n8n in any case -> deny. A server not starting with n8n
     (case-insensitive), or a non-MCP tool -> pass. The matcher should never
     send one; the guard must not block unrelated tools.
  3. The tool segment must be exactly one of READ_ALLOWLIST -- the six
     official n8n MCP reads the /triage procedure uses, and nothing else
     (no tags, projects, folders, data tables, history, SDK docs, or
     workflow/node validation: scrub.py hides parameters, so there is
     nothing to validate) -- else deny, naming the tool. The community server's
     names (`n8n_update_full_workflow`, `n8n_list_executions`, ...) are
     therefore all denied: unsupported, fail closed.
  4. `tool_input` must be a JSON object, else deny.
  5. `get_workflow_execution` with `includeData` set to anything other than
     false/absent must carry `nodeNames` (a list of 1-3 non-empty strings)
     and `truncateData` (an integer 1 or 2), else deny. Full execution
     payloads are never read.

This script never raises: an internal error while judging an n8n tool
denies; on anything else it passes.

This is a seatbelt on MCP tool calls, not a sandbox: a shell command (curl,
Invoke-RestMethod, a script) calling the n8n REST API directly never goes
through this hook. /triage's procedure forbids that; the guard cannot see it.

Plugin-bundled n8n servers (`mcp__plugin_*`) are outside the lock (the
matcher sees only `mcp__n8n*` names, any case);
disable them before running /triage.

stdlib only.
"""
import json
import sys

MCP = "mcp__"
SEP = "__"

READ_ALLOWLIST = frozenset({
    # instance data: each of these four is rebuilt by scrub.py (PostToolUse)
    "search_workflow_executions",
    "get_workflow_execution",
    "search_workflows",
    "get_workflow_details",
    # n8n's own node documentation (no instance data)
    "get_node_types",
    "search_nodes",
})

MAX_NODE_NAMES = 3
TRUNCATE_MIN, TRUNCATE_MAX = 1, 2

_HANDOFF = (
    "triage is read-only; run the fix through /model-router:fabstra in a "
    "fresh session. This guard stays on for the rest of the session."
)


def _deny(tool, why):
    return f"[triage] blocked {tool}: {why}"


def _check_execution_read(tool, tool_input):
    """Payload minimisation for get_workflow_execution."""
    include = tool_input.get("includeData")
    if include is None or include is False:
        return None
    names = tool_input.get("nodeNames")
    if not isinstance(names, list) or not 1 <= len(names) <= MAX_NODE_NAMES:
        return _deny(tool, "includeData true needs nodeNames, a list of 1 to "
                           f"{MAX_NODE_NAMES} node names. Never read full payloads.")
    if not all(isinstance(n, str) and n.strip() for n in names):
        return _deny(tool, "every nodeNames entry must be a non-empty node name.")
    trunc = tool_input.get("truncateData")
    if type(trunc) is not int or not TRUNCATE_MIN <= trunc <= TRUNCATE_MAX:
        return _deny(tool, "includeData true needs truncateData set to an "
                           f"integer {TRUNCATE_MIN} or {TRUNCATE_MAX}. "
                           "Never read full payloads.")
    return None


def split_mcp(tool):
    """`mcp__<server>__<tool>` -> (server, tool); None when not that shape."""
    if not tool.startswith(MCP):
        return None
    server, sep, short = tool[len(MCP):].partition(SEP)
    if not sep or not server or not short:
        return None
    return server, short


def is_n8n_tool(tool):
    """True when the guard must judge `tool` (n8n server or unparsable n8n)."""
    parts = split_mcp(tool)
    if parts is None:
        return tool.startswith(MCP) and "n8n" in tool.lower()
    return parts[0].lower().startswith("n8n")


def check(payload):
    """Return a deny reason (str) for a parsed hook payload, or None to allow.

    `payload` is the decoded PreToolUse JSON. Anything that is not a dict
    with a string tool_name is denied (fail closed).
    """
    if not isinstance(payload, dict):
        return _deny("<unknown tool>", "hook payload is not a JSON object.")
    tool = payload.get("tool_name")
    if not isinstance(tool, str):
        return _deny("<unknown tool>", "hook payload has no tool_name.")
    if not is_n8n_tool(tool):
        return None
    parts = split_mcp(tool)
    if parts is None:
        return _deny(tool, "unparsable n8n MCP tool name; failing closed.")
    short = parts[1]
    if short not in READ_ALLOWLIST:
        return _deny(tool, _HANDOFF)
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return _deny(tool, "tool_input cannot be read.")
    if short == "get_workflow_execution":
        return _check_execution_read(tool, tool_input)
    return None


def decide(raw):
    """Full stdin text -> deny reason or None. Never raises."""
    try:
        payload = json.loads(raw)
    except Exception:
        return _deny("<unknown tool>", "hook payload is not valid JSON.")
    tool = payload.get("tool_name") if isinstance(payload, dict) else None
    try:
        return check(payload)
    except Exception:
        try:
            if isinstance(tool, str) and not is_n8n_tool(tool):
                return None
        except Exception:
            pass
        return _deny(tool if isinstance(tool, str) else "<unknown tool>",
                     "internal guard error; failing closed.")


def main():
    try:
        data = sys.stdin.buffer.read()
        raw = data.decode("utf-8", errors="replace")
    except Exception:
        raw = None
    try:
        reason = decide(raw) if raw is not None else _deny(
            "<unknown tool>", "stdin cannot be read.")
    except Exception:
        reason = _deny("<unknown tool>", "internal guard error; failing closed.")

    if reason:
        sys.stderr.write(reason + "\n")
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
