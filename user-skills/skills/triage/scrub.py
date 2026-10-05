#!/usr/bin/env python3
"""PostToolUse scrubber for the /triage skill: structure only.

Reads a Claude Code PostToolUse hook payload from stdin (see
https://code.claude.com/docs/en/hooks) for the four allowlisted n8n reads that
return instance data -- `search_workflow_executions`, `get_workflow_execution`,
`search_workflows`, `get_workflow_details` -- on any n8n MCP server (name
starts with n8n, case-insensitive), and replaces the tool's output BEFORE the
model sees it. Registered via /triage's own SKILL.md frontmatter `hooks:`
block.

Why structure only: every free-text masking scheme leaked (quoted passwords,
Basic auth, URLs with apostrophes, URL expressions) and over-masked ordinary
node names. So no free text reaches the model at all.

Contract:
  - Input: `tool_response` for an MCP tool is a list of content blocks
    ({"type": "text", "text": <JSON>}); a bare string is also accepted.
  - Output (always, exit 0): {"hookSpecificOutput": {"hookEventName":
    "PostToolUse", "updatedMCPToolOutput": [{"type": "text", "text": ...}]}}.
  - The replacement is REBUILT from validated structural fields only; a field
    whose value fails its validator is DROPPED (never masked); JSON null
    passes for any scalar field except sameAsDraft (it carries no data):
      ids      execution id, executionId: [0-9]{1,20}; workflowId, workflow
               id, settings.errorWorkflow: [A-Za-z0-9]{1,32} (an integer is
               checked as its decimal text); list cursor: base64-like
      enums    status, executionStatus: canceled crashed error new running
               success unknown waiting; mode: cli error integrated internal
               manual retry trigger webhook evaluation chat; onError:
               stopWorkflow continueRegularOutput continueErrorOutput;
               connection type keys and target type: main | ai_[a-zA-Z]{1,32}
      time     startedAt, stoppedAt, startTime, createdAt, updatedAt: an
               ISO-8601 string that datetime.fromisoformat parses (Z read as
               +00:00), or a ms-epoch number 10^12..10^14
      flags    active, disabled, continueOnFail, retryOnFail, hasMore,
               estimated, sameAsDraft (from workflow.activeVersion): boolean;
               count: integer 0..10,000,000; connection index: integer;
               typeVersion: number, 0 < v <= 100
      error    name (class): only a name in ERROR_CLASSES (n8n's own error
               classes and JS built-ins; client code can set error.name);
               httpCode: three digits, string or int, emitted as a string
      type     node type: (@scope/)?package.nodeName, scope and package
               lower-case [a-z0-9-]
      label    node names (lastNodeExecuted, error.node.name, runData keys,
               nodes[].name, connection keys and targets) and workflow
               names: passed RAW when 1..128 printable chars with no `@`,
               `://`, `=`, run of 6+ digits, 9+ digits in total, host/path
               shape (example.com/, example.com:8080/, 10.0.0.1/,
               localhost:5678/) or credential pair (pass:, api_key:,
               access-token=, username:, ...; `_` and `-` join words)
               (and not itself shaped like [LABEL-n]); otherwise a unique
               [LABEL-n], the same n for the same name everywhere in one
               response, so keys never collide.
    NaN and Infinity are dropped everywhere; the output is strict JSON.
    Nothing else: no message, description, parameters, url, credentials,
    notes, pinData, stack, context, items, tags, activeVersion graph.
  - Fail closed: unparsable stdin or text, a non-object, an unexpected
    structure, a non-text block, an unknown n8n tool, or any internal error
    -> the whole output becomes the single UNDIAGNOSED line. A tool on a
    non-n8n server (the matcher should never send one) -> exit 0, no output.

Residual: node and workflow names are developer-written labels and pass
through when they look like labels. If python cannot start, Claude Code treats
the hook as failed and the original output goes through -- the guard's
payload minimisation (nodeNames 1-3, truncateData 1-2) still applies.

Not scrubbed, on purpose: get_node_types and search_nodes are allowlisted by
guard.py but return n8n's own node documentation, not instance data, so the
PostToolUse matcher does not send them here. Every other n8n read is denied.

stdlib only.
"""
import json
import math
import re
import sys
from datetime import datetime

