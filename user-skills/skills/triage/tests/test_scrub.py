"""Tests for the /triage PostToolUse scrubber (scrub.py): structure only.

Fixtures model the observed n8n MCP shapes (field names only, fake values).
The scrubber rebuilds each of the four instance-data reads from validated
structural fields; free text (messages, descriptions, parameters, URLs,
credentials, notes, items, tags) never survives; a field that fails its
validator is dropped; a structural mismatch fails closed. Local only.
"""
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scrub  # noqa: E402

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRUB_PATH = SKILL_DIR / "scrub.py"
GWE = "mcp__n8n-mcp__get_workflow_execution"
GWD = "mcp__n8n-mcp__get_workflow_details"
SW = "mcp__n8n-mcp__search_workflows"
SWE = "mcp__n8n-mcp__search_workflow_executions"
UNDIAGNOSED = ("[triage] scrubber could not parse the response; treat this "
               "execution as UNDIAGNOSED")

INPUT_ITEM = {"json": {"email": "jane@example.com", "name": "Jane Citizen",
                       "phone": "+61 412 345 678", "address": "42 Wallaby Way",
                       "note": "cust-secret-note"}}

EXECUTION = {
    "id": "4711",
    "workflowId": "wfAbC123",
    "mode": "trigger",
    "status": "error",
    "startedAt": "2026-10-01T03:04:05.000Z",
    "stoppedAt": "2026-10-01T03:04:06.000Z",
    "retryOf": None,
    "customData": {"customer": "jane@example.com"},
    "data": {
        "startData": {},
        "resultData": {
            "lastNodeExecuted": "HTTP Request",
            "error": {
                "node": {"name": "HTTP Request",
                         "type": "n8n-nodes-base.httpRequest",
                         "parameters": {"url": "https://hooks.example.com/x"}},
                "name": "NodeApiError",
                "message": "Request failed with status code 422",
                "description": "Contact jane@example.com or call 0412345678",
                "httpCode": "422",
                "stack": "NodeApiError: at /srv/n8n/jane@example.com",
                "context": {"itemIndex": 0, "data": INPUT_ITEM},
            },
            "runData": {
                "Webhook": [{
                    "startTime": 1759287845000,
                    "executionTime": 3,
                    "executionStatus": "success",
                    "source": [],
                    "data": {"main": [[INPUT_ITEM]]},
                }],
                "HTTP Request": [{
                    "startTime": 1759287845100,
                    "executionStatus": "error",
                    "error": {"name": "NodeApiError",
                              "message": "Unprocessable for jane@example.com",
                              "description": "see https://api.example.com/v1/x?token=abc123token",
                              "httpCode": 422,
                              "stack": "trace"},
                    "data": {"main": [[INPUT_ITEM]]},
                    "inputOverride": {"main": [[INPUT_ITEM]]},
                }],
            },
        },
        "executionData": {
            "contextData": {},
            "nodeExecutionStack": [{"node": {"name": "HTTP Request"},
                                    "data": {"main": [[INPUT_ITEM]]},
                                    "source": None}],
            "waitingExecution": {},
            "waitingExecutionSource": {},
        },
        "resumeToken": "resume-abc123token",
    },
}

EXECUTION_EXPECTED = {
    "id": "4711", "workflowId": "wfAbC123", "status": "error", "mode": "trigger",
    "startedAt": "2026-10-01T03:04:05.000Z",
    "stoppedAt": "2026-10-01T03:04:06.000Z",
    "data": {"resultData": {
        "lastNodeExecuted": "HTTP Request",
        "error": {"node": {"name": "HTTP Request"}, "name": "NodeApiError",
                  "httpCode": "422"},
        "runData": {
            "Webhook": [{"executionStatus": "success", "startTime": 1759287845000}],
            "HTTP Request": [{"error": {"name": "NodeApiError", "httpCode": "422"},
                              "executionStatus": "error",
                              "startTime": 1759287845100}],
        },
    }},
}

WORKFLOW = {
    "id": "wfAbC123",
    "name": "Lead intake",
    "description": "Owner contact jane@example.com",
    "active": True,
    "tags": [{"id": "t1", "name": "Client Jane Citizen"}],
    "settings": {"errorWorkflow": "wfErr9", "timezone": "Australia/Sydney",
                 "callerPolicy": "workflowsFromSameOwner"},
    "staticData": {"lastId": "jane@example.com"},
    "pinData": {"Webhook": [INPUT_ITEM]},
    "connections": {"Webhook": {"main": [[{"node": "HTTP Request",
                                           "type": "main", "index": 0}]]}},
    "nodes": [
        {
            "id": "0f8b-uuid", "name": "Webhook",
            "type": "n8n-nodes-base.webhook", "typeVersion": 2,
            "webhookId": "hooksecret987",
            "parameters": {"path": "hooksecret987", "httpMethod": "POST"},
        },
        {
            "id": "1a2b-uuid", "name": "HTTP Request",
            "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
            "onError": "continueErrorOutput", "retryOnFail": True,
            "continueOnFail": False, "disabled": False,
            "notes": "owner Jane Citizen",
            "credentials": {"httpHeaderAuth": {"id": "c1", "name": "Jane key"}},
            "parameters": {
                "method": "POST",
                "url": "https://user:s3cr3tP4ss@hooks.example.com/services/"
                       "T0000/B0000/XXXXXXXXXXXXXXXXXXXX1234?token=abc123token",
                "headerParameters": {"parameters": [
                    {"name": "Authorization",
                     "value": "Bearer " + "sk_" + "live_51HxYzAbCdEfGh1234567890"}]},
                "jsonBody": "{\"email\": \"jane@example.com\"}",
                "options": {"timeout": 10000},
            },
        },
        {
            "name": "Sheets", "type": "n8n-nodes-base.googleSheets",
            "typeVersion": 4, "parameters": {
                "resource": "sheet", "operation": "append",
                "documentId": {"__rl": True, "value": "1AbC"},
            },
        },
    ],
}

