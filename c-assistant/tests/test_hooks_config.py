import json, os, unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")

class HooksConfig(unittest.TestCase):
    def test_hooks_json_shape(self):
        with open(os.path.join(ROOT, "hooks", "hooks.json")) as f:
            cfg = json.load(f)
        hooks = cfg["hooks"]
        for event, script in [("SessionStart", "register-session.py"), ("Stop", "needs-input-hook.py")]:
            entries = hooks[event]
            self.assertEqual(len(entries), 1)
            cmd = entries[0]["hooks"][0]["command"]
            self.assertIn("${CLAUDE_PLUGIN_ROOT}", cmd)
            self.assertIn(script, cmd)
            self.assertTrue(cmd.startswith('python3 "'))

    def test_register_session_parses(self):
        import ast
        with open(os.path.join(ROOT, "scripts", "register-session.py")) as f:
            ast.parse(f.read())

if __name__ == "__main__":
    unittest.main()
