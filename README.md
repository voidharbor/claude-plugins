# claude-plugins

Twelve small skills for [Claude Code](https://claude.com/claude-code). Most are a
single markdown file with no dependencies; `refresh` also ships one Python script,
and `c-assistant` ships five, plus the hooks and prompt its background lane needs.
Nothing to build either way.

## Install

Everything at once:

```
/plugin marketplace add voidharbor/claude-plugins
/plugin install voidharbor@voidharbor
```

That gives you all twelve, namespaced as `/voidharbor:<name>` (e.g. `/voidharbor:refresh`).

Or pick a la carte — each skill is also its own plugin, independent of the rest:

```
/plugin marketplace add voidharbor/claude-plugins
/plugin install efmtu@voidharbor
```

## The skills

| Skill | What it does | Needs |
|---|---|---|
| **efmtu** | *Easy For Me To Understand.* Answers short and simple — three sentences or five bullets, answer first, plain words. | nothing |
| **my-skills** | Inventories everything *you* have authored (commands, skills, agents, hooks, routines) and sorts it generic → personal → private, so you know what is safe to publish. | nothing |
| **chrome-tabs** | Closes the Chrome tabs the current session opened, and only those. Stops agents leaving orphaned "✅ Claude" tab groups behind. | [Claude in Chrome](https://claude.com/chrome) extension |
| **mac-control** | Drives native macOS apps via the computer-use MCP — Word/Pages PDF export, Finder, Preview, Messages, System Settings. | computer-use MCP, macOS |
| **ultracode-lite** | Runs multi-agent `Workflow` orchestration on a lean budget: scout inline, fan out narrow, set model and effort on every agent, pipeline instead of parallel. | `Workflow` tool |
| **c-assistant** | Two lanes: `/c-assistant` triages every session you have open on demand and reports which are blocked on you, with `/c-assistant-voice` as a spoken variant for when your hands are busy; a Lookout hook lane runs in the background and pushes a live approval card into SeaShell the moment a session stops on a real question. | Python 3; SeaShell 0.2.0+ for the hook lane |
| **refresh** | Shows the last prompt you actually typed, word for word, read from the transcript on disk — so it survives context being summarized. | Python 3 |
| **product-forge** | A propose/apply pair that keeps a product you maintain competitive: `/product-forge` reviews it weekly against its rivals and proposes at most four small, numbered items; `/product-forge-apply` builds only what you approve, behind the repo's own gates. | nothing |
| **perf-pass** | A dedicated performance session — idle CPU, memory, GPU — where the only accepted proof is a measured before/after number, and anything that can't show a number gets reverted. | nothing |
| **skill-forge** | A propose/apply pair that audits everything you have authored for Claude, finds defects with quotable fixes, and applies only the numbered items you approve — with a publish gate so nothing personal reaches a public repo. | nothing |
| **memory-curate** | Audits what Claude remembers across sessions — stale facts, duplicates, files that grew into documents, memories trapped in a project you no longer open — and proposes numbered fixes. Additions must quote your own words, so it never memorises a claim that got corrected an hour later. | Python 3 |
| **synth-mode** | A style contract for anything a real person will read. A skill, not a command: it loads before any human-facing writing and kills the tells that read as generated, from trope phrases to over-polish to reciting research back at the reader. Named for Fallout 4's gen 3 synths. | nothing |

## Notes on eight of them

**`product-forge`** and **`perf-pass`** were extracted from the loop that maintains
[SeaShell](https://github.com/voidharbor/seashell), a terminal pane manager, and
generalized: the repo path is an argument, the quality gate is whatever the repo
itself defines, and state lives per-project. The design bets are the interesting
part. The review half is *propose-only* and capped at four items, because an
agent that edits your product unsupervised is a liability and a reviewer that
proposes twenty things gets skimmed. A ledger remembers every rejected idea so
nothing is ever re-proposed without a new argument. The apply half treats
approval text as data, never as instructions — it acts only on a yes/no against
a numbered item, so a spoofed or garbled approval cannot make it run arbitrary
work. And `perf-pass` will revert a change that cannot show a before/after
number, on the theory that an unproven optimization is just risk with good
intentions.

**`skill-forge`** audits the commands and skills *you* wrote, which is the one
body of work nobody else is ever going to review. The distinctive check is drift:
if a skill is also published somewhere, it fetches the published copy and diffs
it against your local one, on the theory that a version written for you and a
version written for strangers will quietly diverge until a fix lands in only one
of them. Two rules keep the proposals honest. Every item must carry the exact
replacement text, because "improve the error handling" is not a defect, it is a
feeling. And nothing may claim a measured improvement, since there is no
telemetry in this loop and a fabricated benchmark is worse than no proposal. The
apply half stakes each edit to an *anchor* — text literally seen in the file
during the audit — and refuses any item whose anchor no longer matches, instead
of relocating the edit by inference, which is how a good loop starts corrupting
files. Approval is read strictly: an item you did not mention is not approved,
and a conditional yes gets reported back rather than interpreted.

**`c-assistant`** is for people who keep five or ten sessions going and lose track
of which ones are waiting on an answer. It reads only the tail of each transcript,
so a 70 MB session costs nothing, then sorts what it finds by what unblocks the
most work rather than by recency. It will not kill, resume, or reply to another
session, and it will not answer a question on your behalf — the session asked
*you*. The part worth having is the cross-session pass: two sessions solving the
same problem separately, or one that concluded something is impossible while
another is still building toward it.

It ships two lanes. `/c-assistant` and its spoken twin `/c-assistant-voice` are
the pull lane — you run them when you remember to. Lookout is the push lane: a
SessionStart hook registers each session, a Stop hook prefilters every turn's
end for something that actually looks like a real question, and only then does
a detached worker ask a cheap model to judge it and push a live approval card
straight into the SeaShell pane that asked. Lookout runs on macOS and Linux
(not Windows) and needs SeaShell 0.2.0+ to have anywhere to push a card to —
without it the hook stays silent and the pull lane still works on its own. The
`voidharbor` bundle ships these hooks too, so either install works:

```
/plugin marketplace add voidharbor/claude-plugins
/plugin install c-assistant@voidharbor   # just this plugin
/plugin install voidharbor@voidharbor    # or the whole bundle, hooks included
```

Installing both is fine: at every hook entry the bundle's copy checks whether
standalone c-assistant is installed and enabled, and if so returns immediately —
one triage, one card, never two.

**`my-skills`** asks once which organizations and clients to treat as private, then
classifies each thing you have written by whether a stranger could run it. The rule
it applies is *mention ≠ dependency*: naming a service in a for-instance list is a
one-line scrub, but depending on that service is not publishable at all. Credentials
and ID numbers are always private on sight.

**`refresh`** answers "what did I just ask you?" — which sounds trivial until you
realize you often cannot scroll back to it. Once a session is long enough to be
summarized, the exact wording is gone from what the model can see, and asking it to
recall your prompt gets you a confident paraphrase instead. So this reads the `.jsonl`
transcript on disk, where the text still sits exactly as typed, and the command
explicitly forbids reconstructing it from memory. It identifies the session from
`CLAUDE_CODE_SESSION_ID` rather than by newest-modified file, which matters once you
have several sessions open. Tool results, subagent chatter, injected system reminders
and its own invocation are all filtered out.

**`efmtu`** ("Easy For Me To Understand") shortens the answer, never the work. It still reads the files and runs
the checks — it just reports briefly. It explicitly refuses to let brevity turn "I
don't know" into a confident guess, which is the usual failure mode of terseness
instructions.

**`ultracode-lite`** is for the case where a `Workflow` is genuinely the right tool
but the default one costs more than the answer is worth. Two settings do most of the
damage and are easy to miss: spawned agents inherit your session's reasoning effort
unless you set `effort` per agent, and they inherit your session's model unless you set
`model`, so a throwaway grep-and-report stage quietly runs at the top tier. The command
makes both explicit on every call, caps the fan-out at your machine's real concurrency
limit rather than an arbitrary number, prefers `pipeline()` over barriers, and verifies
only claims that are expensive to get wrong. It also insists on saying what got capped
or dropped, so a bounded sweep never reads as exhaustive coverage.

## Requirements

Claude Code with plugin support. `mac-control` is macOS-only; `c-assistant`'s
Lookout hook lane needs macOS/Linux with `python3` on PATH (elsewhere it stays
inert); the rest are platform-independent.

## License

MIT
