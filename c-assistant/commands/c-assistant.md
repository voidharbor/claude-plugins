---
description: Use when the user asks what their other Claude sessions are waiting on, says they have too many sessions running, wants a triage of open sessions, or asks "what needs my input". Reads every recent session transcript and reports which ones are blocked on them, ordered by what unblocks the most.
---

People who run several Claude Code sessions at once lose track of which ones are
sitting there waiting on an answer. Your job is to read them and hand back one
short list: **what each session wants from the user, and what they should say.**

You are the assistant, not the worker. You report. You do not do the other
sessions' work, and you do not answer on the user's behalf.

Optional argument: a time window (`6h`, `2d`) or a topic filter. Default 12 hours.

## Procedure

### 1. Timestamp first

```bash
date "+%Y-%m-%d %H:%M:%S %Z"
```

Transcript ages are the whole signal here. Do not reason about "live" or "stale"
from anything but a real clock reading.

### 2. Scan the transcripts

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session-scan.py" --hours 12 --self <your-own-session-id>
```

Your session ID is in your system prompt — the scratchpad path contains it. Pass
it, otherwise you report yourself back as a session needing input.

The scanner reads only the tail of each transcript, so a 70 MB session costs
nothing. For any session where the tail is not enough to understand the ask:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session-scan.py" --full <session-id-prefix>
```

### 3. Count what is actually running

```bash
ps -eo pid,etime,command | grep "[c]laude" | grep -v bg-pty-host
```

That is the live-process count. Compare it to the number of transcripts touched
in the last ~30 minutes; they should roughly agree. A transcript touched 3 hours
ago with no matching process is a closed window, not a waiting session — say so
rather than putting it on the action list.

**Do not try to map a PID to a session.** Sessions started from the same
directory all report the same cwd, and start times do not line up with transcript
timestamps. Suggesting a `kill` here is a coin flip on somebody's live work. If
the user wants one gone, they close that terminal window themselves.

### 4. Judge each session

The scanner's `state:` line is a keyword heuristic and it is wrong maybe a third
of the time — it flags any reply containing a question mark. Read the actual last
reply before you classify anything. What you are deciding is:

| Read the last reply and ask | Then |
|---|---|
| Is there a real question with real options in it? | **Blocked** — list it, with the options |
| Is it waiting on something only a human can do (a password, a click in a browser they are logged into, a phone call, a purchase)? | **Blocked on their hands** — list separately, these can be knocked out in a batch |
| Was it interrupted mid-turn? | **Needs a nudge** — say what it was doing when it stopped |
| Did it finish and just narrate what it did? | **Done** — one line, or omit |
| Is it offering a nice-to-have follow-up ("say the word and I'll...")? | **Optional** — group at the bottom, do not make it look urgent |

### 5. Look across sessions, not just within them

This is the part a single session cannot do for itself, and it is most of the
value of running this.

- **Duplicate work.** Two sessions attacking the same problem from different
  angles, neither knowing about the other. Say which one is further along.
- **Contradictions.** One session concluded something is impossible while another
  is still building toward it. The user needs to know before answering either.
- **One answer that unblocks several.** If three sessions are stuck behind the
  same missing credential, that is one action, not three. Lead with it.
- **Stale premises.** A session asking about something already resolved in a
  different window an hour later.

### 6. Report

Straight into the chat. Not a file, not an artifact — they asked here.

Order by **what unblocks the most work**, not by recency. For each blocked
session give:

- A short handle for it (`the email sender one`), then the 8-char session ID
- One sentence on where it stands
- **The actual question, in its own words if it was well put**
- Your recommendation if you have grounds for one, marked as yours

Then a short "safe to ignore" section so they know you looked and there is
nothing there. End with the cross-session flags from step 5 if any.

Keep it scannable. This is read to decide where to spend the next twenty
minutes, not to be studied.

## Hard rules

- **Never kill, resume, or send input to another session.** Not via `kill`, not
  via `--resume`, not by writing to its transcript. Resuming a live session's
  transcript forks it and loses work.
- **Never answer a question on the user's behalf**, even an obvious one. The
  session asked *them*.
- **Never do the pending work yourself.** If a session is blocked on a design
  decision, you do not go make the design. You report that it is waiting.
- **Do not read another session's transcript for anything but triage.** Sessions
  often span separate clients, employers, or confidentiality boundaries.
  Reporting "this session is waiting on X" is fine. Carrying details sideways
  into a context where they do not belong is not.
- **Quote, do not paraphrase, when the question has specific options in it.**
  "It wants you to pick A or B" is useless. Say what A and B are.

## Notes

- Transcripts live in `~/.claude/projects/<encoded-project-path>/*.jsonl`. The
  nested `subagents/` directories are agent and workflow transcripts, not
  sessions — the scanner already skips them.
- A ~150-byte transcript is a session that opened and never got a prompt. Ignore.
- The `cwd:` line usually tells you the project faster than the topic does.
- If asked to actually go handle one of the items, that is a new task — do it in
  this session and say which session it duplicates, so the other can be closed.
