# Agentic Replanning Plan

## Why This Exists

The original spec asked for LLM usage to explain risks, suggest which features to defer or drop, and summarize tradeoffs while keeping calculations non-LLM. The shipped `V1.0` kept everything deterministic, which was safe for the first release but is not the best example of agentic use.

The next iteration should add a bounded runtime loop where an agent proposes alternatives and the deterministic planner evaluates them.

## Product Goal

Given:

- team capacity
- planning horizon
- roadmap demand
- explicit business goals

the tool should recommend the best acceptable plan, not just the first feasible trimmed plan.

## Example Business Goals

- Deliver features `1`, `5`, `7`, and `8` by the end of Q2
- Preserve all `Critical` features unless no feasible plan exists
- Keep utilization below `0.9`
- Preserve at least `10%` capacity buffer
- Prefer deferring internal work before customer-facing work
- Keep at least one growth feature in scope

## Proposed Input Extension

Add an optional JSON section like:

```json
{
  "business_goals": {
    "must_deliver_feature_ids": ["1", "5", "7", "8"],
    "preserve_priorities": ["Critical"],
    "max_utilization": 0.9,
    "min_buffer_ratio": 0.1,
    "defer_preference": ["Low", "Medium", "High", "Critical"]
  }
}
```

The exact shape can evolve, but the key rule is that business goals remain explicit and machine-readable.

## Proposed Architecture

### Deterministic Layer

Responsible for:

- parsing input JSON
- computing capacity and demand
- generating feature-level demand values
- evaluating candidate plans against feasibility, utilization, and buffer rules
- scoring candidate plans against business-goal constraints

### Agentic Layer

Responsible for:

- reading deterministic planner output
- proposing one or more scope alternatives
- deciding which features to defer or drop to satisfy business goals
- explaining risks and tradeoffs in natural language

### Guardrail

Every agent-proposed alternative must be re-evaluated by the deterministic layer before it can be returned.

## Proposed Agentic Loop

Use a bounded loop:

1. Compute the baseline plan deterministically.
2. If the baseline plan is acceptable, keep it.
3. Otherwise, ask the agent for candidate alternatives that respect the business goals.
4. Re-score each candidate deterministically.
5. Keep the best acceptable candidate.
6. Stop after a small fixed number of rounds or once no better candidate is found.

This is the intended agentic pattern:

- propose
- evaluate
- revise
- stop

## Output Direction

The tool should continue to emit JSON only. A future output may add fields such as:

- `selected_plan_reason`
- `evaluated_alternatives`
- `business_goal_assessment`
- `agentic_iterations`

## Non-Goals

The next iteration should still avoid:

- moving calculations into the LLM
- weekly or sprint-by-sprint scheduling allocation
- a UI or database layer
- open-ended autonomous behavior without bounded retries

## Delivery Plan

1. Add explicit business-goal input schema.
2. Split deterministic evaluation from narrative generation more cleanly.
3. Introduce a bounded replanning loop with deterministic scoring of candidates.
4. Keep all final machine-readable outputs in JSON.
5. Add tests covering:
   - business goal preservation
   - bounded iteration behavior
   - deterministic re-scoring of agent proposals
   - fallback behavior when no acceptable candidate is found
