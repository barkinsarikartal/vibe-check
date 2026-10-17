#!/usr/bin/env python3
"""Build a test-fixture repo for the vibe-check evals.

Copies evals/fixtures/<name>/files to <dest>, fills __FAKE_*__ placeholders
with freshly generated fake keys (so this repo never contains secret-shaped
strings that GitHub push protection would block), and creates git history:
commit 1 = files + history-commit1 overlay (e.g. a committed .env),
commit 2 = the final state.

Usage: python3 build_fixture.py <name> <dest>
Prints the generated fake values as JSON so graders can check none leaked.
"""

import base64
import json
import os
import random
import shutil
import string
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def rand(n, alphabet=string.ascii_letters + string.digits):
    return "".join(random.choice(alphabet) for _ in range(n))


def b64(obj):
    return base64.urlsafe_b64encode(json.dumps(obj, separators=(",", ":")).encode()).decode().rstrip("=")


def fake_jwt(role):
    header = b64({"alg": "HS256", "typ": "JWT"})
    payload = b64({"iss": "supabase", "ref": "qwhzkpdmvtrsylxa", "role": role, "iat": 1698796800, "exp": 2014372800})
    return f"{header}.{payload}.{rand(43, string.ascii_letters + string.digits + '-_')}"


def fakes():
    return {
        "__FAKE_STRIPE_LIVE__": "sk_" + "live_" + rand(24),
        "__FAKE_STRIPE_PK__": "pk_" + "live_" + rand(24),
        "__FAKE_OPENAI__": "sk-" + "proj-" + rand(48, string.ascii_letters + string.digits + "-_"),
        "__FAKE_SENDGRID__": "SG." + rand(22) + "." + rand(43),
        "__FAKE_ANON_JWT__": fake_jwt("anon"),
        "__FAKE_SERVICE_ROLE_JWT__": fake_jwt("service_role"),
    }


def fill(root, values):
    for dirpath, _, filenames in os.walk(root):
        if ".git" in dirpath.split(os.sep):
            continue
        for name in filenames:
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            new = text
            for k, v in values.items():
                new = new.replace(k, v)
            if new != text:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(new)


def git(dest, *args, date=None):
    env = dict(os.environ, GIT_AUTHOR_NAME="Dev", GIT_AUTHOR_EMAIL="dev@example.com",
               GIT_COMMITTER_NAME="Dev", GIT_COMMITTER_EMAIL="dev@example.com")
    if date:
        env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    subprocess.run(["git", *args], cwd=dest, env=env, check=True, capture_output=True)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    name, dest = sys.argv[1], os.path.abspath(sys.argv[2])
    src = os.path.join(HERE, "fixtures", name)
    if os.path.exists(dest):
        sys.exit(f"{dest} already exists")
    values = fakes()

    overlay = os.path.join(src, "history-commit1")
    has_overlay = os.path.isdir(overlay) and os.listdir(overlay)

    shutil.copytree(os.path.join(src, "files"), dest)
    git(dest, "init", "-q", "-b", "main")
    if has_overlay:
        shutil.copytree(overlay, dest, dirs_exist_ok=True)
        fill(dest, values)
        git(dest, "add", "-A")
        git(dest, "commit", "-q", "-m", "initial commit", date="2023-11-01T10:00:00")
        for dirpath, _, filenames in os.walk(overlay):
            for f in filenames:
                rel = os.path.relpath(os.path.join(dirpath, f), overlay)
                final = os.path.join(src, "files", rel)
                target = os.path.join(dest, rel)
                if os.path.exists(final):
                    shutil.copy2(final, target)
                else:
                    os.remove(target)
    fill(dest, values)
    git(dest, "add", "-A")
    git(dest, "commit", "-q", "-m", "payments, ai receipts, cleanup" if has_overlay else "initial commit",
        date="2023-11-20T18:30:00")
    print(json.dumps(values))


if __name__ == "__main__":
    main()
