#!/usr/bin/env python3
"""First-pass recon for a vibe-check audit.

Prints a stack fingerprint and the quick signals that feed several checklist
items: env files (#2), secret-looking strings in the tree and in git history
(#1, #3, #13, #26, #30), infrastructure files, source-map settings (#36) and
which audit tools are installed. Secret values are always redacted.

Read-only. Standard library only.

Usage: python3 recon.py [project-root] [--history-seconds N]
"""

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import time

SKIP_DIRS = {
    ".git", "node_modules", "dist", "build", ".next", ".nuxt", ".output", ".svelte-kit",
    "venv", ".venv", "env", "__pycache__", ".mypy_cache", ".pytest_cache", "Pods",
    ".gradle", "target", "vendor", ".turbo", ".cache", "coverage", ".idea", ".vscode",
}
SKIP_FILE_RE = re.compile(
    r"(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock|Pipfile\.lock|"
    r"Cargo\.lock|composer\.lock|Gemfile\.lock|go\.sum|\.min\.js|\.map|\.svg|\.png|"
    r"\.jpe?g|\.gif|\.webp|\.ico|\.pdf|\.woff2?|\.ttf|\.otf|\.mp[34]|\.mov|\.zip|"
    r"\.gz|\.aab|\.apk|\.ipa|\.jar)$",
    re.I,
)

# (label, regex, confidence). High-confidence patterns are also run over git history.
SECRET_PATTERNS = [
    ("AWS access key ID", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b", "high"),
    ("Stripe live secret key", r"\b[sr]k_live_[0-9A-Za-z]{16,}", "high"),
    ("Stripe test secret key", r"\b[sr]k_test_[0-9A-Za-z]{16,}", "medium"),
    ("Stripe webhook secret", r"\bwhsec_[0-9A-Za-z]{16,}", "high"),
    ("Anthropic API key", r"\bsk-ant-[A-Za-z0-9_\-]{20,}", "high"),
    ("OpenAI API key", r"\bsk-(?:proj-|svcacct-)?(?!ant-)[A-Za-z0-9_\-]{32,}", "high"),
    ("GitHub token", r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})", "high"),
    ("Slack token", r"\bxox[abprs]-[A-Za-z0-9-]{10,}", "high"),
    ("SendGrid API key", r"\bSG\.[A-Za-z0-9_\-]{16,}\.[A-Za-z0-9_\-]{16,}", "high"),
    ("Google API key (public if it is a Firebase web key; check restrictions)",
     r"\bAIza[0-9A-Za-z_\-]{35}\b", "medium"),
    ("Private key block", r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP |ENCRYPTED )?PRIVATE KEY", "high"),
    ("Connection string with password",
     r"\b(?:postgres(?:ql)?|mysql|mariadb|mongodb(?:\+srv)?|rediss?|amqps?)://[^\s:/@'\"`]+:[^\s@'\"`]+@[^\s'\"`]+",
     "high"),
    ("JWT literal (maybe a Supabase anon key = fine, or service_role = critical)",
     r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}", "medium"),
    ("Weak or tutorial secret value",
     r"(?i)\b(?:jwt_?secret|secret_?key|session_?secret|nextauth_secret|auth_secret|app_secret|token_secret)"
     r"\b[\"']?\s*[:=]\s*[\"']?(?:secret|changeme|change[-_]?me|your[-_]?secret[-_\w]*|supersecret|"
     r"mysecret|password|dev|test|123456|keyboard cat|django-insecure-[^\s\"']*)[\"']?(?:\s|$|,|;)", "medium"),
    ("Secret env var with a hardcoded fallback (applies silently if the var is missing)",
     r"(?i)(?:getenv|environ\.get|environ\.setdefault|config)\(\s*[\"'][A-Z0-9_]*(?:SECRET|KEY|PASSWORD|PASSWD|TOKEN)"
     r"[A-Z0-9_]*[\"']\s*,\s*[\"'][^\"']{3,}[\"']"
     r"|process\.env\.[A-Z0-9_]*(?:SECRET|KEY|PASSWORD|PASSWD|TOKEN)[A-Z0-9_]*\s*(?:\|\||\?\?)\s*[\"'`][^\"'`]{3,}[\"'`]",
     "medium"),
    ("Hardcoded credential assignment",
     r"(?i)\b(?:password|passwd|secret|api_?key|apikey|access_?token|auth_?token|private_?key|client_?secret)"
     r"\b[\"']?\s*[:=]\s*[\"'][^\"'\s$<>{}]{8,}[\"']", "low"),
]
COMPILED = [(label, re.compile(rx), conf) for label, rx, conf in SECRET_PATTERNS]
PLACEHOLDER_RE = re.compile(
    r"(?i)(example|placeholder|your[_-]|xxxx|<[^>]+>|\$\{|process\.env|os\.environ|getenv|"
    r"import\.meta\.env|changeme_in_prod|dummy|fake|sample|redacted|\*\*\*\*)"
)

