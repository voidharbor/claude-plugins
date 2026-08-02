import os, unittest

HERE = os.path.dirname(__file__)
CA = os.path.join(HERE, "..")
BUNDLE = os.path.join(HERE, "..", "..", "voidharbor")

# Every file the voidharbor bundle ships as a byte-for-byte copy of the
# c-assistant original. The bundle exists so ONE install gives the whole
# lane, hooks included; a drifted copy means two installs behave
# differently depending on which copy owns the session.
SYNCED = [
    ("hooks/hooks.json", "hooks/hooks.json"),
    ("scripts/register-session.py", "scripts/register-session.py"),
    ("scripts/needs-input-hook.py", "scripts/needs-input-hook.py"),
    ("scripts/push-card.py", "scripts/push-card.py"),
    ("scripts/triage-and-push.py", "scripts/triage-and-push.py"),
    ("scripts/triage-prompt.md", "scripts/triage-prompt.md"),
]


class BundleCopiesInSync(unittest.TestCase):
    def test_bundle_ships_identical_copies(self):
        for src_rel, dst_rel in SYNCED:
            src = os.path.join(CA, src_rel)
            dst = os.path.join(BUNDLE, dst_rel)
            with self.subTest(file=src_rel):
                self.assertTrue(os.path.exists(dst), f"bundle is missing {dst_rel}")
                with open(src, "rb") as a, open(dst, "rb") as b:
                    self.assertEqual(
                        a.read(), b.read(),
                        f"{dst_rel} drifted from the c-assistant original -- "
                        f"re-copy it (cp c-assistant/{src_rel} voidharbor/{dst_rel})",
                    )


if __name__ == "__main__":
    unittest.main()
