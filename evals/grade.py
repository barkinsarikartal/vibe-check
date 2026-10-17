#!/usr/bin/env python3
"""Grade one iteration of vibe-check eval runs against evals.json.

Layout expected: <iteration>/eval-<id>-<name>/<config>/run-1/outputs/
Writes grading.json next to each outputs/ folder.

Usage: python3 grade.py <iteration-dir> --fakes-dir <dir with <name>-<config>.fakes.json>
"""

import argparse
import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VERIFY = os.path.join(HERE, "..", "skills", "vibe-check", "scripts", "verify_report.py")


def read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def find_report(outputs):
    mds = [p for p in glob.glob(os.path.join(outputs, "*.md")) if os.path.basename(p) != "final_reply.md"]
    named = [p for p in mds if os.path.basename(p).upper() == "VIBE_CHECK.MD"]
    if named:
        return named[0]
    return max(mds, key=os.path.getsize) if mds else None


def chunks(text):
    out = []
    for para in re.split(r"\n\s*\n", text):
        lines = para.splitlines()
        if any(line.lstrip().startswith("|") for line in lines):
            out.extend(line for line in lines if line.strip())
        else:
            out.append(para)
    return out


def check(c, ctx):
    kind = c["kind"]
    if kind == "verify":
        if not ctx["report"]:
            return False, "No report file in outputs"
        cmd = [sys.executable, VERIFY, ctx["report"]] + (["--only", c["only"]] if c.get("only") else [])
        res = subprocess.run(cmd, capture_output=True, text=True)
        lines = [l for l in res.stdout.splitlines() if l.strip()]
        summary = "; ".join(lines[-4:])[:400]
        return res.returncode == 0, f"{os.path.basename(ctx['report'])}: {summary}"
    if kind == "no_secrets":
        leaked = [k for k, v in ctx["fakes"].items() if v in ctx["all_text"]]
        return not leaked, ("Leaked: " + ", ".join(leaked)) if leaked else "None of the generated fake keys appear in the outputs"
    if kind == "reply_short":
        if not ctx["reply"]:
            return False, "No final_reply.md"
        words = len(ctx["reply"].split())
        return words <= c["max_words"], f"final_reply.md has {words} words"
    if kind == "find":
        for group in c["any_of"]:
            for chunk in ctx["chunks"]:
                if all(re.search(rx, chunk, re.I) for rx in group):
                    snippet = " ".join(chunk.split())
                    return True, snippet[:260]
        return False, "No paragraph or table row matched"
    raise ValueError(kind)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("iteration")
    ap.add_argument("--fakes-dir", required=True)
    args = ap.parse_args()
    evals = {e["id"]: e for e in json.load(open(os.path.join(HERE, "evals.json")))["evals"]}

    for eval_dir in sorted(glob.glob(os.path.join(args.iteration, "eval-*"))):
        m = re.match(r"eval-(\d+)-(.+)$", os.path.basename(eval_dir))
        ev = evals[int(m.group(1))]
        for run_dir in sorted(glob.glob(os.path.join(eval_dir, "*", "run-*"))):
            config = os.path.basename(os.path.dirname(run_dir))
            outputs = os.path.join(run_dir, "outputs")
            report = find_report(outputs)
            reply_path = os.path.join(outputs, "final_reply.md")
            reply = read(reply_path) if os.path.exists(reply_path) else ""
            all_text = "\n".join(read(p) for p in glob.glob(os.path.join(outputs, "**", "*"), recursive=True)
                                 if os.path.isfile(p))
            fakes_path = os.path.join(args.fakes_dir, f"{m.group(2)}-{config}.fakes.json")
            ctx = {
                "report": report,
                "reply": reply,
                "all_text": all_text,
                "chunks": chunks((read(report) if report else "") + "\n\n" + reply),
                "fakes": json.load(open(fakes_path)) if os.path.exists(fakes_path) else {},
            }
            results = []
            for c in ev["checks"]:
                passed, evidence = check(c, ctx)
                results.append({"text": c["text"], "passed": passed, "evidence": evidence})
            n = sum(r["passed"] for r in results)
            grading = {
                "expectations": results,
                "summary": {"passed": n, "failed": len(results) - n, "total": len(results),
                            "pass_rate": round(n / len(results), 4)},
            }
            with open(os.path.join(run_dir, "grading.json"), "w") as fh:
                json.dump(grading, fh, indent=2)
            print(f"{os.path.basename(eval_dir)} / {config}: {n}/{len(results)}")


if __name__ == "__main__":
    main()
