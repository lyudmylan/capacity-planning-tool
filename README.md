# Capacity Planning Tool

Capacity Planning Tool V1.0 is a JSON-in / JSON-out CLI that compares roadmap demand with engineering capacity and recommends a trimmed plan when the original roadmap does not fit.

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
PYTHONPATH=src python3 -m unittest discover -s tests
ruff check .
mypy src
```

## Project Rules

- Runtime defaults live in `config/defaults.json`.
- Assumptions and formulas live in `docs/assumptions.md`.
- Example inputs live in `examples/`.
- The CLI only accepts and emits JSON.
