#!/usr/bin/env python3
"""SessionStart hook: record this session's (id, pid, tty, app) in
~/.claude/session-registry/ so session-scan.py can tell live terminal
sessions apart from dead transcripts. Ships with the c-assistant plugin;
a personal copy may also run — the write is idempotent.

Fires on startup, resume, /clear, and compact -- so a long-lived window
re-registers itself whenever its session id changes. Writes one small JSON
file per session id. Entries for dead processes are ignored by consumers and
overwritten when a session re-registers.

Must print nothing on stdout (SessionStart stdout is injected into the
session's context) and must never fail loudly (a broken registry hook must
not break session start).
"""
import json, os, subprocess, sys, time

REG = os.path.expanduser("~/.claude/session-registry")


def ps_field(pid, field):
    try:
        return subprocess.run(
            ["ps", "-p", str(pid), "-o", field + "="],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
    except Exception:
        return ""


def find_claude_ancestor():
    """Walk up from our parent to the claude process that spawned this hook.
    There may be an intermediate `zsh -c python3 .../register-session.py`
    whose command line contains '.claude' -- skip anything mentioning the
    script itself before matching on 'claude'."""
    pid = os.getppid()
    for _ in range(6):
        if pid <= 1:
            return None
        cmd = ps_field(pid, "command")
        if "claude" in cmd and "register-session" not in cmd:
            return pid
        ppid = ps_field(pid, "ppid")
        if not ppid.isdigit():
            return None
        pid = int(ppid)
    return None


def main():
    if os.environ.get("LOOKOUT_TRIAGE"):
        return  # headless triage must not register a ghost session pointing at the original pane
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    sid = data.get("session_id")
    if not sid:
        return
    claude_pid = find_claude_ancestor() or os.getppid()
    tty = ps_field(claude_pid, "tty") or "??"
    if os.environ.get("SEASHELL_PANE_ID"):
        app = "SeaShell"
    else:
        app = os.environ.get("TERM_PROGRAM") or "unknown"
    os.makedirs(REG, exist_ok=True)
    rec = {
        "session_id": sid,
        "pid": claude_pid,
        "tty": tty,
        "app": app,
        # SeaShell stamps this into every pane; it is how send-to-pane.py
        # addresses the control socket. Absent outside SeaShell -- and its
        # absence is itself a guard: no pane_id, no delivery.
        "pane_id": os.environ.get("SEASHELL_PANE_ID") or None,
        "cwd": data.get("cwd", ""),
        "transcript_path": data.get("transcript_path", ""),
        "source": data.get("source", ""),
        "registered_at": time.time(),
    }
    tmp = os.path.join(REG, f".{sid}.{os.getpid()}.tmp")
    with open(tmp, "w") as f:
        json.dump(rec, f)
    os.replace(tmp, os.path.join(REG, f"{sid}.json"))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
