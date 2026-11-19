"""Tests for scripts/gemini-hitrate.py (tmp_path only; never reads the real home)."""
import json
import os
import subprocess
import sys

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "gemini-hitrate.py")


def run(args, roots=None, tmp_path=None):
    env = dict(os.environ)
    env.pop("GEMINI_HITRATE_ROOTS", None)
    if roots is not None:
        env["GEMINI_HITRATE_ROOTS"] = os.pathsep.join(str(r) for r in roots)
    if tmp_path is not None:
        # keep Path.home() inside tmp_path so a fallback never reads the real home
        env["USERPROFILE"] = str(tmp_path)
        env["HOME"] = str(tmp_path)
    return subprocess.run(
        [sys.executable, SCRIPT, *map(str, args)],
        capture_output=True, text=True, env=env, timeout=60,
    )


def write_run(folder, name, lines):
    d = folder / ".fabstra"
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def as_json(res):
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def row(data, seat, mode, via="app"):
    for r in data["rows"]:
        if r["seat"] == seat and r["mode"] == mode and r.get("via", "app") == via:
            return r
    raise AssertionError(f"no row {seat}/{mode}/{via}: {data['rows']}")


def test_scored_lines_summed_per_seat_mode(tmp_path):
    write_run(tmp_path, "RUN.md", [
        "- seat=gemini mode=plan 25s ok leads=4 real=2",
        "- seat=gemini mode=plan 30s ok leads=6 real=1",
        "- seat=hydrogen mode=quick 9s ok leads=3 real=3",
        "unrelated line leads=9 real=9",
    ])
    data = as_json(run([tmp_path, "--json"], tmp_path=tmp_path))
    plan = row(data, "gemini", "plan")
    assert (plan["launches"], plan["scored"], plan["leads"], plan["real"]) == (2, 2, 10, 3)
    assert plan["hit_rate"] == 30.0
    quick = row(data, "hydrogen", "quick")
    assert (quick["leads"], quick["real"], quick["hit_rate"]) == (3, 3, 100.0)
    assert data["totals"]["leads"] == 13 and data["totals"]["real"] == 6
    assert data["totals"]["launches"] == 3


def test_unscored_counted_not_summed(tmp_path):
    write_run(tmp_path, "RUN.md", [
        "- seat=gemini mode=pair 20s ok used 2 items",
        "- seat=gemini mode=pair 20s ok leads=5",
        "- seat=gemini mode=pair ok leads=2 real=1",
        "- seat=gemini 20s ok",
    ])
    data = as_json(run([tmp_path, "--json"], tmp_path=tmp_path))
    pair = row(data, "gemini", "pair")
    assert (pair["launches"], pair["scored"], pair["unscored"]) == (3, 1, 2)
    assert (pair["leads"], pair["real"]) == (2, 1)
    unk = row(data, "gemini", "unknown")
    assert unk["unscored"] == 1
    assert data["totals"]["unscored"] == 3


def test_real_above_leads_is_invalid(tmp_path):
    write_run(tmp_path, "RUN.md", [
        "- seat=gemini mode=review ok leads=2 real=5",
        "- seat=gemini mode=review ok leads=4 real=1",
    ])
    data = as_json(run([tmp_path, "--json"], tmp_path=tmp_path))
    rev = row(data, "gemini", "review")
    assert (rev["launches"], rev["invalid"], rev["scored"]) == (2, 1, 1)
    assert (rev["leads"], rev["real"]) == (4, 1)
    assert data["totals"]["invalid"] == 1


def test_skipped_records(tmp_path):
    write_run(tmp_path, "RUN.md", [
        "- seat=gemini mode=plan skipped: plan not abstractable leads=0 real=0",
        "- seat=hydrogen mode=fix skipped: slug latched",
        "- seat=hydrogen mode=fix 8s ok leads=2 real=1",
        "- gemini skipped: plan not abstractable",  # legacy bare form: no seat token
    ])
    data = as_json(run([tmp_path, "--json"], tmp_path=tmp_path))
    plan = row(data, "gemini", "plan")
    assert (plan["launches"], plan["skipped"], plan["scored"], plan["hit_rate"]) == (1, 1, 0, None)
    fix = row(data, "hydrogen", "fix")
    assert (fix["launches"], fix["skipped"], fix["scored"], fix["unscored"]) == (2, 1, 1, 0)
    assert data["totals"]["skipped"] == 2
    assert data["totals"]["launches"] == 3
    t = data["totals"]
    assert t["launches"] == t["scored"] + t["unscored"] + t["invalid"] + t["skipped"]


