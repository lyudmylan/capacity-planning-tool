#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: scripts/pr_ready_check.sh <pr-number> [owner/repo]" >&2
  exit 2
fi

PR_NUMBER="$1"
REPO="${2:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}"

PR_JSON="$(gh pr view -R "$REPO" "$PR_NUMBER" --json state,mergeStateStatus,reviews,comments,statusCheckRollup,labels,url)"
INLINE_JSON="$(gh api "repos/$REPO/pulls/$PR_NUMBER/comments")"

python3 - "$PR_NUMBER" "$PR_JSON" "$INLINE_JSON" <<'PY'
import json
import sys

pr_number = sys.argv[1]
pr = json.loads(sys.argv[2])
inline_comments = json.loads(sys.argv[3])

labels = [label["name"] for label in pr.get("labels", [])]
reviewers = [review.get("author", {}).get("login", "") for review in pr.get("reviews", [])]
codex_review_present = any(
    login in {"chatgpt-codex-connector", "chatgpt-codex-connector[bot]"}
    for login in reviewers
)
override_present = "codex-review-skipped" in labels

check_rollup = pr.get("statusCheckRollup", [])
blocking_checks = []
pending_checks = []
for check in check_rollup:
    status = check.get("status")
    conclusion = check.get("conclusion")
    name = check.get("name", "unknown")
    if status != "COMPLETED":
      pending_checks.append(name)
    elif conclusion != "SUCCESS":
      blocking_checks.append(f"{name} ({conclusion})")

print(f"PR #{pr_number}: {pr.get('url')}")
print(f"State: {pr.get('state')}  Merge status: {pr.get('mergeStateStatus')}")
print(f"Checks: {len(check_rollup)} total")
print(f"Top-level reviews: {len(pr.get('reviews', []))}")
print(f"Top-level comments: {len(pr.get('comments', []))}")
print(f"Inline review comments: {len(inline_comments)}")
print(f"Codex review present: {'yes' if codex_review_present else 'no'}")
print(f"Override label present: {'yes' if override_present else 'no'}")

if blocking_checks:
    print("Blocking checks:")
    for check in blocking_checks:
        print(f"- {check}")

if pending_checks:
    print("Pending checks:")
    for check in pending_checks:
        print(f"- {check}")

if inline_comments:
    print("Inline comment URLs:")
    for comment in inline_comments:
        print(f"- {comment.get('html_url')}")

blocking = False

if pr.get("state") != "OPEN":
    print("Not merge-ready: PR is not open.")
    blocking = True

if blocking_checks or pending_checks:
    print("Not merge-ready: checks are not all green yet.")
    blocking = True

if inline_comments:
    print("Not merge-ready: unresolved inline review comments are present.")
    blocking = True

if not codex_review_present and not override_present:
    print("Not merge-ready: Codex review has not been received and no override label is present.")
    blocking = True

sys.exit(1 if blocking else 0)
PY
