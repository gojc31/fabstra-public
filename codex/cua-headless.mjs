// cua-headless.mjs - Computer Use for headless Codex runs (codex exec / fabstra / fable-mode).
//
// The stock `@oai/sky` client needs the Codex desktop app: it either talks to the app over a
// named pipe (SKY_CUA_NATIVE_PIPE=1) or, when it spawns codex-computer-use.exe itself, it routes
// every per-app approval request through node_repl's elicitation UI, which only the desktop app
// can show. `codex exec` has neither, so every app action fails with
// "Computer Use requires app approval but elicitations are unavailable".
//
// This module builds the same WindowsComputerUseClient on the helper transport (spawns
// codex-computer-use.exe directly, no desktop app needed) and answers each per-app approval
// request itself. The approval is the user's up-front consent: the launcher only loads this
// module when the user said "use computer use". Everything else is stock: the plugin's
// confirmations policy, the Escape-key stop (helper exits 130), the safety denies in SKILL.md.
//
// Usage inside node_repl (replaces the SKILL.md Initialize cell):
//   if (!globalThis.sky) {
//     const { sky } = await import("<CODEX_PRO_HOME, forward slashes>/cua-headless.mjs");
//     globalThis.sky = sky;
//   }
// Then use `sky.*` exactly as docs/api.md and docs/guidance.md describe.
//
// Set globalThis.CUA_HEADLESS_ALLOWED_APPS before the import (or the env var of the same name) to a
// comma-separated list of app ids as list_apps() reports them (e.g.
// "microsoft.windowsnotepad_8wekyb3d8bbwe!app") to approve only those apps; unset = approve every
// app the helper asks about. Audio recording is always declined. Approvals are logged to
// globalThis.cuaApprovals for the run report.
//
// Ships in gojc31/fabstra-public as codex/cua-headless.mjs; copy it into your Pro home (CODEX_PRO_HOME).
// Created 2026-09-06, verified the same day with cua-headless-test.mjs (Notepad: list, launch, read
// state, type, read back; 5 approvals auto-answered; no desktop app). The helper spawns
// `codex app-server` and needs CODEX_CLI_PATH, resolved below. Backup of config:

import { pathToFileURL } from "node:url";
import { existsSync, readdirSync } from "node:fs";
import path from "node:path";

function envGet(name) {
  const fromRepl = globalThis.nodeRepl?.env?.[name];
  if (typeof fromRepl === "string" && fromRepl.trim()) return fromRepl.trim();
  const fromProc = globalThis.process?.env?.[name];
  return typeof fromProc === "string" && fromProc.trim() ? fromProc.trim() : null;
}

function findSkyDir() {
  // 1. The node_modules dir node_repl was launched with (survives app updates because the
  //    desktop app rewrites ~/.codex/config.toml; keep .codex-pro/config.toml in sync).
  const modDirs = envGet("NODE_REPL_NODE_MODULE_DIRS");
  if (modDirs) {
    for (const dir of modDirs.split(";")) {
      const candidate = path.join(dir.trim(), "@oai", "sky");
      if (existsSync(path.join(candidate, "package.json"))) return candidate;
    }
  }
  // 2. Newest installed cua_node runtime that ships @oai/sky.
  const home = globalThis.process?.env?.LOCALAPPDATA ?? path.join(globalThis.process?.env?.USERPROFILE ?? "", "AppData", "Local");
  const runtimes = path.join(home, "OpenAI", "Codex", "runtimes", "cua_node");
  if (existsSync(runtimes)) {
    const hits = readdirSync(runtimes)
      .map((h) => path.join(runtimes, h, "bin", "node_modules", "@oai", "sky"))
      .filter((p) => existsSync(path.join(p, "package.json")));
    if (hits.length) return hits[0];
  }
  throw new Error("cua-headless: could not locate the bundled @oai/sky package");
}

const skyDir = findSkyDir();
const internal = path.join(skyDir, "dist", "project", "cua", "sky_js", "src", "targets", "windows", "internal");
const { WindowsHelperTransport } = await import(pathToFileURL(path.join(internal, "helper_transport.js")).href);
const { WindowsComputerUseClient } = await import(pathToFileURL(path.join(internal, "computer_use_client.js")).href);

const helperExe = path.join(skyDir, "bin", "windows", "codex-computer-use.exe");
if (!existsSync(helperExe)) throw new Error(`cua-headless: helper not found at ${helperExe}`);

// Allowlist: globalThis.CUA_HEADLESS_ALLOWED_APPS (set by the spec before the import) wins over the env var.
const allowed = String(globalThis.CUA_HEADLESS_ALLOWED_APPS ?? envGet("CUA_HEADLESS_ALLOWED_APPS") ?? "")
  .split(",")
  .map((s) => s.trim().toLowerCase())
  .filter(Boolean);

globalThis.cuaApprovals = globalThis.cuaApprovals ?? [];

async function createElicitation(req) {
  const app = String(req?.meta?.tool_params?.app ?? "").toLowerCase();
  const display = req?.meta?.tool_params_display?.[0]?.value ?? app;
  const isAudio = app === "computer-audio";
  const ok = !isAudio && (allowed.length === 0 || allowed.includes(app));
  globalThis.cuaApprovals.push({ app, display, action: ok ? "accept" : "decline", at: new Date().toISOString() });
  return { action: ok ? "accept" : "decline" };
}

// The helper spawns `codex app-server` and locates codex.exe through CODEX_CLI_PATH ("failed to
// launch codex app-server: program not found" otherwise). node_repl already carries it from
// config.toml; a standalone run does not, so resolve it here: env -> newest hashed bin dir -> shim.
function findCodexCli() {
  const fromEnv = envGet("CODEX_CLI_PATH");
  if (fromEnv && existsSync(fromEnv)) return fromEnv;
  const home = globalThis.process?.env?.LOCALAPPDATA ?? path.join(globalThis.process?.env?.USERPROFILE ?? "", "AppData", "Local");
  const bin = path.join(home, "OpenAI", "Codex", "bin");
  if (existsSync(bin)) {
    const hashed = readdirSync(bin)
      .map((h) => path.join(bin, h, "codex.exe"))
      .filter((p) => existsSync(p));
    if (hashed.length) return hashed[0];
    const flat = path.join(bin, "codex.exe");
    if (existsSync(flat)) return flat;
  }
  throw new Error("cua-headless: codex.exe not found; set CODEX_CLI_PATH");
}
export const codexCliPath = findCodexCli();

const inner = new WindowsHelperTransport({
  helperCommand: helperExe,
  helperArgs: ["--parent-pid", String(globalThis.process?.pid ?? 0)],
  helperEnv: { CODEX_CLI_PATH: codexCliPath },
});

const transport = {
  close: () => inner.close(),
  request: (method, params, options = {}) =>
    inner.request(method, params, { ...options, createElicitation }),
};

export const sky = new WindowsComputerUseClient({ transport });
export const skyPackageDir = skyDir;
export const helperPath = helperExe;
