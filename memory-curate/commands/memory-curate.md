---
name: memory-curate
description: Use when the user asks to clean up, curate or audit what Claude remembers across sessions, says their memory has drifted or gone stale, asks what Claude believes that is no longer true, or wants recent sessions mined for facts worth keeping. Proposes only - never writes until specific numbered items are approved.
---

# Memory curation

Audit the per-project memory stores under `~/.claude/projects/*/memory/` and propose changes.

**This is a curator, not a miner.** The default failure mode of anything that reads transcripts
and writes memory is monotonic growth: it only ever adds, the index stops being scannable, and
every session in every project pays context tax for facts the user already knew. Pruning,
correcting and merging matter more than adding. **A run that proposes zero additions and four
archives is a good run.**

## Hard rules

1. **Never write anything until the user approves specific numbered items.** Present the full
   list, wait for a reply, then apply only what was picked.
2. **Additions may only come from the user's own typed words**, and you must quote the turn you
   took it from. Never create a memory from something *you* or a subagent concluded. Transcripts
   are full of claims that got corrected an hour later. An assistant claim can be used to
   *contradict* an existing memory, never to assert a new one.
3. **Archive, never delete.** `ARCHIVE` moves the file to `<store>/_archive/` with a date suffix
   and removes its index line.
4. **Snapshot before writing.** `cp -R <store> <store>.bak-YYYYMMDD-HHMM` first. It is a few
   hundred KB.
5. **Cap additions at 5 per run** and state how many candidates the cap dropped. Never truncate
   silently.
6. Never edit `MEMORY.md` beyond adding, removing or rewording index lines.

## Step 1 - scan

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory-scan.py" --days 30 --top 120
```

`--days N` for a different window, `--top N` to widen the candidate pool, `--json` to
post-process. The script is deterministic and read-only. It inventories every store, runs
structural checks, verifies every filesystem path named inside memory, and ranks the user's typed
turns by durability markers.

It deliberately filters out anything the user did not type — skill bodies, command output and
subagent turns are marked `isMeta` / `sourceToolUseID` / `isSidechain` in the transcript, so
excluding them is exact rather than heuristic. That is what makes rule 2 a guarantee.

## Step 2 - read the corpus

Read every `.md` in the largest store (listed first in the scan output) and the index of each
satellite. Skip `_archive/`. You need the whole corpus in context to judge duplication and
contradiction.

For anything flagged as a stale filesystem ref, **confirm it yourself before proposing a change**
— the path may have moved rather than vanished, and paths on a remote host, a container or another
machine are correct as written but will still show up. `ls` the parent directory.

## Step 3 - build proposals

| Type | When |
|---|---|
| `ADD` | A durable fact in the user's own words that no existing memory covers. Max 5. |
| `UPDATE` | An existing memory is stale, wrong, or was superseded. Show a before/after diff and the evidence. |
| `SPLIT` | A file has grown past ~15 KB and stopped being one fact. Propose the split and the resulting index lines. |
| `MERGE` | Two files cover the same thing. |
| `ARCHIVE` | Obsolete: the project shipped, the question resolved, the one-off passed. |
| `PROMOTE` | A genuinely global fact is trapped in a project store where it only loads if the user happens to open that folder. |
| `DEMOTE` | A narrowly project-specific fact sits in the main store, taxing every session. |

Evidence is mandatory on every item: either `file.md:line` for corpus-derived items, or a quoted
turn with its date for transcript-derived ones.

**Do not propose churn.** Rewording a memory that is still accurate is not an improvement. If
nothing is wrong, say so.

### Watch the boundaries

If the user works across separate clients, employers or organisations, a `PROMOTE`/`DEMOTE` can
move information somewhere it should not be — a project store gets opened on shared screens.
Flag any cross-boundary move as a decision for the user rather than applying it silently.

## Step 4 - present

Numbered list grouped by type, ordered by impact — corrections to things that are actively wrong
first, cosmetics last. Per item: the claim, the evidence, and the exact change. Keep it terse.

End with: reply with the numbers to apply (`1-4, 7, 9`), `all`, or `none`.

## Step 5 - apply

Only after the reply. Snapshot first, then apply only the approved numbers, then report what
changed in one short block: files touched, index lines moved, archive contents. If an item turned
out to be unapplyable, say which and why rather than quietly skipping it.

## Requirements

Python 3 and a Claude Code install that has written transcripts. Transcripts are read strictly
read-only; nothing under `~/.claude/projects/*/memory/` is written without approval.
