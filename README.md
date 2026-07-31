# claude-plugins

Seven small commands for [Claude Code](https://claude.com/claude-code). Five are a
single markdown file with no dependencies; `c-assistant` and `refresh` each also ship
one Python script. Nothing to build either way.

## Install

```
/plugin marketplace add voidharbor/claude-plugins
/plugin install efmtu@voidharbor
```

Install only what you want; each plugin is independent.

## The plugins

| Plugin | What it does | Needs |
|---|---|---|
| **efmtu** | *Easy For Me To Understand.* Answers short and simple — three sentences or five bullets, answer first, plain words. | nothing |
| **my-skills** | Inventories everything *you* have authored (commands, skills, agents, hooks, routines) and sorts it generic → personal → private, so you know what is safe to publish. | nothing |
| **chrome-tabs** | Closes the Chrome tabs the current session opened, and only those. Stops agents leaving orphaned "✅ Claude" tab groups behind. | [Claude in Chrome](https://claude.com/chrome) extension |
| **mac-control** | Drives native macOS apps via the computer-use MCP — Word/Pages PDF export, Finder, Preview, Messages, System Settings. | computer-use MCP, macOS |
| **ultracode-lite** | Runs multi-agent `Workflow` orchestration on a lean budget: scout inline, fan out narrow, set model and effort on every agent, pipeline instead of parallel. | `Workflow` tool |
| **c-assistant** | Triages every session you have open and reports which are blocked on you — the question each one asked, what only you can do, and where two sessions are duplicating work. | Python 3 |
| **refresh** | Shows the last prompt you actually typed, word for word, read from the transcript on disk — so it survives context being summarized. | Python 3 |

## Notes on five of them

**`c-assistant`** is for people who keep five or ten sessions going and lose track
of which ones are waiting on an answer. It reads only the tail of each transcript,
so a 70 MB session costs nothing, then sorts what it finds by what unblocks the
most work rather than by recency. It will not kill, resume, or reply to another
session, and it will not answer a question on your behalf — the session asked
*you*. The part worth having is the cross-session pass: two sessions solving the
same problem separately, or one that concluded something is impossible while
another is still building toward it.

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

Claude Code with plugin support. `mac-control` is macOS-only; the rest are
platform-independent.

## License

MIT
