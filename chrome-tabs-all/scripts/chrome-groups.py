#!/usr/bin/env python3
"""Map every Chrome tab a Claude Code session opened, and close the orphans.

    python3 chrome-groups.py                  # report only, read-only
    python3 chrome-groups.py --close-orphans  # close dead sessions' tabs
    python3 chrome-groups.py --close-orphans --dry-run

macOS + Google Chrome only.

Why this can close another session's tabs when the MCP cannot
-------------------------------------------------------------
Chrome's AppleScript `id of tab` is the SAME integer the Claude in Chrome
extension reports as `tabId` (verified 2026-08-02). Every session's transcript
records its tab group as {"tabId":N,"url":...}. So an orphaned tab can be closed
by EXACT ID -- never guessed from a URL, which is the mistake that closes the
user's own tabs. Duplicate URLs across the user's tabs and Claude's tabs are the
normal case, not the edge case.

Two guards make the ID trustworthy:

  1. Chrome-run scoping. Tab IDs are unique only within one Chrome process run.
     Only transcript entries written AFTER Chrome started are read, so a stale
     ID from a previous run can never be matched against a recycled one.

  2. Conservative liveness. A session counts as dead only if its process is gone
     AND its transcript has been silent past the idle window. Either one saying
     "alive" keeps its tabs. A live session closes its own tabs with
     /chrome-tabs; this script never races it.

Process liveness comes from the session registry that the `c-assistant` plugin
maintains (~/.claude/session-registry). WITHOUT that registry there is no way to
map a running claude process back to a session id, so liveness degrades to
transcript mtime alone and the idle window automatically widens to
IDLE_NO_REGISTRY minutes. The script says so when it happens.

Tabs no session claims belong to the user and are never touched.
"""

import argparse, glob, json, os, re, subprocess, sys, time
from datetime import datetime, timezone

PROJ = os.path.expanduser("~/.claude/projects")
REG = os.path.expanduser("~/.claude/session-registry")
IDLE_REGISTRY = 20     # registry confirms the process is gone -> short window is safe
IDLE_NO_REGISTRY = 120  # mtime is the only signal -> be much slower to call it dead


def sh(cmd, **kw):
    try:
        return subprocess.run(cmd, capture_output=True, text=True,
                              timeout=30, **kw).stdout
    except Exception:
        return ""


def chrome_start_epoch():
    """Epoch seconds when the running Chrome started. None if Chrome is down."""
    for ln in sh(["ps", "-axo", "pid=,lstart=,comm="]).splitlines():
        if ln.rstrip().endswith("/Contents/MacOS/Google Chrome"):
            m = re.match(r"\s*\d+\s+(\w{3}\s+\w{3}\s+\d+\s+[\d:]+\s+\d{4})", ln)
            if m:
                try:
                    return time.mktime(
                        time.strptime(m.group(1), "%a %b %d %H:%M:%S %Y"))
                except ValueError:
                    return None
    return None


def current_tabs():
    """[(tab_id, url)] for every tab open in Chrome right now.

    id + URL only -- neither can contain the delimiter, so parsing cannot be
    fooled by a page title.

    NOTE: the delimiter is `ASCII character 9`, not AppleScript's `tab`
    constant. Inside `tell application "Google Chrome"`, `tab` resolves to
    Chrome's own `tab` CLASS and concatenates as the literal text "tab",
    which silently yields zero parseable rows.
    """
    script = '''tell application "Google Chrome"
  set d to ASCII character 9
  set out to ""
  repeat with w in windows
    repeat with t in tabs of w
      set out to out & (id of t) & d & (URL of t) & linefeed
    end repeat
  end repeat
  return out
end tell'''
    tabs = []
    for ln in sh(["osascript", "-e", script]).splitlines():
        if "\t" not in ln:
            continue
        tid, url = ln.split("\t", 1)
        if tid.strip().isdigit():
            tabs.append((int(tid.strip()), url.strip()))
    return tabs


def registry_live():
    """session_id -> record, for registered sessions whose process is alive.

    Read-only on purpose: c-assistant's session-scan.py owns pruning stale
    entries. A leftover entry here only ever makes this script MORE
    conservative. Returns None when the registry does not exist at all, which
    is a different thing from "it exists and nothing is live"."""
    if not os.path.isdir(REG):
        return None
    live = {}
    for f in glob.glob(os.path.join(REG, "*.json")):
        try:
            with open(f) as fh:
                rec = json.load(fh)
        except Exception:
            continue
        cmd = sh(["ps", "-p", str(rec.get("pid", -1)), "-o", "command="]).strip()
        if cmd and "claude" in cmd.lower():
            live[rec.get("session_id", "")] = rec
    return live


def tab_records(block):
    """Every (tabId, url, groupId) the extension reported in one tool_result.

    The payload is JSON *nested inside* a JSON string, so it arrives escaped
    (\\"tabId\\"). Decoding it properly beats regexing the escaped form -- a
    naive '"tabId"' substring test matches the tool SCHEMAS that tool-search
    writes into the transcript while missing every real result."""
    out = []
    content = block.get("content")
    if isinstance(content, str):
        texts = [content]
    elif isinstance(content, list):
        texts = [c.get("text", "") for c in content
                 if isinstance(c, dict) and c.get("type") == "text"]
    else:
        return out
    for t in texts:
        if "availableTabs" not in t:
            continue
        try:
            payload = json.loads(t)
        except Exception:
            continue
        gid = payload.get("tabGroupId")
        for tab in payload.get("availableTabs") or []:
            if isinstance(tab, dict) and isinstance(tab.get("tabId"), int):
                out.append((tab["tabId"], tab.get("url", ""), gid))
    return out