def test_free_text_skipped_does_not_flip(tmp_path):
    write_run(tmp_path, "RUN.md", ["- seat=gemini mode=solo ok, 2 items skipped leads=3 real=1"])
    data = as_json(run([tmp_path, "--json"], tmp_path=tmp_path))
    solo = row(data, "gemini", "solo")
    assert (solo["skipped"], solo["scored"]) == (0, 1)


def test_folder_arg_finds_run_files_only(tmp_path):
    write_run(tmp_path, "RUN.md", ["seat=gemini mode=plan leads=1 real=1"])
    write_run(tmp_path, "RUN-other.md", ["seat=gemini mode=plan leads=1 real=0"])
    write_run(tmp_path, "REPORT.md", ["seat=gemini mode=plan leads=50 real=50"])
    (tmp_path / "RUN.md").write_text("seat=gemini mode=plan leads=70 real=70\n", encoding="utf-8")
    nested = tmp_path / "sub" / ".fabstra"
    nested.mkdir(parents=True)
    (nested / "RUN.md").write_text("seat=gemini mode=plan leads=90 real=90\n", encoding="utf-8")
    data = as_json(run([tmp_path, "--json"], tmp_path=tmp_path))
    assert data["files_read"] == 2
    plan = row(data, "gemini", "plan")
    assert (plan["leads"], plan["real"]) == (2, 1)


def test_file_arg_any_name(tmp_path):
    p = tmp_path / "notes.txt"
    p.write_text("seat=hydrogen mode=quick leads=2 real=1\n", encoding="utf-8")
    data = as_json(run([p, "--json"], tmp_path=tmp_path))
    assert data["files_read"] == 1
    assert row(data, "hydrogen", "quick")["real"] == 1


def test_env_roots_override_defaults(tmp_path):
    home_proj = tmp_path / "proj"
    write_run(tmp_path, "RUN.md", ["seat=gemini mode=plan leads=10 real=10"])
    write_run(home_proj, "RUN.md", ["seat=gemini mode=plan leads=10 real=10"])
    other = tmp_path / "elsewhere" / "root"
    write_run(other, "RUN-x.md", ["seat=gemini mode=pair leads=3 real=2"])
    write_run(other / "proj", "RUN.md", ["seat=gemini mode=pair leads=1 real=1"])
    write_run(other / "proj" / "deep", "RUN.md", ["seat=gemini mode=pair leads=50 real=50"])
    missing = tmp_path / "does-not-exist"
    data = as_json(run(["--json"], roots=[other, missing], tmp_path=tmp_path))
    assert data["files_read"] == 2
    assert [(r["seat"], r["mode"], r["via"]) for r in data["rows"]] == [("gemini", "pair", "app")]
    assert data["rows"][0]["leads"] == 4


def test_defaults_scan_home_one_level(tmp_path):
    write_run(tmp_path, "RUN.md", ["seat=gemini mode=plan leads=1 real=1"])
    write_run(tmp_path / "proj", "RUN-a.md", ["seat=gemini mode=plan leads=1 real=0"])
    write_run(tmp_path / "a" / "b", "RUN.md", ["seat=gemini mode=plan leads=9 real=9"])
    # R2: an absent D:/ root is skipped silently (pointed at a missing folder here)
    env_extra = {"GEMINI_HITRATE_D_ROOT": str(tmp_path / "no-such-drive")}
    env = dict(os.environ, USERPROFILE=str(tmp_path), HOME=str(tmp_path), **env_extra)
    env.pop("GEMINI_HITRATE_ROOTS", None)
    res = subprocess.run([sys.executable, SCRIPT, "--json"], capture_output=True,
                         text=True, env=env, timeout=60)
    data = as_json(res)
    assert data["files_read"] == 2
    assert row(data, "gemini", "plan")["leads"] == 2


def test_missing_path_exit_2(tmp_path):
    missing = tmp_path / "nope"
    res = run([missing], tmp_path=tmp_path)
    assert res.returncode == 2
    assert str(missing) in res.stderr


