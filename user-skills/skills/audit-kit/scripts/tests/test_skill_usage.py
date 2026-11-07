"""Tests for skill_usage.py. Run from the skill folder:

  python -m unittest discover -s scripts/tests -q

Each test builds a fake home (transcripts, user skills, plugins, settings) in
a temp folder and runs the script against it with --home.
"""
import ast
import contextlib
import datetime as dt
import importlib.util
import io
import json
import os
import subprocess
import sys
import shutil
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "skill_usage.py"
UTC = dt.timezone.utc


def iso(days_ago=0.0):
    t = dt.datetime.now(UTC) - dt.timedelta(days=days_ago)
    return t.strftime("%Y-%m-%dT%H:%M:%S.") + f"{t.microsecond // 1000:03d}Z"


def load_module():
    """Import a fresh copy of skill_usage for in-process tests (no bytecode written)."""
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("skill_usage_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def compact(obj):
    return json.dumps(obj, separators=(",", ":"))


def call(skill, ts, args_first=False, tid=None):
    inp = {"args": "go", "skill": skill} if args_first else {"skill": skill}
    return {"type": "assistant", "timestamp": ts, "uuid": str(uuid.uuid4()),
            "message": {"role": "assistant", "content": [
                {"type": "tool_use", "id": tid or "toolu_" + uuid.uuid4().hex,
                 "name": "Skill", "input": inp}]}}


def typed(name, ts):
    return {"type": "user", "timestamp": ts, "uuid": str(uuid.uuid4()),
            "message": {"role": "user", "content":
                        f"<command-name>/{name}</command-name>\n"
                        f"<command-message>{name}</command-message>\n"
                        "<command-args></command-args>"}}


def assistant_text(text, ts):
    return {"type": "assistant", "timestamp": ts, "uuid": str(uuid.uuid4()),
            "message": {"role": "assistant", "content": [{"type": "text", "text": text}]}}


def tool_result(text, ts):
    return {"type": "user", "timestamp": ts, "uuid": str(uuid.uuid4()),
            "message": {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "toolu_x", "content": text}]}}


def remove_tree(path):
    """Delete a temp tree; Windows may hold a folder a moment after a subprocess exits."""
    for _ in range(10):
        shutil.rmtree(path, ignore_errors=True)
        if not os.path.exists(path):
            return
        time.sleep(0.2)


class Home(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.claude = self.home / ".claude"
        (self.claude / "projects" / "proj").mkdir(parents=True)
        self.user_skill("solo")
        plugins = {}
        for plugin, skill in (("p", "alpha"), ("q", "alpha"), ("r", "beta"), ("loc", "gamma")):
            root = self.home / "cache" / plugin
            self.skill_md(root / "skills" / skill / "SKILL.md", skill)
            plugins[f"{plugin}@market"] = [{"scope": "user", "installPath": str(root)}]
        self.write_json(self.claude / "plugins" / "installed_plugins.json",
                        {"version": 2, "plugins": plugins})
        self.write_json(self.claude / "settings.json", {"enabledPlugins": {
            "p@market": True, "q@market": True, "r@market": True}})
        self.write_json(self.claude / "settings.local.json",
                        {"enabledPlugins": {"loc@market": True}})

    def tearDown(self):
        remove_tree(self.home)

    @staticmethod
    def write_json(path, obj):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj), encoding="utf-8")

    @staticmethod
    def skill_md(path, name):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\nname: {name}\ndescription: test skill\n---\nbody\n", encoding="utf-8")

    def user_skill(self, name):
        self.skill_md(self.claude / "skills" / name / "SKILL.md", name)

    def transcript(self, lines, name="s1.jsonl", mtime_days_ago=None):
        path = self.claude / "projects" / "proj" / name
        text = "\n".join(x if isinstance(x, str) else compact(x) for x in lines) + "\n"
        path.write_text(text, encoding="utf-8")
        if mtime_days_ago is not None:
            t = time.time() - mtime_days_ago * 86400
            os.utime(path, (t, t))
        return path

    def run_script(self, days=30):
        p = subprocess.run([sys.executable, str(SCRIPT), "--days", str(days), "--home", str(self.home)],
                           capture_output=True, timeout=60)
        out = p.stdout.decode("utf-8", "replace") + p.stderr.decode("utf-8", "replace")
        self.assertEqual(p.returncode, 0, out)
        return out

    @staticmethod
    def sections(out):
        used, zero, mode = {}, set(), None
        for line in out.splitlines():
            if line.startswith("Used"):
                mode = "used"
            elif line.startswith("Installed, zero uses"):
                mode = "zero"
            elif line.startswith("  ") and mode == "used":
                left, _, name = line.strip().rpartition(" ")
                c, _, t = left.partition("/")
                used[name] = (int(c), int(t))
            elif line.startswith("  ") and mode == "zero":
                zero.add(line.split()[1])
        return used, zero


