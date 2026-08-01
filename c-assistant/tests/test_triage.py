import importlib.util, json, os, stat, tempfile, unittest

def load_mod():
    p = os.path.join(os.path.dirname(__file__), "..", "scripts", "triage-and-push.py")
    spec = importlib.util.spec_from_file_location("triage_and_push", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

class TriageParse(unittest.TestCase):
    def test_parses_strict_json(self):
        mod = load_mod()
        out = mod.parse_triage_output('{"card": true, "question": "ship?", "draft": "yes"}')
        self.assertEqual(out["draft"], "yes")

    def test_parses_json_wrapped_in_noise(self):
        mod = load_mod()
        out = mod.parse_triage_output('Sure! {"card": false, "question": "x", "draft": null} done')
        self.assertFalse(out["card"])
        self.assertIsNone(out["draft"])

    def test_rejects_missing_keys_and_junk(self):
        mod = load_mod()
        self.assertIsNone(mod.parse_triage_output('{"card": true}'))
        self.assertIsNone(mod.parse_triage_output("no json at all"))

class TriageRun(unittest.TestCase):
    def test_run_triage_calls_claude_from_path(self):
        mod = load_mod()
        with tempfile.TemporaryDirectory() as d:
            shim = os.path.join(d, "claude")
            with open(shim, "w") as f:
                f.write('#!/bin/sh\necho \'{"card": true, "question": "q?", "draft": "ok"}\'\n')
            os.chmod(shim, os.stat(shim).st_mode | stat.S_IEXEC)
            env = {**os.environ, "PATH": d + os.pathsep + os.environ.get("PATH", ""), "LOOKOUT_TRIAGE": "1"}
            out = mod.run_triage("prompt text", env)
            self.assertIn('"card": true', out)

if __name__ == "__main__":
    unittest.main()