def test_json_shape_and_table(tmp_path):
    write_run(tmp_path, "RUN.md", ["seat=gemini mode=plan leads=0 real=0"])
    data = as_json(run([tmp_path, "--json"], tmp_path=tmp_path))
    assert set(data) == {"rows", "totals", "files_read", "unreadable"}
    assert data["unreadable"] == 0
    keys = {"seat", "mode", "via", "model", "launches", "scored", "unscored", "invalid", "skipped",
            "leads", "real", "hit_rate"}
    assert set(data["rows"][0]) == keys
    assert set(data["totals"]) == keys - {"seat", "mode", "via", "model"}
    assert data["rows"][0]["hit_rate"] is None
    res = run([tmp_path], tmp_path=tmp_path)
    assert res.returncode == 0
    out = res.stdout
    assert "seat" in out and "via" in out and "hit" in out and "files read: 1" in out
    assert "unreadable files: 0" in out
    plan_line = [ln for ln in out.splitlines() if ln.startswith("gemini")][0]
    assert plan_line.rstrip().endswith("-")


# ---- fix round 1: anchored records (F-A, F-B), unreadable files (F-C), CLI (F-D) ----

def test_terminal_counts_win_over_prose_counts(tmp_path):
    write_run(tmp_path, "RUN.md", ["- seat=gemini mode=plan fixed example `leads=100 real=100` leads=3 real=1"])
    plan = row(as_json(run([tmp_path, "--json"], tmp_path=tmp_path)), "gemini", "plan")
    assert (plan["scored"], plan["leads"], plan["real"]) == (1, 3, 1)


def test_counts_not_at_line_end_are_unscored(tmp_path):
    write_run(tmp_path, "RUN.md", ["- seat=gemini mode=plan leads=3 real=1 then prose after"])
    plan = row(as_json(run([tmp_path, "--json"], tmp_path=tmp_path)), "gemini", "plan")
    assert (plan["scored"], plan["unscored"], plan["leads"]) == (0, 1, 0)


def test_free_text_skipped_colon_on_scored_line_stays_scored(tmp_path):
    write_run(tmp_path, "RUN.md", ["- seat=gemini mode=solo ok, item (c) skipped: out of scope leads=3 real=1"])
    solo = row(as_json(run([tmp_path, "--json"], tmp_path=tmp_path)), "gemini", "solo")
    assert (solo["skipped"], solo["scored"], solo["leads"], solo["real"]) == (0, 1, 3, 1)


def test_quoted_record_in_prose_is_not_a_launch(tmp_path):
    write_run(tmp_path, "RUN.md", [
        "The log line reads `seat=gemini mode=plan skipped: x leads=0 real=0` in the doc.",
        "gemini plan mode: seat=gemini mode=plan slug=s, launched leads=4 real=4",
        "seat=gemini-x mode=plan leads=1 real=1",
    ])
    data = as_json(run([tmp_path, "--json"], tmp_path=tmp_path))
    assert data["rows"] == [] and data["totals"]["launches"] == 0


def test_list_marker_and_indent_records(tmp_path):
    write_run(tmp_path, "RUN.md", [
        "- seat=gemini mode=pair ok leads=2 real=1",
        "* seat=gemini mode=pair ok leads=2 real=2",
        "    - seat=hydrogen mode=quick ok leads=1 real=1   ",
    ])
    data = as_json(run([tmp_path, "--json"], tmp_path=tmp_path))
    pair = row(data, "gemini", "pair")
    assert (pair["launches"], pair["scored"], pair["leads"], pair["real"]) == (2, 2, 4, 3)
    assert row(data, "hydrogen", "quick")["scored"] == 1


def test_multi_line_record_is_unscored(tmp_path):
    # one record per line: counts on a following line do not belong to the header
    write_run(tmp_path, "RUN.md", [
        "seat=gemini mode=review review-r1 ok, report x. Leads:",
        "- G1 ACCEPTED, G2 REJECTED",
        "leads=2 real=1",
    ])
    data = as_json(run([tmp_path, "--json"], tmp_path=tmp_path))
    rev = row(data, "gemini", "review")
    assert (rev["launches"], rev["unscored"], rev["scored"], rev["leads"]) == (1, 1, 0, 0)


