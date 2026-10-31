#!/usr/bin/env python3
"""slop-gate: deterministic scan for AI-slop tells in anything about to be published.

Usage
-----
    python3 scan.py FILE [FILE...]      # scan files
    cat draft.md | python3 scan.py -    # scan stdin
    python3 scan.py --hook              # Claude Code PreToolUse/Stop hook mode (JSON on stdin)

Exit codes: 0 clean, 1 tells found (so it works in CI and in a pre-commit hook),
2 a file could not be read.

Two tiers
---------
HARD tells fail on a single hit. They have no legitimate use in finished prose.
FILLER words fail when SOFT_LIMIT or more occur, because one is a word choice and
five is decoration. The summary-recap check looks at the last paragraph only.

Fenced code blocks and text inside backticks or quotation marks are stripped before
scanning, so a piece that quotes a tell as an exhibit does not fail on its own
examples.
"""
import json
import os
import re
import sys

SOFT_LIMIT = 3

HARD = [
    ("em dash", r"—", 0),
    ("honesty framing",
     r"\b(honestly|to be honest|if I'm being honest|the honest (part|truth|answer|reason)|I'll be honest)\b", re.I),
    ("not-X-it's-Y contrast",
     r"\b(it'?s|this is|that'?s|the (question|point|problem|issue)) (is )?not (just |only |about )?[^.\n]{2,60}[.,;] ?(it'?s|but|it is) ", re.I),
    ("not-X-it's-Y contrast", r"\bnot just [^.\n]{2,40}, (it'?s|but) ", re.I),
    ("not-X-it's-Y contrast",
     r"\b(it|this|that) (is|was) not (about |just |only )?[^.,;\n]{2,50}, (it|this|that) (is|was) ", re.I),
    ("X-not-Y contrast", r"\b[a-z][a-z-]+, not (a |an |the |just |only )?[a-z][a-z -]{1,30}[.;:]", 0),
    ("rhetorical heading",
     r"^\s*(#{1,6}|<h[1-6][^>]*>)\s*(why (this|it) matters|the (key|real) (insight|point|opportunity|truth)|what this is not|the bottom line|the deeper point|the uncomfortable truth|here'?s the thing|the takeaway|so what|what comes next|what'?s next|where (it|this|we) go(es)? (from here|next))\b", re.I | re.M),
    ("The <Noun> heading", r"^\s*(#{1,6}|<h[1-6][^>]*>)\s*The [A-Z][a-z]+\s*(</h[1-6]>)?\s*$", re.M),
    ("verdict kicker",
     r"\bThat (is|was|'s) (the (point|lie|whole (point|thing)|part [a-z ]{3,30})|all [a-z ]{2,30} is for)\.", re.I),
    ("fake-profound closer",
     r"\b(let that sink in|this changes everything|what nobody (tells|talks about)|the part (everyone|most people) miss(es)?|and that'?s not nothing)\b", re.I),
    ("throat-clearing",
     r"\b(here'?s the thing|let me be clear|it'?s worth noting|it is worth noting|it'?s important to note|at the end of the day|in today'?s (fast-paced|ever-evolving|digital))\b", re.I),
    ("sycophancy",
     r"\b(great question|you'?re (absolutely )?right to push back|that'?s on me|you were right to)\b", re.I),
    ("emoji heading", r"^\s*#{1,6}\s*[\U0001F300-\U0001FAFF☀-➿]", re.M),
]

FILLER = re.compile(
    r"\b(delve|delves|delving|leverag(e|es|ing)|utiliz(e|es|ing)|seamless(ly)?|robust(ly)?"
    r"|tapestry|game[- ]changer|paradigm shift|cutting-edge|empower(s|ing)?|streamlin(e|es|ing)"
    r"|load-bearing|unlock the (potential|power)|genuinely|quietly|deep dive|dive in(to)?)\b", re.I)

# Checked against the last paragraph only: an opener elsewhere is ordinary prose.
ENDING = re.compile(r"^\s*(in conclusion|ultimately|overall|to sum up|in summary)\b", re.I)

# Fenced blocks first: tried after the inline-backtick alternative, a fence opener would
# match as an empty inline span and the block would be scanned.
QUOTED = re.compile(r"^[ \t]*(```|~~~).*?^[ \t]*\1[^\n]*|`[^`\n]*`|\"[^\"\n]{0,160}\"|“[^”\n]{0,160}”", re.M | re.S)

TEXT_EXT = {".md", ".mdx", ".html", ".htm", ".txt", ".svg", ".rst", ""}
# Matched against whole path segments, so `docs/no-ai-slop-notes.md` is scanned and
# `skills/no-ai-slop/SKILL.md` is not.
SKIP_SEGMENTS = {"no-ai-slop", "slop-gate", "voice-baseline", "memory", "hooks", "logs",
                 "node_modules", "site", "build", "dist"}