UNDIAGNOSED = ("[triage] scrubber could not parse the response; treat this "
               "execution as UNDIAGNOSED")
NOTE = ("structure only: error text, parameters, URLs and items removed by "
        "triage/scrub.py; [LABEL-n] = a name that did not look like a label")
EXEC_TOOL = "get_workflow_execution"
DETAILS_TOOL = "get_workflow_details"
SEARCH_EXEC_TOOL = "search_workflow_executions"
SEARCH_WF_TOOL = "search_workflows"


class Unexpected(Exception):
    """The response does not have a shape this scrubber understands."""


# ---------------------------------------------------------------------------
# Validators: value -> kept value, or _DROP
# ---------------------------------------------------------------------------

_DROP = object()
_EXEC_ID = re.compile(r"[0-9]{1,20}")
_WF_ID = re.compile(r"[A-Za-z0-9]{1,32}")
_ISO = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})?")
_CURSOR = re.compile(r"[A-Za-z0-9_\-+/=.]{1,512}")
_HTTP = re.compile(r"\d{3}")
_TYPE = re.compile(r"(@[a-z0-9-]{1,64}/)?[a-z0-9-]{1,64}\.[A-Za-z0-9]{1,64}")
_CONN_TYPE = re.compile(r"main|ai_[a-zA-Z]{1,32}")
_DIGIT_RUN = re.compile(r"\d{6}")
_NON_DIGIT = re.compile(r"\D")
_HOST_PATH = re.compile(
    r"([A-Za-z0-9-]+\.[A-Za-z]{2,}|\d{1,3}(\.\d{1,3}){3})(:\d{1,5})?/"
    r"|(?i:localhost)(:\d+)?/")
# `_` and `-` join words (api_key, client-secret); a letter does not (Monkey:)
_CRED_PAIR = re.compile(
    r"(?i)(^|[^a-z])(api[_-]?key|access[_-]?token|refresh[_-]?token"
    r"|auth[_-]?token|client[_-]?secret|secret|token|pass(word)?|pwd|key"
    r"|user(name)?|login)\s*[:=]")
_GENERATED = re.compile(r"\[LABEL-\d+\]")

STATUSES = frozenset({"canceled", "crashed", "error", "new", "running",
                      "success", "unknown", "waiting"})
MODES = frozenset({"cli", "error", "integrated", "internal", "manual", "retry",
                   "trigger", "webhook", "evaluation", "chat"})
ON_ERROR = frozenset({"stopWorkflow", "continueRegularOutput",
                      "continueErrorOutput"})
EPOCH_MS_MIN, EPOCH_MS_MAX = 10 ** 12, 10 ** 14
COUNT_MAX = 10_000_000
TYPE_VERSION_MAX = 100
# error.name passes only when it is one of these: n8n's own error classes plus
# JS built-ins. A pattern is not enough: client code (a Function or Code node)
# can set error.name from item data, e.g. customer + 'Error'.
ERROR_CLASSES = frozenset({
    "NodeApiError", "NodeOperationError", "NodeSslError", "ExpressionError",
    "WorkflowOperationError", "SubworkflowOperationError",
    "CliWorkflowOperationError", "WorkflowActivationError",
    "WorkflowDeactivationError", "WebhookPathTakenError",
    "ExecutionCancelledError", "ManualExecutionCancelledError",
    "TimeoutExecutionCancelledError", "SystemShutdownExecutionCancelledError",
    "CredentialAccessError", "TriggerCloseError", "ApplicationError",
    "UnexpectedError", "UserError", "OperationalError", "ExecutionBaseError",
    "NodeError", "Error", "TypeError", "ReferenceError", "SyntaxError",
    "RangeError", "EvalError", "URIError", "AggregateError", "AbortError",
    "TimeoutError"})


def _is_int(v):
    return type(v) is int


def _is_num(v):
    """A finite JSON number (never bool, NaN or Infinity)."""
    return type(v) is int or (type(v) is float and math.isfinite(v))


