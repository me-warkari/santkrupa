#!/usr/bin/env python3
"""Push santkrupa local tree to GitHub via the Contents API.

Uploads content/ and tools/ as-is, and the built site/ files to the repo
ROOT (GitHub Pages serves from the branch root, so site/index.html is
pushed as index.html, site/granth/... as granth/..., and so on).
Skips files whose blob SHA already matches the repo. One commit per
changed file.

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
    """Return (local_path, repo_path) pairs.

    content/ and tools/ keep their paths. site/ files map to the repo
    root because GitHub Pages serves from the branch root.
    """
    pairs = []
    for d in DIRS:
        for base, _, names in os.walk(os.path.join(ROOT, d)):
            if "__pycache__" in base:
                continue
            for name in sorted(names):
                full = os.path.join(base, name)
                rel = os.path.relpath(full, ROOT)
                if rel == "site/build.py":
                    # tools/build.py is the canonical script; the copy in
                    # site/ exists only so the built site is self-contained.
                    continue
                repo_path = rel[5:] if rel.startswith("site/") else rel
                pairs.append((full, repo_path))
    return pairs


def delete_path(repo_path, sha):
    status, result = api(
        f"/repos/{REPO}/contents/{repo_path}",
        "DELETE",
        {"message": "Remove duplicate site/ tree (site is served from root)",
         "sha": sha, "branch": BRANCH},
    )
    if status != 200:
        print(f"FAILED delete {repo_path}: HTTP {status} {result}", file=sys.stderr)
        sys.exit(1)
    print(f"deleted {repo_path}")


def cleanup_site_tree():
    """Delete every repo path under site/ (created by mistake in an
    earlier push; the site is served from the root)."""
    status, tree = api(f"/repos/{REPO}/git/trees/{BRANCH}?recursive=1")
    if status != 200:
        print(f"FAILED list tree: HTTP {status} {tree}", file=sys.stderr)
        sys.exit(1)
    doomed = [(t["path"], t["sha"]) for t in tree["tree"]
              if t["type"] == "blob" and t["path"].startswith("site/")]
    for path, sha in doomed:
        delete_path(path, sha)
    print(f"\ndeleted: {len(doomed)}")


def main():
    if "--cleanup-site" in sys.argv:
        cleanup_site_tree()
        return
    message = sys.argv[1] if len(sys.argv) > 1 else "Sync site and content"
    changed, skipped = [], []
    for full, repo_path in collect():
        with open(full, "rb") as f:
            data = f.read()
        status, existing = api(f"/repos/{REPO}/contents/{repo_path}?ref={BRANCH}")
        if status == 200 and existing.get("sha") == blob_sha(data):
            skipped.append(repo_path)
            continue
        body = {
            "message": message,
            "content": base64.b64encode(data).decode("ascii"),
            "branch": BRANCH,
        }
        if status == 200 and existing.get("sha"):
            body["sha"] = existing["sha"]
        status, result = api(f"/repos/{REPO}/contents/{repo_path}", "PUT", body)
        if status in (200, 201):
            changed.append((repo_path, result["commit"]["sha"][:7]))
            print(f"{'updated' if status == 200 else 'created'} {repo_path} ({result['commit']['sha'][:7]})")
        else:
            print(f"FAILED {repo_path}: HTTP {status} {result}", file=sys.stderr)
            sys.exit(1)
    print(f"\nchanged: {len(changed)}, unchanged: {len(skipped)}")


if __name__ == "__main__":
    main()
