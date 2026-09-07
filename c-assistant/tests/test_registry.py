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


if __name__ == "__main__":
    unittest.main()
