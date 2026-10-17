# vibe-check

An agent skill that runs an 84-point production-readiness audit on a vibe-coded (AI-built) app.

Every item gets a verdict backed by evidence (`OK`, `GAP` with severity, `OWNER`, `N/A`, `SKIP`), and the result is written to `VIBE_CHECK.md` in your project: gaps ranked by severity with fixes, a list of things only you can check (dashboards, accounts, legal), and the full 84-row table. Item numbers never change, so you can compare runs over time.

The checklist covers secrets, auth, IDOR, injection, XSS, CSRF, CORS, rate limits, database and bucket permissions, debug pages, source maps, security headers, dependencies, AI features, logging, monitoring, backups, deploys, scaling, privacy policy, legal, trademark, SEO and store listings. See [the full list](skills/vibe-check/references/checklist.md).

## Install

Claude Code, personal (all projects):

```bash
cp -r skills/vibe-check ~/.claude/skills/
```

Or for one project only: copy `skills/vibe-check` into that project's `.claude/skills/`.

Once this repo is on GitHub, others can install it with `npx skills add <your-github-user>/vibe-check`.

## Use

In your project, ask something like:

- "vibe check this project"
- "is this app ready for production?"
- "run my 84-item checklist"
- "just the security items, 1–30"

The agent reads the code (it doesn't change it), writes `VIBE_CHECK.md`, and replies with a short summary. Ask it to fix specific gaps afterwards.

## What's inside

```
skills/vibe-check/
├── SKILL.md                  workflow, verdict rules, report template
├── references/checklist.md   the 84 items: where to look, what "good" means, usual severity
└── scripts/
    ├── recon.py              stack fingerprint + redacted secret scan of files and git history
    └── verify_report.py      checks the report covers every item with evidence; prints the tally
```

Both scripts need only Python 3 (standard library).

## Safety

The audit is read-only. Live checks against your deployed site are passive (a few GET requests). It won't run active scanners or attack anything unless you explicitly ask, and it never writes secret values into the report.
