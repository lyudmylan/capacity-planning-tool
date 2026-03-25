# Current State

## Purpose

This document is the living summary of what the project currently ships.

Use it for:

- current capabilities
- known constraints
- current documentation map
- next-step direction

Use [`product_spec.md`](product_spec.md) for the historical original brief instead.

## Shipped Today

- JSON-in / JSON-out capacity planning CLI
- deterministic capacity and demand calculations
- bounded replanning loop with business-goal support
- thin Flask-backed web UI
- original-vs-selected plan comparison in the UI
- JSON-first UI handoff contract in `specs/ui_handoff_v1.json`

## Still Deterministic

The shipped planner still keeps all calculations deterministic.

- no LLM is used for capacity or demand calculations
- no LLM is used for candidate rescoring
- `risks`, `suggestions`, and `tradeoff_summary` remain deterministic outputs today

## Current Constraints

- no database
- no external integrations
- no week-by-week or sprint allocation engine
- no LLM-backed advisor yet

## Documentation Map

- [`product_spec.md`](product_spec.md)
  Historical original request and guardrails.
- [`assumptions.md`](assumptions.md)
  Formulas, defaults, and behavioral assumptions.
- [`agentic_replanning_plan.md`](agentic_replanning_plan.md)
  Future optional LLM-advisor work.
- [`ui_json_spec.md`](ui_json_spec.md)
  Human-readable explanation of the JSON UI contract.
- [`shipping_workflow.md`](shipping_workflow.md)
  Pointer to the canonical shipping workflow in `AGENTS.md`.

## Known Gaps

- the replanning loop is agentic in structure, but not yet LLM-backed
- the UI is intentionally thin and operational rather than expansive

## Next Best Steps

- add an optional LLM-backed advisor without moving calculations into the model
- deepen the UI only where it improves decision support
- keep reducing duplication across docs when responsibilities drift
