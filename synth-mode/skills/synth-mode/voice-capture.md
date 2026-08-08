# Building a voice profile

The profile lives at `~/.claude/synth-mode/voice.md`. It is local, it is not committed
anywhere, and it survives plugin updates because it sits outside the plugin directory.

Never build one silently in the background, and never block a drafting task to build one.
If a user asks for an email and no profile exists, write the email with tell-removal
only, say in one line that you have no voice reference, and offer to build the profile
afterward.

## Intake

Ask for three to five things they wrote. Real messages sent to a real person, not
writing samples composed for this purpose, because composed samples come out more careful
than their normal writing and will skew the profile formal.

Suggest places to look, in this order. The list is ordered by how likely the writing is
to be genuinely theirs:

1. Short functional notes to suppliers, coworkers, or a landlord. Chasing something,
   confirming something, correcting something. These are almost never assisted and they
   carry the most signal per word.
2. Texts or DMs to someone they know well.
3. Sent email from before they started using an AI assistant.
4. Forum or community comments under their own account.

Avoid anything long and polished, anything customer-facing that may have come from a
template or CRM, and anything they might have drafted with an assistant.

## The contamination check

Ask directly, for each sample: did you type this yourself, without an assistant?

This matters more than it sounds. A user's sent folder can be almost entirely model
output that they approved and sent. If you profile that, you are profiling the assistant,
the voice compounds on itself every cycle, and it drifts toward polished and quotable
with nothing pulling it back. That is the failure this whole skill exists to prevent, and
it arrives through the corpus, not through the rules.

Two signals that a sample is not theirs, worth checking even when they say it is:

- Em dashes, if the rest of their writing has none.
- A well-turned line. Real messages written in ninety seconds do not contain one.

If a sample fails the check, set it aside and ask for another. Do not average the two
voices together.

## What to extract

Read the samples and record what is observably true. Do not infer personality, do not
describe them as a writer, and do not write anything you could not point at in a sample.

Record, per register where the samples support it:

- **Openers.** Exact form. "Hey Dave," is different from "Hi Dave," is different from no
  greeting at all.
- **Closings.** Exact form, including initials, first name, or nothing.
- **Length.** Word count of the shortest and longest sample.
- **Punctuation habits.** Exclamation marks and their density. Dropped apostrophes.
  Missing end punctuation. Anything unusual, like a space before a question mark.
- **Capitalization.** Whether they lowercase sentence starts, proper nouns, addresses.
- **Spelling.** Words they misspell repeatedly. Record them, never reproduce them
  deliberately.
- **Warmth markers.** Thanks, apologies, enthusiasm, and how often.
- **What they never do.** Structure, bold, bullets in a personal message, summary
  paragraphs. This section is usually the most useful one.

## Scrub before writing

Replace names, street addresses, phone numbers, email addresses, prices, account numbers,
and company names with placeholders as you write the file. Keep the sentence structure,
punctuation and spelling exactly as typed, including errors.

Tell the user where the file is and what is in it. Some people will not want their
writing stored on disk at all, and that is a reasonable position: offer to hold the
profile in the conversation instead and rebuild it next time.

## File format

```markdown
# Voice profile
Built YYYY-MM-DD from N samples. All samples confirmed self-typed.

## Samples
(scrubbed, verbatim, grouped by register)

## Observed
(the extraction sections above)

## Not ground truth
(anything that failed the contamination check, listed so it is never reused)
```

## Refreshing

Rebuild when the user says the output does not sound like them, or when the profile is
more than a few months old. On rebuild, take new samples from the same sources. Never
add text this skill produced to the profile, even if the user liked it and sent it.
