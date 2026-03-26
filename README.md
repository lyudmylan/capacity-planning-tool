# Capacity Planning Tool

Capacity Planning Tool is a JSON-in / JSON-out planning CLI. The current version evaluates whether a roadmap fits within engineering capacity, supports explicit business goals, and uses a bounded replanning loop to recommend a better plan when the original scope does not fit.

The living product overview now lives in [`docs/product.md`](docs/product.md). Use that file as the source of truth for current scope, constraints, and next steps.

## Web UI

The project includes a thin web interface for interactive planning. It wraps the existing planner with no duplicated logic.

```bash
# Start the UI server
PYTHONPATH=src python3 -m capacity_planning_tool.server
# or: make serve

# Open http://127.0.0.1:8000 in your browser
```

The UI lets you:
- Paste, upload, or drag-drop planning input JSON
- Edit key planning fields in a structured form
- Run the planner and inspect results (feasibility, utilization, scope decisions, business goals)
- Compare the original roadmap against the selected plan to see how demand, utilization, buffer, and scope changed
- Copy or download raw output JSON

### Architecture

- **Backend**: A minimal Flask server (`server.py`) with two API endpoints: `POST /api/plan` (runs the planner) and `GET /api/examples` (loads example inputs). All calculations stay in the Python planner.
- **Frontend**: A single `ui/index.html` file with embedded CSS and vanilla JavaScript. No build step, no npm, no framework dependencies.
- **Dependency**: Flask is the only new runtime dependency.

## Quick Start

```bash
PYTHONPATH=src python3 -m capacity_planning_tool --input examples/feasible_plan.json
PYTHONPATH=src python3 -m capacity_planning_tool --input examples/goal_driven_plan.json
PYTHONPATH=src python3 -m capacity_planning_tool --input examples/infeasible_plan.json --log-level INFO
```

Normal CLI runs default to warning-level logging so stdout stays clean JSON. Use `--log-level INFO` when you want runtime trace output, or `--quiet` to suppress everything except errors.

Additional v2 schema examples live in `examples/v2_rd_org_capacity_check.json` and
`examples/v2_rd_org_planning_schedule.json`. They are useful for contract and validation work while
the planner is still transitioning from the legacy input shape.

## Shortcuts

```bash
make test
make check
make run-feasible
make run-infeasible
```

## Development

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
node --test tests/ui_logic.test.mjs
ruff check .
mypy src
```

## Documentation

- [`docs/product.md`](docs/product.md)
  Living product overview: goal, current shape, constraints, and next steps.
- [`docs/assumptions.md`](docs/assumptions.md)
  Current formulas, assumptions, and behavior notes.
- [`docs/ui_json_spec.md`](docs/ui_json_spec.md)
  The human-readable guide for the future JSON-first UI contract.
- [`.codex/skills/github-shipping/SKILL.md`](.codex/skills/github-shipping/SKILL.md)
  Shared shipping workflow skill for collaborators using Codex-style tooling.
- [`.codex/prompts/`](.codex/prompts)
  Shared prompt shortcuts for shipping, review, and Claude UI delegation.
- [`AGENTS.md`](AGENTS.md)
  Minimal repository instructions for agents working in this codebase.
- [`specs/ui_handoff_v1.json`](specs/ui_handoff_v1.json)
  Machine-readable UI handoff spec for agent-built and human-facing interfaces.

## Project Rules

- Runtime defaults live in `config/defaults.json`.
- Logging defaults and replanning policy defaults also live in `config/defaults.json`.
- Machine-readable inputs and outputs stay in JSON.
- Formulas and planning assumptions live in Markdown docs.
- Example JSON inputs live in `examples/`.
