# JSON-First UI Spec

## Purpose

The next UI phase should start from a machine-readable JSON spec rather than from prose alone.

That JSON spec serves two audiences:

- coding agents such as Claude Code that need an explicit handoff contract
- a future human-facing web interface that should stay aligned with the planner's JSON input and output model

## Source of Truth

- `specs/ui_handoff_v1.json` is the current machine-readable UI contract for the shipped v2-aware UI.
- This Markdown document explains how to interpret and evolve it.
- `docs/product.md` is the living product and scope reference.

## Core Principle

Define the UI as a structured contract, not as an informal design request.

That means the spec should describe:

- the supported user tasks
- the screens or panels required
- the JSON data the UI consumes and emits
- the actions the UI must support
- the design constraints that matter for implementation quality

## Why This Fits The Project

The planner already uses JSON for machine-readable input and output. A JSON-first UI spec extends the same philosophy:

- agents can read it and implement from it
- humans can review it in code review
- a web UI can map directly to planner inputs and outputs
- the repo preserves a versioned contract instead of relying on chat history

## Expected Workflow

1. Update `specs/ui_handoff_v1.json` when shipped UI scope or contract behavior changes.
2. Update this Markdown doc if the interpretation rules change.
3. Let the UI implementation follow the JSON contract.
4. Keep planner calculations and output generation in backend or shared deterministic logic, not duplicated in frontend code.
5. Review UI changes against the JSON contract, the living product doc, and the shipped planner output.

## Shipped v2 Scope

The current UI stays narrow and operational, but it now has to reflect two planner modes:

- `capacity_check`
- `planning_schedule`

The current shipped scope is:

- load or paste planning input JSON
- edit key planning fields in a structured form
- keep period selectors schema-valid when `planning_horizon` changes in the structured editor
- run the planner
- compare the original roadmap and the selected plan for `capacity_check`
- inspect delivered scope, deferred scope, dropped scope, and selected-plan details
- inspect capacity, demand, utilization, and bottlenecks by function
- inspect business-goal status and dependency-rule outcomes when present
- view or export raw output JSON

## Shipped Output Contract

The shipped planner output is mode-specific.

For `capacity_check`, the top-level UI contract is:

- shared context such as `planning_mode`, `capacity_dev_days`, and `capacity_by_function`
- `baseline_plan`
- `selected_plan`
- `evaluated_alternatives`
- `agentic_iterations`
- `risks`
- `suggestions`
- `tradeoff_summary`

For `planning_schedule`, the top-level UI contract is:

- the evaluated plan fields directly at the top level
- `selected_plan`
- `dependency_rules_pass`
- `dependency_violations`
- `evaluated_alternatives`
- `agentic_iterations`
- `risks`
- `suggestions`
- `tradeoff_summary`

Both modes expose function-aware plan payloads, and `planning_schedule` adds dependency-rule status.

## Claude Code Handoff

When UI work is delegated to Claude Code, the handoff should include:

- the current `specs/ui_handoff_v1.json`
- the relevant planner input and output examples in `examples/`
- the product rules in `AGENTS.md`
- explicit instruction not to move calculations into the frontend
- explicit instruction to preserve the mode-specific v2 output contract unless the spec changes first

## Design Direction

The UI should be clean, readable, and decision-oriented.

Important qualities:

- structured rather than decorative
- strong visual hierarchy for risks, utilization, and scope decisions
- raw JSON still available for agent and power-user workflows
- no hidden business logic in the presentation layer
