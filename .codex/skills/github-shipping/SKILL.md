---
name: "github-shipping"
description: "Use when the user wants to finish, ship, push, merge, or complete a routine code change with the normal GitHub workflow. It applies the repo's shared shipping workflow and honors any stricter repo-specific AGENTS.md rules."
---

# GitHub Shipping

## When to use

- The user asks to ship, push, merge, finish, or complete a routine change.
- The work is already implemented and needs the standard GitHub delivery flow.
- The repo does not explicitly require a different release process.

## How to use this skill

1. Read the repo's `AGENTS.md` first.
2. Apply the repo's shared shipping workflow.
3. If the repo defines stricter or different rules, follow the repo-specific override.

## What this skill adds

Use this skill as the trigger for shipping mode, especially when the user did not restate the whole workflow.

Default review focus:

- behavioral regressions
- missing or weak tests
- broken contracts or schema drift
- error handling gaps
- logging or observability regressions
- hidden hardcoding of change-prone policy