def strip_quoted(text):
    """Quoted, fenced and code-formatted spans are exhibits, not the author's voice."""
    return QUOTED.sub(" ", text)


def scan(text, soft_limit=SOFT_LIMIT):
    body = strip_quoted(text)
    hits = []
    for label, rx, flags in HARD:
        for m in re.finditer(rx, body, flags):
            frag = body[max(0, m.start() - 28):m.end() + 28].replace("\n", " ").strip()
            hits.append("[%s] ...%s..." % (label, frag))
            if len(hits) >= 12:
                return hits
    paragraphs = [p for p in re.split(r"\n\s*\n", body) if p.strip()]
    if paragraphs:
        m = ENDING.search(paragraphs[-1])
        if m:
            frag = paragraphs[-1][:m.end() + 28].replace("\n", " ").strip()
            hits.append("[summary-recap ending] ...%s..." % frag)
    soft = []
    for m in re.finditer(FILLER, body):
        frag = body[max(0, m.start() - 28):m.end() + 28].replace("\n", " ").strip()
        soft.append("[filler word %d; %d or more fail] ...%s..." % (len(soft) + 1, soft_limit, frag))
    if len(soft) >= soft_limit:
        hits.extend(soft[:6])
    return hits


def exempt(path, text):
    if "slop-ok:" in text:
        return True
    if not path:
        return False
    if SKIP_SEGMENTS.intersection(re.split(r"[\\/]+", path)):
        return True
    ext = os.path.splitext(path)[1].lower()
    return bool(ext) and ext not in TEXT_EXT


def hook():
    """Claude Code hook mode. Reads the hook payload on stdin, writes a decision on stdout."""
    try:
        d = json.loads(sys.stdin.read())
    except Exception:
        print("{}")
        return 0

    if d.get("hook_event_name") == "Stop":
        if d.get("stop_hook_active"):
            print("{}")
            return 0
        # The final reply is every assistant entry after the last user entry (tool
        # results are user entries too). Claude Code writes one line per content
        # block, so the last line alone is often a tool_use entry with no text.
        text, parts = "", []
        try:
            with open(d.get("transcript_path", ""), encoding="utf-8") as f:
                for line in f:
                    try:
                        o = json.loads(line)
                    except Exception:
                        continue
                    if o.get("type") == "user":
                        parts = []
                    elif o.get("type") == "assistant":
                        parts.append(o)
            for o in parts:
                for c in o.get("message", {}).get("content", []):
                    if isinstance(c, dict) and c.get("type") == "text":
                        text += c.get("text", "") + "\n"
        except Exception:
            pass
        hits = scan(text)
        if hits:
            print(json.dumps({"decision": "block",
                              "reason": "slop-gate (reply): rewrite without these tells, then stop.\n"
                                        + "\n".join(hits)}))
        else:
            print("{}")
        return 0

    tool = d.get("tool_name", "")
    ti = d.get("tool_input") or {}
    path = ti.get("file_path") or ti.get("path") or ""
    text = ""
    if tool == "Write":
        text = ti.get("content", "") or ""
    elif tool == "Edit":
        text = ti.get("new_string", "") or ""
        if path and os.path.isfile(path):
            try:
                if "slop-ok:" in open(path, encoding="utf-8").read():
                    print("{}")
                    return 0
            except Exception:
                pass
    else:
        # Any message-sending tool: Slack, Confluence, Jira, Linear, email.
        for key in ("message", "text", "body", "content"):
            if ti.get(key):
                text = ti[key] if isinstance(ti[key], str) else json.dumps(ti[key])
                break
        path = ""
        if not text:
            print("{}")
            return 0

    if exempt(path, text) or not text:
        print("{}")
        return 0

    hits = scan(text)
    if hits:
        reason = ("slop-gate: %s blocked. Rewrite without these tells. "
                  "For a deliberate exhibit add `slop-ok: <reason>` to the file.\n" % tool) + "\n".join(hits)
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                 "permissionDecision": "deny",
                                                 "permissionDecisionReason": reason}}))
    else:
        print("{}")
    return 0


def main():
    args = [a for a in sys.argv[1:] if a != "--"]
    if "--hook" in args:
        return hook()
    if not args or "--help" in args or "-h" in args:
        print(__doc__)
        return 0
    failed = 0
    for path in args:
        label = "stdin" if path == "-" else path
        try:
            text = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
        except (OSError, UnicodeDecodeError) as e:
            print("%s: could not read (%s)" % (label, e), file=sys.stderr)
            return 2
        if path != "-" and exempt(path, text):
            print("%s: exempt" % label)
            continue
        hits = scan(text)
        if hits:
            failed = 1
            print("%s: %d tell(s)" % (label, len(hits)))
            for h in hits:
                print("  " + h)
        else:
            print("%s: clear" % label)
    return failed


if __name__ == "__main__":
    sys.exit(main())
