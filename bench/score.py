"""Score a review output against the five planted bugs, plus output quality.

Usage: python score.py <findings_file> [fallback_output] [fixture_dir]
saved reflects <findings_file>; when it is missing, the fallback output is scored instead.

Prints one summary line, then per-bug found/MISSED lines:
  recall=<found>/5 findings=<n> false_positives=<n> saved=<yes|no>
  contract=<ok|partial|broken> cites=<valid>/<total> confidence=<n>/<findings> noise=<pct>

Quality metrics (the "did the message survive the transport" checks):
  contract    ok = both required sections present, each function has PASS/FAIL, no trailing
              chatter after the findings; partial = sections present but something missing;
              broken = no recognisable structure.
  cites       util.py:N or util.py:N-M citations whose line range overlaps a real function body
              (checked against the fixture file when fixture_dir is given).
  confidence  findings that carry a 0-100 confidence number (inline or in the item's sub-bullets).
  noise       share of non-empty lines that belong to neither section (preamble, apologies,
              tool chatter, translation artefacts such as raw JSON or role tags).

Findings are recognised in either layout: one line per finding carrying an inline P1/P2/P3
tag, or numbered items grouped under a "P1"/"P2"/"P3" heading.
"""
import os
import re
import sys

PLANTED = {
    "slugify edge hyphens": [r"slugify", r"(leading|trailing|edge).{0,40}hyphen|hyphen.{0,40}(leading|trailing|edge)|strip"],
    "paginate 0-indexed": [r"paginate", r"0-index|zero-index|zero-based|page \* per_page|page - 1|1-index|one-based"],
    "parse_price comma": [r"parse_price", r"comma|thousand|1,234|ValueError"],
    "dedupe order": [r"dedupe", r"order|set\(\)|set\b"],
    "retry swallows": [r"retry", r"None|swallow|re-?raise|raise"],
}
FUNCS = ["slugify", "paginate", "parse_price", "dedupe", "retry"]
SEV_HEAD = re.compile(r"^\s*(#{1,6}\s*|\*\*)?\s*P[123]\b[^\n]{0,40}$")
INLINE_TAG = re.compile(r"\bP[123]\b")
NUMBERED = re.compile(r"^\s*\d+[.)]\s+\S")


def func_ranges(fixture_dir):
    """Map function name -> (first_line, last_line) in util.py, 1-indexed."""
    path = os.path.join(fixture_dir, "util.py")
    if not os.path.isfile(path):
        return {}
    lines = open(path, encoding="utf-8").read().splitlines()
    starts = [(i + 1, m.group(1)) for i, ln in enumerate(lines) if (m := re.match(r"def (\w+)\(", ln))]
    ranges = {}
    for idx, (start, name) in enumerate(starts):
        end = starts[idx + 1][0] - 1 if idx + 1 < len(starts) else len(lines)
        while end > start and not lines[end - 1].strip():
            end -= 1
        ranges[name] = (start, end)
    return ranges


def collect_findings(lines):
    """Return a list of (finding_line_index, block_text) for every finding, either layout."""
    findings = []
    in_sev = False
    for i, ln in enumerate(lines):
        if SEV_HEAD.match(ln) and not NUMBERED.match(ln):
            in_sev = True
            continue
        # "(3) nothing else" ends the findings section; a bare "3." is finding #3
        if re.match(r"^\s*#{1,6}\s", ln) or re.match(r"^\s*\(3\)", ln):
            in_sev = False
        inline = INLINE_TAG.search(ln) and (re.search(r"util\.py", ln) or "—" in ln or " - " in ln)
        grouped = in_sev and NUMBERED.match(ln)
        if inline or grouped:
            # block = this line plus following indented sub-bullets
            j = i + 1
            while j < len(lines) and (lines[j].startswith("   ") or lines[j].startswith("\t") or lines[j].strip() == ""):
                if lines[j].strip() == "" and j + 1 < len(lines) and not (lines[j + 1].startswith("   ") or lines[j + 1].startswith("\t")):
                    break
                j += 1
            findings.append((i, "\n".join(lines[i:j])))
    return findings


def main(path, fallback=None, fixture_dir=None):
    saved = os.path.isfile(path)
    src = path if saved else fallback
    text = open(src, encoding="utf-8", errors="replace").read() if src and os.path.isfile(src) else ""
    lines = text.splitlines()

    found = [name for name, pats in PLANTED.items() if all(re.search(p, text, re.I | re.S) for p in pats)]
    findings = collect_findings(lines)
    blocks = [b for _, b in findings]
    # match the whole finding block: reviewers name the function in prose
    # ("exhausted retries", "the documented price example"), not just by identifier
    fp = sum(1 for b in blocks if not any(re.search(p[0], b, re.I) for p in PLANTED.values()))

    # contract
    per_func = sum(1 for f in FUNCS if re.search(rf"\b{f}\b.{{0,80}}\b(PASS|FAIL)\b", text, re.S))
    has_sec1 = per_func >= 3
    has_sec2 = bool(findings) or bool(re.search(r"no findings|nothing wrong|finding nothing", text, re.I))
    nonempty = [ln for ln in lines if ln.strip()]
    tail_chatter = 0
    if findings:
        last_idx = findings[-1][0]
        # lines after the last finding block that are not sub-bullets, section markers, or "(3) nothing"
        k = last_idx + 1
        while k < len(lines) and (lines[k].startswith("   ") or lines[k].startswith("\t") or not lines[k].strip()):
            k += 1
        for ln in lines[k:]:
            if ln.strip() and not re.match(r"^\s*(\(?3\)?[.)]?|#+|-|\*|\d+[.)])\s", ln) and not re.search(r"saved|findings\.md", ln, re.I):
                tail_chatter += 1
    if has_sec1 and has_sec2 and per_func >= 5 and tail_chatter == 0:
        contract = "ok"
    elif has_sec1 or has_sec2:
        contract = "partial"
    else:
        contract = "broken"

    # citations
    cites = re.findall(r"util\.py:(\d+)(?:-(\d+))?", text)
    ranges = func_ranges(fixture_dir) if fixture_dir else {}
    valid = 0
    if ranges:
        for a, b in cites:
            lo, hi = int(a), int(b or a)
            if any(lo <= r_hi and hi >= r_lo for (r_lo, r_hi) in ranges.values()):
                valid += 1
    cites_str = f"{valid}/{len(cites)}" if ranges else f"?/{len(cites)}"

    conf = sum(1 for b in blocks if re.search(r"confidence[:*\s]*\d{1,3}", b, re.I))

    # noise: non-empty lines that are neither structure nor finding content
    finding_lines = set()
    for i, b in findings:
        for k in range(i, i + b.count("\n") + 1):
            finding_lines.add(k)
    struct = 0
    for i, ln in enumerate(lines):
        if not ln.strip():
            continue
        if i in finding_lines or re.search(r"\b(PASS|FAIL)\b", ln) or re.match(r"^\s*(\(?[123]\)?[.)]?|#+|-|\*|\d+[.)])\s", ln) or SEV_HEAD.match(ln):
            struct += 1
    noise = 0 if not nonempty else round(100 * (len(nonempty) - struct) / len(nonempty))

    print(f"recall={len(found)}/5 findings={len(findings)} false_positives={fp} saved={'yes' if saved else 'no'} "
          f"contract={contract} cites={cites_str} confidence={conf}/{len(findings)} noise={noise}%")
    for name in PLANTED:
        print(("  found   " if name in found else "  MISSED  ") + name)


if __name__ == "__main__":
    args = sys.argv[1:] + [None, None]
    main(args[0], args[1], args[2])
