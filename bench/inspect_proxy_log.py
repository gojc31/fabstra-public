"""Summarise one CLIProxyAPI request log: what the proxy forwarded upstream.

Usage: python inspect_proxy_log.py <log_file>
Reports developer-prompt size, tool schemas forwarded, reasoning effort, and token usage.
Requires `request-log: true` in the proxy's config.yaml (turn it off afterwards; the
logs hold full prompts and can reach megabytes per request).

Log layout (v7.2.x): === REQUEST BODY === (Anthropic-format inbound), === API REQUEST n ===
(OpenAI Responses-format upstream), === API RESPONSE n ===, === RESPONSE === (translated back).
"""
import re
import sys


def section(t, name):
    i = t.find(f"=== {name} ===")
    if i < 0:
        return ""
    j = t.find("\n=== ", i + 5)
    return t[i:j if j > 0 else len(t)]


def main(path):
    t = open(path, encoding="utf-8", errors="replace").read()
    inbound = section(t, "REQUEST BODY")
    upstream = section(t, "API REQUEST 1")
    upstream_resp = section(t, "API RESPONSE 1")
    back = section(t, "RESPONSE")
    print("log bytes:", len(t), "| inbound:", len(inbound), "| upstream req:", len(upstream),
          "| upstream resp:", len(upstream_resp), "| translated back:", len(back))

    # developer / system prompt forwarded
    dev = re.findall(r'"role":"developer","content":\[\{"type":"input_text","text":"((?:[^"]|(?<=\\)")*)"', upstream)
    print("developer-message chars forwarded:", [len(d) for d in dev])
    sys_in = re.findall(r'"system":(\[.*?\]|".*?")', inbound, re.S)
    print("inbound system chars:", [len(s) for s in sys_in])

    tools = re.findall(r'"name":"(\w+)","description":"[^"]*","type":"function"', upstream)
    print("tool schemas forwarded:", len(tools), tools)
    tools_in = re.findall(r'"name":"(\w+)"', re.search(r'"tools":\[.*', inbound, re.S).group(0)) if '"tools"' in inbound else []
    print("tools in inbound request:", len(set(tools_in)))

    print("inbound thinking:", re.findall(r'"thinking":\{[^{}]*\}', inbound)[:1])
    print("upstream reasoning:", re.findall(r'"reasoning":\{[^{}]*\}', upstream)[:1])
    print("upstream model:", re.findall(r'"model":"([\w.\-]+)"', upstream)[:1],
          "| inbound model:", re.findall(r'"model":"([\w.\-]+)"', inbound)[:1])
    for k in ["input_tokens", "cached_tokens", "output_tokens", "reasoning_tokens"]:
        print(f"  {k}:", re.findall(r'"%s":(\d+)' % k, upstream_resp)[-1:])
    # did the translated-back response keep the text intact?
    up_text = "".join(re.findall(r'"type":"output_text","text":"((?:[^"]|(?<=\\)")*)"', upstream_resp))
    back_text = "".join(re.findall(r'"type":"text","text":"((?:[^"]|(?<=\\)")*)"', back))
    print("response text chars upstream vs translated back:", len(up_text), len(back_text),
          "| identical:", up_text == back_text)


if __name__ == "__main__":
    main(sys.argv[1])
