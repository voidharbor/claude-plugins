---
description: Use for a dedicated performance session on an app you maintain — idle CPU, memory, GPU cost — when the result has to be measured before/after numbers, not plausible-sounding tweaks. Fits an overnight unattended run.
---

Cut what the app costs when nobody is looking at it, and prove it with numbers.

Argument: the path to the repo. With no argument, use the current directory if
it is a git repo; otherwise stop and ask.

---

## Rule zero — never touch a running copy

Check whether the app is running before anything else (`pgrep` for its process
name). **If it is, do not kill it and do not repackage** — rebuilding a bundle
underneath a live process corrupts the running instance. Do the source work,
run the checks, commit, and stop before packaging; say so in the report.

Also stop if the tree is dirty. Never stash, never force anything.

---

## Measure before you change anything

A perf change with no number attached is a guess. Capture a baseline and keep it:

1. Build and launch the real artifact — the packaged app, not the dev server.
2. Let it settle about 60 seconds, **idle and unfocused**. Idle is the state
   the app spends most of its life in and the one nobody profiles.
3. Record, for the main process and every helper: CPU %, RSS
   (`ps -Ao pid,ppid,rss,%cpu,comm` filtered to the app).
4. Repeat under a realistic working load — however many documents, tabs, or
   panes a heavy day actually holds.
5. Quit cleanly when done measuring.

Idle CPU is the headline number. An app doing nothing should be at essentially
zero; anything above ~1% sustained is a bug, not a cost of doing business.

## Leads are hypotheses, not findings

Reading the code will suggest suspects. **Confirm each one is real before
changing anything** — a fix for a problem that does not exist is worse than no
fix, because it is code nobody can justify later.

The usual suspects in an idle app:

- **Timers that run regardless of visibility.** Polling on a fixed cadence for
  a window nobody is looking at. If you drop the cadence when hidden, any
  rate math must use the real elapsed time between ticks, not the nominal
  interval.
- **State rebuilt wholesale on every tick.** A reducer or store that
  reallocates unchanged objects makes everything downstream re-render or
  recompute. Return the same object when nothing in it changed.
- **Expensive resources torn down and rebuilt on navigation.** Buffers,
  GPU/WebGL contexts, connections — destroyed on tab switch and recreated on
  the way back. The fix is rarely "keep everything alive"; contexts and
  buffers usually need to be kept *and bounded*, because platforms force-lose
  them past a limit.
- **Polling that shells out.** A subprocess sweep on a timer costs a process
  spawn every tick, forever.
- **Per-item costs that multiply.** Whatever one pane, tab, or document costs,
  the user has N of them. Measure one before deciding N is fine.

Treat that as a starting point, not the list.

## Prove it worked

Re-measure exactly as the baseline: same build steps, same settle time, same
load. Put the before/after numbers in the report and in the commit body — one
short line. **If a change cannot be shown to help, revert it.** "Should be
faster" is not a result.

---

## Gates before anything is pushed

Run the repo's own gate — typecheck, tests, build, whatever it defines — and,
**only if no copy of the app was running when you started**, a packaged smoke
test: launch the built artifact and confirm it does its first real thing (a
shell spawns, a window renders, a request serves). A green suite with a dead
artifact means the build is broken whatever the tests said.

Nothing red gets pushed. Never `--force`.

## Report

Leave a short note where the user will find it (`PERF-REPORT.md` next to the
repo, or the path they gave):

- baseline vs final numbers, plainly
- what was changed and what each change bought
- what was tried and reverted, and why — this is as useful as what shipped
- anything that needs the user

Do **not** replace the user's installed copy of the app. Leave that to them.
