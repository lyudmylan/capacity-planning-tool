---
name: "ui-handoff"
description: "Use when the user wants to implement or update this repo's UI using the planner as the source of truth and the repo's JSON UI spec as the implementation contract."
---

# UI Handoff

## When to use

- The user wants to implement or update the UI for this repo.
- The task depends on the repo's machine-readable UI spec and planner output contract.
- The work should keep the frontend thin and avoid duplicating planner logic.

## How to use this skill

1. Read these first:
   - `AGENTS.md`
   - `docs/product.md`
   - `docs/ui_json_spec.md`
   - `specs/ui_handoff_v1.json`
   - `docs/assumptions.md`
2. Use relevant JSON examples from `examples/` for the target mode or contract path.
3. Keep the planner as the source of truth for calculations and output JSON.
4. Do not move calculations into the frontend.
5. If UI behavior or scope changes, update `specs/ui_handoff_v1.json` first, then implementation, then docs and tests.
6. Keep the UI thin, clean, decision-oriented, and transparent about raw JSON.

## Delivery expectations

- Implement the requested UI change end to end.
- Add or update tests.
- Update docs if UI behavior or setup changes.
- Run the relevant verification for the repo.
- Summarize what changed, assumptions made, and how to validate the UI locally.

## Boundaries

- Use `github-planning` for GitHub issue and milestone setup.
- Use this skill for actual UI/spec-driven implementation work.
