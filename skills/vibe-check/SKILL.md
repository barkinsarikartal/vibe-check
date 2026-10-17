---
name: vibe-check
description: Run a full 84-point production-readiness audit on a vibe-coded (AI-built) app and write a VIBE_CHECK.md report where every item gets a verdict backed by evidence (OK, GAP with severity, OWNER, N/A, SKIP). Covers secrets, auth and authorization, IDOR, injection, XSS, CSRF, CORS, rate limits, database and bucket permissions, Supabase RLS and Firebase rules, debug pages, source maps, security headers, dependencies, AI and prompt-injection risks, logging, monitoring, backups and restore, deploys, scaling, privacy policy, legal, trademark, SEO and store listing. Use this whenever the user asks to audit, harden, security-check or "vibe check" a project, asks if an app is ready for production, launch or the App Store, mentions their 84-item checklist or one of its item numbers, or wants a pre-launch review of code written with AI, even if they only say "check everything before I ship".
---

# Vibe Check

An 84-point audit of the things AI-built apps routinely get wrong. The items are in `references/checklist.md`; read the relevant category there before you investigate it.

AI-written apps tend to work on the happy path and fail where nobody prompted: a secret in the bundle, a missing ownership check, rate limits on some routes but not others, debug on in production, backups nobody has restored, a privacy policy that doesn't match the code. A generic security review catches some of this and quietly skips the rest. What this skill adds is **completeness with honesty**: every one of the 84 items gets a verdict with evidence, and the numbers never change, so reports can be compared across runs and projects ("#29 is still open").

`<skill-dir>` below means the folder this SKILL.md is in.

## Verdicts

| Status | Meaning | Must include |
|---|---|---|
| `OK` | Checked and handled | The evidence you actually saw: `file:line`, config value, command output |
| `GAP (CRITICAL)` / `GAP (HIGH)` / `GAP (MEDIUM)` / `GAP (LOW)` | A real problem | A pointer to its write-up (`G3`) |
| `OWNER` | Can't be verified from the repo or terminal: dashboards, account settings, legal or business decisions | The exact steps the owner should take to check it |
| `N/A` | Doesn't apply to this app | Why, and what you searched to confirm it ("no upload handlers: grepped multer, FormData, UploadFile, presigned") |
| `SKIP` | Applies, but you recommend not doing it | The reason |

Severity:
- **CRITICAL**: exploitable now by an outsider with no special access, a live secret exposed, or money or data loss possible. Fix today.
- **HIGH**: a real vulnerability or launch blocker that needs some precondition. Fix before launch.
- **MEDIUM**: weakens defenses or will hurt at scale. Fix before growth.
- **LOW**: hygiene or nice-to-have.

Each checklist entry has a usual severity. Adjust it to the real exposure: a missing rate limit on an endpoint that calls a paid API is worse than one on a static lookup.

## Workflow

### 1. Scope

- Find the project root and its parts (frontend, backend, mobile, infra) in a monorepo.
- If a previous `VIBE_CHECK.md` exists, read it. This run adds a "Changes since last check" section.
- Read the project's own docs that record decisions (README, SECURITY.md, docs/, project plans). They tell you what is intentional, so you don't re-argue settled choices. Still verify their claims in code, because docs drift.
- If the user asked for a subset ("just the security items", "items 1–30"), audit only those and keep the original numbers.
- Find the deployed URL from README or config. If there is one, use it for passive checks in step 4. If there isn't, run code-only and turn live-only checks into `OWNER` rows; don't stall the audit to ask.

### 2. Recon

Run:

```bash
python3 <skill-dir>/scripts/recon.py <project-root>
```

It prints the stack fingerprint, env-file status, secret-looking strings in current files and git history (redacted), infrastructure files, source-map settings and installed audit tools. Its hits are leads, not findings: open each one before reporting it.

Then read the README, manifests, entry points, route definitions, middleware, auth setup, database schema and migrations, deploy config and CI workflows. Write a **stack profile** (it goes in the report header): frontend, backend, data stores, auth model, payments, AI features, uploads and user content, hosting and deploys, mobile, CI. The profile tells you which items are likely N/A, but each N/A still needs its own evidence.

### 3. Investigate

Work category by category (the table at the top of `references/checklist.md`), not 1 to 84. Items in a category share evidence: the route list you build for #5 also answers #9, #28 and #33.

Evidence rules. These are what make the report trustworthy:

