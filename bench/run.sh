#!/usr/bin/env bash
# Benchmark one Sol review transport on the planted-bug fixture.
#
#   bash run.sh <codex|proxy> [model] [effort] [runs]
#   defaults: model=gpt-5.6-sol effort=xhigh runs=1
#
# Each run gets a fresh fixture repo under results/work-<transport>-<n>, a fresh
# scratch dir, and the same review spec. Appends one CSV line per run to
# results/results.csv and prints the score. Compare transports by running both
# with the same model/effort/runs, ideally back to back.
#
# Columns: speed (seconds, turns), reliability (exit, saved), quality
# (recall, findings, false_positives, contract, cites, confidence, noise),
# translation (upstream_effort = the reasoning effort the proxy actually sent to
# OpenAI for THIS run's requests, read from its request log; needs
# `request-log: true` in the proxy config.yaml, else "unlogged"; n/a for codex).
set -u
TRANSPORT="${1:?codex|proxy}"; MODEL="${2:-gpt-5.6-sol}"; EFFORT="${3:-xhigh}"; RUNS="${4:-1}"
BENCH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS="$BENCH/results"; mkdir -p "$RESULTS"
COMPANION="$HOME/.claude/plugins/cache/openai-codex/codex/1.0.3/scripts/codex-companion.mjs"
PROXY_URL="http://127.0.0.1:8317"
PROXY_LOGS="$HOME/.cli-proxy-api/logs"
SPEC_MARK="util.py provides slugify"      # text unique to this benchmark's requests
CSV="$RESULTS/results.csv"
HEADER="timestamp,transport,model,effort,run,seconds,turns,exit,saved,recall,findings,false_positives,contract,cites,confidence,noise,upstream_effort"
if [ ! -f "$CSV" ] || [ "$(head -1 "$CSV")" != "$HEADER" ]; then
  [ -f "$CSV" ] && mv "$CSV" "$CSV.old-$(date +%H%M%S)"
  echo "$HEADER" > "$CSV"
fi

proxy_key() {
  "$(dirname "$0")/../bin/proxy-key"
}
field() { echo "$1" | sed -nE "s/.*$2=([^ ]+).*/\1/p"; }

for n in $(seq 1 "$RUNS"); do
  WORK="$RESULTS/work-$TRANSPORT${SPEC_TAG:-}-$n"; rm -rf "$WORK"
  python "$BENCH/fixture.py" "$WORK" >/dev/null 2>&1
  SCRATCH="$WORK/.scratch"; mkdir -p "$SCRATCH"
  SCRATCH_WIN="$(cygpath -w "$SCRATCH")"
  SPEC="$WORK/.spec.md"
  SPEC_SRC="$BENCH/${SPEC_FILE:-review-spec.md}"   # SPEC_FILE=review-spec-v2.md for the front-loaded variant
  python - "$SPEC_SRC" "$SPEC" "$SCRATCH_WIN" "$WORK" <<'PY'
import sys,subprocess
src,dst,scratch,work=sys.argv[1:5]
t=open(src,encoding='utf-8').read().replace('__SCRATCH__',scratch)
if '__DIFF__' in t:
    diff=subprocess.run(['git','show','--format=','HEAD','--','util.py'],cwd=work,capture_output=True,text=True).stdout
    t=t.replace('__DIFF__',diff.strip())
open(dst,'w',encoding='utf-8',newline='\n').write(t)
PY
  OUT="$WORK/.out.txt"; RESULT="$WORK/.result.md"
  TURNS="?"; UP_EFFORT="n/a"
  echo "[$TRANSPORT #$n] $MODEL @ $EFFORT ..."
  START=$(date +%s); MARK="$WORK/.start"; touch "$MARK"
  case "$TRANSPORT" in
    codex)
      (cd "$WORK" && timeout 1500 node "$COMPANION" task --wait --model "$MODEL" --effort "$EFFORT" "$(cat "$SPEC")" > "$OUT" 2>&1)
      EXIT=$?
      grep -v -E "^\[codex\]|DEP0190|trace-deprecation" "$OUT" > "$RESULT"
      TURNS=$(grep -c "^\[codex\] Turn started" "$OUT") ;;
    proxy)
      KEY="$(proxy_key)"
      (cd "$WORK" && ANTHROPIC_BASE_URL="$PROXY_URL" ANTHROPIC_AUTH_TOKEN="$KEY" \
        timeout 1500 claude -p "$(cat "$SPEC")" --model "$MODEL" --effort "$EFFORT" \
        --bare --max-turns 30 --permission-mode default --allowedTools "Read,Grep,Glob,Bash" \
        --output-format json < /dev/null > "$OUT" 2>&1)
      EXIT=$?
      TURNS=$(python "$BENCH/parse_claude_json.py" "$OUT" "$RESULT")
      if [ -d "$PROXY_LOGS" ]; then
        UP_EFFORT=$(grep -l "$SPEC_MARK" $(find "$PROXY_LOGS" -name 'v1-messages-*.log' -newer "$MARK" 2>/dev/null) /dev/null 2>/dev/null \
          | xargs -r grep -ohE '"reasoning":\{"effort":"[a-z]+"' 2>/dev/null \
          | sed -E 's/.*"effort":"([a-z]+)"/\1/' | sort | uniq -c | sort -rn | awk '{printf "%s(x%s) ", $2, $1}')
        [ -n "$UP_EFFORT" ] || UP_EFFORT="unlogged"
      fi ;;
    *) echo "unknown transport: $TRANSPORT" >&2; exit 2 ;;
  esac
  SECS=$(( $(date +%s) - START ))
  [ "$EXIT" -eq 0 ] || cp "$OUT" "$RESULTS/fail-$TRANSPORT-$(date +%H%M%S).txt"   # keep failed outputs; work dirs are recycled
  FINDINGS="$SCRATCH/findings.md"
  SCORE="$(python "$BENCH/score.py" "$FINDINGS" "$RESULT" "$WORK")"
  L1="$(echo "$SCORE" | head -1)"
  echo "$(date -Iseconds),$TRANSPORT,$MODEL,$EFFORT,$n,$SECS,$TURNS,$EXIT,$(field "$L1" saved),$(field "$L1" recall),$(field "$L1" findings),$(field "$L1" false_positives),$(field "$L1" contract),$(field "$L1" cites),$(field "$L1" confidence),$(field "$L1" noise),$(echo "$UP_EFFORT" | sed 's/ *$//;s/,/;/g')" >> "$CSV"
  echo "  ${SECS}s turns=$TURNS exit=$EXIT upstream_effort=${UP_EFFORT}"
  echo "  $L1"
  echo "$SCORE" | tail -5 | sed 's/^/  /'
  echo "  output: $OUT"
done
echo "CSV: $CSV"
