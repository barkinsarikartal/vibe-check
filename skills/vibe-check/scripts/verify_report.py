#!/usr/bin/env python3
"""Check a VIBE_CHECK.md report for completeness before handing it over.

Checks: every expected item number appears exactly once in the full table,
each status is valid, GAP rows carry a severity and point to an existing
"### G<n>." write-up, every row has evidence, and nothing in the report
looks like an unredacted secret. Prints the tally line to paste into the
report header. Exit code 0 = pass, 1 = problems found.

Usage: python3 verify_report.py VIBE_CHECK.md [--only 1-20,35,40-44]
"""

import argparse
import re
import sys

STATUS_RE = re.compile(r"^(OK|N/A|OWNER|SKIP|GAP\s*\((CRITICAL|HIGH|MEDIUM|LOW)\))$", re.I)
ROW_RE = re.compile(r"^\|\s*#?(\d{1,2})\s*\|(.*)$")
HEADER_RE = re.compile(r"^\|\s*#\s*\|\s*Item\s*\|\s*Status\s*\|", re.I)
SECRET_RES = [
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"\b[sr]k_(?:live|test)_[0-9A-Za-z]{16,}"),
    re.compile(r"\bwhsec_[0-9A-Za-z]{16,}"),
    re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_\-]{32,}"),
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY"),
    re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),
    re.compile(r"://[^\s:/@'\"`]+:(?!\*{3,}|<|\$\{|password@|pass@|PASSWORD)[^\s@'\"`]{6,}@"),
]
ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]


def parse_only(spec):
    wanted = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            wanted.update(range(int(a), int(b) + 1))
        else:
            wanted.add(int(part))
    bad = [n for n in wanted if not 1 <= n <= 84]
    if bad:
        sys.exit(f"--only contains numbers outside 1-84: {sorted(bad)}")
    return wanted


def split_cells(rest):
    cells = [c.strip() for c in rest.rstrip().rstrip("|").split("|")]
    return cells


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("report")
    ap.add_argument("--only", help="item subset the user asked for, e.g. 1-20,35")
    args = ap.parse_args()
    expected = parse_only(args.only) if args.only else set(range(1, 85))

    with open(args.report, encoding="utf-8") as fh:
        text = fh.read()
    lines = text.splitlines()
    problems, warnings = [], []

    gap_headings, open_order = {}, []
    for line in lines:
        m = re.match(r"^###\s+(~~)?G(\d+)\.\s*(.*)$", line)
        if m:
            sev = next((s for s in ORDER if re.search(rf"\b{s}\b", m.group(3))), None)
            gap_headings[int(m.group(2))] = sev
            if not m.group(1) and sev:
                open_order.append(sev)

    rows = {}
    in_table = False
    for lineno, line in enumerate(lines, 1):
        if HEADER_RE.match(line):
            in_table = True
            continue
        if not line.startswith("|"):
            in_table = False
            continue
        m = ROW_RE.match(line)
        if not in_table or not m:
            continue
        num = int(m.group(1))
        cells = split_cells(m.group(2))
        if len(cells) < 3:
            problems.append(f"line {lineno}: row #{num} needs 4 columns (# | Item | Status | Evidence)")
            continue
        item, status_raw, evidence = cells[0], cells[1], " | ".join(cells[2:])
        status = re.sub(r"[*`_]", "", status_raw).strip()
        if num in rows:
            problems.append(f"line {lineno}: item #{num} appears more than once (first on line {rows[num]['line']})")
            continue
        rows[num] = {"line": lineno, "item": item, "status": status, "evidence": evidence}

    if not rows:
        problems.append("no full table found: it needs a header row '| # | Item | Status | Evidence / note |'")
    missing = sorted(expected - rows.keys())
    extra = sorted(rows.keys() - expected)
    if missing:
        problems.append(f"missing items: {', '.join(map(str, missing))}")
    if extra:
        problems.append(f"items outside the requested scope: {', '.join(map(str, extra))}")

    tally = {"OK": 0, "GAP": 0, "OWNER": 0, "N/A": 0, "SKIP": 0}
    sev_count = {s: 0 for s in ORDER}
    referenced = set()
    for num in sorted(rows):
        r = rows[num]
        sm = STATUS_RE.match(r["status"])
        if not sm:
            problems.append(f"line {r['line']}: #{num} has invalid status '{r['status']}' "
                            "(use OK, GAP (CRITICAL|HIGH|MEDIUM|LOW), OWNER, N/A, SKIP)")
            continue
        kind = sm.group(1).upper()
        if kind.startswith("GAP"):
            tally["GAP"] += 1
            sev = sm.group(2).upper()
            sev_count[sev] += 1
            refs = [int(g) for g in re.findall(r"\bG(\d+)\b", r["evidence"])]
            if not refs:
                problems.append(f"line {r['line']}: #{num} is a GAP but its note doesn't point to a G# write-up")
            for g in refs:
                referenced.add(g)
                if g not in gap_headings:
                    problems.append(f"line {r['line']}: #{num} points to G{g}, but there is no '### G{g}.' heading")
        else:
            tally[kind.upper()] += 1
        referenced.update(int(g) for g in re.findall(r"\bG(\d+)\b", r["evidence"]))
        evidence = re.sub(r"[*`_]", "", r["evidence"]).strip()
        if len(evidence) < 12:
            problems.append(f"line {r['line']}: #{num} ({kind}) needs real evidence or a reason, got '{evidence}'")

    for g in sorted(set(gap_headings) - referenced):
        warnings.append(f"G{g} write-up exists but no table row points to it")

    if open_order != sorted(open_order, key=ORDER.index):
        warnings.append("gap write-ups are not ordered most severe first")
    for g, sev in gap_headings.items():
        if sev is None:
            warnings.append(f"G{g} heading has no severity word (CRITICAL/HIGH/MEDIUM/LOW)")

    for lineno, line in enumerate(lines, 1):
        for rx in SECRET_RES:
            m = rx.search(line)
            if m:
                problems.append(f"line {lineno}: looks like an unredacted secret ('{m.group(0)[:8]}…'); "
                                "show at most the first few characters")

    total = len(rows)
    sev_txt = ", ".join(f"{sev_count[s]} {s.lower()}" for s in ORDER if sev_count[s])
    plural = lambda n, word: f"{n} {word}{'' if n == 1 else 's'}"
    tally_line = (f"{total} items · {tally['OK']} OK · {plural(tally['GAP'], 'gap')}"
                  f"{f' ({sev_txt})' if sev_txt else ''} · {plural(tally['OWNER'], 'owner check')} · "
                  f"{tally['N/A']} N/A · {tally['SKIP']} skip")

    for w in warnings:
        print(f"warning: {w}")
    if problems:
        for p in problems:
            print(f"problem: {p}")
        print(f"\nFAIL: {len(problems)} problem(s). Fix them and run again.")
        sys.exit(1)
    print(f"PASS\nTally: {tally_line}")


if __name__ == "__main__":
    main()