def _pattern(rx):
    def check(v):
        return v if isinstance(v, str) and rx.fullmatch(v) else _DROP
    return check


def _id(rx):
    """String id matching rx; an integer is checked as its decimal text."""
    def check(v):
        s = str(v) if _is_int(v) else v
        return v if isinstance(s, str) and rx.fullmatch(s) else _DROP
    return check


def _enum(values):
    def check(v):
        return v if isinstance(v, str) and v in values else _DROP
    return check


def v_time(v):
    if _is_num(v):
        return v if EPOCH_MS_MIN <= v <= EPOCH_MS_MAX else _DROP
    if not (isinstance(v, str) and _ISO.fullmatch(v)):
        return _DROP
    try:
        datetime.fromisoformat(v[:-1] + "+00:00" if v.endswith("Z") else v)
    except ValueError:
        return _DROP
    return v


def v_bool(v):
    return v if isinstance(v, bool) else _DROP


def v_int(v):
    return v if _is_int(v) else _DROP


def v_count(v):
    return v if _is_int(v) and 0 <= v <= COUNT_MAX else _DROP


def v_type_version(v):
    return v if _is_num(v) and 0 < v <= TYPE_VERSION_MAX else _DROP


def v_http(v):
    if _is_int(v):
        return str(v) if 100 <= v <= 999 else _DROP
    return _pattern(_HTTP)(v)


v_cursor = _pattern(_CURSOR)
v_type = _pattern(_TYPE)
v_conn_type = _pattern(_CONN_TYPE)
v_exec_id = _id(_EXEC_ID)
v_wf_id = _id(_WF_ID)
v_status = _enum(STATUSES)
v_mode = _enum(MODES)
v_on_error = _enum(ON_ERROR)
v_class = _enum(ERROR_CLASSES)


def label_ok(s):
    """True when a name looks like a developer-written label."""
    return (isinstance(s, str) and 1 <= len(s) <= 128 and s.isprintable()
            and "@" not in s and "://" not in s and "=" not in s
            and not _DIGIT_RUN.search(s) and not _GENERATED.fullmatch(s)
            and len(_NON_DIGIT.sub("", s)) < 9
            and not _HOST_PATH.search(s) and not _CRED_PAIR.search(s))


class Labels:
    """Per-response label mapper: raw when label_ok, else [LABEL-n] with n
    stable for the same name within this response."""

    def __init__(self):
        self._bad = {}

    def __call__(self, v):
        if v is None:
            return None
        if not isinstance(v, str):
            raise Unexpected("name is not a string")
        if label_ok(v):
            return v
        if v not in self._bad:
            self._bad[v] = "[LABEL-%d]" % (len(self._bad) + 1)
        return self._bad[v]


def _put(out, src, key, check):
    """Copy src[key] into out when present and valid; null always passes."""
    if not isinstance(src, dict) or key not in src:
        return
    v = src[key]
    if v is None:
        out[key] = None
        return
    v = check(v)
    if v is not _DROP:
        out[key] = v


def _fields(src, spec):
    out = {}
    for key, check in spec:
        _put(out, src, key, check)
    return out


def _error(err, labels, with_node):
    if not isinstance(err, dict):
        return None
    out = {}
    node = err.get("node")
    if with_node and isinstance(node, dict) and "name" in node:
        out["node"] = {"name": labels(node["name"])}
    _put(out, err, "name", v_class)
    _put(out, err, "httpCode", v_http)
    return out


def _obj(v, what):
    if not isinstance(v, dict):
        raise Unexpected(what + " is not an object")
    return v


def _list(v, what):
    if not isinstance(v, list):
        raise Unexpected(what + " is not a list")
    return v


# ---------------------------------------------------------------------------
# get_workflow_execution
# ---------------------------------------------------------------------------

EXEC_META = (("id", v_exec_id), ("executionId", v_exec_id),
             ("workflowId", v_wf_id), ("status", v_status), ("mode", v_mode),
             ("startedAt", v_time), ("stoppedAt", v_time))
RUN_FIELDS = (("executionStatus", v_status), ("startTime", v_time))


