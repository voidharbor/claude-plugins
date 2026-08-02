import importlib.util, json, os, tempfile, time, unittest


def load(name, filename):
    p = os.path.join(os.path.dirname(__file__), "..", "scripts", filename)
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_entry(reg, sid, pid, pane_id="pane-1", tty="ttys004", age_s=0):
    rec = {
        "session_id": sid, "pid": pid, "tty": tty, "app": "SeaShell",
        "pane_id": pane_id, "cwd": "/tmp", "transcript_path": "",
        "source": "startup", "registered_at": time.time() - age_s,
    }
    with open(os.path.join(reg, sid + ".json"), "w") as f:
        json.dump(rec, f)
    return rec


class PruneDeadEntries(unittest.TestCase):
    """register-session.py must prune entries whose process is gone —
    measured 2026-08-02: 55 of 68 entries carried dead pids after one day."""

    def test_prunes_dead_keeps_live_and_own(self):
        mod = load("register_session", "register-session.py")
        with tempfile.TemporaryDirectory() as reg:
            write_entry(reg, "dead-one", pid=999999991)
            write_entry(reg, "dead-two", pid=999999992)
            write_entry(reg, "live-one", pid=os.getpid())
            write_entry(reg, "own-sid", pid=999999993)  # dead pid but it is ours
            mod.prune_dead_entries(reg, live_pids={str(os.getpid())}, keep_sid="own-sid")
            left = sorted(os.listdir(reg))
            self.assertEqual(left, ["live-one.json", "own-sid.json"])

    def test_prunes_unreadable_entries(self):
        mod = load("register_session", "register-session.py")
        with tempfile.TemporaryDirectory() as reg:
            with open(os.path.join(reg, "garbage.json"), "w") as f:
                f.write("not json")
            write_entry(reg, "live-one", pid=os.getpid())
            mod.prune_dead_entries(reg, live_pids={str(os.getpid())}, keep_sid="live-one")
            self.assertEqual(sorted(os.listdir(reg)), ["live-one.json"])

    def test_never_raises_on_a_vanishing_dir(self):
        mod = load("register_session", "register-session.py")
        mod.prune_dead_entries("/nonexistent/registry", live_pids=set(), keep_sid="x")


class ResolveAmongLiveEntries(unittest.TestCase):
    """push-card.py prefix resolution must not be blocked or misled by dead
    entries: a prefix shared with a dead entry is not ambiguous, and a dead
    entry alone is not a hit."""

    def test_dead_entry_does_not_make_prefix_ambiguous(self):
        mod = load("push_card", "push-card.py")
        with tempfile.TemporaryDirectory() as reg:
            write_entry(reg, "abc-dead", pid=999999991)
            live = write_entry(reg, "abc-live", pid=os.getpid())
            rec, err = mod.resolve_session(reg, "abc", is_live=lambda pid: pid == os.getpid())
            self.assertIsNone(err)
            self.assertEqual(rec["session_id"], live["session_id"])

    def test_only_dead_entries_is_a_miss(self):
        mod = load("push_card", "push-card.py")
        with tempfile.TemporaryDirectory() as reg:
            write_entry(reg, "abc-dead", pid=999999991)
            rec, err = mod.resolve_session(reg, "abc", is_live=lambda pid: False)
            self.assertIsNone(rec)
            self.assertIn("gone", err)

    def test_two_live_entries_is_ambiguous(self):
        mod = load("push_card", "push-card.py")
        with tempfile.TemporaryDirectory() as reg:
            write_entry(reg, "abc-one", pid=os.getpid())
            write_entry(reg, "abc-two", pid=os.getpid())
            rec, err = mod.resolve_session(reg, "abc", is_live=lambda pid: True)
            self.assertIsNone(rec)
            self.assertIn("ambiguous", err)

    def test_no_prefix_match_is_a_miss(self):
        mod = load("push_card", "push-card.py")
        with tempfile.TemporaryDirectory() as reg:
            rec, err = mod.resolve_session(reg, "zzz", is_live=lambda pid: True)
            self.assertIsNone(rec)
            self.assertIn("no live session", err)


class RequestCarriesTty(unittest.TestCase):
    """The card request must carry the registered tty so SeaShell can refuse
    a stale pane id reused by a different pane in a newer run."""

    def test_build_request_includes_registered_tty(self):
        mod = load("push_card", "push-card.py")
        req = mod.build_request(
            {"pane_id": "p1", "tty": "ttys004"}, "ok?", None, False
        )
        self.assertEqual(req["tty"], "ttys004")

    def test_unknown_tty_is_omitted(self):
        mod = load("push_card", "push-card.py")
        req = mod.build_request({"pane_id": "p1", "tty": "??"}, "ok?", None, False)
        self.assertIsNone(req.get("tty"))
        req2 = mod.build_request({"pane_id": "p1"}, "ok?", None, False)
        self.assertIsNone(req2.get("tty"))


if __name__ == "__main__":
    unittest.main()
