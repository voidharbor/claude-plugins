---
description: Use when the user wants every leftover "Claude" tab group in Chrome cleaned up, not just this session's — stray chips piling up in the tab strip, tabs left behind by sessions that already ended. The cross-session version of /chrome-tabs.
---

Clear **every** Claude tab group in Chrome, not just this session's.

`/chrome-tabs` can only reach your own group. This one reaches the rest, because
it identifies tabs by **exact tab ID** instead of by URL.

macOS + Google Chrome only. Requires the Claude in Chrome extension.

## Why this is safe when closing by URL is not

Verified 2026-08-02: Chrome's AppleScript `id of tab` is the **same integer** the
extension reports as `tabId`. Every session's transcript records its group as
`{"tabId":N,"url":...}`. So an orphaned tab can be closed by ID — never guessed
from a URL.

That distinction is the whole skill. In a real run, one X profile URL was open
three times: two orphaned Claude tabs and **one of the user's own**. By URL you
close theirs. By ID you close exactly the right two.

Two guards keep the ID trustworthy:

1. **Chrome-run scoping.** Tab IDs are unique only within one Chrome process run.
   Only transcript entries written *after* Chrome started are read, so a stale ID
   can never match a recycled one.
2. **Conservative liveness.** A session counts as ended only if its process is
   gone **and** its transcript has been quiet past the idle window. Either one
   saying "alive" keeps its tabs.

Tabs no session claims belong to the user. They are never touched, and the report
says how many were left alone so that stays visible.

## Procedure

1. **Report first, always.**

       python3 "${CLAUDE_PLUGIN_ROOT}/scripts/chrome-groups.py" --self <your-session-id>

   Read-only. Prints every Claude-owned tab grouped by owning session, tagged
   `THIS SESSION` / `LIVE` / `ENDED`, plus the count of the user's untouched tabs.
   Your own session id is in your system prompt; pass it so your group is not
   mistaken for someone else's.

2. **Close your own group** with `/chrome-tabs` (MCP: `tabs_context_mcp` →
   `tabs_close_mcp` per tab). Use the MCP for your own — not the ID path.

3. **Close the ended sessions' tabs.**

       python3 "${CLAUDE_PLUGIN_ROOT}/scripts/chrome-groups.py" --close-orphans

   Add `--dry-run` first if anything in the report looked surprising.

4. **Leave LIVE sessions alone** — see below.

5. **Re-run the report** and say what closed, what stayed, and why.

## Live sessions

Several sessions may be running at once, some mid-browser-task. Closing a live
session's tabs yanks the page out from under it.

| Situation | Do |
|---|---|
| Session is live | Leave it. Name it in the report |
| User says close everything anyway | `--close-orphans --include-live`, after telling them which sessions lose tabs |
| Session is live in a terminal you can write to | Better: ask that session to run `/chrome-tabs` itself, so it knows its tabs are gone |

## Liveness accuracy

Process-level liveness comes from the session registry that the **c-assistant**
plugin maintains (`~/.claude/session-registry`). Without it there is no way to map
a running claude process back to a session id, so liveness falls back to
transcript mtime alone and the idle window automatically widens from 20 to 120
minutes. The script prints a NOTE when that happens — pass it on rather than
quietly closing more than you should.

## Hazards

- **Never close by URL or title, ever.** Duplicate URLs across the user's tabs and
  Claude's tabs are the normal case, not the edge case.
- **Never close a whole window.** The user's tabs and Claude group tabs live
  interleaved in one window — verified, 15 of 24 tabs were theirs.
- **After a Chrome restart**, tabs opened before it lose their ID mapping and count
  as the user's. They will not be detected, and clearing them is a right-click →
  **Close group** job. Say so rather than hunting for them.
- If Chrome is not running the script says so and exits. Nothing to do.
- `--include-live` is never the default and never inferred from "clean it all up."
  Ask, name the sessions that lose tabs, then run it.

## Two traps that cost real time here

Both fail **silently** — no error, just empty or no-op results:

- Inside `tell application "Google Chrome"`, the word `tab` resolves to Chrome's
  `tab` **class**, not the tab character. `... & tab & ...` concatenates the
  literal text `"tab"` and every row becomes unparseable. Use
  `set d to ASCII character 9`.
- `id of tab` is **text**, not an integer (`scripting.sdef` says `type="text"`).
  `if (id of t) is 478910973` is always false, so every close reports `notfound`
  and nothing happens. Compare `((id of t) as text) is "478910973"`.

And when parsing transcripts: the extension's payload is JSON nested inside a JSON
string, so it arrives escaped (`\"tabId\"`). A `'"tabId"' in line` prefilter
matches the tool **schemas** written into the transcript while missing every real
result. Decode the block properly — `chrome-groups.py` already does.

## When to run this

When the user asks, or when the tab strip has visibly accumulated chips. For your
own cleanup at the end of browser work, `/chrome-tabs` is the right skill — it
needs no AppleScript and no cross-session reasoning.
