# FabStra browser and desktop surfaces

Contents: Browser and desktop surfaces (Codex transport on the Pro home only); jev-ultrafast - allowlisted read-only browser goals

Reached from: fabstra SKILL.md - browser QA, "use computer use", or a concept render

Related:
> The Codex transport these surfaces launch through is in transport.md.
## Browser and desktop surfaces (Codex transport on the Pro home only)

The Pro home `"${CODEX_PRO_HOME:-$HOME/.codex-pro}"` carries Codex's Browser plugin and
Computer Use plugin (config.toml: `[mcp_servers.node_repl]`,
`[mcp_servers.cua_repl]`, `[plugins."browser@openai-bundled"]`,
`[plugins."computer-use@openai-bundled"]`, bundled marketplace mirrored under
`.tmp/`). Verified on 2026-09-05 and 2026-09-06 from headless `codex exec`
launches (the desktop app rewrites `~/.codex/config.toml` on every update;
after an update re-sync the `node_repl` / `cua_repl` paths in
`.codex-pro/config.toml` by hand - runtime hash under `runtimes\cua_node\`,
`CODEX_CLI_PATH` hash under `Codex\bin\`, `ChatGPT.exe` version):

- **Browser plugin, Chrome backend: WORKS headless.** Astra drives its own
  Chrome - data dir `%USERPROFILE%\ChromeAstra`, desktop shortcut "Astra
  Chrome", Codex extension instance `bcb4ef71-2587-45b8-a174-4655537d3a66`.
  The Pro home's node_repl env pins that instance and sets
  `BROWSER_USE_SECURITY_MODE=disabled-for-local-testing`, which skips the
  site-safety check and the per-action consent prompt (a shell launch has
  nobody to answer them). Your main Chrome may also carry the extension; the pin
  is honoured ONLY by URL-based selection, so the spec must force it.
- **In-app browser: does NOT work headless** ("Browser is not available:
  iab" - it lives only inside a thread the app window hosts).
- **Computer Use: WORKS headless through
  `"${CODEX_PRO_HOME:-$HOME/.codex-pro}/cua-headless.mjs"`** (verified 2026-09-06:
  Notepad launched, state read, text typed and read back, no desktop app).
  The stock `@oai/sky` import needs the desktop app - every app action
  returns a per-app approval request that only the app's UI can answer
  ("Computer Use was not approved to use <app>"). The module builds the
  same client on the plugin's direct helper transport (spawns
  `codex-computer-use.exe` itself) and answers those approvals in-process;
  it also passes `CODEX_CLI_PATH`, which the helper needs to spawn `codex
  app-server`. Optional allowlist `globalThis.CUA_HEADLESS_ALLOWED_APPS`
  (app ids as `list_apps()` reports them); audio recording always declined;
  answered approvals logged in `globalThis.cuaApprovals`. The Escape key
  still stops the helper. Stock plugin docs (`api.md`, `guidance.md`,
  `confirmations.md`) apply unchanged.
- Neither surface exists on the `claude -p` transport - there browser work
  is browser-harness (global CLAUDE.md). No conflict: browser-harness for
  Claude-harness runs, the Browser plugin for Codex runs.
- **Image generation (GPT Image 2): WORKS on the Pro home.** Codex's
  built-in `image_gen` tool (`codex-pro features list` -> `image_generation
  stable true`, verified 2026-09-06) with the system skill
  `.codex-pro/skills/.system/imagegen/`. Runs on the ChatGPT login, no
  `OPENAI_API_KEY`; outputs land in `.codex-pro/generated_images/<session>/`.
  Not on the `claude -p` transport - Phase 1b and Lane B Astra sessions
  cannot render, so a render is always its own Codex-transport step.

## jev-ultrafast - allowlisted read-only browser goals (first choice, Claude-harness only)

This section covers CLAUDE-HARNESS browser tasks only. It does not change the
Codex Browser-plugin exception above ("Web page work" and the global
CLAUDE.md's "Codex-side exception" paragraph) - Astra's own Chrome is
untouched by this rule.

On a Claude session, a read-only navigate/click/read goal whose start URL is
on a host already in `$JEV_ULTRAFAST_HOME/jc/allowed-hosts.txt`
goes to `jevgo --url <url> --goal "<goal naming the path>"` first. It prints
one JSON line with the run's status, the final URL, the page title, the
target/tab and session ids, action and decision counts, cost, and an error
field when there is one - plus a short history tail whose action labels can
echo text copied straight off the page's own controls (a button or link's
visible label). None of that is a read of the page's body content, so treat
the line as a navigation-and-cost record, never as proof of what the page
says. It exits 0 done / 1 blocked or budget / 2 error / 3 login wall / 4 host
not allowed. `--close` closes the tab the run opened; leave it off to inspect
the tab yourself first. Name the path in the goal - Jev gives up when the
target is below the fold.

Verify page CONTENT independently, never from the JSON line alone: with
browser-harness, `switch_tab(<target_id from the JSON line>)` on the tab the
run left open, then read its body text with the harness's `js(...)` call
(for example `js("document.body.innerText")`) and check that text for the
facts the goal needed, then close only that tab. `sitecheck` and
`jc/jev_suite.py`'s `inspect()` are a NAVIGATION check, not a content check -
they read only the URL/path, in-view section ids, the page's `h1`, and a
missing-article flag, so they can pass on a page whose body text never
mentions what the goal was looking for. Use them to confirm routing landed in
the right place, and do the body-text read above whenever the goal needs real
content verified. On exit 1-4, or a failed content check, fall back to
browser-harness for the same goal.

Never: client apps, logged-in pages, forms that submit, typing credentials,
any host not already in the file - adding one is JC's call. Site suites:
`sitecheck [suite]` runs the whole allowlisted set the same way (a navigation
check across the set, per above, not a content check).

Rules:

- **Web page work** (dashboard QA, latency, bug hunting, forms) -> Codex
  side on the Pro home. Before launch, confirm Astra's Chrome is running
  (`tasklist` shows a chrome.exe with `ChromeAstra` in its command line);
  if not, start it with the desktop shortcut's command:
  `"C:\Program Files\Google\Chrome\Application\chrome.exe" --user-data-dir="%USERPROFILE%\ChromeAstra" --no-first-run --no-default-browser-check`.
  Spec lines, verbatim: `Surface: Browser plugin, Chrome extension backend.
  Not the in-app browser, not Computer Use, not browser-harness. Select
  the browser ONLY with agent.browsers.getForUrl(<first url>) - never
  get('chrome'), never by id (ids swap between runs). GATE: if the
  selected entry's metadata.extensionInstanceId is not
  bcb4ef71-2587-45b8-a174-4655537d3a66, stop, open nothing, report the
  mismatch. Open new tabs only; close every tab you opened. Stop at any
  login page and report; never type credentials.` Because the consent
  prompt is off on this path, every outward-facing step (submit, send,
  pay, delete, account change) is written into the spec as a hand-off to
  the user, never left to the run.
- **Concept renders** - ONLY when the task is design, dashboard, or UI/UX
  work (a screen, a component set, a landing page, a visual direction) AND
  either the layout is undecided in Phase 1 or the user asks for a mockup,
  hero, or illustration. Any other task, or any UI task whose direction is
  already fixed by a design system or an existing screen: no render. The
  render is a reference for the builder, never the deliverable - the
  dashboard still ships as code. Run it as one Codex-transport job on the
  Pro home (`--write`, effort high) before the builder brief. Spec lines,
  verbatim: `Surface: built-in image_gen tool via the imagegen system
  skill, built-in mode only - never the CLI fallback, there is no
  OPENAI_API_KEY here. One render per named screen or variant, at most 3
  per run. Copy each chosen output from $CODEX_HOME/generated_images/ to
  <project>/design/renders/<screen>-v<N>.png; never overwrite an existing
  file. Report the final paths and the revised prompt for each.` Then put
  the render path in the builder blueprint as `Visual reference:` and log
  each render in RUN.md. "image_gen unavailable" or any fallback offer in
  the report: do not approve the CLI path, report the text, proceed without
  a render.
- **"use computer use"** - only when the user says it. Codex side on the
  Pro home, headless, `-s read-only` like the browser runs (workspace-write
  hangs the node_repl kernel at setup). Before launch, tell the user the run
  takes the mouse and keyboard and to stay off both until the report lands,
  and name the apps the run may touch. Spec lines, verbatim: `Surface:
  Computer Use, headless. Initialize with exactly:
  globalThis.CUA_HEADLESS_ALLOWED_APPS = "<app ids, comma-separated, or
  empty for any>"; if (!globalThis.sky) { const { sky } = await
  import("<CODEX_PRO_HOME as an absolute forward-slash path>/cua-headless.mjs");
  globalThis.sky = sky; } - never import "@oai/sky" directly, never use the cua_repl server.
  Then follow the computer-use plugin's docs/guidance.md and docs/api.md.
  Target window: <exact title>. Observe with get_window_state before every
  action; act only inside the target window; never activate or touch
  another window; never use the Windows key. Every step in
  docs/confirmations.md's hand-off or always-confirm lists is a hand-off to
  the user, not an action. End the report with JSON.stringify(
  globalThis.cuaApprovals).` Because the per-app prompt is answered
  in-process, the allowlist and the hand-off lines are the only consent
  the user gives - write both every time. Without the phrase, Computer Use
  is never used.
- Any "not available" / "not approved" / "declined permission" text in a
  report: do not retry or substitute a surface; report the exact text.