WORKFLOW_EXPECTED = {
    "id": "wfAbC123", "name": "Lead intake", "active": True,
    "settings": {"errorWorkflow": "wfErr9"},
    "connections": {"Webhook": {"main": [[{"node": "HTTP Request",
                                           "type": "main", "index": 0}]]}},
    "nodes": [
        {"name": "Webhook", "type": "n8n-nodes-base.webhook", "typeVersion": 2},
        {"name": "HTTP Request", "type": "n8n-nodes-base.httpRequest",
         "typeVersion": 4.2, "onError": "continueErrorOutput",
         "retryOnFail": True, "continueOnFail": False, "disabled": False},
        {"name": "Sheets", "type": "n8n-nodes-base.googleSheets", "typeVersion": 4},
    ],
}

SEARCH_WORKFLOWS = {
    "data": [{
        "id": "wfAbC123", "name": "Lead intake",
        "description": "Owner contact jane@example.com",
        "active": True, "createdAt": "2026-09-01T00:00:00.000Z",
        "updatedAt": "2026-09-30T12:00:00.000Z", "triggerCount": 1,
        "availableInMCP": True, "parentFolderId": "fold1",
        "tags": [{"id": "t1", "name": "Client Jane Citizen"}],
        "nodes": [{"parameters": {"url": "https://x.example.com/hooksecret987"}}],
    }, {
        "id": "wfB2", "name": None, "description": None, "active": None,
        "createdAt": None, "updatedAt": None, "tags": [],
    }],
    "count": 2,
}

SEARCH_EXECUTIONS = {
    "data": [
        {"id": "4711", "workflowId": "wfAbC123", "status": "error",
         "mode": "trigger", "startedAt": "2026-10-01T03:04:05.000Z",
         "stoppedAt": "2026-10-01T03:04:06.000Z", "waitTill": None,
         "customData": {"email": "jane@example.com"}},
        {"id": "4712", "workflowId": "wfAbC123", "status": "crashed",
         "mode": "webhook", "startedAt": "2026-10-01T04:00:00.000Z",
         "stoppedAt": None},
    ],
    "count": 2, "estimated": False, "nextCursor": "eyJsYXN0SWQiOiI0NzEyIn0=",
    "error": "partial result for jane@example.com",
}


def mcp_payload(tool, obj, as_text=None):
    text = as_text if as_text is not None else json.dumps(obj)
    return {"session_id": "t", "hook_event_name": "PostToolUse",
            "tool_name": tool, "tool_input": {},
            "tool_use_id": "toolu_x",
            "tool_response": [{"type": "text", "text": text}]}


def out_text(blocks):
    assert isinstance(blocks, list) and blocks
    for b in blocks:
        assert set(b) == {"type", "text"} and b["type"] == "text"
    return "\n".join(b["text"] for b in blocks)


def scrubbed(tool, obj):
    """Rewrite one response; return (raw text, parsed object minus _triage)."""
    text = out_text(scrub.rewrite(mcp_payload(tool, obj)))
    out = json.loads(text)
    assert isinstance(out, dict) and "_triage" in out, text
    return text, {k: v for k, v in out.items() if k != "_triage"}


def run_raw(stdin_text):
    return subprocess.run([sys.executable, "-B", str(SCRUB_PATH)], input=stdin_text,
                          capture_output=True, text=True, timeout=10)


# ---------------------------------------------------------------------------
# Exact rebuilds: the output is these structural fields and NOTHING ELSE
# ---------------------------------------------------------------------------

def test_execution_rebuilt_exactly():
    assert scrubbed(GWE, EXECUTION)[1] == EXECUTION_EXPECTED


def test_execution_wrapped_under_execution_key():
    assert scrubbed(GWE, {"execution": copy.deepcopy(EXECUTION)})[1] == EXECUTION_EXPECTED


def test_execution_metadata_only():
    meta = {k: EXECUTION[k] for k in ("id", "workflowId", "status",
                                      "startedAt", "stoppedAt", "mode")}
    assert scrubbed(GWE, meta)[1] == meta


def test_details_rebuilt_exactly():
    assert scrubbed(GWD, WORKFLOW)[1] == WORKFLOW_EXPECTED


def test_details_wrapped_under_workflow_key():
    assert scrubbed(GWD, {"workflow": WORKFLOW})[1] == WORKFLOW_EXPECTED


def test_search_workflows_rebuilt_exactly():
    assert scrubbed(SW, SEARCH_WORKFLOWS)[1] == {
        "data": [{"id": "wfAbC123", "name": "Lead intake", "active": True,
                  "createdAt": "2026-09-01T00:00:00.000Z",
                  "updatedAt": "2026-09-30T12:00:00.000Z"},
                 {"id": "wfB2", "name": None, "active": None,
                  "createdAt": None, "updatedAt": None}],
        "count": 2}


def test_search_executions_rebuilt_exactly():
    assert scrubbed(SWE, SEARCH_EXECUTIONS)[1] == {
        "data": [{"id": "4711", "workflowId": "wfAbC123", "status": "error",
                  "mode": "trigger", "startedAt": "2026-10-01T03:04:05.000Z",
                  "stoppedAt": "2026-10-01T03:04:06.000Z"},
                 {"id": "4712", "workflowId": "wfAbC123", "status": "crashed",
                  "mode": "webhook", "startedAt": "2026-10-01T04:00:00.000Z",
                  "stoppedAt": None}],
        "count": 2, "estimated": False, "nextCursor": "eyJsYXN0SWQiOiI0NzEyIn0="}


def test_search_page_fields_validated():
    obj = dict(SEARCH_EXECUTIONS, nextCursor="jane@example.com next",
               count="12 for jane", estimated="no", hasMore="yes")
    assert set(scrubbed(SWE, obj)[1]) == {"data"}
    obj = dict(SEARCH_EXECUTIONS, nextCursor=None, hasMore=True)
    out = scrubbed(SWE, obj)[1]
    assert out["nextCursor"] is None and out["hasMore"] is True


def test_search_bare_list_and_empty():
    out = scrubbed(SWE, SEARCH_EXECUTIONS["data"])[1]
    assert [e["id"] for e in out["data"]] == ["4711", "4712"]
    assert scrubbed(SW, {"data": [], "count": 0})[1] == {"data": [], "count": 0}


# ---------------------------------------------------------------------------
# Reviewer leak fixtures: free text in message / description / parameters /
# url fields never reaches the output, on any of the four tools
# ---------------------------------------------------------------------------