def scrub_execution(obj, labels):
    obj = _obj(obj, "execution")
    cands = [obj]
    if isinstance(obj.get("execution"), dict):
        cands.append(obj["execution"])
    out = {}
    for key, check in EXEC_META:
        src = next((c for c in cands if key in c), None)
        _put(out, src, key, check)
    data = next((c["data"] for c in cands if c.get("data") is not None), None)
    if data is not None:
        rd = _obj(data, "data").get("resultData")
        if rd is not None:
            rd = _obj(rd, "resultData")
            rout = {}
            if "lastNodeExecuted" in rd:
                rout["lastNodeExecuted"] = labels(rd["lastNodeExecuted"])
            err = _error(rd.get("error"), labels, with_node=True)
            if err is not None:
                rout["error"] = err
            if rd.get("runData") is not None:
                rout["runData"] = {}
                for node, runs in _obj(rd["runData"], "runData").items():
                    kept = []
                    for run in _list(runs, "runData entry"):
                        run = _obj(run, "run")
                        r = {}
                        e = _error(run.get("error"), labels, with_node=False)
                        if e is not None:
                            r["error"] = e
                        r.update(_fields(run, RUN_FIELDS))
                        kept.append(r)
                    rout["runData"][labels(node)] = kept
            out["data"] = {"resultData": rout}
    if not out:
        raise Unexpected("no execution fields")
    return out


# ---------------------------------------------------------------------------
# get_workflow_details
# ---------------------------------------------------------------------------

NODE_FIELDS = (("type", v_type), ("typeVersion", v_type_version),
               ("disabled", v_bool), ("onError", v_on_error),
               ("continueOnFail", v_bool), ("retryOnFail", v_bool))


def _connections(conns, labels):
    """{source: {connType: [[{node, type, index}] | null]}} -> same shape,
    labels mapped, ids/indexes validated; any other shape -> Unexpected."""
    out = {}
    for src, by_type in _obj(conns, "connections").items():
        kept = {}
        for ctype, outputs in _obj(by_type, "connection").items():
            if v_conn_type(ctype) is _DROP:
                continue
            outs = []
            for targets in _list(outputs, "connection outputs"):
                if targets is None:
                    outs.append(None)
                    continue
                tl = []
                for t in _list(targets, "connection targets"):
                    t = _obj(t, "connection target")
                    nt = {"node": labels(t.get("node"))}
                    _put(nt, t, "type", v_conn_type)
                    _put(nt, t, "index", v_int)
                    tl.append(nt)
                outs.append(tl)
            kept[ctype] = outs
        out[labels(src)] = kept
    return out


def scrub_details(obj, labels):
    obj = _obj(obj, "workflow")
    cands = [obj]
    if isinstance(obj.get("workflow"), dict):
        cands.append(obj["workflow"])
    wf = next((c for c in cands if "nodes" in c), None)
    if wf is None:
        raise Unexpected("no nodes list")
    nodes = _list(wf["nodes"], "nodes")
    out = _fields(wf, (("id", v_wf_id),))
    if "name" in wf:
        out["name"] = labels(wf["name"])
    _put(out, wf, "active", v_bool)
    # draft vs published graph (workflow.activeVersion.sameAsDraft): bool only
    active = wf.get("activeVersion")
    if isinstance(active, dict) and isinstance(active.get("sameAsDraft"), bool):
        out["sameAsDraft"] = active["sameAsDraft"]
    settings = _fields(wf.get("settings"), (("errorWorkflow", v_wf_id),))
    if settings:
        out["settings"] = settings
    if wf.get("connections") is not None:
        out["connections"] = _connections(wf["connections"], labels)
    kept = []
    for node in nodes:
        node = _obj(node, "node")
        n = {}
        if "name" in node:
            n["name"] = labels(node["name"])
        n.update(_fields(node, NODE_FIELDS))
        kept.append(n)
    out["nodes"] = kept
    return out


# ---------------------------------------------------------------------------
# search_workflow_executions / search_workflows (documented shape:
# {"data": [...], "count": n, ...}; a bare list is also accepted)
# ---------------------------------------------------------------------------

