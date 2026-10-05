"""Route crawl for a speed pass: fetch every route, record status and error markers.

usage:
  crawl.py <routes-file> <out.json> --base http://localhost:3000 [--subs subs.json]
           [--header "Name: value"]... [--target <tabId>]

routes-file : one path per line, dynamic segments in brackets, e.g. /c/[clientSlug]/data
--subs      : JSON object mapping each bracketed segment to a real value,
              e.g. {"[clientSlug]": "acme", "[weekOf]": "2026-06-08"}
--header    : repeatable. Sent with every direct request, e.g. "Cookie: session=..." or
              "Authorization: Bearer ..." for an app behind a login. The user supplies the value.
--target    : optional browser mode. Full tab id of a SIGNED-IN tab from a browser-automation helper
              exposing switch_tab() and js() (browser-harness). Routes are fetched from inside that tab.
              Without --target, routes are fetched directly.

Statuses: 200 rendered, 404 denied/unknown, 0 opaque redirect (redirect: manual), EXC network failure.
Run once on the branch and once on the base (restart the dev server after each checkout), then diff
the two JSON files by status.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

ERRPAT = r"Application error|Internal Server Error|Something went wrong|Unhandled Runtime Error"


def load_urls(routes_file, subs):
    urls = []
    for line in open(routes_file, encoding="utf-8"):
        r = line.strip()
        if not r:
            continue
        for k, v in subs.items():
            r = r.replace(k, v)
        urls.append(r)
    return urls


def crawl_in_tab(urls, target):
    js_src = (
        "(async()=>{const out={};for(const p of " + json.dumps(urls) + "){"
        "try{const r=await fetch(p,{cache:'no-store',redirect:'manual'});"
        "const t=await r.text();const m=t.match(/" + ERRPAT + "/i);"
        "out[p]={s:r.status,len:t.length,err:m?m[0]:null};}"
        "catch(e){out[p]={s:'EXC',len:0,err:String(e).slice(0,80)};}}"
        "return JSON.stringify(out);})()"
    )
    code = "switch_tab(%r)\nprint(js(%r))" % (target, js_src)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run(["browser-harness", "-c", code], capture_output=True, text=True, env=env, timeout=1800)
    lines = [l for l in r.stdout.splitlines() if l.startswith("{")]
    if not lines:
        sys.exit("CRAWL FAILED (is the tab id current and signed in?): " + (r.stderr or r.stdout)[-400:])
    return json.loads(lines[-1])


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def crawl_direct(urls, base, headers):
    opener = urllib.request.build_opener(_NoRedirect)
    opener.addheaders = list(headers.items())
    out = {}
    for p in urls:
        try:
            with opener.open(base.rstrip("/") + p, timeout=60) as resp:
                body = resp.read().decode("utf-8", "replace")
                m = re.search(ERRPAT, body, re.I)
                out[p] = {"s": resp.status, "len": len(body), "err": m.group(0) if m else None}
        except urllib.error.HTTPError as e:
            out[p] = {"s": 0 if 300 <= e.code < 400 else e.code, "len": 0, "err": None}
        except Exception as e:  # network failure: the server is probably down
            out[p] = {"s": "EXC", "len": 0, "err": str(e)[:80]}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("routes_file")
    ap.add_argument("out")
    ap.add_argument("--base", default="http://localhost:3000")
    ap.add_argument("--subs")
    ap.add_argument("--header", action="append", default=[])
    ap.add_argument("--target")
    a = ap.parse_args()

    subs = json.load(open(a.subs, encoding="utf-8")) if a.subs else {}
    urls = load_urls(a.routes_file, subs)
    unresolved = [u for u in urls if "[" in u]
    if unresolved:
        sys.exit("unsubstituted dynamic segments: " + ", ".join(unresolved[:5]))

    headers = {}
    for h in a.header:
        if ":" not in h:
            sys.exit("bad --header (want 'Name: value'): " + h)
        k, v = h.split(":", 1)
        headers[k.strip()] = v.strip()

    data = crawl_in_tab(urls, a.target) if a.target else crawl_direct(urls, a.base, headers)
    json.dump(data, open(a.out, "w", encoding="utf-8"))

    bad = {k: v for k, v in data.items() if v.get("err") or v.get("s") in (500, "EXC")}
    hist = {}
    for v in data.values():
        hist[str(v["s"])] = hist.get(str(v["s"]), 0) + 1
    print("routes=%d statuses=%s errors=%d" % (len(data), hist, len(bad)))
    for k, v in bad.items():
        print("  ERR", k, v)
    if any(v.get("s") == "EXC" for v in data.values()):
        print("  NOTE: EXC means the request never reached the server - restart the dev server and re-run.")


if __name__ == "__main__":
    main()
