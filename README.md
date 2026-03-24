# Capacity Planning Tool

Capacity Planning Tool is a JSON-in / JSON-out planning CLI. The current shipped version evaluates whether a roadmap fits within engineering capacity for a single planning horizon and recommends a trimmed plan when it does not.

## Status

- `V1.0` is shipped and deterministic.
- Capacity, demand, feasibility, and scope-reduction calculations are non-LLM.
- The original product brief has now been captured in the repo at [`docs/product_spec.md`](docs/product_spec.md).
- A stronger agentic runtime design is planned next and documented in [`docs/agentic_replanning_plan.md`](docs/agentic_replanning_plan.md).

## Quick Start

```bash
PYTHONPATH=src python3 -m capacity_planning_tool --input examples/feasible_plan.json
```

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
  Current formulas, assumptions, and V1 behavior notes.
- [`docs/agentic_replanning_plan.md`](docs/agentic_replanning_plan.md)
  Planned next iteration for bounded agentic replanning driven by business goals.
- [`docs/shipping_workflow.md`](docs/shipping_workflow.md)
  Standard implementation, review, GitHub push, and CI flow.
- [`AGENTS.md`](AGENTS.md)
  Repository instructions for coding agents.

## Project Rules

- Runtime defaults live in `config/defaults.json`.
- Machine-readable inputs and outputs stay in JSON.
- Formulas and planning assumptions live in Markdown docs.
- Example JSON inputs live in `examples/`.
