# claude-plugins

Five small commands for [Claude Code](https://claude.com/claude-code). Each one is
a single markdown file — no dependencies, nothing to build.

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

## Notes on two of them

**`my-skills`** asks once which organizations and clients to treat as private, then
classifies each thing you have written by whether a stranger could run it. The rule
it applies is *mention ≠ dependency*: naming a service in a for-instance list is a
one-line scrub, but depending on that service is not publishable at all. Credentials
and ID numbers are always private on sight.

**`efmtu`** ("Easy For Me To Understand") shortens the answer, never the work. It still reads the files and runs
the checks — it just reports briefly. It explicitly refuses to let brevity turn "I
don't know" into a confident guess, which is the usual failure mode of terseness
instructions.

## Requirements

Claude Code with plugin support. `mac-control` is macOS-only; the rest are
platform-independent.

## License

MIT
