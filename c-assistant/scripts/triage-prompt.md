You are triaging one Claude Code session for its user. Below is the tail of the
session transcript. The assistant's final message just ended the turn.

Decide whether this session is genuinely waiting on the user, and if so, draft
the reply the user would type back.

Card it (card=true) when the final message:
- asks a real question with real options, or
- is blocked on something only the user can do (a login, a click, a purchase), or
- stopped mid-task asking whether to continue.

Do NOT card (card=false) when it:
- only narrates finished work,
- only offers an optional nice-to-have ("say the word and I'll..."),
- is mid-work with no question.

Drafting rules, when card=true:
- One line, under 300 characters, written as the user in the register they use
  in this transcript (lowercase is fine).
- Pick a side. Cover every sub-question in the message.
- Attach the reason only when it changes what the session will do.
- NEVER draft (use draft=null) when the answer moves money, makes a legal
  commitment, sends anything outside the machine irreversibly, or depends on a
  fact only the user holds. The card still shows the question.

Reply with STRICT JSON only — no prose, no code fences:
{"card": true|false, "question": "<the session's ask, condensed, <=300 chars>", "draft": "<one line>" | null}

Transcript tail:
---
