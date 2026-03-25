# JSON-First UI Spec

## Purpose

The next UI phase should start from a machine-readable JSON spec rather than from prose alone.

That JSON spec serves two audiences:

- coding agents such as Claude Code that need an explicit handoff contract
- a future human-facing web interface that should stay aligned with the planner's JSON input and output model

## Source of Truth

- `specs/ui_handoff_v1.json` is the machine-readable UI contract.
- This Markdown document explains how to interpret and evolve it.
- `docs/product_spec.md` remains the historical product brief and scope reference.

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

1. Update `specs/ui_handoff_v1.json` when UI scope or behavior changes.
2. Update this Markdown doc if the interpretation rules change.
3. Let the UI implementation follow the JSON contract.
4. Keep planner calculations and output generation in backend or shared deterministic logic, not duplicated in frontend code.
5. Review UI changes against both the JSON contract and the product spec.

## Recommended UI Scope For The First Human Interface

The first UI should stay narrow and operational:

- load or paste planning input JSON
- edit key planning fields in a structured form
- run the planner
- compare the original roadmap and the selected plan
- inspect the selected plan, delivered scope, deferred scope, and dropped scope
- inspect utilization, buffer, and business-goal assessment
- view or export raw output JSON

## Claude Code Handoff

When UI work is delegated to Claude Code, the handoff should include:

- the current `specs/ui_handoff_v1.json`
- the planner input and output examples in `examples/`
- the product rules in `AGENTS.md`
- explicit instruction not to move calculations into the frontend

## Design Direction

The UI should be clean, readable, and decision-oriented.

Important qualities:

- structured rather than decorative
- strong visual hierarchy for risks, utilization, and scope decisions
- raw JSON still available for agent and power-user workflows
- no hidden business logic in the presentation layer
