#!/usr/bin/env python3
"""Scan Claude Code session transcripts and report which ones are waiting on the user.

Usage:
  python3 ~/.claude/bin/session-scan.py [--hours 12] [--self <session-id>] [--full <session-id>]

Reads only the tail of each .jsonl transcript, so it is cheap even on the 70MB ones.
Prints one block per session: topic, state, the user's last message, the session's
last reply. The reading and judging is yours -- this just gets the text in front
of you without loading gigabytes into context.
"""
import json, os, re, sys, time, glob

PROJ = os.path.expanduser("~/.claude/projects")
TAIL_BYTES = 900_000
FULL_TAIL_BYTES = 4_000_000

ASK_PAT = re.compile(
    r"\?|(\bwant me to\b)|(\bshould i\b)|(\bwhich\b)|(\blet me know\b)|(\bsay the word\b)"
    r"|(\bwaiting on you\b)|(\byour call\b)|(\bconfirm\b)|(\btell me\b)|(\bsay \*\*)|(\bpick\b)"
    r"|(\byes or no\b)|(\bapprove\b)|(\bneeds? you\b)|(\bup to you\b)|(\bdo you want\b)",
    re.I | re.M,
)


def parse_tail(path, nbytes):
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        if size > nbytes:
            f.seek(size - nbytes)
            f.readline()
        data = f.read()
    recs = []
    for ln in data.split(b"\n"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            recs.append(json.loads(ln))
        except Exception:
            pass
    return recs


def text_of(o):
    m = o.get("message") or {}
    c = m.get("content")
    if isinstance(c, str):
        return c
    parts = []
    if isinstance(c, list):
        for b in c:
            if not isinstance(b, dict):
                continue
            t = b.get("type")
            if t == "text":
                parts.append(b.get("text", ""))
            elif t == "tool_use":
                parts.append(f"[tool:{b.get('name')}]")
            elif t == "tool_result":
                parts.append("[tool_result]")
    return "\n".join(parts)


def clean(t):
    t = re.sub(r"<system-reminder>.*?</system-reminder>", "", t, flags=re.S)
    t = re.sub(r"<local-command-[a-z]+>.*?</local-command-[a-z]+>", "", t, flags=re.S)
    return t.strip()


def first_user(path):
    """First real thing the user typed. Skips slash-command wrappers and /clear markers,
    which otherwise read as the session topic and tell you nothing."""
    with open(path, "rb") as f:
        for _ in range(1200):
            ln = f.readline()
            if not ln:
                break
            try:
                o = json.loads(ln)
            except Exception:
                continue
            if o.get("type") != "user":
                continue
            t = clean(text_of(o))
            if not t or "[tool_result]" in t or t.startswith("Caveat"):
                continue
            if t.lstrip().startswith("<command-") or t.lstrip().startswith("<local-command"):
                continue
            return " ".join(t.split())[:300]
    return "(opened with a slash command -- read the tail for the real topic)"


def scan(path, self_id, verbose=False):
    sid = os.path.basename(path)[:-6]
    if sid == self_id:
        return None
    recs = parse_tail(path, FULL_TAIL_BYTES if verbose else TAIL_BYTES)
    if not recs:
        return None
    mtime = os.path.getmtime(path)
    cwd = next((r["cwd"] for r in reversed(recs) if r.get("cwd")), "?")

    last_user = last_asst = ""
    last_asst_ts = ""
    interrupted = False
    for r in recs:
        typ = r.get("type")
        if typ == "user":
            t = clean(text_of(r))
            if not t or "[tool_result]" in t:
                continue
            if "[Request interrupted by user]" in t:
                interrupted = True
                continue
            interrupted = False
            last_user = t
        elif typ == "assistant":
            t = text_of(r)
            if t.strip() and not t.strip().startswith("[tool:"):
                last_asst, last_asst_ts = t, r.get("timestamp", "")
                interrupted = False

    age_min = (time.time() - mtime) / 60
    if interrupted:
        state = "INTERRUPTED mid-task -- needs a nudge to resume"
    elif ASK_PAT.search(last_asst[-900:]):
        state = "ASKED A QUESTION -- waiting on an answer"
    else:
        state = "idle, no explicit question"
    live = "LIVE" if age_min < 30 else ("recent" if age_min < 240 else "stale")

    n = 6000 if verbose else 2500
    return "\n".join([
        "=" * 96,
        f"{sid}  [{live}, last touched {age_min:.0f} min ago]  {os.path.getsize(path)/1e6:.1f}MB",
        f"  cwd:   {cwd}",
        f"  state: {state}",
        f"  topic: {first_user(path)}",
        f"  --- user's last message ---\n{last_user[-800:]}",
        f"  --- session's last reply ({last_asst_ts}) ---\n{last_asst[-n:]}",
        "",
    ])


def main():
    a = sys.argv[1:]
    hours = 12.0
    self_id = os.environ.get("CLAUDE_SESSION_ID", "")
    only = None
    i = 0
    while i < len(a):
        if a[i] == "--hours":
            hours = float(a[i + 1]); i += 2
        elif a[i] == "--self":
            self_id = a[i + 1]; i += 2
        elif a[i] == "--full":
            only = a[i + 1]; i += 2
        else:
            i += 1

    paths = glob.glob(os.path.join(PROJ, "*", "*.jsonl"))
    if only:
        paths = [p for p in paths if only in p]
        for p in paths:
            out = scan(p, "", verbose=True)
            if out:
                print(out)
        return

    cutoff = time.time() - hours * 3600
    paths = [p for p in paths if os.path.getmtime(p) > cutoff and os.path.getsize(p) > 2000]
    paths.sort(key=os.path.getmtime, reverse=True)
    print(f"# {len(paths)} transcript(s) touched in the last {hours:g}h "
          f"(scanned {time.strftime('%Y-%m-%d %H:%M %Z')})\n")
    for p in paths:
        out = scan(p, self_id)
        if out:
            print(out)


if __name__ == "__main__":
    main()
