---
description: Use when a session has finished browser work, is wrapping up a turn in which it opened Chrome tabs, or the user asks to clean up Chrome tabs and stray "Claude" tab groups. Also covers reporting leftover groups that no live session owns.
---

Close the Chrome tabs **this session** opened and no longer needs, so it does not
leave an orphaned "✅ Claude" group sitting in the user's tab strip.

Optional argument: which tabs to keep or close. If absent, judge it from the table below.

## The one rule that matters

**You can only see and close your OWN tab group.** `tabs_context_mcp` returns this
session's group and nothing else. `tabs_close_mcp` accepts only those tab IDs.
Every other tab in Chrome belongs to the user or to another live Claude session.

So there is exactly one correct scope: your own tabs. If you find yourself
enumerating Chrome with AppleScript and reasoning about which tabs some *other*
session might own, stop — that is the failure mode this skill exists to prevent.
Assume several sessions may be running at once, some mid-task in the browser.

## Procedure

1. `tabs_context_mcp` with no arguments. If it says no tab group exists, this
   session has nothing to clean up. Say so and stop — do not go looking elsewhere.
2. For each tab it lists, decide keep or close using the table.
3. `tabs_close_mcp` once per tab, one tab ID per call. It reports tabs remaining.
4. Closing the last tab auto-removes the group and the chip disappears from the
   tab strip. That is the goal state once browser work is done.

Verified behaviour: the final close returns "Group is now empty (auto-removed)";
closing an ID that is not in your group returns an error and changes nothing.

## Keep or close

| Tab | Do |
|---|---|
| Step is finished and you already extracted what you needed | Close |
| Search results, docs, articles you have read | Close |
| Logged-in session the user would have to re-authenticate, and the task is not finished | Keep |
| Half-filled form, unsaved draft, unsubmitted order | Keep, and never close without asking |
| Not sure | Keep |

Leaving a tab open costs nothing. Closing one that was still needed costs a re-login.

## What you cannot do

- **You cannot close another session's group.** Not through the MCP (scoped to
  yours), and not through computer-use — Chrome is granted at **read** tier, so
  clicks and keystrokes are blocked there by design.
- **Never use `osascript` to close Chrome tabs.** AppleScript can list tabs but
  cannot see tab groups, so it cannot tell a Claude tab from one of the user's. It
  is the one tool that will cheerfully close the wrong thing.
- Leftover "✅ Claude" chips from sessions that ended without cleaning up are the
  user's to clear: right-click the chip → **Close group**. Report how many you can
  see and stop there.

## If asked to clean up everything, not just yours

Say what you can and cannot reach, then give something actionable:

- Screenshot the tab strip (computer-use, read tier is enough) and count the
  "✅ Claude" chips.
- Check which sessions are still live before suggesting anything gets closed.
  Transcripts live in `~/.claude/projects/<project-slug>/*.jsonl`, where the slug
  is the project path with `/` replaced by `-`. A transcript touched in the last
  few minutes means that session is working right now. Your own session ID is in
  your system prompt — exclude it, since your transcript contains whatever you
  just dumped and will match everything.
- Attribute tabs to sessions by grepping those transcripts for the URLs, rather
  than guessing from favicons.

Then report and let the user decide. Do not close another session's tabs on inference.

## When to run this

At the end of any turn where you opened Chrome tabs, and whenever asked. Do not
wait to be told — sessions finishing browser work and abandoning their groups is
exactly what creates the pile-up.
