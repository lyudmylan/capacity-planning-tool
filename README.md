# Capacity Planning Tool

Capacity Planning Tool is a JSON-in / JSON-out planning CLI. The current version evaluates whether a roadmap fits within engineering capacity, supports explicit business goals, and uses a bounded replanning loop to recommend a better plan when the original scope does not fit.

## Status

- `V1.1` adds a bounded agentic replanning loop on top of the deterministic planner.
- Capacity, demand, feasibility, and candidate scoring calculations remain non-LLM.
- `business_goals` can now guide must-deliver protection, priority preservation, utilization limits, and buffer targets.
- The original product brief is preserved in [`docs/product_spec.md`](docs/product_spec.md).
- The agentic architecture and remaining future work are documented in [`docs/agentic_replanning_plan.md`](docs/agentic_replanning_plan.md).

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
ruff check .
mypy src
```

## Documentation

- [`docs/product_spec.md`](docs/product_spec.md)
  Original requested product specification, now preserved in version control.
- [`docs/assumptions.md`](docs/assumptions.md)
  Current formulas, assumptions, and behavior notes.
- [`docs/agentic_replanning_plan.md`](docs/agentic_replanning_plan.md)
  The implemented agentic replanning design plus remaining gaps and next steps.
- [`docs/shipping_workflow.md`](docs/shipping_workflow.md)
  Standard implementation, review, GitHub push, and CI flow.
- [`AGENTS.md`](AGENTS.md)
  Repository instructions for coding agents.

## Project Rules

- Runtime defaults live in `config/defaults.json`.
- Logging defaults and replanning policy defaults also live in `config/defaults.json`.
- Machine-readable inputs and outputs stay in JSON.
- Formulas and planning assumptions live in Markdown docs.
- Example JSON inputs live in `examples/`.
