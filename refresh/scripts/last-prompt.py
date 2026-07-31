#!/usr/bin/env python3
"""Print the last prompt(s) the user actually typed, read verbatim from the transcript.

Usage:
  python3 last-prompt.py                # last prompt, this session
  python3 last-prompt.py -n 5           # last 5 prompts, this session
  python3 last-prompt.py --all          # last prompt from ANY session
  python3 last-prompt.py --all -n 5     # last 5 across all sessions
  python3 last-prompt.py --session <id> # a specific session

Why this exists rather than just scrolling back: after a long session the context
gets summarized, and the verbatim wording of what was asked can be gone from what
the model can see. The .jsonl on disk still has it exactly as typed.

What counts as "a prompt": anything the user sent by hand, including slash commands
(shown as "/name args"). Deliberately NOT counted: tool results, system-injected
messages, subagent chatter, command stdout, and /refresh itself -- otherwise
/refresh would just report /refresh.

Transcripts are only ever read, never written.
"""
import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime, timezone

PROJ = os.path.expanduser("~/.claude/projects")

# Tail sizes to try in order. Transcripts reach 55MB+ and a single prompt can sit
# behind a lot of tool output, so grow the window instead of guessing one size.
TAIL_STEPS = (1_000_000, 8_000_000, None)  # None = read the whole file

SYSTEM_REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
COMMAND_NAME = re.compile(r"<command-name>(.*?)</command-name>", re.S)
COMMAND_ARGS = re.compile(r"<command-args>(.*?)</command-args>", re.S)
# Wrappers the CLI writes into the user stream that the user never typed.
NOISE_TAGS = ("<local-command-stdout>", "<local-command-stderr>", "<bash-stdout>")

SELF_COMMANDS = {"/refresh"}


def read_records(path, nbytes):
    """Parse JSONL from the tail of a file. nbytes=None reads all of it."""
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        if nbytes is not None and size > nbytes:
            f.seek(size - nbytes)
            f.readline()  # drop the partial line we probably landed in
        data = f.read()
    out = []
    for line in data.split(b"\n"):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            pass  # a truncated first line is expected, and corrupt lines are not fatal
    return out


def raw_text(rec):
    """Flatten a user record's content to text, or return None if it is not typed input."""
    msg = rec.get("message") or {}
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if not isinstance(block, dict):
                continue
            # A tool_result anywhere means this record is the harness talking, not the user.
            if block.get("type") == "tool_result":
                return None
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts) if parts else None
    return None


def as_prompt(rec):
    """Return the prompt text the user typed, or None if this record is not one.

    Slash commands are normalised to "/name args" so they read the way they were typed.
    """
    if rec.get("type") != "user":
        return None
    if rec.get("isSidechain") or rec.get("isMeta"):
        return None

    text = raw_text(rec)
    if text is None:
        return None

    if any(tag in text for tag in NOISE_TAGS):
        return None

    name = COMMAND_NAME.search(text)
    if name:
        cmd = name.group(1).strip()
        if cmd in SELF_COMMANDS:
            return None  # never report the /refresh invocation as the answer
        args_match = COMMAND_ARGS.search(text)
        args = (args_match.group(1).strip() if args_match else "")
        return f"{cmd} {args}".strip()

    text = SYSTEM_REMINDER.sub("", text).strip()
    return text or None


def prompts_from(path, want, session_id):
    """Newest-first prompts from one transcript, growing the tail until we have enough."""
    for nbytes in TAIL_STEPS:
        try:
            recs = read_records(path, nbytes)
        except OSError:
            return []
        found = []
        for rec in reversed(recs):
            p = as_prompt(rec)
            if p:
                found.append((rec.get("timestamp", ""), session_id, p))
                if len(found) >= want:
                    return found
        # Whole file already read, or the tail covered the whole file anyway.
        if nbytes is None or os.path.getsize(path) <= nbytes:
            return found
    return found


def when(ts):
    """'12:09 PM, 42 minutes ago' from an ISO-8601 UTC stamp."""
    if not ts:
        return "unknown time"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()
    except ValueError:
        return ts
    delta = datetime.now(timezone.utc) - dt.astimezone(timezone.utc)
    secs = int(delta.total_seconds())
    if secs < 90:
        ago = f"{max(secs, 0)} seconds ago"
    elif secs < 5400:
        ago = f"{secs // 60} minutes ago"
    elif secs < 172800:
        ago = f"{secs // 3600} hours ago"
    else:
        ago = f"{secs // 86400} days ago"
    stamp = dt.strftime("%-I:%M %p")
    if secs >= 43200:
        stamp = dt.strftime("%a %-d %b, %-I:%M %p")
    return f"{stamp}, {ago}"


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("-n", type=int, default=1, help="how many prompts back (default 1)")
    ap.add_argument("--all", action="store_true",
                    help="search every session, not just this one")
    ap.add_argument("--session", help="a specific session id")
    args = ap.parse_args()
    want = max(1, args.n)

    sid = args.session or os.environ.get("CLAUDE_CODE_SESSION_ID", "")

    if args.all:
        paths = glob.glob(os.path.join(PROJ, "*", "*.jsonl"))
        if not paths:
            print(f"No transcripts found under {PROJ}.")
            return 1
        # Newest files first, and stop early: a prompt cannot be newer than its file.
        paths.sort(key=os.path.getmtime, reverse=True)
        collected = []
        for p in paths[:40]:
            collected.extend(prompts_from(p, want, os.path.basename(p)[:-6]))
        collected.sort(key=lambda t: t[0], reverse=True)
        rows = collected[:want]
        scope = "across all sessions"
    else:
        if not sid:
            print("Could not tell which session this is: CLAUDE_CODE_SESSION_ID is not set.")
            print("Re-run with --session <id>, or use --all to search every session.")
            return 1
        matches = glob.glob(os.path.join(PROJ, "*", f"{sid}.jsonl"))
        if not matches:
            print(f"No transcript on disk for session {sid}.")
            print("Use --all to search every session instead.")
            return 1
        rows = prompts_from(matches[0], want, sid)
        scope = f"this session ({sid[:8]})"

    if not rows:
        print(f"No earlier prompt found {scope} -- this looks like the first thing sent here.")
        return 0

    label = "Last prompt" if len(rows) == 1 else f"Last {len(rows)} prompts"
    print(f"{label} sent, {scope}:")
    for ts, session, text in rows:
        print()
        head = when(ts)
        if args.all:
            head += f"  [session {session[:8]}]"
        print(f"--- {head} ---")
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
