---
description: Use when a multi-agent Workflow is about to be launched and cost or latency matters, or when the user wants workflow horsepower without a full-scale orchestration budget.
---

Do the task given as the argument, using the Workflow tool, but under the lean
budget below. Same structure as a full orchestration, a fraction of the spend and
wall clock.

If no argument was given, ask what to run — do not launch a workflow on a guess.

## The one-line version

Scout inline first, fan out **narrow**, run every agent on the **cheapest tier and
lowest effort that can do its job**, `pipeline()` instead of `parallel()`, verify
only what is expensive to get wrong.

## Establish your machine's facts first

These numbers are per-machine and per-session. Do not assume them — check, once,
before sizing anything:

| Fact | How to get it | Consequence |
|---|---|---|
| Concurrency cap | `min(16, cores − 2)`; cores via `sysctl -n hw.ncpu` or `nproc` | Fanning out beyond it does not run faster, it queues. Width above the cap is pure latency. |
| Session effort | `~/.claude/settings.json` | Agents **inherit** it unless `opts.effort` is set. If the session runs at a high effort tier, inheriting it is the single biggest waste in a default workflow. |
| Session model | The model running the main loop | Agents inherit it unless `opts.model` is set. Most stages do not need the top tier. |
| Workflow size guideline | `/config` → "Dynamic workflow size" | Lean mode caps below this. See ladder. |

## Step 1 — Decide whether to spawn anything at all

The cheapest workflow is the one not run. Do the work inline, with no Workflow call, when:

- It touches ≤3 files you can already name
- It is one search, one edit, one question, or one command
- A `grep`/`rg`/`Read` answers it
- The answer is a fact, not a judgment

Only reach for Workflow when there is **real fan-out** (many independent items) or a
genuine need for **independent perspectives**. Say in one line why a workflow is
warranted before launching it. If it is not, just do the task and say so.

## Step 2 — Scout inline before fanning out

Never pay an agent to discover the work-list. In the main loop, cheaply establish:

- the exact file paths / items / URLs in scope
- roughly how many there are
- what "done" looks like

Then pass that concrete list into the workflow via `args`. An agent handed
`["a.ts","b.ts"]` costs a fraction of one told "find the relevant files."

## Step 3 — Size the fan-out (hard ladder)

| Task shape | Agents | Verify pass |
|---|---|---|
| Known files, one dimension | **1–3** | none |
| Multi-file review, focused research, ≤10 migration sites | **4–7** | one batched verifier |
| Audit / "be comprehensive" / wide sweep | **8–12** *(ceiling)* | one verifier per finding, single vote |
| Anything larger | **ask first** | — |

Rules:
- **Never exceed 12 agents** in lean mode unless the user explicitly says "no limit"
  or asks for a full-scale run.
- **Never exceed the concurrency cap** in a single `parallel()`/`pipeline()` —
  beyond that it queues.
- Prefer **more items per agent** over more agents: batch 3–5 cheap items into one
  agent call instead of one agent per item. Every agent pays a fixed system-prompt
  and context-loading tax; batching amortizes it.

## Step 4 — Assign model and effort per agent (do not skip this)

Set `model` and `effort` on **every** `agent()` call. Defaults are the expensive path.

| Stage type | model | effort |
|---|---|---|
| Mechanical extraction, grep-and-report, file listing, formatting, schema fill | cheapest tier | `'low'` |
| Standard review, research read, per-item transform, verification | mid tier | `'medium'` |
| Final synthesis, hard architectural judgment, the one call that decides the answer | omit (inherit) | `'high'` |

At most **one or two** top-tier agents in a lean workflow, and only at the end.
If a stage's output is a list, a diff, or a yes/no, it is not a top-tier stage.

## Step 5 — Structure for speed

- **`pipeline()` by default.** Only use `parallel()` when a stage genuinely needs *all*
  prior results at once (dedup across the full set, early-exit on zero, cross-comparison).
  A barrier you did not need wastes the fast agents' wall clock.
- **Always pass `schema`.** Structured output stops agents writing essays, cuts output
  tokens hard, and removes parsing work.
- **Cap output in the prompt**: "return at most 8 items", "≤150 words", "no preamble,
  no restating the task."
- **Forbid re-discovery**: "The files are listed below. Do not search the repo."
- **Skip `isolation: 'worktree'`** unless agents actually write files concurrently
  (~200–500ms + disk each).
- **Guard with budget** when a token target was set:
  `while (budget.total && budget.remaining() > 60_000) { ... }`

## Step 6 — Verify sparingly

A full-scale orchestration runs 3–5 adversarial voters per finding. Lean mode does not.

- Verify a claim only when **being wrong is more expensive than checking** (it will be
  acted on, shipped, sent to a client, or changes a decision).
- **One** skeptic, mid tier, `effort: 'medium'`, prompted to refute.
- **Batch it**: one verifier handles up to 5 findings in a single call.
- Skip verification entirely for descriptive output (summaries, inventories, maps).

## Step 7 — Report honestly

At the end, say in 2–4 lines:

- agents spawned / models used
- what was **capped or dropped** (top-N, batch limits, skipped verification) — never let
  a bounded sweep read as exhaustive coverage
- what a full-scale run would have added, so the user can call for it if they want it

## Script skeleton (adapt, do not copy blindly)

```js
export const meta = {
  name: 'lean-review',
  description: 'Lean fan-out over a pre-scouted item list',
  phases: [{ title: 'Work' }, { title: 'Verify' }, { title: 'Synthesize' }],
}

const CAP = 10                                 // your measured concurrency cap
const ITEMS = args ?? []                       // scouted inline, passed in
const BATCHES = []                             // batch cheap items: 3-5 per agent
for (let i = 0; i < ITEMS.length; i += 4) BATCHES.push(ITEMS.slice(i, i + 4))
const WIDTH = Math.min(BATCHES.length, CAP)
if (BATCHES.length > WIDTH) log(`capped: ${BATCHES.length - WIDTH} batches dropped`)

phase('Work')
const results = await pipeline(
  BATCHES.slice(0, WIDTH),
  b => agent(
    `Files:\n${b.join('\n')}\nDo not search the repo; these are the only files in scope.\n` +
    `<the actual task>. Return at most 6 findings. No preamble.`,
    { phase: 'Work', model: 'sonnet', effort: 'medium', schema: FINDINGS }
  ),
  (r, b, i) => r?.findings?.length
    ? agent(
        `Try to refute each of these findings. Default to refuted=true if uncertain.\n` +
        JSON.stringify(r.findings),
        { phase: 'Verify', label: `verify:${i}`, model: 'sonnet', effort: 'medium', schema: VERDICTS }
      ).then(v => ({ findings: r.findings, verdicts: v?.verdicts ?? [] }))
    : null
)

const kept = results.filter(Boolean).flatMap(r =>
  r.findings.filter((_, i) => !r.verdicts[i]?.refuted))

phase('Synthesize')
return await agent(
  `Synthesize into a single ranked answer:\n${JSON.stringify(kept)}`,
  { phase: 'Synthesize', effort: 'high', schema: SUMMARY }   // the one top-tier call
)
```

## Escape hatches

- The user says **"no limit"**, "be exhaustive", or "spare no expense" → drop this
  skill's caps and run the full-scale version.
- Correctness genuinely depends on redundancy (money, contracts, anything client-facing,
  anything that ships) → keep lean models but restore multi-vote verification on the
  claims that matter, and say that you did.
- A workflow already ran and needs a tweak → **resume, do not re-run**:
  `Workflow({scriptPath, resumeFromRunId})` replays the unchanged prefix from cache for free.
