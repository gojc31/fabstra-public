# bench/orch - fabstra orchestration eval

One fixed real build (brief.md: the "ledger" CSV summary CLI, four tasks T1-T4) run headlessly through three arms, scored on held-out tests plus process metrics.

Arms (case-sensitive): `A` = Fable 5.1, Orchestrate mode, Astra review; `B1` = Opus 5.5, Lead mode, fresh-Fable review (model-router:reviewer); `B2` = Opus 5.5 forced into Orchestrate mode, fresh-Fable review. Astra gates the plan in all three.
- `B0` = Opus 5.5 no-skill baseline: model-router plugin off for the run, prompt keeps only the generic headless rules plus a per-run exemption from the CLAUDE.md fabstra mandate, no Astra probe, METRICS `"mode":"none"`.
- `B1L` = `B1` with fabstra loaded from `variants/model-router-lean` via `--plugin-dir`; only the preamble's file-access line differs (names the variant path only).
- Mechanism (B0, B1L): run.sh writes `.scratch/settings.json` = `{"enabledPlugins":{"model-router@robonuggets":false}}` and passes `--settings .scratch/settings.json` (per run; user config untouched). Verified 2026-10-07 from the stream-json init message: B0 lists no model-router plugin, agents or fabstra; B1L lists one `model-router@inline` plugin at the variant path.

Run: `bash run.sh <ARM> <N> [--dry]` from Git Bash. It recreates `results/work-<ARM>-<N>` via `fixture.py`, probes Astra (exit 3 `ASTRA_COOLING`, exit 4 proxy down), writes `.scratch/prompt.md`, runs `claude -p` (7200 s cap) with it on stdin, then `score.py`. `--dry` stops after printing the command.
Re-score any work dir: `python score.py <work> <ARM> <N>` (appends to `results/results.csv`, writes the header if absent, prints key=value).

Files: `fixture.py` (stub repo + git commit), `brief.md` (the client brief, copied in), `hidden/test_hidden.py` (36 held-out tests, never copied in), `reference/ledger/` (proof the hidden tests pass: overlay it on a fixture), `run.sh`, `score.py`.

Columns:
- `hidden_pass/total`, `visible_pass/total`: pytest counts (collection error = 0 passed, total from a static `def test_` count).
- `exit_code`, `seconds`: from `timing.txt` (start, end, exit). `api_seconds`, `cost_usd`, `turns`, `opus_out_tokens`, `fable_out_tokens`: from `claude.out.json` (`modelUsage` keys matched on "opus"/"fable").
- `lead_model`, `mode`, `plan_*`, `review_*`, `fix_rounds`, `in_session_edits`, `defaults_taken`, `unfinished`: from `.fabstra/METRICS.json` (`metrics_present=1`). Without it (`metrics_present=0`) only `review_findings` (ACCEPTED+REJECTED), `review_p1` (P1 tokens), `review_rounds` (re-review lines), `fix_rounds` (fix round lines), `defaults_taken` are guessed from `.fabstra/RUN.md`.
- `review_seats` is `;`-joined. `files_changed`: files differing from the fixture commit (committed or not) plus untracked, excluding `.fabstra/`, `.scratch/`, `.pytest_cache/`, `claude.*`, `timing.txt`, `__pycache__`; `files_outside_ledger`: those not under `ledger/` or `tests/`.

Empty cell = input missing, never a crash. Delete `results/` for a clean series.

## Readout 2026-09-27

| Orchestrator | Reviewer | n | Hidden | Avg min | Avg $ | Avg review findings | Avg fix rounds |
|---|---|---|---|---|---|---|---|
| Fable 5.1 | Astra | 2 | 36/36 | 40 | 11.24 | 6.5 | 3.5 |
| Fable 5.1 | Fable | 2 | 36/36 | 21 | 10.05 | 0.5 | 0.5 |
| Opus 5.5 orchestrate | Astra (+Fable parallel) | 2 | 36/36 | 38 | 9.08 | 6.0 | 2.0 |
| Opus 5.5 orchestrate | Fable | 2 | 36/36 | 16 | 5.75 | 0.5 | 0.0 |
| Opus 5.5 lead | Fable | 2 | 36/36 | 20 | 7.08 | 1.5 | 1.0 |

1. The reviewer, not the orchestrator, drives findings and wall time: Astra reports 6-7 findings where Fable reports about 0.5 on the same build.
2. With the reviewer held constant, Opus 5.5 orchestrating is cheaper than Fable 5.1 orchestrating at identical hidden-test quality.
3. Astra's findings graded 5 real / 7 marginal / 0 wrong across 12; the parallel Fable review and the 36 hidden tests missed all 5 real ones. Keep the GPT gate seat as the primary reviewer and Fable as the parallel second seat.

Arms: A = Fable-orch + Astra review; AF = Fable-orch + Fable review; B2 = Opus-orch + Fable review; B2A = Opus-orch + Astra review; B1 = Opus-lead + Fable review. results.csv holds one stale partial B2A-1 row (no cost column) from an interrupted run - exclude it.