class TestEventWindow(Home):
    """Finding 6: events count by their own timestamp, not file mtime."""

    def test_old_event_in_recent_file_is_not_counted(self):
        self.transcript([call("p:alpha", "2020-01-01T00:00:00.000Z")])
        used, zero = self.sections(self.run_script())
        self.assertNotIn("p:alpha", used)
        self.assertIn("p:alpha", zero)

    def test_oldest_event_date_is_reported(self):
        ts = iso(days_ago=3)
        self.transcript([call("p:alpha", ts)])
        out = self.run_script()
        self.assertIn(f"oldest event counted: {ts[:10]}", out)

    def test_file_last_written_before_window_is_not_opened(self):
        # Documented limit: transcripts are append-only, so the mtime pre-filter
        # stays; a copied or restored file with an old mtime is missed.
        self.transcript([call("p:alpha", iso(1))], mtime_days_ago=40)
        used, zero = self.sections(self.run_script())
        self.assertIn("p:alpha", zero)

    def test_docstring_explains_mtime_prefilter(self):
        doc = ast.get_docstring(ast.parse(SCRIPT.read_text(encoding="utf-8")))
        flat = " ".join(doc.split())
        self.assertIn("Claude Code appends to transcripts", flat)
        self.assertIn("a copied or restored file with an old mtime would be missed", flat)


class TestStructuredParse(Home):
    """Finding 7: parse message structure and roles, not byte shapes."""

    def test_spaced_json_and_args_first_are_counted(self):
        self.transcript([
            json.dumps(call("p:alpha", iso(1))),                  # spaces after : and ,
            compact(call("r:beta", iso(1), args_first=True)),     # args before skill
        ])
        used, zero = self.sections(self.run_script())
        self.assertEqual(used.get("p:alpha"), (1, 0))
        self.assertEqual(used.get("r:beta"), (1, 0))
        self.assertNotIn("p:alpha", zero)
        self.assertNotIn("r:beta", zero)

    def test_command_quoted_by_assistant_is_not_typed(self):
        self.transcript([assistant_text("<command-name>/beta</command-name>", iso(1))])
        used, zero = self.sections(self.run_script())
        self.assertNotIn("beta", used)
        self.assertIn("r:beta", zero)

    def test_command_inside_tool_output_is_not_typed(self):
        self.transcript([tool_result("<command-name>/beta</command-name>", iso(1))])
        used, zero = self.sections(self.run_script())
        self.assertNotIn("beta", used)
        self.assertIn("r:beta", zero)

    def test_typed_command_from_user_is_counted(self):
        self.transcript([typed("solo", iso(1)), typed("r:beta", iso(1))])
        used, zero = self.sections(self.run_script())
        self.assertEqual(used.get("solo"), (0, 1))
        self.assertEqual(used.get("r:beta"), (0, 1))
        self.assertNotIn("solo", zero)
        self.assertNotIn("r:beta", zero)

    def test_repeated_tool_use_id_counts_once(self):
        ev = call("p:alpha", iso(1), tid="toolu_same")
        self.transcript([ev])
        self.transcript([ev], name="s1-copy.jsonl")
        used, _ = self.sections(self.run_script())
        self.assertEqual(used.get("p:alpha"), (1, 0))


