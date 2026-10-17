# The 84-item checklist

Numbering is fixed. Reports, follow-ups and past runs all refer to items by number ("#29 is still open"), so never renumber, merge or drop items. Several items overlap on purpose (the same risk seen from a different angle); investigate them together but give each its own verdict.

Each entry has:
- **Look for**: where the problem usually hides and what to search.
- **Good**: what a handled item looks like, so you know when to mark it OK.
- **N/A when**: the condition that makes it not apply. An N/A still needs the evidence that the condition holds.
- **Usual severity**: a starting point for a GAP. Adjust it to the actual exposure.

## Contents by category

Investigate one category at a time. Items in a category share evidence.

| Category | Items |
|---|---|
| Secrets and credentials | 1, 2, 3, 11, 13, 14, 26, 30, 67 |
| Authentication, authorization, sessions | 4, 5, 6, 9, 15, 24, 25, 33, 34, 47 |
| Input handling and injection | 16, 17, 18, 19, 20, 21, 22, 23, 64 |
| Database and storage access | 7, 8, 41, 48, 49, 71, 73 |
| API surface and traffic | 27, 28, 31, 32, 58, 65, 82 |
| Production exposure | 10, 12, 29, 36, 45, 46, 60, 77 |
| Dependencies and review process | 37, 38, 50, 79 |
| AI features | 39, 40 |
| Operations, logging, recovery | 35, 42, 43, 44, 66, 75, 76 |
| Architecture and scale | 51, 52, 53, 54, 59, 68, 72 |
| Hands-on security testing | 57, 78 |
| Legal, privacy, business | 61, 62, 63, 69, 70, 74, 83, 84 |
| Discoverability and support | 55, 56, 80, 81 |

---

### 1. Exposed database credentials
- **Look for:** connection strings with a password (`postgres://user:pass@`, `mongodb+srv://`, `redis://:pass@`) in code, config, `docker-compose.yml`, CI files, docs, notebooks, seed scripts, and git history (`recon.py` lists hits). A database reachable from the internet: a published port in compose on a server, a public proxy URL from the host, Atlas allowing `0.0.0.0/0`.
- **Good:** credentials come only from env or a secret manager; compose uses `${POSTGRES_PASSWORD:?}` with no default; any credential that ever reached git has been rotated (deleting the commit does not un-leak it).
- **Usual severity:** CRITICAL for live production credentials in a public repo or bundle; HIGH in a private repo.

### 2. Public .env files
- **Look for:** `.env*` files tracked now or ever committed (`recon.py`), `.gitignore` and `.dockerignore` coverage, `COPY . .` in a Dockerfile with no `.dockerignore` (bakes `.env` into the image), a web server whose root is the project folder (serves `/.env`). On a live site, a passive `GET /.env` should 404.
- **Good:** `.env` ignored by git and Docker; a `.env.example` with placeholders only.
- **Note:** variables with a public prefix (`VITE_`, `NEXT_PUBLIC_`, `REACT_APP_`, `EXPO_PUBLIC_`, `PUBLIC_`) are shipped to the browser by design. Judge those under #14.
- **Usual severity:** CRITICAL if a real `.env` is in a public repo or served; HIGH if in history of a private repo.

### 3. Hardcoded API keys
- **Look for:** `recon.py` secret hits; string literals assigned to names like `key`, `token`, `secret`, `password`; keys in tests, fixtures, seed scripts, README examples, native mobile config (`Info.plist`, `AndroidManifest.xml`, `strings.xml`).
- **Separate publishable from secret:** Stripe `pk_`, the Firebase web `apiKey`, a Supabase anon key, and a referrer-restricted Google Maps key are meant to be public. Stripe `sk_`, OpenAI/Anthropic keys, a Supabase `service_role` key, and cloud access keys are not.
- **Good:** all secret keys come from env; publishable keys are restricted by domain or bundle ID where the provider allows.
- **Usual severity:** CRITICAL for a working secret key in client code or a public repo.

