#!/usr/bin/env python3
"""
memory-scan.py - deterministic first stage of /memory-curate.

Does the cheap, exact, zero-hallucination work:
  1. inventories every per-project memory store
  2. structural checks (index/file mismatches, oversize, bad frontmatter, dead wikilinks)
  3. filesystem verification of every path referenced inside memory
  4. extracts the user's *typed* turns from recent transcripts and ranks them
     for durability markers

Emits a report the LLM half of the skill reads. It never writes to memory.
"""

import argparse
import glob
import hashlib
import json
import os
import re
import sys
import time

PROJECTS = os.path.expanduser("~/.claude/projects")
HOME = os.path.expanduser("~")

# ---------------------------------------------------------------- stores


def find_stores():
    stores = []
    for d in sorted(glob.glob(os.path.join(PROJECTS, "*", "memory"))):
        if not os.path.isdir(d):
            continue
        files = [
            f
            for f in sorted(glob.glob(os.path.join(d, "*.md")))
            if os.path.basename(f) != "MEMORY.md"
        ]
        stores.append(
            {
                "path": d,
                "project": os.path.basename(os.path.dirname(d)),
                "index": os.path.join(d, "MEMORY.md"),
                "files": files,
            }
        )
    # Claude Code names a project dir after its cwd with "/" -> "-", so the store
    # for the home directory is the one loaded by most sessions. Derive it rather
    # than hardcoding a username.
    home_project = HOME.replace("/", "-")
    stores.sort(key=lambda s: (s["project"] != home_project, -len(s["files"])))
    return stores


# ------------------------------------------------------------ structure

FM_NAME = re.compile(r"^name:\s*(.+?)\s*$", re.M)
FM_DESC = re.compile(r"^description:\s*(.+?)\s*$", re.M)
FM_TYPE = re.compile(r"^\s*type:\s*(.+?)\s*$", re.M)
INDEX_LINE = re.compile(r"\[[^\]]*\]\(([^)]+\.md)\)")
WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")

OVERSIZE = 15000  # bytes; above this a "fact" has become a document
LARGE = 8000


def norm(s):
    """Older auto-memory stores use underscore filenames with hyphenated
    frontmatter names. That is a convention difference, not rot - collapse both
    so we do not report ~45 phantom findings."""
    return s.replace("_", "-").lower()


def check_store(store):
    issues = []
    index_txt = ""
    if os.path.exists(store["index"]):
        index_txt = open(store["index"], errors="replace").read()
    else:
        issues.append(("no-index", "MEMORY.md missing entirely"))

    indexed = {norm(os.path.basename(m)) for m in INDEX_LINE.findall(index_txt)}
    actual = {norm(os.path.basename(f)) for f in store["files"]}
    names = set()

    for f in store["files"]:
        base = os.path.basename(f)
        try:
            txt = open(f, errors="replace").read()
        except Exception as e:
            issues.append(("unreadable", f"{base}: {e}"))
            continue
        size = os.path.getsize(f)
        if size > OVERSIZE:
            issues.append(
                ("oversize", f"{base}: {size // 1024} KB - split candidate")
            )
        elif size > LARGE:
            issues.append(("large", f"{base}: {size // 1024} KB"))

        nm = FM_NAME.search(txt)
        if not nm:
            issues.append(("no-frontmatter-name", base))
        else:
            names.add(nm.group(1))
            if norm(nm.group(1)) != norm(base[:-3]):
                issues.append(
                    ("name-mismatch", f"{base}: frontmatter name is '{nm.group(1)}'")
                )
        if not FM_DESC.search(txt):
            issues.append(("no-description", base))
        if not FM_TYPE.search(txt):
            issues.append(("no-type", base))

    for f in store["files"]:
        base = os.path.basename(f)
        txt = open(f, errors="replace").read()
        for link in set(WIKILINK.findall(txt)):
            if norm(link + ".md") not in actual:
                issues.append(("dead-wikilink", f"{base} -> [[{link}]]"))

    for missing in sorted(indexed - actual):
        issues.append(("index-points-nowhere", missing))
    for orphan in sorted(actual - indexed):
        issues.append(("not-in-index", orphan))

    return issues


# ----------------------------------------------------------- stale refs

# backtick-quoted candidates catch paths containing spaces
TICKED = re.compile(r"`([^`\n]{3,200})`")
BARE_PATH = re.compile(r"(?<![\w`])(~/|/Users/|/home/)[\w./~+-]{2,160}")
TRAILING = " \t.,;:)]}'\"*"
LOCAL_ROOTS = ("~/", "/Users/", "/home/")


