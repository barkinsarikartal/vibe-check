<h1 align="center">vibe-check</h1>

<p align="center">
  An 84-point production-readiness audit for apps built with AI.<br />
  Every item gets a verdict, and every verdict comes with evidence.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT license" /></a>
  <a href="https://skills.sh"><img src="https://img.shields.io/badge/install-npx%20skills%20add-000000?logo=npm&logoColor=white" alt="Install with npx skills" /></a>
  <a href="https://code.claude.com/docs/en/skills"><img src="https://img.shields.io/badge/Claude%20Code-skill-D97757?logo=claude&logoColor=white" alt="Claude Code skill" /></a>
  <a href="skills/vibe-check/references/checklist.md"><img src="https://img.shields.io/badge/checklist-84%20items-2b303c" alt="84 checklist items" /></a>
</p>

<p align="center">
  <a href="https://github.com/barkinsarikartal/vibe-check/stargazers"><img src="https://img.shields.io/github/stars/barkinsarikartal/vibe-check?style=flat" alt="GitHub stars" /></a>
  <a href="https://github.com/barkinsarikartal/vibe-check/forks"><img src="https://img.shields.io/github/forks/barkinsarikartal/vibe-check?style=flat" alt="GitHub forks" /></a>
  <a href="https://github.com/barkinsarikartal/vibe-check/graphs/contributors"><img src="https://img.shields.io/github/contributors/barkinsarikartal/vibe-check?style=flat" alt="Contributors" /></a>
  <a href="https://github.com/barkinsarikartal/vibe-check/commits/main"><img src="https://img.shields.io/github/last-commit/barkinsarikartal/vibe-check?style=flat" alt="Last commit" /></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/-Python-3776AB?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/-Markdown-000000?logo=markdown&logoColor=white" alt="Markdown" />
</p>

<p align="center"><a href="#install">Jump to install ↓</a></p>

---

AI-built apps usually work on the happy path. What gets skipped is everything nobody asked for: the admin key that ends up in the browser bundle, the webhook nobody verifies, rate limits on some routes but not others, backups no one has ever restored, a privacy policy that doesn't match what the code collects.

vibe-check is an agent skill that takes your project through 84 checks for exactly those things and writes the result to `VIBE_CHECK.md`:

```text
recon -> 84 checks -> evidence for each -> VIBE_CHECK.md -> fixes, when you ask
```

It reads your code and doesn't change it. Item numbers never change, so you can rerun it before every release and compare results ("#29 is still open").

## What it checks

| Area | Items | For example |
|---|--:|---|
| Secrets and credentials | 9 | keys in the client bundle, `.env` in git history, weak JWT secrets |
| Auth and access control | 10 | missing ownership checks, IDOR, admin pages guarded only in the browser |
| Input and injection | 9 | SQL and NoSQL injection, XSS, SSRF, path traversal, file uploads |
| Database and storage | 7 | Supabase RLS, Firebase rules, public buckets, connection pooling |
| API surface | 7 | CORS, rate limits, unsigned webhooks, prices trusted from the client |
| Production exposure | 8 | debug pages, source maps, security headers, staging left public |
| Dependencies and review | 4 | known vulnerabilities, outdated packages, security scans in CI |
| AI features | 2 | prompt injection, AI tools that skip permission checks |
| Operations | 7 | logs, monitoring, backups and restore, rollback |
| Architecture and scale | 7 | load tests, in-memory sessions, queues, single points of failure |
| Hands-on testing | 2 | OWASP ZAP baseline, a Burp Suite test plan |
| Legal and business | 8 | privacy policy vs. what the code collects, terms, DMCA, trademark |
| Discoverability and support | 4 | SEO, Bing and Google consoles, store listing, support URL |

The full list, with where to look and what "good" means for each item, is in [`checklist.md`](skills/vibe-check/references/checklist.md).

## Install

```bash
npx skills add barkinsarikartal/vibe-check -g -a claude-code
```

`-g` installs it for all your projects; leave it out to add it to the current project only. Leave out `-a claude-code` to choose other agents (Codex, Cursor, OpenCode and more).

<details>
<summary><strong>Manual install</strong></summary>

```bash
git clone https://github.com/barkinsarikartal/vibe-check.git
cp -r vibe-check/skills/vibe-check ~/.claude/skills/
```

For a single project, copy it into that project's `.claude/skills/` instead.

</details>

Requires Python 3 for the two helper scripts (standard library only). Git is optional; without it, the history scan is skipped.

## Use

Open your project in your agent and ask in plain words:

| What you want | Say something like |
|---|---|
| A full audit before launch | "vibe check this project" |
| A yes/no on launching | "is this ready for production?" |
| Part of the list | "only items 1–30" or "just the security items" |
| Fixes for what it found | "fix G1 to G3" |
| A rerun after fixing | "vibe check again" (the report gains a "Changes since last check" section) |

The chat reply stays short: the verdict, the critical gaps and counts for the rest. Everything else is in `VIBE_CHECK.md`.

## What you get

Each item gets one of five verdicts:

| Verdict | Meaning |
|---|---|
| `OK` | Checked and handled, with the evidence (`file:line`, config, command output) |
| `GAP` | A real problem, rated `CRITICAL`, `HIGH`, `MEDIUM` or `LOW`, with a write-up and a fix |
| `OWNER` | Only you can check it (dashboards, accounts, legal); the exact steps are included |
| `N/A` | Doesn't apply to this app, and what was searched to confirm that |
| `SKIP` | Applies, but isn't worth doing yet, with the reason |

