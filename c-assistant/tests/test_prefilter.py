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


class ImplicitAsks(Prefilter):
    """A turn can be blocked on the user without containing a question mark.

    Every string below is copied from a real transcript of a session that was
    sitting waiting while the literal-`?` prefilter refused it as "no-question"
    (surveyed across 43 real panes, 2026-08-02: the old gate passed 11, this
    one passes 13 — a real gain, but not the reason the plugin lane was silent).

    The prefilter is only a cost gate — triage-and-push.py runs the model and
    pushes a card only on `card: true` — so a false positive here costs one
    cheap call, while a false negative costs the entire feature.
    """

    def assertGoes(self, text):
        t = write_transcript(self.tmp.name, [assistant(text)])
        ok, why = self.mod.should_triage(self.payload(t), {}, "Darwin", self.reg, self.state)
        self.assertTrue(ok, "refused %r for %r" % (why, text[-60:]))

    def assertRefused(self, text):
        t = write_transcript(self.tmp.name, [assistant(text)])
        ok, why = self.mod.should_triage(self.payload(t), {}, "Darwin", self.reg, self.state)
        self.assertEqual((ok, why), (False, "no-question"))

    def test_just_say_go(self):
        self.assertGoes('Once you\'ve switched it, just say "go" and I\'ll start.')

    def test_if_you_tell_me(self):
        self.assertGoes("If you tell me where you saw the 2GB, I can pin it to the exact process.")

    def test_say_the_word(self):
        self.assertGoes("Say the word once it's on and I'll request again.")

    def test_want_me_to(self):
        self.assertGoes("Want me to start on the detector fix.")

    def test_let_me_know(self):
        self.assertGoes("Both routes work. Let me know which you'd prefer.")

    def test_your_call(self):
        self.assertGoes("I'd take the second one, but it's your call.")

    # --- and the refusals still have to hold ---

    def test_plain_completion_still_refused(self):
        self.assertRefused("All done. Committed and pushed.")

    def test_confirmed_is_not_a_request_to_confirm(self):
        self.assertRefused("Confirmed the fix works. Tests are green.")

    def test_told_in_past_tense_is_not_an_ask(self):
        self.assertRefused("I told the build to skip signing, and it did.")


if __name__ == "__main__":
    unittest.main()
