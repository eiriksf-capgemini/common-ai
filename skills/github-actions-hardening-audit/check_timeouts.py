#!/usr/bin/env python3
"""Report GitHub Actions jobs that declare no job-level `timeout-minutes`.

zizmor has no audit for this, so it is the one check in the hardening
baseline that this skill has to do itself. Deliberately dependency-free
(no PyYAML): the skill runs against arbitrary client repos where installing
anything is friction, and workflow YAML is regular enough to scan by
indentation.

Usage:
    check_timeouts.py <repo-or-workflow-path> [...]
    check_timeouts.py --json <repo-or-workflow-path> [...]

Exit codes: 0 = every job has a timeout, 1 = at least one job does not,
2 = nothing scanned (no files, no parseable jobs, or all unreadable).
"""

import json
import os
import re
import sys

KEY = re.compile(r"^(\s*)([A-Za-z0-9_.-]+|\"[^\"]+\"|'[^']+'):\s*(.*)$")


def indent_of(line):
    return len(line) - len(line.lstrip(" "))


def strip_quotes(name):
    if len(name) > 1 and name[0] == name[-1] and name[0] in "\"'":
        return name[1:-1]
    return name


def scannable(lines):
    """Line numbers (1-based) and text, minus comments and blank lines.

    Block scalars (`run: |`) can contain anything, including text that looks
    like a YAML key, so their bodies are skipped wholesale.
    """
    out = []
    skip_deeper_than = None
    for i, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n")
        if skip_deeper_than is not None:
            if line.strip() and indent_of(line) > skip_deeper_than:
                continue
            skip_deeper_than = None
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = KEY.match(line)
        if m and m.group(3).strip().startswith(("|", ">")):
            skip_deeper_than = indent_of(line)
        out.append((i, line))
    return out


def find_jobs_block(entries):
    """Return entries under the top-level `jobs:` mapping."""
    jobs_indent = None
    block = []
    for lineno, line in entries:
        ind = indent_of(line)
        m = KEY.match(line)
        if jobs_indent is None:
            if m and ind == 0 and strip_quotes(m.group(2)) == "jobs":
                jobs_indent = ind
            continue
        if line.strip() and ind <= jobs_indent:
            break
        block.append((lineno, line))
    return block


def audit_file(path):
    """Yield one dict per job in `path`."""
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
    except (OSError, UnicodeDecodeError) as exc:
        return [{"file": path, "job": None, "status": "unreadable", "line": 0,
                 "detail": str(exc)}]

    block = find_jobs_block(scannable(lines))
    if not block:
        return []

    job_indent = min(indent_of(line) for _, line in block)
    jobs, current = [], None
    for lineno, line in block:
        ind = indent_of(line)
        m = KEY.match(line)
        if not m:
            continue
        key = strip_quotes(m.group(2))
        if ind == job_indent:
            current = {"file": path, "job": key, "line": lineno,
                       "timeout": False, "reusable": False, "child_indent": None}
            jobs.append(current)
            continue
        if current is None:
            continue
        if current["child_indent"] is None and ind > job_indent:
            current["child_indent"] = ind
        # Only direct children of the job count: `timeout-minutes` nested
        # under `steps:` is a step timeout, which is not what we check.
        if ind == current["child_indent"]:
            if key == "timeout-minutes":
                current["timeout"] = True
            elif key == "uses":
                current["reusable"] = True

    results = []
    for job in jobs:
        if job["timeout"]:
            status = "ok"
        elif job["reusable"]:
            # A job that calls a reusable workflow is a thin caller; the
            # timeout belongs in the called workflow's own jobs. Surfaced
            # separately rather than counted as a finding.
            status = "reusable-call"
        else:
            status = "missing"
        results.append({"file": job["file"], "job": job["job"],
                        "line": job["line"], "status": status})
    return results


def collect(targets):
    paths = []
    for target in targets:
        if os.path.isdir(target):
            wf = os.path.join(target, ".github", "workflows")
            root = wf if os.path.isdir(wf) else target
            for dirpath, _, filenames in os.walk(root):
                for name in sorted(filenames):
                    if name.endswith((".yml", ".yaml")):
                        paths.append(os.path.join(dirpath, name))
        elif os.path.isfile(target):
            paths.append(target)
        else:
            print(f"no such path: {target}", file=sys.stderr)
    return paths


def main(argv):
    as_json = "--json" in argv
    targets = [a for a in argv if not a.startswith("--")]
    if not targets:
        print(__doc__.strip(), file=sys.stderr)
        return 2

    paths = collect(targets)
    if not paths:
        print("no workflow files found", file=sys.stderr)
        return 2

    results = [r for path in paths for r in audit_file(path)]
    missing = [r for r in results if r["status"] == "missing"]
    scanned = [r for r in results if r["status"] != "unreadable"]

    if not scanned:
        for r in results:
            print(f"warning: {r['file']}: could not read ({r['detail']})",
                  file=sys.stderr)
        print("no jobs found in the scanned workflow files", file=sys.stderr)
        if as_json:
            json.dump(results, sys.stdout, indent=2)
            sys.stdout.write("\n")
        return 2

    if as_json:
        json.dump(results, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 1 if missing else 0

    for r in missing:
        print(f"{r['file']}:{r['line']}: job '{r['job']}' has no timeout-minutes")
    for r in results:
        if r["status"] == "reusable-call":
            print(f"{r['file']}:{r['line']}: job '{r['job']}' calls a reusable "
                  f"workflow; set the timeout in the called workflow")
        elif r["status"] == "unreadable":
            print(f"warning: {r['file']}: could not read ({r['detail']})",
                  file=sys.stderr)

    total = len(scanned)
    print(f"\n{len(missing)}/{total} jobs missing timeout-minutes "
          f"across {len(paths)} workflow file(s)")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
