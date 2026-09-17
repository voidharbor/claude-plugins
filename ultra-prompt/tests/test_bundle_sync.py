import os, re, unittest

HERE = os.path.dirname(__file__)
UP = os.path.join(HERE, "..")
ROOT = os.path.join(HERE, "..", "..")
BUNDLE = os.path.join(ROOT, "voidharbor")

# The voidharbor bundle ships a copy of every command, so one install gives the
# whole set. A drifted copy means two installs behave differently depending on
# which one the user happens to have.
SYNCED = [
    ("commands/ultra-prompt.md", "commands/ultra-prompt.md"),
    ("scripts/last-prompt.py", "scripts/last-prompt.py"),
]

# last-prompt.py is shared with the `refresh` plugin. Three copies exist and all
# three must stay identical, or a fix lands in one install and not the other.
SCRIPT_COPIES = [
    "ultra-prompt/scripts/last-prompt.py",
    "refresh/scripts/last-prompt.py",
    "voidharbor/scripts/last-prompt.py",
]


class BundleCopiesInSync(unittest.TestCase):
    def test_bundle_ships_identical_copies(self):
        for src_rel, dst_rel in SYNCED:
            src = os.path.join(UP, src_rel)
            dst = os.path.join(BUNDLE, dst_rel)
            with self.subTest(file=src_rel):
                self.assertTrue(os.path.exists(dst), f"bundle is missing {dst_rel}")
                with open(src, "rb") as a, open(dst, "rb") as b:
                    self.assertEqual(
                        a.read(), b.read(),
                        f"{dst_rel} drifted from the ultra-prompt original -- "
                        f"re-copy it (cp ultra-prompt/{src_rel} "
                        f"voidharbor/{dst_rel})",
                    )


class SharedScriptInSync(unittest.TestCase):
    def test_all_three_copies_are_identical(self):
        bodies = {}
        for rel in SCRIPT_COPIES:
            path = os.path.join(ROOT, rel)
            self.assertTrue(os.path.exists(path), f"missing {rel}")
            with open(path, "rb") as fh:
                bodies[rel] = fh.read()
        first = SCRIPT_COPIES[0]
        for rel in SCRIPT_COPIES[1:]:
            with self.subTest(file=rel):
                self.assertEqual(
                    bodies[rel], bodies[first],
                    f"{rel} drifted from {first} -- the two plugins share this "
                    f"script and all three copies must match",
                )


class SelfCommandIsRegistered(unittest.TestCase):
    """Without this entry, a bare /ultra-prompt improves the string
    "/ultra-prompt" instead of the prompt the user actually typed. It fails
    silently and looks like a model problem, so it gets its own test."""

    def test_ultra_prompt_skips_itself(self):
        for rel in SCRIPT_COPIES:
            with open(os.path.join(ROOT, rel)) as fh:
                body = fh.read()
            with self.subTest(file=rel):
                self.assertIn(
                    "/ultra-prompt", body.split("SELF_COMMANDS")[1].split("\n")[0],
                    f"{rel} does not list /ultra-prompt in SELF_COMMANDS",
                )


class ScriptIsSelfContained(unittest.TestCase):
    """The published copy must not leak the author's machine.

    Checked by pattern rather than by literal name, so the test itself does
    not publish the thing it exists to keep unpublished."""

    HOME_PATH = re.compile(r"(?:/Users|/home)/(?!<)[A-Za-z0-9._-]+")

    def test_no_hardcoded_home_directory(self):
        for rel in ("scripts/last-prompt.py", "commands/ultra-prompt.md",
                    "../voidharbor/scripts/last-prompt.py",
                    "../voidharbor/commands/ultra-prompt.md"):
            path = os.path.join(UP, rel)
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


if __name__ == "__main__":
    unittest.main()
