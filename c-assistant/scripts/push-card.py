#!/usr/bin/env python3
"""Push a Lookout card -- a question, with an optional draft reply -- onto
the SeaShell pane running a given session.

    python3 push-card.py <session-id-prefix> --question TEXT [--draft TEXT] [--dry-run]

env:   SEASHELL_CONTROL_SOCKET overrides the socket path (default
       ~/Library/Application Support/seashell/control.sock on Darwin,
       ~/.config/seashell/control.sock on Linux)
prints DELIVERED/VALIDATED/REFUSED lines; exit 0 only on delivered/validated.

Guards on this side (the socket has its own):
  - registry entry must exist and carry a pane_id (SeaShell sessions only)
  - the registered claude process must still be alive
  - question and draft, once collapsed to a single line, must be non-empty
    (question only), free of control characters, and within the server's
    caps (question <= 2000 chars, draft <= 4000)

--dry-run sets validateOnly on the request instead of skipping it -- session
resolution, the live-pid check, and the socket round trip to the server all
still happen for real; only the on-screen card itself is skipped.
"""
import glob, json, os, platform, re, socket, subprocess, sys

REG = os.path.expanduser("~/.claude/session-registry")
DEFAULT_SOCK = (
    os.path.expanduser("~/Library/Application Support/seashell/control.sock")
    if platform.system() == "Darwin"
    else os.path.expanduser("~/.config/seashell/control.sock")
)
SOCK = os.environ.get("SEASHELL_CONTROL_SOCKET", DEFAULT_SOCK)
MAX_QUESTION = 2000
MAX_DRAFT = 4000
CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def one_line(text):
    return " ".join(text.split())


def is_claude_main(cmd):
    if not cmd:
        return False
    tok = cmd.split()[0]
    return os.path.basename(tok) == "claude" or "/share/claude/versions/" in tok


def build_request(rec, question, draft, dry_run):
    return {
        "cmd": "card",
        "paneId": rec["pane_id"],
        "question": one_line(question),
        "draft": one_line(draft) if draft is not None else None,
        "validateOnly": bool(dry_run),
    }


def deliver(sock_path, req):
    conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    conn.settimeout(10)
    conn.connect(sock_path)
    try:
        conn.sendall((json.dumps(req) + "\n").encode())
        raw = b""
        while b"\n" not in raw:
            chunk = conn.recv(4096)
            if not chunk:
                break
            raw += chunk
    finally:
        conn.close()
    return json.loads(raw.decode().strip() or "{}")


def die(msg):
    print(f"REFUSED: {msg}")
    sys.exit(1)


def parse_args(argv):
    """Hand-rolled, order-independent parsing: <prefix> plus --question TEXT
    (required), --draft TEXT (optional), --dry-run (flag). Returns None on
    anything malformed so main() can print usage and exit 2."""
    positional = []
    question = None
    draft = None
    dry_run = False
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--question":
            if i + 1 >= len(argv):
                return None
            question = argv[i + 1]
            i += 2
        elif arg == "--draft":
            if i + 1 >= len(argv):
                return None
            draft = argv[i + 1]
            i += 2
        elif arg == "--dry-run":
            dry_run = True
            i += 1
        else:
            positional.append(arg)
            i += 1
    if len(positional) != 1 or question is None:
        return None
    return positional[0], question, draft, dry_run


def main():
    parsed = parse_args(sys.argv[1:])
    if parsed is None:
        print(__doc__)
        sys.exit(2)
    prefix, question, draft, dry_run = parsed

    hits = [f for f in glob.glob(os.path.join(REG, "*.json"))
            if os.path.basename(f).startswith(prefix)]
    if not hits:
        die(f"no live session registered matching '{prefix}'")
    if len(hits) > 1:
        die(f"'{prefix}' is ambiguous ({len(hits)} sessions) -- use more characters")
    with open(hits[0]) as fh:
        rec = json.load(fh)

    if not rec.get("pane_id"):
        die("that session is not in a SeaShell pane -- it can never receive a card")

    cmd = subprocess.run(
        ["ps", "-p", str(rec.get("pid", -1)), "-o", "command="],
        capture_output=True, text=True,
    ).stdout.strip()
    if not is_claude_main(cmd):
        die("the session's claude process is gone (window closed or /clear'd)")

    req = build_request(rec, question, draft, dry_run)
    q, d = req["question"], req["draft"]
    if not q:
        die("empty question")
    if CONTROL.search(q) or (d and CONTROL.search(d)):
        die("question or draft has control characters")
    if len(q) > MAX_QUESTION:
        die(f"question too long ({len(q)} > {MAX_QUESTION} chars)")
    if d is not None and len(d) > MAX_DRAFT:
        die(f"draft too long ({len(d)} > {MAX_DRAFT} chars)")

    try:
        res = deliver(SOCK, req)
    except OSError:
        die("SeaShell's control socket isn't there -- SeaShell is not running, "
            "or is an older build without card support (relaunch on the new build)")
    except ValueError:
        die("garbled response from SeaShell")

    if res.get("ok"):
        if dry_run:
            print("VALIDATED: server accepted the card without creating it")
        else:
            sid = rec.get("session_id", prefix)
            print(f"DELIVERED: card pushed to {rec['pane_id']} (session {sid[:8]})")
        sys.exit(0)
    die(f"SeaShell refused: {res.get('error', 'no reason given')}")


if __name__ == "__main__":
    main()