MANIFESTS = {
    "package.json": "Node/JS", "requirements.txt": "Python", "pyproject.toml": "Python",
    "Pipfile": "Python", "setup.py": "Python", "go.mod": "Go", "Cargo.toml": "Rust",
    "Gemfile": "Ruby", "composer.json": "PHP", "pubspec.yaml": "Flutter/Dart",
    "pom.xml": "Java (Maven)", "build.gradle": "JVM (Gradle)", "build.gradle.kts": "JVM (Gradle)",
    "Package.swift": "Swift", "mix.exs": "Elixir", "deno.json": "Deno", "bun.lockb": "Bun",
}
INFRA_PATTERNS = [
    (r"(^|/)Dockerfile[^/]*$", "Dockerfile"),
    (r"(^|/)\.dockerignore$", ".dockerignore"),
    (r"(^|/)docker-compose[^/]*\.ya?ml$|(^|/)compose\.ya?ml$", "Docker Compose"),
    (r"(^|/)vercel\.json$", "Vercel"), (r"(^|/)netlify\.toml$|(^|/)_headers$|(^|/)_redirects$", "Netlify"),
    (r"(^|/)fly\.toml$", "Fly.io"), (r"(^|/)railway\.(json|toml)$", "Railway"),
    (r"(^|/)render\.yaml$", "Render"), (r"(^|/)Procfile$", "Procfile (Heroku-style)"),
    (r"(^|/)app\.yaml$", "Google App Engine"), (r"(^|/)wrangler\.(toml|jsonc?)$", "Cloudflare Workers"),
    (r"(^|/)serverless\.ya?ml$", "Serverless Framework"), (r"\.tf$", "Terraform"),
    (r"(^|/)firebase\.json$", "Firebase config"), (r"(^|/)firestore\.rules$", "Firestore rules"),
    (r"(^|/)database\.rules\.json$", "Realtime Database rules"), (r"(^|/)storage\.rules$", "Storage rules"),
    (r"(^|/)supabase/config\.toml$", "Supabase config"), (r"(^|/)supabase/migrations/", "Supabase migrations"),
    (r"(^|/)prisma/schema\.prisma$", "Prisma schema"), (r"(^|/)alembic\.ini$", "Alembic migrations"),
    (r"(^|/)nginx[^/]*\.conf$|(^|/)nginx/", "nginx config"), (r"(^|/)Caddyfile$", "Caddy config"),
    (r"(^|/)\.github/workflows/", "GitHub Actions"), (r"(^|/)\.gitlab-ci\.yml$", "GitLab CI"),
    (r"(^|/)\.github/dependabot\.yml$", "Dependabot"), (r"(^|/)renovate\.json5?$", "Renovate"),
    (r"(^|/)capacitor\.config\.(ts|js|json)$", "Capacitor (mobile)"),
    (r"(^|/)app\.json$|(^|/)eas\.json$", "Expo/React Native (check)"),
    (r"(^|/)(ios|android)/", "Native mobile project"), (r"(^|/)fastlane/", "fastlane"),
    (r"(^|/)robots\.txt$", "robots.txt"), (r"(^|/)sitemap[^/]*\.xml$", "sitemap"),
    (r"(^|/)(k6|loadtest|load-test|locust|artillery)[^/]*", "Load-test files (check)"),
    (r"(^|/)(privacy|terms)[^/]*\.(md|html|vue|tsx?|jsx?|svelte|astro)$", "Privacy/terms page (check)"),
]
SIGNALS = {
    "Auth": ["next-auth", "@auth/", "passport", "jsonwebtoken", "jose", "@clerk/", "lucia", "better-auth",
             "@supabase/auth", "firebase/auth", "auth0", "django-allauth", "fastapi-users", "python-jose",
             "pyjwt", "flask-login", "devise", "bcrypt", "argon2", "iron-session", "express-session"],
    "Payments": ["stripe", "@paddle/", "lemonsqueezy", "@lemonsqueezy/", "revenuecat", "purchases-capacitor",
                 "react-native-purchases", "braintree", "iyzipay", "paypal", "@polar-sh/"],
    "AI / LLM": ["openai", "@anthropic-ai/", "anthropic", "langchain", "@langchain/", "llamaindex",
                 "llama-index", "@ai-sdk/", "\"ai\"", "@google/genai", "google-generativeai", "ollama",
                 "mistralai", "cohere", "groq", "replicate", "@modelcontextprotocol/"],
    "Uploads / object storage": ["multer", "formidable", "busboy", "uploadthing", "@aws-sdk/client-s3",
                                 "aws-sdk", "boto3", "cloudinary", "python-multipart", "@vercel/blob",
                                 "firebase/storage", "@uppy/"],
    "Database / data": ["prisma", "@prisma/client", "drizzle-orm", "mongoose", "mongodb", "sequelize",
                        "typeorm", "knex", "\"pg\"", "mysql2", "better-sqlite3", "sqlalchemy", "psycopg",
                        "asyncpg", "django", "redis", "ioredis", "@supabase/supabase-js", "firebase",
                        "firebase-admin", "@neondatabase/", "@planetscale/", "convex", "pocketbase"],
    "Monitoring / analytics": ["@sentry/", "sentry-sdk", "posthog", "mixpanel", "@amplitude/", "datadog",
                               "dd-trace", "logrocket", "newrelic", "pino", "winston", "structlog",
                               "@opentelemetry/", "@vercel/analytics", "react-ga", "gtag"],
    "Security middleware": ["helmet", "express-rate-limit", "rate-limiter-flexible", "@upstash/ratelimit",
                            "slowapi", "django-ratelimit", "flask-limiter", "cors", "csurf", "csrf",
                            "flask-talisman", "django-csp", "dompurify", "isomorphic-dompurify",
                            "sanitize-html", "bleach", "zod", "joi", "yup", "valibot", "pydantic",
                            "class-validator", "express-validator"],
    "Queues / background jobs": ["bull", "bullmq", "bee-queue", "agenda", "celery", "rq", "dramatiq",
                                 "huey", "sidekiq", "inngest", "@trigger.dev/", "node-cron", "apscheduler"],
    "Ads": ["adsense", "admob", "@capacitor-community/admob", "react-native-google-mobile-ads"],
    "Mobile / desktop wrapper": ["@capacitor/", "react-native", "expo", "electron", "tauri", "flutter"],
    "Testing": ["jest", "vitest", "mocha", "@playwright/", "playwright", "cypress", "pytest", "k6",
                "artillery", "locust", "supertest", "@testing-library/"],
}
TOOLS = ["gitleaks", "trufflehog", "semgrep", "bandit", "osv-scanner", "pip-audit", "npm", "pnpm",
         "yarn", "trivy", "docker", "zap.sh", "nuclei"]