def looks_like_path(s):
    """Only real local paths. Deliberately excludes URL routes (/admin/...),
    slash-command names (/c-assistant) and container paths (/app/data), all of
    which live in memory legitimately and are not filesystem refs."""
    s = s.strip()
    if not s or " -> " in s:
        return False
    if not s.startswith(LOCAL_ROOTS):
        return False
    if any(c in s for c in "|<>$*?{}"):
        return False
    return True


def stale_refs(stores):
    seen = {}
    for store in stores:
        for f in store["files"] + [store["index"]]:
            if not os.path.exists(f):
                continue
            txt = open(f, errors="replace").read()
            cands = set()
            for t in TICKED.findall(txt):
                t = t.strip().rstrip(TRAILING)
                if looks_like_path(t):
                    cands.add(t)
            for m in BARE_PATH.finditer(txt):
                t = m.group(0).rstrip(TRAILING)
                if looks_like_path(t):
                    cands.add(t)
            for c in cands:
                real = os.path.expanduser(c)
                if os.path.exists(real):
                    continue
                # Only report when the parent exists: the location is real but the
                # item is gone. Kills paths truncated at a space and anything that
                # was never a local path to begin with.
                if not os.path.isdir(os.path.dirname(real.rstrip("/"))):
                    continue
                # A bare regex stops at the first space, so a path like
                # "~/Desktop/My Project" arrives truncated as "~/Desktop/My". If
                # anything on disk extends this prefix, it is a truncation
                # artifact rather than a missing file.
                if glob.glob(glob.escape(real) + "*"):
                    continue
                seen.setdefault(c, []).append(
                    f"{store['project']}/{os.path.basename(f)}"
                )
    return seen


# ------------------------------------------------------------ transcripts

SKIP_PREFIX = (
    "<system-reminder",
    "<command-name",
    "<command-message",
    "<local-command",
    "<user-memory",
    "<task-notification",
    "Caveat:",
    "[Request interrupted",
    # auto-generated context handoff, not typed by the user - dense enough to score
    # highly on every marker if left in
    "This session is being continued from a previous conversation",
)

MARKERS = [
    # (weight, label, regex)
    (5, "rule", re.compile(
        r"\b(never|always|from now on|going forward|make sure (you|to)|"
        r"don'?t ever|stop (doing|using|adding)|my rule|the rule is|"
        r"remember (that|to|this))\b", re.I)),
    (4, "correction", re.compile(
        r"(^\s*(no|nope|wrong|actually)\b)|"
        r"\b(that'?s (wrong|not right|incorrect|backwards)|"
        r"you (misunderstood|got that wrong)|not what i (said|meant)|"
        r"it'?s not .{1,40} it'?s)\b", re.I)),
    (3, "decision", re.compile(
        r"\b(approved|let'?s go with|we'?re (going with|doing)|"
        r"decided|go with (option|the)|use (this|that) one|"
        r"final answer|lock (it|that) in)\b", re.I)),
    (3, "preference", re.compile(
        r"\b(i (prefer|hate|really like|don'?t (like|want))|"
        r"my (preference|style|workflow)|i want you to)\b", re.I)),
    (2, "constraint", re.compile(
        r"\b(can'?t|cannot|won'?t work|blocked|doesn'?t work|"
        r"only works? (if|when)|requires?|depends on)\b", re.I)),
    (2, "fact", re.compile(
        r"(~/[\w./+-]{3,}|/Users/[\w./+-]{3,}|https?://\S{6,}|"
        r"\$\d[\d,.]*|\b\d{3}-\d{3}-\d{4}\b|\b\d+\.\d+\.\d+\.\d+\b)")),
]

LOW_VALUE = re.compile(
    r"^\s*(y|yes|yep|yeah|ok(ay)?|k|sure|no|nope|thanks|ty|continue|go ahead|"
    r"do it|proceed|next|stop|wait|nice|cool|perfect|good|great|done|"
    r"/\w[\w-]*)\s*[.!]?\s*$", re.I)


def extract_turns(days, min_len):
    cutoff = time.time() - days * 86400
    files = [
        f
        for f in glob.glob(os.path.join(PROJECTS, "*", "*.jsonl"))
        if os.path.getmtime(f) > cutoff
    ]
    turns = []
    for path in files:
        project = os.path.basename(os.path.dirname(path))
        try:
            fh = open(path, errors="replace")
        except Exception:
            continue
        with fh:
            for line in fh:
                if '"user"' not in line:
                    continue
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                if e.get("type") != "user":
                    continue
                # Exact markers for content the user did NOT type: skill bodies and
                # command output are isMeta, tool/skill injections carry a
                # sourceToolUseID, subagent turns are sidechains. This is what makes
                # "additions only from his own words" a guarantee, not a hope.
                if e.get("isMeta") or e.get("sourceToolUseID") or e.get("isSidechain"):
                    continue
                msg = e.get("message") or {}
                c = msg.get("content")
                if isinstance(c, list):
                    c = "".join(
                        b.get("text", "")
                        for b in c
                        if isinstance(b, dict) and b.get("type") == "text"
                    )
                if not isinstance(c, str):
                    continue
                c = c.strip()
                if len(c) < min_len:
                    continue
                if c.startswith(SKIP_PREFIX) or "tool_use_id" in c:
                    continue
                if LOW_VALUE.match(c):
                    continue
                turns.append(
                    {
                        "text": c,
                        "ts": (e.get("timestamp") or "")[:10],
                        "project": project,
                        "session": os.path.basename(path)[:8],
                    }
                )
    return turns, len(files)


