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
- `src/capacity_planning_tool/server.py`
  Minimal Flask server that bridges the UI to the existing planner.
- `ui/index.html`
  Single-page web UI driven by the JSON handoff contract.
- `tests/`
  Covers planning calculations, defaults, prioritization, CLI behavior, and web API.
- `docs/assumptions.md`
  Documents formulas, assumptions, and recommendation rules.
- `docs/current_state.md`
  Tracks the current shipped product shape, known gaps, and next-step direction.
- `docs/product_spec.md`
  Preserves the original requested product brief as a historical reference.
- `docs/agentic_replanning_plan.md`
  Tracks the optional future LLM-advisor direction beyond the shipped planner.
- `docs/ui_json_spec.md`
  Defines the JSON-first UI handoff model for future human and agent-facing interfaces.
- `docs/shipping_workflow.md`
  Short human-readable pointer to the canonical shipping workflow in this file.
- `specs/ui_handoff_v1.json`
  Machine-readable UI source-of-truth for agent handoff and future web implementation.
- `examples/`
  Provides sample JSON inputs for quick validation.

## Coding Conventions

- Keep all machine-readable inputs and outputs in JSON.
- Keep runtime defaults and domain numeric constants in `config/defaults.json`.
- Keep UI/product surface contracts that need to be read by agents in JSON spec files under `specs/`.
- Keep formulas, assumptions, and product reasoning in Markdown docs rather than inline comments.
- Prefer pure functions for calculations.
- Keep business-goal evaluation deterministic even when agentic behavior is added.
- Use dataclasses and explicit type hints.
- Validate input early and fail with actionable error messages.
- Preserve feature order in delivered output unless recommendation logic removes items.
- Avoid hardcoding change-prone policy in code.
  Put defaults, thresholds, scoring order, log defaults, and machine-readable UI contracts in JSON files.
- Use hardcoded literals in Python only for stable control flow, small fixed enums, and code structure.

## Error Handling and Logging

- Handle expected failures with clean user-facing errors rather than raw Python tracebacks.
- Treat invalid input, unreadable config, and output write failures as first-class CLI error cases.
- Keep machine-readable JSON on stdout.
- Send runtime logging to stderr through Python's `logging` module.
- Keep logging configurable and quiet by default for CLI usage.
- Log major planner decisions and stop conditions at appropriate levels so troubleshooting does not require stepping through code.
- Do not silently swallow exceptions just to keep the CLI running.

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
- For meaningful code changes, prefer using one sub-agent for an independent external-style review pass.
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

- Preserve the original product brief in `docs/product_spec.md` as a historical reference.
- Do not use `docs/product_spec.md` for current status tracking or roadmap notes.
- Keep current shipped status and next-step notes in `docs/current_state.md`.
- If current behavior differs from the original brief, document that gap explicitly rather than hiding it.
- Keep forward-looking design work in dedicated docs such as `docs/agentic_replanning_plan.md`.
- Update or add JSON examples when input or output shapes change.
- Add or update tests with every feature or bug fix.
- Add or update tests for every schema change, planner behavior change, logging behavior change, and agentic loop change.
- Review the business-goal and replanning rules after planner changes.
- Keep runtime defaults and iteration limits in JSON config.
- Keep stdout JSON-compatible for automation use.
- Keep the planner core intentionally simple:
  - no database
  - no external integrations
  - no weekly or sprint-level scheduling allocation
- If a UI is added, keep it thin and driven by the JSON handoff spec instead of embedding planner logic in the frontend.

## UI Handoff Rules

- The next UI phase should be driven by a JSON-first spec that can be consumed by agents and also rendered by a human-facing web interface.
- Treat `specs/ui_handoff_v1.json` as the machine-readable source of truth for UI scope and behavior.
- Treat `docs/ui_json_spec.md` as the human-readable explanation of that contract.
- If a UI is built, update the JSON spec first, then the implementation, then the docs and tests.
- Keep the planner as the source of truth for calculations and output JSON.
- UI work may be delegated to Claude Code when the handoff contract is explicit and versioned.
- Keep UI logic from duplicating planner calculations in the frontend.

## Extension Notes

- If future versions add more sizing levels or ranking logic, update both `config/defaults.json` and `docs/assumptions.md`.
- If the output schema changes, update CLI tests and example files in the same change.