### 4. Weak or missing authentication
- **Look for:** which auth exists and where it is enforced; handlers that return or change private data with no auth middleware; WebSocket connections that skip the auth HTTP gets; homemade password storage (plain text, MD5, SHA-1 instead of bcrypt, argon2 or scrypt); login with no brute-force protection (#28); magic links and OTPs with no expiry; admin accounts without MFA.
- **Good:** a proven provider or framework auth, enforced server-side on every protected route and socket.
- **N/A when:** the app has no accounts at all. Then check that whatever replaces auth (room codes, share links, capability URLs) is long and random enough not to be guessed.
- **Usual severity:** CRITICAL when private data or actions are reachable without auth.

### 5. No authorization checks
- **Look for:** handlers that check *who* the user is but not *whether they may* do this (role, ownership, plan). Compare the full route list with where middleware is applied: Next.js `middleware.ts` matchers with gaps, server actions and API routes that each need their own check, GraphQL resolvers, admin actions hidden only in the UI.
- **Good:** deny by default; one shared policy helper; tests for the forbidden paths.
- **Usual severity:** CRITICAL to HIGH.

### 6. Users able to access other users' data
- **Look for:** lookups by ID that are not scoped to the current user or org (`findById(req.params.id)` instead of `where: { id, userId: session.user.id }`); list, search and export endpoints that return every row; responses that over-share (password hashes, other users' emails, internal flags); direct client queries to Supabase or Firebase that rely on RLS or rules (#73, #8).
- **Good:** every query is scoped by the session's identity; a test where user A asks for user B's record and gets 403/404.
- **Investigate with:** #33 and #34.
- **Usual severity:** CRITICAL.

### 7. Open database read/write permissions
- **Look for:** Firestore or Realtime Database rules with `allow read, write: if true`, or `if request.auth != null` on everything (any signed-up stranger can read all data); Supabase tables without RLS while the anon key is in the frontend; a database or Redis reachable from the internet without an IP allowlist or password; PostgREST, Hasura or GraphQL auto-exposing whole tables.
- **Good:** the database sits on a private network, or every client-facing path is locked by per-user rules or RLS.
- **Usual severity:** CRITICAL.

### 8. Misconfigured Firebase / Supabase / S3 buckets
- **Look for:** `storage.rules`, Supabase storage policies, S3 bucket policies and ACLs in infrastructure code (`public-read`, `"Principal": "*"`), public buckets holding private things (user uploads, exports, **database backups**), listing enabled, presigned URLs that live for days, uploads with no size or type limits.
- **Bucket settings often live only in a dashboard.** Then make it an OWNER check with exact steps: public access off, no public URL, access key scoped to the one bucket with the least permissions.
- **Good:** private by default; public buckets contain only public assets.
- **Usual severity:** CRITICAL if private data is publicly listable or readable.

### 9. Admin routes left unprotected
- **Look for:** `/admin`, `/dashboard`, `/internal`, `/api/admin`, `/manage`; dev leftovers like `/api/seed`, `/api/reset`, `/debug`; bundled panels (Django admin, Strapi, Directus, Prisma Studio, Adminer, Bull Board, Flower); admin checks done only on the client (a hidden menu item).
- **Good:** a server-side role check in every admin handler; MFA for admins; optional IP restriction.
- **N/A when:** no admin routes or panels exist (say what you searched).
- **Usual severity:** CRITICAL if reachable without auth; HIGH if any logged-in user can reach it.

### 10. Debug pages exposed in production
- **Look for:** Django `DEBUG = True`, the Flask/Werkzeug debugger (an interactive console means remote code execution), `NODE_ENV` not set to production, a dev build deployed, Spring actuator, `phpinfo`, Laravel Telescope or debugbar, Rails web-console, GraphQL playground or introspection, FastAPI docs exposing internal routes, health endpoints that print env or config. Check how production decides: a debug flag that defaults to **on** when an env var is missing is a GAP.
- **Good:** debug is off unless explicitly enabled; docs and introspection are off or harmless in production.
- **Usual severity:** CRITICAL for an interactive debugger; MEDIUM for docs or verbose health output.

### 11. Build logs leaking secrets
- **Look for:** CI steps that `echo` secrets, `set -x` in scripts that use secrets, `env` or `printenv` steps, secrets passed as Docker `--build-arg` (they stay in image history), app startup lines that print config or full connection URLs (a logged `DATABASE_URL` or `REDIS_URL` includes the password), public CI logs (a public repo has public Actions logs).
- **Hosting dashboards hold the real logs:** add an OWNER check to skim one recent build log and one deploy log for secrets.
- **Good:** secrets are masked; startup logs print host and port only.
- **Usual severity:** HIGH if a live secret is printed anywhere others can read.

### 12. Verbose error messages leaking stack traces
- **Look for:** error handlers that return `err.message`, `err.stack` or `str(e)` to the client; `res.status(500).json({ error })`; database errors passed through (they reveal schema); GraphQL `debug: true` or `includeStacktraceInErrorResponses`; framework debug pages (#10). Passive live check: request a route that doesn't exist and send an invalid body.
- **Good:** the client gets a short message and an error code; the stack goes to logs or the error tracker.
- **Usual severity:** MEDIUM; HIGH if it leaks secrets or queries.

### 13. Leaked GitHub repos or commit history
- **Look for:** is the repo public? Find the remote with `git remote -v`, then check anonymously: `curl -s -o /dev/null -w "%{http_code}" https://github.com/<owner>/<repo>` returns 404 for private. Secrets anywhere in history (`recon.py` scans it; run `gitleaks git` too if installed). A served `.git` folder on the live site (`GET /.git/config` should 404). Public forks of a repo that used to be public. Published Docker images or npm packages that include source or `.env`.
- **Good:** private repo (or public with a clean history); every secret that ever touched git has been rotated.
- **Usual severity:** CRITICAL if a public history contains live secrets.

### 14. Secrets included in frontend JavaScript
- **Look for:** env vars with a public prefix (`VITE_`, `NEXT_PUBLIC_`, `REACT_APP_`, `EXPO_PUBLIC_`, `PUBLIC_`) holding secret values; server SDKs used in client code (OpenAI, Stripe secret, Supabase `service_role`, `firebase-admin`); `"use client"` files importing server-only modules. **Mobile bundles count:** anything in a Capacitor, React Native or Flutter app can be unpacked and read. If a build output exists (`dist/`, `build/`, `.next/static/`), grep it for key patterns.
- **Good:** the client holds only publishable keys; anything secret is called through the backend.
- **Usual severity:** CRITICAL for a usable secret key in the bundle.

### 15. Client-side-only security checks
- **Look for:** permissions, plan limits, prices, quotas or validation enforced only in the UI (disabled buttons, hidden routes, frontend-only form rules) while the API accepts anything; `isAdmin` or `isPro` read from localStorage; game results or scores computed on the client and trusted by the server.
- **Good:** the server re-checks everything; client checks are only for UX.
- **Usual severity:** HIGH to CRITICAL, depending on what can be bypassed.

### 16. Missing input validation
- **Look for:** request bodies, params, headers and WebSocket messages used without a schema (zod, joi, yup, valibot, pydantic, class-validator, Django forms or serializers); no length limits (huge strings fill storage or slow the server); no request body size limit; **mass assignment** (`User.update(req.body)`, Prisma `data: req.body`, `Model(**data)`), where a user can send `role: "admin"`.
- **Good:** a schema at every boundary, with an allowlist of fields and limits on size.
- **Investigate with:** #64.
- **Usual severity:** HIGH for mass assignment of privileged fields; MEDIUM otherwise.

### 17. SQL injection
- **Look for:** SQL built with concatenation, f-strings or template literals that contain user input; raw query APIs (`$queryRawUnsafe`, `$executeRawUnsafe`, `sequelize.query` with interpolation, `knex.raw` with concatenation, `cursor.execute(f"...")`, SQLAlchemy `text(f"...")`, Django `.extra()` and `RawSQL`); column names or `ORDER BY` taken from input (parameters don't protect identifiers; use an allowlist). Trace each hit back to see whether user input can reach it.
- **Good:** parameterized queries or an ORM everywhere; allowlists for identifiers.
- **N/A when:** no SQL database.
- **Usual severity:** CRITICAL when reachable.

### 18. NoSQL injection
- **Look for:** MongoDB filters built from raw request objects (`find({ email: req.body.email })` accepts `{"$ne": null}` and can bypass login); `$where` with user strings; `$regex` from input (also a ReDoS risk); Redis keys or commands built from unsanitized input; Firestore paths taken from input.
- **Good:** inputs cast to the expected type or validated before they reach a query.
- **N/A when:** no NoSQL store is used, or keys come only from validated or server-generated values (say which).
- **Usual severity:** CRITICAL for an auth bypass; HIGH otherwise.

### 19. Cross-site scripting (XSS)
- **Look for:** `dangerouslySetInnerHTML`, `v-html`, `innerHTML`, Svelte `{@html}`, Angular `[innerHTML]`, template escapes turned off (`|safe`, `mark_safe`, `{!! !!}`, `html_safe`); Markdown rendered with raw HTML allowed and no sanitizer; `href` or `src` from user input (`javascript:` URLs); user data inside an inline `<script>` without escaping; `eval` or `new Function` on user data; user SVGs served from your own origin. A Content Security Policy is the backstop (#46).
- **Good:** framework escaping everywhere, DOMPurify for any HTML that must render, and an enforced CSP.
- **Usual severity:** HIGH for stored XSS; MEDIUM for reflected.

### 20. Cross-site request forgery (CSRF)
- **Look for:** cookie-based auth (session cookie, or JWT in a cookie) combined with state-changing requests that have no CSRF token and no `SameSite` protection; GET requests that change state; CORS with credentials and reflected origins (#27). Framework protection switched off (`csrf_exempt`, Rails `protect_from_forgery` removed, Laravel `$except` lists). Express has no default protection.
- **Good:** `SameSite=Lax` or `Strict` cookies plus tokens or Origin checks on state-changing requests.
- **N/A when:** auth uses only an `Authorization` header with no cookies. Say so explicitly.
- **Usual severity:** HIGH when exploitable on sensitive actions.

### 21. Insecure file uploads
- **Look for:** upload endpoints with no size limit; file type checked only by extension or the client's MIME type (check the real content); files saved inside the web root and served from the app's own origin (an uploaded HTML or SVG becomes stored XSS; on some servers, code execution); user-supplied filenames used as paths (#22); image processing on untrusted files; public buckets (#8); presigned uploads with no constraints.
- **Good:** size and type allowlists, random server-side names, user files on a separate domain or bucket, `Content-Disposition: attachment` for anything that isn't an image.
- **N/A when:** no upload endpoints exist (say what you searched: multipart parsers, `UploadFile`, `FormData`, presigned URLs).
- **Usual severity:** HIGH.

### 22. Path traversal bugs
- **Look for:** user input inside filesystem paths (`path.join(dir, req.params.file)`, `open(f"uploads/{name}")`, `send_file`, `res.sendFile`, `fs.readFile`); zip extraction without checking entry paths (zip slip); custom static file handlers; template names taken from input.
- **Good:** resolve the path, then confirm it is still inside the allowed folder; or map IDs to paths on the server.
- **N/A when:** no user-derived file paths exist.
- **Usual severity:** HIGH to CRITICAL.

### 23. Server-side request forgery (SSRF)
- **Look for:** the server fetching a URL a user supplied: link previews, user-configured webhooks, image import from URL, PDF or screenshot generators, OIDC discovery URLs, AI tools that browse. The danger is the server reaching cloud metadata (`169.254.169.254`), localhost admin ports or internal services.
- **Good:** an allowlist of hosts; private and link-local IP ranges blocked after DNS resolution; redirects not followed to internal addresses; timeouts.
- **N/A when:** outbound requests go only to fixed hosts, with user input only in validated query values.
- **Usual severity:** HIGH; CRITICAL on cloud hosts with a reachable metadata service.

### 24. Broken password reset flows
- **Look for:** reset tokens that are short, guessable, reusable or never expire; the reset link built from the request `Host` header (host-header poisoning); messages that reveal whether an email has an account; sessions not invalidated after a reset; no rate limit on reset requests; the token leaking through `Referer` to third-party scripts on the reset page. With a provider (Supabase Auth, Firebase Auth, Clerk, Auth0), check its redirect URL allowlist instead.
- **Good:** random single-use tokens that expire within an hour, fixed base URL, sessions revoked after reset.
- **N/A when:** there are no passwords.
- **Usual severity:** HIGH.

### 25. Weak session management
- **Look for:** session IDs or tokens not from a secure random source, or too short; no expiry (absolute and idle); not rotated on login (session fixation); not invalidated on the server at logout or password change; JWTs with no or very long expiry and no revocation; refresh tokens with no reuse detection; tokens in localStorage (readable by any XSS) instead of an HttpOnly cookie.
- **Good:** provider or framework sessions with sane defaults, expiry, and server-side revocation.
- **Usual severity:** MEDIUM to HIGH.

### 26. JWT secrets that are weak, leaked, or reused
- **Look for:** hardcoded or tutorial secrets (`"secret"`, `"changeme"`, `"your-secret-key"`; `recon.py` flags common ones); the same secret in every environment; a secret committed to git; tokens decoded without verifying (`jwt.decode` used for auth); `alg: none` accepted or the algorithm not pinned at verify time; secrets shorter than 32 random bytes.
- **Good:** a random 256-bit-or-longer secret from env, different per environment, rotated if it ever leaked, algorithms pinned.
- **N/A when:** no JWTs are issued or verified. Say what the app uses instead.
- **Usual severity:** CRITICAL for a known or leaked signing secret (anyone can mint admin tokens).

### 27. Overly permissive CORS
- **Look for:** `origin: "*"` or `allow_origins=["*"]`, especially together with credentials; the request's Origin reflected back (`origin: true`, a callback that always allows); regexes that also match `evil-yourdomain.com` or `yourdomain.com.evil.com`; the `null` origin allowed; localhost allowed in production.
- **Remember:** CORS only limits browsers. It is not access control (#65).
- **Good:** an explicit list of origins per environment.
- **Usual severity:** HIGH with credentials; LOW for a public, unauthenticated read API.

### 28. Rate limits missing on login, signup and APIs — all endpoints, basically
- **Look for:** the rate-limiting middleware and its real coverage. List every route and mark which are limited. Login, signup, password reset, OTP, contact forms, and anything that costs money per call (SMS, email, LLM calls, paid third-party APIs) matter most. Also: a limiter keyed on a client IP read from a spoofable header (the first value of `X-Forwarded-For`) without trusted-proxy config; an in-memory limiter running on several instances (each keeps its own count); no limits on WebSocket connections or messages.
- **Good:** a default limit on everything, stricter limits on sensitive or costly routes, the correct client IP, and a shared store (such as Redis) when there is more than one instance.
- **Usual severity:** HIGH for auth and paid endpoints; MEDIUM elsewhere.

### 29. Public test or staging environments
- **Look for:** staging, preview or dev deployments mentioned in config, CI or docs (Vercel preview URLs, `staging.` subdomains, `*.up.railway.app`, `*.onrender.com`, `*.herokuapp.com`, `*.fly.dev`, `*.pages.dev`), especially with weaker settings (debug on, auth or rate limits off, seeded test accounts, copies of production data); preview deployments wired to the production database or secrets.
- **Good:** staging behind auth or an IP allowlist, or deleted when unused; never real user data.
- **Often partly OWNER:** list deployments in the hosting dashboard.
- **Usual severity:** HIGH if it holds real data or production secrets.

### 30. Default credentials left unchanged
- **Look for:** seed scripts that create `admin`/`admin` or `admin@example.com`/`password`; compose defaults (`POSTGRES_PASSWORD: postgres`, `minioadmin`, RabbitMQ `guest`, Grafana `admin`, Redis without a password) used beyond local dev; config fallbacks such as `process.env.SECRET || "dev-secret"` or `os.getenv("SECRET_KEY", "changeme")` that quietly apply in production; Django keys starting `django-insecure-`.
- **Good:** no fallback values for secrets; the app refuses to start in production when one is missing.
- **Usual severity:** CRITICAL if a default works in production; MEDIUM for a fallback that would only apply if config is missing.

### 31. Webhook endpoints without signature verification
- **Look for:** inbound webhook handlers (Stripe, Paddle, Lemon Squeezy, RevenueCat, Clerk, GitHub, Twilio, Shopify, Resend, custom). Is the signature checked against the **raw** body (a JSON body parser placed before the route breaks Stripe verification, and developers then delete the check)? Is there a timestamp tolerance against replays? Is processing idempotent, so a retried event can't grant credit twice?
- **Good:** the provider's official verification helper, raw body, idempotency key stored.
- **N/A when:** no inbound webhooks exist.
- **Usual severity:** CRITICAL for payment webhooks; HIGH otherwise.

### 32. Payment or subscription checks only done on the frontend
- **Look for:** premium features unlocked by a client flag; the amount or price sent by the client and trusted at checkout; a success page that grants access without the server confirming the payment; subscription status read from client storage; mobile in-app purchases unlocked without server-side receipt validation or an entitlement check (such as RevenueCat).
- **Good:** entitlements stored on the server, updated only from verified webhooks or receipts, checked on every paid action.
- **N/A when:** nothing is sold.
- **Usual severity:** CRITICAL.

### 33. Insecure direct object references (IDOR)
- **Look for:** guessable or sequential IDs in URLs, API bodies, WebSocket messages, download links and share links, combined with a missing ownership check (#6). Random UUIDs make guessing harder but are not access control.
- **Good:** every object lookup checks ownership or membership on the server.
- **Investigate with:** #6 and #34.
- **Usual severity:** CRITICAL.

### 34. API endpoints that trust user-controlled IDs or roles
- **Look for:** `userId`, `role`, `orgId`, `isAdmin`, `plan` or `price` taken from the body, query or headers instead of the verified session; client-set headers like `X-User-Id`; JWT claims used without verifying the signature; hidden form fields.
- **Good:** identity and role come only from the verified session or token.
- **Usual severity:** CRITICAL.

### 35. Logs containing tokens, emails, passwords, or private user data
- **Look for:** log calls that print request bodies, headers (`Authorization`, cookies), full user objects, emails, phone numbers, tokens or passwords; logged URLs that carry tokens (reset links, magic links, `?token=`); error tracking set to send PII (Sentry `sendDefaultPii: true`, request bodies, session replay without masking); analytics events with emails.
- **Good:** redaction in the logger, PII off in error tracking, user IDs instead of emails.
- **Usual severity:** HIGH for passwords or tokens; MEDIUM for emails and IPs.

### 36. Source maps exposed in production
- **Look for:** Next.js `productionBrowserSourceMaps: true`, Vite `build.sourcemap: true`, webpack `devtool: 'source-map'` in production, Create React App (generates maps by default unless `GENERATE_SOURCEMAP=false`), `.map` files in the build output. Passive live check: open a JS asset, look for `//# sourceMappingURL=`, request that `.map`.
- **Good:** no public maps; maps uploaded privately to the error tracker (`hidden` source maps, then deleted from the output).
- **Usual severity:** LOW to MEDIUM (it exposes code and comments, not a hole by itself); HIGH if the source contains secrets.

### 37. Dependency vulnerabilities
- **Look for:** run the ecosystem's audit (`npm audit --omit=dev`, `pnpm audit`, `yarn npm audit`, `pip-audit`, `cargo audit`, `bundle audit`, or `osv-scanner` if installed). Record counts by severity and focus on runtime dependencies. Note whether audits run in CI (#79) and whether Dependabot or Renovate is set up.
- **Good:** no known high or critical issues in runtime dependencies; automated alerts on.
- **Usual severity:** follow the advisory, adjusted for whether the vulnerable code path is used.

### 38. Outdated packages
- **Look for:** `npm outdated`, `pip list --outdated` (inside the project's environment); runtimes and frameworks past end of security support (Node, Python, Next.js, Django and so on); no lockfile committed (unpinned versions upgrade by surprise); abandoned packages.
- **Good:** a committed lockfile, supported runtime versions, a routine for updates.
- **Usual severity:** LOW to MEDIUM; HIGH for an end-of-life runtime.

### 39. Prompt injection in AI features
- **Look for:** LLM calls where user-controlled or third-party content (web pages, uploaded files, emails, other users' messages) goes into the prompt; model output trusted to take actions, render as HTML (XSS through the model), run code, query the database or call tools; secrets inside the system prompt; no validation of model output.
- **Good:** model output treated as untrusted input; tools with least privilege; human confirmation for destructive actions; untrusted content clearly separated from instructions.
- **N/A when:** no LLM calls exist (check dependencies and grep for API calls; `recon.py` lists AI SDKs).
- **Usual severity:** HIGH when the model can take actions or see other users' data; MEDIUM otherwise.

### 40. AI tools/actions allowed to access data without permission checks
- **Look for:** function calling, agents or MCP tools that read the database, send email or call internal APIs. Do they run with the **requesting user's** permissions or with a service account that can see everything? Can a user ask the bot for someone else's data? Vector stores and RAG retrieval without a per-user or per-tenant filter.
- **Good:** tools enforce the same authorization as the API (#5, #6); every retrieval query is filtered by tenant.
- **N/A when:** the AI features use no tools or retrieval over private data.
- **Usual severity:** CRITICAL if cross-user data is reachable.

### 41. Excessive database permissions for the app user
- **Look for:** the app connecting as the database owner or superuser (`postgres`, MongoDB root, MySQL `root`); the same credentials for migrations and runtime; the Supabase `service_role` key used in normal request paths (it bypasses RLS).
- **Good:** a runtime role with only the data permissions it needs; migrations under a separate role.
- **Investigate with:** #7.
- **Usual severity:** LOW to MEDIUM for small apps on a managed database (record it as a conscious decision); HIGH if `service_role` is used for user-facing queries.

### 42. No audit logs
- **Look for:** a record of security-relevant events: logins and failed logins, password and email changes, admin actions, permission changes, payments and refunds, data exports and deletions, API key creation. Who, what, when, from where. A retention limit (#63).
- **Good:** an append-only table or log stream for those events.
- **Usual severity:** scale with what's at stake. MEDIUM when there is money or admin power; LOW for a small app with no accounts.

### 43. No monitoring or alerting
- **Look for:** error tracking (Sentry, Bugsnag, Rollbar, PostHog), uptime checks (UptimeRobot, Better Stack, Checkly), a health endpoint, alerts that reach a human (email, Slack, push), resource alerts (CPU, memory, database connections, disk), **spend alerts on paid APIs** (LLM providers, SMS, cloud). The SDK setup is in code; alert rules live in dashboards, so part of this is an OWNER check.
- **Good:** you hear about an outage before users tell you.
- **Usual severity:** HIGH before launch.

### 44. No backup or restore plan
- **Look for:** database backups (provider automatic backups, point-in-time recovery, a custom dump job), where they are stored (a different account or region?), retention, encryption; user files backed up too. Then the half almost everyone skips: a **tested restore**. Is there a written procedure, and has anyone restored a backup into a fresh database?
- **Good:** automatic backups plus a written restore procedure that has been run at least once.
- **"Backups exist, restore never tested" is still a GAP.**
- **Usual severity:** HIGH before launch.

### 45. Publicly exposed internal dashboards
- **Look for:** internal UIs reachable from the internet: Grafana, Kibana, Prometheus, Bull Board, Flower, Sidekiq Web, Adminer, pgAdmin, phpMyAdmin, Mongo Express, Redis Commander, self-hosted Supabase Studio, Metabase, Airflow, Jupyter, n8n. Check compose files for published `ports:` and reverse-proxy routes.
- **Good:** on a private network, or behind SSO or an IP allowlist.
- **N/A when:** none exist.
- **Usual severity:** CRITICAL if reachable without auth.

### 46. Missing security headers
- **Look for:** where headers are set (helmet, `next.config` `headers()`, nginx or Caddy config, `vercel.json`, Netlify `_headers`, Django `SecurityMiddleware`, Flask-Talisman). Expect `Strict-Transport-Security`, an enforced `Content-Security-Policy` (not report-only; avoid `unsafe-inline` for scripts), `X-Content-Type-Options: nosniff`, `frame-ancestors` or `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`; no `X-Powered-By` or server version banner. Passive live check: `curl -sI https://<site>`.
- **Good:** the full set on HTML and API responses.
- **Usual severity:** MEDIUM (HIGH for a missing CSP when XSS sinks exist).

### 47. Cookies missing HttpOnly, Secure, or SameSite
- **Look for:** every place that sets a cookie. Session and auth cookies need `HttpOnly`, `Secure` and `SameSite=Lax` or `Strict` (`None` only with `Secure` and a reason). Check framework session settings (`SESSION_COOKIE_SECURE`, `cookie: { secure, httpOnly, sameSite }`).
- **Good:** all auth cookies flagged correctly.
- **N/A when:** the app sets no cookies of its own (say so). Third-party analytics or ad cookies belong under #61 and #63.
- **Usual severity:** MEDIUM to HIGH.

### 48. Unencrypted sensitive data
- **Look for:** HTTPS everywhere (HSTS, no mixed content); database connections encrypted when they cross a public network (`sslmode=require`); passwords hashed (bcrypt, argon2, scrypt), not encrypted or MD5/SHA'd; field-level encryption for truly sensitive fields (users' third-party tokens, health, financial or ID data); encrypted backups; mobile secrets stored in Keychain or Keystore, not plain preferences.
- **Good:** protection proportional to how sensitive the data is.
- **Usual severity:** CRITICAL for plain-text passwords; otherwise MEDIUM to HIGH.

### 49. Poor tenant isolation in multi-user apps
- **Look for:** shared structures (orgs, teams, workspaces, rooms) where every query must be scoped by tenant; the tenant ID taken from the session, not the request; cache keys that include the tenant (a shared key leaks data between tenants); background jobs carrying the right tenant; per-tenant file paths; search indexes and vector stores filtered by tenant.
- **Good:** tenant scoping enforced in one central place (RLS, query middleware, a repository layer).
- **N/A when:** single-user app with no shared data.
- **Usual severity:** CRITICAL when one tenant can see another's data.

### 50. Over-trusting generated code without review
- **Look for:** signs of review and testing: a test suite that runs in CI, linting and type checks, tests on auth, payments and data access. Also typical generated-code leftovers in sensitive paths: `// TODO: verify signature`, placeholder or mock auth, `if (process.env.NODE_ENV !== 'production') skipAuth()`, `except: pass` around security logic, duplicated logic that drifted apart, dead code.
- **Good:** critical paths covered by tests plus at least one independent review pass.
- **This item is about process.** Report the concrete signs you found either way.
- **Usual severity:** MEDIUM; HIGH if leftovers sit in security code.

### 51. Load tests
- **Look for:** load-test scripts (k6, Artillery, Locust, JMeter, autocannon), recorded results, a known capacity figure (concurrent users or requests per second before things degrade), and the identified bottleneck (database pool, single worker, WebSocket limits, third-party rate limits).
- **Good:** one realistic test against a production-like environment, with the result written down.
- **If missing:** include a starter test plan in the gap write-up.
- **Usual severity:** MEDIUM before launch; HIGH if a traffic spike is expected (a launch, an influencer post).

### 52. Is session data held on the server? If not, is the app ready for production?
- **Look for:** where session and app state live. Server memory is lost on every restart or deploy and breaks with more than one instance (are there sticky sessions?). Redis or the database survives and scales. Client-side state (JWT, localStorage) means checking #15 and #25. Serverless functions (Vercel, Netlify, Lambda) cannot keep in-memory state between requests at all.
- **Good:** state that must survive restarts lives in a shared store, or the in-memory design and its limits are written down as a conscious choice.
- **Usual severity:** MEDIUM to HIGH, depending on what is lost on a restart.

### 53. Are there file uploads that may require object storage in the future?
- **Look for:** files written to local disk on hosts where disk is temporary (Heroku, Railway, Render or Fly without volumes, serverless: files vanish on redeploy); base64 images stored in database rows; uploads served by the app server itself.
- **Good:** object storage (S3, R2, GCS, Supabase Storage) for anything users create.
- **N/A when:** no uploads and no user-generated files.
- **Usual severity:** HIGH if user files are already being lost; LOW as a future note.

### 54. Is there a queue system for background tasks? Is it necessary?
- **Look for:** slow or failure-prone work done inside the request (sending email, LLM calls, image processing, webhook processing, third-party API calls), which causes timeouts and lost work on a crash; fire-and-forget promises or `asyncio.create_task` with no retry; cron jobs and how they run.
- **Good:** a queue with retries (BullMQ, Celery, RQ, Sidekiq, Inngest, Trigger.dev, Cloud Tasks, SQS) for work that must not be lost, **or** a reasoned "not needed yet". Don't recommend a queue by reflex; name the concrete failure it would prevent.
- **Usual severity:** MEDIUM when important work (payments, emails) can be silently lost; otherwise LOW or OK.

### 55. Adding a support URL?
- **Look for:** a support contact users can actually find: a contact or support page, an email in the footer or in the app, a contact in the privacy policy. App Store and Google Play listings require a support URL. Does the mailbox work? (OWNER: send a test email.)
- **Good:** one reachable support channel linked from the app, the site, the legal pages and the store listings.
- **Usual severity:** MEDIUM before launch (required for store review).

### 56. App title with keywords, subtitle, description?
- **Look for (web):** `<title>`, meta description, Open Graph and Twitter card tags with an image, canonical URL, favicon and apple-touch-icon, web manifest; per-page titles in an SPA (or prerendering).
- **Look for (mobile):** App Store name (30 characters), subtitle (30) and keyword field (100); Google Play title, short description (80) and full description. Keywords people actually search for, and no competitor trademarks. Store metadata usually lives outside the repo (unless `fastlane/metadata` exists), so that part is an OWNER check with concrete suggestions.
- **Good:** keyword-aware title and description on every surface.
- **Usual severity:** LOW to MEDIUM (it costs growth, not security).

### 57. OWASP ZAP and Shannon?
- **Meaning:** dynamic, black-box scanning of the running app: OWASP ZAP (a passive baseline or an active scan) and Shannon (an autonomous AI pentesting tool).
- **Look for:** evidence a dynamic scan was ever done (reports, a ZAP baseline step in CI).
- **Never run an active scan against production** without explicit permission from the owner. Offer the passive baseline against a local or staging instance instead: `docker run -t ghcr.io/zaproxy/zaproxy:stable zap-baseline.py -t <url>`.
- **Good:** at least one passive baseline scan reviewed; an active scan against staging before major launches.
- **Usual verdict:** OWNER, or GAP (LOW) with the command ready to run.

### 58. JSON compression?
- **Look for:** gzip or brotli on API JSON responses and static assets (compression middleware, nginx `gzip_types application/json`, a CDN that does it by default). Passive live check: `curl -sI -H 'Accept-Encoding: gzip, br' <api-url>` and look for `Content-Encoding`. Very large payloads that should be paginated rather than compressed. WebSocket compression (permessage-deflate) is rarely worth it for small messages.
- **Good:** compression on, either from the platform or the server.
- **Usual severity:** LOW.

### 59. Single dependency bottleneck?
- **Look for:** one external service whose failure takes the whole product down (one data vendor or scraper, one LLM provider, one auth provider, one payment provider, one region). Is there a fallback, graceful degradation, timeouts, cached last-good data, a clear outage message? Would switching vendors be a rewrite?
- **Good:** the biggest dependency risks are named with a plan, even if the plan is "accept it", written down.
- **This is a business-risk item:** give an honest opinion and a cheap first step (for example, research one alternative vendor and keep notes on how to swap).
- **Usual severity:** MEDIUM to HIGH, depending on how central the dependency is.

### 60. Non-statically hosted site?
- **Meaning:** is anything served dynamically that could be static? Landing pages, marketing, docs and SPA shells are cheapest and most resilient on a static host or CDN. Server rendering for pages that don't need it costs money and adds an outage surface. The reverse matters too: are static assets actually cached (`Cache-Control: immutable` on hashed files, short cache on HTML)?
- **Good:** static where possible, dynamic only where needed, or a stated reason.
- **Usual verdict:** often OK. A GAP only with a concrete cost, speed or reliability win.

### 61. Is the privacy policy covering every single thing we collect? (Termly or iubenda?)
- **Look for:** build a **data inventory from the code**: form fields; analytics (Google Analytics, PostHog, Mixpanel, Meta Pixel); error tracking (Sentry collects IPs and device data, replays may capture screens); ads SDKs (AdSense, AdMob: cookies and ad IDs); auth, payment and email providers; cookies and localStorage keys; server logs with IPs; third-party embeds (YouTube, TikTok, Maps set their own cookies); mobile permissions (camera, location, contacts, App Tracking Transparency). Then find the privacy policy (in the repo or on the live site) and compare: every collector, purpose, third party, retention period, user rights and contact. List each missing disclosure by name.
- **Good:** every item in the inventory is disclosed. Termly or iubenda are fine starting points; the inventory is what makes the policy accurate.
- **Not legal advice:** recommend a lawyer review for anything material.
- **Usual severity:** HIGH before launch (store review and regulators both check this).

### 62. IP infringement?
- **Look for:** other brands' names, logos or look used in a way that implies affiliation ("for <Platform>", platform logos in the UI or icon); assets without a license (fonts, images, icons, music, sound effects, stock photos); code copied under an incompatible license (GPL inside closed source; run `npx license-checker` or `pip-licenses` if available); AI-generated assets from models with non-commercial terms; third-party content re-hosted instead of embedded.
- **Good:** a list of assets and their licenses; a "not affiliated with X" line wherever a platform name is used; embeds instead of copies.
- **Not legal advice.**
- **Usual severity:** MEDIUM to HIGH.

### 63. Data compliance?
- **Look for:** which laws apply depends on where users are: GDPR (EU and UK), KVKK (Turkey), CCPA/CPRA (California), COPPA (US children under 13), plus app store rules. Check: consent for non-essential cookies and analytics (does the banner actually block scripts before consent?); data minimization; retention limits and deletion jobs; a way to delete an account and its data (the App Store requires in-app account deletion when accounts exist); data export on request; vendor list and cross-border transfers; an age gate if children may use it; a plan for a data breach.
- **Good:** each applicable requirement has a concrete implementation.
- **Not legal advice.** List concrete gaps, not a lecture.
- **Usual severity:** MEDIUM to HIGH.

### 64. Sanitizing every field?
- **Look for:** every user-supplied field validated on the way in (type, length, format, allowlist) and encoded on the way out for its context (HTML, URL, SQL, shell, CSV). Check the less obvious fields: display names, filenames, headers, query params, WebSocket messages, webhook payloads, URL slugs, data imported from third-party APIs, and **CSV exports** (a cell starting with `=`, `+`, `-` or `@` runs as a formula in Excel).
- **Good:** no field reaches storage or output unvalidated.
- **Investigate with:** #16 and #19. Name the specific unsanitized fields you found.
- **Usual severity:** follows the worst sink the field reaches.

### 65. Processing requests from our domain only?
- **Meaning:** the API is meant to serve your own frontend. CORS (#27) stops other websites' browsers, not scripts or bots.
- **Look for:** Origin or Referer checks on sensitive endpoints; CSRF protection (#20); rate limits (#28); bot protection where abuse is costly (Cloudflare Turnstile, reCAPTCHA, hCaptcha on signup or expensive endpoints); Firebase App Check, Play Integrity or App Attest for mobile clients; API keys for server-to-server calls.
- **Be honest:** a public frontend's API can always be called by anyone. The goal is to make abuse expensive, not impossible.
- **Usual severity:** MEDIUM; HIGH when each call costs money.

### 66. Blue-green strategy for instant recovery?
- **Look for:** how deploys happen (auto-deploy on every push to main?); zero-downtime deploys (health checks, rolling or blue-green, readiness probes); what a deploy does to live users (in-memory state lost, WebSockets dropped?); the rollback path (one-click rollback on the host, previous image tags); database migrations that stay backward-compatible so the old version can still run.
- **Good:** a tested way back to the last good version within minutes. Full blue-green may be overkill; recommend the cheapest approach that works (for example, manual deploy approval during peak hours).
- **Usual severity:** MEDIUM.

### 67. Moving all sensitive data to env files
- **Look for:** secrets or environment-specific config still in code (same scan as #1 and #3); env validation at startup that fails fast on missing values (zod, envalid, pydantic-settings); a `.env.example` documenting every variable; production secrets kept in the host's secret store, not a `.env` file baked into the image.
- **Good:** every secret is env-driven, validated at boot and documented.
- **Usual severity:** follows #1 and #3 if secrets are in code; LOW for missing validation or docs.

### 68. Optimistic loading UI?
- **Meaning:** does the UI feel instant? Optimistic updates where safe (likes, toggles, list edits) with rollback on failure; skeletons or spinners on slow actions; no blank screens; buttons disabled against double-submit (a double-submit on "pay" or "create" is also a correctness bug).
- **Look for:** data-fetching patterns (React Query or SWR mutations with `onMutate`, Vue or Svelte equivalents), double-submit protection on create and payment buttons.
- **Good:** instant feedback on every action.
- **Can be SKIP:** when server-authoritative state makes optimism risky (games, payments, anti-cheat). Explain why.
- **Usual severity:** LOW (MEDIUM for missing double-submit protection on payments).

### 69. DMCA for UGC liability?
- **Applies when** users can post content others see (images, videos, text, links).
- **Look for:** a takedown process (a copyright contact, a repeat-infringer policy in the terms); a DMCA designated agent registered with the US Copyright Office (needed for US safe harbor; a small fee, renewed every 3 years); EU Digital Services Act notice-and-action if serving EU users; reporting and moderation tools in the UI.
- **N/A when:** no user-generated content is visible to other users. Check embeds and links before deciding.
- **Not legal advice.**
- **Usual severity:** MEDIUM.

### 70. Subscription compliance
- **Applies when** subscriptions are sold.
- **Look for:** clear price, billing period and auto-renewal terms before purchase; easy cancellation (US FTC rules, EU and Turkish consumer law); App Store and Play rules (digital goods inside mobile apps must use in-app purchase; a restore-purchases button; links to terms and privacy on the paywall); trial-ending reminders where required; receipts; tax and VAT handling (is there a merchant of record?).
- **N/A when:** no subscriptions.
- **Usual severity:** HIGH (store rejection, chargebacks, regulators).

### 71. Connection pooling on database
- **Look for:** how connections are created. A new client per request is common in generated serverless code (`new PrismaClient()` inside a handler, a `pg.Client` per request). Compare pool size times instance count against the database's connection limit (managed databases often allow 20–100). Serverless needs a pooler (PgBouncer, Supabase's pooled port 6543, Neon pooled URL, Prisma Accelerate). Pool timeouts and pre-ping or health checks.
- **Good:** one shared pool per process, sized to the database limit.
- **Usual severity:** MEDIUM; HIGH on serverless with no pooler.

### 72. Tests — k6, Artillery?
- **Look for:** automated tests at every level: unit and integration (jest, vitest, pytest), end-to-end (Playwright, Cypress), load (k6, Artillery; see #51). Do they run in CI and block merges? Do they cover auth, payments and data-access rules, including negative tests (user A cannot read user B's data)?
- **Good:** tests on the critical paths, run on every push.
- **Report:** counts and what is and isn't covered.
- **Usual severity:** MEDIUM; HIGH when there are no tests at all around auth or payments.

### 73. Row-level security?
- **Critical when clients talk to the database directly:** Supabase (anon key plus PostgREST), Hasura, PocketBase; Firebase rules are the equivalent (#7). Check every table has RLS enabled with policies scoped to the user (`auth.uid()`). A table without RLS is readable and writable by anyone holding the anon key. Watch for `using (true)` policies, storage bucket policies, and `security definer` functions or views that bypass RLS. Look in `supabase/migrations/*.sql` and schema dumps; the live state is in the dashboard (OWNER: run Supabase's Security Advisor).
- **When only your backend touches the database with one role,** RLS is defense in depth: usually N/A or LOW. Say which model the app uses.
- **Usual severity:** CRITICAL for a client-reachable table without RLS.

### 74. Terms of use scope?
- **Look for:** terms that exist and cover acceptable use, the license to user content (if any), account termination, disclaimers and limitation of liability, governing law and jurisdiction, dispute resolution, minimum age, payments and refunds (if paid), third-party platform disclaimers, and how changes are announced. Are they linked at signup or purchase? Do they match what the app actually does?
- **Not legal advice.** Flag what's missing.
- **Usual severity:** MEDIUM to HIGH before launch.

### 75. Valuable error messages?
- **Meaning:** the other side of #12. Errors should help the user without leaking internals.
- **Look for:** a generic "Something went wrong" everywhere (users can't fix anything themselves); raw technical errors shown to users; untranslated errors in a translated app; no error codes users can quote to support; no per-field form errors; no offline, timeout or empty states.
- **Good:** stable error codes, human copy, and an ID that support can find in the logs.
- **Usual severity:** LOW to MEDIUM.

### 76. Observability/logging framework
- **Look for:** structured logging (pino, winston, structlog, JSON logs) or scattered `console.log` and `print`; log levels; request or correlation IDs; where logs go and how long they're kept (host log drains); traces and metrics (OpenTelemetry, Sentry performance); slow-query logging; a health endpoint. Test question: could you answer "what happened to this user's request at 14:02?" without redeploying?
- **Good:** you can debug a production issue from logs and traces alone.
- **Usual severity:** MEDIUM.

### 77. Allowlist for folder and file structure?
- **Meaning:** the web server serves only what is meant to be public.
- **Look for:** a static root pointing at the project folder instead of the build output (exposes `.env`, `.git`, source and backups); directory listing (`autoindex on`, `serve-index`, `express.static` serving dotfiles); backup or temp files in public folders (`.bak`, `.sql`, `.zip`, `.DS_Store`); an uploads folder that can execute code. Passive live checks: `/.git/config`, `/.env`, `/.DS_Store`, `/backup.sql` should all 404.
- **Good:** only the build output is served; dotfiles are denied.
- **Usual severity:** CRITICAL if source, `.git` or `.env` is served; LOW for listing alone.

### 78. API test in Burp Suite?
- **Meaning:** a hands-on attack pass on the API: intercept and change requests, swap IDs between two accounts (IDOR), change roles or prices in bodies, replay requests, remove auth headers, fuzz parameters, fire parallel requests to find race conditions (double-redeem, double-spend).
- **You can't drive Burp, but you can write the test plan:** list the endpoints and the exact tampering to try on each, so the owner can run it in an hour.
- **Never test systems the user doesn't own.**
- **Usual verdict:** OWNER with the plan, or GAP (LOW to MEDIUM).

### 79. Automated security scanning in CI
- **Look for:** CI workflows (`.github/workflows`, GitLab CI, and so on) that run a dependency audit (#37), static analysis (Semgrep, CodeQL, Bandit, ESLint security plugins, gosec), secret scanning (gitleaks, trufflehog, GitHub secret scanning and push protection), container scanning (Trivy) if Docker is used; Dependabot or Renovate.
- **Good:** at least a dependency audit, a secret scan and one static analyzer on every push or PR, failing on high severity.
- **Usual severity:** MEDIUM.

### 80. Bing Webmasters?
- **Look for:** a Bing verification tag or file (`msvalidate.01`, `BingSiteAuth.xml`) or DNS verification (not visible from the repo: OWNER); a submitted sitemap; IndexNow. Bing's index feeds ChatGPT search, Copilot and DuckDuckGo, so it matters for AI-assistant discovery too.
- **Good:** site verified, sitemap submitted.
- **N/A when:** the product has no public website.
- **Usual verdict:** OWNER, with the steps.

### 81. Google SEO and GEO for searches and agentic finds?
- **Look for (SEO):** leftover `noindex` (meta tag or `X-Robots-Tag` header); `robots.txt` still saying `Disallow: /` from a beta (very common); `sitemap.xml` with real URLs; canonical URLs pointing at the production domain; content pages rendered on the server or prerendered (an SPA that renders everything in the browser indexes poorly); unique titles and descriptions per page (#56); structured data (JSON-LD: Organization, SoftwareApplication, FAQPage); page speed; Google Search Console verification (OWNER).
- **Look for (GEO, generative engine optimization):** clear, factual, crawlable copy that says what the product is and who it's for; FAQ content; `robots.txt` choices about AI crawlers (GPTBot, ClaudeBot, PerplexityBot, Google-Extended) made on purpose either way; optional `llms.txt`.
- **N/A when:** no public website.
- **Usual severity:** HIGH if the production site is accidentally noindexed; otherwise LOW to MEDIUM.

### 82. IP ban feature for cyber attacks?
- **Look for:** a way to block abusive IPs, ranges or countries quickly: a CDN or WAF in front (Cloudflare's free tier gives IP, ASN and country rules, DDoS absorption and bot protection), an app-level blocklist checked in middleware (Redis or database), fail2ban on self-managed servers; the correct client IP behind proxies (trusted-proxy config, `CF-Connecting-IP`); bans that apply without a redeploy. Account-level bans if there are accounts.
- **Good:** a documented way to ban an IP within minutes.
- **Usual severity:** MEDIUM.

### 83. Trademarking the brand?
- **Owner decision; give an opinion.** Check for name conflicts: clearance searches in the relevant registries (USPTO, EUIPO or TMview, WIPO Global Brand Database, the national office such as TÜRKPATENT) in the classes that matter (software 9 and 42, entertainment 41); domain and social handles secured; conflicts with existing app store names.
- **Typical advice:** do the clearance search before spending money on marketing the name; file when traction makes a dispute costly.
- **Not legal advice.**
- **Usual verdict:** OWNER, or GAP (LOW to MEDIUM) if a conflicting mark turns up.

### 84. Provisional patent?
- **Owner decision; give an honest opinion.** Software and game mechanics often fail as abstract ideas (Alice in the US) or against prior art. A provisional only buys 12 months of priority for claims that must later be filed properly, and it does nothing against a clone written differently. For most indie and vibe-coded apps this is a SKIP unless there is a genuinely new technical method; the money is usually better spent on a trademark (#83).
- **Not legal advice.**
- **Usual verdict:** SKIP, with the reasoning.