LEAKS = [  # (fixture text, substrings that must not survive)
    ("Error: password: 's3cr3tP4ss'", ["s3cr3tP4ss"]),
    ("Authorization: Basic dXNlcjpwYXNz", ["dXNlcjpwYXNz"]),
    ("POST https://hooks.example.com/webhook/abc's3cr3tP4ss failed",
     ["s3cr3tP4ss", "hooks.example.com"]),
    ("={{ 'https://api.example.com/v1/x?key=' + 'liveKEY998877' }}",
     ["liveKEY998877", "api.example.com"]),
    ("=https://api.example.com/{{ $json.id }}?token=tokLIT4455", ["tokLIT4455"]),
    ("Remote API rejected {'user': 'admin', 'pass': 'hunter2pass'}", ["hunter2pass"]),
    ('Bad body {"api_key": "abc123token", "user": "Jane Citizen"}',
     ["abc123token", "Jane Citizen"]),
    ("card 4111 1111 1111 1111 declined", ["4111 1111 1111 1111", "declined"]),
    ("card 4111111111111111 declined", ["4111111111111111"]),
    ("https://automation.example.com/webhook/lead-hook-secret", ["lead-hook-secret"]),
    ("GET https://api.example.com/users/jane%40example.com", ["jane%40", "jane"]),
    ("Owner contact jane@example.com", ["jane@example.com", "Owner contact"]),
    ("array('password' => 'phpS3cret')", ["phpS3cret"]),
    ("<auth><password>xmlS3cret</password></auth>", ["xmlS3cret"]),
]


def _exec_with_leak(text):
    obj = copy.deepcopy(EXECUTION)
    err = obj["data"]["resultData"]["error"]
    err["message"] = err["description"] = err["stack"] = text
    err["node"]["parameters"] = {"url": text, "jsonBody": text}
    err["context"] = {"request": text}
    run_err = obj["data"]["resultData"]["runData"]["HTTP Request"][0]["error"]
    run_err["message"] = run_err["description"] = text
    obj["customData"] = {"note": text}
    return obj


def _details_with_leak(text):
    wf = copy.deepcopy(WORKFLOW)
    wf["description"] = text
    wf["tags"] = [{"id": "t9", "name": text}]
    http = wf["nodes"][1]
    http["notes"] = text
    http["credentials"] = {"httpBasicAuth": {"id": "c1", "name": text}}
    http["parameters"] = {"method": "POST", "url": text, "jsonBody": text,
                          "headerParameters": {"parameters": [
                              {"name": "Authorization", "value": text}]}}
    wf["pinData"] = {"Webhook": [{"json": {"x": text}}]}
    return wf


def _search_workflows_with_leak(text):
    obj = copy.deepcopy(SEARCH_WORKFLOWS)
    obj["data"][0]["description"] = text
    obj["data"][0]["tags"] = [{"id": "t1", "name": text}]
    obj["data"][0]["nodes"] = [{"parameters": {"url": text}}]
    return obj


def _search_executions_with_leak(text):
    obj = copy.deepcopy(SEARCH_EXECUTIONS)
    obj["data"][0]["customData"] = {"note": text}
    obj["error"] = text
    return obj


BUILDERS = [(GWE, _exec_with_leak), (GWD, _details_with_leak),
            (SW, _search_workflows_with_leak), (SWE, _search_executions_with_leak)]


@pytest.mark.parametrize("tool,build", BUILDERS, ids=[t.rsplit("__", 1)[1] for t, _ in BUILDERS])
@pytest.mark.parametrize("text,secrets", LEAKS, ids=[f"leak{i}" for i in range(len(LEAKS))])
def test_reviewer_leak_fixture_absent(tool, build, text, secrets):
    raw, out = scrubbed(tool, build(text))
    for s in secrets:
        assert s not in raw, (s, raw)
    # the structure the procedure needs is still there
    if tool == GWE:
        err = out["data"]["resultData"]["error"]
        assert err == {"node": {"name": "HTTP Request"}, "name": "NodeApiError",
                       "httpCode": "422"}
    elif tool == GWD:
        assert out["nodes"][1]["name"] == "HTTP Request"
        assert out["nodes"][1]["type"] == "n8n-nodes-base.httpRequest"
    else:
        assert out["data"][0]["id"] in ("wfAbC123", "4711")


def test_items_and_payload_keys_never_survive():
    for tool, obj in ((GWE, EXECUTION), (GWD, WORKFLOW),
                      (SW, SEARCH_WORKFLOWS), (SWE, SEARCH_EXECUTIONS)):
        raw = scrubbed(tool, obj)[0]
        for s in ("jane@example.com", "Jane Citizen", "412 345 678", "0412345678",
                  "42 Wallaby Way", "cust-secret-note", "s3cr3tP4ss", "abc123token",
                  "sk_live_", "hooksecret987", "hooks.example.com", "https://",
                  "XXXXXXXXXXXXXXXXXXXX1234", "Request failed"):
            assert s not in raw, (tool, s)
        for key in ("message", "description", "parameters", "url", "credentials",
                    "notes", "pinData", "stack", "context", "nodeExecutionStack",
                    "executionData", "resumeToken", "inputOverride", "customData",
                    "staticData", "tags", "webhookId"):
            assert f'"{key}"' not in raw, (tool, key)


# ---------------------------------------------------------------------------
# Labels: node and workflow names pass raw when they look like labels, else
# become a unique [LABEL-n], stable within one response
# ---------------------------------------------------------------------------

GOOD_LABELS = ["Update_HubSpot_Contact_v2", "Send_Notification_v1",
               "Send_Notification_v2", "HTTP Request"]
BAD_LABELS = ["jane@example.com", "Call 0412345678", "https://x.y/z", "a=b"]
BAD_FRAGMENTS = ["jane", "0412345678", "x.y/z", "a=b", "https"]
ALL_LABELS = GOOD_LABELS + BAD_LABELS


def _chain_workflow(names):
    nodes = [{"name": n, "type": "n8n-nodes-base.set", "typeVersion": 3}
             for n in names]
    conns = {a: {"main": [[{"node": b, "type": "main", "index": 0}]]}
             for a, b in zip(names, names[1:])}
    return {"id": "wf1", "name": "Label test", "nodes": nodes, "connections": conns}


