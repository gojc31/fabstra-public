#!/usr/bin/env bash
# Orchestration eval: run ONE fabstra arm once on a fresh ledger fixture, then score it.
#
#   bash run.sh <A|B1|B2|AF|B2A|B0|B1L> <N> [--dry]
#
# A  = Fable 5.1, Orchestrate mode, Astra reviews (skill's pairing rule)
# B1 = Opus 5.5, Lead mode, fresh-Fable reviewer (model-router:reviewer)
# B2 = Opus 5.5 forced into Orchestrate mode, fresh-Fable reviewer
# AF = Fable 5.1, Orchestrate mode, review seat overridden to a fresh Fable (not Astra/Sol)
# B2A = Opus 5.5 forced into Orchestrate mode, review seat follows the skill's pairing rule (Astra)
# B0 = Opus 5.5, no-skill baseline: model-router plugin disabled for the run, no fabstra lines, no Astra probe
# B1L = B1 with fabstra loaded from variants/model-router-lean (--plugin-dir) and the installed plugin disabled
# Plugin switch (B0, B1L) is per run only: --settings .scratch/settings.json sets
# enabledPlugins."model-router@robonuggets"=false; user config is never touched.
# Work dir: results/work-<ARM>-<N> (recreated). --dry builds the fixture and the
# prompt, prints the command, and exits 0 without calling claude or the proxy.
# Exit 3 = Astra cooling (no run), 4 = proxy unreachable (no run).
set -u
ARM="${1:?usage: bash run.sh <A|B1|B2|AF|B2A|B0|B1L> <N> [--dry]}"
N="${2:?usage: bash run.sh <A|B1|B2|AF|B2A|B0|B1L> <N> [--dry]}"
DRY=0; [ "${3:-}" = "--dry" ] && DRY=1

BENCH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS="$BENCH/results"; mkdir -p "$RESULTS"
WORK="$RESULTS/work-$ARM-$N"
SCRATCH="$WORK/.scratch"
PROMPT="$SCRATCH/prompt.md"
VARIANT="$BENCH/variants/model-router-lean"
VARIANT_W="$(cygpath -m "$VARIANT" 2>/dev/null || echo "$VARIANT")"
# Extra claude flags (B0, B1L only; empty keeps the other arms' command unchanged).
EXTRA=""
# The preamble's file-access line; B1L swaps it for the variant path.
READ_LINE='- You may read the fabstra skill files (the plugin cache under ~/.claude/plugins/cache/robonuggets/model-router/ and $MODEL_ROUTER_HOME/skills/fabstra/) and the proxy config key; otherwise do not read or modify anything outside this repository and its .scratch directory. Never push. Commits are fine.'

case "$ARM" in
  A)  MODEL="claude-fable-5-1"
      ARM_TEXT='Run /model-router:fabstra in Orchestrate mode as the skill says for Fable 5.1. The review seat follows the skill'"'"'s pairing rule (Astra).' ;;
  B1) MODEL="claude-opus-5-5"
      ARM_TEXT='MODE OVERRIDE for this run: run /model-router:fabstra in LEAD mode (lead-mode.md) even though the plan is above the Orchestrate threshold - you build BUILDER tasks yourself or delegate by tier as lead-mode.md says. REVIEW SEAT OVERRIDE: the review and every re-review are done by a fresh Fable (Agent tool, subagent_type "model-router:reviewer"), not by Astra or Sol; Astra still gates the plan.' ;;
  B2) MODEL="claude-opus-5-5"
      ARM_TEXT='MODE OVERRIDE for this run: run /model-router:fabstra in ORCHESTRATE mode (phases.md, specs.md) exactly as Fable 5.1 would, even though you are Opus 5.5: never write or edit code or tests in-session - every task, fix, and probe file is built by a subagent by tier; you write specs, verdicts, the logbook and the report only. REVIEW SEAT OVERRIDE: the review and every re-review are done by a fresh Fable (Agent tool, subagent_type "model-router:reviewer"), not by Astra or Sol; Astra still gates the plan.' ;;
  AF) MODEL="claude-fable-5-1"
      ARM_TEXT='Run /model-router:fabstra in Orchestrate mode as the skill says for Fable 5.1. REVIEW SEAT OVERRIDE for this run: the review and every re-review are done by a fresh Fable (Agent tool, subagent_type "model-router:reviewer"), not by Astra or Sol; Astra still gates the plan.' ;;
  B2A) MODEL="claude-opus-5-5"
      ARM_TEXT='MODE OVERRIDE for this run: run /model-router:fabstra in ORCHESTRATE mode (phases.md, specs.md) exactly as Fable 5.1 would, even though you are Opus 5.5: never write or edit code or tests in-session - every task, fix, and probe file is built by a subagent by tier; you write specs, verdicts, the logbook and the report only. The review seat follows the skill'"'"'s pairing rule with Astra pinned (Astra reviews).' ;;
  B0) MODEL="claude-opus-5-5"
      ARM_TEXT=''
      EXTRA=" --settings .scratch/settings.json" ;;
  B1L) MODEL="claude-opus-5-5"
      ARM_TEXT='MODE OVERRIDE for this run: run /model-router:fabstra in LEAD mode (lead-mode.md) even though the plan is above the Orchestrate threshold - you build BUILDER tasks yourself or delegate by tier as lead-mode.md says. REVIEW SEAT OVERRIDE: the review and every re-review are done by a fresh Fable (Agent tool, subagent_type "model-router:reviewer"), not by Astra or Sol; Astra still gates the plan.'
      EXTRA=" --settings .scratch/settings.json --plugin-dir $VARIANT_W"
      READ_LINE='- You may read the fabstra skill files ONLY from the lean variant plugin at '"$(printf '%s' "$VARIANT_W" | tr / '\\')"'\ (fabstra reference files are read from its skills\fabstra\references\, never from $MODEL_ROUTER_HOME/skills/fabstra/ nor the plugin cache) and the proxy config key; otherwise do not read or modify anything outside this repository and its .scratch directory. Never push. Commits are fine.' ;;
  *)  echo "unknown ARM '$ARM' (case-sensitive: A, B1, B2, AF, B2A, B0, B1L)" >&2; exit 2 ;;
