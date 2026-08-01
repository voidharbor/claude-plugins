---
description: Use for a recurring audit of everything you have authored for Claude — commands, skills, helper scripts, published plugins — when you want real defects found and staged as numbered items to approve, not silently fixed. Proposes only; /skill-forge-apply applies what you approve.
---

Audit your own Claude work, find what is actually wrong with it, and stage the
fixes as numbered items the user can approve one by one.

**You propose. You never apply.** `/skill-forge-apply` does the applying, after
the user has said yes. Writing a change into a command file here would mean
shipping an edit they never saw.

Optional arguments:

- a single skill name to audit alone (`/skill-forge my-command`)
- `--dry-run` to do the whole audit and stage the proposals, but write nothing
  to the proposals inbox

## Step 1 — read what exists

```bash
date "+%Y-%m-%d %H:%M:%S %Z"
ls ~/.claude/commands/*.md ~/.claude/skills/*/SKILL.md ~/.claude/bin/* 2>/dev/null
```

Read **every** command and skill file in full, plus any helper script they call.
Skimming produces generic advice; the whole value here is specificity.

If any of this work is published — a plugins repo, a marketplace — fetch the
published copy of each file and **diff it against the local one**. Drift between
the two is itself a finding: a local version written for you and a published
version written for strangers can silently diverge until a fix lands in only
one of them.

## Step 2 — find real defects, not polish

For each skill, hunt for the failure modes that actually bite:

| Look for | Example of the real thing |
|---|---|
| Documented behaviour that is not wired up | An argument described in the header that the procedure never passes through |
| A tool called before it is loaded | Deferred MCP tools invoked without a `ToolSearch` step first |
| Stale facts | A path, count, price, or "as of" date that has since moved |
| Silent no-ops | A step that does nothing when its precondition fails, and says nothing |
| Guidance that costs time or money | Advice that was right for tokens and wrong for wall clock |
| Missing failure modes | What happens when the file is absent, the login expired, the list is empty |

Two rules that keep this honest:

- **Every proposal needs a quotable change.** Not "improve the error handling"
  but the exact replacement text. If you cannot write the change, you have not
  found a defect, you have found a feeling. Drop it.
- **Never claim a measured improvement.** There is no telemetry in this loop.
  You cannot know that a change made anything faster or cheaper. Say "should"
  and say why, or say nothing. A fabricated benchmark is worse than no proposal.

## Step 3 — propose new skills, with evidence

Look for recurring manual toil in the actual record, not in your imagination:
memory files, recent transcripts, and any rule currently written as "remember
to do X every time" — those are skills waiting to be written.

Each idea must cite the specific file or memory that shows the need. An idea
with no citation is a guess; do not propose it. Reject anything an existing
command already covers.

## Step 4 — stage the diffs

Write the full detail to `~/.claude/skill-forge/proposals-<YYYY-MM-DD>.json`:

```json
{ "generated": "<ISO timestamp>",
  "items": [
    { "id": "SKILL-001", "target": "~/.claude/commands/my-command.md",
      "kind": "improve", "title": "<short>", "why": "<one sentence>",
      "anchor": "<exact existing text to locate the edit>",
      "change": "<exact replacement or insertion>",
      "publish": true, "confidence": "high" } ] }
```

`anchor` must be text you have literally seen in the file this run.
`/skill-forge-apply` refuses an item whose anchor no longer matches — that is
the guard against applying a stale proposal to a file that moved underneath it.

Create the directory if it does not exist. This file is the payload; the inbox
entry is only the summary the user reads.

## Step 5 — hand off to one inbox

Append a numbered summary of each item to `~/.claude/skill-forge/PROPOSALS.md`.
If the user already keeps a single review file they actually read, append to
that instead — **never create a second queue they have to remember to visit.**

Each item reads:

```
SKILL-001 improve my-command
  What: <one line, plain>
  Why:  <the defect, one line>
  Risk: <what breaks if this is wrong, or "low, text only">
  Reply "SKILL-001 yes" to apply, "no" to drop it.
```

**Cap at four items per run.** More than that and the user skims instead of
deciding, and the whole loop stops working. Rank by defect severity and hold
the rest in the staged JSON as `parked`, so nothing is lost and the next run
can repropose them.

`SKILL-` IDs are never renumbered and never reused. Before assigning one, scan
the inbox and the previous `proposals-*.json` files for the highest ID used.

## Step 6 — report

Short. What you read, how many items you staged, what you dropped and why, and
the one finding you would act on first. Say plainly if a skill came back clean;
"nothing wrong with it" is a real result, not a gap in the audit.

## Hard rules

- **Never edit a command file.** Proposing is this skill's entire job.
- **Never push anywhere.** That is `/skill-forge-apply`, after approval.
- **Nothing naming the user's clients, employers, or private projects** goes
  into a proposal marked `"publish": true`. If a fix needs private detail, mark
  it `"publish": false` and say why.
- **No new queue.** If something cannot reach the inbox, say so out loud rather
  than parking it somewhere the user will not look.
