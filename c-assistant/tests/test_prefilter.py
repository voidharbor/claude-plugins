import importlib.util, json, os, tempfile, time, unittest

def load_mod():
    p = os.path.join(os.path.dirname(__file__), "..", "scripts", "needs-input-hook.py")
    spec = importlib.util.spec_from_file_location("needs_input_hook", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def write_transcript(dirpath, lines):
    p = os.path.join(dirpath, "t.jsonl")
    with open(p, "w") as f:
        for obj in lines:
            f.write(json.dumps(obj) + "\n")
    return p

def assistant(text):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}

class Prefilter(unittest.TestCase):
    def setUp(self):
        self.mod = load_mod()
        self.tmp = tempfile.TemporaryDirectory()
        self.reg = os.path.join(self.tmp.name, "reg"); os.makedirs(self.reg)
        self.state = os.path.join(self.tmp.name, "state"); os.makedirs(self.state)

    def payload(self, transcript):
        sid = "abc123"
        with open(os.path.join(self.reg, sid + ".json"), "w") as f:
            json.dump({"session_id": sid, "pane_id": "pane-1"}, f)
        return {"session_id": sid, "transcript_path": transcript}

    def test_question_goes(self):
        t = write_transcript(self.tmp.name, [assistant("Should I ship it?")])
        ok, why = self.mod.should_triage(self.payload(t), {}, "Darwin", self.reg, self.state)
        self.assertTrue(ok, why)

    def test_no_question_refused(self):
        t = write_transcript(self.tmp.name, [assistant("All done. Committed.")])
        ok, why = self.mod.should_triage(self.payload(t), {}, "Darwin", self.reg, self.state)
        self.assertEqual((ok, why), (False, "no-question"))

    def test_env_marker_refused(self):
        t = write_transcript(self.tmp.name, [assistant("Ship it?")])
        ok, why = self.mod.should_triage(self.payload(t), {"LOOKOUT_TRIAGE": "1"}, "Darwin", self.reg, self.state)
        self.assertEqual((ok, why), (False, "triage-of-triage"))

    def test_windows_refused(self):
        t = write_transcript(self.tmp.name, [assistant("Ship it?")])
        ok, why = self.mod.should_triage(self.payload(t), {}, "Windows", self.reg, self.state)
        self.assertEqual((ok, why), (False, "platform"))

    def test_no_pane_refused(self):
        t = write_transcript(self.tmp.name, [assistant("Ship it?")])
        payload = {"session_id": "nope", "transcript_path": t}
        ok, why = self.mod.should_triage(payload, {}, "Darwin", self.reg, self.state)
        self.assertEqual((ok, why), (False, "no-pane"))

    def test_cooldown_refused_until_transcript_grows(self):
        t = write_transcript(self.tmp.name, [assistant("Ship it?")])
        p = self.payload(t)
        with open(os.path.join(self.state, "abc123.json"), "w") as f:
            json.dump({"at": time.time(), "offset": os.path.getsize(t)}, f)
        ok, why = self.mod.should_triage(p, {}, "Darwin", self.reg, self.state)
        self.assertEqual((ok, why), (False, "cooldown"))

    def test_last_assistant_text_takes_the_last_one(self):
        t = write_transcript(self.tmp.name, [assistant("first?"), {"type": "user"}, assistant("second — no q")])
        self.assertIn("second", self.mod.last_assistant_text(t))

if __name__ == "__main__":
    unittest.main()