- **Trace before you accuse.** A raw SQL call is only injection if user input reaches it. A key-like string may be a publishable key. Follow the data before you call something CRITICAL.
- **Search before you clear.** For OK and N/A, say what you looked at. "No auth issues" isn't evidence; "every handler in `src/routes/*` goes through `requireUser` (`src/server.ts:41`); no route registered outside it" is.
- **Run the tools that exist.** `npm audit`, `pip-audit`, `gitleaks`, `semgrep` and similar, when installed (recon lists them). Don't install tools globally without asking.
- **History counts.** A secret deleted in a later commit is still leaked. Mark it, and say it must be rotated.
- **Never write a secret value** into the report or the chat. Show the first few characters at most (recon already redacts).
- **Stay read-only.** Don't change code, commit or migrate during the audit. Fixing comes after, when asked.
- **Live checks are passive only:** a handful of GET requests to the user's own deployed site (`curl -sI` for headers, `robots.txt`, `/.env`, `/.git/config`, a `.map` file, compression). No fuzzing, no active scanners, no login attempts unless the user explicitly asks, and never against hosts the user doesn't own.
- **Be proportional.** Business and legal items (#59, #61–#63, #69, #70, #74, #83, #84) need an honest opinion sized to the project, not boilerplate. Legal items get a "not legal advice" line and concrete gaps.

For a large codebase you may split categories across subagents if you have them, but you own the final table: re-check anything that comes back without evidence.

### 4. Write the report

Write `VIBE_CHECK.md` at the project root (or wherever the user asks), using the template below. Group items that share one root cause into a single gap (#6, #33 and #34 are often one missing ownership check); each table row then points to the same `G#`.

### 5. Verify the report

```bash
python3 <skill-dir>/scripts/verify_report.py VIBE_CHECK.md          # add --only 1-30 for a subset
```

It checks that every expected item appears exactly once with a valid status and real evidence, that every GAP points to an existing write-up, and that no secret slipped in. It prints the tally line: paste that into the header. Fix and re-run until it says PASS. A long table is exactly where items go missing, so don't skip this.

### 6. Reply in chat

Keep it under about 250 words. The person has the report for detail, and a long chat reply buries the few things they must act on today:
- one sentence verdict (ready or not, and why)
- the tally line
- each CRITICAL gap in one short line (top five if there are more)
- HIGH and the rest as counts with their G numbers ("8 high: G6–G13")
- how many owner checks are waiting, and any key rotation they must do themselves
- the report path
- an offer to fix: "Want me to start on G1–G3?"

Don't paste the full table or the gap write-ups into chat.

## Report template

```markdown
# Vibe Check: <project name>

**Date:** YYYY-MM-DD · **Commit:** <short sha> · **Scope:** all 84 items (or: items 1–30)
**Stack:** <one line>
**Live checks:** <URL checked passively> (or: none, code-only)
**Tally:** <paste from verify_report.py>

## Stack profile
- **Frontend:** …
- **Backend:** …
- **Data:** …
- **Auth:** …
- **Payments / AI / Uploads & user content:** …
- **Hosting & deploys / Mobile / CI:** …

## Changes since last check
<!-- Only on re-runs. -->
- #28 GAP (HIGH) → OK: rate limiting added (`src/middleware/limit.ts:12`)

## 1. Gaps, most severe first

### G1. <Short title>: CRITICAL (items #3, #14)
**What:** what's wrong, with `file:line` evidence.
**Why it matters:** the concrete bad outcome: who can do what.
**Fix:** concrete steps, and what the owner must do outside the code (for example, rotate the key). Effort: minutes / hours / days.

## 2. Owner checks: things the code can't show
- [ ] **#13 Repo visibility:** open https://github.com/<owner>/<repo> in a private window; expect a 404.

## 3. Recommended skips
- **#84 Provisional patent:** <reason>.

## 4. All 84 items

| # | Item | Status | Evidence / note |
|---|---|---|---|
| 1 | Exposed database credentials | OK | `DATABASE_URL` read from env only (`src/db.ts:3`); no URLs with passwords in tree or history (recon) |
| 2 | Public .env files | GAP (CRITICAL) | G1: `.env` committed in a1b2c3d, still in history |
```

Use the item names from `references/checklist.md` (short forms are fine). Keep the table header exactly as shown; the verifier looks for it.

## Fixing (only when asked)

When the user picks gaps to fix:
- Work in severity order, one gap at a time. Match the project's code style, and add tests where a test suite exists.
- Re-verify each fix the same way you found the problem, then update the row to `OK` with the new evidence, and mark the write-up heading `~~G1. …~~ fixed YYYY-MM-DD`.
- Leaked secrets need rotating by the owner. Changing the code doesn't un-leak them, so say so plainly.
- Don't commit unless the user asks.
- Re-run `verify_report.py` after updating the report.
