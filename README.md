# Capacity Planning Tool

Capacity Planning Tool is a JSON-in / JSON-out planning CLI. The current version evaluates whether a roadmap fits within engineering capacity, supports explicit business goals, and uses a bounded replanning loop to recommend a better plan when the original scope does not fit.

## Current Shape

- Deterministic capacity planning CLI with JSON input and output
- Bounded replanning loop with explicit business goals
- Thin web UI on top of the existing planner
- JSON-first UI contract for future agent or human-facing interfaces
- Optional future LLM work documented separately from the shipped planner

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

- [`docs/current_state.md`](docs/current_state.md)
  Current shipped capabilities, known gaps, and next-step direction.
- [`docs/product_spec.md`](docs/product_spec.md)
  Historical original product brief that started the project.
- [`docs/assumptions.md`](docs/assumptions.md)
  Current formulas, assumptions, and behavior notes.
- [`docs/agentic_replanning_plan.md`](docs/agentic_replanning_plan.md)
  Future optional LLM-advisor direction, separate from the shipped deterministic planner.
- [`docs/ui_json_spec.md`](docs/ui_json_spec.md)
  The human-readable guide for the future JSON-first UI contract.
- [`docs/shipping_workflow.md`](docs/shipping_workflow.md)
  Short pointer to the canonical shipping process in `AGENTS.md`.
- [`AGENTS.md`](AGENTS.md)
  Repository instructions for coding agents.
- [`specs/ui_handoff_v1.json`](specs/ui_handoff_v1.json)
  Machine-readable UI handoff spec for agent-built and human-facing interfaces.

## Project Rules

- Runtime defaults live in `config/defaults.json`.
- Logging defaults and replanning policy defaults also live in `config/defaults.json`.
- Machine-readable inputs and outputs stay in JSON.
- Formulas and planning assumptions live in Markdown docs.
- Example JSON inputs live in `examples/`.