def score(turn):
    hits, total = [], 0
    for weight, label, rx in MARKERS:
        if rx.search(turn["text"]):
            hits.append(label)
            total += weight
    # long deliberate messages carry more durable content than one-liners
    if len(turn["text"]) > 400:
        total += 1
    return total, hits


def rank(turns, top):
    scored = []
    seen = set()
    for t in turns:
        s, hits = score(t)
        if s < 4:  # needs more than a lone weak marker
            continue
        key = hashlib.md5(
            re.sub(r"\s+", " ", t["text"].lower())[:200].encode()
        ).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        t["score"] = s
        t["markers"] = hits
        scored.append(t)
    scored.sort(key=lambda x: -x["score"])
    return scored[:top], len(scored)


# ---------------------------------------------------------------- report


def human(stores, structure, refs, top_turns, kept_total, nfiles, days, top):
    out = []
    w = out.append
    w("=" * 72)
    w("MEMORY CURATION SCAN")
    w("=" * 72)

    w("\n## STORES\n")
    w(f"{'files':>6}  {'size':>7}  {'newest':<12} project")
    for s in stores:
        tot = sum(os.path.getsize(f) for f in s["files"]) if s["files"] else 0
        newest = max(
            (os.path.getmtime(f) for f in s["files"]), default=0
        )
        stamp = time.strftime("%Y-%m-%d", time.localtime(newest)) if newest else "-"
        w(f"{len(s['files']):>6}  {tot // 1024:>5} KB  {stamp:<12} {s['project']}")

    w("\n## STRUCTURE\n")
    any_issue = False
    for s in stores:
        iss = structure[s["path"]]
        if not iss:
            continue
        any_issue = True
        w(f"[{s['project']}]")
        by_kind = {}
        for kind, detail in iss:
            by_kind.setdefault(kind, []).append(detail)
        for kind in sorted(by_kind):
            for d in by_kind[kind]:
                w(f"  {kind:<22} {d}")
        w("")
    if not any_issue:
        w("  (clean)")

    w("\n## STALE FILESYSTEM REFS")
    w("   paths named inside memory that no longer exist on THIS machine.")
    w("   NOTE: a path on a remote host, container or another machine is correct")
    w("   as written and will show up here anyway - confirm before changing it.\n")
    if refs:
        for p, where in sorted(refs.items()):
            w(f"  MISSING  {p}")
            w(f"           cited by: {', '.join(sorted(set(where)))}")
    else:
        w("  (none)")

    w(f"\n## CANDIDATE TURNS  (last {days}d)")
    w(f"   {nfiles} session transcripts scanned")
    w(f"   {kept_total} turns passed the durability filter, showing top {len(top_turns)}")
    if kept_total > top:
        w(f"   !! {kept_total - top} candidates dropped by the --top cap")
    w("")
    for i, t in enumerate(top_turns, 1):
        w(f"--- [{i}] score {t['score']}  {t['ts']}  {t['project']}  ({','.join(t['markers'])})")
        body = t["text"]
        if len(body) > 1200:
            body = body[:1200] + "\n    ... [truncated]"
        for line in body.splitlines():
            w("    " + line)
        w("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--top", type=int, default=120)
    ap.add_argument("--min-len", type=int, default=30)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    stores = find_stores()
    structure = {s["path"]: check_store(s) for s in stores}
    refs = stale_refs(stores)
    turns, nfiles = extract_turns(a.days, a.min_len)
    top_turns, kept_total = rank(turns, a.top)

    if a.json:
        json.dump(
            {
                "stores": [
                    {
                        "project": s["project"],
                        "path": s["path"],
                        "files": [os.path.basename(f) for f in s["files"]],
                        "issues": structure[s["path"]],
                    }
                    for s in stores
                ],
                "stale_refs": refs,
                "transcripts_scanned": nfiles,
                "candidates_total": kept_total,
                "candidates": top_turns,
            },
            sys.stdout,
            indent=2,
        )
    else:
        print(human(stores, structure, refs, top_turns, kept_total, nfiles, a.days, a.top))


if __name__ == "__main__":
    main()