EXEC_ITEM = (("id", v_exec_id), ("workflowId", v_wf_id),
             ("status", v_status), ("mode", v_mode),
             ("startedAt", v_time), ("stoppedAt", v_time))
PAGE_FIELDS = (("count", v_count), ("estimated", v_bool), ("hasMore", v_bool),
               ("nextCursor", v_cursor))


def _items(obj):
    data = obj.get("data") if isinstance(obj, dict) else obj
    return [_obj(i, "list item") for i in _list(data, "data")]


def _page(obj, data):
    out = {"data": data}
    out.update(_fields(obj, PAGE_FIELDS))
    return out


def scrub_search_executions(obj, labels):
    return _page(obj, [_fields(i, EXEC_ITEM) for i in _items(obj)])


def scrub_search_workflows(obj, labels):
    data = []
    for item in _items(obj):
        w = _fields(item, (("id", v_wf_id),))
        if "name" in item:
            w["name"] = labels(item["name"])
        w.update(_fields(item, (("active", v_bool), ("createdAt", v_time),
                                ("updatedAt", v_time))))
        data.append(w)
    return _page(obj, data)


# ---------------------------------------------------------------------------
# Hook plumbing
# ---------------------------------------------------------------------------

def _split(tool):
    """`mcp__<server>__<tool>` -> (server, tool), else None."""
    if not isinstance(tool, str) or not tool.startswith("mcp__"):
        return None
    server, sep, short = tool[5:].partition("__")
    if not sep or not server or not short:
        return None
    return server, short


def _texts(resp):
    if isinstance(resp, str):
        return [resp]
    if isinstance(resp, dict) and isinstance(resp.get("content"), list):
        resp = resp["content"]
    if not isinstance(resp, list) or not resp:
        raise Unexpected("tool_response is not a list of content blocks")
    texts = []
    for block in resp:
        if not (isinstance(block, dict) and block.get("type") == "text"
                and isinstance(block.get("text"), str)):
            raise Unexpected("non-text content block")
        texts.append(block["text"])
    return texts


def _line():
    return [{"type": "text", "text": UNDIAGNOSED}]


def rewrite(payload):
    """Parsed PostToolUse payload -> replacement content blocks. Never raises;
    any failure returns the single UNDIAGNOSED line."""
    try:
        parts = _split(payload.get("tool_name")) if isinstance(payload, dict) else None
        if parts is None or not parts[0].lower().startswith("n8n"):
            return _line()
        scrubber = {EXEC_TOOL: scrub_execution,
                    DETAILS_TOOL: scrub_details,
                    SEARCH_EXEC_TOOL: scrub_search_executions,
                    SEARCH_WF_TOOL: scrub_search_workflows}.get(parts[1])
        if scrubber is None:
            return _line()
        labels = Labels()  # one mapping per response
        blocks = []
        for text in _texts(payload.get("tool_response")):
            clean = {"_triage": NOTE, **scrubber(json.loads(text), labels)}
            blocks.append({"type": "text",
                           "text": json.dumps(clean, ensure_ascii=True,
                                              allow_nan=False)})
        return blocks
    except Exception:
        return _line()


def envelope(blocks):
    return {"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                   "updatedMCPToolOutput": blocks}}


def _passes(payload):
    """A tool on a non-n8n server: the matcher should never send one."""
    if not isinstance(payload, dict):
        return False
    tool = payload.get("tool_name")
    if not isinstance(tool, str):
        return False
    parts = _split(tool)
    if parts is None:
        return not tool.startswith("mcp__")
    return not parts[0].lower().startswith("n8n")


def main():
    blocks = _line()
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        payload = json.loads(raw)
        if _passes(payload):
            sys.exit(0)
        blocks = rewrite(payload)
    except SystemExit:
        raise
    except Exception:
        blocks = _line()
    try:
        out = json.dumps(envelope(blocks), ensure_ascii=True, allow_nan=False)
    except Exception:
        out = json.dumps(envelope(_line()), ensure_ascii=True, allow_nan=False)
    sys.stdout.buffer.write(out.encode("ascii"))
    sys.stdout.buffer.flush()
    sys.exit(0)


if __name__ == "__main__":
    main()
