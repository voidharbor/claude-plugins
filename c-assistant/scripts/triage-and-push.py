#!/usr/bin/env python3
"""Detached triage worker for one Lookout candidate session.

Spawned by needs-input-hook.py as `python3 triage-and-push.py <session_id>`,
fully detached (stdio to DEVNULL, LOOKOUT_TRIAGE=1 in env) once that hook's
prefilter decides a session is worth a closer look. This process reads the
session's registry entry and transcript tail, asks the Claude CLI's cheap
tier to judge whether the session is genuinely waiting on its user, and --
only when it says yes -- pushes a card via push-card.py.

`last_assistant_text` below is a local reimplementation of the same-named
function in needs-input-hook.py, not an import: the hyphenated script names
make cross-imports awkward, so the ~20 lines are deliberately duplicated
here rather than shared.

This script owns releasing the lock directory needs-input-hook.py claimed
before spawning it (STATE_DIR/lock) -- main() releases it in a finally, no
matter how triage turns out.

Silence is the failure mode: any parse failure, timeout, or missing
registry/transcript means this exits 0 having done nothing. Must never
print (stdio is already DEVNULL from the spawn, but the discipline holds
even if this is ever run some other way).
"""
import json, os, subprocess, sys

STATE_DIR = os.path.expanduser("~/.claude/lookout")
LOCK_DIR = os.path.join(STATE_DIR, "lock")
REGISTRY_DIR = os.path.expanduser("~/.claude/session-registry")
TAIL_BYTES = 65536


def last_assistant_text(transcript_path):
    """Text of the last assistant message in the transcript's tail, "" when
    there is none. Reads only the final TAIL_BYTES so this stays cheap even
    on multi-hundred-MB transcripts. Duplicated from needs-input-hook.py --
    see that file's docstring for why this isn't a shared import."""
    try:
        size = os.path.getsize(transcript_path)
        with open(transcript_path, "rb") as f:
            if size > TAIL_BYTES:
                f.seek(size - TAIL_BYTES)
                f.readline()  # drop the partial line the seek landed in
            data = f.read()
    except OSError:
        return ""
    for line in reversed(data.split(b"\n")):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if obj.get("type") != "assistant":
            continue
        try:
            content = obj["message"]["content"]
            return "".join(
                block.get("text", "") for block in content if block.get("type") == "text"
            )
        except Exception:
            return ""
    return ""


def parse_triage_output(stdout):
    """Slice the first "{" through the last "}" out of the model's stdout
    and json.loads it. Requires all three keys -- card (bool), question
    (str), draft (str or None) -- with the model's own STRICT JSON reply
    contract (see triage-prompt.md) always emitting all three. Anything
    else -- no braces, invalid JSON, wrong shape, wrong types -- is None,
    never a raised exception."""
    start = stdout.find("{")
    end = stdout.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        obj = json.loads(stdout[start:end + 1])
    except ValueError:
        return None
    if not isinstance(obj, dict):
        return None
    if not {"card", "question", "draft"} <= obj.keys():
        return None
    card, question, draft = obj["card"], obj["question"], obj["draft"]
    if not isinstance(card, bool):
        return None
    if not isinstance(question, str):
        return None
    if draft is not None and not isinstance(draft, str):
        return None
    return {"card": card, "question": question, "draft": draft}


def run_triage(prompt, env):
    """Run the triage prompt through the Claude CLI's cheap tier on stdin
    and return raw stdout for parse_triage_output to make sense of."""
    return subprocess.run(
        ["claude", "-p", "--model", "haiku"],  # CLI's own alias for its cheap tier, by design --
                                                # pinned model ids are the CLI's business, not this script's
        input=prompt, capture_output=True, text=True, timeout=90, env=env,
    ).stdout


def main(session_id):
    """registry -> tail -> prompt -> run -> parse -> push (only when card is
    true) -- finally: best-effort release of the lock needs-input-hook.py
    claimed on this triage's behalf."""
    try:
        with open(os.path.join(REGISTRY_DIR, session_id + ".json")) as f:
            reg = json.load(f)
        transcript_path = reg.get("transcript_path")
        if not transcript_path:
            return

        tail = last_assistant_text(transcript_path)
        prompt_path = os.path.join(os.path.dirname(__file__), "triage-prompt.md")
        with open(prompt_path) as f:
            prompt = f.read() + tail

        env = {**os.environ, "LOOKOUT_TRIAGE": "1"}
        stdout = run_triage(prompt, env)
        res = parse_triage_output(stdout)

        if res and res["card"]:
            push_path = os.path.join(os.path.dirname(__file__), "push-card.py")
            cmd = [sys.executable, push_path, session_id, "--question", res["question"]]
            if res["draft"] is not None:
                cmd += ["--draft", res["draft"]]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finally:
        try:
            os.rmdir(LOCK_DIR)
        except OSError:
            pass


if __name__ == "__main__":
    try:
        main(sys.argv[1])
    except Exception:
        pass
