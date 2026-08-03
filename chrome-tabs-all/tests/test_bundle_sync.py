import os, re, unittest

HERE = os.path.dirname(__file__)
CTA = os.path.join(HERE, "..")
BUNDLE = os.path.join(HERE, "..", "..", "voidharbor")

# Every file the voidharbor bundle ships as a byte-for-byte copy of the
# chrome-tabs-all original. The bundle exists so ONE install gives the whole
# set; a drifted copy means two installs behave differently depending on
# which one the user happens to have.
SYNCED = [
    ("commands/chrome-tabs-all.md", "commands/chrome-tabs-all.md"),
    ("scripts/chrome-groups.py", "scripts/chrome-groups.py"),
]


class BundleCopiesInSync(unittest.TestCase):
    def test_bundle_ships_identical_copies(self):
        for src_rel, dst_rel in SYNCED:
            src = os.path.join(CTA, src_rel)
            dst = os.path.join(BUNDLE, dst_rel)
            with self.subTest(file=src_rel):
                self.assertTrue(os.path.exists(dst), f"bundle is missing {dst_rel}")
                with open(src, "rb") as a, open(dst, "rb") as b:
                    self.assertEqual(
                        a.read(), b.read(),
                        f"{dst_rel} drifted from the chrome-tabs-all original -- "
                        f"re-copy it (cp chrome-tabs-all/{src_rel} "
                        f"voidharbor/{dst_rel})",
                    )


class ScriptIsSelfContained(unittest.TestCase):
    """The published copy must not leak the author's machine.

    Checked by pattern rather than by literal name, so the test itself does
    not publish the thing it exists to keep unpublished."""

    HOME_PATH = re.compile(r"(?:/Users|/home)/(?!<)[A-Za-z0-9._-]+")

    def test_no_hardcoded_home_directory(self):
        for rel in ("scripts/chrome-groups.py", "commands/chrome-tabs-all.md",
                    "../voidharbor/scripts/chrome-groups.py"):
            path = os.path.join(CTA, rel)
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