def run(cmd, cwd, timeout=60):
    try:
        out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                             errors="replace")
        return out.stdout if out.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


LOCAL_HOST_RE = re.compile(r"@(localhost|127\.0\.0\.1|0\.0\.0\.0|host|db|postgres|redis|example\.\w+)[:/]", re.I)


def redact(value):
    value = value.strip()
    fb = re.search(r"([A-Z0-9_]*(?:SECRET|KEY|PASSWORD|PASSWD|TOKEN)[A-Z0-9_]*).*[\"'`]([^\"'`]+)[\"'`]$", value)
    if fb and ("getenv" in value or "environ" in value or "process.env" in value or "config(" in value):
        return f"{fb.group(1)} falls back to '{fb.group(2)[:2]}…' ({len(fb.group(2))} chars)"
    m = re.match(r"^(\w[\w+.-]*://[^\s:/@]+:)([^\s@]+)(@.*)$", value)
    if m:
        note = " (local or placeholder host: likely dev-only)" if LOCAL_HOST_RE.search(value) else ""
        return f"{m.group(1)}****{m.group(3)[:40]}{note}"
    if len(value) <= 8:
        return value[:2] + "…"
    return f"{value[:6]}…[{len(value)} chars]"


def list_files(root, in_git):
    if in_git:
        out = run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], root)
        files = [f for f in out.split("\0") if f]
        return [f for f in files if not any(part in SKIP_DIRS for part in f.split("/")[:-1])]
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            files.append(os.path.relpath(os.path.join(dirpath, name), root))
    return files


