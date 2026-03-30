# JSON-First UI Spec

## Purpose

The UI handoff should now be treated as an implementation-ready target, not just a record of the shipped UI.

`specs/ui_handoff_v1.json` defines the next UI iteration we want Claude Code to build, while staying anchored to the shipped v2 planner contract.

## Source of Truth

- `specs/ui_handoff_v1.json` is the machine-readable handoff contract.
- `docs/product.md` is the product and scope reference.
- `tests/test_server.py` locks the shipped backend output contract.
- `tests/test_ui_spec.py` locks the UI handoff contract.
- `ui/index.html` and `ui/app.js` are the shipped baseline, not the limit of the next iteration.

## What Changed In This Spec Pass

This pass moves the UI spec from "shipped contract alignment" to "build-ready target."

The spec now defines:

- intended information architecture
- mode flows for `capacity_check` and `planning_schedule`
- structured editing scope and field groups
- validation and state behavior
- output presentation priority
- Claude-facing implementation guidance

## Core Principle

Define the UI as a structured contract, not as an informal design brief.

That means the spec should tell an implementation agent:

- what the user is trying to do
- which surfaces and sections exist
- which planner fields deserve prominent UI treatment
- which planner fields stay secondary or raw-only
- how mode-specific behavior should change the experience

## Scope Boundary

This spec is for the next UI iteration.

It should:

- reflect the shipped backend contract exactly
- make the UI more intentional and easier to scan
- keep raw JSON available at all times
- keep planner calculations in backend code only

It should not:

- invent new backend fields
- duplicate planner logic in frontend code
- turn the UI into a stateful product with persistence or integrations

## Information Architecture

The next UI should still be a single-page workspace, but it should read as two coordinated workspaces:

- `Planning Input`: author a valid planner payload
- `Planning Output`: review the decision produced by the planner

Inside those workspaces, the intended sections are:

### Input Workspace

- `example_loader`
- `mode_and_period`
- `capacity_controls`
- `organization`
- `roadmap`
- `business_goals`
- `raw_input_json`

### Output Workspace

- `summary`
- `function_analysis`
- `scope_decision`
- `goal_and_dependency_review`
- `raw_output_json`

This is a deliberate upgrade from the shipped operational UI: function analysis becomes a first-class section instead of being implied through summary details.

## Mode Flows

### Capacity Check

The UI should guide the user through:

1. choose `planning_mode = capacity_check`
2. define horizon and period selectors
3. define organization and roadmap
4. optionally add business goals
5. run planner
6. compare `baseline_plan` and `selected_plan`
7. inspect function bottlenecks and scope cuts

The primary UI question is:

"Can the current organization likely deliver this roadmap in the chosen horizon?"

### Planning Schedule

The UI should guide the user through:

1. choose `planning_mode = planning_schedule`
2. define horizon and period selectors
3. define organization and roadmap
4. configure `org_schedule_policies`
5. optionally add business goals
6. run planner
7. inspect dependency-rule pressure and selected-plan feasibility

The primary UI question is:

"Can this selected scope finish inside the horizon once dependency rules are applied?"

Unlike `capacity_check`, this mode should not visually center a baseline-vs-selected comparison. The selected plan is the primary output surface.

## Input Editing Model

The next UI should support two synchronized input paths:

- structured editing for common and high-value planner fields
- raw JSON editing for full-fidelity control

The raw JSON payload remains the source of truth.

Structured editing should cover:

- mode and period selection
- capacity controls
- R&D organization setup
- roadmap feature editing
- business goals
- schedule-policy editing when `planning_mode = planning_schedule`

Structured editing does not need to expose every possible planner field. Unsupported fields must survive round-trips through the raw JSON editor.

## Validation Behavior

The UI should treat these as blocking errors:

- invalid JSON
- non-object JSON
- schema validation failures

Expected behavior:

- the Run action is disabled while input is invalid
- parse and validation errors appear inline in the input workspace
- schema errors should preserve the backend field path in the message
- planner execution failures should show as a blocking summary banner

Important normalization rules:

- changing `planning_horizon` must reconcile period selectors automatically
- switching to `capacity_check` hides schedule-policy inputs
- manual capacity-day fields remain all-or-none

## State Model

The intended UI state model is:

- `pristine`
- `draft_loaded`
- `draft_dirty`
- `input_invalid`
- `ready_to_run`
- `running`
- `result_ready`
- `run_error`

Important transitions:

- loading an example or JSON moves the UI into `draft_loaded`
- editing either raw JSON or structured fields moves the UI into `draft_dirty`
- successful validation moves it to `ready_to_run`
- validation failure moves it to `input_invalid`
- running the planner moves it to `running`
- a successful run moves it to `result_ready`
- a failed run moves it to `run_error`

This matters because the next UI iteration should make the editing and execution lifecycle obvious rather than relying on implicit browser state.

## Output Presentation Rules

The next UI should treat planner output fields in three tiers.

### Primary

These deserve visible UI treatment:

- mode and feasibility
- function capacity fit and bottlenecks
- delivered, deferred, and dropped scope
- risks, suggestions, and tradeoff summary
- dependency-rule pass or fail and dependency violations when present

### Secondary

These should be shown, but can live in denser cards or expandable details:

- aggregate capacity and demand metrics
- per-function demand, utilization, and buffer values
- business-goal assessment details
- evaluated alternatives
- agentic iteration counts

### Raw JSON Only By Default

Any planner field not explicitly promoted to primary or secondary should still be available in the raw output panel, but it does not need its own dedicated visual component.

## Panel Expectations

### Summary

Must answer:

- which mode ran
- whether the result is feasible
- whether function capacity fits
- whether dependency rules passed when applicable

### Function Analysis

Must make these easy to scan:

- capacity by function
- demand by function
- utilization by function
- buffer by function
- bottleneck functions

### Scope Decision

For `capacity_check`, this panel should emphasize:

- `baseline_plan`
- `selected_plan`
- what changed between them

For `planning_schedule`, this panel should emphasize:

- selected-plan delivered scope
- deferred or dropped scope
- schedule consequences rather than comparison-first framing

### Goals And Dependencies

This panel should present:

- canonical plan-level goal status
- business-goal assessment details
- dependency violations when present
- tradeoff summary

## Claude Code Handoff

When this UI work is handed to Claude Code, the handoff should include:

- `specs/ui_handoff_v1.json`
- this document
- relevant planner examples from `examples/`
- the current backend contract tests in `tests/test_server.py`
- the shipped UI baseline in `ui/index.html` and `ui/app.js`

Implementation guidance for Claude:

- keep planner logic in backend code
- preserve raw JSON access
- implement mode-specific views deliberately rather than sharing one vague summary surface
- update `tests/test_ui_spec.py` whenever the handoff contract changes
- update UI logic tests when interaction rules or normalization behavior change

## Review Standard

UI implementation review should verify:

- alignment with `specs/ui_handoff_v1.json`
- no frontend duplication of planner calculations
- mode-specific output rendering matches shipped backend fields
- raw JSON fidelity is preserved
- horizon and mode switching remain schema-valid
