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
- `.codex/skills/github-shipping/SKILL.md`
  Shared repo shipping workflow skill that can be reused by collaborators.
- `.codex/prompts/`
  Shared prompt shortcuts for shipping, review, and Claude UI delegation.
- `docs/product.md`
  Living product overview, current scope, and next-step direction.
- `docs/assumptions.md`
  Documents formulas, assumptions, and recommendation rules.
- `docs/ui_json_spec.md`
  Defines the JSON-first UI handoff model for future human and agent-facing interfaces.
- `specs/ui_handoff_v1.json`
  Machine-readable UI source-of-truth for agent handoff and future web implementation.
- `examples/`
  Provides sample JSON inputs for quick validation.

## Repo Rules

- Keep all machine-readable inputs and outputs in JSON.
- Keep runtime defaults and domain numeric constants in `config/defaults.json`.
- Keep UI/product surface contracts that need to be read by agents in JSON spec files under `specs/`.
- Keep reusable Codex workflow assets in `.codex/` so they can be versioned in Git.
- Keep formulas, assumptions, and product reasoning in Markdown docs rather than inline comments.
- Prefer pure functions for calculations.
- Keep business-goal evaluation deterministic even when agentic behavior is added.
- Preserve feature order in delivered output unless recommendation logic removes items.
- Keep change-prone policy in JSON config or JSON specs rather than burying it in Python.

## Product Rules

- Keep the living product overview in `docs/product.md`.
- Update or add JSON examples when input or output shapes change.
- Keep runtime defaults and iteration limits in JSON config.
- Keep stdout JSON-compatible for automation use.
- Keep the planner core intentionally simple:
  - no database
  - no external integrations
  - no weekly or sprint-level scheduling allocation
- If a UI is added, keep it thin and driven by the JSON handoff spec instead of embedding planner logic in the frontend.

## UI Handoff

- For UI work, follow `specs/ui_handoff_v1.json` and `docs/ui_json_spec.md`.
- Keep the planner as the source of truth for calculations and output JSON.

## Extension Notes

- If future versions add more sizing levels or ranking logic, update both `config/defaults.json` and `docs/assumptions.md`.
- If the output schema changes, update CLI tests and example files in the same change.
