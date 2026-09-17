import os, re, unittest

HERE = os.path.dirname(__file__)
RS = os.path.join(HERE, "..")
BUNDLE = os.path.join(HERE, "..", "..", "voidharbor")

# The voidharbor bundle ships a copy of every command, so one install gives the
# whole set. A drifted copy means two installs behave differently depending on
# which one the user happens to have.
SYNCED = [
    ("commands/rename-session.md", "commands/rename-session.md"),
    ("scripts/rename-session.py", "scripts/rename-session.py"),
]


class BundleCopiesInSync(unittest.TestCase):
    def test_bundle_ships_identical_copies(self):
        for src_rel, dst_rel in SYNCED:
            src = os.path.join(RS, src_rel)
            dst = os.path.join(BUNDLE, dst_rel)
            with self.subTest(file=src_rel):
                self.assertTrue(os.path.exists(dst), f"bundle is missing {dst_rel}")
                with open(src, "rb") as a, open(dst, "rb") as b:
                    self.assertEqual(
                        a.read(), b.read(),
                        f"{dst_rel} drifted from the rename-session original -- "
                        f"re-copy it (cp rename-session/{src_rel} "
                        f"voidharbor/{dst_rel})",
                    )


class ScriptIsSelfContained(unittest.TestCase):
    """The published copy must not leak the author's machine.

    Checked by pattern rather than by literal name, so the test itself does
    not publish the thing it exists to keep unpublished."""

    HOME_PATH = re.compile(r"(?:/Users|/home)/(?!<)[A-Za-z0-9._-]+")

    def test_no_hardcoded_home_directory(self):
        for rel in ("scripts/rename-session.py", "commands/rename-session.md",
                    "../voidharbor/scripts/rename-session.py",
                    "../voidharbor/commands/rename-session.md"):
            path = os.path.join(RS, rel)
            if not os.path.exists(path):
                continue
            with open(path) as fh:
                body = fh.read()
            with self.subTest(file=rel):
                hits = self.HOME_PATH.findall(body)
                self.assertEqual(
                    hits, [],
                    f"{rel} hardcodes a home directory {hits} -- use "
                    f"os.path.expanduser('~/...') so it runs on any machine",
                )


class RenameStillWrites(unittest.TestCase):
    """The rename is only real if BOTH writes land. The sidecar alone does not
    survive, and the transcript line alone is not what every picker reads."""

    def test_writes_transcript_line_and_sidecar(self):
        import json, subprocess, sys, tempfile, pathlib
        script = os.path.abspath(os.path.join(RS, "scripts", "rename-session.py"))
        with tempfile.TemporaryDirectory() as tmp:
            sid = "11111111-2222-3333-4444-555555555555"
            proj = pathlib.Path(tmp) / ".claude" / "projects" / "demo"
            proj.mkdir(parents=True)
            (proj / f"{sid}.jsonl").write_text('{"type":"user"}\n')
            env = dict(os.environ, HOME=tmp, CLAUDE_CODE_SESSION_ID=sid)
            out = subprocess.run([sys.executable, script, "CHECKOUT RETRY BUG"],
                                 env=env, capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)

            lines = (proj / f"{sid}.jsonl").read_text().strip().split("\n")
            rec = json.loads(lines[-1])
            self.assertEqual(rec["type"], "custom-title")
            self.assertEqual(rec["customTitle"], "CHECKOUT RETRY BUG")
            self.assertEqual(rec["sessionId"], sid)

            sidecar = json.loads((proj / sid / "custom-title.json").read_text())
            self.assertEqual(sidecar["customTitle"], "CHECKOUT RETRY BUG")


if __name__ == "__main__":
    unittest.main()
