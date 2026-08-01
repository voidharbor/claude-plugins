---
description: Use when the user has approved numbered SKILL- items from /skill-forge and wants them applied — or asks to apply, publish, or ship an approved skill fix. The only half of the loop that writes anything.
---

Take the items the user approved, make the edits, and — where a public copy
exists — publish them. This is the only half of the loop that writes.

Optional argument: a specific item (`/skill-forge-apply SKILL-002`), or
`--dry-run` to show what would change and stop.

## Step 1 — find the answers

```bash
date "+%Y-%m-%d %H:%M:%S %Z"
```

Read `~/.claude/skill-forge/PROPOSALS.md` (or the single review file the user
keeps) for decisions, and take any given directly in the conversation.

People answer in running plain text: `1 yes 2 no 4 yes but rename it`. So:

- Accept `SKILL-001 yes`, `skill-1 yes`, and a bare `1 yes` when the inbox
  numbered it that way. Match on the number, case-insensitively.
- Act only on `SKILL-` items. If the inbox mixes in other queues' items, leave
  those for whatever owns them, and say which items you took.
- **An item the user did not mention is not approved.** Silence is not consent.
- If they answered with a condition rather than yes or no ("yes but keep the
  old name"), **do not apply it and do not guess the interpretation.** Report
  it as needing them.

If there are no unprocessed decisions, stop and say so. Do not fall back to
applying anything.

## Step 2 — load the staged proposal

Read `~/.claude/skill-forge/proposals-<date>.json` for the matching run. Each
approved item carries `target`, `anchor`, and `change`.

**Verify the anchor still matches the file exactly before editing.** If it does
not, the file moved since the proposal was written. Skip the item and report it
as stale rather than relocating the edit by inference — that guess is how a
good loop starts corrupting files.

## Step 3 — apply

For each verified item:

1. Edit `target` — replace or insert at the anchor, nothing else.
2. Re-read the result and confirm the file is still coherent. A command file
   that no longer parses as instructions is worse than the defect it fixed.

## Step 4 — publish gate

This step only exists if you publish skills somewhere public. If you do, it is
a hard gate, not a formality: classify every file you touched before it goes
anywhere (the `my-skills` plugin in this marketplace does exactly this — sort
by whether a stranger could run it).

- Welded to one client, employer, or account → **never publish.** Apply
  locally, stop there.
- Names you, your paths, your machine → scrub to the neutral phrasing the
  public repo already uses, or hold it.
- Generic → publish.

If a proposal would introduce a personal detail into a published skill, that is
a defect in the proposal. Do not publish it, and say so. Credentials, contact
details, and anything naming a private project never go into a public repo, in
any form, including in an example.

## Step 5 — push

Clone the public repo fresh rather than trusting a stale checkout — another
session or machine may be ahead of you, and a stale copy is how you push a
revert.

Then, per published skill:

- Copy the scrubbed command into place.
- **Bump the version in both** the plugin's own manifest **and** the
  marketplace index that lists it. Those two disagreeing is the most likely
  thing to break the marketplace, and nothing will tell you it happened.
- Update the README row if what the skill does actually changed.
- Commit one skill per commit, message naming the defect fixed, not the file
  touched. Push.

If the push is rejected as non-fast-forward, **pull and reapply. Never force.**
Someone's work is on the other end of that rejection.

## Step 6 — close the loop

Mark handled items done in the inbox and remove them from the awaiting section
— a decided item must not keep appearing. Declined items are recorded as
rejected so `/skill-forge` never reproposes them. Stale-anchor items go back to
open with the reason, so the next run reproposes them against the current file.

## Step 7 — report

Per item: applied and published, applied locally only and why, or skipped and
why. Then the commit URLs. If nothing was approved, say that in one line rather
than manufacturing activity.

## Hard rules

- **Approval is per item.** Never treat one yes as blanket approval for a batch.
- **Never apply an item with a stale anchor.**
- **Never force-push.**
- **Never publish anything personal or client-specific**, and never let a
  proposal quietly demote a published skill into being one.
- If anything is ambiguous, leave it for the user. An unapplied improvement
  costs a week. A wrongly applied one costs trust in the whole loop.
