"""Extract the final result text and turn count from `claude -p --output-format json` output.

Usage: python parse_claude_json.py <raw_output> <result_out>
Writes the result text to <result_out>; prints num_turns (or ? when not parseable).
Tolerates warning lines before or after the JSON object.
"""
import json
import sys

raw = open(sys.argv[1], encoding="utf-8", errors="replace").read()
text, turns = raw, "?"
for line in raw.splitlines():
    s = line.strip()
    if s.startswith("{") and '"type":"result"' in s.replace(" ", ""):
        try:
            j = json.loads(s)
            text = j.get("result", raw)
            turns = str(j.get("num_turns", "?"))
            break
        except Exception:
            continue
else:
    # fallback: last {...} block in the output
    a, b = raw.find("{"), raw.rfind("}")
    if 0 <= a < b:
        try:
            j = json.loads(raw[a:b + 1])
            text = j.get("result", raw)
            turns = str(j.get("num_turns", "?"))
        except Exception:
            pass
open(sys.argv[2], "w", encoding="utf-8").write(text)
print(turns)
