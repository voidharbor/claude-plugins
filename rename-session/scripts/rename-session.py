#!/usr/bin/env python3
"""Rename the current Claude Code session. Usage: rename-session.py "NEW TITLE"

Writes the title the same two places the app itself writes on a rename:
  1. a {"type":"custom-title",...} line appended to the session transcript .jsonl
  2. the <project>/<session-id>/custom-title.json sidecar
Session is identified by $CLAUDE_CODE_SESSION_ID, never by newest mtime.
"""
import glob, json, os, sys

def main():
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        sys.exit("usage: rename-session.py \"NEW TITLE\"")
    title = " ".join(sys.argv[1:]).strip()
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if not sid:
        sys.exit("CLAUDE_CODE_SESSION_ID not set: run this from inside a Claude Code session")
    paths = glob.glob(os.path.expanduser(f"~/.claude/projects/*/{sid}.jsonl"))
    if len(paths) != 1:
        sys.exit(f"expected exactly 1 transcript for {sid}, found {len(paths)}: {paths}")
    transcript = paths[0]
    compact = {"separators": (",", ":")}  # match the app's byte format exactly
    with open(transcript, "a") as f:
        f.write(json.dumps({"type": "custom-title", "customTitle": title, "sessionId": sid}, **compact) + "\n")
    sidecar_dir = transcript[: -len(".jsonl")]
    os.makedirs(sidecar_dir, exist_ok=True)
    with open(os.path.join(sidecar_dir, "custom-title.json"), "w") as f:
        json.dump({"customTitle": title}, f, **compact)
    print(f"renamed session {sid[:8]} -> {title}")

if __name__ == "__main__":
    main()
