---
description: Use when a product you maintain needs a recurring competitive review — what the tools people actually choose ship that yours does not — and you want the findings as a short list of numbered items to approve or reject, not as edits. Proposes only; /product-forge-apply builds what you approve.
---

Keep a product competitive without letting it sprawl.

Argument: the path to the repo to review. With no argument, use the current
directory if it is a git repo; otherwise stop and ask.

You are auditing that repo against the products people actually choose instead
of it, and proposing a **small** number of concrete improvements.

**This command proposes. It never edits source, never commits, never pushes.**
`/product-forge-apply` does that, and only for items the user approved by number.

---

## Step 0 — read the ground truth first

Do not research before you know what already exists. In order:

1. The repo's README.
2. `git log --oneline -20`.
3. Any design doc or roadmap in the repo — especially a deferred or won't-do
   list. Everything there was already costed and consciously cut.
4. `~/.claude/product-forge/<repo-name>/ledger.json` — every idea previously
   proposed, with its outcome. Create it as `{"proposed": []}` if missing.

An idea that is already built, already deferred with a stated reason, or already
in the ledger as rejected **must not be proposed again**. Re-proposing something
the user already said no to is the fastest way to make them stop reading these.

## Step 1 — research the field

Work out the competitive set from the README's own positioning — what does this
product describe itself as an alternative to? Then use WebSearch: the rivals'
release notes and docs, plus whatever forum and community threads from the last
year say people actually switch for.

You are looking for two things specifically:

- **Table stakes the product is missing** — the thing a reviewer would call out
  immediately. These matter more than novelties.
- **Small high-leverage features** — something under a few hundred lines that
  changes daily use.

Ignore anything that is a whole product direction (a cloud service, a plugin
ecosystem, a config language, collaboration). Those are strategy decisions, not
review findings.

## Step 2 — filter hard

Every candidate must pass **all** of these. Write the verdict per item; do not
silently drop things.

| Test | Fails if |
|---|---|
| **Small** | More than roughly 300 lines, or touches more than ~4 files |
| **No heavy dependency** | Needs a new runtime, a WASM blob, or a large library |
| **Keeps the security posture** | Widens an attack surface, relaxes a CSP or sandbox, adds a new privileged surface, or lets untrusted bytes become markup |
| **Keeps the product's identity** | Reverses a design decision the repo records as deliberate |
| **Actually useful to the owner** | Score against how the owner really uses it — the README and commit history tell you — not against a general audience |
| **Not already deferred** | Appears in the deferred list with a stated reason, unless you have a genuinely new argument — and then say what changed |

Cap the output at **4 items**. Fewer is better. A week with one strong proposal
beats a week with six mediocre ones. If nothing clears the bar, say so and
propose nothing — that is a valid and useful outcome.

## Step 3 — write the proposals

Append to `~/.claude/product-forge/<repo-name>/PROPOSALS.md`, under a heading
`## Awaiting your yes or no`.

**One inbox.** If the user already keeps a single review file they actually
read, append to that instead — never create a second queue they have to
remember to visit. A queue nobody visits is where proposals go to die.

Format each item exactly like this, with `<NAME>` an uppercase slug of the repo:

```
- <NAME>-<n>: <one-line what it is>
  WHY: <what it changes about a real day of use, in one or two sentences>
  WHO HAS IT: <which rivals ship this, so the owner can judge whether it is table stakes>
  COST: <files touched, rough line count, any new dependency>
  RISK: <what could regress, or "none identified">
  IF YES: reply "<NAME>-<n> yes" — /product-forge-apply implements it, runs the
  repo's own gate, and pushes. If anything fails it stops and reports instead.
```

Number continues from the highest ever used — read the ledger, do not restart
at 1.

## Step 4 — update the ledger

Write every proposed item to the ledger:

```json
{"proposed": [
  {"id": "NAME-1", "title": "...", "date": "...",
   "status": "awaiting", "source": "which rival", "estLines": 120}
]}
```

`status` is one of `awaiting`, `approved`, `rejected`, `shipped`. Only
`/product-forge-apply` moves an item past `awaiting`.

## Step 5 — report

Print a short summary: what you researched, what you rejected and why, what you
proposed, and where the proposals file is. Keep it to a screen.

---

## Rules that are not negotiable

- **Propose only.** No edits to the repo, no commits, no pushes.
- **One approval inbox.** Proposals go to the proposals file, nowhere else.
- **Never re-propose a rejected item** without a genuinely new argument.
- **Nothing about the user's other projects, clients, or businesses** goes into
  this repo, its issues, or anything staged for it. Sessions often span
  confidentiality boundaries; this loop must not carry material across one.
- If the repo has uncommitted changes, say so and stop — do not audit a dirty
  tree and propose work on top of something half-finished.
