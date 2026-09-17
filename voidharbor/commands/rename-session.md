---
description: Use when the user runs /rename-session or asks for this chat to be renamed automatically. Renames the current session based on what the conversation has actually been about.
---

Rename this session so it is findable later in the resume picker, at claude.ai/code, and
in any cross-session triage.

## Derive the title

Read the whole conversation and name what the session is REALLY about: the dominant
work, not the first message and not the most recent tangent. If the session pivoted,
name the destination, not the origin.

Rules:

- 2 to 5 words, ALL CAPS, so titles stay scannable in a list of twenty
- Concrete nouns beat categories: "CHECKOUT RETRY BUG" not "BUG FIXING"
- No dashes as punctuation, and no filler words like SESSION, CHAT or WORK
- If the user passed arguments, treat them as the topic they want named. Uppercase them
  and use them, tightening only for length.

The test for a good title: six weeks from now, in a list of thirty sessions, does this
one line tell them which session this was. "IMAGE GENERATION" fails that test when three
sessions touched image generation. "PRODUCT CARD THUMBNAILS" passes.

## Apply it

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/rename-session.py" "THE TITLE"
```

The helper finds the transcript through the `CLAUDE_CODE_SESSION_ID` environment
variable, never by newest modification time, which matters once several sessions are
open at once. It writes the title to both of the places the app itself writes on a
rename: the `custom-title` line appended to the transcript `.jsonl`, and the
`custom-title.json` sidecar beside it.

## Confirm

Tell the user the new name in one line.

Worth knowing: the pane or tab header of the live session may not pick up the new name
until it is reopened. The stored name is what the resume picker and any triage tool
read, so the rename has taken effect even when the header still shows the old one. Say
so rather than renaming twice.

## Requirements

Python 3, and a session that has written a transcript. The transcript is appended to,
never rewritten.