esac
# Fallback if the first real run shows the slash command was taken literally (no
# .fabstra/RUN.md), uncomment the line below to prefix an explicit Skill-tool
# instruction. The orchestrator decides; not applied by default.
# ARM_TEXT="Invoke the model-router:fabstra skill with the Skill tool, then follow it as below. $ARM_TEXT"

rm -rf "$WORK"
python "$BENCH/fixture.py" "$WORK" >/dev/null || { echo "fixture.py failed" >&2; exit 1; }
mkdir -p "$SCRATCH"
if [ -n "$EXTRA" ]; then
  # Per-run plugin switch: the installed model-router plugin is off for this run only.
  echo '{"enabledPlugins":{"model-router@robonuggets":false}}' > "$SCRATCH/settings.json"
fi

if [ "$DRY" -eq 0 ] && [ "$ARM" != "B0" ]; then
  KEY=$(python -c "import re;t=open(r'${CLIPROXY_DIR:-~/cli-proxy-api}/config.yaml').read();print(re.search(r'api-keys:\s*\n\s*-\s*\"?([^\"\n]+)\"?',t).group(1).strip())")
  STATUS=$(curl -s -m 60 -o "$SCRATCH/astra-probe.json" -w '%{http_code}' http://127.0.0.1:8317/v1/messages \
    -H "x-api-key: $KEY" -H "anthropic-version: 2023-06-01" -H "content-type: application/json" \
    -d '{"model":"gpt-6-astra","max_tokens":8,"messages":[{"role":"user","content":"ping"}]}')
  if [ "$STATUS" = "429" ] || grep -qi "cooling" "$SCRATCH/astra-probe.json" 2>/dev/null; then
    echo "ASTRA_COOLING"; exit 3
  fi
  if [ "$STATUS" = "000" ]; then
    echo "PROXY_UNREACHABLE (127.0.0.1:8317)"; exit 4
  fi
fi

if [ "$ARM" = "B0" ]; then
cat > "$PROMPT" <<'EOF'
You are running HEADLESS with no user available. Rules for this run:
- Run condition: the model-router plugin and its fabstra skill are not installed for this run. The CLAUDE.md instructions that route hard tasks through /model-router:fabstra (the "Fable Method" section and any line that mandates fabstra) do not apply to this run; do not try to invoke it. Work the task directly however you judge best, including your own subagents if you want them. The rest of CLAUDE.md still applies.
- Never ask the user anything. Where you would ask, take the sensible default, log it in .fabstra/RUN.md as "default taken: ...", and continue.
- Never end your turn while any job or subagent is still running.
- When you are done, ALSO write .fabstra/METRICS.json with exactly this shape and then stop ("mode" is "none"; plan_gate seat is "none"; review seats is [] unless you chose to run a review, then name the reviewer models):
  {"mode":"none","lead_model":"<id>","plan_gate":{"seat":"none","effort":"<x>","findings":N,"p1":N,"accepted":N,"rejected":N,"seconds":N},"review":{"seats":[],"findings":N,"p1":N,"accepted":N,"rejected":N,"rounds":N},"fix_rounds":N,"tasks":N,"builders":["<model or agent>",...],"in_session_code_edits":N,"defaults_taken":N,"unfinished":true|false}
