# AGENTS.md

## Purpose

This project provides a JSON-in / JSON-out CLI for capacity planning. It evaluates whether a roadmap fits within available engineering capacity for a planning horizon and uses a bounded agentic replanning loop to recommend a better alternative when it does not.

## Architecture

- `src/capacity_planning_tool/models.py`
  Defines validated input, output, and config dataclasses.
- `src/capacity_planning_tool/config.py`
  Loads runtime defaults from `config/defaults.json`.
- `src/capacity_planning_tool/planner.py`
  Contains deterministic planning calculations, business-goal evaluation, and the bounded agentic replanning loop.
- `src/capacity_planning_tool/cli.py`
  Reads input JSON, runs the planner, and writes output JSON.
- `tests/`
  Covers planning calculations, defaults, prioritization, and CLI behavior.
- `docs/assumptions.md`
  Documents formulas, assumptions, and recommendation rules.
- `docs/product_spec.md`
  Preserves the original requested product spec and notes the current V1 gap.
- `docs/agentic_replanning_plan.md`
  Defines the planned bounded agentic replanning architecture for the next iteration.
- `docs/shipping_workflow.md`
  Defines the GitHub shipping standard for routine changes.
- `examples/`
  Provides sample JSON inputs for quick validation.

## Coding Conventions

- Keep all machine-readable inputs and outputs in JSON.
- Keep runtime defaults and domain numeric constants in `config/defaults.json`.
- Keep formulas, assumptions, and product reasoning in Markdown docs rather than inline comments.
- Prefer pure functions for calculations.
- Keep business-goal evaluation deterministic even when agentic behavior is added.
- Use dataclasses and explicit type hints.
- Validate input early and fail with actionable error messages.
- Preserve feature order in delivered output unless recommendation logic removes items.

## Shipping Workflow

Use this sequence for routine code changes unless the task explicitly calls for a different process.

### Default Sequence

1. Implement the requested change locally.
2. Run the full local test suite:
   `python3 -m unittest discover -s tests -v`
3. Do an independent code review pass focused on bugs, regressions, and missing tests.
4. Fix anything found in testing or review.
5. Re-run the full local test suite.
6. Commit the changes with a clear, scoped message.
7. Push the branch to GitHub.
8. Check remote CI and confirm it passes before considering the work done.

### Delegation Guidance

- Keep test execution, fixes, commit, push, and CI checks in the main thread.
- If parallel help is useful, use one sub-agent for an independent review pass.
- Do not split each step into a separate sub-agent unless the work is unusually large or the write scopes are cleanly separated.

### Merge Standard

Do not push as complete if:

- local tests are failing
- review findings are unresolved
- the output schema changed without updating tests or docs
- CI has not been checked after push

## Local Verification

- `make check`
- `make test`
- `python3 -m unittest discover -s tests -v`
- `ruff check .`
- `mypy src`

## Product Rules

- Keep the original product brief updated in `docs/product_spec.md`.
- If current behavior differs from the original brief, document that gap explicitly rather than hiding it.
- Keep forward-looking design work in dedicated docs such as `docs/agentic_replanning_plan.md`.
- Update or add JSON examples when input or output shapes change.
- Add or update tests with every feature or bug fix.
- Review the business-goal and replanning rules after planner changes.
- Keep runtime defaults and iteration limits in JSON config.
- Keep the product intentionally simple:
  - no UI
  - no database
  - no external integrations
  - no weekly or sprint-level scheduling allocation

## Extension Notes

- If future versions add more sizing levels or ranking logic, update both `config/defaults.json` and `docs/assumptions.md`.
- If the output schema changes, update CLI tests and example files in the same change.
