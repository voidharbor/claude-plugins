---
description: Use when the user asks what they last asked, what their last prompt or last message was, what they told this session, where things were left, or says they lost track / forgot what they were doing here. Also covers wanting the verbatim wording of an earlier request back.
---

Show the user the last thing they actually typed, word for word.

People who run several Claude Code sessions at once lose track of which session
they told what. This hands it straight back to them.

## Why not just scroll up

Because you often cannot. After a long session the context gets summarized, and the
exact wording of what they asked is gone from what you can see — you have a paraphrase
at best. The `.jsonl` transcript on disk still has it exactly as typed. **Always read
it from disk. Never reconstruct their prompt from memory or from the summary.** A
plausible-sounding paraphrase is the one failure mode this command exists to prevent:
they are asking precisely because they want the real wording, not your version of it.

## Run it

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/last-prompt.py"
```

That is the whole job in the default case. It finds the current session on its own via
the `CLAUDE_CODE_SESSION_ID` environment variable, so it works even with a dozen
sessions open — no guessing by file modification time.

| They asked for | Flag |
|---|---|
| the last thing they said (default) | *(none)* |
| the last few, to see where things were going | `-n 5` |
| what they last said *anywhere*, not just here | `--all` |
| a specific session | `--session <id>` |

`--all` and `-n` combine. Run `--help` for the full list.

Slash commands count as prompts and print as `/name args`. `/refresh` itself never
does, or this would just report itself.

## What to say back

Print what the script returned, then **one line** of your own: where that request
currently stands. Answer the question they are really asking, which is "did that get
done?" — not just "what did I say?".

Keep it to the one line unless they ask for more. They want the reminder, not a recap
of the session.

> **Last prompt, 44 minutes ago:**
> "add retry logic to the upload path and make the timeout configurable"
>
> Retries are in and tested; the timeout is still hardcoded at 30s.

If the script reports no earlier prompt, say so plainly — that means `/refresh` is
the first thing sent in this session, so there is nothing to show yet. Do not go
hunting through other sessions to find them something; offer `--all` and let them
choose.

## Requirements

Nothing beyond Python 3 and a Claude Code session that has written a transcript.
Transcripts are read strictly read-only.