- Do not read or modify anything outside this repository and its .scratch directory. Never push. Commits are fine.

Task: implement everything in brief.md in this repository. Read brief.md first. Done means the visible tests and every behaviour in brief.md hold. Start now.
EOF
else
{
cat <<'EOF'
You are running HEADLESS with no user available. Rules for this run:
- Every gate call (the proxy `claude -p` for Astra/Sol, any Codex job) is a FOREGROUND Bash call with `timeout 1500`; never a background call. Never end your turn while any job or subagent is still running.
- Never ask the user anything. Where the skill says to ask, take the sensible default, log it in .fabstra/RUN.md as "default taken: ...", and continue.
- This is a REAL BUILD (four tasks). Run the plan gate and the review gate; never skip either.
- Plan gate seat: Astra (`--model gpt-6-astra --effort high`). If Astra is cooling, use Sol (`--model gpt-6-sol --effort high`) and log it.
- Builders: delegate by tier exactly as the skill says (model-router:builder / builder-medium for Opus-tier, model "sonnet" / "haiku" otherwise).
- Fix rounds: at most two per finding, as the skill says; then stop and log.
- Ownership override for this run: every task is BUILDER-owned (Claude side, Agent tool). Skip the Codex write probe and log "default taken: probe skipped, eval pins Claude builders".
- Skip the /goal hand-off (headless; this prompt is the goal). Skip the run-recipe step of the smoke gate (no recipe in this repo); run the test suite.
- Gate seat for this run is Astra (pinned above) regardless of the gate seat rubric row.
- When the report is written (Gate 5 / Phase 5), ALSO write .fabstra/METRICS.json with exactly this shape and then stop:
  {"mode":"orchestrate|lead","lead_model":"<id>","plan_gate":{"seat":"astra|sol|fable|none","effort":"<x>","findings":N,"p1":N,"accepted":N,"rejected":N,"seconds":N},"review":{"seats":["astra"|"sol"|"fable",...],"findings":N,"p1":N,"accepted":N,"rejected":N,"rounds":N},"fix_rounds":N,"tasks":N,"builders":["model-router:builder","sonnet",...],"in_session_code_edits":N,"defaults_taken":N,"unfinished":true|false}
EOF
printf '%s\n' "$READ_LINE"
echo
echo "$ARM_TEXT"
echo
cat <<'EOF'
Task: implement everything in brief.md in this repository. Read brief.md first. Done means the visible tests and every behaviour in brief.md hold. Start now.
EOF
} > "$PROMPT"
fi

CMD="timeout 7200 claude -p --model $MODEL$EXTRA --permission-mode bypassPermissions --output-format json --max-turns 400 < .scratch/prompt.md > claude.out.json 2> claude.err.txt"

if [ "$DRY" -eq 1 ]; then
  echo "cwd:     $WORK"
  echo "command: $CMD"
  echo "prompt:  $PROMPT"
  exit 0
fi

# The fixture's CLAUDE.md says `python -m pytest -q`; make sure `python` in the
# run resolves to an interpreter that has pytest (an active venv may not).
PYDIR=""
for cand in "python" "py -3.12"; do
  if $cand -c "import pytest" >/dev/null 2>&1; then
    PYDIR=$($cand -c "import os,sys;print(os.path.dirname(sys.executable))"); break
  fi
done
if [ -n "$PYDIR" ]; then
  PYDIR_U="$(cygpath -u "$PYDIR" 2>/dev/null || echo "$PYDIR")"
  export PATH="$PYDIR_U:$PYDIR_U/Scripts:$PATH"; unset VIRTUAL_ENV
fi

echo "[$ARM #$N] $MODEL in $WORK ..."
cd "$WORK" || exit 1
date +%s > timing.txt
timeout 7200 claude -p --model "$MODEL" $EXTRA --permission-mode bypassPermissions --output-format json --max-turns 400 < .scratch/prompt.md > claude.out.json 2> claude.err.txt
RC=$?
date +%s >> timing.txt
echo "$RC" >> timing.txt
python "$BENCH/score.py" "$WORK" "$ARM" "$N"