The report has four parts: gaps ranked by severity, owner checks, recommended skips, and the full 84-row table. Below is an excerpt from a test run on a deliberately broken demo app (Next.js, Supabase, Stripe, OpenAI):

```markdown
**Tally:** 84 items · 15 OK · 55 gaps (16 critical, 23 high, 11 medium, 5 low) · 5 owner checks · 7 N/A · 2 skip

### G4. Pro can be had for free: CRITICAL (items #15, #31, #32)
**What:** There are four separate holes:
- **The unlock is client-only.** `/pro` saves `isPro` in localStorage whenever the URL
  contains `?success` (`app/pro/page.tsx:12-13`). Visiting `/pro?success=1` unlocks Pro.
- **The client sets the price.** The server passes `priceAmount` to Stripe as
  `unit_amount` (`app/api/checkout/route.ts:5,15`).
- **The webhook is unsigned.** No `stripe.webhooks.constructEvent`; anyone can POST a
  fake `checkout.session.completed` (`app/api/stripe/webhook/route.ts:5`).
...

| #  | Item                     | Status | Evidence / note                                          |
|----|--------------------------|--------|----------------------------------------------------------|
| 17 | SQL injection            | OK     | All DB access goes through the supabase-js query builder; no raw SQL or `.rpc` |
| 21 | Insecure file uploads    | GAP (HIGH) | G8: only `accept="image/*"` on the client (`app/upload/page.tsx:29`) |
| 44 | No backup or restore plan | GAP (HIGH) | G13: no backup or restore notes in the repo |
| 83 | Trademarking the brand   | OWNER  | Name clearance can't be seen from the repo; search steps in section 2 |
```

> [!NOTE]
> Legal and business items (privacy policy, terms, DMCA, trademark, patent) come with concrete gaps and an honest opinion. They are not legal advice.

## Safety

- The audit is read-only: no code changes, no commits.
- Live checks are a few passive GET requests to your own deployed site (headers, `robots.txt`, `/.env`, source maps). Nothing active runs unless you ask: no scanners, fuzzing or login attempts.
- Secret values never appear in the report. `verify_report.py` fails the report if one slips in.

## Platform support

| Agent | Status |
|---|---|
| Claude Code | Tested (results below) |
| Codex, Cursor, OpenCode and other agents that read `SKILL.md` | Should work when installed with `npx skills add`; not tested yet |

## Test results

The skill was tested on two deliberately broken demo apps (Next.js + Supabase, FastAPI + React) with 38 planted problems, running the same prompts with and without it:

| | With vibe-check | Without |
|---|---|---|
| Checks passed (52 across 3 prompts) | 97% | 82% |
| Planted problems found | 38 / 38 | 38 / 38 |
| Verdict on every one of the 84 items | yes | no |
| Average time per run | about 10 min | about 6 min |

Without the skill, the agent still finds the obvious bugs. What it skips is the rest of the list: backups, monitoring, legal pages, trademark, load tests, rollback. That's the part vibe-check adds.

<details>
<summary><strong>Running the evals yourself</strong></summary>

The demo apps live in `evals/fixtures/`. Fake keys are generated when a fixture is built, so nothing secret-shaped is stored in this repo.

```bash
mkdir -p /tmp/vc/fakes

# 1. Build a test app
python3 evals/build_fixture.py splitly /tmp/vc/splitly-full-audit-with_skill \
  > /tmp/vc/fakes/splitly-full-audit-with_skill.fakes.json

# 2. Run your agent on /tmp/vc/splitly-full-audit-with_skill with the prompt from
#    evals/evals.json. Save its VIBE_CHECK.md and final_reply.md to:
#    workspace/iteration-1/eval-1-splitly-full-audit/with_skill/run-1/outputs/

# 3. Score it
python3 evals/grade.py workspace/iteration-1 --fakes-dir /tmp/vc/fakes
```

`workspace/` is in `.gitignore`.

</details>

## Repo layout

```text
skills/vibe-check/
├── SKILL.md                  workflow, verdict rules, report template
├── references/checklist.md   the 84 items: where to look, what "good" means, usual severity
└── scripts/
    ├── recon.py              stack fingerprint + redacted secret scan of files and git history
    └── verify_report.py      checks the report covers every item with evidence; prints the tally
evals/
├── fixtures/                 two broken demo apps used for testing
├── build_fixture.py          turns a fixture into a git repo with generated fake keys
├── evals.json                test prompts and pass/fail checks
└── grade.py                  scores a test run
```

## Update and uninstall

```bash
npx skills update vibe-check
npx skills remove vibe-check
```

If you installed manually, delete `~/.claude/skills/vibe-check` (or the copy in your project's `.claude/skills/`).

<details>
<summary><strong>Contributing</strong></summary>

Issues and pull requests are welcome, especially new checks and better detection for stacks the checklist covers thinly.

- Item numbers are permanent. Add new items at the end (85, 86, …) and never renumber, because reports refer to items by number.
- Run the evals before and after you change `SKILL.md` or `checklist.md`, and include the before/after numbers in the PR.
- Keep the scripts standard-library Python so the skill installs with no setup.

</details>

## License

[MIT](LICENSE)