def _chain_execution(names, last):
    return {"id": "9", "status": "error", "data": {"resultData": {
        "lastNodeExecuted": last,
        "error": {"node": {"name": last}, "name": "NodeOperationError"},
        "runData": {n: [{"executionStatus": "success", "startTime": 1}] for n in names},
    }}}


def test_labels_details_good_raw_bad_distinct_and_consistent():
    raw, out = scrubbed(GWD, _chain_workflow(ALL_LABELS))
    for frag in BAD_FRAGMENTS:
        assert frag not in raw, frag
    names = [n["name"] for n in out["nodes"]]
    assert names[:4] == GOOD_LABELS
    generated = names[4:]
    assert all(g.startswith("[LABEL-") and g.endswith("]") for g in generated)
    assert len(set(names)) == len(names) == 8
    # every connection key and target refers to a node name in this response
    conns = out["connections"]
    assert len(conns) == 7
    for src, by_type in conns.items():
        assert src in names
        assert by_type["main"][0][0]["node"] in names
    assert [src for src in conns] == names[:7]
    assert [conns[s]["main"][0][0]["node"] for s in names[:7]] == names[1:]


def test_labels_execution_rundata_keys_do_not_collide():
    raw, out = scrubbed(GWE, _chain_execution(ALL_LABELS, "jane@example.com"))
    for frag in BAD_FRAGMENTS:
        assert frag not in raw, frag
    rd = out["data"]["resultData"]
    keys = list(rd["runData"])
    assert len(keys) == 8 and keys[:4] == GOOD_LABELS
    assert len(set(keys[4:])) == 4
    # the same bad label maps to the same [LABEL-n] everywhere in one response
    assert rd["lastNodeExecuted"] == rd["error"]["node"]["name"]
    assert rd["lastNodeExecuted"] in keys[4:]


def test_two_bad_labels_in_one_response_do_not_collide():
    t1, t2 = 1759287845001, 1759287845002  # round 3: ms-epoch range enforced
    obj = {"id": "9", "data": {"resultData": {"runData": {
        "a=b": [{"startTime": t1}], "c=d": [{"startTime": t2}]}}}}
    rd = scrubbed(GWE, obj)[1]["data"]["resultData"]["runData"]
    assert len(rd) == 2 and sorted(v[0]["startTime"] for v in rd.values()) == [t1, t2]


def test_literal_generated_label_cannot_collide():
    # a node literally named like a generated label is itself replaced
    obj = {"id": "9", "data": {"resultData": {"runData": {
        "[LABEL-1]": [{"startTime": 1}], "a=b": [{"startTime": 2}]}}}}
    rd = scrubbed(GWE, obj)[1]["data"]["resultData"]["runData"]
    assert len(rd) == 2


def test_workflow_name_is_a_label():
    obj = copy.deepcopy(SEARCH_WORKFLOWS)
    obj["data"][0]["name"] = "Lead intake for jane@example.com"
    raw, out = scrubbed(SW, obj)
    assert "jane" not in raw and out["data"][0]["name"].startswith("[LABEL-")
    wf = dict(WORKFLOW, name="Sync 123456789 rows")
    raw, out = scrubbed(GWD, wf)
    assert "123456789" not in raw and out["name"].startswith("[LABEL-")


@pytest.mark.parametrize("s", ["", "x" * 129, "a\nb", "tab\there", "a@b",
                               "s3://bucket", "k=v", "id 123456 x", "[LABEL-3]"])
def test_label_check_rejects(s):
    assert not scrub.label_ok(s)


@pytest.mark.parametrize("s", ["x" * 128, "Node 12345", "Fehler über", "If",
                               "Update_HubSpot_Contact_v2", "HTTP Request (v2)"])
def test_label_check_accepts(s):
    assert scrub.label_ok(s)


# ---------------------------------------------------------------------------
# Validators: a field that fails its check is dropped, not masked
# ---------------------------------------------------------------------------

def _exec_set(path, value):
    obj = copy.deepcopy(EXECUTION)
    cur = obj
    for k in path[:-1]:
        cur = cur[k]
    cur[path[-1]] = value
    return obj


ERR = ("data", "resultData", "error")
RUN_ERR = ("data", "resultData", "runData", "HTTP Request", 0, "error")


@pytest.mark.parametrize("path,value", [
    (("id",), "4711; DROP"), (("id",), "4711\n"), (("id",), "x" * 65),
    (("workflowId",), "jane@example.com"), (("status",), "error for jane"),
    (("mode",), "trig ger"), (("startedAt",), "yesterday at 3"),
    (("startedAt",), True),
    (ERR + ("name",), "Error: password s3cr3t"), (ERR + ("name",), "1Bad"),
    (ERR + ("name",), "A" * 65),
    (ERR + ("httpCode",), "4xx"), (ERR + ("httpCode",), "12345"),
    (ERR + ("httpCode",), 12345), (ERR + ("httpCode",), True),
    (ERR + ("httpCode",), "422\n"),
    (RUN_ERR + ("httpCode",), 42), (RUN_ERR + ("name",), "bad class!"),
    (("data", "resultData", "runData", "HTTP Request", 0, "executionStatus"), "err or"),
])
def test_execution_bad_value_dropped(path, value):
    raw, out = scrubbed(GWE, _exec_set(path, value))
    cur = out
    for k in path[:-1]:
        cur = cur[k]
    assert path[-1] not in cur, (path, cur)
    if isinstance(value, str) and value.strip():
        assert value not in raw


def test_http_code_int_emitted_as_string():
    out = scrubbed(GWE, _exec_set(ERR + ("httpCode",), 503))[1]
    assert out["data"]["resultData"]["error"]["httpCode"] == "503"


@pytest.mark.parametrize("field,value", [
    ("type", "n8n-nodes-base.http Request"), ("type", "https://x.y/z"),
    ("type", "x" * 129), ("typeVersion", "4.2"), ("typeVersion", True),
    ("disabled", "no"), ("onError", "continue error output"),
    ("retryOnFail", 1), ("continueOnFail", "false"),
])
def test_details_node_bad_value_dropped(field, value):
    wf = copy.deepcopy(WORKFLOW)
    wf["nodes"][1][field] = value
    raw, out = scrubbed(GWD, wf)
    assert field not in out["nodes"][1]
    assert out["nodes"][1]["name"] == "HTTP Request"


