import importlib.util
import json
import os
import tempfile
import time
import unittest
from unittest import mock


def load():
    p = os.path.join(os.path.dirname(__file__), "..", "scripts", "needs-input-hook.py")
    spec = importlib.util.spec_from_file_location("needs_input_hook", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class LockClaim(unittest.TestCase):
    """The triage lock is a directory under the state dir: mkdir acquires,
    triage-and-push.py releases, and a crashed run's leftover is stolen once
    it is older than LOCK_STALE_S. Stealing is the dangerous part: it must
    never remove a lock a PEER just legitimately acquired, or two triages run
    for one Stop burst and the lock protected nothing."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state_dir = os.path.join(self.tmp.name, "lookout")
        self.registry_dir = os.path.join(self.tmp.name, "session-registry")
        os.makedirs(self.state_dir)
        os.makedirs(self.registry_dir)
        self.lock_path = os.path.join(self.state_dir, "lock")

        self.sid = "11111111-2222-3333-4444-555555555555"
        self.transcript = os.path.join(self.tmp.name, "t.jsonl")
        with open(self.transcript, "w") as f:
            f.write(json.dumps({
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Ship it?"}]},
            }) + "\n")
        with open(os.path.join(self.registry_dir, self.sid + ".json"), "w") as f:
            json.dump({"pane_id": "pane-7"}, f)
        self.payload = {"session_id": self.sid, "transcript_path": self.transcript}

    def tearDown(self):
        self.tmp.cleanup()

    def run_entrant(self, mod):
        return mod.should_triage(self.payload, {}, "Darwin", self.registry_dir, self.state_dir)

    def make_stale_lock(self, mod):
        os.mkdir(self.lock_path)
        old = time.time() - mod.LOCK_STALE_S - 60
        os.utime(self.lock_path, (old, old))
        return old

    def test_fresh_lock_refuses(self):
        mod = load()
        os.mkdir(self.lock_path)  # held by a live triage right now
        self.assertEqual(self.run_entrant(mod), (False, "locked"))
        self.assertTrue(os.path.isdir(self.lock_path))

    def test_stale_lock_is_stolen(self):
        mod = load()
        self.make_stale_lock(mod)
        self.assertEqual(self.run_entrant(mod), (True, "go"))
        # The thief holds a FRESH lock now.
        self.assertTrue(os.path.isdir(self.lock_path))
        self.assertLess(time.time() - os.path.getmtime(self.lock_path), 5)

    def test_steal_never_destroys_a_freshly_acquired_lock(self):
        """Two entrants both observe the same crashed-run stale lock. C steals
        it and holds; D's stat raced ahead of C's steal, so D still believes
        the lock is stale. D must back off — with an rmdir+mkdir steal, D's
        rmdir lands on C's brand-new lock and BOTH entrants proceed, which is
        the exact double-triage the lock exists to prevent."""
        mod = load()
        observed_before_steal = self.make_stale_lock(mod)

        # Entrant C: legitimate steal. Holds a fresh lock from here on.
        self.assertEqual(self.run_entrant(mod), (True, "go"))
        self.assertTrue(os.path.isdir(self.lock_path))

        # Entrant D: judged staleness from a stat taken BEFORE C's steal. Only
        # the shared lock path lies to D — anything D inspects that C cannot
        # still be racing on (a name D owns exclusively) reports the truth.
        real_getmtime = os.path.getmtime

        def pre_steal_view(path):
            if os.path.normpath(path) == os.path.normpath(self.lock_path):
                return observed_before_steal
            return real_getmtime(path)

        with mock.patch("os.path.getmtime", side_effect=pre_steal_view):
            verdict = self.run_entrant(mod)

        self.assertEqual(verdict, (False, "locked"))
        # C's lock survived D's attempt and is still the fresh one.
        self.assertTrue(os.path.isdir(self.lock_path))
        self.assertLess(time.time() - real_getmtime(self.lock_path), 5)
        # And D left no debris behind in the state dir.
        self.assertEqual(sorted(os.listdir(self.state_dir)), ["lock"])


if __name__ == "__main__":
    unittest.main()