def harvest(chrome_start):
    """tab_id -> {session, url, group, ts} from entries newer than Chrome's start.

    Later observations win, so `url` is the last URL that session saw on the tab."""
    owners = {}
    for path in glob.glob(os.path.join(PROJ, "*", "*.jsonl")):
        try:
            if os.path.getmtime(path) < chrome_start:
                continue
            fh = open(path, errors="replace")
        except OSError:
            continue
        sid = os.path.basename(path)[:-6]
        with fh:
            for ln in fh:
                if "availableTabs" not in ln:
                    continue
                try:
                    d = json.loads(ln)
                    ent = datetime.strptime(
                        d.get("timestamp", ""), "%Y-%m-%dT%H:%M:%S.%fZ"
                    ).replace(tzinfo=timezone.utc).timestamp()
                except Exception:
                    continue
                if ent < chrome_start:   # guard 1: pre-restart IDs are meaningless
                    continue
                blocks = (d.get("message") or {}).get("content")
                if not isinstance(blocks, list):
                    continue
                for b in blocks:
                    if not (isinstance(b, dict) and b.get("type") == "tool_result"):
                        continue
                    for tid, url, gid in tab_records(b):
                        if tid not in owners or ent >= owners[tid]["ts"]:
                            owners[tid] = {"session": sid, "url": url,
                                           "group": gid, "ts": ent}
    return owners


def close_tab(tab_id):
    """Close exactly the tab with this ID. Returns 'closed' or 'notfound'.

    NOTE: Chrome's `id of tab` is TEXT, not an integer (scripting.sdef says
    type="text"). Comparing it to a bare number silently evaluates false, so
    every close reports 'notfound' and nothing happens."""
    script = f'''tell application "Google Chrome"
  repeat with w in windows
    repeat with t in tabs of w
      if ((id of t) as text) is "{tab_id}" then
        close t
        return "closed"
      end if
    end repeat
  end repeat
  return "notfound"
end tell'''
    return sh(["osascript", "-e", script]).strip() or "error"


def main():
    ap = argparse.ArgumentParser(
        description="Report and close leftover Claude Code Chrome tab groups.")
    ap.add_argument("--close-orphans", action="store_true",
                    help="close tabs owned by sessions that have ended")
    ap.add_argument("--include-live", action="store_true",
                    help="ALSO close tabs owned by sessions that are still "
                         "running. Only with the user's explicit go-ahead -- a "
                         "live session may be mid-browser-task and will lose "
                         "the page it is working on.")
    ap.add_argument("--dry-run", action="store_true",
                    help="print what would close, change nothing")
    ap.add_argument("--idle-min", type=int, default=None,
                    help="minutes of transcript silence before a session with no "
                         "live process counts as ended")
    ap.add_argument("--self", dest="me", default=None,
                    help="your own session id, so it is reported separately "
                         "(defaults to $CLAUDE_CODE_SESSION_ID)")
    a = ap.parse_args()

    start = chrome_start_epoch()
    if start is None:
        print("Chrome is not running. Nothing to clean up.")
        return 0

    live = registry_live()
    have_reg = live is not None
    idle = a.idle_min if a.idle_min is not None else (
        IDLE_REGISTRY if have_reg else IDLE_NO_REGISTRY)
    live = live or {}

    me = a.me or os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    tabs = current_tabs()
    owners = harvest(start)
    now = time.time()

    print(f"Chrome up since {time.strftime('%a %b %d %H:%M', time.localtime(start))} "
          f"| {len(tabs)} tabs open | this session {me[:8] or '?'}")
    if not have_reg:
        print(f"NOTE: no session registry (~/.claude/session-registry) -- install the "
              f"c-assistant plugin for process-level liveness.\n      Falling back to "
              f"transcript mtime alone, idle window widened to {idle} min. "
              f"Consider --dry-run first.")
    print()

    groups, unowned = {}, []
    for tid, url in tabs:
        o = owners.get(tid)
        if o:
            groups.setdefault(o["session"], []).append((tid, url, o["url"]))
        else:
            unowned.append((tid, url))

    doomed = []
    for sid, items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        hits = glob.glob(os.path.join(PROJ, "*", sid + ".jsonl"))
        try:
            quiet = (now - os.path.getmtime(hits[0])) / 60 if hits else 9e9
        except OSError:
            quiet = 9e9
        is_me = sid == me
        alive = sid in live or quiet < idle
        tag = ("THIS SESSION" if is_me else
               "LIVE" if alive else f"ENDED (quiet {quiet:.0f}m)")
        why = []
        if sid in live:
            why.append(f"pid {live[sid].get('pid')} alive")
        if quiet < idle:
            why.append(f"transcript touched {quiet:.0f}m ago")
        print(f"[{tag}] {sid[:8]}  {len(items)} tab(s)"
              + (f"  ({'; '.join(why)})" if why else ""))
        for tid, url, seen in items:
            moved = "" if url == seen else "  (navigated since last seen)"
            print(f"      {tid}  {url[:96]}{moved}")
        if not is_me and (not alive or a.include_live):
            doomed += [t[0] for t in items]
        print()

    print(f"{len(unowned)} tab(s) belong to the user / no Claude session "
          f"-- never touched.")

    if not a.close_orphans:
        if doomed:
            print(f"\n{len(doomed)} tab(s) closable with --close-orphans")
        return 0
    if not doomed:
        print("\nNothing to close.")
        return 0

    print(f"\n{'Would close' if a.dry_run else 'Closing'} {len(doomed)} tab(s):")
    for tid in doomed:
        print(f"  {tid}  {'(dry run)' if a.dry_run else close_tab(tid)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