class TestQualifiedNames(Home):
    """Finding 8: exact qualified names; bare typed names only when unique."""

    def test_same_short_name_in_two_plugins(self):
        self.transcript([call("p:alpha", iso(1))])
        used, zero = self.sections(self.run_script())
        self.assertNotIn("p:alpha", zero)
        self.assertIn("q:alpha", zero)

    def test_ambiguous_bare_typed_name_matches_neither(self):
        self.transcript([typed("alpha", iso(1))])
        _, zero = self.sections(self.run_script())
        self.assertIn("p:alpha", zero)
        self.assertIn("q:alpha", zero)

    def test_unique_bare_typed_name_matches_plugin_skill(self):
        self.transcript([typed("beta", iso(1))])
        _, zero = self.sections(self.run_script())
        self.assertNotIn("r:beta", zero)


class TestPluginScope(Home):
    """Finding 9 (partial): only ~/.claude/settings.json enables plugins."""

    def test_settings_local_is_not_read_as_global(self):
        out = self.run_script()
        self.assertNotIn("loc:gamma", out)
        _, zero = self.sections(out)
        self.assertIn("p:alpha", zero)
        self.assertIn("solo", zero)

    def test_docstring_states_inventory_limits(self):
        doc = ast.get_docstring(ast.parse(SCRIPT.read_text(encoding="utf-8")))
        for phrase in ("project", "managed", "manifest", "/skill-doctor"):
            self.assertIn(phrase, doc)


class TestTypedWrapper(Home):
    """Round 2, still open 7: a typed command is a user message that opens with the wrapper."""

    def user_text(self, text, as_blocks=False):
        content = [{"type": "text", "text": text}] if as_blocks else text
        return {"type": "user", "timestamp": iso(1), "uuid": str(uuid.uuid4()),
                "message": {"role": "user", "content": content}}

    def test_tag_inside_user_prose_is_not_typed(self):
        self.transcript([self.user_text("please look at <command-name>/r:beta</command-name> here")])
        used, zero = self.sections(self.run_script())
        self.assertNotIn("r:beta", used)
        self.assertIn("r:beta", zero)

    def test_wrapper_with_message_first_and_whitespace_is_typed(self):
        self.transcript([
            self.user_text("\n  <command-message>beta is running</command-message>\n"
                           "<command-name>/r:beta</command-name>\n<command-args></command-args>"),
            self.user_text("<command-name>/solo</command-name>", as_blocks=True),
        ])
        used, zero = self.sections(self.run_script())
        self.assertEqual(used.get("r:beta"), (0, 1))
        self.assertEqual(used.get("solo"), (0, 1))


class TestFrontmatter(Home):
    """Round 2, N5: top-level keys only, inline comments and quotes stripped, YAML booleans."""

    def parse(self, body):
        path = self.home / "fm" / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\n" + body + "---\nbody\n", encoding="utf-8")
        return load_module().frontmatter(path)

    def test_comment_nested_key_and_true_comment(self):
        got = self.parse("name: alpha # human note\ndescription: x\nmetadata:\n  name: beta\n"
                         "disable-model-invocation: true # typed only\n")
        self.assertEqual(got, ("alpha", False))

    def test_boolean_spellings(self):
        for v in ("yes", "On", "1", "TRUE", "'true'"):
            with self.subTest(v=v):
                self.assertEqual(self.parse(f"name: s\ndisable-model-invocation: {v}\n"), ("s", False))
        for v in ("false", "no", "0", "off"):
            with self.subTest(v=v):
                self.assertEqual(self.parse(f"name: s\ndisable-model-invocation: {v}\n"), ("s", True))

    def test_quoted_values_keep_hash(self):
        self.assertEqual(self.parse("name: 'quoted # kept'\n")[0], "quoted # kept")
        self.assertEqual(self.parse('name: "dq"  # note\n')[0], "dq")

    def test_inventory_uses_clean_name(self):
        path = self.claude / "skills" / "noted" / "SKILL.md"
        path.parent.mkdir(parents=True)
        path.write_text("---\nname: noted # human note\ndisable-model-invocation: yes\n---\n", encoding="utf-8")
        out = self.run_script()
        self.assertIn("user-invoked   noted  [user]", out)


