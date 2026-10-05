---
name: triage
description: "User-invoked, read-only n8n production-error triage: reads failed executions, groups and diagnoses them, writes .fabstra/TRIAGE-{stamp}.md with severity and a fix plan, then stops. Locks every n8n MCP server to reads and validated structure (no error text, parameters or URLs) for the session."
disable-model-invocation: true
hooks:
  PreToolUse:
    - matcher: "^mcp__[nN]8[nN]"
      hooks:
        - type: command
          command: python
          args:
            - '{{SKILLS_DIR}}\triage\guard.py'
  PostToolUse:
    - matcher: "^mcp__[nN]8[nN][^_]*(_[^_]+)*__(search_workflow_executions|get_workflow_execution|search_workflows|get_workflow_details)$"
      hooks:
        - type: command
          command: python
          args:
            - '{{SKILLS_DIR}}\triage\scrub.py'
---

# triage

The user types `/triage [workflow] [window]`; it never fires on its own.

**The n8n lock lasts until the session ends.** It hooks every MCP server whose name starts with n8n, any case. `guard.py` (PreToolUse) allows six reads (the four below, `get_node_types`, `search_nodes`) and denies every other n8n tool (community `n8n_*` included). Plugin-bundled n8n servers (`mcp__plugin_*`) are outside the lock; disable them before running /triage. `includeData: true` also needs `nodeNames` (1-3) and `truncateData` 1 or 2. `scrub.py` (PostToolUse) rebuilds those four's responses from validated structure (ids, status, times, counts, flags, names, types, connections, error class, HTTP code), dropping any failing field. Error text, parameters and URLs never reach Claude by design. Residual: node and workflow names are developer-written labels; they pass raw when label-shaped, else as `[LABEL-n]`. "Could not parse" on a search: say so and stop. No off switch; the fix runs in a fresh session. A seatbelt, not a sandbox: both hooks see MCP calls only, so never call the n8n API from a shell. A denied call is out of scope: note it in the fix plan, never route around it.

1. **Inputs.** Optional workflow id or name (resolve with `search_workflows`); optional window, default 24h (`7d`, `48h`). Compute `startedAfter` as an ISO timestamp.
2. **List.** `search_workflow_executions` with `status: ["error","crashed"]`, `startedAfter`, `limit: 200` (+ `workflowId` if given). Page with the parameter the schema exposes, max 3 pages. `cursor` = previous `nextCursor`; stop at no next cursor. `lastId` = last execution id; stop at a page with fewer than `limit` items or no new ids, or the 600 cap. Per-workflow counts and first/last seen (`startedAt`) come from the list. `nextCursor: null` or a short page: counts are exact. Else (capped, no new ids, cursor missing, `count` above what you fetched) say coverage is partial: counts are "at least N fetched", first seen "earliest fetched", sampling "N of M fetched failures; window total unknown". Zero failures: say so and stop.
3. **Find the failing node.** Per workflow (most failures first, max 5), sample up to 5 executions, newest first. `get_workflow_details` once per workflow, pick up to 3 candidate nodes (last in chain, with error outputs, HTTP/API/code), then `get_workflow_execution` with `includeData: true`, `nodeNames: <those>`, `truncateData: 1`. Read `lastNodeExecuted`, `error` (`node.name`, `name`, `httpCode`) and `runData[<node>][].error`. A `[LABEL-n]` node cannot be requested: UNDIAGNOSED. "Could not parse", or no node/error: that execution is UNDIAGNOSED (note what was tried).
4. **Group** by signature = workflow + node + error class + HTTP code. Counts are sample counts: "sampled N of M failures in this workflow" (capped: as in step 2); list the unsampled rest as unclassified; never extrapolate. Rank by workflow failure count, sample share, then recency.
5. **Diagnose the top 3** from structure: node type (`get_node_types` for what it expects), error class, HTTP code, the node's position in `connections`. `sameAsDraft` false or absent: say the graph may differ from what ran; node-type / connection causes are ASSUMED. Causes are usually **ASSUMED** (say what would confirm it); **VERIFIED** only when structure alone proves it (cite execution id, node, field). Every group gets a `confirm in n8n: open execution <id>` line.
6. **Write** `.fabstra/TRIAGE-<YYYY-MM-DD-HHMM>.md` in the cwd (create `.fabstra/` if missing). In a git repo, first run `git check-ignore -q .fabstra/`; not ignored: write to the session scratchpad and tell the user (never edit `.gitignore`). Per group: signature, count, first/last seen, up to 3 execution ids, severity (P1 = data loss, missed customer-facing action or full outage; P2 = degraded, retried or partial; P3 = noise or self-healing), cause VERIFIED/ASSUMED, the confirm line, the proposed fix (node + field + change), how to validate it. Then UNDIAGNOSED executions and nodes, then the unclassified rest. The file and chat contain no message text.
7. **Stop.** Print a short summary (groups, counts, severities, file path) and the hand-off line (scratchpad path if the file went there): `/model-router:fabstra fix triage group <N> from .fabstra/TRIAGE-<stamp>.md`

**Never:** fixes, subagents, executions, deploys, or anything sent outside the machine. To share the file or draft a client message from it, run your own redaction gate first if you have one.
