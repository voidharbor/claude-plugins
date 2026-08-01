#!/usr/bin/env python3
"""Stop hook: decide whether this session just asked a question worth
surfacing, and if so, kick off a detached triage of it.

Fires on every Stop event in every session once installed, so the refusal
paths must stay cheap: read the registry entry Task 2's SessionStart hook
wrote, tail the transcript for the assistant's last message, and bail unless
it looks like a real question. When it does, this writes a small cooldown
marker under ~/.claude/lookout/, claims a lock directory (stealing a stale
one left by a crashed run), and spawns triage-and-push.py detached -- this
process never waits on it and never releases the lock itself.

Must print nothing on stdout (Stop stdout is injected into the session's
context) and must never fail loudly (a broken hook must not break Stop).
"""
import json, os, platform, subprocess, sys, time

STATE_DIR = os.path.expanduser("~/.claude/lookout")
REGISTRY_DIR = os.path.expanduser("~/.claude/session-registry")
COOLDOWN_S = 180
TAIL_BYTES = 65536
LOCK_STALE_S = 120


def last_assistant_text(transcript_path):
    """Text of the last assistant message in the transcript's tail, "" when
    there is none. Reads only the final TAIL_BYTES so this stays cheap even
    on multi-hundred-MB transcripts."""
    try:
        size = os.path.getsize(transcript_path)
        with open(transcript_path, "rb") as f:
            if size > TAIL_BYTES:
                f.seek(size - TAIL_BYTES)
                f.readline()  # drop the partial line the seek landed in
            data = f.read()
    except OSError:
        return ""
    for line in reversed(data.split(b"\n")):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if obj.get("type") != "assistant":
            continue
        try:
            content = obj["message"]["content"]
            return "".join(
                block.get("text", "") for block in content if block.get("type") == "text"
            )
        except Exception:
            return ""
    return ""


def should_triage(payload, env, sysname, registry_dir, state_dir):
    """Ordered guards, first refusal wins. Returns (True, "go") only when
    every guard clears, at which point the lock directory has already been
    claimed on this call's behalf -- triage-and-push.py releases it."""
    if env.get("LOOKOUT_TRIAGE"):
        return False, "triage-of-triage"
    if payload.get("stop_hook_active"):
        return False, "stop-hook-active"
    if sysname not in ("Darwin", "Linux"):
        return False, "platform"

    sid = payload.get("session_id")
    transcript_path = payload.get("transcript_path")
    if not sid or not transcript_path:
        return False, "no-session"

    try:
        with open(os.path.join(registry_dir, sid + ".json")) as f:
            reg = json.load(f)
    except Exception:
        return False, "no-pane"
    if not reg.get("pane_id"):
        return False, "no-pane"

    if "?" not in last_assistant_text(transcript_path):
        return False, "no-question"

    state_path = os.path.join(state_dir, sid + ".json")
    try:
        with open(state_path) as f:
            state = json.load(f)
    except Exception:
        state = None
    if state is not None:
        try:
            tsize = os.path.getsize(transcript_path)
        except OSError:
            tsize = 0
        still_cooling = (time.time() - state.get("at", 0)) < COOLDOWN_S
        no_new_text = tsize <= state.get("offset", 0)
        if still_cooling or no_new_text:
            return False, "cooldown"

    lock_path = os.path.join(state_dir, "lock")
    try:
        os.mkdir(lock_path)
    except FileExistsError:
        try:
            lock_age = time.time() - os.path.getmtime(lock_path)
        except OSError:
            lock_age = LOCK_STALE_S  # lock vanished mid-check; treat as stale
        if lock_age < LOCK_STALE_S:
            return False, "locked"
        try:
            os.rmdir(lock_path)
            os.mkdir(lock_path)
        except OSError:
            return False, "locked"

    return True, "go"


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    os.makedirs(STATE_DIR, exist_ok=True)
    ok, _why = should_triage(payload, os.environ, platform.system(), REGISTRY_DIR, STATE_DIR)
    if not ok:
        return

    sid = payload["session_id"]
    try:
        offset = os.path.getsize(payload["transcript_path"])
    except OSError:
        offset = 0
    with open(os.path.join(STATE_DIR, sid + ".json"), "w") as f:
        json.dump({"at": time.time(), "offset": offset}, f)

    subprocess.Popen(
        [sys.executable, os.path.join(os.path.dirname(__file__), "triage-and-push.py"),
         payload["session_id"]],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL, start_new_session=True,
        env={**os.environ, "LOOKOUT_TRIAGE": "1"},
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