def jwt_role(token):
    try:
        part = token.split(".")[1]
        payload = json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))
        return payload.get("role") if isinstance(payload, dict) else None
    except (ValueError, IndexError):
        return None


def scan_text(text, confidences):
    hits = []
    for label, rx, conf in COMPILED:
        for m in rx.finditer(text):
            value, eff_label, eff_conf = m.group(0), label, conf
            if label.startswith("JWT literal"):
                role = jwt_role(value)
                if role == "service_role":
                    eff_label, eff_conf = "Supabase service_role key (bypasses RLS)", "high"
                elif role == "anon":
                    eff_label, eff_conf = "Supabase anon key (public by design if RLS is on)", "low"
            if eff_conf in confidences:
                hits.append((eff_label, eff_conf, value))
    return hits


def section(title):
    print(f"\n## {title}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--history-seconds", type=int, default=90,
                    help="time budget for the git history scan (default 90)")
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        sys.exit(f"Not a directory: {root}")

    in_git = run(["git", "rev-parse", "--is-inside-work-tree"], root).strip() == "true"
    files = list_files(root, in_git)
    tracked = set(f for f in run(["git", "ls-files", "-z"], root).split("\0") if f) if in_git else set()

    print(f"# vibe-check recon: {root}")
    if in_git:
        sha = run(["git", "rev-parse", "--short", "HEAD"], root).strip() or "(no commits)"
        branch = run(["git", "branch", "--show-current"], root).strip()
        remotes = sorted(set(line.split()[1] for line in run(["git", "remote", "-v"], root).splitlines()
                             if len(line.split()) > 1))
        print(f"- Git: commit {sha} on '{branch}', {len(tracked)} tracked files")
        print(f"- Remotes: {', '.join(remotes) if remotes else 'none'}")
    else:
        print("- Not a git repository: history checks skipped (#13 needs another way to verify)")
    print(f"- Files scanned (excluding dependency/build dirs): {len(files)}")

    section("Stack manifests")
    found = [(f, MANIFESTS[os.path.basename(f)]) for f in files if os.path.basename(f) in MANIFESTS]
    for f, kind in sorted(found)[:40]:
        print(f"- {f} ({kind})")
    if not found:
        print("- none found")

    section("Infrastructure, deploy and policy files")
    infra = {}
    for f in files:
        for rx, label in INFRA_PATTERNS:
            if re.search(rx, f):
                infra.setdefault(label, []).append(f)
    for label in sorted(infra):
        sample = infra[label][:4]
        more = f" (+{len(infra[label]) - 4} more)" if len(infra[label]) > 4 else ""
        print(f"- {label}: {', '.join(sample)}{more}")
    if not infra:
        print("- none found")

    section("Dependency signals (decide N/A items from these, then confirm in code)")
    manifest_text = ""
    for f, _ in found:
        try:
            with open(os.path.join(root, f), encoding="utf-8", errors="replace") as fh:
                content = fh.read()
            if f.endswith("package.json"):
                try:
                    data = json.loads(content)
                    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                    content = "\n".join(f'"{k}": "{v}"' for k, v in deps.items())
                except ValueError:
                    pass
            manifest_text += "\n" + content.lower()
        except OSError:
            continue
    for group, needles in SIGNALS.items():
        hits = sorted({n.strip('"') for n in needles if n in manifest_text})
        print(f"- {group}: {', '.join(hits) if hits else 'none detected'}")

    section("Env files (#2, #67)")
    env_files = [f for f in files if re.search(r"(^|/)\.env(\.|$)", f)]
    if in_git:
        env_files += [f for f in tracked if re.search(r"(^|/)\.env(\.|$)", f) and f not in env_files]
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in filenames:
                if re.match(r"^\.env(\.|$)", name):
                    rel = os.path.relpath(os.path.join(dirpath, name), root)
                    if rel not in env_files:
                        env_files.append(rel)
    if not env_files:
        print("- no .env files on disk or in git")
    for f in sorted(set(env_files)):
        example = bool(re.search(r"\.(example|sample|template|dist)$", f))
        if in_git:
            if f in tracked:
                state = "TRACKED in git" + (" (example file: check values are placeholders)" if example
                                            else " <- likely problem")
            elif subprocess.run(["git", "check-ignore", "-q", f], cwd=root).returncode == 0:
                state = "on disk, ignored by git (fine)"
            else:
                state = "on disk, NOT ignored by git <- add to .gitignore"
        else:
            state = "on disk"
        print(f"- {f}: {state}")
    if in_git:
        ever = sorted(set(
            line for line in run(["git", "log", "--all", "--diff-filter=A", "--name-only",
                                  "--format="], root, timeout=120).splitlines()
            if re.search(r"(^|/)\.env(\.|$)", line) and not re.search(r"\.(example|sample|template)$", line)
        ))
        if ever:
            print(f"- EVER COMMITTED (in history even if deleted since): {', '.join(ever)}")
            print("  -> treat every secret in those files as leaked; rotate")
        else:
            print("- no non-example .env file was ever committed")

    section("Secret-looking strings in current files (values redacted; verify each before reporting)")
    count = 0
    by_conf = {"high": [], "medium": [], "low": []}
    for f in files:
        if SKIP_FILE_RE.search(f):
            continue
        path = os.path.join(root, f)
        try:
            if os.path.getsize(path) > 1_000_000:
                continue
            with open(path, encoding="utf-8", errors="strict") as fh:
                lines = fh.readlines()
        except (OSError, UnicodeDecodeError):
            continue
        for i, line in enumerate(lines, 1):
            for label, conf, value in scan_text(line, {"high", "medium", "low"}):
                if conf != "high" and not label.startswith("Secret env var") and PLACEHOLDER_RE.search(line):
                    continue
                by_conf[conf].append(f"- [{conf}] {label}: {f}:{i} -> {redact(value)}")
                count += 1
    for conf in ("high", "medium", "low"):
        items = by_conf[conf]
        for item in items[:40]:
            print(item)
        if len(items) > 40:
            print(f"- … {len(items) - 40} more {conf}-confidence hits")
    if count == 0:
        print("- none found")

    if in_git:
        section(f"Secret-looking strings in git history (high-confidence patterns, {args.history_seconds}s budget)")
        start = time.time()
        seen, truncated = {}, False
        proc = subprocess.Popen(
            ["git", "log", "--all", "-p", "--no-color", "--no-ext-diff", "--format=@@commit %h %as"],
            cwd=root, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, errors="replace")
        commit, current_file = "?", "?"
        for line in proc.stdout:
            if time.time() - start > args.history_seconds:
                truncated = True
                break
            if line.startswith("@@commit "):
                commit = line.split()[1] + " " + (line.split()[2] if len(line.split()) > 2 else "")
            elif line.startswith("+++ b/"):
                current_file = line[6:].strip()
            elif line.startswith("+") and not line.startswith("+++"):
                if SKIP_FILE_RE.search(current_file):
                    continue
                for label, conf, value in scan_text(line, {"high"}):
                    key = (label, value)
                    if key not in seen:
                        seen[key] = f"- {label}: first seen in {commit.strip()} {current_file} -> {redact(value)}"
        proc.kill()
        proc.wait()
        for entry in list(seen.values())[:40]:
            print(entry)
        if len(seen) > 40:
            print(f"- … {len(seen) - 40} more")
        if not seen:
            print("- none found" + (" (scan truncated)" if truncated else ""))
        if truncated:
            print("- history scan hit its time budget: rerun with --history-seconds 600, or use gitleaks")

    section("Source map settings (#36)")
    sm_hits = []
    for f in files:
        base = os.path.basename(f)
        if re.match(r"(vite|next|nuxt|webpack|svelte|astro|vue|angular|craco|rollup)\.config\.|angular\.json$|"
                    r"^\.env|^package\.json$", base):
            try:
                with open(os.path.join(root, f), encoding="utf-8", errors="replace") as fh:
                    for i, line in enumerate(fh, 1):
                        if re.search(r"(?i)sourcemap|source-map|productionBrowserSourceMaps|devtool|"
                                     r"GENERATE_SOURCEMAP", line):
                            sm_hits.append(f"- {f}:{i}: {line.strip()[:120]}")
            except OSError:
                continue
    print("\n".join(sm_hits[:20]) if sm_hits else "- no explicit source-map settings (check the bundler default)")
    build_maps = [f for f in files if f.endswith(".map") and re.search(r"(^|/)(dist|build|public|out)/", f)]
    if build_maps:
        print(f"- .map files in build/public output: {', '.join(build_maps[:5])}")

    section("Tools available on this machine")
    for tool in TOOLS:
        print(f"- {tool}: {'yes' if shutil.which(tool) else 'no'}")

    print("\nNext: read README, entry points, routes, middleware, auth, schema and deploy config, "
          "then write the stack profile.")


if __name__ == "__main__":
    main()