class TestIncomplete(Home):
    """Round 2, N6: unreadable transcripts are listed and the run exits 3."""

    def run_inproc(self):
        mod = load_module()
        buf = io.StringIO()
        argv = ["skill_usage.py", "--days", "30", "--home", str(self.home)]
        with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(buf):
            try:
                code = mod.main()
            except SystemExit as e:
                code = e.code
        return code, buf.getvalue()

    def test_unreadable_transcript_exits_3(self):
        self.transcript([call("p:alpha", iso(1))])
        self.transcript([call("q:alpha", iso(1))], name="locked.jsonl")
        real = Path.read_bytes

        def fake(path):
            if path.name == "locked.jsonl":
                raise PermissionError(13, "Permission denied", str(path))
            return real(path)
        with mock.patch.object(Path, "read_bytes", fake):
            code, out = self.run_inproc()
        self.assertEqual(code, 3, out)
        self.assertIn("locked.jsonl", out)
        self.assertIn("INCOMPLETE: 1 transcripts unreadable - the zero-use list is not definitive", out)

    def test_unlistable_project_folder_exits_3(self):
        self.transcript([call("p:alpha", iso(1))])
        sealed = self.claude / "projects" / "sealed"
        sealed.mkdir()
        (sealed / "s.jsonl").write_text(compact(call("q:alpha", iso(1))) + "\n", encoding="utf-8")
        real = os.scandir

        def fake(path="."):
            if os.path.basename(os.fspath(path).rstrip("\\/")) == "sealed":
                raise PermissionError(13, "Permission denied", os.fspath(path))
            return real(path)
        with mock.patch("os.scandir", fake):
            code, out = self.run_inproc()
        self.assertEqual(code, 3, out)
        self.assertIn("sealed", out)
        self.assertIn("INCOMPLETE: 1 transcripts unreadable", out)

    def test_all_readable_exits_0(self):
        self.transcript([call("p:alpha", iso(1))])
        code, out = self.run_inproc()
        self.assertEqual(code, 0, out)
        self.assertNotIn("INCOMPLETE", out)


class TestTypedFirstBlock(Home):
    """Round 3: in list content only the first block, a text block opening with the wrapper, counts."""

    def user_blocks(self, *blocks):
        return {"type": "user", "timestamp": iso(1), "uuid": str(uuid.uuid4()),
                "message": {"role": "user", "content": list(blocks)}}

    def test_wrapper_in_second_block_is_not_typed(self):
        self.transcript([self.user_blocks(
            {"type": "text", "text": "some prose first"},
            {"type": "text", "text": "<command-name>/r:beta</command-name>"})])
        used, zero = self.sections(self.run_script())
        self.assertNotIn("r:beta", used)
        self.assertIn("r:beta", zero)

    def test_wrapper_after_non_text_first_block_is_not_typed(self):
        self.transcript([self.user_blocks(
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "AA=="}},
            {"type": "text", "text": "<command-name>/r:beta</command-name>"})])
        used, zero = self.sections(self.run_script())
        self.assertNotIn("r:beta", used)
        self.assertIn("r:beta", zero)

    def test_wrapper_in_first_block_is_typed(self):
        self.transcript([self.user_blocks(
            {"type": "text", "text": "<command-name>/r:beta</command-name>"},
            {"type": "text", "text": "more"})])
        used, _ = self.sections(self.run_script())
        self.assertEqual(used.get("r:beta"), (0, 1))


if __name__ == "__main__":
    unittest.main()