def test_details_bad_settings_and_ids_dropped():
    wf = dict(copy.deepcopy(WORKFLOW), id="wf 1", active="yes",
              settings={"errorWorkflow": "wf err"})
    out = scrubbed(GWD, wf)[1]
    assert "id" not in out and "active" not in out and "settings" not in out


def test_details_scoped_package_type_kept():
    wf = copy.deepcopy(WORKFLOW)
    wf["nodes"][1]["type"] = "@n8n/n8n-nodes-langchain.agent"
    assert scrubbed(GWD, wf)[1]["nodes"][1]["type"] == "@n8n/n8n-nodes-langchain.agent"


def test_connection_bad_type_and_index_dropped():
    wf = copy.deepcopy(WORKFLOW)
    wf["connections"] = {"Webhook": {"main": [[{"node": "HTTP Request",
                                                "type": "ma in", "index": "0"}]],
                                     "bad key": [[]]}}
    out = scrubbed(GWD, wf)[1]
    assert out["connections"] == {"Webhook": {"main": [[{"node": "HTTP Request"}]]}}


def test_search_item_bad_values_dropped():
    obj = copy.deepcopy(SEARCH_EXECUTIONS)
    obj["data"][0]["id"] = "47 11"
    obj["data"][0]["startedAt"] = "Oct 1st"
    item = scrubbed(SWE, obj)[1]["data"][0]
    assert "id" not in item and "startedAt" not in item and item["status"] == "error"


# ---------------------------------------------------------------------------
# Round 3 hardening: data-shaped strings no longer pass n8n-controlled slots.
# Each case: (field path, value, kept?)
# ---------------------------------------------------------------------------

NAN, INF = float("nan"), float("inf")
SECRET = "s3cr3tP4ss"
RUN = ("data", "resultData", "runData", "HTTP Request", 0)


@pytest.mark.parametrize("path,value,kept", [
    (("status",), "canceled", True), (("status",), "waiting", True),
    (("status",), SECRET, False), (("status",), "ERROR", False),
    (("mode",), "manual", True), (("mode",), "evaluation", True),
    (("mode",), SECRET, False), (("mode",), "trigger_x", False),
    (RUN + ("executionStatus",), "success", True),
    (RUN + ("executionStatus",), SECRET, False),
    (ERR + ("name",), "NodeOperationError", True),
    (ERR + ("name",), "ExpressionError", True),
    (ERR + ("name",), SECRET, False), (ERR + ("name",), "nodeApiError", False),
    (ERR + ("name",), "NodeApiError2", False), (ERR + ("name",), "Node_ApiError", False),
    (RUN_ERR + ("name",), "NodeApiError", True), (RUN_ERR + ("name",), SECRET, False),
    (("id",), "4711", True), (("id",), 4711, True), (("id",), "9" * 20, True),
    (("id",), "9" * 21, False), (("id",), "4711x", False), (("id",), -5, False),
    (("executionId",), "4712", True), (("executionId",), SECRET, False),
    (("workflowId",), "wfAbC123", True), (("workflowId",), "wf_AbC123", False),
    (("workflowId",), "x" * 33, False), (("workflowId",), "wf-1", False),
    (("startedAt",), "2026-10-01T03:04:05.000Z", True),
    (("startedAt",), "2026-10-01T03:04:05+10:00", True),
    (("startedAt",), "2026-13-45T03:04:05Z", False),
    (("startedAt",), "2026-02-30T03:04:05Z", False),
    (("startedAt",), 1759287845000, True), (("startedAt",), 1759287845, False),
    (("startedAt",), NAN, False), (("startedAt",), INF, False),
    (RUN + ("startTime",), 10 ** 12, True), (RUN + ("startTime",), 10 ** 14, True),
    (RUN + ("startTime",), 10 ** 14 + 1, False),
    (RUN + ("startTime",), 10 ** 12 - 1, False),
    (RUN + ("startTime",), 4111111111111111, False),
    (RUN + ("startTime",), NAN, False), (RUN + ("startTime",), -INF, False),
    (RUN + ("startTime",), True, False),
])
def test_r3_execution_field(path, value, kept):
    raw, out = scrubbed(GWE, _exec_set(path, value))
    cur = out
    for k in path[:-1]:
        cur = cur[k]
    if kept:
        assert cur[path[-1]] == value, (path, cur)
    else:
        assert path[-1] not in cur, (path, cur)
        if isinstance(value, str):
            assert value not in raw


@pytest.mark.parametrize("field,value,kept", [
    ("type", "n8n-nodes-base.httpRequest", True),
    ("type", "@n8n/n8n-nodes-langchain.agent", True),
    ("type", "n8n-nodes-foo.myNode2", True),
    ("type", "hooks.example.com/webhook/s3cr3tP4ss", False),
    ("type", "n8n-nodes-httprequest", False), ("type", "N8N-nodes-base.http", False),
    ("type", "@n8n/sub/n8n-nodes.agent", False),
    ("typeVersion", 4.2, True), ("typeVersion", 100, True), ("typeVersion", 1, True),
    ("typeVersion", 4111111111111111, False), ("typeVersion", 0, False),
    ("typeVersion", -1, False), ("typeVersion", 100.5, False),
    ("typeVersion", NAN, False), ("typeVersion", INF, False), ("typeVersion", -INF, False),
    ("onError", "stopWorkflow", True), ("onError", "continueRegularOutput", True),
    ("onError", "continueErrorOutput", True), ("onError", SECRET, False),
    ("onError", "continue_error_output", False),
])
def test_r3_details_node_field(field, value, kept):
    wf = copy.deepcopy(WORKFLOW)
    wf["nodes"][1][field] = value
    raw, out = scrubbed(GWD, wf)
    node = out["nodes"][1]
    assert node["name"] == "HTTP Request"
    if kept:
        assert node[field] == value
    else:
        assert field not in node
        if isinstance(value, str):
            assert value not in raw