def test_bom_first_line_is_a_record(tmp_path):
    d = tmp_path / ".fabstra"
    d.mkdir()
    (d / "RUN.md").write_bytes("﻿seat=gemini mode=plan ok leads=2 real=1\n".encode("utf-8"))
    plan = row(as_json(run([tmp_path, "--json"], tmp_path=tmp_path)), "gemini", "plan")
    assert plan["scored"] == 1


def _load_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gemini_hitrate", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_unreadable_file_counted_and_exit_0(tmp_path, monkeypatch, capsys):
    mod = _load_module()
    good = write_run(tmp_path, "RUN.md", ["seat=gemini mode=plan leads=2 real=1"])
    bad = write_run(tmp_path, "RUN-locked.md", ["seat=gemini mode=plan leads=9 real=9"])
    real_read = mod.Path.read_text

    def fake_read(self, *a, **k):
        if self.name == bad.name:
            raise PermissionError(13, "Permission denied", str(self))
        return real_read(self, *a, **k)

    monkeypatch.setattr(mod.Path, "read_text", fake_read)
    assert mod.main([str(tmp_path), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["unreadable"] == 1 and data["files_read"] == 1
    assert row(data, "gemini", "plan")["leads"] == 2
    assert mod.main([str(good), str(bad)]) == 0
    out = capsys.readouterr().out
    assert "unreadable files: 1" in out


def test_intermixed_args(tmp_path):
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    a.write_text("seat=gemini mode=plan leads=2 real=1\n", encoding="utf-8")
    b.write_text("seat=gemini mode=plan leads=3 real=3\n", encoding="utf-8")
    data = as_json(run([a, "--json", b], tmp_path=tmp_path))
    assert data["files_read"] == 2
    assert row(data, "gemini", "plan")["leads"] == 5


def test_bad_option_exit_64(tmp_path):
    res = run(["--nope"], tmp_path=tmp_path)
    assert res.returncode == 64
    assert "--nope" in res.stderr


# ---- API backup launches: the via=api record token ----

def test_b1_via_api_record(tmp_path):
    write_run(tmp_path, "RUN.md", ["seat=hydrogen mode=fix via=api fix-r1 20 s ok leads=3 real=1"])
    data = as_json(run([tmp_path, "--json"], tmp_path=tmp_path))
    assert len(data["rows"]) == 1
    r = row(data, "hydrogen", "fix", "api")
    assert (r["via"], r["launches"], r["scored"], r["leads"], r["real"]) == ("api", 1, 1, 3, 1)


def test_b2_app_and_api_rows_split_totals_joined(tmp_path):
    write_run(tmp_path, "RUN.md", [
        "seat=hydrogen mode=fix via=api fix-r1 20 s ok leads=3 real=1",
        "seat=hydrogen mode=fix fix-r2 ok leads=2 real=2",
    ])
    data = as_json(run([tmp_path, "--json"], tmp_path=tmp_path))
    assert sorted(r["via"] for r in data["rows"]) == ["api", "app"]
    api, app = row(data, "hydrogen", "fix", "api"), row(data, "hydrogen", "fix", "app")
    assert (api["leads"], api["real"]) == (3, 1)
    assert (app["leads"], app["real"]) == (2, 2)
    assert (data["totals"]["leads"], data["totals"]["real"], data["totals"]["launches"]) == (5, 3, 2)
    assert "via" not in data["totals"]


def test_b3_skip_rule_unchanged_by_via(tmp_path):
    write_run(tmp_path, "RUN.md", [
        "seat=gemini mode=review skipped: slug latched leads=0 real=0",
        "seat=hydrogen mode=quick via=api skipped: x leads=0 real=0",
    ])
    data = as_json(run([tmp_path, "--json"], tmp_path=tmp_path))
    rev = row(data, "gemini", "review", "app")
    assert (rev["launches"], rev["skipped"]) == (1, 1)
    q = row(data, "hydrogen", "quick", "api")
    assert (q["launches"], q["skipped"], q["scored"], q["leads"], q["real"], q["hit_rate"]) == (1, 0, 1, 0, 0, None)
    assert data["totals"]["skipped"] == 1


def test_b4_only_exact_via_api_token_counts(tmp_path):
    write_run(tmp_path, "RUN.md", [
        "seat=gemini mode=plan notvia=api leads=1 real=1",
        "seat=gemini mode=plan via=apix leads=1 real=1",
        "seat=gemini mode=plan via=web leads=1 real=1",
    ])
    data = as_json(run([tmp_path, "--json"], tmp_path=tmp_path))
    assert [r["via"] for r in data["rows"]] == ["app"]
    assert row(data, "gemini", "plan", "app")["launches"] == 3


def test_b4_via_api_outside_a_record_changes_nothing(tmp_path):
    base = ["seat=gemini mode=plan ok leads=2 real=1"]
    write_run(tmp_path / "a", "RUN.md", base)
    write_run(tmp_path / "b", "RUN.md", base + [
        "via=api seat=gemini mode=plan leads=1 real=1",
        "The backup line carries via=api seat=hydrogen mode=fix leads=4 real=4",
    ])
    want = as_json(run([tmp_path / "a", "--json"], tmp_path=tmp_path))
    got = as_json(run([tmp_path / "b", "--json"], tmp_path=tmp_path))
    assert got["rows"] == want["rows"] and got["totals"] == want["totals"]
    assert [r["via"] for r in got["rows"]] == ["app"]


def test_b5_table_aligned_with_via_column(tmp_path):
    write_run(tmp_path, "RUN.md", [
        "seat=hydrogen mode=fix via=api fix-r1 ok leads=3 real=1",
        "seat=hydrogen mode=fix fix-r2 ok leads=12 real=2",
        "seat=gemini mode=review ok leads=4 real=4",
    ])
    res = run([tmp_path], tmp_path=tmp_path)
    assert res.returncode == 0, res.stderr
    lines = res.stdout.splitlines()
    head = lines[0]
    assert head.split()[:3] == ["seat", "mode", "via"]
    table = [ln for ln in lines if ln.split() and ln.split()[0] in ("seat", "gemini", "hydrogen", "TOTAL")]
    assert len(table) == 5
    assert len({len(ln) for ln in table}) == 1
    col = head.index("via")
    vias = [ln[col:].split()[0] for ln in table[1:-1]]
    assert sorted(vias) == ["api", "app", "app"]


# ---- model split: the optional model=<name> record token ----

LEGACY = [
    "seat=gemini mode=review via=api r1 ok leads=3 real=1",
    "seat=gemini mode=review r2 ok leads=4 real=4",
    "- seat=hydrogen mode=fix via=api fix-r1 leads=5 real=2",
    "seat=hydrogen mode=quick skipped: none",
    "seat=gemini mode=plan no counts here",
    "seat=gemini mode=plan leads=1 real=3",
]


def test_m1_model_token_split(tmp_path):
    write_run(tmp_path, "RUN.md", [
        "seat=gemini mode=review via=api model=neon review-r1 41 s ok leads=3 real=1",
        "seat=gemini mode=review via=api model=carbon review-r2 30 s ok leads=2 real=2",
    ])
    data = as_json(run([tmp_path, "--json"], tmp_path=tmp_path))
    got = sorted((r["model"], r["via"], r["launches"], r["leads"], r["real"]) for r in data["rows"])
    assert got == [("gemini-4-carbon", "api", 1, 2, 2), ("gemini-4-neon", "api", 1, 3, 1)]
    assert (data["totals"]["leads"], data["totals"]["real"]) == (5, 3)
    assert "model" not in data["totals"]


def test_m2_no_token_legacy_matches_pre_change(tmp_path):
    # expected values captured from the pre-change script on this exact fixture
    write_run(tmp_path, "RUN.md", LEGACY)
    data = as_json(run([tmp_path, "--json"], tmp_path=tmp_path))
    got = [(r["seat"], r["mode"], r["via"], r["model"], r["launches"], r["scored"], r["unscored"],
            r["invalid"], r["skipped"], r["leads"], r["real"]) for r in data["rows"]]
    assert got == [
        ("gemini", "plan", "app", "-", 2, 0, 1, 1, 0, 0, 0),
        ("gemini", "review", "api", "-", 1, 1, 0, 0, 0, 3, 1),
        ("gemini", "review", "app", "-", 1, 1, 0, 0, 0, 4, 4),
        ("hydrogen", "fix", "api", "-", 1, 1, 0, 0, 0, 5, 2),
        ("hydrogen", "quick", "app", "-", 1, 0, 0, 0, 1, 0, 0),
    ]
    assert data["totals"] == {"launches": 6, "scored": 3, "unscored": 1, "invalid": 1, "skipped": 1,
                              "leads": 12, "real": 7, "hit_rate": 58.3}
    res = run([tmp_path], tmp_path=tmp_path)
    lines = res.stdout.splitlines()
    assert lines[0].split()[:4] == ["seat", "mode", "via", "model"]
    total = [ln for ln in lines if ln.startswith("TOTAL")][0]
    assert total.split() == ["TOTAL", "6", "3", "1", "12", "7", "58.3%"]


def test_m3_not_a_model_token(tmp_path):
    write_run(tmp_path, "RUN.md", [
        'seat=gemini mode=plan via=api "model=neon" leads=1 real=1',
        "seat=gemini mode=plan via=api notmodel=neon leads=1 real=1",
        "seat=gemini mode=plan via=api model=NEON leads=1 real=1",
    ])
    data = as_json(run([tmp_path, "--json"], tmp_path=tmp_path))
    assert [(r["model"], r["launches"]) for r in data["rows"]] == [("-", 3)]


def test_m4_model_token_anywhere_after_seat(tmp_path):
    write_run(tmp_path, "RUN.md", [
        "seat=gemini model=neon mode=review via=api ok leads=1 real=1",
        "seat=hydrogen mode=fix fix-r1 model=hydrogen ok leads=2 real=1",
        "model=neon seat=gemini mode=review leads=9 real=9",
    ])
    data = as_json(run([tmp_path, "--json"], tmp_path=tmp_path))
    got = sorted((r["seat"], r["mode"], r["via"], r["model"]) for r in data["rows"])
    assert got == [("gemini", "review", "api", "gemini-4-neon"), ("hydrogen", "fix", "app", "gemini-4-hydrogen")]


def test_m5_table_model_column_aligned(tmp_path):
    write_run(tmp_path, "RUN.md", [
        "seat=gemini mode=review via=api model=neon ok leads=3 real=1",
        "seat=gemini mode=review via=api model=carbon ok leads=2 real=2",
        "seat=gemini mode=review ok leads=4 real=4",
    ])
    res = run([tmp_path], tmp_path=tmp_path)
    assert res.returncode == 0, res.stderr
    lines = res.stdout.splitlines()
    head = lines[0]
    table = [ln for ln in lines if ln.split() and ln.split()[0] in ("seat", "gemini", "TOTAL")]
    assert len(table) == 5
    assert len({len(ln) for ln in table}) == 1
    col = head.index("model")
    assert sorted(ln[col:].split()[0] for ln in table[1:-1]) == ["-", "gemini-4-carbon", "gemini-4-neon"]


# ---- model fold: aliases normalize to the API id geminipro reports ----

def test_m6_fold_aliases(tmp_path):
    write_run(tmp_path, "RUN.md", [
        "seat=gemini mode=review via=api model=carbon ok leads=1 real=1",
        "seat=gemini mode=review via=api model=gemini-carbon ok leads=2 real=1",
        "seat=gemini mode=review via=api model=gemini-4-carbon ok leads=3 real=2",
    ])
    data = as_json(run([tmp_path, "--json"], tmp_path=tmp_path))
    got = [(r["model"], r["launches"], r["scored"], r["leads"], r["real"]) for r in data["rows"]]
    assert got == [("gemini-4-carbon", 3, 3, 6, 4)]


def test_m7_fold_neon(tmp_path):
    write_run(tmp_path, "RUN.md", [
        "seat=gemini mode=review via=api model=neon ok leads=2 real=1",
        "seat=gemini mode=review via=api model=gemini-neon ok leads=1 real=1",
    ])
    data = as_json(run([tmp_path, "--json"], tmp_path=tmp_path))
    got = [(r["model"], r["launches"], r["leads"], r["real"]) for r in data["rows"]]
    assert got == [("gemini-4-neon", 2, 3, 2)]


def test_m8_unknown_model_kept(tmp_path):
    write_run(tmp_path, "RUN.md", [
        "seat=gemini mode=review via=api model=gemini-9-x ok leads=2 real=1",
        "seat=gemini mode=review via=api model=carbon ok leads=1 real=1",
    ])
    data = as_json(run([tmp_path, "--json"], tmp_path=tmp_path))
    got = sorted((r["model"], r["launches"], r["leads"]) for r in data["rows"])
    assert got == [("gemini-4-carbon", 1, 1), ("gemini-9-x", 1, 2)]
