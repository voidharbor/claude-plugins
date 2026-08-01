---
description: Use when the user asks by voice what their other Claude sessions are waiting on, or wants their session triage read aloud — hands busy, eyes elsewhere. The spoken variant of /c-assistant.
---

Voice branch of `/c-assistant`. **Do the triage exactly as that command
specifies** — read `${CLAUDE_PLUGIN_ROOT}/commands/c-assistant.md` and follow
its procedure, judgment table, cross-session analysis, and hard rules in full.
Nothing about *what counts as blocked* changes here.

What changes is **delivery**. The parent writes a scannable report for the eye.
This one produces something the user can absorb with their hands busy and their
eyes elsewhere.

## The one rule that drives everything else

**Nobody can scroll back through speech.** A spoken answer is heard once, in
order, with no skimming. So it has to be short, ranked hardest-first, and it
must never contain anything that is meaningless out loud.

## Speak this, not that

| Never say aloud | Say instead |
|---|---|
| Session IDs (`a3f8c2e1`) | how they'll recognise the window: *"the one you opened with 'fix the CSV importer'"* |
| File paths, URLs, commands | *"a file on your Desktop"*, *"the analytics dashboard"* |
| Markdown, blockquotes, bullets | plain connected sentences |
| Counts of everything you scanned | only what is blocked |
| The full draft reply | *"I've got a reply drafted for that one"* |

## Shape of the spoken answer

Three parts, in this order, no headings:

1. **The headline number, then the single most valuable action.** Lead with the
   one answer that unblocks the most work — the cross-session insight from the
   parent's step 5, if there is one. That is the whole reason they ran this.
2. **At most three items.** For each: the recognisable handle, one sentence on
   what it wants, and the decision to make. If two sessions are stuck behind
   the same thing, that is one item, not two.
3. **One closing offer.** *"Want me to read the drafts, or go deeper on any of
   them?"*

Anything past the top three is noise in audio. Say *"there are four more, none
urgent"* and stop.

**Target 20 to 30 seconds of speech.** Roughly 60 to 90 words. If it runs
longer, you are reporting instead of triaging — cut to the decisions.

## Still write the drafts

The drafts are the point of the parent command and they survive here. Write
every one of them, to the parent's standard, **as text in the chat** — those
are read and pasted with the eyes. Just do not read them aloud unless asked.

So: **spoken summary short, on-screen drafts complete.** The voice is an index
into the text, not a replacement for it.

## If the user answers back by voice

They may reply conversationally — *"what about the second one"*, *"read me that
draft"*, *"just tell me the importer one"*. Answer the follow-up directly and
stay short. Do not re-read the whole list.

## Hard rules

Every hard rule in `/c-assistant` applies here unchanged, in particular:

- **Never kill, resume, or send input to another session.** Speaking a draft
  aloud is not delivering it. The user still pastes it themselves.
- **Never carry detail sideways between sessions.** Sessions often span
  separate clients, employers, or confidentiality boundaries, and that does not
  relax because the output is audio — if anything, spoken summaries blur
  context more easily. Say *that* a session is blocked, not what it contains.
- **Never invent a fact only the user holds.** Out loud this is more dangerous
  than in text, because a confident sentence in a natural voice is easy to
  accept. If a fact is theirs to supply, say so plainly.