def test_r3_connection_types():
    wf = copy.deepcopy(WORKFLOW)
    wf["connections"] = {
        "Webhook": {
            "main": [[{"node": "HTTP Request", "type": "main", "index": 0}]],
            "ai_languageModel": [[{"node": "HTTP Request", "type": "ai_tool"}]],
            SECRET: [[{"node": "HTTP Request", "type": "main"}]],
            "ai_": [[]], "ai_x1": [[]], "Main": [[]],
        },
        "HTTP Request": {"main": [[{"node": "Sheets", "type": SECRET},
                                  {"node": "Sheets", "type": "ai_"},
                                  {"node": "Sheets", "type": "hooks.example.com/x"}]]},
    }
    raw, out = scrubbed(GWD, wf)
    assert out["connections"] == {
        "Webhook": {
            "main": [[{"node": "HTTP Request", "type": "main", "index": 0}]],
            "ai_languageModel": [[{"node": "HTTP Request", "type": "ai_tool"}]],
        },
        "HTTP Request": {"main": [[{"node": "Sheets"}, {"node": "Sheets"},
                                  {"node": "Sheets"}]]},
    }
    assert SECRET not in raw and "hooks.example.com" not in raw


@pytest.mark.parametrize("value,kept", [
    ("wfAbC123", True), ("x" * 32, True), ("x" * 33, False),
    ("wf_err-9", False), (SECRET + "!", False),
])
def test_r3_workflow_ids(value, kept):
    wf = dict(copy.deepcopy(WORKFLOW), id=value, settings={"errorWorkflow": value})
    out = scrubbed(GWD, wf)[1]
    assert ("id" in out) is kept and ("settings" in out) is kept
    obj = copy.deepcopy(SEARCH_WORKFLOWS)
    obj["data"][0]["id"] = value
    assert ("id" in scrubbed(SW, obj)[1]["data"][0]) is kept


@pytest.mark.parametrize("value,kept", [
    (0, True), (2, True), (10_000_000, True), (-1, False), (10_000_001, False),
    (2.0, False), (True, False), ("2", False),
])
def test_r3_count_range(value, kept):
    out = scrubbed(SWE, dict(SEARCH_EXECUTIONS, count=value))[1]
    assert (out.get("count", "absent") == value) if kept else ("count" not in out)


@pytest.mark.parametrize("field,value,kept", [
    ("id", "4711", True), ("id", "wfAbC123", False),
    ("status", "success", True), ("status", SECRET, False),
    ("mode", "chat", True), ("mode", SECRET, False),
    ("workflowId", "wfAbC123", True), ("workflowId", "jane.citizen", False),
    ("startedAt", 1759287845000, True), ("startedAt", NAN, False),
])
def test_r3_search_execution_item(field, value, kept):
    obj = copy.deepcopy(SEARCH_EXECUTIONS)
    obj["data"][0][field] = value
    item = scrubbed(SWE, obj)[1]["data"][0]
    assert (item.get(field) == value) if kept else (field not in item)


def _strict_loads(text):
    def bad(c):
        raise ValueError("non-strict JSON constant " + c)
    return json.loads(text, parse_constant=bad)


def test_r3_output_is_strict_json_without_nan():
    ex = _exec_set(("startedAt",), NAN)
    ex["stoppedAt"] = INF
    ex["data"]["resultData"]["runData"]["Webhook"][0]["startTime"] = -INF
    wf = copy.deepcopy(WORKFLOW)
    wf["nodes"][0]["typeVersion"] = NAN
    for tool, obj in ((GWE, ex), (GWD, wf),
                      (SWE, dict(SEARCH_EXECUTIONS, count=NAN))):
        text = out_text(scrub.rewrite(mcp_payload(tool, obj)))
        assert "NaN" not in text and "Infinity" not in text, text
        assert isinstance(_strict_loads(text), dict)


def test_r3_non_finite_rebuild_fails_closed(monkeypatch):
    # belt and braces: json.dumps(allow_nan=False) refuses what a validator missed
    monkeypatch.setattr(scrub, "scrub_execution", lambda *_a: {"x": NAN})
    assert out_text(scrub.rewrite(mcp_payload(GWE, EXECUTION))) == UNDIAGNOSED


def test_r3_subprocess_output_is_strict_json():
    r = run_raw(json.dumps(mcp_payload(GWE, _exec_set(("startedAt",), NAN))))
    assert r.returncode == 0 and "NaN" not in r.stdout
    env = _strict_loads(r.stdout)
    _strict_loads(env["hookSpecificOutput"]["updatedMCPToolOutput"][0]["text"])


# Labels (Fable P3-1): reviewer strings
R3_BAD_LABELS = ["0412 345 678", "4111 1111 1111 1111",
                 "hooks.example.com/webhook/abc's3cr3tP4ss",
                 "api.example.com/v1/users/jane.citizen?token:abc12345",
                 "pass: hunter2 / user: admin", "Sydney 2000 NSW +61 2 1234 5678",
                 "Jane Citizen 0412 345 678"]
R3_GOOD_LABELS = ["Update_HubSpot_Contact_v2", "HTTP Request",
                  "Wait until 2026-10-01", "Send_Notification_v1"]


@pytest.mark.parametrize("s", R3_BAD_LABELS + [
    "Token = x", "secret:abc", "PWD:x", "Password : x", "key=v", "user:admin",
    "ref 1234 5678 9", "x.co/y"])
def test_r3_label_rejects(s):
    assert not scrub.label_ok(s)


@pytest.mark.parametrize("s", R3_GOOD_LABELS + [
    "Order 1234 5678", "Keyword filter", "Token refresh", "Get user details",
    "Ver 1.2/3", "IF: status ok"])
def test_r3_label_accepts(s):
    assert scrub.label_ok(s)


def test_r3_reviewer_labels_in_one_response():
    names = R3_GOOD_LABELS + R3_BAD_LABELS
    raw, out = scrubbed(GWD, _chain_workflow(names))
    got = [n["name"] for n in out["nodes"]]
    assert got[:4] == R3_GOOD_LABELS
    assert got[4:] == ["[LABEL-%d]" % i for i in range(1, 8)]
    for frag in ("0412", "4111", "hooks.example.com", "s3cr3tP4ss", "jane.citizen",
                 "abc12345", "hunter2", "admin", "Sydney", "1234 5678", "Jane"):
        assert frag not in raw, frag


# Draft vs published graph (Astra P2): workflow.activeVersion.sameAsDraft
def _with_active_version(av):
    wf = copy.deepcopy(WORKFLOW)
    wf["versionId"] = "v-draft"
    wf["activeVersionId"] = "v-pub"
    wf["activeVersion"] = av
    return wf


