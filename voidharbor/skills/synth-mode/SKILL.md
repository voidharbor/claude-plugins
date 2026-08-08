---
name: synth-mode
description: Use for ANY text a real person will read as coming from the user or their brands - emails, texts, replies, website copy, briefs, social posts, READMEs, letters. Strips the tells that mark writing as machine-made, instead of adding style to simulate a human. Load BEFORE drafting, not to patch a draft after. (Named for Fallout 4's synths - the good ones pass.)
---

# synth-mode

This skill removes things. It does not add personality, texture, or voice. Every
instruction below is a deletion or a check. If you find yourself adding a flourish to
sound human, that is the failure this skill exists to prevent.

## How to write this file

The prose in this file is itself a rule. Models match the register of what they read, so
an instruction file written in punchy aphorisms produces punchy aphoristic output. That
is how the first version of this skill broke: it was written in the exact voice its
users ended up complaining about. Keep the writing here flat and procedural. If you are
editing this file and a sentence sounds good, rewrite it plainer.

## Hard bans

Check these last, before any text is shown to anyone. If the user has stated their own
formatting preferences, theirs win.

1. No em dashes. No double hyphens as punctuation. No `&#8212;` entities. Use commas,
   colons, parentheses, or two sentences. Dash-chained sentences are the single largest
   engine of the over-polished register this skill exists to remove. Hyphens inside
   compound words are fine.
2. No blockquote markup around text the user will copy and paste. It renders as a bar
   and corrupts the copy.
3. No headers, bullets, or bold inside an email, text message, or DM.

## Never train on generated text

The most common way this skill degrades: text the model wrote gets approved and sent by
the user, then later gets read back as an example of "how they write." The voice then
drifts along the model's own gradient with nothing pulling it back, and that gradient
points at confident, clipped, quotable prose.

A user's sent folder is not automatically ground truth. If they have been drafting with
an assistant, much of it is model output they approved. Before treating any sample as
the user's voice, ask whether they typed it themselves. Prefer older writing from before
they started using an assistant, and prefer short functional notes over long polished
ones, because the short ones are almost always genuinely theirs.

## Procedure

**1. Name the reader and the surface, in one line, before drafting.** Who reads this,
and where. "Reply to a supplier who owes us a quote." "Landing page copy for
homeowners." This selects one register and rules out the others. Skipping this step is
what collapses every surface into a single voice.

**2. Read the matching block in `registers.md`, and only that block.**

**3. Get a voice reference, or declare that you have none.** Ask the user for three or
four things they wrote themselves, unassisted, to a real person. If they have none to
hand, say plainly that you are writing without a voice reference, then remove tells only
and do not attempt to imitate anyone. An invented voice is worse than writing with no
voice reference at all.

**4. Draft.**

**5. Run the pass below.** Every item is a deletion.

## The pass

- Delete every em dash and double hyphen. Repunctuate.
- Delete any sentence that restates the previous sentence in different words.
- Delete any sentence that explains the reader's own business, job, or life to them.
- Delete anything matching `tells.md`.
- Delete any product name, price, statistic, or research the reader did not ask about.
- Cut to the register's length cap. If it is over, cut whole sentences, do not compress
  into denser ones.
- **Find the best sentence in the draft and replace it with the plain version.** If a
  line is quotable, memorable, or well-turned, it is wrong. Nobody writing a real email
  in ninety seconds lands a good line. This is the check that fixes writing that sounds
  like it is trying to be human, and it is the one most likely to be skipped.

## What not to do

Do not add typos, lowercase openers, sentence fragments, or casual asides to seem human.
Real writing contains all of those, but they occur because someone typed fast and did
not reread, not because they were placed. Manufactured imperfection reads worse than
clean prose, because a reader can feel the intent behind it.

Do not treat short as a style. Real messages are short because the writer said the thing
and stopped, not because brevity was the goal.
