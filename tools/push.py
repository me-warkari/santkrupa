#!/usr/bin/env python3
"""Push santkrupa local tree to GitHub via the Contents API.

Uploads content/, site/ and tools/ (excluding __pycache__), skipping files
whose blob SHA already matches the repo. One commit per changed file.

The token is read ONLY from the GITHUB_TOKEN environment variable and is
never written to disk, logs, or the repo. Run as:
  GITHUB_TOKEN=<token> python3 tools/push.py

Token: a fine-grained PAT scoped to me-warkari/santkrupa only,
Contents Read and write, Metadata read-only.
"""

import base64
import hashlib
import json
import os
import sys
import urllib.request
import urllib.error

REPO = "me-warkari/santkrupa"
BRANCH = "main"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIRS = ["content", "site", "tools"]


def blob_sha(data: bytes) -> str:
    h = hashlib.sha1()
    h.update(b"blob %d\x00" % len(data))
    h.update(data)
    return h.hexdigest()


def api(path, method="GET", body=None):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("error: GITHUB_TOKEN is not set", file=sys.stderr)
        sys.exit(2)
    url = "https://api.github.com" + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "santkrupa-push")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        payload = e.read().decode("utf-8", "replace")
        return e.code, json.loads(payload) if payload else {}


def collect():
    files = []
    for d in DIRS:
        for base, _, names in os.walk(os.path.join(ROOT, d)):
            if "__pycache__" in base:
                continue
            for name in sorted(names):
                full = os.path.join(base, name)
                rel = os.path.relpath(full, ROOT)
                files.append(rel)
    return files


def main():
    message = sys.argv[1] if len(sys.argv) > 1 else "Sync site and content"
    changed, skipped = [], []
    for rel in collect():
        with open(os.path.join(ROOT, rel), "rb") as f:
            data = f.read()
        status, existing = api(f"/repos/{REPO}/contents/{rel}?ref={BRANCH}")
        if status == 200 and existing.get("sha") == blob_sha(data):
            skipped.append(rel)
            continue
        body = {
            "message": message,
            "content": base64.b64encode(data).decode("ascii"),
            "branch": BRANCH,
        }
        if status == 200 and existing.get("sha"):
            body["sha"] = existing["sha"]
        status, result = api(f"/repos/{REPO}/contents/{rel}", "PUT", body)
        if status in (200, 201):
            changed.append((rel, result["commit"]["sha"][:7]))
            print(f"{'updated' if status == 200 else 'created'} {rel} ({result['commit']['sha'][:7]})")
        else:
            print(f"FAILED {rel}: HTTP {status} {result}", file=sys.stderr)
            sys.exit(1)
    print(f"\nchanged: {len(changed)}, unchanged: {len(skipped)}")


if __name__ == "__main__":
    main()
