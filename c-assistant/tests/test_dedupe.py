import importlib.util, io, json, os, sys, tempfile, unittest
from unittest import mock


def load():
    p = os.path.join(os.path.dirname(__file__), "..", "scripts", "needs-input-hook.py")
    spec = importlib.util.spec_from_file_location("needs_input_hook", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f)


STANDALONE_SCRIPT = "/x/cache/voidharbor/c-assistant/1.2.1/scripts/needs-input-hook.py"
BUNDLE_SCRIPT = "/x/cache/voidharbor/voidharbor/1.1.0/scripts/needs-input-hook.py"


class DuplicateHookCopy(unittest.TestCase):
    """The bundle ships the same hooks as standalone c-assistant. When both
    are installed, both copies fire on every Stop -- the dedupe must make the
    bundle copy a no-op so exactly one triage runs."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.plugins_file = os.path.join(self.tmp.name, "plugins", "installed_plugins.json")
        self.settings_file = os.path.join(self.tmp.name, "settings.json")

    def tearDown(self):
        self.tmp.cleanup()

    def both_installed(self, standalone_enabled=True):
        write_json(self.plugins_file, {"plugins": {
            "c-assistant@voidharbor": [{"installPath": "/x", "version": "1.2.1"}],
            "voidharbor@voidharbor": [{"installPath": "/y", "version": "1.1.0"}],
        }})
        write_json(self.settings_file, {"enabledPlugins": {
            "c-assistant@voidharbor": standalone_enabled,
            "voidharbor@voidharbor": True,
        }})

    def test_standalone_copy_never_defers(self):
        mod = load()
        self.both_installed()
        self.assertFalse(
            mod.duplicate_hook_copy(STANDALONE_SCRIPT, self.plugins_file, self.settings_file)
        )

    def test_bundle_copy_defers_when_standalone_is_installed_and_enabled(self):
        mod = load()
        self.both_installed()
        self.assertTrue(
            mod.duplicate_hook_copy(BUNDLE_SCRIPT, self.plugins_file, self.settings_file)
        )

    def test_bundle_copy_owns_when_standalone_absent(self):
        mod = load()
        write_json(self.plugins_file, {"plugins": {
            "voidharbor@voidharbor": [{"installPath": "/y", "version": "1.1.0"}],
        }})
        write_json(self.settings_file, {"enabledPlugins": {"voidharbor@voidharbor": True}})
        self.assertFalse(
            mod.duplicate_hook_copy(BUNDLE_SCRIPT, self.plugins_file, self.settings_file)
        )

    def test_bundle_copy_owns_when_standalone_disabled(self):
        # A disabled standalone fires no hooks; the bundle must not defer to
        # a copy that will never run, or the feature dies silently.
        mod = load()
        self.both_installed(standalone_enabled=False)
        self.assertFalse(
            mod.duplicate_hook_copy(BUNDLE_SCRIPT, self.plugins_file, self.settings_file)
        )

    def test_unreadable_manifests_mean_own_the_session(self):
        mod = load()
        self.assertFalse(
            mod.duplicate_hook_copy(BUNDLE_SCRIPT, self.plugins_file, self.settings_file)
        )


class TwoInvocationsOneTriage(unittest.TestCase):
    """The required end-to-end check: simulate the two hook invocations both
    copies produce for the SAME session id and Stop event, and count triage
    spawns per copy. The bundle copy runs FIRST and on a clean state — the
    ordering where the global lock and cooldown offer no protection at all —
    so this fails while the bundle copy fires and passes once the dedupe
    holds. Total across both invocations must still be exactly one."""

    def run_invocation(self, mod, script_path, payload):
        # The hook reads its own location via module-level SCRIPT_PATH so the
        # two installed copies are simulable in one process; override it.
        mod.SCRIPT_PATH = script_path
        with mock.patch.object(mod.sys, "stdin", io.StringIO(json.dumps(payload))):
            mod.main()

    def test_same_session_same_event_spawns_one_triage(self):
        mod = load()
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = os.path.join(tmp, "lookout")
            reg_dir = os.path.join(tmp, "session-registry")
            plugins_file = os.path.join(tmp, "plugins", "installed_plugins.json")
            settings_file = os.path.join(tmp, "settings.json")
            os.makedirs(state_dir)
            os.makedirs(reg_dir)
            write_json(plugins_file, {"plugins": {
                "c-assistant@voidharbor": [{"installPath": "/x", "version": "1.2.1"}],
                "voidharbor@voidharbor": [{"installPath": "/y", "version": "1.1.0"}],
            }})
            write_json(settings_file, {"enabledPlugins": {
                "c-assistant@voidharbor": True, "voidharbor@voidharbor": True,
            }})

            sid = "sess-dedupe-1"
            transcript = os.path.join(tmp, "t.jsonl")
            with open(transcript, "w") as f:
                f.write(json.dumps({
                    "type": "assistant",
                    "message": {"content": [{"type": "text", "text": "Ship it now?"}]},
                }) + "\n")
            write_json(os.path.join(reg_dir, sid + ".json"), {
                "session_id": sid, "pid": os.getpid(), "pane_id": "pane-1",
            })

            mod.STATE_DIR = state_dir
            mod.REGISTRY_DIR = reg_dir
            mod.PLUGINS_FILE = plugins_file
            mod.SETTINGS_FILE = settings_file

            payload = {"session_id": sid, "transcript_path": transcript}
            spawns = []
            with mock.patch.object(mod.subprocess, "Popen", side_effect=lambda *a, **k: spawns.append(a)):
                self.run_invocation(mod, BUNDLE_SCRIPT, payload)
                self.assertEqual(
                    len(spawns), 0,
                    "the bundle copy fired its own triage — the dedupe is not holding",
                )
                self.run_invocation(mod, STANDALONE_SCRIPT, payload)

            self.assertEqual(
                len(spawns), 1,
                f"expected exactly one triage spawn for one Stop event, got {len(spawns)}",
            )


if __name__ == "__main__":
    unittest.main()
