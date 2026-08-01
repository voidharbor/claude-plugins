import importlib.util, json, os, socket, tempfile, threading, unittest

def load_mod():
    p = os.path.join(os.path.dirname(__file__), "..", "scripts", "push-card.py")
    spec = importlib.util.spec_from_file_location("push_card", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

class FakeSocketServer:
    def __init__(self, reply):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "ctl.sock")
        self.received = []
        self.reply = reply
        self.srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.srv.bind(self.path)
        self.srv.listen(1)
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self):
        conn, _ = self.srv.accept()
        data = b""
        while b"\n" not in data:
            data += conn.recv(4096)
        self.received.append(json.loads(data.decode()))
        conn.sendall((json.dumps(self.reply) + "\n").encode())
        conn.close()

class PushCard(unittest.TestCase):
    def test_build_request_collapses_newlines_and_marks_dry_run(self):
        mod = load_mod()
        req = mod.build_request({"pane_id": "p1"}, "line one\nline two?", "a\nb", True)
        self.assertEqual(req["question"], "line one line two?")
        self.assertEqual(req["draft"], "a b")
        self.assertTrue(req["validateOnly"])
        self.assertEqual(req["cmd"], "card")
        self.assertIsNone(mod.build_request({"pane_id": "p1"}, "q?", "   ", False)["draft"])

    def test_deliver_round_trip(self):
        mod = load_mod()
        srv = FakeSocketServer({"ok": True})
        res = mod.deliver(srv.path, {"cmd": "card", "paneId": "p1", "question": "q?", "draft": None, "validateOnly": False})
        self.assertTrue(res["ok"])
        self.assertEqual(srv.received[0]["question"], "q?")

    def test_deliver_surfaces_refusal(self):
        mod = load_mod()
        srv = FakeSocketServer({"ok": False, "error": "unknown cmd"})
        res = mod.deliver(srv.path, {"cmd": "card", "paneId": "p1", "question": "q?", "draft": None, "validateOnly": False})
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"], "unknown cmd")

if __name__ == "__main__":
    unittest.main()
