#!/usr/bin/env python3
"""Detect which cost-data requirements (R1-R11) a repository already satisfies.

Read-only. Dependency-free (stdlib only). Prints a match count for every check
so a zero is a measured zero, never a silent one.

Usage:
  detect.py <repo-root>            human-readable
  detect.py --json <repo-root>     machine-readable
  detect.py --items items.json <repo-root>
        use a generic JSON array of work items (each with a "metadata" object)
        instead of auto-detecting a beads database

Exit 0 on a completed scan, 2 on a usage error, a missing git, or a target that is
not a git repository.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

CODE_EXT = {".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs", ".java", ".kt",
            ".cs", ".rb", ".php", ".swift", ".c", ".cc", ".cpp", ".h", ".sql",
            ".prisma", ".sh", ".yml", ".yaml", ".json", ".md", ".css", ".scss"}

TOKEN_FIELDS = ["tokens_impl", "tokens_qa", "tokens_impl_passes"]
ROUND_FIELD_RE = re.compile(r"^tokens_qa_r\d+$")
FINDINGS_FIELD_RE = re.compile(r"^findings_r\d+$")
FRESH_FIELDS = ["resumed", "fresh_agent", "agent_mode"]
COVARIATE_FIELDS = ["model", "model_effort", "cc_type", "cc_scope"]
HUMAN_FIELDS = ["handback", "handbacks", "manual_merge", "human_minutes", "human_roundtrips"]
CONTROL_MARKERS = ["retro_source", "control", "audit", "gate"]
ID_RE = re.compile(r"(?:[A-Z][A-Z0-9]+-\d+|#\d+|[a-z][a-z0-9]*-\d+)")
LONG_LIVED_BRANCHES = {"main", "master", "develop", "dev", "trunk", "staging", "production"}
POLICY_TERMS = ["severity", "round", "lenient", "approx", "exact", "blocks", "cap"]
TELEMETRY_KEYS = ["CLAUDE_CODE_ENABLE_TELEMETRY", "OTEL_EXPORTER", "OTEL_METRICS_EXPORTER", "OTEL_LOGS_EXPORTER"]


def run(cmd, cwd, timeout=60):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, "", str(e)


def load_items(root, items_path):
    """Return (items, source_label). Items are dicts with a 'metadata' dict."""
    if items_path:
        data = json.loads(Path(items_path).read_text())
        return normalise(data), f"--items {items_path}"
    if (root / ".beads").exists() and shutil.which("bd"):
        rc, out, err = run(["bd", "list", "--all", "--json"], cwd=root, timeout=120)
        if rc == 0 and out.strip():
            try:
                return normalise(json.loads(out)), "bd list --all --json"
            except json.JSONDecodeError:
                return [], "bd output was not JSON"
        return [], f"bd list failed (rc={rc}): {err.strip()[:120]}"
    if (root / ".beads").exists():
        return [], ".beads/ present but `bd` not on PATH"
    return [], "no tracker detected (no .beads/; pass --items for another tracker)"


def normalise(data):
    """Accept a list of items, or an object wrapping one list (`{"issues": [...]}`)."""
    if isinstance(data, dict):
        lists = [v for v in data.values() if isinstance(v, list)]
        data = lists[0] if len(lists) == 1 else []
    items = []
    for b in data if isinstance(data, list) else []:
        if not isinstance(b, dict):
            continue
        m = b.get("metadata") or {}
        if isinstance(m, str):
            try:
                m = json.loads(m)
            except json.JSONDecodeError:
                m = {}
        if not isinstance(m, dict):
            m = {}
        b = dict(b)
        b["metadata"] = m
        items.append(b)
    return items


def field_counts(items):
    c = Counter()
    for b in items:
        c.update(b["metadata"].keys())
    return c


def status(present, partial=False, unknown=False):
    if unknown:
        return "unknown"
    if present:
        return "present"
    if partial:
        return "partial"
    return "missing"


def grep_files(paths, terms):
    """Return {term: count} across the given files, plus files-scanned count."""
    counts = Counter()
    scanned = 0
    for p in paths:
        try:
            text = p.read_text(errors="replace").lower()
        except OSError:
            continue
        scanned += 1
        for t in terms:
            counts[t] += len(re.findall(r"\b" + re.escape(t.lower()) + r"\b", text))
    return counts, scanned


def doc_paths(root):
    out = []
    for pat in ["CLAUDE.md", "AGENTS.md", ".claude/skills/*/SKILL.md", ".claude/agents/*.md", "docs/**/*.md"]:
        out.extend(root.glob(pat))
    return [p for p in out if p.is_file()]


def settings_paths(root):
    cands = [root / ".claude/settings.json", root / ".claude/settings.local.json",
             Path.home() / ".claude/settings.json"]
    return [p for p in cands if p.is_file()]


def main():
    args = sys.argv[1:]
    as_json = "--json" in args
    items_path = None
    if "--items" in args:
        i = args.index("--items")
        if i + 1 >= len(args) or args[i + 1].startswith("--"):
            print("usage: detect.py [--json] [--items items.json] <repo-root>", file=sys.stderr)
            sys.exit(2)
        items_path = args[i + 1]
        del args[i:i + 2]
    args = [a for a in args if a != "--json"]
    root = Path(args[0] if args else ".").resolve()

    if not shutil.which("git"):
        print("git not found on PATH", file=sys.stderr)
        sys.exit(2)
    rc, _, _ = run(["git", "rev-parse", "--is-inside-work-tree"], cwd=root)
    if rc != 0:
        print(f"not a git repository: {root}", file=sys.stderr)
        sys.exit(2)

    items, tracker_src = load_items(root, items_path)
    n_items = len(items)
    fc = field_counts(items)
    rows = []

    def row(rid, name, st, evidence):
        rows.append({"id": rid, "requirement": name, "status": st, "evidence": evidence})

    # R1 join key: branch names carry a work-item id
    branches = []
    if shutil.which("gh"):
        rc, out, _ = run(["gh", "pr", "list", "--state", "merged", "--limit", "100", "--json", "headRefName"], cwd=root, timeout=60)
        if rc == 0 and out.strip():
            try:
                branches = [x["headRefName"] for x in json.loads(out)]
                bsrc = "gh pr list --state merged (last 100)"
            except (json.JSONDecodeError, KeyError):
                branches = []
    if not branches:
        # A bare remote name is how a modern git prints origin/HEAD with this format.
        rc, out, _ = run(["git", "for-each-ref", "refs/remotes", "--format=%(refname:short)"], cwd=root)
        branches = [b.split("/", 1)[1] for b in out.split() if "/" in b and not b.endswith("/HEAD")]
        bsrc = "git for-each-ref refs/remotes"
    branches = [b for b in branches if b not in LONG_LIVED_BRANCHES]
    ids = {str(b.get("id")) for b in items if b.get("id")}
    if ids:
        id_rx = re.compile(r"(?<![A-Za-z0-9])(?:%s)(?![A-Za-z0-9])" % "|".join(re.escape(i) for i in sorted(ids, key=len, reverse=True)))
        with_id = [b for b in branches if id_rx.search(b)]
        how = "contain a real item id"
    else:
        with_id = [b for b in branches if ID_RE.search(b)]
        how = "carry an id-shaped token (no tracker to check against)"
    share = (len(with_id) / len(branches)) if branches else 0
    row("R1", "join key: branch or PR carries work-item id",
        status(share >= 0.9, partial=0 < share < 0.9, unknown=not branches),
        f"{len(with_id)}/{len(branches)} branches {how} ({bsrc}); tracker: {tracker_src}, {n_items} items")

    # R2 harness-measured tokens: telemetry export or usage script
    sp = settings_paths(root)
    tel_hits = Counter()
    for p in sp:
        try:
            t = p.read_text()
        except OSError:
            continue
        for k in TELEMETRY_KEYS:
            # A key with a non-empty value, not a mention or an explicit "0".
            tel_hits[k] += len(re.findall(r'"%s[A-Z_]*"\s*:\s*"(?!0?"|false")[^"]+"' % k, t))
    env_hits = [k for k in TELEMETRY_KEYS if os.environ.get(k, "").strip().lower() not in ("", "0", "false")]
    usage_scripts = [str(p.relative_to(root)) for p in root.glob("scripts/*") if re.search(r"usage|cost|token", p.name, re.I)]
    tel_total = sum(tel_hits.values()) + len(env_hits)
    self_reported = fc.get("tokens_impl", 0)
    row("R2", "harness-measured tokens by component and model",
        status(tel_total > 0, partial=(tel_total == 0 and (usage_scripts or self_reported))),
        f"telemetry keys in {len(sp)} settings files: {dict(tel_hits) or 0}; in env: {env_hits or 0}; usage scripts: {usage_scripts or 0}; "
        f"self-reported tokens_impl on {self_reported}/{n_items} items")

    # R3 phase, pass, round labels; fresh vs resumed
    round_fields = sorted(k for k in fc if ROUND_FIELD_RE.match(k))
    passes = fc.get("tokens_impl_passes", 0)
    r1 = fc.get("tokens_qa_r1", 0)
    fresh = {k: fc[k] for k in FRESH_FIELDS if k in fc}
    row("R3", "phase, pass and round labels; fresh vs resumed",
        status(bool(round_fields) and passes and fresh, partial=bool(round_fields or passes), unknown=n_items == 0),
        f"round fields {round_fields or 0}; tokens_qa_r1 on {r1}, tokens_impl_passes on {passes} of {n_items}; fresh/resumed fields: {fresh or 0}")

    # R4 review policy as data
    docs = doc_paths(root)
    pol, scanned = grep_files(docs, POLICY_TERMS)
    policy_files = []
    for p in docs:
        if not re.search(r"review|process", p.name, re.I):
            continue
        try:
            t = p.read_text(errors="replace").lower()
        except OSError:
            continue
        if len(re.findall(r"\bseverity\b", t)) >= 3 and len(re.findall(r"\bround", t)) >= 3:
            policy_files.append(str(p.relative_to(root)))
    row("R4", "review policy recorded (cap, severity, lenient band, identity, effective dates)",
        status(bool(policy_files), partial=pol["severity"] > 0 and pol["round"] > 0, unknown=scanned == 0),
        f"{scanned} docs scanned; term hits {dict(pol)}; policy-named files: {len(policy_files)} ({', '.join(policy_files[:4])}{'...' if len(policy_files) > 4 else ''}). Effective dates: not detectable mechanically")

    # R5 findings per round
    ffields = sorted(k for k in fc if FINDINGS_FIELD_RE.match(k))
    fgrep, _ = grep_files(docs, ["findings_r"])
    sev = fc.get("severity", 0)
    row("R5", "findings per round by severity and family",
        status(bool(ffields), partial=sev > 0 or fgrep["findings_r"] > 0, unknown=n_items == 0),
        f"findings_rN fields on items: {ffields or 0}; mentions in docs: {fgrep['findings_r']}; a per-item 'severity' field on {sev} items (per item, not per round)")

    # R6 covariates
    cov = {k: fc.get(k, 0) for k in COVARIATE_FIELDS}
    crit = sum(1 for b in items if (b.get("acceptance_criteria") or "").strip())
    prs = fc.get("prs", 0)
    row("R6", "size and difficulty covariates (tier, effort, type, scope, criteria, PR link)",
        status(all(v >= 0.8 * n_items for v in cov.values()) and n_items > 0, partial=any(cov.values()), unknown=n_items == 0),
        f"{cov}; acceptance criteria on {crit}; PR link on {prs} of {n_items}. Diff size comes from the PR, not the item")

    # R7 outcome
    rc, out, _ = run(["git", "log", "--oneline", "--grep=^Revert", "--grep=^revert"], cwd=root)
    reverts = len([l for l in out.splitlines() if l.strip()])
    fixes = sum(1 for b in items if (b["metadata"].get("cc_type") or b.get("issue_type") or "") in ("fix", "bug"))
    linked = 0
    for b in items:
        deps = b.get("dependencies") or []
        if any((d.get("type") or d.get("dependency_type") or "") == "discovered-from" for d in deps if isinstance(d, dict)):
            linked += 1
    row("R7", "outcome: fixes traced to origin, reverts, escaped defects",
        status(False, partial=linked > 0 or fixes > 0),
        f"fix-typed items {fixes}; items with a discovered-from link {linked}; revert commits {reverts}. No field marks an escaped defect")

    # R8 human cost
    hf = {k: fc[k] for k in HUMAN_FIELDS if k in fc}
    hgrep, _ = grep_files(docs, ["handback", "manual merge", "round-trip"])
    row("R8", "human cost: handbacks, manual merges, wall-clock",
        status(bool(hf), partial=sum(hgrep.values()) > 0),
        f"fields {hf or 0}; doc mentions {dict(hgrep)}; started_at/closed_at present on {sum(1 for b in items if b.get('started_at') and b.get('closed_at'))} items (wall-clock is derivable)")

    # R9 controls tagged
    marker_rx = re.compile(r"\b(%s)\b" % "|".join(CONTROL_MARKERS), re.I)
    ctrl = 0
    for b in items:
        labels = b.get("labels") or []
        haystack = " ".join([str(b["metadata"].get("cc_type") or "")] + [str(l) for l in (labels if isinstance(labels, list) else [labels])])
        if marker_rx.search(haystack) or "retro_source" in b["metadata"]:
            ctrl += 1
    row("R9", "controls (audits, gates, retros) tracked as items with cost",
        status(False, partial=ctrl > 0, unknown=n_items == 0),
        f"{ctrl} items carry a control marker ({CONTROL_MARKERS}); none has a dedicated control flag")

    # R10 project context: LOC and prefix size
    rc, out, _ = run(["git", "ls-files"], cwd=root)
    files = [root / f for f in out.splitlines() if Path(f).suffix in CODE_EXT]
    loc = 0
    for f in files[:20000]:
        try:
            with open(f, "rb") as fh:
                loc += sum(1 for _ in fh)
        except OSError:
            pass
    prefix_bytes = 0
    for name in ["CLAUDE.md", "AGENTS.md"]:
        p = root / name
        if p.is_file():
            prefix_bytes += p.stat().st_size
    for p in list(root.glob(".claude/skills/*/SKILL.md")) + list(root.glob(".claude/agents/*.md")):
        try:
            head = p.read_text(errors="replace").split("---")
            prefix_bytes += len(head[1]) if len(head) > 2 else 0
        except OSError:
            pass
    row("R10", "project context: stack, LOC, prefix size, harness, schema version",
        status(False, partial=True),
        f"{len(files)} tracked text files, {loc} lines; always-loaded prefix ~{prefix_bytes} bytes (~{prefix_bytes // 4} tokens: CLAUDE.md + AGENTS.md + skill/agent frontmatter). Harness version and schema_version: {fc.get('schema_version', 0)} items carry schema_version")

    # R11 definitions
    defs = [str(p.relative_to(root)) for p in root.glob("docs/**/*") if re.search(r"definition|glossary|schema|metric", p.name, re.I)]
    row("R11", "written, versioned definitions of round, pass, finding, severity",
        status(False, partial=bool(defs)),
        f"candidate files: {defs or 0}; schema_version field on {fc.get('schema_version', 0)} items")

    report = {"repo": str(root), "items": n_items, "tracker": tracker_src, "rows": rows,
              "metadata_fields": dict(fc.most_common())}
    if as_json:
        print(json.dumps(report, indent=2))
        return
    print(f"cost-data-audit: {root}")
    print(f"tracker: {tracker_src}; items: {n_items}\n")
    w = max(len(r["requirement"]) for r in rows)
    for r in rows:
        print(f"{r['id']:<4} {r['status']:<8} {r['requirement']}")
        print(f"     {r['evidence']}")
    c = Counter(r["status"] for r in rows)
    print(f"\npresent {c['present']}  partial {c['partial']}  missing {c['missing']}  unknown {c['unknown']}  (of {len(rows)})")


if __name__ == "__main__":
    main()
