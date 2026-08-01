---
description: Use when the user asks what they have built, wants an inventory of their own commands/skills/agents/hooks, asks "what skills do I have", or needs to know which of their work is safe to share publicly. Also the first step before publishing anything to a plugin marketplace.
---

Inventory everything **the user authored** for Claude, sorted along one axis:
**generic → personal → private**.

Optional argument filters the output:
- no argument → the full inventory
- `generic` / `personal` / `private` → only that tier
- a name (e.g. `mac-control`) → the deep read on that one item

Do not report anything they merely *installed*. Other people's plugins are not
their work. Note them in a one-line footer, never in the table.

## Where their work lives

Scan all of these. Missing directories are normal — say "none" and move on, do not
treat it as an error.

| Source | Path |
|---|---|
| User commands | `~/.claude/commands/*.md` |
| User skills | `~/.claude/skills/*/SKILL.md` |
| Subagents | `~/.claude/agents/*.md` |
| Project-scoped | `<project>/.claude/{commands/*.md,skills/*/SKILL.md,agents/*.md}` |
| Hooks | the `hooks` key in `~/.claude/settings.json` and `settings.local.json` |
| Scheduled routines | the `/schedule` skill, or https://claude.ai/code/routines |

Two traps:

- **Parse settings JSON, never grep it.** The word `hooks` also appears inside
  permission strings and webhook URLs, so grep reports hooks that do not exist.
- **Project paths contain spaces.** Use
  `find ~ -maxdepth 5 -type d -name ".claude" -print0` piped to a null-delimited
  read, or the loop silently shreds every path.
- **`CronList` is session-scoped** and will report nothing for cloud routines.
  It is not evidence that none exist.

## The three tiers

The axis is **how much of the author's private world you must already have for
this to run.**

**1 — Generic.** Runs on a stranger's machine unmodified. Names no person, no
organization, no account, no absolute path in someone's home directory. May
require a common dependency (an MCP, a browser extension, a tool) as long as it
is one anybody can install.

**2 — Personal.** Assumes *this user's* setup — their home directory, their
folder layout, their installed MCPs, their habits — but is not welded to any one
organization or account. A stranger could use it after a find-and-replace.

**3 — Private.** Welded to one organization, account, customer, or document.
Names a company, a client, a phone number, a rate sheet, a self-hosted host, an
internal system, a campaign ID. Useless to anyone else and unsafe to publish.

## How to classify — run the test, do not eyeball it

Build the tier-3 pattern from what you can discover plus what the user tells you.
**Ask once, up front:** "Which organizations, clients, products, or internal
system names should I treat as private?" Their answer joins the pattern below.
If they decline to answer, say the private-entity scan is running on generic
signals only and is therefore weaker.

```bash
# Tier-3 signals that need no configuration
grep -niE '[a-z0-9.-]+\.(com|net|org|io|dev|app|co)|[0-9]{3}[-.][0-9]{3}[-.][0-9]{4}|[a-z0-9._%+-]+@[a-z0-9.-]+|(api[_-]?key|secret|token|password|passwd|bearer)[^a-z]|[0-9]+ [A-Z][a-z]+ (St|Ave|Rd|Dr|Ln|Blvd)|\b[0-9]{6,}\b' FILE

# Tier-2 signals: this machine and this person
grep -niE "$USER|$HOME|/Users/[a-z]|/home/[a-z]|MacBook|iMac" FILE
```

Also flag any **capitalized multi-word proper noun** that is not a well-known
product — those are usually company, client, or project names the generic
patterns miss.

Then **read every hit before it counts.** Three kinds do not:

- **Self-match.** This file lists the patterns, so it matches itself. Anything
  inside a fenced code block is the classifier, not a finding. Skip fences.
- **Generic placeholder.** `example.com`, `555-0100`, `Acme`, `foo@bar.com`.
- **Illustrative mention.** A name in a for-instance list is not a dependency.

**Mention ≠ dependency, and only dependency is tier 3.** Ask: if that entity
vanished, would the command still work?
- Still works → the name is a **mention**. Tier 2, flagged as one line to scrub.
- Breaks → it is a **dependency**. Tier 3.

So:
- any tier-3 **dependency** → **Private**
- else any tier-2 hit, or a tier-3 mention → **Personal**
- else → **Generic**

Grep is the floor. It cannot see an unnamed specific — "the rate sheet in the
shared drive", "the office line", "the usual client". If the prose assumes a
resource only this user has, promote the tier and say which line did it. Always
quote the deciding line so they can argue with the call.

**A credential, key, or ID number is never merely a mention.** It is Private on
sight, and say so loudly — that is the finding people actually need.

## Output

Sorted **most generic first**, so the publishable ones are at the top and the
locked ones are at the bottom. Tiers as section headers.

```
## 1 — Generic · safe to publish as-is
| Item | Does | Needs |
|---|---|---|

## 2 — Personal · publishable after a scrub
| Item | Does | What ties it to you |
|---|---|---|

## 3 — Private · never publish
| Item | Does | What locks it |
|---|---|---|
```

Close with one line: total count, how many are publishable today, and how many
would be after a scrub. Then the footer naming installed-not-authored plugins.

If asked about one item by name, skip the table: give what it does, its tier,
the exact lines that set the tier, and what a scrub would have to change.

## Getting it wrong

- **Do not guess a tier from the name.** A command called `mac-control` sounds
  generic and may be hardcoded to one person's credential paths.
- **Do not mark something Generic because the description reads clean.** The
  description is two lines of a long file. Scan the body.
- **Do not silently skip a source that came back empty.** "No skills directory
  yet" is a finding; a missing row reads as an oversight.
- **Do not rank within a tier.** The three tiers are the whole sort. Ordering
  inside them is noise.