@pytest.mark.parametrize("flag", [True, False])
def test_r3_same_as_draft_kept_as_bool(flag):
    av = {"sameAsDraft": flag,
          "nodes": [{"name": "Old", "parameters": {"url": "https://hooks.example.com/" + SECRET}}],
          "connections": {"Old": {"main": [[{"node": "jane@example.com"}]]}}}
    for obj in (_with_active_version(av), {"workflow": _with_active_version(av)}):
        raw, out = scrubbed(GWD, obj)
        assert out["sameAsDraft"] is flag
        assert out == dict(WORKFLOW_EXPECTED, sameAsDraft=flag)
        for s in (SECRET, "hooks.example.com", "jane@example.com", "activeVersion",
                  "v-draft", "v-pub"):
            assert s not in raw, s


@pytest.mark.parametrize("av", [
    {"sameAsDraft": "false"}, {"sameAsDraft": 0}, {"sameAsDraft": 1},
    {"sameAsDraft": None}, {"sameAsDraft": SECRET}, {}, None, "x", [True],
])
def test_r3_same_as_draft_dropped_when_not_bool(av):
    raw, out = scrubbed(GWD, _with_active_version(av))
    assert "sameAsDraft" not in out and SECRET not in raw
    assert out == WORKFLOW_EXPECTED


def test_r3_same_as_draft_absent_without_active_version():
    assert "sameAsDraft" not in scrubbed(GWD, WORKFLOW)[1]


# ---------------------------------------------------------------------------
# Fail closed
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad", [
    dict(EXECUTION, data="[{\"resultData\":\"1\"},\"jane@example.com\"]"),
    _exec_set(("data", "resultData", "runData"), [INPUT_ITEM]),
    _exec_set(("data", "resultData", "runData", "HTTP Request"), {"x": 1}),
    _exec_set(("data", "resultData", "runData", "HTTP Request"), ["jane@example.com"]),
    _exec_set(("data", "resultData"), "jane@example.com"),
    _exec_set(("data", "resultData", "lastNodeExecuted"), {"x": "jane@example.com"}),
    {"error": "Execution jane@example.com not found"},
])
def test_execution_structural_mismatch_fails_closed(bad):
    assert out_text(scrub.rewrite(mcp_payload(GWE, bad))) == UNDIAGNOSED


@pytest.mark.parametrize("mutate", [
    lambda wf: wf.pop("nodes"),
    lambda wf: wf.__setitem__("nodes", ["jane@example.com"]),
    lambda wf: wf.__setitem__("connections", ["jane@example.com"]),
    lambda wf: wf.__setitem__("connections", {"Webhook": ["x"]}),
    lambda wf: wf.__setitem__("connections", {"Webhook": {"main": ["jane@example.com"]}}),
    lambda wf: wf.__setitem__("connections", {"Webhook": {"main": [["jane@example.com"]]}}),
    lambda wf: wf["nodes"][0].__setitem__("name", 42),
])
def test_details_structural_mismatch_fails_closed(mutate):
    wf = copy.deepcopy(WORKFLOW)
    mutate(wf)
    assert out_text(scrub.rewrite(mcp_payload(GWD, wf))) == UNDIAGNOSED


@pytest.mark.parametrize("tool", [SW, SWE])
@pytest.mark.parametrize("bad", [
    {"data": "jane@example.com"}, {"data": ["jane@example.com"]},
    {"error": "No access for jane@example.com"}, {"items": []}, "x", 5,
])
def test_search_unexpected_shape_fails_closed(tool, bad):
    assert out_text(scrub.rewrite(mcp_payload(tool, bad))) == UNDIAGNOSED


@pytest.mark.parametrize("text", ["not json", "{", "", "[1, 2]", "null",
                                  "\"jane@example.com\"", "42"])
def test_unparsable_or_non_dict_text_fails_closed(text):
    assert out_text(scrub.rewrite(mcp_payload(GWE, None, as_text=text))) == UNDIAGNOSED
    assert out_text(scrub.rewrite(mcp_payload(GWD, None, as_text=text))) == UNDIAGNOSED


@pytest.mark.parametrize("resp", [None, 42, {"weird": 1},
                                  [{"type": "image", "data": "x"}],
                                  [{"type": "text"}], []])
def test_unexpected_tool_response_fails_closed(resp):
    p = mcp_payload(GWE, EXECUTION)
    p["tool_response"] = resp
    assert out_text(scrub.rewrite(p)) == UNDIAGNOSED


def test_any_bad_block_fails_whole_output():
    p = mcp_payload(GWE, EXECUTION)
    p["tool_response"].append({"type": "text", "text": "jane@example.com"})
    assert out_text(scrub.rewrite(p)) == UNDIAGNOSED


def test_string_tool_response_is_parsed():
    p = mcp_payload(GWE, EXECUTION)
    p["tool_response"] = json.dumps(EXECUTION)
    out = json.loads(out_text(scrub.rewrite(p)))
    out.pop("_triage")
    assert out == EXECUTION_EXPECTED


def test_other_n8n_tool_or_bad_payload_fails_closed():
    assert out_text(scrub.rewrite(mcp_payload(SW, WORKFLOW))) == UNDIAGNOSED
    # an n8n tool the scrubber does not rebuild (the matcher never sends one)
    assert out_text(scrub.rewrite(mcp_payload(
        "mcp__n8n-mcp__get_node_types", {"x": 1}))) == UNDIAGNOSED
    assert out_text(scrub.rewrite({"tool_response": []})) == UNDIAGNOSED
    assert out_text(scrub.rewrite([1])) == UNDIAGNOSED


def test_internal_error_fails_closed(monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("boom")
    monkeypatch.setattr(scrub, "scrub_execution", boom)
    assert out_text(scrub.rewrite(mcp_payload(GWE, EXECUTION))) == UNDIAGNOSED


def test_free_text_masking_code_is_gone():
    src = SCRUB_PATH.read_text(encoding="utf-8")
    for name in ("def mask", "_KV", "_URL", "_EMAIL", "_CARD", "_PHONE",
                 "_BEARER", "_BASIC", "_JWT", "_PREFIXED", "[SECRET]", "[VALUE]"):
        assert name not in src, name
    assert not hasattr(scrub, "mask")


def test_unscrubbed_reads_are_documented():
    src = SCRUB_PATH.read_text(encoding="utf-8")
    for tool in ("get_node_types", "search_nodes"):
        assert tool in src


# ---------------------------------------------------------------------------
# Hook envelope (subprocess, exactly as Claude Code runs it)
# ---------------------------------------------------------------------------

def _envelope(result):
    assert result.returncode == 0, result.stderr
    env = json.loads(result.stdout)
    hso = env["hookSpecificOutput"]
    assert hso["hookEventName"] == "PostToolUse"
    assert set(hso) == {"hookEventName", "updatedMCPToolOutput"}
    return out_text(hso["updatedMCPToolOutput"])


def test_subprocess_envelope_scrubbed():
    text = _envelope(run_raw(json.dumps(mcp_payload(GWE, _exec_with_leak(
        "Error: password: 's3cr3tP4ss'")))))
    assert "s3cr3tP4ss" not in text
    out = json.loads(text)
    out.pop("_triage")
    assert out == EXECUTION_EXPECTED


def test_subprocess_other_n8n_server_scrubbed():
    p = mcp_payload("mcp__N8N-clientx__get_workflow_details", WORKFLOW)
    out = json.loads(_envelope(run_raw(json.dumps(p))))
    out.pop("_triage")
    assert out == WORKFLOW_EXPECTED


def test_subprocess_search_workflows_scrubbed_on_any_n8n_server():
    p = mcp_payload("mcp__n8n-clientx__search_workflows", SEARCH_WORKFLOWS)
    text = _envelope(run_raw(json.dumps(p)))
    assert "jane@example.com" not in text and "Owner contact" not in text
    assert json.loads(text)["data"][0]["id"] == "wfAbC123"


@pytest.mark.parametrize("stdin_text", ["", "not json", "[1]", "null"])
def test_subprocess_malformed_stdin_fails_closed(stdin_text):
    assert _envelope(run_raw(stdin_text)) == UNDIAGNOSED


def test_subprocess_non_ascii_label_survives():
    obj = _exec_set(("data", "resultData", "lastNodeExecuted"), "Fehler über")
    text = _envelope(run_raw(json.dumps(mcp_payload(GWE, obj))))
    assert json.loads(text)["data"]["resultData"]["lastNodeExecuted"] == "Fehler über"


def test_subprocess_non_n8n_tool_passes_silently():
    r = run_raw(json.dumps({"tool_name": "mcp__other__get_workflow_execution",
                            "tool_response": [{"type": "text", "text": "x"}]}))
    assert r.returncode == 0 and r.stdout.strip() == ""


# ---------------------------------------------------------------------------
# Round 4 (final): error.name allowlist (client code can set error.name),
# compound credential keys and username aliases, ports and IP hosts
# ---------------------------------------------------------------------------

R4_ERROR_CLASSES = {
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
    "TimeoutError"}


def test_r4_error_classes_is_the_fixed_frozenset():
    assert isinstance(scrub.ERROR_CLASSES, frozenset)
    assert scrub.ERROR_CLASSES == R4_ERROR_CLASSES
    assert not hasattr(scrub, "_CLASS")


@pytest.mark.parametrize("path,value,kept", [
    (ERR + ("name",), "NodeApiError", True), (ERR + ("name",), "Error", True),
    (ERR + ("name",), "TypeError", True), (ERR + ("name",), "AbortError", True),
    (ERR + ("name",), "SystemShutdownExecutionCancelledError", True),
    (RUN_ERR + ("name",), "Error", True), (RUN_ERR + ("name",), "NodeApiError", True),
    (ERR + ("name",), "JaneCitizenError", False),
    (RUN_ERR + ("name",), "JaneCitizenError", False),
    (ERR + ("name",), "AcmePtyLtdError", False), (ERR + ("name",), "customerError", False),
    (ERR + ("name",), "NodeApiError ", False), (ERR + ("name",), "nodeapierror", False),
])
def test_r4_error_name_allowlist(path, value, kept):
    raw, out = scrubbed(GWE, _exec_set(path, value))
    cur = out
    for k in path[:-1]:
        cur = cur[k]
    if kept:
        assert cur[path[-1]] == value, (path, cur)
    else:
        assert path[-1] not in cur, (path, cur)
        assert value not in raw


def test_r4_client_built_error_name_never_reaches_output():
    ex = _exec_set(ERR + ("name",), "JaneCitizenError")
    ex["data"]["resultData"]["runData"]["HTTP Request"][0]["error"]["name"] = "JaneCitizenError"
    raw, out = scrubbed(GWE, ex)
    assert "Jane" not in raw and "Citizen" not in raw
    assert out["data"]["resultData"]["error"]["node"] == {"name": "HTTP Request"}


R4_BAD_LABELS = ["api_key: demoSecret", "access_token: demoSecret",
                 "username: demoAccount", "client-secret=abc",
                 "example.com:8080/privateToken", "10.0.0.1/privateToken",
                 "localhost:5678/webhook"]
R4_GOOD_LABELS = ["Keystone Sync", "User Lookup", "Split In Batches 1/2"]


@pytest.mark.parametrize("s", R4_BAD_LABELS + [
    "refresh-token: x", "AUTH_TOKEN:x", "Sync my_api_key : x", "login: admin",
    "apikey: x", "Client_Secret: x", "Username: x",
    "10.0.0.1:5678/x", "localhost/webhook", "api.example.io:443/v1"])
def test_r4_label_rejects(s):
    assert not scrub.label_ok(s)


@pytest.mark.parametrize("s", R4_GOOD_LABELS + [
    "Monkey: patch", "MONKEY: patch", "Token refresh", "Login check",
    "Ver 1.2/3", "Call localhost API", "Port 8080 check"])
def test_r4_label_accepts(s):
    assert scrub.label_ok(s)


def test_r4_reviewer_labels_in_one_response():
    names = R4_GOOD_LABELS + R4_BAD_LABELS
    raw, out = scrubbed(GWD, _chain_workflow(names))
    got = [n["name"] for n in out["nodes"]]
    assert got[:3] == R4_GOOD_LABELS
    assert got[3:] == ["[LABEL-%d]" % i for i in range(1, 8)]
    for frag in ("demoSecret", "demoAccount", "privateToken", "example.com",
                 "10.0.0.1", "localhost", "5678", "api_key", "abc"):
        assert frag not in raw, frag
